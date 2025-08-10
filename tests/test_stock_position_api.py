"""
Unit tests for stock position management API endpoints.

Tests cover:
- Adding stock positions to trading accounts
- Updating existing stock positions
- Deleting stock positions
- Retrieving stock positions
- Updating stock prices automatically
- Portfolio value calculations including unrealized gains/losses
- Error handling and validation
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import date, datetime, timedelta

from app import app
from services.auth import AuthenticationManager
from services.database import DatabaseService
from services.encryption import EncryptionService
from models.accounts import AccountType, StockPosition


class TestStockPositionAPI:
    """Test suite for stock position management API endpoints"""

    def setup_method(self):
        """Set up test fixtures"""
        # Create temporary database
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Configure app for testing
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.db_path
        app.config['WTF_CSRF_ENABLED'] = False

        # Replace auth manager with test instance
        import app as app_module
        app_module.auth_manager = AuthenticationManager(self.db_path)

        self.client = app.test_client()
        self.test_password = "TestPassword123!"

        # Set up authentication
        self._setup_auth()

        # Create test trading account
        self.trading_account_id = self._create_test_trading_account()

    def teardown_method(self):
        """Clean up test fixtures"""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def _setup_auth(self):
        """Set up authentication for tests"""
        # Set up master password
        self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        })

        # Login
        self.client.post('/login', data={
            'password': self.test_password
        })

    def _create_test_trading_account(self):
        """Create a test trading account and return its ID"""
        account_data = {
            'name': 'Test Trading Account',
            'institution': 'Test Broker',
            'type': 'TRADING',
            'broker_name': 'Test Broker',
            'cash_balance': 10000.0
        }

        response = self.client.post('/api/accounts',
                                  data=json.dumps(account_data),
                                  content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)
        return data['account']['id']

    def _create_test_position_data(self):
        """Create test stock position data"""
        return {
            'symbol': 'AAPL',
            'shares': 100.0,
            'purchase_price': 150.0,
            'purchase_date': (date.today() - timedelta(days=30)).isoformat()
        }

    def test_get_stock_positions_empty(self):
        """Test getting stock positions for account with no positions"""
        response = self.client.get(f'/api/accounts/{self.trading_account_id}/positions')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['positions'] == []
        assert data['count'] == 0

    def test_get_stock_positions_invalid_account(self):
        """Test getting stock positions for non-existent account"""
        response = self.client.get('/api/accounts/invalid-id/positions')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'ACCOUNT_NOT_FOUND'

    def test_get_stock_positions_non_trading_account(self):
        """Test getting stock positions for non-trading account"""
        # Create a savings account
        savings_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        response = self.client.post('/api/accounts',
                                  data=json.dumps(savings_data),
                                  content_type='application/json')

        savings_id = json.loads(response.data)['account']['id']

        # Try to get positions for savings account
        response = self.client.get(f'/api/accounts/{savings_id}/positions')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_ACCOUNT_TYPE'

    def test_add_stock_position_success(self):
        """Test successfully adding a stock position"""
        position_data = self._create_test_position_data()

        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')

        assert response.status_code == 201
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Stock position added successfully'
        assert data['position']['symbol'] == 'AAPL'
        assert data['position']['shares'] == 100.0
        assert data['position']['purchase_price'] == 150.0

    def test_add_stock_position_missing_fields(self):
        """Test adding stock position with missing required fields"""
        incomplete_data = {
            'symbol': 'AAPL',
            'shares': 100.0
            # Missing purchase_price and purchase_date
        }

        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(incomplete_data),
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'MISSING_REQUIRED_FIELDS'
        assert 'purchase_price' in data['message']
        assert 'purchase_date' in data['message']

    def test_add_stock_position_invalid_values(self):
        """Test adding stock position with invalid field values"""
        # Test negative shares
        invalid_data = self._create_test_position_data()
        invalid_data['shares'] = -10

        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(invalid_data),
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_FIELD_VALUE'
        assert 'Shares must be positive' in data['message']

        # Test zero purchase price
        invalid_data = self._create_test_position_data()
        invalid_data['purchase_price'] = 0

        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(invalid_data),
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_FIELD_VALUE'
        assert 'Purchase price must be positive' in data['message']

        # Test future purchase date
        invalid_data = self._create_test_position_data()
        invalid_data['purchase_date'] = (date.today() + timedelta(days=1)).isoformat()

        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(invalid_data),
                                  content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_FIELD_VALUE'
        assert 'Purchase date cannot be in the future' in data['message']

    def test_add_stock_position_duplicate_symbol(self):
        """Test adding stock position with duplicate symbol"""
        position_data = self._create_test_position_data()

        # Add first position
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')
        assert response.status_code == 201

        # Try to add duplicate
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')

        assert response.status_code == 409
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'POSITION_ALREADY_EXISTS'
        assert 'AAPL' in data['message']

    def test_get_stock_positions_with_data(self):
        """Test getting stock positions after adding some"""
        # Add multiple positions
        positions_data = [
            {
                'symbol': 'AAPL',
                'shares': 100.0,
                'purchase_price': 150.0,
                'purchase_date': (date.today() - timedelta(days=30)).isoformat()
            },
            {
                'symbol': 'GOOGL',
                'shares': 50.0,
                'purchase_price': 2500.0,
                'purchase_date': (date.today() - timedelta(days=60)).isoformat()
            }
        ]

        for pos_data in positions_data:
            response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                      data=json.dumps(pos_data),
                                      content_type='application/json')
            assert response.status_code == 201

        # Get all positions
        response = self.client.get(f'/api/accounts/{self.trading_account_id}/positions')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['count'] == 2
        assert len(data['positions']) == 2

        symbols = [pos['symbol'] for pos in data['positions']]
        assert 'AAPL' in symbols
        assert 'GOOGL' in symbols

    def test_update_stock_position_success(self):
        """Test successfully updating a stock position"""
        # First add a position
        position_data = self._create_test_position_data()
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')
        position_id = json.loads(response.data)['position']['id']

        # Update the position
        update_data = {
            'shares': 150.0,
            'purchase_price': 140.0
        }

        response = self.client.put(f'/api/accounts/{self.trading_account_id}/positions/{position_id}',
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Stock position updated successfully'
        assert data['position']['shares'] == 150.0
        assert data['position']['purchase_price'] == 140.0

    def test_update_stock_position_not_found(self):
        """Test updating non-existent stock position"""
        update_data = {'shares': 150.0}

        response = self.client.put(f'/api/accounts/{self.trading_account_id}/positions/invalid-id',
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'POSITION_NOT_FOUND'

    def test_update_stock_position_invalid_values(self):
        """Test updating stock position with invalid values"""
        # First add a position
        position_data = self._create_test_position_data()
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')
        position_id = json.loads(response.data)['position']['id']

        # Try to update with negative shares
        update_data = {'shares': -50.0}

        response = self.client.put(f'/api/accounts/{self.trading_account_id}/positions/{position_id}',
                                 data=json.dumps(update_data),
                                 content_type='application/json')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_SHARES'

    def test_delete_stock_position_success(self):
        """Test successfully deleting a stock position"""
        # First add a position
        position_data = self._create_test_position_data()
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data=json.dumps(position_data),
                                  content_type='application/json')
        position_id = json.loads(response.data)['position']['id']

        # Delete the position
        response = self.client.delete(f'/api/accounts/{self.trading_account_id}/positions/{position_id}')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'Stock position deleted successfully'
        assert data['deleted_position_id'] == position_id

        # Verify position is gone
        response = self.client.get(f'/api/accounts/{self.trading_account_id}/positions')
        data = json.loads(response.data)
        assert data['count'] == 0

    def test_delete_stock_position_not_found(self):
        """Test deleting non-existent stock position"""
        response = self.client.delete(f'/api/accounts/{self.trading_account_id}/positions/invalid-id')

        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'POSITION_NOT_FOUND'

    @patch('services.stock_prices.yf.Ticker')
    def test_update_stock_prices_success(self, mock_ticker):
        """Test successfully updating stock prices for all positions"""
        # Mock yfinance responses
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            prices = {'AAPL': 175.0, 'GOOGL': 2600.0}
            # Create a proper pandas DataFrame mock
            import pandas as pd
            price_data = pd.DataFrame({
                'Close': [prices.get(symbol, 100.0)]
            }, index=[datetime.now()])
            return price_data

        mock_ticker_instance.history.side_effect = mock_history

        # Add test positions
        positions_data = [
            {
                'symbol': 'AAPL',
                'shares': 100.0,
                'purchase_price': 150.0,
                'purchase_date': (date.today() - timedelta(days=30)).isoformat()
            },
            {
                'symbol': 'GOOGL',
                'shares': 50.0,
                'purchase_price': 2500.0,
                'purchase_date': (date.today() - timedelta(days=60)).isoformat()
            }
        ]

        for pos_data in positions_data:
            response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                      data=json.dumps(pos_data),
                                      content_type='application/json')
            assert response.status_code == 201

        # Update stock prices
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions/update-prices')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['total_positions'] == 2
        assert data['successful_updates'] == 2

        # Check that positions were updated with new prices and calculations
        updated_positions = data['updated_positions']
        assert len(updated_positions) == 2

        # Find AAPL position and verify calculations
        aapl_pos = next(p for p in updated_positions if p['symbol'] == 'AAPL')
        assert aapl_pos['current_price'] == 175.0
        assert aapl_pos['current_value'] == 17500.0  # 175 * 100
        assert aapl_pos['unrealized_gain_loss'] == 2500.0  # 17500 - 15000
        assert abs(aapl_pos['unrealized_gain_loss_pct'] - 16.67) < 0.1  # ~16.67%

    def test_update_stock_prices_no_positions(self):
        """Test updating stock prices for account with no positions"""
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions/update-prices')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True
        assert data['message'] == 'No positions to update'
        assert data['updated_positions'] == []
        assert data['update_results'] == []

    @patch('services.stock_prices.yf.Ticker')
    def test_get_portfolio_summary(self, mock_ticker):
        """Test getting portfolio summary with calculations"""
        # Add test positions
        positions_data = [
            {
                'symbol': 'AAPL',
                'shares': 100.0,
                'purchase_price': 150.0,
                'purchase_date': (date.today() - timedelta(days=30)).isoformat()
            },
            {
                'symbol': 'GOOGL',
                'shares': 50.0,
                'purchase_price': 2500.0,
                'purchase_date': (date.today() - timedelta(days=60)).isoformat()
            }
        ]

        for pos_data in positions_data:
            response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                      data=json.dumps(pos_data),
                                      content_type='application/json')
            assert response.status_code == 201

        # Mock price updates
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            prices = {'AAPL': 175.0, 'GOOGL': 2600.0}
            # Create a proper pandas DataFrame mock
            import pandas as pd
            price_data = pd.DataFrame({
                'Close': [prices.get(symbol, 100.0)]
            }, index=[datetime.now()])
            return price_data

        mock_ticker_instance.history.side_effect = mock_history

        # Update prices first
        self.client.post(f'/api/accounts/{self.trading_account_id}/positions/update-prices')

        # Get portfolio summary
        response = self.client.get(f'/api/accounts/{self.trading_account_id}/portfolio-summary')

        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['success'] is True

        summary = data['portfolio_summary']
        assert summary['account_id'] == self.trading_account_id
        assert summary['cash_balance'] == 10000.0
        assert summary['position_count'] == 2

        # Verify calculations
        # AAPL: 100 * 175 = 17500, cost basis = 100 * 150 = 15000, gain = 2500
        # GOOGL: 50 * 2600 = 130000, cost basis = 50 * 2500 = 125000, gain = 5000
        # Total stock value = 147500, total cost basis = 140000, total gain = 7500
        assert summary['total_stock_value'] == 147500.0
        assert summary['total_cost_basis'] == 140000.0
        assert summary['total_unrealized_gain_loss'] == 7500.0
        assert summary['total_portfolio_value'] == 157500.0  # 10000 cash + 147500 stocks
        assert abs(summary['total_unrealized_gain_loss_pct'] - 5.36) < 0.1  # ~5.36%

        # Check individual position summaries
        positions = summary['positions']
        assert len(positions) == 2

        aapl_pos = next(p for p in positions if p['symbol'] == 'AAPL')
        assert aapl_pos['current_value'] == 17500.0
        assert aapl_pos['unrealized_gain_loss'] == 2500.0

    def test_portfolio_summary_non_trading_account(self):
        """Test getting portfolio summary for non-trading account"""
        # Create a savings account
        savings_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        response = self.client.post('/api/accounts',
                                  data=json.dumps(savings_data),
                                  content_type='application/json')

        savings_id = json.loads(response.data)['account']['id']

        # Try to get portfolio summary for savings account
        response = self.client.get(f'/api/accounts/{savings_id}/portfolio-summary')

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_ACCOUNT_TYPE'

    def test_authentication_required(self):
        """Test that all endpoints require authentication"""
        # Logout first
        self.client.post('/logout')

        endpoints = [
            ('GET', f'/api/accounts/{self.trading_account_id}/positions'),
            ('POST', f'/api/accounts/{self.trading_account_id}/positions'),
            ('PUT', f'/api/accounts/{self.trading_account_id}/positions/test-id'),
            ('DELETE', f'/api/accounts/{self.trading_account_id}/positions/test-id'),
            ('POST', f'/api/accounts/{self.trading_account_id}/positions/update-prices'),
            ('GET', f'/api/accounts/{self.trading_account_id}/portfolio-summary')
        ]

        for method, endpoint in endpoints:
            if method == 'GET':
                response = self.client.get(endpoint)
            elif method == 'POST':
                response = self.client.post(endpoint, data='{}', content_type='application/json')
            elif method == 'PUT':
                response = self.client.put(endpoint, data='{}', content_type='application/json')
            elif method == 'DELETE':
                response = self.client.delete(endpoint)

            assert response.status_code == 302  # Redirect to login
            assert '/login' in response.location

    def test_invalid_json_requests(self):
        """Test handling of invalid JSON in requests"""
        # Test POST endpoint with invalid content type
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data='not json', content_type='text/plain')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_CONTENT_TYPE'

        # Test POST with malformed JSON
        response = self.client.post(f'/api/accounts/{self.trading_account_id}/positions',
                                  data='{"invalid": json}', content_type='application/json')
        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert data['code'] == 'INVALID_JSON_FORMAT'


if __name__ == '__main__':
    pytest.main([__file__])