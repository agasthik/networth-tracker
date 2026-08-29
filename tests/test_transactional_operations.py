"""Regression tests for atomic financial mutations and strict restores."""

from datetime import datetime
from unittest.mock import patch

import pytest

from services.account_operations import AccountOperationService
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.export_import import ExportImportService


@pytest.fixture
def db_service(tmp_path):
    encryption = EncryptionService()
    encryption.derive_key("TransactionalTestPassword123!")
    service = DatabaseService(str(tmp_path / "transactional.db"), encryption)
    service.connect()
    yield service
    service.close()


def test_account_creation_rolls_back_when_snapshot_fails(db_service):
    operations = AccountOperationService(db_service)
    account_data = {
        "name": "Atomic Savings",
        "institution": "Test Bank",
        "type": "SAVINGS",
        "current_balance": 1000.0,
        "interest_rate": 1.0,
    }

    with patch.object(
        db_service,
        "create_historical_snapshot",
        side_effect=RuntimeError("snapshot failed"),
    ):
        with pytest.raises(RuntimeError, match="snapshot failed"):
            operations.create_account(account_data, 1000.0)

    assert db_service.get_accounts() == []


def test_quote_update_rolls_back_when_snapshot_fails(db_service):
    account_id = db_service.create_account(
        {
            "name": "Atomic Brokerage",
            "institution": "Test Broker",
            "type": "TRADING",
            "broker_name": "Test Broker",
            "cash_balance": 100.0,
        }
    )
    position_id = db_service.create_stock_position(
        account_id,
        "AAPL",
        2.0,
        100.0,
        int(datetime(2024, 1, 1).timestamp()),
    )
    db_service.update_stock_price(position_id, 110.0)

    with patch.object(
        db_service,
        "create_historical_snapshot",
        side_effect=RuntimeError("snapshot failed"),
    ):
        with pytest.raises(RuntimeError, match="snapshot failed"):
            AccountOperationService(db_service).update_stock_prices(
                account_id,
                [{"position_id": position_id, "price": 125.0}],
            )

    position = db_service.get_stock_positions(account_id)[0]
    assert position["current_price"] == 110.0


def test_import_failure_rolls_back_all_prior_records(db_service):
    backup = {
        "backup_metadata": {
            "backup_version": "1.0",
            "format_version": 1,
        },
        "accounts": [
            {
                "id": "valid-account",
                "name": "Valid",
                "institution": "Bank",
                "type": "SAVINGS",
                "current_balance": 10.0,
                "created_date": "2024-01-01T00:00:00",
                "last_updated": "2024-01-02T00:00:00",
            },
            {
                "id": "invalid-account",
                "name": "Invalid",
                "type": "SAVINGS",
            },
        ],
        "stock_positions": {},
        "watchlist": [],
        "historical_snapshots": {},
        "app_settings": {},
    }

    with pytest.raises(Exception, match="Failed to import data"):
        ExportImportService(
            db_service,
            db_service.encryption_service,
        ).import_data(backup)

    assert db_service.get_accounts() == []


def test_import_preserves_account_identity_and_timestamps(db_service):
    backup = {
        "backup_metadata": {
            "backup_version": "1.0",
            "format_version": 1,
        },
        "accounts": [
            {
                "id": "preserved-account-id",
                "name": "Preserved",
                "institution": "Bank",
                "type": "SAVINGS",
                "current_balance": 25.0,
                "created_date": "2024-02-03T04:05:06",
                "last_updated": "2024-03-04T05:06:07",
            }
        ],
        "stock_positions": {},
        "watchlist": [],
        "historical_snapshots": {},
        "app_settings": {},
    }

    ExportImportService(
        db_service,
        db_service.encryption_service,
    ).import_data(backup)

    restored = db_service.get_account("preserved-account-id")
    assert restored["id"] == "preserved-account-id"
    assert restored["created_date"] == datetime(2024, 2, 3, 4, 5, 6)
    assert restored["last_updated"] == datetime(2024, 3, 4, 5, 6, 7)
