"""
Edge case error handling tests for HSA and watchlist operations.

This test module covers edge cases and boundary conditions:
- Empty/null input handling
- Extreme values
- Concurrent operation errors
- Database corruption scenarios
- Network failure recovery
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date
import sqlite3

from services.error_handler import (
    DatabaseError, NetworkError, SystemError, ValidationError,
    HSABalanceValidationError, HSABalanceMismatchError, WatchlistError, StockValidationError
)
from models.accounts import HSAAccount, AccountType
from models.watchlist import WatchlistItem
from services.watchlist import WatchlistService, WatchlistServiceError
from services.stock_prices import StockPriceService, StockPriceServiceError


class TestEdgeCaseInputHandling:
    """Test edge cases for input validation."""

    def test_hsa_extreme_values(self):
        """Test HSA account with extreme values."""
        # Test with very large values
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=999999999.99,
            cash_balance=999999999.99,
            investment_balance=0.0,
            annual_contribution_limit=999999.0,
            current_year_contributions=0.0
        )

        assert hsa.get_current_value() == 999999999.99

    def test_hsa_zero_values(self):
        """Test HSA account with zero values."""
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=0.0,
            cash_balance=0.0,
            investment_balance=0.0,
            annual_contribution_limit=0.0,
            current_year_contributions=0.0
        )

        assert hsa.get_current_value() == 0.0
        assert hsa.get_remaining_contribution_capacity() == 0.0

    def test_watchlist_empty_symbol_variations(self):
        """Test watchlist with various empty symbol inputs."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Test various empty/invalid inputs
        invalid_symbols = ["", " ", None, "   ", "\t", "\n"]

        for symbol in invalid_symbols:
            with pytest.raises((ValidationError, StockValidationError)):
                watchlist_service.add_stock(symbol, "Test notes")

    def test_watchlist_symbol_case_handling(self):
        """Test watchlist symbol case normalization."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock empty watchlist and successful price fetch
        watchlist_service.get_watchlist = Mock(return_value=[])
        mock_stock_service.get_current_price.return_value = 150.0
        watchlist_service._store_watchlist_item = Mock()

        # Test that lowercase symbol is normalized to uppercase
        item_id = watchlist_service.add_stock("aapl", "Apple Inc.")

        # Verify the stock service was called with uppercase symbol
        mock_stock_service.get_current_price.assert_called_with("AAPL")

    def test_watchlist_notes_edge_cases(self):
        """Test watchlist with edge case notes."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        watchlist_service.get_watchlist = Mock(return_value=[])
        mock_stock_service.get_current_price.return_value = 150.0
        watchlist_service._store_watchlist_item = Mock()

        # Test with very long notes
        long_notes = "A" * 1000
        item_id = watchlist_service.add_stock("AAPL", long_notes)

        # Should succeed (service doesn't enforce length limit, API does)
        assert item_id is not None

    def test_stock_price_special_characters(self):
        """Test stock price service with special characters."""
        stock_service = StockPriceService()

        # Test symbols with special characters (should fail validation)
        invalid_symbols = ["AAPL$", "GOOGL@", "MSFT#", "TSLA%", "AMZN&"]

        for symbol in invalid_symbols:
            with pytest.raises(StockPriceServiceError) as exc_info:
                stock_service.get_current_price(symbol)
            assert "Invalid symbol format" in str(exc_info.value)


class TestConcurrencyAndRaceConditions:
    """Test concurrent operation error handling."""

    def test_watchlist_concurrent_add_same_symbol(self):
        """Test adding same symbol concurrently."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # First call returns empty list, second call returns item (simulating race condition)
        existing_item = WatchlistItem.create_new("AAPL", "Apple Inc.")
        watchlist_service.get_watchlist = Mock(side_effect=[[], [existing_item]])

        mock_stock_service.get_current_price.return_value = 150.0

        # First add should succeed
        watchlist_service._store_watchlist_item = Mock()
        item_id = watchlist_service.add_stock("AAPL", "Apple Inc.")
        assert item_id is not None

        # Second add should fail with duplicate error
        from services.error_handler import WatchlistDuplicateError
        with pytest.raises(WatchlistDuplicateError):
            watchlist_service.add_stock("AAPL", "Apple Inc.")

    def test_hsa_concurrent_contribution_validation(self):
        """Test HSA contribution validation under concurrent updates."""
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=1000.0,
            cash_balance=1000.0,
            investment_balance=0.0,
            annual_contribution_limit=3000.0,
            current_year_contributions=2000.0
        )

        # Should allow contribution of 1000 (at limit)
        hsa.validate_contribution(1000.0)

        # Should fail if trying to contribute more than remaining
        from services.error_handler import HSAContributionLimitError
        with pytest.raises(HSAContributionLimitError):
            hsa.validate_contribution(1001.0)


class TestDatabaseErrorScenarios:
    """Test database error handling scenarios."""

    def test_watchlist_database_connection_failure(self):
        """Test watchlist operations with database connection failure."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock database connection failure
        mock_db_service.connect.side_effect = sqlite3.OperationalError("Database is locked")

        with pytest.raises(WatchlistServiceError) as exc_info:
            watchlist_service.get_watchlist()

        assert "Failed to retrieve watchlist" in str(exc_info.value)

    def test_watchlist_database_corruption(self):
        """Test watchlist operations with database corruption."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock database corruption
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.side_effect = sqlite3.DatabaseError("Database disk image is malformed")
        mock_connection.cursor.return_value = mock_cursor
        mock_db_service.connect.return_value = mock_connection

        with pytest.raises(WatchlistServiceError) as exc_info:
            watchlist_service.get_watchlist()

        assert "Failed to retrieve watchlist" in str(exc_info.value)

    def test_watchlist_encryption_failure(self):
        """Test watchlist operations with encryption failure."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock successful database query but encryption failure
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_cursor.fetchall.return_value = [
            {
                'id': 'test-id',
                'symbol': 'AAPL',
                'encrypted_data': b'corrupted_data',
                'added_date': int(datetime.now().timestamp()),
                'last_price_update': None,
                'is_demo': False
            }
        ]
        mock_connection.cursor.return_value = mock_cursor
        mock_db_service.connect.return_value = mock_connection

        # Mock decryption failure
        mock_db_service.encryption_service.decrypt.side_effect = Exception("Decryption failed")

        # Should return empty list and log errors (graceful degradation)
        result = watchlist_service.get_watchlist()
        assert result == []


class TestNetworkErrorScenarios:
    """Test network error handling scenarios."""

    @patch('yfinance.Ticker')
    def test_stock_price_network_timeout_recovery(self, mock_ticker):
        """Test stock price service recovery from network timeouts."""
        stock_service = StockPriceService(max_retries=3)

        # Mock network timeout on first two attempts, success on third
        mock_ticker_instance = Mock()
        # Create a proper mock for the successful history call
        successful_hist = Mock()
        successful_hist.empty = False
        successful_hist.__getitem__ = Mock(return_value=Mock(iloc=Mock(__getitem__=lambda x, y: 150.0)))

        mock_ticker_instance.history.side_effect = [
            Exception("Connection timeout"),
            Exception("Read timeout"),
            successful_hist
        ]
        mock_ticker.return_value = mock_ticker_instance

        # Should succeed after retries
        price = stock_service.get_current_price("AAPL")
        assert price == 150.0
        assert mock_ticker_instance.history.call_count == 3

    @patch('yfinance.Ticker')
    def test_stock_price_persistent_network_failure(self, mock_ticker):
        """Test stock price service with persistent network failure."""
        stock_service = StockPriceService(max_retries=2)

        # Mock persistent network failure
        mock_ticker.side_effect = Exception("Network unreachable")

        with pytest.raises(StockPriceServiceError) as exc_info:
            stock_service.get_current_price("AAPL")

        assert "Failed to fetch price" in str(exc_info.value)
        assert "after 2 attempts" in str(exc_info.value)

    def test_watchlist_price_update_network_failure(self):
        """Test watchlist price update with network failure."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock watchlist with items
        items = [WatchlistItem.create_new("AAPL", "Apple")]
        watchlist_service.get_watchlist = Mock(return_value=items)

        # Mock network failure in batch price fetch
        mock_stock_service.get_batch_prices.side_effect = Exception("Network error")

        with pytest.raises(WatchlistServiceError) as exc_info:
            watchlist_service.update_prices()

        assert "Failed to fetch stock prices" in str(exc_info.value)


class TestBoundaryConditions:
    """Test boundary conditions and limits."""

    def test_hsa_floating_point_precision(self):
        """Test HSA account with floating point precision issues."""
        # Test balance that might have floating point precision issues
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=1000.01,  # Total
            cash_balance=500.005,     # These don't add up exactly due to floating point
            investment_balance=500.005  # but should be within tolerance
        )

        # Should succeed due to 0.01 tolerance in validation
        assert hsa.get_current_value() == 1000.01

    def test_hsa_balance_precision_boundary(self):
        """Test HSA balance validation at precision boundary."""
        # Test exactly at the boundary of floating point tolerance
        with pytest.raises(HSABalanceMismatchError):
            HSAAccount(
                id="test-id",
                name="Test HSA",
                institution="Test Bank",
                account_type=AccountType.HSA,
                created_date=datetime.now(),
                last_updated=datetime.now(),
                current_balance=1000.0,
                cash_balance=500.0,
                investment_balance=500.02  # Exceeds 0.01 tolerance
            )

    def test_watchlist_maximum_size_boundary(self):
        """Test watchlist at maximum size boundary."""
        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock watchlist at exactly the limit
        max_size = 50
        existing_items = [WatchlistItem.create_new(f"STOCK{i:02d}", f"Stock {i}") for i in range(max_size)]
        watchlist_service.get_watchlist = Mock(return_value=existing_items)

        from services.error_handler import WatchlistLimitExceededError
        with pytest.raises(WatchlistLimitExceededError):
            watchlist_service.add_stock("NEWSTOCK", "New Stock", max_watchlist_size=max_size)

    def test_stock_symbol_length_boundaries(self):
        """Test stock symbol validation at length boundaries."""
        stock_service = StockPriceService()

        # Test minimum length (1 character) - should be valid format
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.history.return_value.empty = True
            mock_ticker.return_value = mock_ticker_instance

            with pytest.raises(StockPriceServiceError) as exc_info:
                stock_service.get_current_price("A")
            # Should fail due to no data, not format
            assert "No data available" in str(exc_info.value)

        # Test maximum length (10 characters) - should be valid format
        with patch('yfinance.Ticker') as mock_ticker:
            mock_ticker_instance = Mock()
            mock_ticker_instance.history.return_value.empty = True
            mock_ticker.return_value = mock_ticker_instance

            with pytest.raises(StockPriceServiceError) as exc_info:
                stock_service.get_current_price("ABCDEFGHIJ")
            # Should fail due to no data, not format
            assert "No data available" in str(exc_info.value)

        # Test over maximum length (11 characters) - should fail format validation
        with pytest.raises(StockPriceServiceError) as exc_info:
            stock_service.get_current_price("ABCDEFGHIJK")
        assert "Invalid symbol format" in str(exc_info.value)


class TestErrorMessageQuality:
    """Test error message quality and user-friendliness."""

    def test_hsa_error_messages_user_friendly(self):
        """Test that HSA error messages are user-friendly."""
        from services.error_handler import HSAContributionLimitError

        error = HSAContributionLimitError(1500.0, 1000.0)

        # Check message is clear and includes specific amounts
        assert "$1500.00" in error.message
        assert "$1000.00" in error.message
        assert "exceeds remaining capacity" in error.message

        # Check user action is helpful
        assert error.user_action is not None
        assert "$1000.00" in error.user_action

    def test_watchlist_error_messages_actionable(self):
        """Test that watchlist error messages are actionable."""
        from services.error_handler import WatchlistDuplicateError, StockValidationError

        # Test duplicate error
        duplicate_error = WatchlistDuplicateError("AAPL")
        assert "AAPL" in duplicate_error.message
        assert duplicate_error.user_action is not None

        # Test validation error
        validation_error = StockValidationError("INVALID", "Symbol not found")
        assert "INVALID" in validation_error.message
        assert "Symbol not found" in validation_error.message
        assert validation_error.user_action is not None

    def test_error_context_preservation(self):
        """Test that error context is preserved through the stack."""
        from services.error_handler import ErrorContext, SystemError

        context = ErrorContext(
            user_id="test-user",
            operation="add_watchlist_stock",
            additional_data={"symbol": "AAPL"}
        )

        error = SystemError(
            message="Test error",
            code="TEST_001",
            context=context
        )

        error_dict = error.to_dict()
        assert error_dict['context']['symbol'] == "AAPL"


if __name__ == "__main__":
    pytest.main([__file__])