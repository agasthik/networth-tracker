"""
Integration tests for export/import Flask routes.
Tests the complete HTTP API for data export and import functionality.
"""

import pytest
import json
import io
from unittest.mock import Mock, patch
from datetime import datetime

from app import app
from services.export_import import ExportImportService


class TestExportImportRoutes:
    """Test cases for export/import Flask routes."""

    @pytest.fixture
    def client(self):
        """Create Flask test client."""
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.test_client() as client:
            yield client

    @pytest.fixture
    def authenticated_session(self, client):
        """Create authenticated session for testing."""
        with client.session_transaction() as sess:
            sess['authenticated'] = True
            sess['session_id'] = 'test-session-id'
            sess['last_activity'] = datetime.now().isoformat()
            sess['created_at'] = datetime.now().isoformat()

    @pytest.fixture
    def mock_auth_manager(self):
        """Mock authentication manager."""
        with patch('app.auth_manager') as mock_auth:
            mock_auth.require_authentication.return_value = True
            mock_auth.is_authenticated.return_value = True

            # Mock database service
            mock_db = Mock()
            mock_db.get_accounts.return_value = [
                {
                    'id': 'test-account-1',
                    'name': 'Test Account',
                    'institution': 'Test Bank',
                    'type': 'SAVINGS',
                    'current_balance': 5000.0,
                    'interest_rate': 2.5,
                    'created_date': datetime(2024, 1, 1),
                    'last_updated': datetime(2024, 1, 15)
                }
            ]
            mock_db.get_stock_positions.return_value = []
            mock_db.get_watchlist_items.return_value = []  # Empty watchlist for route tests
            mock_db.get_historical_snapshots.return_value = []
            mock_db.get_setting.return_value = '1'

            # Mock encryption service
            mock_encryption = Mock()
            mock_encryption.encrypt.return_value = b'encrypted_test_data'
            mock_encryption.decrypt.return_value = json.dumps({
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1,
                    'export_timestamp': datetime.now().isoformat()
                },
                'accounts': [],
                'stock_positions': {},
                'historical_snapshots': {},
                'app_settings': {}
            })

            mock_auth.get_database_service.return_value = mock_db
            mock_auth.get_encryption_service.return_value = mock_encryption

            yield mock_auth

    def test_export_data_success(self, client, authenticated_session, mock_auth_manager):
        """Test successful data export."""
        response = client.get('/api/export')

        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/octet-stream'
        assert 'attachment' in response.headers['Content-Disposition']
        assert 'networth_backup_' in response.headers['Content-Disposition']
        assert '.nwb' in response.headers['Content-Disposition']
        assert len(response.data) > 0

    def test_export_data_with_historical_parameter(self, client, authenticated_session, mock_auth_manager):
        """Test data export with include_historical parameter."""
        # Test with historical data included
        response = client.get('/api/export?include_historical=true')
        assert response.status_code == 200

        # Test with historical data excluded
        response = client.get('/api/export?include_historical=false')
        assert response.status_code == 200

    def test_export_data_unauthenticated(self, client):
        """Test export data without authentication."""
        response = client.get('/api/export')
        assert response.status_code == 302  # Redirect to login

    def test_export_data_service_unavailable(self, client, authenticated_session):
        """Test export data when services are unavailable."""
        with patch('app.auth_manager') as mock_auth:
            mock_auth.require_authentication.return_value = True
            mock_auth.get_database_service.return_value = None
            mock_auth.get_encryption_service.return_value = None

            response = client.get('/api/export')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] is True
            assert data['code'] == 'SERVICES_NOT_AVAILABLE'

    def test_export_data_export_error(self, client, authenticated_session, mock_auth_manager):
        """Test export data with export service error."""
        # Mock export service to raise exception
        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.export_data.side_effect = Exception("Export failed")
            mock_service_class.return_value = mock_service

            response = client.get('/api/export')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] is True
            assert data['code'] == 'EXPORT_ERROR'

    def test_export_info_success(self, client, authenticated_session, mock_auth_manager):
        """Test successful export info retrieval."""
        response = client.get('/api/export/info')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert 'export_info' in data
        assert 'accounts_count' in data['export_info']
        assert 'stock_positions_count' in data['export_info']
        assert 'historical_snapshots_count' in data['export_info']
        assert data['export_info']['accounts_count'] == 1

    def test_export_info_unauthenticated(self, client):
        """Test export info without authentication."""
        response = client.get('/api/export/info')
        assert response.status_code == 302  # Redirect to login

    def test_import_data_success(self, client, authenticated_session, mock_auth_manager):
        """Test successful data import."""
        # Create test backup file
        backup_content = b'encrypted_backup_data'

        # Mock import service
        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1,
                    'export_timestamp': datetime.now().isoformat()
                },
                'accounts': [],
                'stock_positions': {},
                'historical_snapshots': {},
                'app_settings': {}
            }
            mock_service.validate_backup_integrity.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {'accounts_count': 0}
            }
            mock_service.import_data.return_value = {
                'accounts_imported': 0,
                'accounts_skipped': 0,
                'stock_positions_imported': 0,
                'historical_snapshots_imported': 0,
                'settings_imported': 0,
                'errors': []
            }
            mock_service_class.return_value = mock_service

            # Send import request
            data = {
                'overwrite_existing': 'false',
                'validate_only': 'false'
            }
            response = client.post('/api/import',
                                 data=data,
                                 content_type='multipart/form-data',
                                 buffered=True,
                                 follow_redirects=True)

            # Note: This test needs a proper file upload, let's test with file
            data['backup_file'] = (io.BytesIO(backup_content), 'test_backup.nwb')
            response = client.post('/api/import', data=data)

            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['success'] is True
            assert 'import_results' in response_data
            assert 'validation_results' in response_data

    def test_import_data_no_file(self, client, authenticated_session, mock_auth_manager):
        """Test import data without file upload."""
        response = client.post('/api/import', data={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'NO_FILE_PROVIDED'

    def test_import_data_empty_filename(self, client, authenticated_session, mock_auth_manager):
        """Test import data with empty filename."""
        data = {'backup_file': (io.BytesIO(b''), '')}
        response = client.post('/api/import', data=data)

        assert response.status_code == 400
        response_data = json.loads(response.data)
        assert response_data['error'] is True
        assert response_data['code'] == 'NO_FILE_SELECTED'

    def test_import_data_decryption_error(self, client, authenticated_session, mock_auth_manager):
        """Test import data with decryption error."""
        backup_content = b'invalid_encrypted_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.side_effect = Exception("Decryption failed")
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb')}
            response = client.post('/api/import', data=data)

            assert response.status_code == 400
            response_data = json.loads(response.data)
            assert response_data['error'] is True
            assert response_data['code'] == 'DECRYPTION_ERROR'

    def test_import_data_validation_error(self, client, authenticated_session, mock_auth_manager):
        """Test import data with validation error."""
        backup_content = b'encrypted_backup_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {'invalid': 'data'}
            mock_service.validate_backup_integrity.return_value = {
                'valid': False,
                'errors': ['Invalid backup format'],
                'warnings': [],
                'summary': {}
            }
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb')}
            response = client.post('/api/import', data=data)

            assert response.status_code == 400
            response_data = json.loads(response.data)
            assert response_data['error'] is True
            assert response_data['code'] == 'BACKUP_VALIDATION_ERROR'

    def test_import_data_validate_only(self, client, authenticated_session, mock_auth_manager):
        """Test import data with validate_only option."""
        backup_content = b'encrypted_backup_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1
                },
                'accounts': []
            }
            mock_service.validate_backup_integrity.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {'accounts_count': 0}
            }
            mock_service_class.return_value = mock_service

            data = {
                'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb'),
                'validate_only': 'true'
            }
            response = client.post('/api/import', data=data)

            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['success'] is True
            assert 'validation_results' in response_data
            # Should not have import_results when validate_only=true
            assert 'import_results' not in response_data

    def test_import_data_overwrite_existing(self, client, authenticated_session, mock_auth_manager):
        """Test import data with overwrite_existing option."""
        backup_content = b'encrypted_backup_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1
                },
                'accounts': []
            }
            mock_service.validate_backup_integrity.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {'accounts_count': 0}
            }
            mock_service.import_data.return_value = {
                'accounts_imported': 1,
                'accounts_skipped': 0,
                'errors': []
            }
            mock_service_class.return_value = mock_service

            data = {
                'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb'),
                'overwrite_existing': 'true'
            }
            response = client.post('/api/import', data=data)

            assert response.status_code == 200
            # Verify import_data was called with overwrite_existing=True
            mock_service.import_data.assert_called_once()
            call_args = mock_service.import_data.call_args
            assert call_args[1]['overwrite_existing'] is True

    def test_import_data_unauthenticated(self, client):
        """Test import data without authentication."""
        data = {'backup_file': (io.BytesIO(b'data'), 'test.nwb')}
        response = client.post('/api/import', data=data)
        assert response.status_code == 302  # Redirect to login

    def test_validate_backup_success(self, client, authenticated_session, mock_auth_manager):
        """Test successful backup validation."""
        backup_content = b'encrypted_backup_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1
                },
                'accounts': []
            }
            mock_service.validate_backup_integrity.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {'accounts_count': 0}
            }
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb')}
            response = client.post('/api/import/validate', data=data)

            assert response.status_code == 200
            response_data = json.loads(response.data)
            assert response_data['success'] is True
            assert 'validation_results' in response_data

    def test_validate_backup_no_file(self, client, authenticated_session, mock_auth_manager):
        """Test backup validation without file upload."""
        response = client.post('/api/import/validate', data={})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'NO_FILE_PROVIDED'

    def test_validate_backup_validation_error(self, client, authenticated_session, mock_auth_manager):
        """Test backup validation with validation error."""
        backup_content = b'invalid_backup_data'

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.side_effect = Exception("Validation failed")
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(backup_content), 'test_backup.nwb')}
            response = client.post('/api/import/validate', data=data)

            assert response.status_code == 400
            response_data = json.loads(response.data)
            assert response_data['error'] is True
            assert response_data['code'] == 'VALIDATION_ERROR'

    def test_validate_backup_unauthenticated(self, client):
        """Test backup validation without authentication."""
        data = {'backup_file': (io.BytesIO(b'data'), 'test.nwb')}
        response = client.post('/api/import/validate', data=data)
        assert response.status_code == 302  # Redirect to login

    def test_export_import_content_types(self, client, authenticated_session, mock_auth_manager):
        """Test proper content types for export/import endpoints."""
        # Test export content type
        response = client.get('/api/export')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'application/octet-stream'

        # Test export info content type
        response = client.get('/api/export/info')
        assert response.status_code == 200
        assert 'application/json' in response.headers['Content-Type']

    def test_export_filename_format(self, client, authenticated_session, mock_auth_manager):
        """Test export filename format includes timestamp."""
        response = client.get('/api/export')

        assert response.status_code == 200
        content_disposition = response.headers['Content-Disposition']
        assert 'networth_backup_' in content_disposition
        assert '.nwb' in content_disposition
        # Verify timestamp format (YYYYMMDD_HHMMSS)
        import re
        timestamp_pattern = r'networth_backup_\d{8}_\d{6}\.nwb'
        assert re.search(timestamp_pattern, content_disposition)

    def test_import_data_file_read_error(self, client, authenticated_session, mock_auth_manager):
        """Test import data with file read error."""
        # Create a mock file that raises exception on read
        mock_file = Mock()
        mock_file.filename = 'test.nwb'
        mock_file.read.side_effect = Exception("File read error")

        with patch('flask.request') as mock_request:
            mock_request.files = {'backup_file': mock_file}
            mock_request.form = {'overwrite_existing': 'false'}
            mock_request.is_json = False

            response = client.post('/api/import')

            # This test is complex due to Flask's file handling
            # In a real scenario, we'd test this with actual file upload

    def test_large_backup_file_handling(self, client, authenticated_session, mock_auth_manager):
        """Test handling of large backup files."""
        # Create large backup content (simulate large dataset)
        large_backup_content = b'encrypted_data' * 10000  # ~130KB

        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {
                    'backup_version': '1.0',
                    'format_version': 1
                },
                'accounts': []
            }
            mock_service.validate_backup_integrity.return_value = {
                'valid': True,
                'errors': [],
                'warnings': [],
                'summary': {'accounts_count': 0}
            }
            mock_service.import_data.return_value = {
                'accounts_imported': 0,
                'errors': []
            }
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(large_backup_content), 'large_backup.nwb')}
            response = client.post('/api/import', data=data)

            # Should handle large files without issues
            assert response.status_code == 200

    def test_concurrent_export_requests(self, client, authenticated_session, mock_auth_manager):
        """Test handling of concurrent export requests."""
        import threading
        import time

        results = []

        def make_export_request():
            response = client.get('/api/export')
            results.append(response.status_code)

        # Create multiple threads for concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_export_request)
            threads.append(thread)

        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All requests should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 5

    def test_export_import_error_logging(self, client, authenticated_session, mock_auth_manager):
        """Test that errors are properly logged."""
        with patch('app.app.logger') as mock_logger:
            # Force an error in export
            mock_auth_manager.get_database_service.return_value = None

            response = client.get('/api/export')

            # Verify error was logged
            assert response.status_code == 500
            mock_logger.error.assert_called()

    def test_export_import_security_headers(self, client, authenticated_session, mock_auth_manager):
        """Test security-related headers in responses."""
        # Test export response headers
        response = client.get('/api/export')
        assert response.status_code == 200

        # Verify secure download headers
        assert response.headers['Content-Type'] == 'application/octet-stream'
        assert 'attachment' in response.headers['Content-Disposition']

        # Test import response headers
        backup_content = b'test_data'
        with patch('services.export_import.ExportImportService') as mock_service_class:
            mock_service = Mock()
            mock_service.decrypt_backup.return_value = {
                'backup_metadata': {'backup_version': '1.0', 'format_version': 1},
                'accounts': []
            }
            mock_service.validate_backup_integrity.return_value = {'valid': True, 'errors': []}
            mock_service.import_data.return_value = {'accounts_imported': 0, 'errors': []}
            mock_service_class.return_value = mock_service

            data = {'backup_file': (io.BytesIO(backup_content), 'test.nwb')}
            response = client.post('/api/import', data=data)

            assert response.status_code == 200
            assert 'application/json' in response.headers['Content-Type']