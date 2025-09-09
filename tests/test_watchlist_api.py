"""
Tests for watchlist API endpoints.

This module tests the Flask API endpoints for watchlist functionality including:
- GET /api/watchlist - retrieve all watchlist items
- POST /api/watchlist - add stocks to watchlist
- DELETE /api/watchlist/{symbol} - remove stocks from watchlist
- GET /api/watchlist/{symbol} - get specific stock details
- PUT /api/watchlist/prices - batch price updates
"""

import json
import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Import the Flask app and test client
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.auth import AuthenticationManager
from services.database import DatabaseService
from services.encryption import EncryptionService
from models.watchlist import WatchlistItem


class TestWatchlistAPI:
    """Test class for watchlist API endpoints"""

    @pytest.fixture
    def client(self):
        """Create a test client with temporary database"""
        # Create temporary database file
        db_fd, db_path = tempfile.mkstemp()

        # Configure app for testing
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = db_path

        with app.test_client() as client:
            with app.app_context():
                # Mock authentication to be always authenticated
                app.auth_manager.is_authenticated = Mock(return_value=True)
                app.auth_manager.require_authentication = Mock(return_value=True)

                # Create mock database service
                mock_db_service = Mock(spec=DatabaseService)
                mock_encryption_service = Mock(spec=EncryptionService)

                app.auth_manager.get_database_service = Mock(return_value=mock_db_service)
                app.auth_manager.get_encryption_service = Mock(return_value=mock_encryption_service)

                yield client, mock_db_service, mock_encryption_service

        # Clean up
        os.close(db_fd)
        os.unlink(db_path)

    def test_get_watchlist_success(self, client):
        """Test successful retrieval of watchlist items"""
        test_client, mock_db_service, mock_encryption_service = client

        # Mock watchlist items
        mock_item1 = Mock(spec=WatchlistItem)
        mock_item1.to_dict.return_value = {
            'id': 'test-id-1',
            'symbol': 'AAPL',
            'notes': 'Apple Inc.',
            'current_price': 150.00,
            'daily_change': 2.50,
            'daily_change_percent': 1.69
        }

        mock_item2 = Mock(spec=WatchlistItem)
        mock_item2.to_dict.return_value = {
            'id': 'test-id-2',
            'symbol': 'GOOGL',
            'notes': 'Alphabet Inc.',
            'current_price': 2500.00,
            'daily_change': -10.00,
            'daily_change_percent': -0.40
        }

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.get_watchlist.return_value = [mock_item1, mock_item2]
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.get('/api/watchlist')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 2
            assert len(data['watchlist']) == 2
            assert data['watchlist'][0]['symbol'] == 'AAPL'
            assert data['watchlist'][1]['symbol'] == 'GOOGL'

    def test_get_watchlist_empty(self, client):
        """Test retrieval of empty watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.get_watchlist.return_value = []
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.get('/api/watchlist')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['count'] == 0
            assert data['watchlist'] == []

    def test_add_to_watchlist_success(self, client):
        """Test successful addition of stock to watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        mock_item = Mock(spec=WatchlistItem)
        mock_item.to_dict.return_value = {
            'id': 'test-id',
            'symbol': 'AAPL',
            'notes': 'Apple Inc.',
            'current_price': None,
            'daily_change': None,
            'daily_change_percent': None
        }

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.add_stock.return_value = 'test-id'
            mock_service.get_stock_details.return_value = mock_item
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.post('/api/watchlist',
                                      json={'symbol': 'AAPL', 'notes': 'Apple Inc.'})

            assert response.status_code == 201
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'AAPL added to watchlist' in data['message']
            assert data['item']['symbol'] == 'AAPL'

            # Verify service was called correctly
            mock_service.add_stock.assert_called_once_with('AAPL', 'Apple Inc.')

    def test_add_to_watchlist_missing_symbol(self, client):
        """Test adding to watchlist without symbol"""
        test_client, mock_db_service, mock_encryption_service = client

        response = test_client.post('/api/watchlist', json={'notes': 'Some notes'})

        assert response.status_code == 400
        data = json.loads(response.data)
        assert data['error'] is True
        assert 'symbol' in data['message'].lower()

    def test_add_to_watchlist_invalid_json(self, client):
        """Test adding to watchlist with invalid JSON"""
        test_client, mock_db_service, mock_encryption_service = client

        response = test_client.post('/api/watchlist',
                                  data='invalid json',
                                  content_type='application/json')

        assert response.status_code == 500  # Error handling system converts BadRequest to 500
        data = json.loads(response.data)
        assert data['error'] is True

    def test_add_to_watchlist_duplicate_symbol(self, client):
        """Test adding duplicate symbol to watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        from services.watchlist import WatchlistServiceError

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.add_stock.side_effect = WatchlistServiceError("Stock AAPL is already in the watchlist")
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.post('/api/watchlist', json={'symbol': 'AAPL'})

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'already in the watchlist' in data['message']

    def test_remove_from_watchlist_success(self, client):
        """Test successful removal of stock from watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.remove_stock.return_value = True
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.delete('/api/watchlist/AAPL')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert 'AAPL removed from watchlist' in data['message']
            assert data['removed_symbol'] == 'AAPL'

            # Verify service was called correctly
            mock_service.remove_stock.assert_called_once_with('AAPL')

    def test_remove_from_watchlist_not_found(self, client):
        """Test removal of non-existent stock from watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.remove_stock.return_value = False
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.delete('/api/watchlist/NONEXISTENT')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'not found in watchlist' in data['message']

    def test_get_watchlist_stock_success(self, client):
        """Test successful retrieval of specific stock details"""
        test_client, mock_db_service, mock_encryption_service = client

        mock_item = Mock(spec=WatchlistItem)
        mock_item.to_dict.return_value = {
            'id': 'test-id',
            'symbol': 'AAPL',
            'notes': 'Apple Inc.',
            'current_price': 150.00,
            'daily_change': 2.50,
            'daily_change_percent': 1.69
        }

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.get_stock_details.return_value = mock_item
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.get('/api/watchlist/AAPL')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['item']['symbol'] == 'AAPL'
            assert data['item']['current_price'] == 150.00

            # Verify service was called correctly
            mock_service.get_stock_details.assert_called_once_with('AAPL')

    def test_get_watchlist_stock_not_found(self, client):
        """Test retrieval of non-existent stock details"""
        test_client, mock_db_service, mock_encryption_service = client

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.get_stock_details.return_value = None
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.get('/api/watchlist/NONEXISTENT')

            assert response.status_code == 400
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'not found in watchlist' in data['message']

    def test_update_watchlist_prices_success(self, client):
        """Test successful batch price update"""
        test_client, mock_db_service, mock_encryption_service = client

        update_results = {
            'AAPL': True,
            'GOOGL': True,
            'TSLA': False
        }

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.update_prices.return_value = update_results
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.put('/api/watchlist/prices')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['summary']['total_items'] == 3
            assert data['summary']['successful_updates'] == 2
            assert data['summary']['failed_updates'] == 1
            assert 'AAPL' in data['summary']['successful_symbols']
            assert 'GOOGL' in data['summary']['successful_symbols']
            assert 'TSLA' in data['summary']['failed_symbols']
            assert data['results'] == update_results

            # Verify service was called
            mock_service.update_prices.assert_called_once()

    def test_update_watchlist_prices_empty_watchlist(self, client):
        """Test price update with empty watchlist"""
        test_client, mock_db_service, mock_encryption_service = client

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.update_prices.return_value = {}
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.put('/api/watchlist/prices')

            assert response.status_code == 200
            data = json.loads(response.data)
            assert data['success'] is True
            assert data['summary']['total_items'] == 0
            assert data['summary']['successful_updates'] == 0
            assert data['summary']['failed_updates'] == 0

    def test_update_watchlist_prices_service_error(self, client):
        """Test price update with service error"""
        test_client, mock_db_service, mock_encryption_service = client

        from services.watchlist import WatchlistServiceError

        with patch('services.watchlist.WatchlistService') as mock_watchlist_service_class:
            mock_service = Mock()
            mock_service.update_prices.side_effect = WatchlistServiceError("Price update failed")
            mock_watchlist_service_class.return_value = mock_service

            response = test_client.put('/api/watchlist/prices')

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'Failed to update watchlist prices' in data['message']

    def test_database_service_unavailable(self, client):
        """Test API endpoints when database service is unavailable"""
        test_client, mock_db_service, mock_encryption_service = client

        # Mock database service as unavailable
        app.auth_manager.get_database_service = Mock(return_value=None)

        # Test all endpoints
        endpoints = [
            ('GET', '/api/watchlist'),
            ('POST', '/api/watchlist'),
            ('DELETE', '/api/watchlist/AAPL'),
            ('GET', '/api/watchlist/AAPL'),
            ('PUT', '/api/watchlist/prices')
        ]

        for method, endpoint in endpoints:
            if method == 'GET':
                response = test_client.get(endpoint)
            elif method == 'POST':
                response = test_client.post(endpoint, json={'symbol': 'AAPL'})
            elif method == 'DELETE':
                response = test_client.delete(endpoint)
            elif method == 'PUT':
                response = test_client.put(endpoint)

            assert response.status_code == 500
            data = json.loads(response.data)
            assert data['error'] is True
            assert 'Database service not available' in data['message']

    def test_authentication_required(self, client):
        """Test that all endpoints require authentication"""
        test_client, mock_db_service, mock_encryption_service = client

        # Mock authentication as not authenticated
        app.auth_manager.is_authenticated = Mock(return_value=False)
        app.auth_manager.require_authentication = Mock(return_value=False)

        # Test all endpoints should require authentication
        # Note: The actual authentication behavior depends on the decorators used
        # This test verifies the authentication check is in place
        endpoints = [
            ('GET', '/api/watchlist'),
            ('POST', '/api/watchlist'),
            ('DELETE', '/api/watchlist/AAPL'),
            ('GET', '/api/watchlist/AAPL'),
            ('PUT', '/api/watchlist/prices')
        ]

        for method, endpoint in endpoints:
            if method == 'GET':
                response = test_client.get(endpoint)
            elif method == 'POST':
                response = test_client.post(endpoint, json={'symbol': 'AAPL'})
            elif method == 'DELETE':
                response = test_client.delete(endpoint)
            elif method == 'PUT':
                response = test_client.put(endpoint)

            # The exact response depends on the authentication decorator implementation
            # but it should not be a successful 200 response
            assert response.status_code != 200 or 'error' in json.loads(response.data)


if __name__ == '__main__':
    pytest.main([__file__])