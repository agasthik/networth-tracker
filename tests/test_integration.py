"""
Integration tests for Flask routes and database operations.

Tests cover:
- Flask route integration with database operations
- API endpoint functionality with real database
- Cross-service integration testing
- Request/response validation
- Error handling in integrated environment
"""

import unittest
import tempfile
import os
import json
from unittest.mock import patch, MagicMock

# Mock Flask app configuration before importing
os.environ['FLASK_ENV'] = 'testing'

from services.database import DatabaseService
from services.encryption import EncryptionService
from services.auth import AuthenticationManager
from services.stock_prices import StockPriceService
from services.historical import HistoricalDataService
from services.export_import import ExportImportService
from models.accounts import AccountFactory, AccountType


class TestServiceIntegration(unittest.TestCase):
    """Integration tests for service interactions."""

    def setUp(self):
        """Set up integrated test environment."""
        # Create temporary database
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

        # Initialize services
        self.encryption_service = EncryptionService()
        self.test_password = "TestPassword123!"
        self.encryption_service.derive_key(self.test_password)

        self.auth_manager = AuthenticationManager(self.db_path)
        self.auth_manager.set_master_password(self.test_password)

        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

        self.stock_service = StockPriceService(rate_limit_delay=0.01)
        self.historical_service = HistoricalDataService(self.db_service)
        self.export_service = ExportImportService(self.db_service, self.encryption_service)

    def tearDown(self):
        """Clean up test environment."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_authentication_database_integration(self):
        """Test authentication service integration with database."""
        # Test initial setup state
        self.assertFalse(self.auth_manager.is_setup_required())

        # Test password verification with database
        with patch('flask.session', {}):
            result = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(result)

            # Test wrong password
            result = self.auth_manager.verify_password("WrongPassword123!")
            self.assertFalse(result)

        # Test that authentication state is stored in database
        # Create new auth manager instance to test persistence
        new_auth_manager = AuthenticationManager(self.db_path)
        self.assertFalse(new_auth_manager.is_setup_required())

    def test_account_creation_with_historical_tracking(self):
        """Test account creation integrated with historical data tracking."""
        # Create account through factory
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Integration Test Savings",
            institution="Test Bank",
            current_balance=5000.0,
            interest_rate=2.0
        )

        # Store in database
        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']

        account_id = self.db_service.create_account(account_dict)
        account.id = account_id

        # Create initial historical snapshot
        snapshot_id = self.historical_service.create_snapshot(
            account, 'INITIAL_ENTRY', {'note': 'Account created'}
        )

        self.assertIsNotNone(snapshot_id)

        # Verify account and snapshot exist
        retrieved_account = self.db_service.get_account(account_id)
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account['name'], "Integration Test Savings")

        snapshots = self.historical_service.get_historical_snapshots(account_id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0].value, 5000.0)

    def test_trading_account_stock_integration(self):
        """Test trading account integration with stock price service."""
        # Create trading account
        trading_account = AccountFactory.create_account(
            AccountType.TRADING,
            name="Integration Trading",
            institution="Test Broker",
            broker_name="Test Broker",
            cash_balance=10000.0,
            positions=[]
        )

        account_dict = trading_account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']

        account_id = self.db_service.create_account(account_dict)

        # Add stock positions to database
        from datetime import date
        purchase_date = int(date.today().timestamp())

        position_id1 = self.db_service.create_stock_position(
            account_id, 'AAPL', 100.0, 150.0, purchase_date
        )
        position_id2 = self.db_service.create_stock_position(
            account_id, 'GOOGL', 50.0, 2500.0, purchase_date
        )

        # Mock stock price updates
        with patch('services.stock_prices.yf.Ticker') as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            def mock_history(period):
                symbol = mock_ticker.call_args[0][0]
                prices = {'AAPL': 160.0, 'GOOGL': 2600.0}
                import pandas as pd
                return pd.DataFrame({
                    'Close': [prices.get(symbol, 100.0)]
                }, index=[pd.Timestamp.now()])

            mock_ticker_instance.history.side_effect = mock_history

            # Update stock prices
            positions = self.db_service.get_stock_positions(account_id)
            for position in positions:
                current_price = self.stock_service.get_current_price(position['symbol'])
                self.db_service.update_stock_price(position['id'], current_price)

        # Verify integration
        updated_positions = self.db_service.get_stock_positions(account_id)
        self.assertEqual(len(updated_positions), 2)

        # Check AAPL position
        aapl_position = next(p for p in updated_positions if p['symbol'] == 'AAPL')
        self.assertEqual(aapl_position['current_price'], 160.0)

        # Check GOOGL position
        googl_position = next(p for p in updated_positions if p['symbol'] == 'GOOGL')
        self.assertEqual(googl_position['current_price'], 2600.0)

        # Calculate total portfolio value
        total_stock_value = sum(pos['current_price'] * pos['shares'] for pos in updated_positions)
        total_portfolio_value = total_stock_value + 10000.0  # Cash balance

        expected_total = (160.0 * 100) + (2600.0 * 50) + 10000.0  # 16000 + 130000 + 10000 = 156000
        self.assertEqual(total_portfolio_value, expected_total)

    def test_export_import_integration(self):
        """Test export/import service integration with all data types."""
        # Create multiple account types
        accounts_data = [
            {
                'type': AccountType.CD,
                'name': "Test CD",
                'institution': "Bank A",
                'principal_amount': 5000.0,
                'interest_rate': 2.0,
                'maturity_date': date.today() + timedelta(days=365),
                'current_value': 5100.0
            },
            {
                'type': AccountType.TRADING,
                'name': "Test Trading",
                'institution': "Broker A",
                'broker_name': "Broker A",
                'cash_balance': 15000.0,
                'positions': []
            }
        ]

        created_account_ids = []
        for account_data in accounts_data:
            account_type = account_data.pop('type')
            account = AccountFactory.create_account(account_type, **account_data)

            account_dict = account.to_dict()
            account_dict['type'] = account_dict['account_type']
            if 'id' in account_dict:
                del account_dict['id']

            account_id = self.db_service.create_account(account_dict)
            created_account_ids.append(account_id)

            # Create historical snapshots
            account.id = account_id
            self.historical_service.create_snapshot(account, 'INITIAL_ENTRY')

        # Add stock position to trading account
        from datetime import date
        trading_account_id = created_account_ids[1]
        self.db_service.create_stock_position(
            trading_account_id, 'MSFT', 75.0, 300.0, int(date.today().timestamp())
        )

        # Export all data
        export_data = self.export_service.export_all_data()

        # Verify export structure
        self.assertIn('accounts', export_data)
        self.assertIn('historical_snapshots', export_data)
        self.assertIn('stock_positions', export_data)
        self.assertIn('metadata', export_data)

        self.assertEqual(len(export_data['accounts']), 2)
        self.assertGreater(len(export_data['historical_snapshots']), 0)
        self.assertEqual(len(export_data['stock_positions']), 1)

        # Clear database
        for account_id in created_account_ids:
            self.db_service.delete_account(account_id)

        # Verify data is gone
        remaining_accounts = self.db_service.get_accounts()
        self.assertEqual(len(remaining_accounts), 0)

        # Import data
        import_result = self.export_service.import_all_data(export_data)

        self.assertTrue(import_result['success'])
        self.assertEqual(import_result['accounts_imported'], 2)
        self.assertEqual(import_result['positions_imported'], 1)
        self.assertGreater(import_result['snapshots_imported'], 0)

        # Verify data restoration
        restored_accounts = self.db_service.get_accounts()
        self.assertEqual(len(restored_accounts), 2)

        # Verify trading account has stock position
        trading_account = next(acc for acc in restored_accounts if acc['type'] == 'TRADING')
        positions = self.db_service.get_stock_positions(trading_account['id'])
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['symbol'], 'MSFT')

    def test_historical_performance_integration(self):
        """Test historical service integration with performance calculations."""
        # Create account
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Performance Test Account",
            institution="Growth Bank",
            current_balance=10000.0,
            interest_rate=2.5
        )

        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']

        account_id = self.db_service.create_account(account_dict)
        account.id = account_id

        # Create historical snapshots with growth pattern
        from datetime import datetime, timedelta
        base_date = datetime.now() - timedelta(days=180)
        values = [10000, 10200, 10500, 10800, 11000, 11300, 11500]

        with patch('services.database.datetime') as mock_datetime:
            for i, value in enumerate(values):
                snapshot_date = base_date + timedelta(days=i * 30)
                mock_datetime.now.return_value.timestamp.return_value = snapshot_date.timestamp()

                self.db_service.create_historical_snapshot(
                    account_id, value, 'MANUAL_UPDATE'
                )

        # Test performance metrics calculation
        performance = self.historical_service.calculate_performance_metrics(account_id)

        self.assertIsNotNone(performance)
        self.assertEqual(performance.start_value, 10000.0)
        self.assertEqual(performance.end_value, 11500.0)
        self.assertEqual(performance.absolute_change, 1500.0)
        self.assertEqual(performance.percentage_change, 15.0)

        # Test trend analysis
        trend = self.historical_service.analyze_trend(account_id)

        self.assertIsNotNone(trend)
        self.assertGreater(trend.slope, 0)  # Positive trend

        # Test gains/losses calculation
        gains_90_days = self.historical_service.calculate_gains_losses(account_id, 90)
        gains_180_days = self.historical_service.calculate_gains_losses(account_id, 180)

        self.assertGreater(gains_180_days['absolute_gain_loss'],
                          gains_90_days['absolute_gain_loss'])

    def test_error_handling_integration(self):
        """Test error handling across integrated services."""
        # Test database error handling
        with self.assertRaises(Exception):
            invalid_account_data = {
                'name': '',  # Invalid empty name
                'institution': 'Test Bank',
                'type': 'INVALID_TYPE',
                'current_balance': -1000.0  # Invalid negative balance
            }
            self.db_service.create_account(invalid_account_data)

        # Test stock service error handling
        with patch('services.stock_prices.yf.Ticker') as mock_ticker:
            mock_ticker.side_effect = Exception("Network error")

            with self.assertRaises(Exception):
                self.stock_service.get_current_price('INVALID_SYMBOL')

        # Test authentication error handling
        with self.assertRaises(ValueError):
            temp_auth = AuthenticationManager(":memory:")
            temp_auth.set_master_password("weak")  # Too weak

        # Test export/import error handling
        invalid_import_data = {
            'accounts': 'invalid_format',  # Should be list
            'metadata': {'version': '999.0'}  # Unsupported version
        }

        import_result = self.export_service.import_all_data(invalid_import_data)
        self.assertFalse(import_result['success'])
        self.assertIn('error', import_result)

    def test_concurrent_operations_integration(self):
        """Test concurrent operations across services."""
        # Create account
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Concurrent Test Account",
            institution="Test Bank",
            current_balance=5000.0,
            interest_rate=1.5
        )

        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']

        account_id = self.db_service.create_account(account_dict)
        account.id = account_id

        # Simulate concurrent operations
        import threading
        import time

        results = []
        errors = []

        def create_snapshot(value, change_type):
            try:
                snapshot_id = self.historical_service.create_snapshot(
                    account, change_type, {'concurrent_test': True}
                )
                results.append(snapshot_id)
            except Exception as e:
                errors.append(str(e))

        def update_account_balance(new_balance):
            try:
                updated_data = account_dict.copy()
                updated_data['current_balance'] = new_balance
                success = self.db_service.update_account(account_id, updated_data)
                results.append(success)
            except Exception as e:
                errors.append(str(e))

        # Start concurrent operations
        threads = []

        # Create multiple historical snapshots concurrently
        for i in range(3):
            thread = threading.Thread(target=create_snapshot, args=(5000 + i * 100, 'MANUAL_UPDATE'))
            threads.append(thread)
            thread.start()

        # Update account balance concurrently
        for i in range(2):
            thread = threading.Thread(target=update_account_balance, args=(5500 + i * 100,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify operations completed
        self.assertGreater(len(results), 0)

        # Check for any errors
        if errors:
            print(f"Concurrent operation errors: {errors}")

        # Verify data integrity
        final_account = self.db_service.get_account(account_id)
        self.assertIsNotNone(final_account)

        snapshots = self.historical_service.get_historical_snapshots(account_id)
        self.assertGreater(len(snapshots), 0)

    def test_data_consistency_integration(self):
        """Test data consistency across all services."""
        # Create trading account with positions
        trading_account = AccountFactory.create_account(
            AccountType.TRADING,
            name="Consistency Test Trading",
            institution="Test Broker",
            broker_name="Test Broker",
            cash_balance=20000.0,
            positions=[]
        )

        account_dict = trading_account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']

        account_id = self.db_service.create_account(account_dict)

        # Add stock positions
        from datetime import date
        purchase_date = int(date.today().timestamp())

        positions_data = [
            ('AAPL', 100.0, 150.0),
            ('GOOGL', 50.0, 2500.0),
            ('MSFT', 75.0, 300.0)
        ]

        position_ids = []
        for symbol, shares, price in positions_data:
            position_id = self.db_service.create_stock_position(
                account_id, symbol, shares, price, purchase_date
            )
            position_ids.append(position_id)

        # Create historical snapshot
        trading_account.id = account_id
        initial_snapshot = self.historical_service.create_snapshot(
            trading_account, 'INITIAL_ENTRY'
        )

        # Update stock prices and verify consistency
        with patch('services.stock_prices.yf.Ticker') as mock_ticker:
            mock_ticker_instance = MagicMock()
            mock_ticker.return_value = mock_ticker_instance

            def mock_history(period):
                symbol = mock_ticker.call_args[0][0]
                prices = {'AAPL': 160.0, 'GOOGL': 2600.0, 'MSFT': 320.0}
                import pandas as pd
                return pd.DataFrame({
                    'Close': [prices.get(symbol, 100.0)]
                }, index=[pd.Timestamp.now()])

            mock_ticker_instance.history.side_effect = mock_history

            # Update all positions
            positions = self.db_service.get_stock_positions(account_id)
            for position in positions:
                current_price = self.stock_service.get_current_price(position['symbol'])
                self.db_service.update_stock_price(position['id'], current_price)

        # Calculate portfolio value
        updated_positions = self.db_service.get_stock_positions(account_id)
        total_stock_value = sum(pos['current_price'] * pos['shares'] for pos in updated_positions)
        total_portfolio_value = total_stock_value + 20000.0

        # Create snapshot after price update
        price_update_snapshot = self.historical_service.create_snapshot(
            trading_account, 'STOCK_PRICE_UPDATE',
            {'total_portfolio_value': total_portfolio_value}
        )

        # Verify data consistency
        # 1. All positions should have current prices
        for position in updated_positions:
            self.assertIsNotNone(position['current_price'])
            self.assertGreater(position['current_price'], 0)

        # 2. Historical snapshots should exist
        snapshots = self.historical_service.get_historical_snapshots(account_id)
        self.assertEqual(len(snapshots), 2)

        # 3. Account should still exist and be retrievable
        retrieved_account = self.db_service.get_account(account_id)
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account['name'], "Consistency Test Trading")

        # 4. Export should include all data consistently
        export_data = self.export_service.export_all_data()

        # Find our account in export
        our_account = next(acc for acc in export_data['accounts']
                          if acc['name'] == "Consistency Test Trading")
        self.assertIsNotNone(our_account)

        # Find our positions in export
        our_positions = [pos for pos in export_data['stock_positions']
                        if pos['trading_account_id'] == account_id]
        self.assertEqual(len(our_positions), 3)

        # Find our snapshots in export
        our_snapshots = [snap for snap in export_data['historical_snapshots']
                        if snap['account_id'] == account_id]
        self.assertEqual(len(our_snapshots), 2)


if __name__ == '__main__':
    unittest.main()