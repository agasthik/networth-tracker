"""
Database service for encrypted SQLite operations in the networth tracker application.
Handles all database operations with encryption for sensitive financial data.
"""

import sqlite3
import json
import uuid
import os
import threading
from datetime import datetime
from typing import List, Optional, Dict, Any, Union
from pathlib import Path

from .encryption import EncryptionService
from .error_handler import (
    DatabaseError, DatabaseConnectionError, DatabaseCorruptionError,
    RecordNotFoundError, EncryptionError, DecryptionError, SystemError,
    FilePermissionError, DiskSpaceError
)
from .logging_config import get_logger, log_function_call, log_performance, with_logging_context

logger = get_logger(__name__)


class DatabaseService:
    """Service for encrypted SQLite database operations."""

    SCHEMA_VERSION = 5

    def __init__(self, db_path: str, encryption_service: EncryptionService):
        """
        Initialize database service.

        Args:
            db_path: Path to SQLite database file
            encryption_service: Initialized encryption service with derived key
        """
        self.db_path = db_path
        self.encryption_service = encryption_service
        self.connection: Optional[sqlite3.Connection] = None
        self._thread_local = threading.local()

    def connect(self) -> sqlite3.Connection:
        """
        Create database connection and initialize schema if needed.
        Uses thread-local storage to ensure each thread gets its own connection.

        Returns:
            SQLite connection object

        Raises:
            DatabaseConnectionError: If unable to connect to database
            FilePermissionError: If insufficient permissions to access database file
            DiskSpaceError: If insufficient disk space
        """
        # Check if we have a connection for this thread
        if not hasattr(self._thread_local, 'connection') or self._thread_local.connection is None:
            try:
                # Check if database directory exists and is writable
                db_dir = Path(self.db_path).parent
                if not db_dir.exists():
                    try:
                        db_dir.mkdir(parents=True, exist_ok=True)
                    except PermissionError:
                        raise FilePermissionError(
                            file_path=str(db_dir),
                            technical_details="Cannot create database directory"
                        )

                # Check disk space (at least 10MB required)
                if hasattr(os, 'statvfs'):  # Unix-like systems
                    stat = os.statvfs(db_dir)
                    free_space = stat.f_bavail * stat.f_frsize
                    if free_space < 10 * 1024 * 1024:  # 10MB
                        raise DiskSpaceError(
                            technical_details=f"Only {free_space / 1024 / 1024:.1f}MB available"
                        )

                # Attempt to connect to database
                self._thread_local.connection = sqlite3.connect(self.db_path)
                self._thread_local.connection.row_factory = sqlite3.Row  # Enable dict-like access

                # Enable foreign key constraints
                self._thread_local.connection.execute('PRAGMA foreign_keys = ON')

                # Test the connection
                self._thread_local.connection.execute('SELECT 1').fetchone()

                # Initialize schema
                self._initialize_schema()

                logger.info(f"Database connection established: {self.db_path}")

            except sqlite3.OperationalError as e:
                error_msg = str(e).lower()
                if 'permission denied' in error_msg or 'readonly' in error_msg:
                    raise FilePermissionError(
                        file_path=self.db_path,
                        technical_details=str(e),
                        original_exception=e
                    )
                elif 'disk' in error_msg or 'space' in error_msg:
                    raise DiskSpaceError(
                        technical_details=str(e),
                        original_exception=e
                    )
                elif 'database is locked' in error_msg:
                    raise DatabaseConnectionError(
                        technical_details="Database is locked by another process",
                        user_action="Please ensure no other instances of the application are running",
                        original_exception=e
                    )
                else:
                    raise DatabaseConnectionError(
                        technical_details=str(e),
                        original_exception=e
                    )
            except Exception as e:
                raise DatabaseConnectionError(
                    technical_details=f"Unexpected error connecting to database: {str(e)}",
                    original_exception=e
                )

        # Also set the main connection for backward compatibility
        self.connection = self._thread_local.connection
        return self._thread_local.connection

    def close(self):
        """Close database connection for current thread."""
        # Close thread-local connection
        if hasattr(self._thread_local, 'connection') and self._thread_local.connection:
            self._thread_local.connection.close()
            self._thread_local.connection = None

        # Also close main connection for backward compatibility
        if self.connection:
            self.connection.close()
            self.connection = None

    def _get_connection(self) -> sqlite3.Connection:
        """Get the current database connection (thread-local or main)."""
        connection = getattr(self._thread_local, 'connection', None) or self.connection
        if not connection:
            # Try to connect if no connection exists
            return self.connect()
        return connection

    def _initialize_schema(self):
        """
        Create database tables if they don't exist and run migrations if needed.

        Raises:
            DatabaseError: If schema initialization fails
        """
        try:
            connection = self._get_connection()
            cursor = connection.cursor()

            # Accounts table with flexible schema for future investment types
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    institution TEXT NOT NULL,
                    type TEXT NOT NULL,
                    encrypted_data BLOB NOT NULL,
                    created_date INTEGER NOT NULL,
                    last_updated INTEGER NOT NULL,
                    schema_version INTEGER DEFAULT 1,
                    is_demo BOOLEAN DEFAULT FALSE
                )
            ''')

            # Historical snapshots table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS historical_snapshots (
                    id TEXT PRIMARY KEY,
                    account_id TEXT NOT NULL,
                    timestamp INTEGER NOT NULL,
                    value REAL NOT NULL,
                    change_type TEXT NOT NULL,
                    encrypted_metadata BLOB,
                    FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
                )
            ''')

            # Stock positions table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS stock_positions (
                    id TEXT PRIMARY KEY,
                    trading_account_id TEXT NOT NULL,
                    symbol TEXT NOT NULL,
                    shares REAL NOT NULL,
                    purchase_price REAL NOT NULL,
                    purchase_date INTEGER NOT NULL,
                    current_price REAL,
                    last_price_update INTEGER,
                    FOREIGN KEY (trading_account_id) REFERENCES accounts (id) ON DELETE CASCADE
                )
            ''')

            # Application settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT,
                    encrypted_value BLOB
                )
            ''')

            # Watchlist table for stock tracking
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

            # Create indexes for better performance
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts (type)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_account_id ON historical_snapshots (account_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_timestamp ON historical_snapshots (timestamp)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_positions_account ON stock_positions (trading_account_id)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_symbol ON watchlist (symbol)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_added_date ON watchlist (added_date)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_watchlist_is_demo ON watchlist (is_demo)')

            connection.commit()

            # Set schema version if not exists
            self._set_schema_version_if_needed()

            # Run migrations if needed
            self._run_migrations_if_needed()

            # Run demo column migration if needed
            self.migrate_add_demo_column()

            logger.info("Database schema initialized successfully")

        except sqlite3.Error as e:
            raise DatabaseError(
                message="Failed to initialize database schema",
                code="DB_006",
                technical_details=str(e),
                original_exception=e
            )
        except Exception as e:
            raise DatabaseError(
                message="Unexpected error during schema initialization",
                code="DB_007",
                technical_details=str(e),
                original_exception=e
            )

    def _set_schema_version_if_needed(self):
        """Set initial schema version in app_settings if not exists."""
        try:
            self.get_setting('schema_version')
        except KeyError:
            self.set_setting('schema_version', str(self.SCHEMA_VERSION))

    def _run_migrations_if_needed(self):
        """Run database migrations if needed."""
        try:
            from .migration import DatabaseMigration
            migration = DatabaseMigration(self)

            if migration.needs_migration():
                logger.info("Database migration needed, starting migration process")
                migration.migrate_to_latest()
                logger.info("Database migration completed successfully")
            else:
                logger.debug("Database is up to date, no migration needed")

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Don't raise here to allow application to start with current schema
            # Migration can be attempted manually later

    def database_exists(self) -> bool:
        """Check if database file exists."""
        return Path(self.db_path).exists()

    # Account operations
    def create_account(self, account_data: Dict[str, Any]) -> str:
        """
        Create new account with encrypted data.

        Args:
            account_data: Account data dictionary

        Returns:
            Generated account ID
        """
        # Use provided ID if available, otherwise generate new one
        account_id = account_data.get('id', str(uuid.uuid4()))
        now = int(datetime.now().timestamp())

        # Separate public and sensitive data
        public_data = {
            'name': account_data['name'],
            'institution': account_data['institution'],
            'type': account_data['type']
        }

        # Handle demo marker - default to False if not specified
        is_demo = account_data.get('is_demo', False)

        # Encrypt sensitive account-specific data
        sensitive_data = {k: v for k, v in account_data.items()
                         if k not in ['name', 'institution', 'type', 'is_demo']}

        # Use default=str to handle any non-serializable objects (like datetime)
        encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data, default=str))

        cursor = self.connect().cursor()
        cursor.execute('''
            INSERT INTO accounts (id, name, institution, type, encrypted_data,
                                created_date, last_updated, schema_version, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_id, public_data['name'], public_data['institution'],
              public_data['type'], encrypted_data, now, now, self.SCHEMA_VERSION, is_demo))

        self.connection.commit()
        return account_id

    def get_account(self, account_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve account by ID with decrypted data.

        Args:
            account_id: Account ID to retrieve

        Returns:
            Account data dictionary or None if not found
        """
        cursor = self.connect().cursor()
        cursor.execute('SELECT * FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()

        if not row:
            return None

        # Decrypt sensitive data
        encrypted_data = row['encrypted_data']
        sensitive_data = json.loads(self.encryption_service.decrypt(encrypted_data))

        # Combine public and decrypted data
        account_data = {
            'id': row['id'],
            'name': row['name'],
            'institution': row['institution'],
            'type': row['type'],
            'created_date': datetime.fromtimestamp(row['created_date']),
            'last_updated': datetime.fromtimestamp(row['last_updated']),
            'schema_version': row['schema_version']
        }

        # Handle is_demo column gracefully (might not exist in older databases)
        try:
            account_data['is_demo'] = bool(row['is_demo'])
        except (IndexError, KeyError):
            account_data['is_demo'] = False
        account_data.update(sensitive_data)

        return account_data

    def get_accounts(self, account_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts, optionally filtered by type.

        Args:
            account_type: Optional account type filter

        Returns:
            List of account data dictionaries
        """
        cursor = self.connect().cursor()

        if account_type:
            cursor.execute('SELECT * FROM accounts WHERE type = ? ORDER BY name', (account_type,))
        else:
            cursor.execute('SELECT * FROM accounts ORDER BY name')

        accounts = []
        for row in cursor.fetchall():
            account_data = self.get_account(row['id'])
            if account_data:
                accounts.append(account_data)

        return accounts

    def get_demo_accounts(self) -> List[Dict[str, Any]]:
        """
        Retrieve all demo accounts.

        Returns:
            List of demo account data dictionaries
        """
        cursor = self.connect().cursor()
        cursor.execute('SELECT * FROM accounts WHERE is_demo = 1 ORDER BY name')

        accounts = []
        for row in cursor.fetchall():
            account_data = self.get_account(row['id'])
            if account_data:
                accounts.append(account_data)

        return accounts

    def get_real_accounts(self) -> List[Dict[str, Any]]:
        """
        Retrieve all real (non-demo) accounts.

        Returns:
            List of real account data dictionaries
        """
        cursor = self.connect().cursor()
        cursor.execute('SELECT * FROM accounts WHERE is_demo = 0 ORDER BY name')

        accounts = []
        for row in cursor.fetchall():
            account_data = self.get_account(row['id'])
            if account_data:
                accounts.append(account_data)

        return accounts

    def get_all_accounts(self) -> List[Dict[str, Any]]:
        """
        Retrieve all accounts (both demo and real).

        Returns:
            List of all account data dictionaries
        """
        cursor = self.connect().cursor()
        cursor.execute('SELECT * FROM accounts ORDER BY name')

        accounts = []
        for row in cursor.fetchall():
            account_data = self.get_account(row['id'])
            if account_data:
                accounts.append(account_data)

        return accounts

    def delete_demo_accounts(self) -> int:
        """
        Bulk delete all demo accounts and their related data.

        Returns:
            Number of demo accounts deleted

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.connect().cursor()

            # Get list of demo account IDs before deletion
            cursor.execute('SELECT id FROM accounts WHERE is_demo = 1')
            demo_account_ids = [row['id'] for row in cursor.fetchall()]

            if not demo_account_ids:
                return 0

            # Delete related data first (due to foreign key constraints)
            # Delete historical snapshots for demo accounts - use individual deletes for security
            for account_id in demo_account_ids:
                cursor.execute('DELETE FROM historical_snapshots WHERE account_id = ?', (account_id,))

            # Delete stock positions for demo trading accounts - use individual deletes for security
            for account_id in demo_account_ids:
                cursor.execute('DELETE FROM stock_positions WHERE trading_account_id = ?', (account_id,))

            # Finally, delete the demo accounts themselves
            cursor.execute('DELETE FROM accounts WHERE is_demo = 1')
            deleted_count = cursor.rowcount

            self.connection.commit()

            logger.info(f"Successfully deleted {deleted_count} demo accounts and their related data")
            return deleted_count

        except sqlite3.Error as e:
            self.connection.rollback()
            raise DatabaseError(
                message="Failed to delete demo accounts",
                code="DB_008",
                technical_details=str(e),
                original_exception=e
            )
        except Exception as e:
            self.connection.rollback()
            raise DatabaseError(
                message="Unexpected error during demo account deletion",
                code="DB_009",
                technical_details=str(e),
                original_exception=e
            )

    def update_account(self, account_id: str, account_data: Dict[str, Any]) -> bool:
        """
        Update existing account with encrypted data.

        Args:
            account_id: Account ID to update
            account_data: Updated account data

        Returns:
            True if account was updated, False if not found
        """
        cursor = self.connect().cursor()

        # Check if account exists and get current demo status
        cursor.execute('SELECT id, is_demo FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()
        if not row:
            return False

        now = int(datetime.now().timestamp())

        # Separate public and sensitive data
        public_data = {
            'name': account_data.get('name'),
            'institution': account_data.get('institution'),
            'type': account_data.get('type')
        }

        # Preserve demo marker if not explicitly provided in update
        try:
            current_is_demo = bool(row['is_demo'])
        except (IndexError, KeyError):
            current_is_demo = False
        is_demo = account_data.get('is_demo', current_is_demo)

        # Encrypt sensitive account-specific data
        sensitive_data = {k: v for k, v in account_data.items()
                         if k not in ['name', 'institution', 'type', 'id', 'created_date', 'last_updated', 'is_demo']}

        # Use default=str to handle any non-serializable objects (like datetime)
        encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data, default=str))

        cursor.execute('''
            UPDATE accounts
            SET name = ?, institution = ?, type = ?, encrypted_data = ?, last_updated = ?, is_demo = ?
            WHERE id = ?
        ''', (public_data['name'], public_data['institution'], public_data['type'],
              encrypted_data, now, is_demo, account_id))

        self.connection.commit()
        return True

    def save_account(self, account, is_demo: bool = False) -> str:
        """
        Save account (create or update) with demo marker support.

        Args:
            account: Account object to save
            is_demo: Whether this is a demo account

        Returns:
            Account ID
        """
        # Convert account object to dictionary
        if hasattr(account, 'to_dict'):
            account_data = account.to_dict()
        else:
            account_data = account

        # Add demo marker
        account_data['is_demo'] = is_demo

        # Fix field name mapping (account objects use 'account_type', database uses 'type')
        if 'account_type' in account_data and 'type' not in account_data:
            account_data['type'] = account_data['account_type']

        # Check if account exists
        if hasattr(account, 'id') and account.id:
            cursor = self.connect().cursor()
            cursor.execute('SELECT id FROM accounts WHERE id = ?', (account.id,))
            if cursor.fetchone():
                # Update existing account
                self.update_account(account.id, account_data)
                return account.id

        # Create new account, but preserve the original ID if provided
        if hasattr(account, 'id') and account.id:
            account_data['id'] = account.id
            return self.create_account(account_data)
        else:
            return self.create_account(account_data)

    def delete_account(self, account_id: str) -> bool:
        """
        Delete account and all related data.

        Args:
            account_id: Account ID to delete

        Returns:
            True if account was deleted, False if not found
        """
        cursor = self.connect().cursor()

        # Check if account exists
        cursor.execute('SELECT id FROM accounts WHERE id = ?', (account_id,))
        if not cursor.fetchone():
            return False

        # Delete account (cascading deletes will handle related data)
        cursor.execute('DELETE FROM accounts WHERE id = ?', (account_id,))
        self.connection.commit()
        return True

    # Historical snapshots operations
    def create_historical_snapshot(self, account_id: str, value: float,
                                 change_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create historical snapshot for account value.

        Args:
            account_id: Account ID for snapshot
            value: Account value at snapshot time
            change_type: Type of change that triggered snapshot
            metadata: Optional metadata dictionary

        Returns:
            Generated snapshot ID
        """
        snapshot_id = str(uuid.uuid4())
        now = int(datetime.now().timestamp())

        encrypted_metadata = None
        if metadata:
            encrypted_metadata = self.encryption_service.encrypt(json.dumps(metadata, default=str))

        cursor = self.connect().cursor()
        cursor.execute('''
            INSERT INTO historical_snapshots (id, account_id, timestamp, value,
                                            change_type, encrypted_metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (snapshot_id, account_id, now, value, change_type, encrypted_metadata))

        self.connection.commit()
        return snapshot_id

    def get_historical_snapshots(self, account_id: str,
                               start_timestamp: Optional[int] = None,
                               end_timestamp: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve historical snapshots for account.

        Args:
            account_id: Account ID to get snapshots for
            start_timestamp: Optional start timestamp filter
            end_timestamp: Optional end timestamp filter

        Returns:
            List of historical snapshot dictionaries
        """
        cursor = self.connect().cursor()

        query = 'SELECT * FROM historical_snapshots WHERE account_id = ?'
        params = [account_id]

        if start_timestamp:
            query += ' AND timestamp >= ?'
            params.append(start_timestamp)

        if end_timestamp:
            query += ' AND timestamp <= ?'
            params.append(end_timestamp)

        query += ' ORDER BY timestamp DESC'

        cursor.execute(query, params)

        snapshots = []
        for row in cursor.fetchall():
            snapshot_data = {
                'id': row['id'],
                'account_id': row['account_id'],
                'timestamp': datetime.fromtimestamp(row['timestamp']),
                'value': row['value'],
                'change_type': row['change_type']
            }

            # Decrypt metadata if present
            if row['encrypted_metadata']:
                metadata = json.loads(self.encryption_service.decrypt(row['encrypted_metadata']))
                snapshot_data['metadata'] = metadata

            snapshots.append(snapshot_data)

        return snapshots

    # Stock positions operations
    def create_stock_position(self, trading_account_id: str, symbol: str, shares: float,
                            purchase_price: float, purchase_date: int) -> str:
        """
        Create stock position for trading account.

        Args:
            trading_account_id: Trading account ID
            symbol: Stock symbol
            shares: Number of shares
            purchase_price: Purchase price per share
            purchase_date: Purchase date timestamp

        Returns:
            Generated position ID
        """
        position_id = str(uuid.uuid4())

        cursor = self.connect().cursor()
        cursor.execute('''
            INSERT INTO stock_positions (id, trading_account_id, symbol, shares,
                                       purchase_price, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (position_id, trading_account_id, symbol, shares, purchase_price, purchase_date))

        self.connection.commit()
        return position_id

    def get_stock_positions(self, trading_account_id: str) -> List[Dict[str, Any]]:
        """
        Get all stock positions for trading account.

        Args:
            trading_account_id: Trading account ID

        Returns:
            List of stock position dictionaries
        """
        cursor = self.connect().cursor()
        cursor.execute('''
            SELECT * FROM stock_positions
            WHERE trading_account_id = ?
            ORDER BY symbol
        ''', (trading_account_id,))

        positions = []
        for row in cursor.fetchall():
            position_data = {
                'id': row['id'],
                'trading_account_id': row['trading_account_id'],
                'symbol': row['symbol'],
                'shares': row['shares'],
                'purchase_price': row['purchase_price'],
                'purchase_date': datetime.fromtimestamp(row['purchase_date']),
                'current_price': row['current_price'],
                'last_price_update': datetime.fromtimestamp(row['last_price_update']) if row['last_price_update'] else None
            }
            positions.append(position_data)

        return positions

    def update_stock_price(self, position_id: str, current_price: float) -> bool:
        """
        Update current price for stock position.

        Args:
            position_id: Stock position ID
            current_price: Current stock price

        Returns:
            True if position was updated, False if not found
        """
        cursor = self.connect().cursor()
        now = int(datetime.now().timestamp())

        cursor.execute('''
            UPDATE stock_positions
            SET current_price = ?, last_price_update = ?
            WHERE id = ?
        ''', (current_price, now, position_id))

        if cursor.rowcount > 0:
            self.connection.commit()
            return True
        return False

    def update_stock_position(self, position_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update stock position with new data.

        Args:
            position_id: Stock position ID
            updates: Dictionary of fields to update

        Returns:
            True if position was updated, False if not found
        """
        cursor = self.connect().cursor()

        # Use explicit field updates for maximum security - no dynamic SQL
        updated = False

        if 'shares' in updates:
            cursor.execute('UPDATE stock_positions SET shares = ? WHERE id = ?', (updates['shares'], position_id))
            updated = True

        if 'purchase_price' in updates:
            cursor.execute('UPDATE stock_positions SET purchase_price = ? WHERE id = ?', (updates['purchase_price'], position_id))
            updated = True

        if 'purchase_date' in updates:
            cursor.execute('UPDATE stock_positions SET purchase_date = ? WHERE id = ?', (updates['purchase_date'], position_id))
            updated = True

        if 'current_price' in updates:
            cursor.execute('UPDATE stock_positions SET current_price = ? WHERE id = ?', (updates['current_price'], position_id))
            updated = True

        if not updated:
            return False

        if cursor.rowcount > 0:
            self.connection.commit()
            return True
        return False

    def delete_stock_position(self, position_id: str) -> bool:
        """
        Delete stock position.

        Args:
            position_id: Stock position ID to delete

        Returns:
            True if position was deleted, False if not found
        """
        cursor = self.connect().cursor()
        cursor.execute('DELETE FROM stock_positions WHERE id = ?', (position_id,))

        if cursor.rowcount > 0:
            self.connection.commit()
            return True
        return False

    # Application settings operations
    def set_setting(self, key: str, value: str):
        """
        Set encrypted application setting.

        Args:
            key: Setting key
            value: Setting value (will be encrypted)
        """
        encrypted_value = self.encryption_service.encrypt(value)

        cursor = self.connect().cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, encrypted_value)
            VALUES (?, ?)
        ''', (key, encrypted_value))

        self.connection.commit()

    def get_setting(self, key: str) -> str:
        """
        Get decrypted application setting.

        Args:
            key: Setting key

        Returns:
            Decrypted setting value

        Raises:
            KeyError: If setting key not found
        """
        cursor = self.connect().cursor()
        cursor.execute('SELECT encrypted_value FROM app_settings WHERE key = ?', (key,))
        row = cursor.fetchone()

        if not row:
            raise KeyError(f"Setting '{key}' not found")

        return self.encryption_service.decrypt(row['encrypted_value'])

    def get_schema_version(self) -> int:
        """
        Get current database schema version.

        Returns:
            Schema version number
        """
        try:
            return int(self.get_setting('schema_version'))
        except KeyError:
            return 1  # Default version

    def migrate_add_demo_column(self) -> bool:
        """
        Migration function to add is_demo column to existing databases.
        This is safe to run multiple times - it will only add the column if it doesn't exist.

        Returns:
            True if migration was successful or column already exists, False otherwise

        Raises:
            DatabaseError: If migration fails
        """
        try:
            cursor = self.connect().cursor()

            # Check if is_demo column already exists
            cursor.execute("PRAGMA table_info(accounts)")
            columns = [column[1] for column in cursor.fetchall()]

            if 'is_demo' in columns:
                logger.info("is_demo column already exists, no migration needed")
                return True

            # Add the is_demo column with default value FALSE
            cursor.execute('ALTER TABLE accounts ADD COLUMN is_demo BOOLEAN DEFAULT FALSE')

            # Update all existing accounts to have is_demo = FALSE (explicit)
            cursor.execute('UPDATE accounts SET is_demo = FALSE WHERE is_demo IS NULL')

            self.connection.commit()

            logger.info("Successfully added is_demo column to accounts table")
            return True

        except sqlite3.Error as e:
            self.connection.rollback()
            raise DatabaseError(
                message="Failed to add is_demo column to accounts table",
                code="DB_010",
                technical_details=str(e),
                user_action="Please check database permissions and try again",
                original_exception=e
            )
        except Exception as e:
            self.connection.rollback()
            raise DatabaseError(
                message="Unexpected error during database migration",
                code="DB_011",
                technical_details=str(e),
                original_exception=e
            )

    # Watchlist operations
    def create_watchlist_item(self, watchlist_data: Dict[str, Any]) -> str:
        """
        Create new watchlist item with encrypted data.

        Args:
            watchlist_data: Watchlist item data dictionary

        Returns:
            Generated watchlist item ID

        Raises:
            DatabaseError: If creation fails
        """
        try:
            # Use provided ID if available, otherwise generate new one
            item_id = watchlist_data.get('id', str(uuid.uuid4()))
            now = int(datetime.now().timestamp())

            # Extract public data
            symbol = watchlist_data['symbol'].upper()  # Normalize symbol to uppercase
            is_demo = watchlist_data.get('is_demo', False)
            added_date = watchlist_data.get('added_date', now)

            # Encrypt sensitive data (notes, price data, etc.)
            sensitive_data = {k: v for k, v in watchlist_data.items()
                             if k not in ['id', 'symbol', 'is_demo', 'added_date']}

            encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data, default=str))

            cursor = self.connect().cursor()
            cursor.execute('''
                INSERT INTO watchlist (id, symbol, encrypted_data, added_date, is_demo)
                VALUES (?, ?, ?, ?, ?)
            ''', (item_id, symbol, encrypted_data, added_date, is_demo))

            self.connection.commit()
            logger.info(f"Created watchlist item for symbol {symbol}")
            return item_id

        except sqlite3.IntegrityError as e:
            if 'UNIQUE constraint failed' in str(e):
                raise DatabaseError(
                    message=f"Stock symbol {symbol} is already in watchlist",
                    code="DB_012",
                    technical_details=str(e),
                    user_action="Remove existing entry or choose a different symbol",
                    original_exception=e
                )
            else:
                raise DatabaseError(
                    message="Failed to create watchlist item due to constraint violation",
                    code="DB_013",
                    technical_details=str(e),
                    original_exception=e
                )
        except Exception as e:
            raise DatabaseError(
                message="Failed to create watchlist item",
                code="DB_014",
                technical_details=str(e),
                original_exception=e
            )

    def get_watchlist_item(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve watchlist item by symbol with decrypted data.

        Args:
            symbol: Stock symbol to retrieve

        Returns:
            Watchlist item data dictionary or None if not found

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            cursor = self.connect().cursor()
            cursor.execute('SELECT * FROM watchlist WHERE symbol = ?', (symbol.upper(),))
            row = cursor.fetchone()

            if not row:
                return None

            # Decrypt sensitive data
            encrypted_data = row['encrypted_data']
            sensitive_data = json.loads(self.encryption_service.decrypt(encrypted_data))

            # Combine public and decrypted data
            watchlist_data = {
                'id': row['id'],
                'symbol': row['symbol'],
                'added_date': datetime.fromtimestamp(row['added_date']),
                'last_price_update': datetime.fromtimestamp(row['last_price_update']) if row['last_price_update'] else None,
                'is_demo': bool(row['is_demo'])
            }
            watchlist_data.update(sensitive_data)

            return watchlist_data

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to retrieve watchlist item for symbol {symbol}",
                code="DB_015",
                technical_details=str(e),
                original_exception=e
            )

    def get_watchlist_items(self, include_demo: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve all watchlist items with decrypted data.

        Args:
            include_demo: Whether to include demo watchlist items

        Returns:
            List of watchlist item data dictionaries

        Raises:
            DatabaseError: If retrieval fails
        """
        try:
            cursor = self.connect().cursor()

            if include_demo:
                cursor.execute('SELECT * FROM watchlist ORDER BY symbol')
            else:
                cursor.execute('SELECT * FROM watchlist WHERE is_demo = 0 ORDER BY symbol')

            watchlist_items = []
            for row in cursor.fetchall():
                item_data = self.get_watchlist_item(row['symbol'])
                if item_data:
                    watchlist_items.append(item_data)

            return watchlist_items

        except Exception as e:
            raise DatabaseError(
                message="Failed to retrieve watchlist items",
                code="DB_016",
                technical_details=str(e),
                original_exception=e
            )

    def get_demo_watchlist_items(self) -> List[Dict[str, Any]]:
        """
        Retrieve all demo watchlist items.

        Returns:
            List of demo watchlist item data dictionaries
        """
        try:
            cursor = self.connect().cursor()
            cursor.execute('SELECT * FROM watchlist WHERE is_demo = 1 ORDER BY symbol')

            watchlist_items = []
            for row in cursor.fetchall():
                item_data = self.get_watchlist_item(row['symbol'])
                if item_data:
                    watchlist_items.append(item_data)

            return watchlist_items

        except Exception as e:
            raise DatabaseError(
                message="Failed to retrieve demo watchlist items",
                code="DB_017",
                technical_details=str(e),
                original_exception=e
            )

    def get_real_watchlist_items(self) -> List[Dict[str, Any]]:
        """
        Retrieve all real (non-demo) watchlist items.

        Returns:
            List of real watchlist item data dictionaries
        """
        try:
            cursor = self.connect().cursor()
            cursor.execute('SELECT * FROM watchlist WHERE is_demo = 0 ORDER BY symbol')

            watchlist_items = []
            for row in cursor.fetchall():
                item_data = self.get_watchlist_item(row['symbol'])
                if item_data:
                    watchlist_items.append(item_data)

            return watchlist_items

        except Exception as e:
            raise DatabaseError(
                message="Failed to retrieve real watchlist items",
                code="DB_018",
                technical_details=str(e),
                original_exception=e
            )

    def update_watchlist_item(self, symbol: str, watchlist_data: Dict[str, Any]) -> bool:
        """
        Update existing watchlist item with encrypted data.

        Args:
            symbol: Stock symbol to update
            watchlist_data: Updated watchlist item data

        Returns:
            True if item was updated, False if not found

        Raises:
            DatabaseError: If update fails
        """
        try:
            cursor = self.connect().cursor()

            # Check if item exists
            cursor.execute('SELECT id, is_demo FROM watchlist WHERE symbol = ?', (symbol.upper(),))
            row = cursor.fetchone()
            if not row:
                return False

            # Preserve demo marker if not explicitly provided in update
            current_is_demo = bool(row['is_demo'])
            is_demo = watchlist_data.get('is_demo', current_is_demo)

            # Update last_price_update if price data is being updated
            last_price_update = None
            if 'current_price' in watchlist_data or 'daily_change' in watchlist_data:
                last_price_update = int(datetime.now().timestamp())

            # Encrypt sensitive data
            sensitive_data = {k: v for k, v in watchlist_data.items()
                             if k not in ['symbol', 'is_demo', 'added_date']}

            encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data, default=str))

            # Update the record
            if last_price_update:
                cursor.execute('''
                    UPDATE watchlist
                    SET encrypted_data = ?, last_price_update = ?, is_demo = ?
                    WHERE symbol = ?
                ''', (encrypted_data, last_price_update, is_demo, symbol.upper()))
            else:
                cursor.execute('''
                    UPDATE watchlist
                    SET encrypted_data = ?, is_demo = ?
                    WHERE symbol = ?
                ''', (encrypted_data, is_demo, symbol.upper()))

            self.connection.commit()
            logger.info(f"Updated watchlist item for symbol {symbol}")
            return True

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to update watchlist item for symbol {symbol}",
                code="DB_019",
                technical_details=str(e),
                original_exception=e
            )

    def delete_watchlist_item(self, symbol: str) -> bool:
        """
        Delete watchlist item by symbol.

        Args:
            symbol: Stock symbol to delete

        Returns:
            True if item was deleted, False if not found

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.connect().cursor()

            # Check if item exists
            cursor.execute('SELECT id FROM watchlist WHERE symbol = ?', (symbol.upper(),))
            if not cursor.fetchone():
                return False

            # Delete the item
            cursor.execute('DELETE FROM watchlist WHERE symbol = ?', (symbol.upper(),))
            self.connection.commit()

            logger.info(f"Deleted watchlist item for symbol {symbol}")
            return True

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to delete watchlist item for symbol {symbol}",
                code="DB_020",
                technical_details=str(e),
                original_exception=e
            )

    def delete_demo_watchlist_items(self) -> int:
        """
        Bulk delete all demo watchlist items.

        Returns:
            Number of demo watchlist items deleted

        Raises:
            DatabaseError: If deletion fails
        """
        try:
            cursor = self.connect().cursor()

            # Delete demo watchlist items
            cursor.execute('DELETE FROM watchlist WHERE is_demo = 1')
            deleted_count = cursor.rowcount

            self.connection.commit()

            logger.info(f"Successfully deleted {deleted_count} demo watchlist items")
            return deleted_count

        except Exception as e:
            raise DatabaseError(
                message="Failed to delete demo watchlist items",
                code="DB_021",
                technical_details=str(e),
                original_exception=e
            )

    def save_watchlist_item(self, watchlist_item, is_demo: bool = False) -> str:
        """
        Save watchlist item (create or update) with demo marker support.

        Args:
            watchlist_item: WatchlistItem object or dictionary to save
            is_demo: Whether this is a demo watchlist item

        Returns:
            Watchlist item ID

        Raises:
            DatabaseError: If save fails
        """
        try:
            # Convert watchlist item object to dictionary
            if hasattr(watchlist_item, 'to_dict'):
                item_data = watchlist_item.to_dict()
            else:
                item_data = watchlist_item

            # Add demo marker
            item_data['is_demo'] = is_demo

            # Check if item exists
            symbol = item_data['symbol'].upper()
            existing_item = self.get_watchlist_item(symbol)

            if existing_item:
                # Update existing item
                self.update_watchlist_item(symbol, item_data)
                return existing_item['id']
            else:
                # Create new item
                return self.create_watchlist_item(item_data)

        except Exception as e:
            raise DatabaseError(
                message=f"Failed to save watchlist item for symbol {item_data.get('symbol', 'unknown')}",
                code="DB_022",
                technical_details=str(e),
                original_exception=e
            )