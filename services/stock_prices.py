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

    def __init__(self, rate_limit_delay: float = 3.0, max_retries: int = 2):
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
        self._session = None

    def _enforce_rate_limit(self):
        """Enforce rate limiting between API requests"""
        if self.last_request_time is not None:
            elapsed = time.time() - self.last_request_time
            if elapsed < self.rate_limit_delay:
                sleep_time = self.rate_limit_delay - elapsed
                time.sleep(sleep_time)

        self.last_request_time = time.time()

    def _get_session(self):
        """Get or create a requests session for yfinance."""
        if self._session is None:
            import requests
            self._session = requests.Session()
            # Add headers to look more like a regular browser
            self._session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            })
        return self._session

    def _try_alternative_price_fetch(self, symbol: str) -> Optional[float]:
        """
        Try alternative methods to fetch stock price using free APIs.
        """
        # Method 1: Try Yahoo Finance direct API
        try:
            price = self._fetch_from_yahoo_direct(symbol)
            if price:
                return price
        except Exception as e:
            self.logger.warning(f"Yahoo direct API failed for {symbol}: {e}")

        # Method 2: Try Financial Modeling Prep (free tier)
        try:
            price = self._fetch_from_fmp(symbol)
            if price:
                return price
        except Exception as e:
            self.logger.warning(f"FMP API failed for {symbol}: {e}")

        return None

    def _fetch_from_yahoo_direct(self, symbol: str) -> Optional[float]:
        """Fetch price directly from Yahoo Finance API."""
        import requests

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'chart' in data and 'result' in data['chart'] and len(data['chart']['result']) > 0:
                    result = data['chart']['result'][0]
                    if 'meta' in result and 'regularMarketPrice' in result['meta']:
                        price = float(result['meta']['regularMarketPrice'])
                        if price > 0:
                            self.logger.info(f"Successfully fetched price from Yahoo direct for {symbol}: ${price:.2f}")
                            return price
        except Exception as e:
            self.logger.warning(f"Yahoo direct request failed for {symbol}: {e}")

        return None

    def _fetch_from_fmp(self, symbol: str) -> Optional[float]:
        """Fetch price from Financial Modeling Prep (free tier)."""
        import requests

        url = f"https://financialmodelingprep.com/api/v3/quote-short/{symbol}?apikey=demo"

        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data and len(data) > 0 and 'price' in data[0]:
                    price = float(data[0]['price'])
                    if price > 0:
                        self.logger.info(f"Successfully fetched price from FMP for {symbol}: ${price:.2f}")
                        return price
        except Exception as e:
            self.logger.warning(f"FMP request failed for {symbol}: {e}")

        return None

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

        # Basic symbol validation
        if not symbol.isalnum() or len(symbol) > 10 or len(symbol) < 1:
            raise StockPriceServiceError(f"Invalid symbol format: {symbol}")

        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()

                # Try alternative method first (less likely to be rate limited)
                price = self._try_alternative_price_fetch(symbol)
                if price:
                    return price

                # Fallback to yfinance with session
                session = self._get_session()
                ticker = yf.Ticker(symbol, session=session)

                # Method 1: Try historical data first (more reliable)
                periods_to_try = ["1d", "2d", "5d"]

                for period in periods_to_try:
                    try:
                        hist = ticker.history(period=period)
                        if not hist.empty:
                            price = float(hist['Close'].iloc[-1])
                            if price > 0:
                                self.logger.info(f"Successfully fetched price from {period} history for {symbol}: ${price:.2f}")
                                return price
                    except Exception as e:
                        self.logger.warning(f"Failed to fetch {period} data for {symbol}: {e}")
                        continue

                # Method 2: Try fast_info (newer yfinance feature)
                try:
                    fast_info = ticker.fast_info
                    if hasattr(fast_info, 'last_price') and fast_info.last_price:
                        price = float(fast_info.last_price)
                        if price > 0:
                            self.logger.info(f"Successfully fetched fast_info price for {symbol}: ${price:.2f}")
                            return price
                except Exception as e:
                    self.logger.warning(f"Failed to get fast_info for {symbol}: {e}")

                raise StockPriceServiceError(f"No valid price data available for symbol: {symbol}")

            except StockPriceServiceError:
                # Re-raise our custom errors without modification
                raise
            except Exception as e:
                error_msg = str(e).lower()

                # Categorize different types of errors
                if "not found" in error_msg or "invalid" in error_msg or "no data" in error_msg:
                    if attempt == self.max_retries - 1:
                        raise StockPriceServiceError(f"Symbol '{symbol}' not found or invalid")
                elif "timeout" in error_msg or "connection" in error_msg:
                    if attempt == self.max_retries - 1:
                        raise StockPriceServiceError(f"Network timeout while fetching price for {symbol}")
                elif "rate limit" in error_msg or "too many requests" in error_msg:
                    if attempt == self.max_retries - 1:
                        raise StockPriceServiceError(f"Rate limit exceeded for stock price API")
                else:
                    self.logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
                    if attempt == self.max_retries - 1:
                        raise StockPriceServiceError(f"Failed to fetch price for {symbol} after {self.max_retries} attempts: {str(e)}")

                # Brief delay before retry for transient errors
                if attempt < self.max_retries - 1:
                    time.sleep(min(2 ** attempt, 10))  # Exponential backoff, max 10 seconds

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