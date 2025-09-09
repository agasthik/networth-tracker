"""
Unit tests for HSA and watchlist export/import functionality.
Tests the extended export/import service with HSA accounts and watchlist data.
"""

import pytest
import json
from datetime import datetime, date
from unittest.mock import Mock, patch

from services.export_import import ExportImportService
from services.encryption import EncryptionService
from services.database import DatabaseService


class TestExportImportHSAWatchlist:
    """Test cases for HSA and watchlist export/import functionality."""

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        service = EncryptionService()
        service.derive_key("test_password_123!")
        return service

    @pytest.fixture
    def mock_db_service_with_hsa_watchlist(self):
        """Create mock database service with HSA accounts and watchlist data."""
        mock_db = Mock(spec=DatabaseService)

        # Mock account data including HSA accounts
        mock_accounts = [
            {
                'id': 'hsa-account-1',
                'name': 'Test HSA',
                'institution': 'Health Bank',
                'type': 'HSA',
                'current_balance': 5000.0,
                'annual_contribution_limit': 4300.0,
                'current_year_contributions': 2000.0,
                'employer_contributions': 1000.0,
                'investment_balance': 3000.0,
                'cash_balance': 2000.0,
                'created_date': datetime(2024, 1, 1),
                'last_updated': datetime(2024, 1, 15)
            },
            {
                'id': 'cd-account-1',
                'name': 'Test CD',
                'institution': 'Test Bank',
                'type': 'CD',
                'principal_amount': 10000.0,
                'interest_rate': 2.5,
                'maturity_date': date(2025, 12, 31),
                'current_value': 10250.0,
                'created_date': datetime(2024, 1, 1),
                'last_updated': datetime(2024, 1, 15)
            }
        ]

        # Mock watchlist data
        mock_watchlist = [
            {
                'id': 'watch-1',
                'symbol': 'AAPL',
                'notes': 'Apple Inc. - Tech stock',
                'added_date': datetime(2024, 1, 1),
                'current_price': 180.50,
                'last_price_update': datetime(2024, 1, 15),
                'daily_change': 2.50,
                'daily_change_percent': 1.41,
                'is_demo': False
            },
            {
                'id': 'watch-2',
                'symbol': 'GOOGL',
                'notes': 'Alphabet Inc. - Search giant',
                'added_date': datetime(2024, 1, 2),
                'current_price': 2800.00,
                'last_price_update': datetime(2024, 1, 15),
                'daily_change': -15.00,
                'daily_change_percent': -0.53,
                'is_demo': True
            }
        ]

        # Mock historical snapshots
        mock_snapshots = [
            {
                'id': 'snap-1',
                'account_id': 'hsa-account-1',
                'timestamp': datetime(2024, 1, 1),
                'value': 4500.0,
                'change_type': 'INITIAL_ENTRY'
            },
            {
                'id': 'snap-2',
                'account_id': 'hsa-account-1',
                'timestamp': datetime(2024, 1, 15),
                'value': 5000.0,
                'change_type': 'CONTRIBUTION'
            }
        ]

        mock_db.get_accounts.return_value = mock_accounts
        mock_db.get_stock_positions.return_value = []  # No stock positions for this test
        mock_db.get_watchlist_items.return_value = mock_watchlist
        mock_db.get_historical_snapshots.return_value = mock_snapshots
        mock_db.get_setting.return_value = '1'

        return mock_db

    @pytest.fixture
    def export_import_service_hsa_watchlist(self, mock_db_service_with_hsa_watchlist, encryption_service):
        """Create ExportImportService with HSA and watchlist data for testing."""
        return ExportImportService(mock_db_service_with_hsa_watchlist, encryption_service)

    def test_export_data_with_hsa_accounts(self, export_import_service_hsa_watchlist, mock_db_service_with_hsa_watchlist):
        """Test exporting data that includes HSA accounts."""
        # Export data
        export_data = export_import_service_hsa_watchlist.export_data(include_historical=True)

        # Verify export structure includes HSA accounts
        assert 'backup_metadata' in export_data
        assert 'accounts' in export_data
        assert 'watchlist' in export_data

        # Verify metadata includes watchlist count
        metadata = export_data['backup_metadata']
        assert metadata['accounts_count'] == 2
        assert metadata['watchlist_count'] == 2

        # Verify HSA account is included
        accounts = export_data['accounts']
        hsa_account = next((acc for acc in accounts if acc['type'] == 'HSA'), None)
        assert hsa_account is not None
        assert hsa_account['name'] == 'Test HSA'
        assert hsa_account['current_balance'] == 5000.0
        assert hsa_account['annual_contribution_limit'] == 4300.0
        assert hsa_account['current_year_contributions'] == 2000.0
        assert hsa_account['employer_contributions'] == 1000.0
        assert hsa_account['investment_balance'] == 3000.0
        assert hsa_account['cash_balance'] == 2000.0

        # Verify datetime fields are serialized as ISO strings
        assert isinstance(hsa_account['created_date'], str)
        assert isinstance(hsa_account['last_updated'], str)

    def test_export_data_with_watchlist(self, export_import_service_hsa_watchlist, mock_db_service_with_hsa_watchlist):
        """Test exporting data that includes watchlist items."""
        # Export data
        export_data = export_import_service_hsa_watchlist.export_data()

        # Verify watchlist data is included
        watchlist = export_data['watchlist']
        assert len(watchlist) == 2

        # Verify first watchlist item
        aapl_item = next((item for item in watchlist if item['symbol'] == 'AAPL'), None)
        assert aapl_item is not None
        assert aapl_item['notes'] == 'Apple Inc. - Tech stock'
        assert aapl_item['current_price'] == 180.50
        assert aapl_item['daily_change'] == 2.50
        assert aapl_item['daily_change_percent'] == 1.41
        assert aapl_item['is_demo'] is False

        # Verify datetime fields are serialized as ISO strings
        assert isinstance(aapl_item['added_date'], str)
        assert isinstance(aapl_item['last_price_update'], str)

        # Verify second watchlist item (demo)
        googl_item = next((item for item in watchlist if item['symbol'] == 'GOOGL'), None)
        assert googl_item is not None
        assert googl_item['is_demo'] is True

    def test_serialize_watchlist_for_export(self, export_import_service_hsa_watchlist):
        """Test watchlist serialization for export."""
        # Create test watchlist data with datetime objects
        watchlist_data = [
            {
                'id': 'watch-test',
                'symbol': 'TSLA',
                'notes': 'Tesla Inc.',
                'added_date': datetime(2024, 1, 1, 12, 0, 0),
                'last_price_update': datetime(2024, 1, 15, 15, 30, 0),
                'current_price': 250.00,
                'daily_change': 5.00,
                'daily_change_percent': 2.04
            }
        ]

        # Serialize watchlist
        serialized = export_import_service_hsa_watchlist._serialize_watchlist_for_export(watchlist_data)

        # Verify datetime objects were converted to ISO strings
        assert isinstance(serialized[0]['added_date'], str)
        assert isinstance(serialized[0]['last_price_update'], str)
        assert serialized[0]['added_date'] == '2024-01-01T12:00:00'
        assert serialized[0]['last_price_update'] == '2024-01-15T15:30:00'

        # Verify other fields remain unchanged
        assert serialized[0]['symbol'] == 'TSLA'
        assert serialized[0]['current_price'] == 250.00

    def test_import_data_with_hsa_accounts(self, encryption_service):
        """Test importing data that includes HSA accounts."""
        # Create test backup data with HSA account
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat(),
                'accounts_count': 1,
                'watchlist_count': 0
            },
            'accounts': [
                {
                    'id': 'import-hsa-1',
                    'name': 'Imported HSA',
                    'institution': 'Health Savings Bank',
                    'type': 'HSA',
                    'current_balance': 7500.0,
                    'annual_contribution_limit': 4300.0,
                    'current_year_contributions': 3000.0,
                    'employer_contributions': 1500.0,
                    'investment_balance': 5000.0,
                    'cash_balance': 2500.0,
                    'created_date': '2024-01-01T00:00:00',
                    'last_updated': '2024-01-15T00:00:00'
                }
            ],
            'stock_positions': {},
            'watchlist': [],
            'historical_snapshots': {},
            'app_settings': {'schema_version': '1'}
        }

        # Create mock database for import
        import_mock_db = Mock(spec=DatabaseService)
        import_mock_db.get_account.return_value = None  # Account doesn't exist
        import_mock_db.create_account.return_value = 'new-hsa-id'
        import_mock_db.get_watchlist_item.return_value = None
        import_mock_db.set_setting.return_value = None

        # Create import service
        import_service = ExportImportService(import_mock_db, encryption_service)

        # Import data
        import_results = import_service.import_data(backup_data, overwrite_existing=False)

        # Verify HSA account was imported
        assert import_results['accounts_imported'] == 1
        assert import_results['accounts_skipped'] == 0
        assert import_results['watchlist_imported'] == 0
        assert len(import_results['errors']) == 0

        # Verify database methods were called correctly
        import_mock_db.create_account.assert_called_once()

        # Verify the account data passed to create_account includes HSA-specific fields
        call_args = import_mock_db.create_account.call_args[0][0]
        assert call_args['type'] == 'HSA'
        assert call_args['current_balance'] == 7500.0
        assert call_args['annual_contribution_limit'] == 4300.0
        assert call_args['current_year_contributions'] == 3000.0
        assert call_args['employer_contributions'] == 1500.0
        assert call_args['investment_balance'] == 5000.0
        assert call_args['cash_balance'] == 2500.0

    def test_import_data_with_watchlist(self, encryption_service):
        """Test importing data that includes watchlist items."""
        # Create test backup data with watchlist
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat(),
                'accounts_count': 0,
                'watchlist_count': 2
            },
            'accounts': [],
            'stock_positions': {},
            'watchlist': [
                {
                    'id': 'import-watch-1',
                    'symbol': 'NVDA',
                    'notes': 'NVIDIA Corporation',
                    'added_date': '2024-01-01T12:00:00',
                    'current_price': 450.00,
                    'last_price_update': '2024-01-15T15:30:00',
                    'daily_change': 10.00,
                    'daily_change_percent': 2.27,
                    'is_demo': False
                },
                {
                    'id': 'import-watch-2',
                    'symbol': 'AMZN',
                    'notes': 'Amazon.com Inc.',
                    'added_date': '2024-01-02T10:00:00',
                    'current_price': 3200.00,
                    'last_price_update': '2024-01-15T16:00:00',
                    'daily_change': -25.00,
                    'daily_change_percent': -0.77,
                    'is_demo': True
                }
            ],
            'historical_snapshots': {},
            'app_settings': {}
        }

        # Create mock database for import
        import_mock_db = Mock(spec=DatabaseService)
        import_mock_db.get_watchlist_item.return_value = None  # Items don't exist
        import_mock_db.create_watchlist_item.return_value = 'new-watch-id'

        # Create import service
        import_service = ExportImportService(import_mock_db, encryption_service)

        # Import data
        import_results = import_service.import_data(backup_data, overwrite_existing=False)

        # Verify watchlist items were imported
        assert import_results['accounts_imported'] == 0
        assert import_results['watchlist_imported'] == 2
        assert import_results['watchlist_skipped'] == 0
        assert len(import_results['errors']) == 0

        # Verify database methods were called correctly
        assert import_mock_db.create_watchlist_item.call_count == 2

        # Verify the watchlist data passed to create_watchlist_item
        call_args_list = import_mock_db.create_watchlist_item.call_args_list

        # Check first watchlist item
        first_call_data = call_args_list[0][0][0]
        assert first_call_data['symbol'] == 'NVDA'
        assert first_call_data['notes'] == 'NVIDIA Corporation'
        assert first_call_data['current_price'] == 450.00
        assert isinstance(first_call_data['added_date'], datetime)
        assert isinstance(first_call_data['last_price_update'], datetime)

        # Check second watchlist item
        second_call_data = call_args_list[1][0][0]
        assert second_call_data['symbol'] == 'AMZN'
        assert second_call_data['is_demo'] is True

    def test_import_data_with_existing_watchlist_items(self, encryption_service):
        """Test importing watchlist data when items already exist."""
        # Create test backup data
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1,
                'export_timestamp': datetime.now().isoformat(),
                'watchlist_count': 1
            },
            'accounts': [],
            'stock_positions': {},
            'watchlist': [
                {
                    'id': 'existing-watch-1',
                    'symbol': 'EXISTING',
                    'notes': 'Existing stock',
                    'added_date': '2024-01-01T12:00:00',
                    'current_price': 100.00,
                    'is_demo': False
                }
            ],
            'historical_snapshots': {},
            'app_settings': {}
        }

        # Create mock database for import
        import_mock_db = Mock(spec=DatabaseService)
        import_mock_db.get_watchlist_item.return_value = {'symbol': 'EXISTING', 'notes': 'Old notes'}
        import_mock_db.update_watchlist_item.return_value = True

        # Create import service
        import_service = ExportImportService(import_mock_db, encryption_service)

        # Import without overwrite
        import_results = import_service.import_data(backup_data, overwrite_existing=False)

        # Verify watchlist item was skipped
        assert import_results['watchlist_imported'] == 0
        assert import_results['watchlist_skipped'] == 1

        # Import with overwrite
        import_results = import_service.import_data(backup_data, overwrite_existing=True)

        # Verify watchlist item was updated
        assert import_results['watchlist_imported'] == 1
        assert import_results['watchlist_skipped'] == 0
        import_mock_db.update_watchlist_item.assert_called_once()

    def test_prepare_watchlist_for_import(self, export_import_service_hsa_watchlist):
        """Test watchlist data preparation for import."""
        # Create test watchlist data with ISO strings
        watchlist_data = {
            'id': 'watch-test',
            'symbol': 'TEST',
            'notes': 'Test stock',
            'added_date': '2024-01-01T12:00:00',
            'last_price_update': '2024-01-15T15:30:00',
            'current_price': 100.00,
            'daily_change': 2.00,
            'daily_change_percent': 2.04
        }

        # Prepare for import
        prepared = export_import_service_hsa_watchlist._prepare_watchlist_for_import(watchlist_data)

        # Verify ISO strings were converted back to datetime objects
        assert isinstance(prepared['added_date'], datetime)
        assert isinstance(prepared['last_price_update'], datetime)
        assert prepared['added_date'] == datetime(2024, 1, 1, 12, 0, 0)
        assert prepared['last_price_update'] == datetime(2024, 1, 15, 15, 30, 0)

        # Verify other fields remain unchanged
        assert prepared['symbol'] == 'TEST'
        assert prepared['current_price'] == 100.00

    def test_prepare_watchlist_for_import_invalid_dates(self, export_import_service_hsa_watchlist):
        """Test watchlist data preparation with invalid date strings."""
        # Create test watchlist data with invalid ISO strings
        watchlist_data = {
            'id': 'watch-test',
            'symbol': 'TEST',
            'added_date': 'invalid-date',
            'last_price_update': 'also-invalid',
            'current_price': 100.00
        }

        # Prepare for import
        prepared = export_import_service_hsa_watchlist._prepare_watchlist_for_import(watchlist_data)

        # Verify invalid dates were handled gracefully
        assert isinstance(prepared['added_date'], datetime)  # Should be current time
        assert prepared['last_price_update'] is None  # Should be None for invalid last_price_update

    def test_validate_backup_integrity_with_hsa_watchlist(self, export_import_service_hsa_watchlist, mock_db_service_with_hsa_watchlist):
        """Test backup integrity validation with HSA and watchlist data."""
        # Create backup data with HSA and watchlist
        export_data = export_import_service_hsa_watchlist.export_data()

        # Validate integrity
        validation_results = export_import_service_hsa_watchlist.validate_backup_integrity(export_data)

        # Verify validation results include HSA and watchlist counts
        assert validation_results['valid'] is True
        assert len(validation_results['errors']) == 0
        assert validation_results['summary']['accounts_count'] == 2
        assert validation_results['summary']['watchlist_count'] == 2

    def test_validate_backup_integrity_invalid_watchlist(self, export_import_service_hsa_watchlist):
        """Test backup integrity validation with invalid watchlist data."""
        # Create invalid backup data with watchlist items missing symbols
        invalid_backup = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1
            },
            'accounts': [],
            'watchlist': [
                {'id': 'watch-1', 'notes': 'Missing symbol'},  # Missing symbol
                {'symbol': 'VALID', 'notes': 'Valid item'},  # Missing ID (warning)
                {'symbol': 'ALSO_VALID', 'id': 'watch-3'}  # Valid
            ]
        }

        # Validate integrity
        validation_results = export_import_service_hsa_watchlist.validate_backup_integrity(invalid_backup)

        # Verify validation caught the issues
        assert validation_results['valid'] is False
        assert len(validation_results['errors']) == 1
        assert len(validation_results['warnings']) == 1
        assert "Watchlist item found without symbol" in validation_results['errors'][0]
        assert "Watchlist item found without ID" in validation_results['warnings'][0]

    def test_end_to_end_export_import_hsa_watchlist(self, mock_db_service_with_hsa_watchlist, encryption_service):
        """Test complete export-import cycle with HSA accounts and watchlist data."""
        # Create export service
        export_service = ExportImportService(mock_db_service_with_hsa_watchlist, encryption_service)

        # Export data
        original_export = export_service.export_data(include_historical=True)
        encrypted_backup = export_service.create_encrypted_backup(original_export)

        # Create import service with fresh mock database
        import_mock_db = Mock(spec=DatabaseService)
        import_mock_db.get_account.return_value = None
        import_mock_db.get_watchlist_item.return_value = None
        import_mock_db.create_account.return_value = 'new-account-id'
        import_mock_db.create_watchlist_item.return_value = 'new-watch-id'
        import_mock_db.create_historical_snapshot.return_value = 'new-snap-id'
        import_mock_db.set_setting.return_value = None

        import_service = ExportImportService(import_mock_db, encryption_service)

        # Decrypt and import
        decrypted_backup = import_service.decrypt_backup(encrypted_backup)
        import_results = import_service.import_data(decrypted_backup, overwrite_existing=False)

        # Verify import was successful
        assert import_results['accounts_imported'] == 2  # HSA + CD accounts
        assert import_results['watchlist_imported'] == 2  # AAPL + GOOGL
        assert import_results['historical_snapshots_imported'] == 2
        assert import_results['settings_imported'] == 1
        assert len(import_results['errors']) == 0

        # Verify data integrity
        validation_results = import_service.validate_backup_integrity(decrypted_backup)
        assert validation_results['valid'] is True
        assert validation_results['summary']['accounts_count'] == 2
        assert validation_results['summary']['watchlist_count'] == 2

    def test_export_import_error_handling_watchlist(self, encryption_service):
        """Test error handling in watchlist export/import operations."""
        # Create mock database that raises errors
        error_mock_db = Mock(spec=DatabaseService)
        error_mock_db.get_accounts.return_value = []
        error_mock_db.get_watchlist_items.side_effect = Exception("Watchlist database error")

        # Create service and test export error
        service = ExportImportService(error_mock_db, encryption_service)

        with pytest.raises(Exception, match="Failed to export data"):
            service.export_data()

        # Test import error with invalid watchlist data
        backup_data = {
            'backup_metadata': {
                'backup_version': '1.0',
                'format_version': 1
            },
            'accounts': [],
            'stock_positions': {},
            'watchlist': [
                {'notes': 'Missing symbol and ID'}  # Invalid watchlist item
            ],
            'historical_snapshots': {},
            'app_settings': {}
        }

        # Create import service
        import_mock_db = Mock(spec=DatabaseService)
        import_service = ExportImportService(import_mock_db, encryption_service)

        # Import should handle errors gracefully
        import_results = import_service.import_data(backup_data, overwrite_existing=False)

        # Verify error was recorded
        assert len(import_results['errors']) > 0
        assert "Watchlist item missing symbol" in import_results['errors'][0]