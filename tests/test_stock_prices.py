"""
Unit tests for StockPriceService with mocked yfinance responses.

Tests cover:
- Individual stock price fetching
- Batch price fetching with rate limiting
- Stock position updates with current prices
- Error handling and retry logic
- Rate limiting functionality
"""

import pytest
import pandas as pd
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import time

from services.stock_prices import StockPriceService, PriceUpdateResult, StockPriceServiceError


class TestStockPriceService:
    """Test suite for StockPriceService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = StockPriceService(rate_limit_delay=0.1, max_retries=2)

    @patch('services.stock_prices.yf.Ticker')
    def test_get_current_price_success(self, mock_ticker):
        """Test successful price fetching for a single symbol"""
        # Mock yfinance response
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        # Create mock price data
        price_data = pd.DataFrame({
            'Close': [150.25]
        }, index=[datetime.now()])
        mock_ticker_instance.history.return_value = price_data

        # Test the service
        price = self.service.get_current_price('AAPL')

        assert price == 150.25
        mock_ticker.assert_called_once_with('AAPL')
        mock_ticker_instance.history.assert_called_once_with(period="1d")

    @patch('services.stock_prices.yf.Ticker')
    def test_get_current_price_empty_data(self, mock_ticker):
        """Test handling of empty data response"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.history.return_value = pd.DataFrame()

        with pytest.raises(StockPriceServiceError, match="No data available for symbol: AAPL"):
            self.service.get_current_price('AAPL')

    @patch('services.stock_prices.yf.Ticker')
    def test_get_current_price_invalid_price(self, mock_ticker):
        """Test handling of invalid price data"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        # Mock negative price
        price_data = pd.DataFrame({
            'Close': [-10.0]
        }, index=[datetime.now()])
        mock_ticker_instance.history.return_value = price_data

        with pytest.raises(StockPriceServiceError, match="Invalid price received for AAPL: -10.0"):
            self.service.get_current_price('AAPL')

    def test_get_current_price_invalid_symbol(self):
        """Test handling of invalid symbol input"""
        with pytest.raises(StockPriceServiceError, match="Invalid symbol: None"):
            self.service.get_current_price(None)

        with pytest.raises(StockPriceServiceError, match="Invalid symbol: "):
            self.service.get_current_price("")

        with pytest.raises(StockPriceServiceError, match="Invalid symbol: 123"):
            self.service.get_current_price(123)

    @patch('services.stock_prices.yf.Ticker')
    def test_get_current_price_with_retries(self, mock_ticker):
        """Test retry logic on API failures"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        # First call fails, second succeeds
        price_data = pd.DataFrame({
            'Close': [100.50]
        }, index=[datetime.now()])

        mock_ticker_instance.history.side_effect = [
            Exception("Network error"),
            price_data
        ]

        price = self.service.get_current_price('MSFT')
        assert price == 100.50
        assert mock_ticker_instance.history.call_count == 2

    @patch('services.stock_prices.yf.Ticker')
    def test_get_current_price_max_retries_exceeded(self, mock_ticker):
        """Test behavior when max retries are exceeded"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.history.side_effect = Exception("Persistent error")

        with pytest.raises(StockPriceServiceError, match="Failed to fetch price for GOOGL after 2 attempts"):
            self.service.get_current_price('GOOGL')

        assert mock_ticker_instance.history.call_count == 2

    @patch('services.stock_prices.yf.Ticker')
    def test_get_batch_prices_success(self, mock_ticker):
        """Test successful batch price fetching"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        # Mock different prices for different symbols
        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            prices = {
                'AAPL': 150.25,
                'GOOGL': 2500.75,
                'MSFT': 300.50
            }
            return pd.DataFrame({
                'Close': [prices.get(symbol, 100.0)]
            }, index=[datetime.now()])

        mock_ticker_instance.history.side_effect = mock_history

        symbols = ['AAPL', 'GOOGL', 'MSFT']
        results = self.service.get_batch_prices(symbols)

        assert len(results) == 3
        assert all(result.success for result in results.values())
        assert results['AAPL'].price == 150.25
        assert results['GOOGL'].price == 2500.75
        assert results['MSFT'].price == 300.50
        assert all(isinstance(result.timestamp, datetime) for result in results.values())

    @patch('services.stock_prices.yf.Ticker')
    def test_get_batch_prices_mixed_results(self, mock_ticker):
        """Test batch fetching with some successes and some failures"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            if symbol == 'INVALID':
                raise Exception("Invalid symbol")
            return pd.DataFrame({
                'Close': [100.0]
            }, index=[datetime.now()])

        mock_ticker_instance.history.side_effect = mock_history

        symbols = ['AAPL', 'INVALID', 'MSFT']
        results = self.service.get_batch_prices(symbols)

        assert len(results) == 3
        assert results['AAPL'].success is True
        assert results['INVALID'].success is False
        assert results['MSFT'].success is True
        assert 'Invalid symbol' in results['INVALID'].error

    def test_get_batch_prices_empty_list(self):
        """Test batch fetching with empty symbol list"""
        results = self.service.get_batch_prices([])
        assert results == {}

    def test_get_batch_prices_deduplication(self):
        """Test that duplicate symbols are deduplicated"""
        with patch.object(self.service, 'get_current_price', return_value=100.0) as mock_get_price:
            symbols = ['AAPL', 'aapl', 'AAPL', 'MSFT']
            results = self.service.get_batch_prices(symbols)

            # Should only call get_current_price twice (AAPL and MSFT)
            assert mock_get_price.call_count == 2
            assert len(results) == 2
            assert 'AAPL' in results
            assert 'MSFT' in results

    @patch('services.stock_prices.yf.Ticker')
    def test_update_stock_positions_success(self, mock_ticker):
        """Test updating stock positions with current prices"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            prices = {'AAPL': 150.0, 'GOOGL': 2500.0}
            return pd.DataFrame({
                'Close': [prices.get(symbol, 100.0)]
            }, index=[datetime.now()])

        mock_ticker_instance.history.side_effect = mock_history

        positions = [
            {
                'symbol': 'AAPL',
                'shares': 100,
                'purchase_price': 140.0
            },
            {
                'symbol': 'GOOGL',
                'shares': 50,
                'purchase_price': 2400.0
            }
        ]

        updated_positions = self.service.update_stock_positions(positions)

        assert len(updated_positions) == 2

        # Check AAPL position
        aapl_pos = updated_positions[0]
        assert aapl_pos['current_price'] == 150.0
        assert aapl_pos['current_value'] == 15000.0  # 150 * 100
        assert aapl_pos['unrealized_gain_loss'] == 1000.0  # 15000 - 14000
        assert aapl_pos['unrealized_gain_loss_pct'] == pytest.approx(7.14, rel=1e-2)

        # Check GOOGL position
        googl_pos = updated_positions[1]
        assert googl_pos['current_price'] == 2500.0
        assert googl_pos['current_value'] == 125000.0  # 2500 * 50
        assert googl_pos['unrealized_gain_loss'] == 5000.0  # 125000 - 120000
        assert googl_pos['unrealized_gain_loss_pct'] == pytest.approx(4.17, rel=1e-2)

    def test_update_stock_positions_empty_list(self):
        """Test updating empty positions list"""
        updated_positions = self.service.update_stock_positions([])
        assert updated_positions == []

    def test_update_stock_positions_missing_symbol(self):
        """Test updating positions with missing symbol"""
        positions = [
            {'shares': 100, 'purchase_price': 140.0},  # No symbol
            {'symbol': '', 'shares': 50, 'purchase_price': 2400.0}  # Empty symbol
        ]

        updated_positions = self.service.update_stock_positions(positions)

        # Positions should be returned unchanged
        assert len(updated_positions) == 2
        assert updated_positions[0] == positions[0]
        assert updated_positions[1] == positions[1]

    @patch('services.stock_prices.time.sleep')
    def test_rate_limiting(self, mock_sleep):
        """Test rate limiting between API calls"""
        service = StockPriceService(rate_limit_delay=1.0)

        # Simulate multiple calls
        service._enforce_rate_limit()
        service._enforce_rate_limit()

        # Should have called sleep once
        mock_sleep.assert_called_once()

    def test_is_market_open_weekend(self):
        """Test market open check for weekends"""
        with patch('services.stock_prices.datetime') as mock_datetime:
            # Mock Saturday
            saturday = datetime(2023, 10, 7, 10, 0)  # Saturday
            mock_datetime.now.return_value = saturday

            assert self.service.is_market_open() is False

    def test_is_market_open_weekday_during_hours(self):
        """Test market open check during market hours"""
        with patch('services.stock_prices.datetime') as mock_datetime:
            # Mock Tuesday at 2 PM
            tuesday = datetime(2023, 10, 3, 14, 0)  # Tuesday 2 PM
            mock_datetime.now.return_value = tuesday

            assert self.service.is_market_open() is True

    @patch('services.stock_prices.yf.Ticker')
    def test_get_price_with_metadata_success(self, mock_ticker):
        """Test getting price with additional metadata"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        price_data = pd.DataFrame({
            'Close': [150.25]
        }, index=[datetime.now()])
        mock_ticker_instance.history.return_value = price_data

        with patch.object(self.service, 'is_market_open', return_value=True):
            result = self.service.get_price_with_metadata('AAPL')

        assert result['symbol'] == 'AAPL'
        assert result['price'] == 150.25
        assert result['success'] is True
        assert result['market_open'] is True
        assert result['error'] is None
        assert isinstance(result['timestamp'], datetime)

    @patch('services.stock_prices.yf.Ticker')
    def test_get_price_with_metadata_failure(self, mock_ticker):
        """Test getting price metadata when price fetch fails"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance
        mock_ticker_instance.history.return_value = pd.DataFrame()  # Empty data

        with patch.object(self.service, 'is_market_open', return_value=False):
            result = self.service.get_price_with_metadata('INVALID')

        assert result['symbol'] == 'INVALID'
        assert result['price'] is None
        assert result['success'] is False
        assert result['market_open'] is False
        assert 'No data available' in result['error']
        assert isinstance(result['timestamp'], datetime)


class TestPriceUpdateResult:
    """Test suite for PriceUpdateResult dataclass"""

    def test_price_update_result_creation(self):
        """Test creating PriceUpdateResult instances"""
        # Success result
        success_result = PriceUpdateResult(
            symbol='AAPL',
            success=True,
            price=150.25,
            timestamp=datetime.now()
        )

        assert success_result.symbol == 'AAPL'
        assert success_result.success is True
        assert success_result.price == 150.25
        assert success_result.error is None

        # Failure result
        failure_result = PriceUpdateResult(
            symbol='INVALID',
            success=False,
            error='Symbol not found'
        )

        assert failure_result.symbol == 'INVALID'
        assert failure_result.success is False
        assert failure_result.price is None
        assert failure_result.error == 'Symbol not found'


class TestStockPriceServiceError:
    """Test suite for StockPriceServiceError exception"""

    def test_exception_creation(self):
        """Test creating StockPriceServiceError"""
        error = StockPriceServiceError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)


# Integration-style tests with more realistic scenarios
class TestStockPriceServiceIntegration:
    """Integration-style tests for StockPriceService"""

    def setup_method(self):
        """Set up test fixtures"""
        self.service = StockPriceService(rate_limit_delay=0.01)  # Faster for tests

    @patch('services.stock_prices.yf.Ticker')
    def test_realistic_portfolio_update(self, mock_ticker):
        """Test updating a realistic portfolio with multiple positions"""
        mock_ticker_instance = Mock()
        mock_ticker.return_value = mock_ticker_instance

        # Mock realistic stock prices
        def mock_history(period):
            symbol = mock_ticker.call_args[0][0]
            prices = {
                'AAPL': 175.43,
                'GOOGL': 2847.52,
                'MSFT': 378.85,
                'AMZN': 3342.88,
                'TSLA': 248.42
            }
            return pd.DataFrame({
                'Close': [prices.get(symbol, 100.0)]
            }, index=[datetime.now()])

        mock_ticker_instance.history.side_effect = mock_history

        # Realistic portfolio positions
        positions = [
            {'symbol': 'AAPL', 'shares': 50, 'purchase_price': 165.20},
            {'symbol': 'GOOGL', 'shares': 10, 'purchase_price': 2650.00},
            {'symbol': 'MSFT', 'shares': 25, 'purchase_price': 350.75},
            {'symbol': 'AMZN', 'shares': 5, 'purchase_price': 3100.00},
            {'symbol': 'TSLA', 'shares': 15, 'purchase_price': 275.30}
        ]

        updated_positions = self.service.update_stock_positions(positions)

        assert len(updated_positions) == 5

        # Verify all positions have been updated with current prices
        for pos in updated_positions:
            assert 'current_price' in pos
            assert 'current_value' in pos
            assert 'unrealized_gain_loss' in pos
            assert 'unrealized_gain_loss_pct' in pos
            assert pos['current_price'] > 0

        # Check specific calculations for AAPL
        aapl_pos = next(p for p in updated_positions if p['symbol'] == 'AAPL')
        expected_current_value = 175.43 * 50  # 8771.50
        expected_cost_basis = 165.20 * 50     # 8260.00
        expected_gain = expected_current_value - expected_cost_basis  # 511.50

        assert aapl_pos['current_value'] == pytest.approx(expected_current_value, rel=1e-6)
        assert aapl_pos['unrealized_gain_loss'] == pytest.approx(expected_gain, rel=1e-6)