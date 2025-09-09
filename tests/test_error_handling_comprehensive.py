"""
Comprehensive error handling tests for HSA and watchlist operations.

This test module covers:
- HSA account validation errors
- Watchlist operation errors
- Stock symbol validation errors
- Price update error handling
- API endpoint error responses
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, date

from services.error_handler import (
    HSAError, HSAContributionLimitError, HSABalanceValidationError,
    HSABalanceMismatchError, HSAContributionValidationError,
    WatchlistError, WatchlistDuplicateError, WatchlistNotFoundError,
    WatchlistLimitExceededError, WatchlistPriceUpdateError,
    StockValidationError, StockPriceUnavailableError, StockNotFoundError
)
from models.accounts import HSAAccount, AccountType
from models.watchlist import WatchlistItem
from services.watchlist import WatchlistService, WatchlistServiceError
from services.stock_prices import StockPriceService, StockPriceServiceError


class TestHSAErrorHandling:
    """Test HSA account error handling."""

    def test_hsa_negative_balance_error(self):
        """Test HSA account creation with negative balance."""
        with pytest.raises(HSABalanceValidationError) as exc_info:
            HSAAccount(
                id="test-id",
                name="Test HSA",
                institution="Test Bank",
                account_type=AccountType.HSA,
                created_date=datetime.now(),
                last_updated=datetime.now(),
                current_balance=-100.0,
                cash_balance=-100.0,
                investment_balance=0.0
            )

        error = exc_info.value
        assert error.code == "HSA_003"
        assert "current_balance" in error.message
        assert error.user_action is not None

    def test_hsa_balance_mismatch_error(self):
        """Test HSA account with mismatched balance components."""
        with pytest.raises(HSABalanceMismatchError) as exc_info:
            HSAAccount(
                id="test-id",
                name="Test HSA",
                institution="Test Bank",
                account_type=AccountType.HSA,
                created_date=datetime.now(),
                last_updated=datetime.now(),
                current_balance=1000.0,
                cash_balance=500.0,
                investment_balance=400.0  # Should be 500 to match total
            )

        error = exc_info.value
        assert error.code == "HSA_004"
        assert "Balance mismatch" in error.message

    def test_hsa_contribution_limit_exceeded(self):
        """Test HSA contribution limit validation."""
        with pytest.raises(HSAContributionValidationError) as exc_info:
            HSAAccount(
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
                current_year_contributions=3500.0  # Exceeds limit
            )

        error = exc_info.value
        assert error.code == "HSA_005"
        assert "exceed annual limit" in error.message

    def test_hsa_validate_contribution_success(self):
        """Test successful HSA contribution validation."""
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
            current_year_contributions=1000.0
        )

        # Should not raise any exception
        hsa.validate_contribution(1500.0)

    def test_hsa_validate_contribution_exceeds_limit(self):
        """Test HSA contribution validation when exceeding limit."""
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
            current_year_contributions=2500.0
        )

        with pytest.raises(HSAContributionLimitError) as exc_info:
            hsa.validate_contribution(1000.0)  # Would exceed limit by 500

        error = exc_info.value
        assert error.code == "HSA_002"
        assert "exceeds remaining capacity" in error.message

    def test_hsa_validate_balance_update_success(self):
        """Test successful HSA balance update validation."""
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=1000.0,
            cash_balance=1000.0,
            investment_balance=0.0
        )

        # Should not raise any exception
        hsa.validate_balance_update(1500.0, 800.0, 700.0)

    def test_hsa_validate_balance_update_mismatch(self):
        """Test HSA balance update validation with mismatch."""
        hsa = HSAAccount(
            id="test-id",
            name="Test HSA",
            institution="Test Bank",
            account_type=AccountType.HSA,
            created_date=datetime.now(),
            last_updated=datetime.now(),
            current_balance=1000.0,
            cash_balance=1000.0,
            investment_balance=0.0
        )

        with pytest.raises(HSABalanceMismatchError):
            hsa.validate_balance_update(1500.0, 800.0, 600.0)  # 800 + 600 != 1500


class TestWatchlistErrorHandling:
    """Test watchlist error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db_service = Mock()
        self.mock_stock_service = Mock()
        self.watchlist_service = WatchlistService(self.mock_db_service, self.mock_stock_service)

    def test_watchlist_duplicate_error(self):
        """Test adding duplicate stock to watchlist."""
        # Mock existing watchlist with AAPL
        existing_item = WatchlistItem.create_new("AAPL", "Apple Inc.")
        self.watchlist_service.get_watchlist = Mock(return_value=[existing_item])

        with pytest.raises(WatchlistDuplicateError) as exc_info:
            self.watchlist_service.add_stock("AAPL", "Duplicate Apple")

        error = exc_info.value
        assert error.code == "WATCH_002"
        assert "already in your watchlist" in error.message

    def test_watchlist_limit_exceeded_error(self):
        """Test watchlist size limit exceeded."""
        # Mock watchlist at capacity
        existing_items = [WatchlistItem.create_new(f"STOCK{i}", f"Stock {i}") for i in range(50)]
        self.watchlist_service.get_watchlist = Mock(return_value=existing_items)

        with pytest.raises(WatchlistLimitExceededError) as exc_info:
            self.watchlist_service.add_stock("NEWSTOCK", "New Stock", max_watchlist_size=50)

        error = exc_info.value
        assert error.code == "WATCH_004"
        assert "limit of 50 stocks exceeded" in error.message

    def test_stock_validation_error_invalid_format(self):
        """Test stock symbol validation with invalid format."""
        self.watchlist_service.get_watchlist = Mock(return_value=[])

        with pytest.raises(StockValidationError) as exc_info:
            self.watchlist_service.add_stock("INVALID_SYMBOL_TOO_LONG", "Invalid symbol")

        error = exc_info.value
        assert error.code == "STOCK_005"
        assert "Invalid stock symbol" in error.message

    def test_stock_validation_error_not_found(self):
        """Test stock symbol validation when symbol not found."""
        self.watchlist_service.get_watchlist = Mock(return_value=[])
        self.mock_stock_service.get_current_price.side_effect = StockPriceServiceError("Symbol not found")

        with pytest.raises(StockValidationError) as exc_info:
            self.watchlist_service.add_stock("NOTFOUND", "Non-existent stock")

        error = exc_info.value
        assert error.code == "STOCK_005"
        assert "Symbol not found" in error.message

    def test_watchlist_price_update_partial_failure(self):
        """Test watchlist price update with partial failures."""
        # Mock watchlist with multiple items
        items = [
            WatchlistItem.create_new("AAPL", "Apple"),
            WatchlistItem.create_new("GOOGL", "Google"),
            WatchlistItem.create_new("INVALID", "Invalid Stock")
        ]
        self.watchlist_service.get_watchlist = Mock(return_value=items)

        # Mock price service to return mixed results
        from services.stock_prices import PriceUpdateResult
        mock_results = {
            "AAPL": PriceUpdateResult("AAPL", True, 150.0, None, datetime.now()),
            "GOOGL": PriceUpdateResult("GOOGL", True, 2500.0, None, datetime.now()),
            "INVALID": PriceUpdateResult("INVALID", False, None, "Symbol not found", datetime.now())
        }
        self.mock_stock_service.get_batch_prices.return_value = mock_results

        # Mock storage method
        self.watchlist_service._store_watchlist_item = Mock()

        result = self.watchlist_service.update_prices()

        assert result['success'] is True
        assert result['summary']['total_items'] == 3
        assert result['summary']['successful_updates'] == 2
        assert result['summary']['failed_updates'] == 1
        assert "INVALID" in result['summary']['failed_symbols']

    def test_watchlist_price_update_complete_failure(self):
        """Test watchlist price update with complete failure."""
        items = [WatchlistItem.create_new("AAPL", "Apple")]
        self.watchlist_service.get_watchlist = Mock(return_value=items)

        # Mock stock service to raise exception
        self.mock_stock_service.get_batch_prices.side_effect = Exception("Network error")

        with pytest.raises(WatchlistServiceError) as exc_info:
            self.watchlist_service.update_prices()

        assert "Failed to fetch stock prices" in str(exc_info.value)


class TestStockPriceErrorHandling:
    """Test stock price service error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.stock_service = StockPriceService()

    @patch('yfinance.Ticker')
    def test_stock_not_found_error(self, mock_ticker):
        """Test stock price fetch for non-existent symbol."""
        # Mock yfinance to return empty history
        mock_ticker_instance = Mock()
        mock_ticker_instance.history.return_value.empty = True
        mock_ticker_instance.info = {}
        mock_ticker.return_value = mock_ticker_instance

        with pytest.raises(StockPriceServiceError) as exc_info:
            self.stock_service.get_current_price("NOTFOUND")

        assert "No data available" in str(exc_info.value)

    @patch('yfinance.Ticker')
    def test_stock_price_network_timeout(self, mock_ticker):
        """Test stock price fetch with network timeout."""
        # Mock yfinance to raise timeout exception
        mock_ticker.side_effect = Exception("Connection timeout")

        with pytest.raises(StockPriceServiceError) as exc_info:
            self.stock_service.get_current_price("AAPL")

        assert "Network timeout while fetching price" in str(exc_info.value)

    @patch('yfinance.Ticker')
    def test_stock_price_invalid_symbol_format(self, mock_ticker):
        """Test stock price fetch with invalid symbol format."""
        with pytest.raises(StockPriceServiceError) as exc_info:
            self.stock_service.get_current_price("INVALID_SYMBOL_TOO_LONG")

        assert "Invalid symbol format" in str(exc_info.value)

    @patch('yfinance.Ticker')
    def test_stock_price_retry_mechanism(self, mock_ticker):
        """Test stock price fetch retry mechanism."""
        # Mock yfinance to fail twice then succeed
        mock_ticker_instance = Mock()
        # Create a proper mock for the successful history call
        successful_hist = Mock()
        successful_hist.empty = False
        successful_hist.__getitem__ = Mock(return_value=Mock(iloc=Mock(__getitem__=lambda x, y: 150.0)))

        mock_ticker_instance.history.side_effect = [
            Exception("Temporary error"),
            Exception("Another temporary error"),
            successful_hist
        ]
        mock_ticker.return_value = mock_ticker_instance

        # Should succeed after retries
        price = self.stock_service.get_current_price("AAPL")
        assert price == 150.0

        # Verify it tried 3 times
        assert mock_ticker_instance.history.call_count == 3


class TestAPIErrorHandling:
    """Test API endpoint error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        # This would typically use a test client
        # For now, we'll test the error handling logic directly
        pass

    def test_watchlist_api_invalid_json(self):
        """Test watchlist API with invalid JSON."""
        from services.error_handler import ValidationError

        # This would be tested with actual Flask test client
        # Here we verify the error types are properly defined
        error = ValidationError(
            message="Request must be JSON",
            code="VAL_001",
            user_action="Please send request with Content-Type: application/json"
        )

        assert error.code == "VAL_001"
        assert error.error_type.value == "VALIDATION"
        assert error.user_action is not None

    def test_watchlist_api_missing_symbol(self):
        """Test watchlist API with missing symbol."""
        from services.error_handler import MissingFieldError

        error = MissingFieldError('symbol')

        assert error.code == "VAL_002"
        assert "symbol" in error.message

    def test_hsa_api_validation_errors(self):
        """Test HSA API validation error responses."""
        from services.error_handler import HSAContributionLimitError

        error = HSAContributionLimitError(1000.0, 500.0)
        error_dict = error.to_dict()

        assert error_dict['error'] is True
        assert error_dict['type'] == "VALIDATION"
        assert error_dict['code'] == "HSA_002"
        assert error_dict['recoverable'] is True
        assert "exceeds remaining capacity" in error_dict['message']


class TestErrorRecoveryAndGracefulDegradation:
    """Test error recovery and graceful degradation scenarios."""

    def test_watchlist_partial_price_update_recovery(self):
        """Test recovery from partial price update failures."""
        # This tests the graceful degradation when some prices fail to update
        # but the operation continues for successful ones

        mock_db_service = Mock()
        mock_stock_service = Mock()
        watchlist_service = WatchlistService(mock_db_service, mock_stock_service)

        # Mock watchlist with items
        items = [
            WatchlistItem.create_new("AAPL", "Apple"),
            WatchlistItem.create_new("FAIL", "Failing Stock")
        ]
        watchlist_service.get_watchlist = Mock(return_value=items)

        # Mock mixed results
        from services.stock_prices import PriceUpdateResult
        mock_results = {
            "AAPL": PriceUpdateResult("AAPL", True, 150.0, None, datetime.now()),
            "FAIL": PriceUpdateResult("FAIL", False, None, "Network error", datetime.now())
        }
        mock_stock_service.get_batch_prices.return_value = mock_results

        # Mock storage to succeed for AAPL
        watchlist_service._store_watchlist_item = Mock()

        result = watchlist_service.update_prices()

        # Should succeed overall but report partial failures
        assert result['success'] is True
        assert result['summary']['successful_updates'] == 1
        assert result['summary']['failed_updates'] == 1
        assert "AAPL" in result['summary']['successful_symbols']
        assert "FAIL" in result['summary']['failed_symbols']

    def test_stock_price_service_graceful_degradation(self):
        """Test stock price service graceful degradation."""
        stock_service = StockPriceService()

        # Test batch operation with mixed results
        with patch('yfinance.Ticker') as mock_ticker:
            # Mock different behaviors for different symbols
            def ticker_side_effect(symbol):
                mock_instance = Mock()
                if symbol == "AAPL":
                    successful_hist = Mock()
                    successful_hist.empty = False
                    successful_hist.__getitem__ = Mock(return_value=Mock(iloc=Mock(__getitem__=lambda x, y: 150.0)))
                    mock_instance.history.return_value = successful_hist
                else:  # FAIL symbol
                    mock_instance.history.return_value.empty = True
                return mock_instance

            mock_ticker.side_effect = ticker_side_effect

            results = stock_service.get_batch_prices(["AAPL", "FAIL"])

            assert len(results) == 2
            assert results["AAPL"].success is True
            assert results["AAPL"].price == 150.0
            assert results["FAIL"].success is False
            assert results["FAIL"].error is not None


if __name__ == "__main__":
    pytest.main([__file__])