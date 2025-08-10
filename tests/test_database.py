"""
Unit tests for DatabaseService with encryption operations.
Tests all CRUD operations and encryption functionality.
"""

import unittest
import tempfile
import os
import json
from datetime import datetime, date
from unittest.mock import patch

from services.database import DatabaseService
from services.encryption import EncryptionService


class TestDatabaseService(unittest.TestCase):
    """Test cases for DatabaseService class."""

    def setUp(self):
        """Set up test database and encryption service."""
        # Create temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

        # Initialize encryption service with test password
        self.encryption_service = EncryptionService()
        self.encryption_service.derive_key("test_password_123")

        # Initialize database service
        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

    def tearDown(self):
        """Clean up test database."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_database_initialization(self):
        """Test database schema initialization."""
        cursor = self.db_service.connection.cursor()

        # Check that all tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        expected_tables = ['accounts', 'historical_snapshots', 'stock_positions', 'app_settings']
        for table in expected_tables:
            self.assertIn(table, tables)

        # Check schema version is set (should be latest after migrations)
        schema_version = self.db_service.get_schema_version()
        self.assertGreaterEqual(schema_version, 1)  # Should be at least 1, likely higher due to migrations

    def test_create_account(self):
        """Test creating account with encrypted data."""
        account_data = {
            'name': 'Test CD Account',
            'institution': 'Test Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'interest_rate': 2.5,
            'maturity_date': '2025-12-31',
            'current_value': 10250.0
        }

        account_id = self.db_service.create_account(account_data)
        self.assertIsInstance(account_id, str)
        self.assertTrue(len(account_id) > 0)

        # Verify account was created
        retrieved_account = self.db_service.get_account(account_id)
        self.assertIsNotNone(retrieved_account)
        self.assertEqual(retrieved_account['name'], account_data['name'])
        self.assertEqual(retrieved_account['institution'], account_data['institution'])
        self.assertEqual(retrieved_account['type'], account_data['type'])
        self.assertEqual(retrieved_account['principal_amount'], account_data['principal_amount'])

    def test_get_account_not_found(self):
        """Test retrieving non-existent account."""
        result = self.db_service.get_account('non-existent-id')
        self.assertIsNone(result)

    def test_get_accounts_empty(self):
        """Test retrieving accounts when none exist."""
        accounts = self.db_service.get_accounts()
        self.assertEqual(len(accounts), 0)

    def test_get_accounts_with_data(self):
        """Test retrieving multiple accounts."""
        # Create test accounts
        cd_account = {
            'name': 'CD Account',
            'institution': 'Bank A',
            'type': 'CD',
            'principal_amount': 5000.0,
            'interest_rate': 2.0,
            'current_value': 5100.0
        }

        savings_account = {
            'name': 'Savings Account',
            'institution': 'Bank B',
            'type': 'SAVINGS',
            'current_balance': 15000.0,
            'interest_rate': 1.5
        }

        cd_id = self.db_service.create_account(cd_account)
        savings_id = self.db_service.create_account(savings_account)

        # Test get all accounts
        all_accounts = self.db_service.get_accounts()
        self.assertEqual(len(all_accounts), 2)

        # Test get accounts by type
        cd_accounts = self.db_service.get_accounts('CD')
        self.assertEqual(len(cd_accounts), 1)
        self.assertEqual(cd_accounts[0]['type'], 'CD')

        savings_accounts = self.db_service.get_accounts('SAVINGS')
        self.assertEqual(len(savings_accounts), 1)
        self.assertEqual(savings_accounts[0]['type'], 'SAVINGS')

    def test_update_account(self):
        """Test updating account data."""
        # Create account
        account_data = {
            'name': 'Original Name',
            'institution': 'Original Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'current_value': 10000.0
        }

        account_id = self.db_service.create_account(account_data)

        # Update account
        updated_data = {
            'name': 'Updated Name',
            'institution': 'Updated Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'current_value': 10500.0
        }

        result = self.db_service.update_account(account_id, updated_data)
        self.assertTrue(result)

        # Verify update
        retrieved_account = self.db_service.get_account(account_id)
        self.assertEqual(retrieved_account['name'], 'Updated Name')
        self.assertEqual(retrieved_account['institution'], 'Updated Bank')
        self.assertEqual(retrieved_account['current_value'], 10500.0)

    def test_update_account_not_found(self):
        """Test updating non-existent account."""
        result = self.db_service.update_account('non-existent-id', {})
        self.assertFalse(result)

    def test_delete_account(self):
        """Test deleting account."""
        # Create account
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0
        }

        account_id = self.db_service.create_account(account_data)

        # Verify account exists
        self.assertIsNotNone(self.db_service.get_account(account_id))

        # Delete account
        result = self.db_service.delete_account(account_id)
        self.assertTrue(result)

        # Verify account is deleted
        self.assertIsNone(self.db_service.get_account(account_id))

    def test_delete_account_not_found(self):
        """Test deleting non-existent account."""
        result = self.db_service.delete_account('non-existent-id')
        self.assertFalse(result)

    def test_create_historical_snapshot(self):
        """Test creating historical snapshot."""
        # Create account first
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0
        }
        account_id = self.db_service.create_account(account_data)

        # Create snapshot
        snapshot_id = self.db_service.create_historical_snapshot(
            account_id, 5250.0, 'MANUAL_UPDATE', {'note': 'Monthly update'}
        )

        self.assertIsInstance(snapshot_id, str)
        self.assertTrue(len(snapshot_id) > 0)

        # Verify snapshot was created
        snapshots = self.db_service.get_historical_snapshots(account_id)
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]['value'], 5250.0)
        self.assertEqual(snapshots[0]['change_type'], 'MANUAL_UPDATE')
        self.assertEqual(snapshots[0]['metadata']['note'], 'Monthly update')

    def test_get_historical_snapshots_with_filters(self):
        """Test retrieving historical snapshots with timestamp filters."""
        # Create account
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0
        }
        account_id = self.db_service.create_account(account_data)

        # Create multiple snapshots
        now = int(datetime.now().timestamp())
        one_day_ago = now - 86400
        two_days_ago = now - 172800

        # Mock timestamps for testing
        with patch('services.database.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = two_days_ago
            self.db_service.create_historical_snapshot(account_id, 5000.0, 'INITIAL')

            mock_datetime.now.return_value.timestamp.return_value = one_day_ago
            self.db_service.create_historical_snapshot(account_id, 5100.0, 'MANUAL_UPDATE')

            mock_datetime.now.return_value.timestamp.return_value = now
            self.db_service.create_historical_snapshot(account_id, 5200.0, 'MANUAL_UPDATE')

        # Test getting all snapshots
        all_snapshots = self.db_service.get_historical_snapshots(account_id)
        self.assertEqual(len(all_snapshots), 3)

        # Test with start timestamp filter
        recent_snapshots = self.db_service.get_historical_snapshots(
            account_id, start_timestamp=one_day_ago
        )
        self.assertEqual(len(recent_snapshots), 2)

        # Test with end timestamp filter
        old_snapshots = self.db_service.get_historical_snapshots(
            account_id, end_timestamp=one_day_ago
        )
        self.assertEqual(len(old_snapshots), 2)

    def test_create_stock_position(self):
        """Test creating stock position."""
        # Create trading account first
        account_data = {
            'name': 'Trading Account',
            'institution': 'Broker',
            'type': 'TRADING',
            'cash_balance': 10000.0
        }
        account_id = self.db_service.create_account(account_data)

        # Create stock position
        purchase_date = int(datetime.now().timestamp())
        position_id = self.db_service.create_stock_position(
            account_id, 'AAPL', 100.0, 150.0, purchase_date
        )

        self.assertIsInstance(position_id, str)
        self.assertTrue(len(position_id) > 0)

        # Verify position was created
        positions = self.db_service.get_stock_positions(account_id)
        self.assertEqual(len(positions), 1)
        self.assertEqual(positions[0]['symbol'], 'AAPL')
        self.assertEqual(positions[0]['shares'], 100.0)
        self.assertEqual(positions[0]['purchase_price'], 150.0)

    def test_update_stock_price(self):
        """Test updating stock position price."""
        # Create trading account and position
        account_data = {
            'name': 'Trading Account',
            'institution': 'Broker',
            'type': 'TRADING',
            'cash_balance': 10000.0
        }
        account_id = self.db_service.create_account(account_data)

        purchase_date = int(datetime.now().timestamp())
        position_id = self.db_service.create_stock_position(
            account_id, 'AAPL', 100.0, 150.0, purchase_date
        )

        # Update stock price
        result = self.db_service.update_stock_price(position_id, 155.0)
        self.assertTrue(result)

        # Verify price was updated
        positions = self.db_service.get_stock_positions(account_id)
        self.assertEqual(positions[0]['current_price'], 155.0)
        self.assertIsNotNone(positions[0]['last_price_update'])

    def test_update_stock_price_not_found(self):
        """Test updating price for non-existent position."""
        result = self.db_service.update_stock_price('non-existent-id', 100.0)
        self.assertFalse(result)

    def test_delete_stock_position(self):
        """Test deleting stock position."""
        # Create trading account and position
        account_data = {
            'name': 'Trading Account',
            'institution': 'Broker',
            'type': 'TRADING',
            'cash_balance': 10000.0
        }
        account_id = self.db_service.create_account(account_data)

        purchase_date = int(datetime.now().timestamp())
        position_id = self.db_service.create_stock_position(
            account_id, 'AAPL', 100.0, 150.0, purchase_date
        )

        # Verify position exists
        positions = self.db_service.get_stock_positions(account_id)
        self.assertEqual(len(positions), 1)

        # Delete position
        result = self.db_service.delete_stock_position(position_id)
        self.assertTrue(result)

        # Verify position is deleted
        positions = self.db_service.get_stock_positions(account_id)
        self.assertEqual(len(positions), 0)

    def test_delete_stock_position_not_found(self):
        """Test deleting non-existent position."""
        result = self.db_service.delete_stock_position('non-existent-id')
        self.assertFalse(result)

    def test_app_settings(self):
        """Test application settings operations."""
        # Set setting
        self.db_service.set_setting('test_key', 'test_value')

        # Get setting
        value = self.db_service.get_setting('test_key')
        self.assertEqual(value, 'test_value')

        # Update setting
        self.db_service.set_setting('test_key', 'updated_value')
        value = self.db_service.get_setting('test_key')
        self.assertEqual(value, 'updated_value')

    def test_get_setting_not_found(self):
        """Test getting non-existent setting."""
        with self.assertRaises(KeyError):
            self.db_service.get_setting('non_existent_key')

    def test_encryption_integration(self):
        """Test that data is properly encrypted in database."""
        # Create account with sensitive data
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'interest_rate': 2.5,
            'current_value': 10250.0
        }

        account_id = self.db_service.create_account(account_data)

        # Check that sensitive data is encrypted in database
        cursor = self.db_service.connection.cursor()
        cursor.execute('SELECT encrypted_data FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()

        # Encrypted data should not contain plain text
        encrypted_data = row['encrypted_data']
        self.assertNotIn(b'10000.0', encrypted_data)
        self.assertNotIn(b'2.5', encrypted_data)
        self.assertNotIn(b'10250.0', encrypted_data)

        # But decrypted data should match
        retrieved_account = self.db_service.get_account(account_id)
        self.assertEqual(retrieved_account['principal_amount'], 10000.0)
        self.assertEqual(retrieved_account['interest_rate'], 2.5)
        self.assertEqual(retrieved_account['current_value'], 10250.0)

    def test_database_exists(self):
        """Test database existence check."""
        # Current database should exist
        self.assertTrue(self.db_service.database_exists())

        # Non-existent database should not exist
        non_existent_db = DatabaseService('/non/existent/path.db', self.encryption_service)
        self.assertFalse(non_existent_db.database_exists())

    def test_cascading_deletes(self):
        """Test that related data is deleted when account is deleted."""
        # Create trading account
        account_data = {
            'name': 'Trading Account',
            'institution': 'Broker',
            'type': 'TRADING',
            'cash_balance': 10000.0
        }
        account_id = self.db_service.create_account(account_data)

        # Create related data
        purchase_date = int(datetime.now().timestamp())
        position_id = self.db_service.create_stock_position(
            account_id, 'AAPL', 100.0, 150.0, purchase_date
        )
        snapshot_id = self.db_service.create_historical_snapshot(
            account_id, 25000.0, 'MANUAL_UPDATE'
        )

        # Verify related data exists
        positions = self.db_service.get_stock_positions(account_id)
        snapshots = self.db_service.get_historical_snapshots(account_id)
        self.assertEqual(len(positions), 1)
        self.assertEqual(len(snapshots), 1)

        # Delete account
        self.db_service.delete_account(account_id)

        # Verify related data is also deleted
        positions = self.db_service.get_stock_positions(account_id)
        snapshots = self.db_service.get_historical_snapshots(account_id)
        self.assertEqual(len(positions), 0)
        self.assertEqual(len(snapshots), 0)


if __name__ == '__main__':
    unittest.main()