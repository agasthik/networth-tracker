"""
End-to-end tests for complete user workflows.

Tests cover:
- Complete user authentication flow
- Account creation and management workflows
- Stock position management workflows
- Data export/import workflows
- Demo mode workflows
- Historical data tracking workflows
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from services.auth import AuthenticationManager
from services.stock_prices import StockPriceService
from services.historical import HistoricalDataService
from services.export_import import ExportImportService

# The demo data generator now lives in the standalone demo database script.
from scripts.generate_demo_database import DemoDataGenerator
from models.accounts import AccountFactory, AccountType, StockPosition, ChangeType


class _FakeSession(dict):
    """Dict-based stand-in for the Flask session that also supports attribute
    access (e.g. ``session.permanent``), used to patch ``services.auth.session``
    outside of a real Flask request context."""

    pass


class TestEndToEndUserWorkflows(unittest.TestCase):
    """End-to-end tests for complete user workflows."""

    def setUp(self):
        """Set up test environment with all services."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")

        # Initialize services
        self.auth_manager = AuthenticationManager(self.db_path)
        self.test_password = "TestPassword123!"

        # Set up authentication
        self.auth_manager.set_master_password(self.test_password)

        # Reuse the auth manager's encryption and database services so the
        # encryption key (derived with the salt persisted in the DB) matches.
        # Creating a standalone EncryptionService would derive a key with a
        # different random salt, causing InvalidToken decryption failures.
        self.encryption_service = self.auth_manager.encryption_service
        self.db_service = self.auth_manager.db_service
        self.db_service.connect()

        # Initialize other services
        self.stock_service = StockPriceService(rate_limit_delay=0.01)
        # Force deterministic behavior: disable the live HTTP "alternative" price
        # fetch so tests exercise the mocked yfinance path instead of the network.
        self.stock_service._try_alternative_price_fetch = lambda symbol: None
        self.historical_service = HistoricalDataService(self.db_service)
        self.export_service = ExportImportService(
            self.db_service, self.encryption_service
        )

    def tearDown(self):
        """Clean up test environment."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_complete_user_onboarding_workflow(self):
        """Test complete user onboarding from setup to first account creation."""
        # Step 1: User sets up master password (already done in setUp)
        self.assertFalse(self.auth_manager.is_setup_required())

        # Step 2: User logs in
        with patch("services.auth.session", _FakeSession()):
            login_success = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(login_success)

        # Step 3: User creates their first account (CD)
        cd_account = AccountFactory.create_account(
            AccountType.CD,
            name="My First CD",
            institution="Local Bank",
            principal_amount=10000.0,
            interest_rate=2.5,
            maturity_date=date.today() + timedelta(days=365),
            current_value=10000.0,
        )

        # Store account in database
        account_dict = cd_account.to_dict()
        account_dict["type"] = account_dict["account_type"]
        if "id" in account_dict:
            del account_dict["id"]

        account_id = self.db_service.create_account(account_dict)
        cd_account.id = account_id

        # Step 4: Verify account was created and can be retrieved
        retrieved_accounts = self.db_service.get_accounts()
        self.assertEqual(len(retrieved_accounts), 1)
        self.assertEqual(retrieved_accounts[0]["name"], "My First CD")

        # Step 5: User updates account value (creates historical snapshot).
        # create_snapshot_if_value_changed compares the account's *current* value
        # against the supplied previous value, so the new value must be applied
        # before the check for a snapshot to be recorded.
        previous_value = cd_account.current_value
        updated_value = 10125.0
        cd_account.current_value = updated_value

        snapshot_id = self.historical_service.create_snapshot_if_value_changed(
            cd_account, previous_value, ChangeType.MANUAL_UPDATE
        )
        self.assertIsNotNone(snapshot_id)

        # Persist the updated account value
        account_dict = cd_account.to_dict()
        account_dict["type"] = account_dict["account_type"]
        self.db_service.update_account(account_id, account_dict)

        # Verify historical snapshot was created
        snapshots = self.historical_service.get_historical_snapshots(account_id)
        self.assertGreater(len(snapshots), 0)

    def test_complete_trading_account_workflow(self):
        """Test complete workflow for trading account with stock positions."""
        # Step 1: Create trading account
        trading_account = AccountFactory.create_account(
            AccountType.TRADING,
            name="My Trading Account",
            institution="Online Broker",
            broker_name="Online Broker",
            cash_balance=5000.0,
            positions=[],
        )

        account_dict = trading_account.to_dict()
        account_dict["type"] = account_dict["account_type"]
        if "id" in account_dict:
            del account_dict["id"]

        account_id = self.db_service.create_account(account_dict)
        trading_account.id = account_id

        # Step 2: Add stock positions
        positions = [
            StockPosition(
                symbol="AAPL",
                shares=50.0,
                purchase_price=150.0,
                purchase_date=date.today() - timedelta(days=30),
            ),
            StockPosition(
                symbol="GOOGL",
                shares=10.0,
                purchase_price=2500.0,
                purchase_date=date.today() - timedelta(days=15),
            ),
        ]

        for position in positions:
            self.db_service.create_stock_position(
                account_id,
                position.symbol,
                position.shares,
                position.purchase_price,
                int(position.purchase_date.strftime("%s")),
            )

        # Step 3: Update stock prices
        with patch("services.stock_prices.yf.Ticker") as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            def mock_history(period):
                symbol = mock_ticker.call_args[0][0]
                prices = {"AAPL": 160.0, "GOOGL": 2600.0}
                import pandas as pd

                return pd.DataFrame(
                    {"Close": [prices.get(symbol, 100.0)]}, index=[datetime.now()]
                )

            mock_ticker_instance.history.side_effect = mock_history

            # Update positions with current prices
            db_positions = self.db_service.get_stock_positions(account_id)
            for position in db_positions:
                current_price = self.stock_service.get_current_price(position["symbol"])
                self.db_service.update_stock_price(position["id"], current_price)

        # Step 4: Verify portfolio value calculation
        updated_positions = self.db_service.get_stock_positions(account_id)
        total_stock_value = sum(
            pos["current_price"] * pos["shares"] for pos in updated_positions
        )
        total_portfolio_value = total_stock_value + trading_account.cash_balance

        # AAPL: 160 * 50 = 8000, GOOGL: 2600 * 10 = 26000, Cash: 5000 = Total: 39000
        expected_total = 39000.0
        self.assertEqual(total_portfolio_value, expected_total)

        # Step 5: Create historical snapshot for portfolio
        self.historical_service.create_snapshot(
            trading_account,
            ChangeType.STOCK_PRICE_UPDATE,
            {"total_portfolio_value": total_portfolio_value},
        )

        # Verify snapshot was created
        snapshots = self.historical_service.get_historical_snapshots(account_id)
        self.assertGreater(len(snapshots), 0)

    def test_complete_export_import_workflow(self):
        """Test complete data export and import workflow."""
        # Step 1: Create multiple accounts with different types
        accounts_data = [
            {
                "type": AccountType.CD,
                "name": "Test CD",
                "institution": "Bank A",
                "principal_amount": 5000.0,
                "interest_rate": 2.0,
                "maturity_date": date.today() + timedelta(days=365),
                "current_value": 5100.0,
            },
            {
                "type": AccountType.SAVINGS,
                "name": "Test Savings",
                "institution": "Bank B",
                "current_balance": 15000.0,
                "interest_rate": 1.5,
            },
        ]

        created_accounts = []
        for account_data in accounts_data:
            account_type = account_data.pop("type")
            account = AccountFactory.create_account(account_type, **account_data)

            account_dict = account.to_dict()
            account_dict["type"] = account_dict["account_type"]
            if "id" in account_dict:
                del account_dict["id"]

            account_id = self.db_service.create_account(account_dict)
            account.id = account_id
            created_accounts.append(account)

        # Step 2: Create historical data
        for account in created_accounts:
            for i in range(3):
                self.historical_service.create_snapshot(
                    account, ChangeType.MANUAL_UPDATE, {"iteration": i}
                )

        # Step 3: Export all data
        export_data = self.export_service.export_data()

        self.assertIn("accounts", export_data)
        self.assertIn("historical_snapshots", export_data)
        self.assertIn("backup_metadata", export_data)
        self.assertEqual(len(export_data["accounts"]), 2)

        # Step 4: Clear database (simulate data loss)
        for account in created_accounts:
            self.db_service.delete_account(account.id)

        # Verify data is gone
        remaining_accounts = self.db_service.get_accounts()
        self.assertEqual(len(remaining_accounts), 0)

        # Step 5: Import data back
        import_result = self.export_service.import_data(export_data)

        self.assertEqual(len(import_result["errors"]), 0)
        self.assertEqual(import_result["accounts_imported"], 2)
        self.assertGreater(import_result["historical_snapshots_imported"], 0)

        # Step 6: Verify data was restored
        restored_accounts = self.db_service.get_accounts()
        self.assertEqual(len(restored_accounts), 2)

        # Verify account details
        cd_account = next(acc for acc in restored_accounts if acc["type"] == "CD")
        self.assertEqual(cd_account["name"], "Test CD")
        self.assertEqual(cd_account["principal_amount"], 5000.0)

    def test_complete_demo_mode_workflow(self):
        """Test complete demo mode workflow."""
        # Step 1: Initialize demo mode
        demo_generator = DemoDataGenerator()

        # Step 2: Generate demo accounts
        demo_accounts = demo_generator.generate_demo_accounts()

        self.assertGreater(len(demo_accounts), 0)

        # Verify we have different account types
        account_types = {account.account_type for account in demo_accounts}
        expected_types = {
            AccountType.CD,
            AccountType.SAVINGS,
            AccountType.ACCOUNT_401K,
            AccountType.TRADING,
            AccountType.I_BONDS,
            AccountType.HSA,
        }
        self.assertTrue(account_types.issubset(expected_types))

        # Step 3: Store demo accounts in database
        demo_account_ids = []
        for account in demo_accounts:
            account_dict = account.to_dict()
            account_dict["type"] = account_dict["account_type"]
            if "id" in account_dict:
                del account_dict["id"]

            account_id = self.db_service.create_account(account_dict)
            demo_account_ids.append(account_id)

        # Step 4: Generate historical data for demo accounts
        for i, account in enumerate(demo_accounts):
            account.id = demo_account_ids[i]
            historical_data = demo_generator.generate_historical_data([account])

            for snapshot in historical_data:
                self.db_service.create_historical_snapshot(
                    snapshot.account_id,
                    snapshot.value,
                    snapshot.change_type.value,
                    snapshot.metadata,
                )

        # Step 5: Verify demo data integrity
        all_accounts = self.db_service.get_accounts()
        self.assertEqual(len(all_accounts), len(demo_accounts))

        # Verify historical data exists
        for account_id in demo_account_ids:
            snapshots = self.historical_service.get_historical_snapshots(account_id)
            self.assertGreater(len(snapshots), 0)

        # Step 6: Test demo mode calculations
        total_networth = 0
        for account in all_accounts:
            if account["type"] == "CD":
                total_networth += account["current_value"]
            elif account["type"] == "SAVINGS":
                total_networth += account["current_balance"]
            elif account["type"] == "401K":
                total_networth += account["current_balance"]
            elif account["type"] == "TRADING":
                total_networth += account["cash_balance"]
                # Add stock positions value if any
                positions = self.db_service.get_stock_positions(account["id"])
                for pos in positions:
                    if pos["current_price"]:
                        total_networth += pos["current_price"] * pos["shares"]
                    else:
                        total_networth += pos["purchase_price"] * pos["shares"]
            elif account["type"] == "I_BONDS":
                total_networth += account["current_value"]

        self.assertGreater(total_networth, 0)

    def test_complete_historical_analysis_workflow(self):
        """Test complete historical data analysis workflow."""
        # Step 1: Create account with varying values over time
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Growth Savings",
            institution="Growth Bank",
            current_balance=10000.0,
            interest_rate=2.0,
        )

        account_dict = account.to_dict()
        account_dict["type"] = account_dict["account_type"]
        if "id" in account_dict:
            del account_dict["id"]

        account_id = self.db_service.create_account(account_dict)
        account.id = account_id

        # Step 2: Create historical snapshots with a growth pattern.
        # Use monthly snapshots spanning a full year and ending "today" so that
        # short (30 day) and long (365 day) look-back windows both resolve to a
        # snapshot near their boundaries. get_value_at_date only considers
        # snapshots within +/-7 days of a target, so sparse/older-only data would
        # leave the recent boundary empty and every period would collapse to 0%.
        values = [
            10000,
            10125,
            10250,
            10300,
            10500,
            10650,
            10800,
            10900,
            11050,
            11150,
            11300,
            11400,
            11500,
        ]
        num_points = len(values)
        # Spread evenly across the last 360 days, with the final point at "today".
        base_date = datetime.now() - timedelta(days=360)
        spacing_days = 360 // (num_points - 1)

        with patch("services.database.datetime") as mock_datetime:
            for i, value in enumerate(values):
                snapshot_date = base_date + timedelta(days=i * spacing_days)
                mock_datetime.now.return_value.timestamp.return_value = (
                    snapshot_date.timestamp()
                )

                self.db_service.create_historical_snapshot(
                    account_id, value, "MANUAL_UPDATE"
                )

        # Step 3: Calculate performance metrics
        performance = self.historical_service.calculate_performance_metrics(account_id)

        self.assertIsNotNone(performance)
        self.assertEqual(performance.start_value, float(values[0]))
        self.assertEqual(performance.end_value, float(values[-1]))
        self.assertEqual(performance.absolute_change, float(values[-1] - values[0]))
        self.assertAlmostEqual(
            performance.percentage_change, (values[-1] - values[0]) / values[0] * 100
        )
        self.assertEqual(performance.total_snapshots, len(values))

        # Step 4: Analyze trend
        trend = self.historical_service.analyze_trend(account_id)

        self.assertIsNotNone(trend)
        self.assertGreater(trend.slope, 0)  # Positive slope for growth
        self.assertGreater(trend.r_squared, 0.5)  # Reasonable correlation

        # Step 5: Calculate gains/losses for different periods
        gains_30_days = self.historical_service.calculate_gains_losses(account_id, 30)
        self.historical_service.calculate_gains_losses(account_id, 90)
        gains_365_days = self.historical_service.calculate_gains_losses(account_id, 365)

        # Verify different time periods show different results
        self.assertNotEqual(
            gains_30_days["percentage_gain_loss"],
            gains_365_days["percentage_gain_loss"],
        )

        # Step 6: Get monthly summary
        current_year = datetime.now().year
        monthly_summary = self.historical_service.get_monthly_summary(
            account_id, current_year
        )

        self.assertEqual(len(monthly_summary), 12)

        # Verify some months have data
        months_with_data = [
            month for month in monthly_summary if month["snapshots_count"] > 0
        ]
        self.assertGreater(len(months_with_data), 0)

    def test_complete_security_workflow(self):
        """Test complete security workflow including encryption and authentication."""
        # Step 1: Test password strength validation
        weak_passwords = ["weak", "12345678", "password"]

        for weak_pwd in weak_passwords:
            with self.assertRaises(ValueError):
                temp_auth = AuthenticationManager(":memory:")
                temp_auth.set_master_password(weak_pwd)

        # Step 2: Test encryption of sensitive data
        sensitive_data = {
            "account_balance": 50000.0,
            "ssn": "123-45-6789",
            "account_number": "9876543210",
        }

        encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data))
        self.assertNotIn(b"50000.0", encrypted_data)
        self.assertNotIn(b"123-45-6789", encrypted_data)

        # Step 3: Test decryption
        decrypted_data = json.loads(self.encryption_service.decrypt(encrypted_data))
        self.assertEqual(decrypted_data, sensitive_data)

        # Step 4: Test session management
        with patch("services.auth.session", _FakeSession()):
            # Login
            login_success = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(login_success)

            # Check authentication status
            is_authenticated = self.auth_manager.is_authenticated()
            self.assertTrue(is_authenticated)

            # Logout
            self.auth_manager.logout()

            # Check authentication status after logout
            is_authenticated = self.auth_manager.is_authenticated()
            self.assertFalse(is_authenticated)

        # Step 5: Test database encryption integrity
        # Logout deliberately clears key material and closes the database, so a
        # fresh authenticated session is required before accessing data again.
        with patch("services.auth.session", _FakeSession()):
            self.assertTrue(self.auth_manager.verify_password(self.test_password))
        self.db_service = self.auth_manager.db_service

        # Create account with sensitive data
        account_data = {
            "name": "Sensitive Account",
            "institution": "Private Bank",
            "type": "SAVINGS",
            "current_balance": 100000.0,
            "account_number": "SENSITIVE123",
        }

        account_id = self.db_service.create_account(account_data)

        # Verify data is encrypted in database
        cursor = self.db_service.connection.cursor()
        cursor.execute(
            "SELECT encrypted_data FROM accounts WHERE id = ?", (account_id,)
        )
        row = cursor.fetchone()

        encrypted_blob = row["encrypted_data"]
        self.assertNotIn(b"100000.0", encrypted_blob)
        self.assertNotIn(b"SENSITIVE123", encrypted_blob)

        # Verify data can be decrypted correctly
        retrieved_account = self.db_service.get_account(account_id)
        self.assertEqual(retrieved_account["current_balance"], 100000.0)
        self.assertEqual(retrieved_account["account_number"], "SENSITIVE123")

    def test_error_recovery_workflow(self):
        """Test error recovery and data integrity workflows."""
        # Step 1: Test database corruption recovery
        account_data = {
            "name": "Test Account",
            "institution": "Test Bank",
            "type": "SAVINGS",
            "current_balance": 5000.0,
        }

        account_id = self.db_service.create_account(account_data)

        # Step 2: Test handling of invalid data.
        # The database layer persists raw dicts without validation, so an invalid
        # account type only raises when constructed through the AccountFactory.
        with self.assertRaises(Exception):
            invalid_data = {
                "name": "",  # Invalid empty name
                "institution": "Test Bank",
                "account_type": "INVALID_TYPE",  # Invalid account type
                "current_balance": -1000.0,  # Invalid negative balance
            }
            AccountFactory.create_account_from_dict(invalid_data)

        # Step 3: Test stock price API failure handling
        with patch("services.stock_prices.yf.Ticker") as mock_ticker:
            mock_ticker.side_effect = Exception("API Error")

            with self.assertRaises(Exception):
                self.stock_service.get_current_price("AAPL")

        # Step 4: Test data backup and recovery
        # Create backup
        export_data = self.export_service.export_data()

        # Simulate data corruption by deleting account
        self.db_service.delete_account(account_id)

        # Verify data is gone
        retrieved_account = self.db_service.get_account(account_id)
        self.assertIsNone(retrieved_account)

        # Restore from backup
        import_result = self.export_service.import_data(export_data)
        self.assertEqual(len(import_result["errors"]), 0)

        # Verify data is restored
        all_accounts = self.db_service.get_accounts()
        self.assertGreater(len(all_accounts), 0)


if __name__ == "__main__":
    unittest.main()
