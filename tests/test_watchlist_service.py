"""
Unit tests for WatchlistService business logic.

Tests cover:
- CRUD operations for watchlist items
- Stock symbol validation using yfinance integration
- Batch price update functionality with error handling
- Database integration and encryption
- Demo data creation
- Error handling and edge cases
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

from models.watchlist import WatchlistItem
from services.watchlist import WatchlistService, WatchlistServiceError
from services.database import DatabaseService
from services.stock_prices import StockPriceService, PriceUpdateResult, StockPriceServiceError
from services.encryption import EncryptionService
from services.error_handler import ValidationError


class TestWatchlistService:
    """Test WatchlistService functionality."""

    @pytest.fixture
    def mock_db_service(self):
        """Create mock database service."""
        mock_db = Mock(spec=DatabaseService)
        mock_db.encryption_service = Mock(spec=EncryptionService)
        mock_db.encryption_service.encrypt.return_value = b'encrypted_data'
        mock_db.encryption_service.decrypt.return_value = '{"notes": "Test notes", "current_price": 150.0, "daily_change": 2.5, "daily_change_percent": 1.69}'

        # Mock database connection and cursor
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        mock_db.connect.return_value = mock_connection

        return mock_db

    @pytest.fixture
    def mock_stock_service(self):
        """Create mock stock price service."""
        mock_stock = Mock(spec=StockPriceService)
        mock_stock.get_current_price.return_value = 150.0
        return mock_stock

    @pytest.fixture
    def watchlist_service(self, mock_db_service, mock_stock_service):
        """Create WatchlistService instance with mocked dependencies."""
        return WatchlistService(mock_db_service, mock_stock_service)

    def test_init(self, mock_db_service, mock_stock_service):
        """Test WatchlistService initialization."""
        service = WatchlistService(mock_db_service, mock_stock_service)
        assert service.db_service == mock_db_service
        assert service.stock_service == mock_stock_service
        assert service.logger is not None

    def test_add_stock_success(self, watchlist_service, mock_stock_service):
        """Test successfully adding a stock to watchlist."""
        # Mock empty watchlist (no existing items)
        watchlist_service.get_watchlist = Mock(return_value=[])
        watchlist_service._store_watchlist_item = Mock()

        # Mock successful price validation
        mock_stock_service.get_current_price.return_value = 150.0

        result_id = watchlist_service.add_stock("AAPL", "Apple Inc.")

        # Verify stock service was called for validation
        mock_stock_service.get_current_price.assert_called_once_with("AAPL")

        # Verify storage was called
        watchlist_service._store_watchlist_item.assert_called_once()

        # Verify return value is a valid UUID-like string
        assert isinstance(result_id, str)
        assert len(result_id) > 0

    def test_add_stock_empty_symbol(self, watchlist_service):
        """Test adding stock with empty symbol."""
        with pytest.raises(ValidationError, match="Stock symbol cannot be empty"):
            watchlist_service.add_stock("")

        with pytest.raises(ValidationError, match="Stock symbol cannot be empty"):
            watchlist_service.add_stock(None)

    def test_add_stock_duplicate_symbol(self, watchlist_service):
        """Test adding duplicate stock symbol."""
        existing_item = WatchlistItem.create_new("AAPL", "Existing Apple")
        watchlist_service.get_watchlist = Mock(return_value=[existing_item])

        with pytest.raises(WatchlistServiceError, match="Stock AAPL is already in the watchlist"):
            watchlist_service.add_stock("aapl", "New Apple")  # Test case insensitive

    def test_add_stock_invalid_symbol(self, watchlist_service, mock_stock_service):
        """Test adding invalid stock symbol."""
        watchlist_service.get_watchlist = Mock(return_value=[])
        mock_stock_service.get_current_price.side_effect = StockPriceServiceError("Invalid symbol")

        with pytest.raises(ValidationError, match="Invalid stock symbol 'INVALID'"):
            watchlist_service.add_stock("INVALID")

    def test_remove_stock_success(self, watchlist_service, mock_db_service):
        """Test successfully removing a stock from watchlist."""
        # Mock database operations
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = {'id': 'test-id'}

        result = watchlist_service.remove_stock("AAPL")

        assert result is True
        mock_cursor.execute.assert_any_call('SELECT id FROM watchlist WHERE symbol = ?', ('AAPL',))
        mock_cursor.execute.assert_any_call('DELETE FROM watchlist WHERE symbol = ?', ('AAPL',))

    def test_remove_stock_not_found(self, watchlist_service, mock_db_service):
        """Test removing non-existent stock."""
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = None

        result = watchlist_service.remove_stock("NONEXISTENT")

        assert result is False

    def test_remove_stock_empty_symbol(self, watchlist_service):
        """Test removing stock with empty symbol."""
        assert watchlist_service.remove_stock("") is False
        assert watchlist_service.remove_stock(None) is False

    def test_get_watchlist_success(self, watchlist_service, mock_db_service):
        """Test successfully retrieving watchlist."""
        # Mock database response
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value
        now_timestamp = int(datetime.now().timestamp())
        mock_row = {
            'id': 'test-id',
            'symbol': 'AAPL',
            'encrypted_data': b'encrypted_data',
            'added_date': now_timestamp,
            'last_price_update': now_timestamp,
            'is_demo': False
        }
        mock_cursor.fetchall.return_value = [mock_row]

        # Mock table creation
        watchlist_service._ensure_watchlist_table = Mock()

        result = watchlist_service.get_watchlist()

        assert len(result) == 1
        assert isinstance(result[0], WatchlistItem)
        assert result[0].symbol == 'AAPL'

    def test_get_watchlist_empty(self, watchlist_service, mock_db_service):
        """Test retrieving empty watchlist."""
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value
        mock_cursor.fetchall.return_value = []
        watchlist_service._ensure_watchlist_table = Mock()

        result = watchlist_service.get_watchlist()

        assert result == []

    def test_get_stock_details_found(self, watchlist_service):
        """Test getting details for existing stock."""
        test_item = WatchlistItem.create_new("AAPL", "Apple Inc.")
        watchlist_service.get_watchlist = Mock(return_value=[test_item])

        result = watchlist_service.get_stock_details("AAPL")

        assert result is not None
        assert result.symbol == "AAPL"
        assert result.notes == "Apple Inc."

    def test_get_stock_details_not_found(self, watchlist_service):
        """Test getting details for non-existent stock."""
        watchlist_service.get_watchlist = Mock(return_value=[])

        result = watchlist_service.get_stock_details("NONEXISTENT")

        assert result is None

    def test_get_stock_details_case_insensitive(self, watchlist_service):
        """Test getting stock details is case insensitive."""
        test_item = WatchlistItem.create_new("AAPL", "Apple Inc.")
        watchlist_service.get_watchlist = Mock(return_value=[test_item])

        result = watchlist_service.get_stock_details("aapl")

        assert result is not None
        assert result.symbol == "AAPL"

    def test_update_prices_success(self, watchlist_service, mock_stock_service):
        """Test successful batch price update."""
        # Create test items
        item1 = WatchlistItem.create_new("AAPL", "Apple Inc.")
        item1.current_price = 148.0  # Previous price for daily change calculation

        item2 = WatchlistItem.create_new("GOOGL", "Google Inc.")

        watchlist_service.get_watchlist = Mock(return_value=[item1, item2])
        watchlist_service._store_watchlist_item = Mock()

        # Mock successful price updates
        price_results = {
            'AAPL': PriceUpdateResult('AAPL', True, 150.0, None, datetime.now()),
            'GOOGL': PriceUpdateResult('GOOGL', True, 2800.0, None, datetime.now())
        }
        mock_stock_service.get_batch_prices.return_value = price_results

        result = watchlist_service.update_prices()

        assert result == {'AAPL': True, 'GOOGL': True}
        mock_stock_service.get_batch_prices.assert_called_once_with(['AAPL', 'GOOGL'])
        assert watchlist_service._store_watchlist_item.call_count == 2

    def test_update_prices_partial_failure(self, watchlist_service, mock_stock_service):
        """Test batch price update with some failures."""
        item1 = WatchlistItem.create_new("AAPL", "Apple Inc.")
        item2 = WatchlistItem.create_new("INVALID", "Invalid Stock")

        watchlist_service.get_watchlist = Mock(return_value=[item1, item2])
        watchlist_service._store_watchlist_item = Mock()

        # Mock mixed results
        price_results = {
            'AAPL': PriceUpdateResult('AAPL', True, 150.0, None, datetime.now()),
            'INVALID': PriceUpdateResult('INVALID', False, None, 'Invalid symbol', datetime.now())
        }
        mock_stock_service.get_batch_prices.return_value = price_results

        result = watchlist_service.update_prices()

        assert result == {'AAPL': True, 'INVALID': False}
        # Only successful update should be stored
        watchlist_service._store_watchlist_item.assert_called_once()

    def test_update_prices_empty_watchlist(self, watchlist_service):
        """Test updating prices with empty watchlist."""
        watchlist_service.get_watchlist = Mock(return_value=[])

        result = watchlist_service.update_prices()

        assert result == {}

    def test_validate_symbol_valid(self, watchlist_service, mock_stock_service):
        """Test validating a valid stock symbol."""
        mock_stock_service.get_current_price.return_value = 150.0

        result = watchlist_service.validate_symbol("AAPL")

        assert result is True
        mock_stock_service.get_current_price.assert_called_once_with("AAPL")

    def test_validate_symbol_invalid(self, watchlist_service, mock_stock_service):
        """Test validating an invalid stock symbol."""
        mock_stock_service.get_current_price.side_effect = StockPriceServiceError("Invalid symbol")

        result = watchlist_service.validate_symbol("INVALID")

        assert result is False

    def test_validate_symbol_empty(self, watchlist_service):
        """Test validating empty symbol."""
        assert watchlist_service.validate_symbol("") is False
        assert watchlist_service.validate_symbol(None) is False

    def test_get_watchlist_summary(self, watchlist_service):
        """Test getting watchlist summary statistics."""
        # Create test items with various states
        item1 = WatchlistItem.create_new("AAPL", "Apple Inc.")
        item1.update_price(150.0, 2.5, 1.69)  # Gainer

        item2 = WatchlistItem.create_new("GOOGL", "Google Inc.")
        item2.update_price(2800.0, -15.0, -0.53)  # Loser

        item3 = WatchlistItem.create_new("MSFT", "Microsoft")  # No price data

        item4 = WatchlistItem.create_new("TSLA", "Tesla")
        item4.update_price(800.0, 0.0, 0.0)  # No change
        # Make price data stale
        item4.last_price_update = datetime.now() - timedelta(hours=25)

        watchlist_service.get_watchlist = Mock(return_value=[item1, item2, item3, item4])

        result = watchlist_service.get_watchlist_summary()

        assert result['total_items'] == 4
        assert result['items_with_prices'] == 3
        assert result['items_with_stale_prices'] == 2  # item3 (no price) + item4 (stale)
        assert result['gainers'] == 1  # item1
        assert result['losers'] == 1   # item2
        assert 'last_updated' in result

    def test_get_watchlist_summary_error_handling(self, watchlist_service):
        """Test watchlist summary with error."""
        watchlist_service.get_watchlist = Mock(side_effect=Exception("Database error"))

        result = watchlist_service.get_watchlist_summary()

        assert result['total_items'] == 0
        assert 'error' in result

    def test_clear_watchlist(self, watchlist_service, mock_db_service):
        """Test clearing all watchlist items."""
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value
        mock_cursor.fetchone.return_value = [5]  # 5 items to be deleted

        result = watchlist_service.clear_watchlist()

        assert result == 5
        mock_cursor.execute.assert_any_call('SELECT COUNT(*) FROM watchlist')
        mock_cursor.execute.assert_any_call('DELETE FROM watchlist')

    def test_add_demo_watchlist_items(self, watchlist_service, mock_stock_service):
        """Test adding demo watchlist items."""
        # Mock no existing items
        watchlist_service.get_stock_details = Mock(return_value=None)
        watchlist_service._store_demo_watchlist_item = Mock()

        # Mock successful price fetches for some stocks
        def mock_get_price(symbol):
            prices = {'AAPL': 150.0, 'GOOGL': 2800.0, 'MSFT': 300.0}
            if symbol in prices:
                return prices[symbol]
            raise StockPriceServiceError("Price not available")

        mock_stock_service.get_current_price.side_effect = mock_get_price

        result = watchlist_service.add_demo_watchlist_items()

        assert len(result) == 8  # Should create 8 demo items
        assert watchlist_service._store_demo_watchlist_item.call_count == 8

    def test_ensure_watchlist_table(self, watchlist_service, mock_db_service):
        """Test ensuring watchlist table exists."""
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value

        watchlist_service._ensure_watchlist_table()

        # Verify table creation SQL was executed
        create_table_calls = [call for call in mock_cursor.execute.call_args_list
                             if 'CREATE TABLE IF NOT EXISTS watchlist' in str(call)]
        assert len(create_table_calls) == 1

        # Verify index creation
        create_index_calls = [call for call in mock_cursor.execute.call_args_list
                             if 'CREATE INDEX IF NOT EXISTS' in str(call)]
        assert len(create_index_calls) == 1

    def test_store_watchlist_item(self, watchlist_service, mock_db_service):
        """Test storing watchlist item in database."""
        watchlist_service._ensure_watchlist_table = Mock()
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value

        item = WatchlistItem.create_new("AAPL", "Apple Inc.")
        item.update_price(150.0, 2.5, 1.69)

        watchlist_service._store_watchlist_item(item)

        # Verify encryption was called
        mock_db_service.encryption_service.encrypt.assert_called_once()

        # Verify database insert was called
        insert_calls = [call for call in mock_cursor.execute.call_args_list
                       if 'INSERT OR REPLACE INTO watchlist' in str(call)]
        assert len(insert_calls) == 1

    def test_store_demo_watchlist_item(self, watchlist_service, mock_db_service):
        """Test storing demo watchlist item."""
        watchlist_service._ensure_watchlist_table = Mock()
        mock_cursor = mock_db_service.connect.return_value.cursor.return_value

        item = WatchlistItem.create_new("AAPL", "Apple Inc.")

        watchlist_service._store_demo_watchlist_item(item)

        # Verify the item was stored with is_demo=True
        insert_calls = mock_cursor.execute.call_args_list
        insert_call = next((call for call in insert_calls
                           if 'INSERT OR REPLACE INTO watchlist' in str(call)), None)

        assert insert_call is not None
        # The last parameter should be True for demo flag
        assert insert_call[0][1][-1] is True  # is_demo parameter

    @patch('services.watchlist.logging.getLogger')
    def test_logging_integration(self, mock_get_logger, watchlist_service):
        """Test that service integrates with logging properly."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger

        # Create new service to trigger logger initialization
        service = WatchlistService(Mock(), Mock())

        mock_get_logger.assert_called_once()
        assert service.logger == mock_logger