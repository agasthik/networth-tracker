"""
Integration tests for account management API endpoints.
Tests all CRUD operations with proper authentication and validation.
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


class TestAccountAPI:
    """Test suite for account management API endpoints."""

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

    def test_get_accounts_empty(self, authenticated_client):
        """Test getting accounts when none exist."""
        response = authenticated_client.get('/api/accounts')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['accounts'] == []
        assert data['count'] == 0

    def test_get_accounts_unauthenticated(self, client):
        """Test getting accounts without authentication."""
        response = client.get('/api/accounts')
        assert response.status_code == 302  # Redirect to login

    def test_create_cd_account_success(self, authenticated_client):
        """Test creating a CD account successfully."""
        account_data = {
            'name': 'Test CD',
            'institution': 'Test Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'interest_rate': 2.5,
            'maturity_date': (date.today() + timedelta(days=365)).isoformat(),
            'current_value': 10250.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Account created successfully'
        assert 'account' in data
        assert data['account']['name'] == 'Test CD'
        assert data['account']['type'] == 'CD'
        assert data['account']['current_value'] == 10250.0
        assert 'id' in data['account']

    def test_create_savings_account_success(self, authenticated_client):
        """Test creating a savings account successfully."""
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['account']['name'] == 'Test Savings'
        assert data['account']['type'] == 'SAVINGS'
        assert data['account']['current_value'] == 5000.0

    def test_create_401k_account_success(self, authenticated_client):
        """Test creating a 401k account successfully."""
        account_data = {
            'name': 'Test 401k',
            'institution': 'Test Company',
            'type': '401K',
            'current_balance': 50000.0,
            'employer_match': 3.0,
            'contribution_limit': 23000.0,
            'employer_contribution': 1500.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['account']['name'] == 'Test 401k'
        assert data['account']['type'] == '401K'
        assert data['account']['current_value'] == 50000.0

    def test_create_trading_account_success(self, authenticated_client):
        """Test creating a trading account successfully."""
        account_data = {
            'name': 'Test Trading',
            'institution': 'Test Broker',
            'type': 'TRADING',
            'broker_name': 'Test Broker',
            'cash_balance': 10000.0,
            'positions': []
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['account']['name'] == 'Test Trading'
        assert data['account']['type'] == 'TRADING'
        assert data['account']['current_value'] == 10000.0

    def test_create_ibonds_account_success(self, authenticated_client):
        """Test creating an I-bonds account successfully."""
        purchase_date = date.today() - timedelta(days=30)
        maturity_date = purchase_date + timedelta(days=365*30)  # 30 years

        account_data = {
            'name': 'Test I-bonds',
            'institution': 'Treasury Direct',
            'type': 'I_BONDS',
            'purchase_amount': 1000.0,
            'purchase_date': purchase_date.isoformat(),
            'current_value': 1025.0,
            'fixed_rate': 0.5,
            'inflation_rate': 3.2,
            'maturity_date': maturity_date.isoformat()
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 201

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['account']['name'] == 'Test I-bonds'
        assert data['account']['type'] == 'I_BONDS'
        assert data['account']['current_value'] == 1025.0

    def test_create_account_missing_required_fields(self, authenticated_client):
        """Test creating account with missing required fields."""
        account_data = {
            'name': 'Test Account'
            # Missing institution and type
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Missing required fields' in data['message']
        assert data['code'] == 'MISSING_REQUIRED_FIELDS'

    def test_create_account_invalid_type(self, authenticated_client):
        """Test creating account with invalid type."""
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'INVALID_TYPE'
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Invalid account type' in data['message']
        assert data['code'] == 'INVALID_ACCOUNT_TYPE'

    def test_create_cd_account_missing_fields(self, authenticated_client):
        """Test creating CD account with missing CD-specific fields."""
        account_data = {
            'name': 'Test CD',
            'institution': 'Test Bank',
            'type': 'CD'
            # Missing CD-specific fields
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'CD account missing required fields' in data['message']
        assert data['code'] == 'MISSING_CD_FIELDS'

    def test_create_cd_account_invalid_values(self, authenticated_client):
        """Test creating CD account with invalid values."""
        account_data = {
            'name': 'Test CD',
            'institution': 'Test Bank',
            'type': 'CD',
            'principal_amount': -1000.0,  # Invalid negative amount
            'interest_rate': 2.5,
            'maturity_date': (date.today() + timedelta(days=365)).isoformat(),
            'current_value': 10250.0
        }

        response = authenticated_client.post('/api/accounts',
                                           json=account_data,
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Principal amount must be positive' in data['message']
        assert data['code'] == 'INVALID_PRINCIPAL_AMOUNT'

    def test_create_account_invalid_json(self, authenticated_client):
        """Test creating account with invalid JSON."""
        response = authenticated_client.post('/api/accounts',
                                           data='invalid json',
                                           content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_JSON_FORMAT'

    def test_create_account_non_json(self, authenticated_client):
        """Test creating account with non-JSON content type."""
        response = authenticated_client.post('/api/accounts',
                                           data='some data',
                                           content_type='text/plain')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Request must be JSON' in data['message']
        assert data['code'] == 'INVALID_CONTENT_TYPE'

    def test_get_account_success(self, authenticated_client):
        """Test getting a specific account successfully."""
        # First create an account
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        create_response = authenticated_client.post('/api/accounts',
                                                  json=account_data,
                                                  content_type='application/json')
        assert create_response.status_code == 201

        created_account = json.loads(create_response.data)['account']
        account_id = created_account['id']

        # Get the account
        response = authenticated_client.get(f'/api/accounts/{account_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert 'account' in data
        assert data['account']['id'] == account_id
        assert data['account']['name'] == 'Test Savings'
        assert data['account']['current_value'] == 5000.0

    def test_get_account_not_found(self, authenticated_client):
        """Test getting a non-existent account."""
        response = authenticated_client.get('/api/accounts/non-existent-id')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Account not found' in data['message']
        assert data['code'] == 'ACCOUNT_NOT_FOUND'

    def test_update_account_success(self, authenticated_client):
        """Test updating an account successfully."""
        # First create an account
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        create_response = authenticated_client.post('/api/accounts',
                                                  json=account_data,
                                                  content_type='application/json')
        assert create_response.status_code == 201

        created_account = json.loads(create_response.data)['account']
        account_id = created_account['id']

        # Update the account
        update_data = {
            'name': 'Updated Savings',
            'current_balance': 6000.0
        }

        response = authenticated_client.put(f'/api/accounts/{account_id}',
                                          json=update_data,
                                          content_type='application/json')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Account updated successfully'
        assert data['account']['name'] == 'Updated Savings'
        assert data['account']['current_value'] == 6000.0

    def test_update_account_not_found(self, authenticated_client):
        """Test updating a non-existent account."""
        update_data = {
            'name': 'Updated Name'
        }

        response = authenticated_client.put('/api/accounts/non-existent-id',
                                          json=update_data,
                                          content_type='application/json')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Account not found' in data['message']
        assert data['code'] == 'ACCOUNT_NOT_FOUND'

    def test_update_account_invalid_data(self, authenticated_client):
        """Test updating account with invalid data."""
        # First create an account
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        create_response = authenticated_client.post('/api/accounts',
                                                  json=account_data,
                                                  content_type='application/json')
        assert create_response.status_code == 201

        created_account = json.loads(create_response.data)['account']
        account_id = created_account['id']

        # Update with invalid data
        update_data = {
            'current_balance': -1000.0  # Invalid negative balance
        }

        response = authenticated_client.put(f'/api/accounts/{account_id}',
                                          json=update_data,
                                          content_type='application/json')
        assert response.status_code == 400

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Account validation failed' in data['message']
        assert data['code'] == 'ACCOUNT_VALIDATION_ERROR'

    def test_delete_account_success(self, authenticated_client):
        """Test deleting an account successfully."""
        # First create an account
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        create_response = authenticated_client.post('/api/accounts',
                                                  json=account_data,
                                                  content_type='application/json')
        assert create_response.status_code == 201

        created_account = json.loads(create_response.data)['account']
        account_id = created_account['id']

        # Delete the account
        response = authenticated_client.delete(f'/api/accounts/{account_id}')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Account deleted successfully'
        assert data['deleted_account_id'] == account_id

        # Verify account is deleted
        get_response = authenticated_client.get(f'/api/accounts/{account_id}')
        assert get_response.status_code == 404

    def test_delete_account_not_found(self, authenticated_client):
        """Test deleting a non-existent account."""
        response = authenticated_client.delete('/api/accounts/non-existent-id')
        assert response.status_code == 404

        data = json.loads(response.data)
        assert data['error'] is True
        assert 'Account not found' in data['message']
        assert data['code'] == 'ACCOUNT_NOT_FOUND'

    def test_get_accounts_with_filter(self, authenticated_client):
        """Test getting accounts with type filter."""
        # Create accounts of different types
        savings_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        cd_data = {
            'name': 'Test CD',
            'institution': 'Test Bank',
            'type': 'CD',
            'principal_amount': 10000.0,
            'interest_rate': 2.5,
            'maturity_date': (date.today() + timedelta(days=365)).isoformat(),
            'current_value': 10250.0
        }

        # Create both accounts
        authenticated_client.post('/api/accounts', json=savings_data, content_type='application/json')
        authenticated_client.post('/api/accounts', json=cd_data, content_type='application/json')

        # Get only savings accounts
        response = authenticated_client.get('/api/accounts?type=SAVINGS')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 1
        assert data['accounts'][0]['type'] == 'SAVINGS'

    def test_account_api_comprehensive_workflow(self, authenticated_client):
        """Test complete CRUD workflow for accounts."""
        # 1. Create multiple accounts
        accounts_to_create = [
            {
                'name': 'Primary Savings',
                'institution': 'Bank A',
                'type': 'SAVINGS',
                'current_balance': 10000.0,
                'interest_rate': 2.0
            },
            {
                'name': 'Emergency CD',
                'institution': 'Bank B',
                'type': 'CD',
                'principal_amount': 15000.0,
                'interest_rate': 3.5,
                'maturity_date': (date.today() + timedelta(days=730)).isoformat(),
                'current_value': 15500.0
            },
            {
                'name': 'Company 401k',
                'institution': 'Company Plan',
                'type': '401K',
                'current_balance': 75000.0,
                'employer_match': 4.0,
                'contribution_limit': 23000.0,
                'employer_contribution': 3000.0
            }
        ]

        created_accounts = []
        for account_data in accounts_to_create:
            response = authenticated_client.post('/api/accounts',
                                               json=account_data,
                                               content_type='application/json')
            assert response.status_code == 201
            created_accounts.append(json.loads(response.data)['account'])

        # 2. Get all accounts
        response = authenticated_client.get('/api/accounts')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 3

        # 3. Update one account
        savings_account = next(acc for acc in created_accounts if acc['type'] == 'SAVINGS')
        update_data = {
            'current_balance': 12000.0,
            'name': 'Updated Primary Savings'
        }

        response = authenticated_client.put(f'/api/accounts/{savings_account["id"]}',
                                          json=update_data,
                                          content_type='application/json')
        assert response.status_code == 200

        updated_account = json.loads(response.data)['account']
        assert updated_account['name'] == 'Updated Primary Savings'
        assert updated_account['current_value'] == 12000.0

        # 4. Delete one account
        cd_account = next(acc for acc in created_accounts if acc['type'] == 'CD')
        response = authenticated_client.delete(f'/api/accounts/{cd_account["id"]}')
        assert response.status_code == 200

        # 5. Verify final state
        response = authenticated_client.get('/api/accounts')
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 2  # One deleted

        # Verify the deleted account is gone
        account_types = [acc['type'] for acc in data['accounts']]
        assert 'CD' not in account_types
        assert 'SAVINGS' in account_types
        assert '401K' in account_types


if __name__ == '__main__':
    pytest.main([__file__])