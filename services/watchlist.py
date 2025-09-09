"""
Watchlist service for managing stock watchlist functionality.

This service provides functionality to:
- Add and remove stocks from watchlist
- Validate stock symbols using yfinance integration
- Update stock prices in batch with error handling
- Manage encrypted watchlist data storage
"""

import json
import uuid
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime

from models.watchlist import WatchlistItem
from .database import DatabaseService
from .stock_prices import StockPriceService, PriceUpdateResult, StockPriceServiceError
from .error_handler import (
    DatabaseError, RecordNotFoundError, ValidationError, SystemError
)


class WatchlistServiceError(Exception):
    """Custom exception for watchlist service errors"""
    pass


class WatchlistService:
    """Service for managing stock watchlist operations"""

    def __init__(self, db_service: DatabaseService, stock_service: StockPriceService):
        """
        Initialize the watchlist service.

        Args:
            db_service: Database service for encrypted storage
            stock_service: Stock price service for price updates and validation
        """
        self.db_service = db_service
        self.stock_service = stock_service
        self.logger = logging.getLogger(__name__)

    def add_stock(self, symbol: str, notes: Optional[str] = None, max_watchlist_size: int = 50) -> str:
        """
        Add a stock to the watchlist with symbol validation.

        Args:
            symbol: Stock ticker symbol
            notes: Optional notes about the stock
            max_watchlist_size: Maximum number of stocks allowed in watchlist

        Returns:
            ID of the created watchlist item

        Raises:
            ValidationError: If symbol validation fails
            WatchlistServiceError: If operation fails
        """
        from .error_handler import (
            WatchlistDuplicateError, WatchlistLimitExceededError,
            StockValidationError, ValidationError
        )

        if not symbol or not isinstance(symbol, str):
            raise ValidationError("Stock symbol cannot be empty", "VAL_SYMBOL_EMPTY")

        symbol = symbol.upper().strip()

        # Basic symbol format validation
        if not symbol.isalnum() or len(symbol) > 10 or len(symbol) < 1:
            raise StockValidationError(symbol, "Symbol must be 1-10 alphanumeric characters")

        # Check watchlist size limit
        existing_items = self.get_watchlist()
        if len(existing_items) >= max_watchlist_size:
            raise WatchlistLimitExceededError(max_watchlist_size)

        # Check if symbol already exists
        for item in existing_items:
            if item.symbol == symbol:
                raise WatchlistDuplicateError(symbol)

        # Validate symbol using yfinance (with fallback for network issues)
        try:
            # Try to fetch current price to validate symbol
            self.stock_service.get_current_price(symbol)
            self.logger.info(f"Symbol {symbol} validated successfully")
        except StockPriceServiceError as e:
            error_msg = str(e).lower()
            if "not found" in error_msg or "invalid" in error_msg:
                raise StockValidationError(symbol, "Symbol not found in stock market data")
            elif "timeout" in error_msg or "connection" in error_msg:
                # For network issues, allow adding but log a warning
                self.logger.warning(f"Could not validate {symbol} due to network issues, adding anyway: {str(e)}")
            elif "rate limit" in error_msg:
                # For rate limiting, allow adding but log a warning
                self.logger.warning(f"Rate limit exceeded while validating {symbol}, adding anyway: {str(e)}")
            else:
                # For other errors, allow adding but log a warning
                self.logger.warning(f"Could not validate {symbol}, adding anyway: {str(e)}")

        # Create new watchlist item
        try:
            item = WatchlistItem.create_new(symbol, notes)
        except Exception as e:
            raise ValidationError(f"Failed to create watchlist item: {str(e)}", "VAL_ITEM_CREATE")

        # Store in database
        try:
            self._store_watchlist_item(item)
            self.logger.info(f"Added {symbol} to watchlist with ID {item.id}")
            return item.id
        except Exception as e:
            self.logger.error(f"Database error adding {symbol} to watchlist: {str(e)}")
            raise WatchlistServiceError(f"Failed to save stock to watchlist: {str(e)}")

    def remove_stock(self, symbol: str) -> bool:
        """
        Remove a stock from the watchlist.

        Args:
            symbol: Stock ticker symbol to remove

        Returns:
            True if stock was removed, False if not found

        Raises:
            WatchlistServiceError: If removal fails
        """
        if not symbol or not isinstance(symbol, str):
            return False

        symbol = symbol.upper().strip()

        try:
            connection = self.db_service.connect()
            cursor = connection.cursor()

            # Find the item by symbol
            cursor.execute('SELECT id FROM watchlist WHERE symbol = ?', (symbol,))
            row = cursor.fetchone()

            if not row:
                self.logger.warning(f"Stock {symbol} not found in watchlist")
                return False

            # Delete the item
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol,))
            connection.commit()

            self.logger.info(f"Removed {symbol} from watchlist")
            return True

        except Exception as e:
            raise WatchlistServiceError(f"Failed to remove stock from watchlist: {str(e)}")

    def get_watchlist(self) -> List[WatchlistItem]:
        """
        Retrieve all watchlist items.

        Returns:
            List of WatchlistItem objects

        Raises:
            WatchlistServiceError: If retrieval fails
        """
        try:
            # Ensure watchlist table exists
            self._ensure_watchlist_table()

            connection = self.db_service.connect()
            cursor = connection.cursor()

            cursor.execute('''
                SELECT id, symbol, encrypted_data, added_date, last_price_update, is_demo
                FROM watchlist
                ORDER BY symbol
            ''')

            items = []
            for row in cursor.fetchall():
                try:
                    # Decrypt the data
                    encrypted_data = row['encrypted_data']
                    decrypted_data = json.loads(self.db_service.encryption_service.decrypt(encrypted_data))

                    # Create WatchlistItem from decrypted data
                    item_data = {
                        'id': row['id'],
                        'symbol': row['symbol'],
                        'added_date': datetime.fromtimestamp(row['added_date']).isoformat(),
                        'last_price_update': datetime.fromtimestamp(row['last_price_update']).isoformat() if row['last_price_update'] else None
                    }
                    item_data.update(decrypted_data)

                    item = WatchlistItem.from_dict(item_data)
                    items.append(item)

                except Exception as e:
                    self.logger.error(f"Failed to decrypt watchlist item {row['id']}: {str(e)}")
                    continue

            return items

        except Exception as e:
            raise WatchlistServiceError(f"Failed to retrieve watchlist: {str(e)}")

    def get_stock_details(self, symbol: str) -> Optional[WatchlistItem]:
        """
        Get details for a specific stock in the watchlist.

        Args:
            symbol: Stock ticker symbol

        Returns:
            WatchlistItem if found, None otherwise

        Raises:
            WatchlistServiceError: If retrieval fails
        """
        if not symbol or not isinstance(symbol, str):
            return None

        symbol = symbol.upper().strip()

        watchlist = self.get_watchlist()
        for item in watchlist:
            if item.symbol == symbol:
                return item

        return None

    def update_prices(self) -> Dict[str, Any]:
        """
        Update prices for all watchlist items in batch with comprehensive error handling.

        Returns:
            Dictionary with update results and detailed error information

        Raises:
            WatchlistServiceError: If batch update fails completely
        """
        from .error_handler import WatchlistPriceUpdateError

        try:
            watchlist = self.get_watchlist()
            if not watchlist:
                return {
                    'success': True,
                    'results': {},
                    'summary': {
                        'total_items': 0,
                        'successful_updates': 0,
                        'failed_updates': 0,
                        'successful_symbols': [],
                        'failed_symbols': []
                    }
                }

            # Extract symbols for batch price update
            symbols = [item.symbol for item in watchlist]
            self.logger.info(f"Starting price update for {len(symbols)} watchlist items")

            # Fetch prices in batch
            try:
                price_results = self.stock_service.get_batch_prices(symbols)
            except Exception as e:
                self.logger.error(f"Batch price fetch failed: {str(e)}")
                raise WatchlistServiceError(f"Failed to fetch stock prices: {str(e)}")

            # Update each item with new price data
            update_results = {}
            successful_symbols = []
            failed_symbols = []
            database_errors = []

            for item in watchlist:
                symbol = item.symbol
                price_result = price_results.get(symbol)

                if price_result and price_result.success:
                    try:
                        # Calculate daily change if we have previous price
                        daily_change = None
                        daily_change_percent = None

                        if item.current_price is not None and price_result.price is not None:
                            daily_change = price_result.price - item.current_price
                            if item.current_price > 0:
                                daily_change_percent = (daily_change / item.current_price) * 100

                        # Update item with new price data
                        item.update_price(
                            current_price=price_result.price,
                            daily_change=daily_change,
                            daily_change_percent=daily_change_percent
                        )

                        # Store updated item
                        self._store_watchlist_item(item)
                        update_results[symbol] = {
                            'success': True,
                            'price': price_result.price,
                            'daily_change': daily_change,
                            'daily_change_percent': daily_change_percent
                        }
                        successful_symbols.append(symbol)
                        self.logger.info(f"Updated price for {symbol}: ${price_result.price:.2f}")

                    except Exception as e:
                        # Database storage error
                        error_msg = f"Database error storing price for {symbol}: {str(e)}"
                        self.logger.error(error_msg)
                        database_errors.append(symbol)
                        update_results[symbol] = {
                            'success': False,
                            'error': 'database_error',
                            'error_message': str(e)
                        }
                        failed_symbols.append(symbol)

                else:
                    # Price fetch failed
                    error_msg = price_result.error if price_result else "Unknown error"
                    update_results[symbol] = {
                        'success': False,
                        'error': 'price_fetch_failed',
                        'error_message': error_msg
                    }
                    failed_symbols.append(symbol)
                    self.logger.warning(f"Failed to update price for {symbol}: {error_msg}")

            # Prepare summary
            total_items = len(symbols)
            successful_updates = len(successful_symbols)
            failed_updates = len(failed_symbols)

            summary = {
                'total_items': total_items,
                'successful_updates': successful_updates,
                'failed_updates': failed_updates,
                'successful_symbols': successful_symbols,
                'failed_symbols': failed_symbols,
                'database_errors': database_errors
            }

            # Log summary
            self.logger.info(f"Price update completed: {successful_updates}/{total_items} successful")

            if failed_symbols:
                self.logger.warning(f"Failed to update prices for: {', '.join(failed_symbols)}")

            # If more than half failed, consider it a significant issue
            if failed_updates > successful_updates and total_items > 1:
                self.logger.error(f"Majority of price updates failed ({failed_updates}/{total_items})")

            return {
                'success': True,
                'results': update_results,
                'summary': summary,
                'timestamp': datetime.now().isoformat()
            }

        except WatchlistServiceError:
            # Re-raise our custom errors
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during price update: {str(e)}")
            raise WatchlistServiceError(f"Failed to update watchlist prices: {str(e)}")

    def validate_symbol(self, symbol: str) -> bool:
        """
        Validate a stock symbol using yfinance.

        Args:
            symbol: Stock ticker symbol to validate

        Returns:
            True if symbol is valid, False otherwise
        """
        if not symbol or not isinstance(symbol, str):
            return False

        try:
            self.stock_service.get_current_price(symbol.upper().strip())
            return True
        except StockPriceServiceError:
            return False

    def get_watchlist_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for the watchlist.

        Returns:
            Dictionary with summary information
        """
        try:
            watchlist = self.get_watchlist()

            total_items = len(watchlist)
            items_with_prices = sum(1 for item in watchlist if item.has_price_data())
            items_with_stale_prices = sum(1 for item in watchlist if item.is_price_data_stale())

            # Calculate gain/loss statistics
            gainers = sum(1 for item in watchlist
                         if item.daily_change is not None and item.daily_change > 0)
            losers = sum(1 for item in watchlist
                        if item.daily_change is not None and item.daily_change < 0)

            return {
                'total_items': total_items,
                'items_with_prices': items_with_prices,
                'items_with_stale_prices': items_with_stale_prices,
                'gainers': gainers,
                'losers': losers,
                'last_updated': datetime.now()
            }

        except Exception as e:
            self.logger.error(f"Failed to generate watchlist summary: {str(e)}")
            return {
                'total_items': 0,
                'items_with_prices': 0,
                'items_with_stale_prices': 0,
                'gainers': 0,
                'losers': 0,
                'last_updated': datetime.now(),
                'error': str(e)
            }

    def _store_watchlist_item(self, item: WatchlistItem) -> None:
        """
        Store or update a watchlist item in the database.

        Args:
            item: WatchlistItem to store

        Raises:
            WatchlistServiceError: If storage fails
        """
        try:
            # Ensure watchlist table exists
            self._ensure_watchlist_table()

            # Prepare data for storage
            public_data = {
                'id': item.id,
                'symbol': item.symbol,
                'added_date': int(item.added_date.timestamp()),
                'last_price_update': int(item.last_price_update.timestamp()) if item.last_price_update else None
            }

            # Encrypt sensitive data (notes and price information)
            sensitive_data = {
                'notes': item.notes,
                'current_price': item.current_price,
                'daily_change': item.daily_change,
                'daily_change_percent': item.daily_change_percent
            }

            encrypted_data = self.db_service.encryption_service.encrypt(
                json.dumps(sensitive_data, default=str)
            )

            connection = self.db_service.connect()
            cursor = connection.cursor()

            # Use INSERT OR REPLACE to handle both create and update
            cursor.execute('''
                INSERT OR REPLACE INTO watchlist
                (id, symbol, encrypted_data, added_date, last_price_update, is_demo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                public_data['id'],
                public_data['symbol'],
                encrypted_data,
                public_data['added_date'],
                public_data['last_price_update'],
                False  # Default to non-demo
            ))

            connection.commit()

        except Exception as e:
            raise WatchlistServiceError(f"Failed to store watchlist item: {str(e)}")

    def _ensure_watchlist_table(self) -> None:
        """
        Ensure the watchlist table exists in the database.

        Raises:
            WatchlistServiceError: If table creation fails
        """
        try:
            connection = self.db_service.connect()
            cursor = connection.cursor()

            # Create watchlist table if it doesn't exist
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS watchlist (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    encrypted_data BLOB NOT NULL,
                    added_date INTEGER NOT NULL,
                    last_price_update INTEGER,
                    is_demo BOOLEAN DEFAULT FALSE
                )
            ''')

            # Create index for efficient symbol lookups
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist (symbol)')

            connection.commit()

        except Exception as e:
            raise WatchlistServiceError(f"Failed to ensure watchlist table exists: {str(e)}")

    def clear_watchlist(self) -> int:
        """
        Clear all items from the watchlist.

        Returns:
            Number of items removed

        Raises:
            WatchlistServiceError: If clearing fails
        """
        try:
            connection = self.db_service.connect()
            cursor = connection.cursor()

            # Count items before deletion
            cursor.execute('SELECT COUNT(*) FROM watchlist')
            count = cursor.fetchone()[0]

            # Delete all items
            cursor.execute('DELETE FROM watchlist')
            connection.commit()

            self.logger.info(f"Cleared {count} items from watchlist")
            return count

        except Exception as e:
            raise WatchlistServiceError(f"Failed to clear watchlist: {str(e)}")

    def add_demo_watchlist_items(self) -> List[str]:
        """
        Add demo watchlist items for demonstration purposes.

        Returns:
            List of IDs of created demo items

        Raises:
            WatchlistServiceError: If demo data creation fails
        """
        demo_stocks = [
            ('AAPL', 'Apple Inc. - Technology giant'),
            ('GOOGL', 'Alphabet Inc. - Search and cloud services'),
            ('MSFT', 'Microsoft Corporation - Software and cloud'),
            ('TSLA', 'Tesla Inc. - Electric vehicles and energy'),
            ('AMZN', 'Amazon.com Inc. - E-commerce and cloud'),
            ('NVDA', 'NVIDIA Corporation - Graphics and AI chips'),
            ('META', 'Meta Platforms Inc. - Social media'),
            ('NFLX', 'Netflix Inc. - Streaming entertainment')
        ]

        created_ids = []

        try:
            for symbol, notes in demo_stocks:
                # Check if already exists
                if self.get_stock_details(symbol):
                    continue

                # Create demo item
                item = WatchlistItem.create_new(symbol, notes)

                # Try to get current price for demo data
                try:
                    price = self.stock_service.get_current_price(symbol)
                    item.update_price(price)
                except StockPriceServiceError:
                    # If price fetch fails, continue without price data
                    pass

                # Store with demo flag
                self._store_demo_watchlist_item(item)
                created_ids.append(item.id)

            self.logger.info(f"Created {len(created_ids)} demo watchlist items")
            return created_ids

        except Exception as e:
            raise WatchlistServiceError(f"Failed to create demo watchlist items: {str(e)}")

    def _store_demo_watchlist_item(self, item: WatchlistItem) -> None:
        """
        Store a demo watchlist item in the database.

        Args:
            item: WatchlistItem to store as demo data
        """
        try:
            self._ensure_watchlist_table()

            public_data = {
                'id': item.id,
                'symbol': item.symbol,
                'added_date': int(item.added_date.timestamp()),
                'last_price_update': int(item.last_price_update.timestamp()) if item.last_price_update else None
            }

            sensitive_data = {
                'notes': item.notes,
                'current_price': item.current_price,
                'daily_change': item.daily_change,
                'daily_change_percent': item.daily_change_percent
            }

            encrypted_data = self.db_service.encryption_service.encrypt(
                json.dumps(sensitive_data, default=str)
            )

            connection = self.db_service.connect()
            cursor = connection.cursor()

            cursor.execute('''
                INSERT OR REPLACE INTO watchlist
                (id, symbol, encrypted_data, added_date, last_price_update, is_demo)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                public_data['id'],
                public_data['symbol'],
                encrypted_data,
                public_data['added_date'],
                public_data['last_price_update'],
                True  # Mark as demo data
            ))

            connection.commit()

        except Exception as e:
            raise WatchlistServiceError(f"Failed to store demo watchlist item: {str(e)}")