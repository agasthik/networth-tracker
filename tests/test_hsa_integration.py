"""
Integration tests specifically for HSA account API functionality.
Tests the complete HSA account lifecycle through the API.
"""

import pytest
import json
import tempfile
import os
from datetime import date, datetime, timedelta
from flask import Flask

from app import app, auth_manager
from services.auth import AuthenticationManager
from services.database import DatabaseService
from services.encryption import EncryptionService
from models.accounts import AccountType


class TestHSAIntegration:
    """Test suite for HSA account integration with the API."""

    @pytest.fixture
    def client(self):
        """Create test client with temporary database."""
        # Create temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp()

        # Configure test app
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.db_path
        app.config['SECRET_KEY'] = 'test-secret-key'

        with app.test_client() as client:
            with app.app_context():
                # Initialize new auth manager for test
                global auth_manager
                auth_manager.__init__(self.db_path)
                yield client

        # Cleanup
        os.close(self.db_fd)
        os.unlink(self.db_path)

    @pytest.fixture
    def authenticated_client(self, client):
        """Create authenticated test client."""
        # Set up master password
        password = "TestPassword123!"
        auth_manager.set_master_password(password)

        # Login using the client
        with client.session_transaction() as sess:
            # Manually set session data to simulate successful login
            sess.permanent = True
            sess['authenticated'] = True
            sess['session_id'] = 'test-session-id'
            sess['last_activity'] = datetime.now().isoformat()
            sess['created_at'] = datetime.now().isoformat()

        return client

    def test_hsa_account_full_lifecycle(self, authenticated_client):
        """Test complete HSA account lifecycle: create, read, update, delete."""

        # 1. Create HSA account
        hsa_data = {
            'name': 'My Health Savings Account',
            'institution': 'HSA Bank',
            'type': 'HSA',
            'current_balance': 8500.0,
            'annual_contribution_limit': 4300.0,
            'current_year_contributions': 3200.0,
            'employer_contributions': 1200.0,
            'investment_balance': 6000.0,
            'cash_balance': 2500.0
        }

        create_response = authenticated_client.post('/api/accounts',
                                                  json=hsa_data,
                                                  content_type='application/json')
        assert create_response.status_code == 201

        created_data = json.loads(create_response.data)
        assert created_data['success'] is True
        assert created_data['account']['type'] == 'HSA'
        assert created_data['account']['current_value'] == 8500.0

        account_id = created_data['account']['id']

        # 2. Read HSA account
        get_response = authenticated_client.get(f'/api/accounts/{account_id}')
        assert get_response.status_code == 200

        get_data = json.loads(get_response.data)
        assert get_data['success'] is True
        assert get_data['account']['name'] == 'My Health Savings Account'
        assert get_data['account']['annual_contribution_limit'] == 4300.0
        assert get_data['account']['current_year_contributions'] == 3200.0

        # 3. Update HSA account (add contribution)
        update_data = {
            'current_balance': 9000.0,
            'current_year_contributions': 3700.0,
            'investment_balance': 6500.0,
            'cash_balance': 2500.0
        }

        update_response = authenticated_client.put(f'/api/accounts/{account_id}',
                                                 json=update_data,
                                                 content_type='application/json')
        assert update_response.status_code == 200

        update_data_response = json.loads(update_response.data)
        assert update_data_response['success'] is True
        assert update_data_response['account']['current_value'] == 9000.0
        assert update_data_response['account']['current_year_contributions'] == 3700.0

        # 4. Verify HSA appears in account list
        list_response = authenticated_client.get('/api/accounts')
        assert list_response.status_code == 200

        list_data = json.loads(list_response.data)
        assert list_data['success'] is True
        assert list_data['count'] == 1

        hsa_account = list_data['accounts'][0]
        assert hsa_account['type'] == 'HSA'
        assert hsa_account['current_value'] == 9000.0

        # 5. Delete HSA account
        delete_response = authenticated_client.delete(f'/api/accounts/{account_id}')
        assert delete_response.status_code == 200

        delete_data = json.loads(delete_response.data)
        assert delete_data['success'] is True
        assert delete_data['deleted_account_id'] == account_id

        # 6. Verify account is deleted
        get_deleted_response = authenticated_client.get(f'/api/accounts/{account_id}')
        assert get_deleted_response.status_code == 404

    def test_hsa_contribution_limit_validation(self, authenticated_client):
        """Test HSA contribution limit validation scenarios."""

        # Test valid contribution within limit
        valid_hsa_data = {
            'name': 'Valid HSA',
            'institution': 'HSA Bank',
            'type': 'HSA',
            'current_balance': 5000.0,
            'annual_contribution_limit': 4300.0,
            'current_year_contributions': 4000.0,  # Within limit
            'employer_contributions': 1000.0,
            'investment_balance': 3000.0,
            'cash_balance': 2000.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=valid_hsa_data,
                                           content_type='application/json')
        assert response.status_code == 201

        # Test invalid contribution exceeding limit
        invalid_hsa_data = {
            'name': 'Invalid HSA',
            'institution': 'HSA Bank',
            'type': 'HSA',
            'current_balance': 5000.0,
            'annual_contribution_limit': 4300.0,
            'current_year_contributions': 5000.0,  # Exceeds limit
            'employer_contributions': 1000.0,
            'investment_balance': 3000.0,
            'cash_balance': 2000.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=invalid_hsa_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Current year contributions cannot exceed annual contribution limit' in data['message']

    def test_hsa_balance_validation(self, authenticated_client):
        """Test HSA balance validation (investment + cash = current)."""

        # Test valid balance distribution
        valid_hsa_data = {
            'name': 'Valid Balance HSA',
            'institution': 'HSA Bank',
            'type': 'HSA',
            'current_balance': 7500.0,
            'annual_contribution_limit': 4300.0,
            'current_year_contributions': 3000.0,
            'employer_contributions': 1000.0,
            'investment_balance': 5000.0,  # 5000 + 2500 = 7500 ✓
            'cash_balance': 2500.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=valid_hsa_data,
                                           content_type='application/json')
        assert response.status_code == 201

        # Test invalid balance distribution
        invalid_hsa_data = {
            'name': 'Invalid Balance HSA',
            'institution': 'HSA Bank',
            'type': 'HSA',
            'current_balance': 7500.0,
            'annual_contribution_limit': 4300.0,
            'current_year_contributions': 3000.0,
            'employer_contributions': 1000.0,
            'investment_balance': 4000.0,  # 4000 + 2500 = 6500 ≠ 7500 ✗
            'cash_balance': 2500.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=invalid_hsa_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Investment balance plus cash balance must equal current balance' in data['message']

    def test_hsa_with_other_account_types(self, authenticated_client):
        """Test HSA accounts work alongside other account types."""

        # Create multiple account types including HSA
        accounts_data = [
            {
                'name': 'Primary Savings',
                'institution': 'Bank A',
                'type': 'SAVINGS',
                'current_balance': 10000.0,
                'interest_rate': 2.0
            },
            {
                'name': 'Company 401k',
                'institution': 'Company Plan',
                'type': '401K',
                'current_balance': 75000.0,
                'employer_match': 4.0,
                'contribution_limit': 23000.0,
                'employer_contribution': 3000.0
            },
            {
                'name': 'Health Savings',
                'institution': 'HSA Bank',
                'type': 'HSA',
                'current_balance': 6000.0,
                'annual_contribution_limit': 4300.0,
                'current_year_contributions': 2500.0,
                'employer_contributions': 800.0,
                'investment_balance': 4000.0,
                'cash_balance': 2000.0
            }
        ]

        created_accounts = []
        for account_data in accounts_data:
            response = authenticated_client.post('/api/accounts',
                                               json=account_data,
                                               content_type='application/json')
            assert response.status_code == 201
            created_accounts.append(json.loads(response.data)['account'])

        # Verify all accounts exist
        list_response = authenticated_client.get('/api/accounts')
        assert list_response.status_code == 200

        list_data = json.loads(list_response.data)
        assert list_data['success'] is True
        assert list_data['count'] == 3

        # Verify HSA account is present with correct data
        hsa_account = next(acc for acc in list_data['accounts'] if acc['type'] == 'HSA')
        assert hsa_account['name'] == 'Health Savings'
        assert hsa_account['current_value'] == 6000.0
        assert hsa_account['annual_contribution_limit'] == 4300.0

        # Test filtering by HSA type
        filter_response = authenticated_client.get('/api/accounts?type=HSA')
        assert filter_response.status_code == 200

        filter_data = json.loads(filter_response.data)
        assert filter_data['success'] is True
        assert filter_data['count'] == 1
        assert filter_data['accounts'][0]['type'] == 'HSA'


if __name__ == '__main__':
    pytest.main([__file__])