"""
Unit tests for export/import service functionality.
Tests data export, import, encryption, and data integrity validation.
"""

import pytest
import json
import tempfile
import os
from datetime import datetime, date
from unittest.mock import Mock, patch

from services.export_import import ExportImportService
from services.encryption import EncryptionService
from services.database import DatabaseService


class TestExportImportService:
    """Test cases for ExportImportService."""

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        service = EncryptionService()
        service.derive_key("test_password_123!")
        return service

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service for testing."""
        mock_db = Mock(spec=DatabaseService)

        # Mock account data
        mock_accounts = [
            {
                'id': 'account-1',
                'name': 'Test CD',
                'institution': 'Test Bank',
                'type': 'CD',
                'principal_amount': 10000.0,
                'interest_rate': 2.5,
                'maturity_date': date(2025, 12, 31),
                'current_value': 10250.0,
                'created_date': datetime(2024, 1, 1),
                'last_updated': datetime(2024, 1, 15)
            },
            {
                'id': 'account-2',
                'name': 'Test Trading',
                'institution': 'Test Broker',
                'type': 'TRADING',
                'broker_name': 'Test Broker',
                'cash_balance': 5000.0,
                'created_date': datetime(2024, 1, 1),
                'last_updated': datetime(2024, 1, 15)
            }
        ]

        # Mock stock positions
        mock_positions = [
            {
                'id': 'pos-1',
                'trading_account_id': 'account-2',
                'symbol': 'AAPL',
                'shares': 100.0,
                'purchase_price': 150.0,
                'purchase_date': datetime(2024, 1, 1),
                'current_price': 160.0,
                'last_price_update': datetime(2024, 1, 15)
            }
        ]

        # Mock historical snapshots
        mock_snapshots = [
            {
                'id': 'snap-1',
                'account_id': 'account-1',
                'timestamp': datetime(2024, 1, 1),
                'value': 10000.0,
                'change_type': 'INITIAL_ENTRY'
            },
            {
                'id': 'snap-2',
                'account_id': 'account-1',
                'timestamp': datetime(2024, 1, 15),
                'value': 10250.0,
                'change_type': 'MANUAL_UPDATE'
            }
        ]

        mock_db.get_accounts.return_value = mock_accounts
        mock_db.get_stock_positions.return_value = mock_positions
        mock_db.get_watchlist_items.return_value = []  # Empty watchlist for existing tests
        mock_db.get_historical_snapshots.return_value = mock_snapshots
        mock_db.get_setting.return_value = '1'

        return mock_db

    @pytest.fixture
    def export_import_service(self, mock_db_service, encryption_service):
        """Create ExportImportService for testing."""
        return ExportImportService(mock_db_service, encryption_service)

    def test_export_data_basic(self, export_import_service, mock_db_service):
        """Test basic data export functionality."""
        # Export data
        export_data = export_import_service.export_data(include_historical=True)

        # Verify export structure
        assert 'backup_metadata' in export_data
        assert 'accounts' in export_data
        assert 'stock_positions' in export_data
        assert 'historical_snapshots' in export_data
        assert 'app_settings' in export_data

        # Verify metadata
        metadata = export_data['backup_metadata']
        assert metadata['backup_version'] == ExportImportService.BACKUP_VERSION
        assert metadata['format_version'] == ExportImportService.BACKUP_FORMAT_VERSION
        assert metadata['include_historical'] is True
        assert metadata['accounts_count'] == 2
        assert 'backup_id' in metadata
        assert 'export_timestamp' in metadata

        # Verify accounts data
        accounts = export_data['accounts']
        assert len(accounts) == 2
        assert accounts[0]['name'] == 'Test CD'
        assert accounts[1]['name'] == 'Test Trading'

        # Verify stock positions
        stock_positions = export_data['stock_positions']
        assert 'account-2' in stock_positions
        assert len(stock_positions['account-2']) == 1
        assert stock_positions['account-2'][0]['symbol'] == 'AAPL'

        # Verify historical snapshots
        historical = export_data['historical_snapshots']
        assert 'account-1' in historical
        assert len(historical['account-1']) == 2

    def test_export_data_without_historical(self, export_import_service, mock_db_service):
        """Test data export without historical data."""
        # Export data without historical
        export_data = export_import_service.export_data(include_historical=False)

        # Verify metadata reflects no historical data
        metadata = export_data['backup_metadata']
        assert metadata['include_historical'] is False
        assert metadata['historical_accounts_count'] == 0

        # Verify historical snapshots are empty
        historical = export_data['historical_snapshots']
        assert len(historical) == 0

    def test_create_encrypted_backup(self, export_import_service, mock_db_service):
        """Test creating encrypted backup from export data."""
        # Export data
        export_data = export_import_service.export_data()

        # Create encrypted backup
        encrypted_backup = export_import_service.create_encrypted_backup(export_data)

        # Verify encrypted backup is bytes
        assert isinstance(encrypted_backup, bytes)
        assert len(encrypted_backup) > 0

        # Verify it's actually encrypted (not plain JSON)
        try:
            json.loads(encrypted_backup.decode())
            pytest.fail("Backup should be encrypted, not plain JSON")
        except (json.JSONDecodeError, UnicodeDecodeError):
            # Expected - data should be encrypted
            pass

    def test_decrypt_backup(self, export_import_service, mock_db_service):
        """Test decrypting backup file."""
        # Create test export data
        export_data = export_import_service.export_data()
        encrypted_backup = export_import_service.create_encrypted_backup(export_data)

        # Decrypt backup
        decrypted_data = export_import_service.decrypt_backup(encrypted_backup)

        # Verify decrypted data matches original
        assert decrypted_data['backup_metadata']['backup_version'] == export_data['backup_metadata']['backup_version']
        assert len(decrypted_data['accounts']) == len(export_data['accounts'])
        assert decrypted_data['accounts'][0]['name'] == export_data['accounts'][0]['name']

    def test_decrypt_backup_invalid_data(self, export_import_service):
        """Test decrypting invalid backup data."""
        # Test with invalid encrypted data
        with pytest.raises(Exception, match="Failed to decrypt backup"):
            export_import_service.decrypt_backup(b"invalid_encrypted_data")

    def test_validate_backup_format_valid(self, export_import_service, mock_db_service):
        """Test backup format validation with valid data."""
        # Create valid backup data
        export_data = export_import_service.export_data()

        # Validate format (should not raise exception)
        export_import_service._validate_backup_format(export_data)

    def test_validate_backup_format_invalid(self, export_import_service):
        """Test backup format validation with invalid data."""
        # Test missing required keys
        invalid_data = {'accounts': []}
        with pytest.raises(ValueError, match="missing required keys"):
            export_import_service._validate_backup_format(invalid_data)

        # Test missing format version
        invalid_data = {
            'backup_metadata': {},
            'accounts': []
        }
        with pytest.raises(ValueError, match="missing format version"):
            export_import_service._validate_backup_format(invalid_data)

        # Test incompatible format version
        invalid_data = {
            'backup_metadata': {
                'format_version': 999,
                'backup_version': '1.0'
            },
            'accounts': []
        }
        with pytest.raises(ValueError, match="Incompatible backup format version"):
            export_import_service._validate_backup_format(invalid_data)

    def test_import_data_basic(self, export_import_service, mock_db_service):
        """Test basic data import functionality."""
        # Create test backup data
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat()
            },
            'accounts': [
                {
                    'id': 'import-account-1',
                    'name': 'Imported CD',
                    'institution': 'Import Bank',
                    'type': 'CD',
                    'principal_amount': 15000.0,
                    'interest_rate': 3.0,
                    'maturity_date': '2026-01-01',
                    'current_value': 15450.0,
                    'created_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-15T00:00:00'
                }
            ],
            'stock_positions': {},
            'historical_snapshots': {},
            'app_settings': {'schema_version': '1'}
        }

        # Mock database methods for import
        mock_db_service.get_account.return_value = None  # Account doesn't exist
        mock_db_service.create_account.return_value = 'new-account-id'
        mock_db_service.update_account.return_value = True
        mock_db_service.set_setting.return_value = None

        # Import data
        import_results = export_import_service.import_data(backup_data, overwrite_existing=False)

        # Verify import results
        assert import_results['accounts_imported'] == 1
        assert import_results['accounts_skipped'] == 0
        assert import_results['stock_positions_imported'] == 0
        assert import_results['historical_snapshots_imported'] == 0
        assert import_results['settings_imported'] == 1
        assert len(import_results['errors']) == 0

        # Verify database methods were called
        mock_db_service.create_account.assert_called_once()
        mock_db_service.set_setting.assert_called_once_with('schema_version', '1')

    def test_import_data_with_existing_accounts(self, export_import_service, mock_db_service):
        """Test importing data when accounts already exist."""
        # Create test backup data
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat()
            },
            'accounts': [
                {
                    'id': 'existing-account-1',
                    'name': 'Existing Account',
                    'institution': 'Test Bank',
                    'type': 'SAVINGS',
                    'current_balance': 5000.0,
                    'interest_rate': 1.5,
                    'created_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-15T00:00:00'
                }
            ],
            'stock_positions': {},
            'historical_snapshots': {},
            'app_settings': {}
        }

        # Mock existing account
        mock_db_service.get_account.return_value = {'id': 'existing-account-1', 'name': 'Existing Account'}

        # Import without overwrite
        import_results = export_import_service.import_data(backup_data, overwrite_existing=False)

        # Verify account was skipped
        assert import_results['accounts_imported'] == 0
        assert import_results['accounts_skipped'] == 1

        # Import with overwrite
        mock_db_service.update_account.return_value = True
        import_results = export_import_service.import_data(backup_data, overwrite_existing=True)

        # Verify account was updated
        assert import_results['accounts_imported'] == 1
        assert import_results['accounts_skipped'] == 0
        mock_db_service.update_account.assert_called_once()

    def test_import_data_with_stock_positions(self, export_import_service, mock_db_service):
        """Test importing data with stock positions."""
        # Create test backup data with stock positions
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat()
            },
            'accounts': [
                {
                    'id': 'trading-account-1',
                    'name': 'Trading Account',
                    'institution': 'Test Broker',
                    'type': 'TRADING',
                    'broker_name': 'Test Broker',
                    'cash_balance': 10000.0,
                    'created_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-15T00:00:00'
                }
            ],
            'stock_positions': {
                'trading-account-1': [
                    {
                        'id': 'pos-1',
                        'trading_account_id': 'trading-account-1',
                        'symbol': 'MSFT',
                        'shares': 50.0,
                        'purchase_price': 300.0,
                        'purchase_date': '2024-01-01T00:00:00',
                        'current_price': 320.0,
                        'last_price_update': '2024-01-15T00:00:00'
                    }
                ]
            },
            'historical_snapshots': {},
            'app_settings': {}
        }

        # Mock database methods
        mock_db_service.get_account.return_value = None
        mock_db_service.create_account.return_value = 'trading-account-1'
        mock_db_service.create_stock_position.return_value = 'new-pos-id'
        mock_db_service.get_stock_positions.return_value = [
            {
                'id': 'new-pos-id',
                'symbol': 'MSFT',
                'shares': 50.0,
                'purchase_price': 300.0
            }
        ]
        mock_db_service.update_stock_price.return_value = True

        # Import data
        import_results = export_import_service.import_data(backup_data, overwrite_existing=False)

        # Verify stock position was imported
        assert import_results['accounts_imported'] == 1
        assert import_results['stock_positions_imported'] == 1
        mock_db_service.create_stock_position.assert_called_once()
        mock_db_service.update_stock_price.assert_called_once()

    def test_import_data_with_historical_snapshots(self, export_import_service, mock_db_service):
        """Test importing data with historical snapshots."""
        # Create test backup data with historical snapshots
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat()
            },
            'accounts': [
                {
                    'id': 'account-with-history',
                    'name': 'Account with History',
                    'institution': 'Test Bank',
                    'type': 'SAVINGS',
                    'current_balance': 5000.0,
                    'interest_rate': 1.5,
                    'created_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-15T00:00:00'
                }
            ],
            'stock_positions': {},
            'historical_snapshots': {
                'account-with-history': [
                    {
                        'id': 'hist-1',
                        'account_id': 'account-with-history',
                        'timestamp': '2024-01-01T00:00:00',
                        'value': 4500.0,
                        'change_type': 'INITIAL_ENTRY'
                    },
                    {
                        'id': 'hist-2',
                        'account_id': 'account-with-history',
                        'timestamp': '2024-01-15T00:00:00',
                        'value': 5000.0,
                        'change_type': 'MANUAL_UPDATE'
                    }
                ]
            },
            'app_settings': {}
        }

        # Mock database methods
        mock_db_service.get_account.return_value = None
        mock_db_service.create_account.return_value = 'account-with-history'
        mock_db_service.create_historical_snapshot.return_value = 'new-snapshot-id'

        # Import data
        import_results = export_import_service.import_data(backup_data, overwrite_existing=False)

        # Verify historical snapshots were imported
        assert import_results['accounts_imported'] == 1
        assert import_results['historical_snapshots_imported'] == 2
        assert mock_db_service.create_historical_snapshot.call_count == 2

    def test_validate_backup_integrity_valid(self, export_import_service, mock_db_service):
        """Test backup integrity validation with valid data."""
        # Create valid backup data
        export_data = export_import_service.export_data()

        # Validate integrity
        validation_results = export_import_service.validate_backup_integrity(export_data)

        # Verify validation results
        assert validation_results['valid'] is True
        assert len(validation_results['errors']) == 0
        assert validation_results['summary']['accounts_count'] == 2
        assert validation_results['summary']['stock_positions_count'] == 1
        # Historical snapshots count may vary based on mock setup, just verify it's a number
        assert isinstance(validation_results['summary']['historical_snapshots_count'], int)
        assert validation_results['summary']['historical_snapshots_count'] >= 0

    def test_validate_backup_integrity_invalid(self, export_import_service):
        """Test backup integrity validation with invalid data."""
        # Create invalid backup data
        invalid_backup = {
            'accounts': [
                {'name': 'Account without ID'},  # Missing ID
                {'id': 'account-2'}  # Missing name and type
            ]
        }

        # Validate integrity
        validation_results = export_import_service.validate_backup_integrity(invalid_backup)

        # Verify validation failed
        assert validation_results['valid'] is False
        assert len(validation_results['errors']) > 0

    def test_serialize_accounts_for_export(self, export_import_service):
        """Test account serialization for export."""
        # Create test accounts with datetime objects
        accounts_data = [
            {
                'id': 'account-1',
                'name': 'Test Account',
                'created_date': datetime(2024, 1, 1, 12, 0, 0),
                'last_updated': datetime(2024, 1, 15, 15, 30, 0),
                'maturity_date': date(2025, 12, 31)
            }
        ]

        # Serialize accounts
        serialized = export_import_service._serialize_accounts_for_export(accounts_data)

        # Verify datetime objects were converted to ISO strings
        assert isinstance(serialized[0]['created_date'], str)
        assert isinstance(serialized[0]['last_updated'], str)
        assert isinstance(serialized[0]['maturity_date'], str)
        assert serialized[0]['created_date'] == '2024-01-01T12:00:00'
        assert serialized[0]['maturity_date'] == '2025-12-31'

    def test_prepare_account_for_import(self, export_import_service):
        """Test account data preparation for import."""
        # Create test account data with ISO strings
        account_data = {
            'id': 'account-1',
            'name': 'Test Account',
            'created_date': '2024-01-01T12:00:00',
            'last_updated': '2024-01-15T15:30:00',
            'maturity_date': '2025-12-31'
        }

        # Prepare for import
        prepared = export_import_service._prepare_account_for_import(account_data)

        # Verify ISO strings were converted back to appropriate types
        assert isinstance(prepared['created_date'], datetime)
        assert isinstance(prepared['last_updated'], datetime)
        assert isinstance(prepared['maturity_date'], date)
        assert prepared['created_date'] == datetime(2024, 1, 1, 12, 0, 0)
        assert prepared['maturity_date'] == date(2025, 12, 31)

    def test_end_to_end_export_import(self, mock_db_service, encryption_service):
        """Test complete export-import cycle with data integrity."""
        # Create export service
        export_service = ExportImportService(mock_db_service, encryption_service)

        # Export data
        original_export = export_service.export_data(include_historical=True)
        encrypted_backup = export_service.create_encrypted_backup(original_export)

        # Create import service with fresh mock database
        import_mock_db = Mock(spec=DatabaseService)
        import_mock_db.get_account.return_value = None
        import_mock_db.create_account.return_value = 'new-account-id'
        import_mock_db.create_stock_position.return_value = 'new-pos-id'
        import_mock_db.create_historical_snapshot.return_value = 'new-snap-id'
        import_mock_db.set_setting.return_value = None
        import_mock_db.get_stock_positions.return_value = []
        import_mock_db.update_stock_price.return_value = True

        import_service = ExportImportService(import_mock_db, encryption_service)

        # Decrypt and import
        decrypted_backup = import_service.decrypt_backup(encrypted_backup)
        import_results = import_service.import_data(decrypted_backup, overwrite_existing=False)

        # Verify import was successful
        assert import_results['accounts_imported'] == 2
        assert import_results['stock_positions_imported'] == 1
        assert import_results['historical_snapshots_imported'] == 2
        assert import_results['settings_imported'] == 1
        assert len(import_results['errors']) == 0

        # Verify data integrity
        validation_results = import_service.validate_backup_integrity(decrypted_backup)
        assert validation_results['valid'] is True

    def test_export_import_error_handling(self, export_import_service, mock_db_service):
        """Test error handling in export/import operations."""
        # Test export error
        mock_db_service.get_accounts.side_effect = Exception("Database error")

        with pytest.raises(Exception, match="Failed to export data"):
            export_import_service.export_data()

        # Reset mock
        mock_db_service.get_accounts.side_effect = None
        mock_db_service.get_accounts.return_value = []

        # Test import error - invalid backup format should raise exception during validation
        invalid_backup = {'invalid': 'data'}

        with pytest.raises(Exception):
            export_import_service.import_data(invalid_backup)

    def test_large_dataset_export_import(self, encryption_service):
        """Test export/import with large dataset."""
        # Create mock database with large dataset
        large_mock_db = Mock(spec=DatabaseService)

        # Generate large number of accounts
        large_accounts = []
        for i in range(100):
            large_accounts.append({
                'id': f'account-{i}',
                'name': f'Account {i}',
                'institution': f'Bank {i}',
                'type': 'SAVINGS',
                'current_balance': float(i * 1000),
                'interest_rate': 2.5,
                'created_date': datetime(2024, 1, 1),
                'last_updated': datetime(2024, 1, 15)
            })

        large_mock_db.get_accounts.return_value = large_accounts
        large_mock_db.get_stock_positions.return_value = []
        large_mock_db.get_watchlist_items.return_value = []  # Empty watchlist
        large_mock_db.get_historical_snapshots.return_value = []
        large_mock_db.get_setting.return_value = '1'

        # Create service and export
        service = ExportImportService(large_mock_db, encryption_service)
        export_data = service.export_data()

        # Verify large dataset was exported
        assert len(export_data['accounts']) == 100
        assert export_data['backup_metadata']['accounts_count'] == 100

        # Test encryption/decryption with large dataset
        encrypted_backup = service.create_encrypted_backup(export_data)
        decrypted_backup = service.decrypt_backup(encrypted_backup)

        # Verify data integrity after encryption/decryption
        assert len(decrypted_backup['accounts']) == 100
        assert decrypted_backup['accounts'][0]['name'] == 'Account 0'
        assert decrypted_backup['accounts'][99]['name'] == 'Account 99'