"""
Stock Price Service for fetching real-time stock prices using yfinance API.

This service provides functionality to:
- Fetch current stock prices for individual symbols
- Batch fetch prices for multiple symbols with rate limiting
- Update stock positions with current market prices
- Handle API errors and rate limiting gracefully
"""

import yfinance as yf
import time
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class PriceUpdateResult:
    """Result of a price update operation"""
    symbol: str
    success: bool
    price: Optional[float] = None
    error: Optional[str] = None
    timestamp: Optional[datetime] = None


class StockPriceServiceError(Exception):
    """Custom exception for stock price service errors"""
    pass


class StockPriceService:
    """Service for fetching stock prices using yfinance API"""

    def __init__(self, rate_limit_delay: float = 1.0, max_retries: int = 3):
        """
        Initialize the stock price service.

        Args:
            rate_limit_delay: Delay in seconds between API requests
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.last_request_time = None
        self.logger = logging.getLogger(__name__)

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests"""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def get_current_price(self, symbol: str) -> float:
        """
        Get current stock price for a single symbol.

        Args:
            symbol: Stock symbol (e.g., 'AAPL', 'GOOGL')

        Returns:
            Current stock price as float

        Raises:
            StockPriceServiceError: If unable to fetch price
        """
        if not symbol or not isinstance(symbol, str):
            raise StockPriceServiceError(f"Invalid symbol: {symbol}")

        symbol = symbol.upper().strip()

        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()

                ticker = yf.Ticker(symbol)
                hist = ticker.history(period="1d")

                if hist.empty:
                    raise StockPriceServiceError(f"No data available for symbol: {symbol}")

                price = float(hist['Close'].iloc[-1])

                if price <= 0:
                    raise StockPriceServiceError(f"Invalid price received for {symbol}: {price}")

                self.logger.info(f"Successfully fetched price for {symbol}: ${price:.2f}")
                return price

            except Exception as e:
                self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                if attempt == self.max_retries - 1:
                    raise StockPriceServiceError(f"Failed to fetch price for {symbol} after {self.max_retries} attempts: {str(e)}")
                time.sleep(1)  # Brief delay before retry

    def get_batch_prices(self, symbols: List[str]) -> Dict[str, PriceUpdateResult]:
        """
        Get current prices for multiple symbols with rate limiting.

        Args:
            symbols: List of stock symbols

        Returns:
            Dictionary mapping symbols to PriceUpdateResult objects
        """
        if not symbols:
            return {}

        # Clean and deduplicate symbols
        clean_symbols = list(set(s.upper().strip() for s in symbols if s and isinstance(s, str)))

        results = {}

        for symbol in clean_symbols:
            try:
                price = self.get_current_price(symbol)
                results[symbol] = PriceUpdateResult(
                    symbol=symbol,
                    success=True,
                    price=price,
                    timestamp=datetime.now()
                )
            except StockPriceServiceError as e:
                self.logger.error(f"Failed to fetch price for {symbol}: {str(e)}")
                results[symbol] = PriceUpdateResult(
                    symbol=symbol,
                    success=False,
                    error=str(e),
                    timestamp=datetime.now()
                )

        return results

    def update_stock_positions(self, positions: List[dict]) -> List[dict]:
        """
        Update stock positions with current market prices.

        Args:
            positions: List of position dictionaries with 'symbol' key

        Returns:
            List of updated position dictionaries with current_price and last_updated fields
        """
        if not positions:
            return []

        # Extract unique symbols from positions
        symbols = list(set(pos.get('symbol') for pos in positions if pos.get('symbol')))

        # Fetch current prices
        price_results = self.get_batch_prices(symbols)

        # Update positions with new prices
        updated_positions = []

        for position in positions:
            symbol = position.get('symbol')
            if not symbol:
                updated_positions.append(position)
                continue

            updated_position = position.copy()
            price_result = price_results.get(symbol.upper())

            if price_result and price_result.success:
                updated_position['current_price'] = price_result.price
                updated_position['last_updated'] = price_result.timestamp

                # Calculate unrealized gain/loss if purchase_price and shares are available
                if 'purchase_price' in position and 'shares' in position:
                    purchase_price = position['purchase_price']
                    shares = position['shares']
                    current_value = price_result.price * shares
                    cost_basis = purchase_price * shares
                    unrealized_gain_loss = current_value - cost_basis
                    unrealized_gain_loss_pct = (unrealized_gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

                    updated_position['current_value'] = current_value
                    updated_position['unrealized_gain_loss'] = unrealized_gain_loss
                    updated_position['unrealized_gain_loss_pct'] = unrealized_gain_loss_pct
            else:
                # Keep existing price if update failed
                self.logger.warning(f"Failed to update price for {symbol}, keeping existing data")

            updated_positions.append(updated_position)

        return updated_positions

    def is_market_open(self) -> bool:
        """
        Check if the stock market is currently open (basic implementation).

        Returns:
            True if market is likely open, False otherwise

        Note: This is a simplified check. For production use, consider
        using a more sophisticated market hours API.
        """
        now = datetime.now()

        # Check if it's a weekday (Monday = 0, Sunday = 6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        # Basic US market hours check (9:30 AM - 4:00 PM ET)
        # Note: This doesn't account for holidays or timezone differences
        market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
        market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)

        return market_open <= now <= market_close

    def get_price_with_metadata(self, symbol: str) -> Dict:
        """
        Get current price along with additional metadata.

        Args:
            symbol: Stock symbol

        Returns:
            Dictionary with price, timestamp, and market status
        """
        try:
            price = self.get_current_price(symbol)
            return {
                'symbol': symbol.upper(),
                'price': price,
                'timestamp': datetime.now(),
                'success': True,
                'market_open': self.is_market_open(),
                'error': None
            }
        except StockPriceServiceError as e:
            return {
                'symbol': symbol.upper(),
                'price': None,
                'timestamp': datetime.now(),
                'success': False,
                'market_open': self.is_market_open(),
                'error': str(e)
            }