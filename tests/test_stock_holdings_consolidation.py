"""Integration tests for canonical trading-account holdings."""

import json
from datetime import date, datetime, timedelta
from unittest.mock import patch

import pytest

import app as app_module
from services.auth import AuthenticationManager
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.migration import DatabaseMigration
from services.stock_prices import PriceUpdateResult


@pytest.fixture
def authenticated_client(tmp_path):
    db_path = str(tmp_path / "holdings.db")
    app_module.app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
    app_module.auth_manager = AuthenticationManager(db_path)
    client = app_module.app.test_client()
    password = "TestPassword123!"
    client.post(
        "/setup",
        data={"password": password, "confirm_password": password},
    )
    client.post("/login", data={"password": password})
    return client


def _trading_account_payload(*positions):
    return {
        "name": "Brokerage",
        "institution": "Test Broker",
        "type": "TRADING",
        "broker_name": "Test Broker",
        "cash_balance": 1000.0,
        "positions": list(positions),
    }


def _position(symbol="AAPL", current_price=120.0):
    return {
        "symbol": symbol,
        "shares": 2.0,
        "purchase_price": 100.0,
        "purchase_date": (date.today() - timedelta(days=30)).isoformat(),
        "current_price": current_price,
    }


def test_account_form_holdings_use_stock_positions_table(authenticated_client):
    response = authenticated_client.post(
        "/api/accounts",
        json=_trading_account_payload(_position()),
    )

    assert response.status_code == 201
    account = response.get_json()["account"]
    account_id = account["id"]
    assert account["current_value"] == 1240.0
    assert [position["symbol"] for position in account["positions"]] == ["AAPL"]

    db_service = app_module.auth_manager.db_service
    assert "positions" not in db_service.get_account(account_id)

    positions_response = authenticated_client.get(
        f"/api/accounts/{account_id}/positions"
    )
    assert positions_response.get_json()["positions"] == account["positions"]

    accounts_response = authenticated_client.get("/api/accounts")
    listed_account = accounts_response.get_json()["accounts"][0]
    assert listed_account["positions"] == account["positions"]
    assert listed_account["current_value"] == 1240.0

    portfolio = authenticated_client.get("/api/portfolio/summary").get_json()
    assert portfolio["total_networth"] == 1240.0
    assert portfolio["account_types"]["TRADING"]["value"] == 1240.0


def test_account_form_update_replaces_canonical_holdings(authenticated_client):
    created = authenticated_client.post(
        "/api/accounts",
        json=_trading_account_payload(_position(), _position("MSFT", 220.0)),
    ).get_json()["account"]
    account_id = created["id"]
    aapl = next(
        position for position in created["positions"] if position["symbol"] == "AAPL"
    )
    aapl.update({"shares": 3.0, "current_price": 130.0})

    response = authenticated_client.put(
        f"/api/accounts/{account_id}",
        json={
            "name": "Brokerage",
            "institution": "Test Broker",
            "broker_name": "Test Broker",
            "cash_balance": 1000.0,
            "positions": [aapl],
        },
    )

    assert response.status_code == 200
    positions = response.get_json()["account"]["positions"]
    assert len(positions) == 1
    assert positions[0]["id"] == aapl["id"]
    assert positions[0]["shares"] == 3.0
    assert positions[0]["current_price"] == 130.0


def test_global_price_update_uses_canonical_holdings(authenticated_client):
    account = authenticated_client.post(
        "/api/accounts",
        json=_trading_account_payload(_position(current_price=None)),
    ).get_json()["account"]

    price_result = PriceUpdateResult(
        symbol="AAPL",
        success=True,
        price=175.0,
        timestamp=datetime.now(),
    )
    with patch(
        "services.stock_prices.StockPriceService.get_batch_prices",
        return_value={"AAPL": price_result},
    ):
        response = authenticated_client.post("/api/stocks/prices")

    assert response.status_code == 200
    result = response.get_json()
    assert result["updated_positions"] == 1
    positions = authenticated_client.get(
        f"/api/accounts/{account['id']}/positions"
    ).get_json()["positions"]
    assert positions[0]["current_price"] == 175.0
    assert positions[0]["last_price_update"] is not None


def test_single_price_route_returns_market_data(authenticated_client):
    quote = {
        "symbol": "AAPL",
        "price": 175.0,
        "timestamp": datetime.now(),
        "success": True,
        "market_open": True,
        "error": None,
    }
    with patch(
        "services.stock_prices.StockPriceService.get_price_with_metadata",
        return_value=quote,
    ):
        response = authenticated_client.get("/api/stocks/aapl/price")

    assert response.status_code == 200
    assert response.get_json()["price"] == 175.0


def test_v6_migration_merges_and_removes_embedded_positions(tmp_path):
    encryption = EncryptionService()
    encryption.derive_key("TestPassword123!")
    db_service = DatabaseService(str(tmp_path / "migration.db"), encryption)
    db_service.connect()
    account_id = db_service.create_account(
        {
            "name": "Legacy Brokerage",
            "institution": "Test Broker",
            "type": "TRADING",
            "broker_name": "Test Broker",
            "cash_balance": 1000.0,
        }
    )
    canonical = _position(current_price=175.0)
    db_service.replace_stock_positions(account_id, [canonical])

    account_data = db_service.get_account(account_id)
    sensitive_data = {
        key: value
        for key, value in account_data.items()
        if key
        not in {
            "id",
            "name",
            "institution",
            "type",
            "created_date",
            "last_updated",
            "schema_version",
            "is_demo",
        }
    }
    sensitive_data["positions"] = [
        _position(current_price=90.0),
        _position("MSFT", 220.0),
    ]
    encrypted_data = encryption.encrypt(json.dumps(sensitive_data))
    cursor = db_service.connect().cursor()
    cursor.execute(
        "UPDATE accounts SET encrypted_data = ? WHERE id = ?",
        (encrypted_data, account_id),
    )
    db_service.connection.commit()

    DatabaseMigration(db_service)._migrate_to_v6_consolidate_stock_positions()

    positions = db_service.get_stock_positions(account_id)
    assert {position["symbol"] for position in positions} == {"AAPL", "MSFT"}
    aapl = next(position for position in positions if position["symbol"] == "AAPL")
    assert aapl["current_price"] == 175.0
    assert "positions" not in db_service.get_account(account_id)
