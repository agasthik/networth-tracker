"""
Database migration service for the networth tracker application.
Handles schema version management and data preservation during updates.
"""

import sqlite3
import json
import logging
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from pathlib import Path

from .error_handler import (
    DatabaseError, DatabaseMigrationError, DataIntegrityError,
    SystemError
)
from .logging_config import get_logger

logger = get_logger(__name__)


class DatabaseMigration:
    """
    Handles database schema migrations with data preservation.

    This class manages schema version upgrades, ensuring existing data
    is preserved and properly migrated when new account types or
    database structure changes are introduced.
    """

    def __init__(self, db_service):
        """
        Initialize migration service.

        Args:
            db_service: DatabaseService instance with active connection
        """
        self.db_service = db_service
        self.migrations: Dict[int, Callable] = {
            2: self._migrate_to_v2_add_i_bonds_support,
            3: self._migrate_to_v3_add_metadata_column,
            4: self._migrate_to_v4_add_broker_support,
            5: self._migrate_to_v5_add_watchlist_support,
            # Future migrations can be added here
        }

    def get_current_schema_version(self) -> int:
        """
        Get current database schema version.

        Returns:
            Current schema version number
        """
        try:
            return self.db_service.get_schema_version()
        except Exception as e:
            logger.warning(f"Could not get schema version, defaulting to 1: {e}")
            return 1

    def get_target_schema_version(self) -> int:
        """
        Get the target schema version (latest available).

        Returns:
            Target schema version number
        """
        return max(self.migrations.keys()) if self.migrations else 1

    def needs_migration(self) -> bool:
        """
        Check if database needs migration.

        Returns:
            True if migration is needed, False otherwise
        """
        current = self.get_current_schema_version()
        target = self.get_target_schema_version()
        return current < target

    def migrate_to_latest(self) -> bool:
        """
        Migrate database to the latest schema version.

        Returns:
            True if migration was successful, False if no migration needed

        Raises:
            DatabaseMigrationError: If migration fails
        """
        current_version = self.get_current_schema_version()
        target_version = self.get_target_schema_version()

        if current_version >= target_version:
            logger.info(f"Database already at latest version {current_version}")
            return False

        logger.info(f"Starting migration from version {current_version} to {target_version}")

        try:
            # Create backup before migration
            backup_path = self._create_backup()
            logger.info(f"Created backup at {backup_path}")

            # Perform migrations sequentially
            for version in range(current_version + 1, target_version + 1):
                if version in self.migrations:
                    logger.info(f"Applying migration to version {version}")
                    self._apply_migration(version)
                    self._update_schema_version(version)
                    logger.info(f"Successfully migrated to version {version}")

            # Verify data integrity after migration
            self._verify_data_integrity()
            logger.info("Migration completed successfully")
            return True

        except Exception as e:
            logger.error(f"Migration failed: {e}")
            # Attempt to restore from backup
            try:
                self._restore_from_backup(backup_path)
                logger.info("Successfully restored from backup")
            except Exception as restore_error:
                logger.error(f"Failed to restore from backup: {restore_error}")
                raise DatabaseMigrationError(
                    message="Migration failed and backup restoration failed",
                    technical_details=f"Migration error: {e}, Restore error: {restore_error}",
                    original_exception=e
                )

            raise DatabaseMigrationError(
                message="Database migration failed",
                technical_details=str(e),
                original_exception=e
            )

    def _apply_migration(self, version: int):
        """
        Apply specific migration version.

        Args:
            version: Migration version to apply

        Raises:
            DatabaseMigrationError: If migration fails
        """
        if version not in self.migrations:
            raise DatabaseMigrationError(
                message=f"No migration available for version {version}",
                technical_details=f"Available migrations: {list(self.migrations.keys())}"
            )

        try:
            migration_func = self.migrations[version]
            migration_func()
        except Exception as e:
            raise DatabaseMigrationError(
                message=f"Failed to apply migration to version {version}",
                technical_details=str(e),
                original_exception=e
            )

    def _update_schema_version(self, version: int):
        """
        Update schema version in database.

        Args:
            version: New schema version
        """
        self.db_service.set_setting('schema_version', str(version))

    def _create_backup(self) -> str:
        """
        Create backup of current database.

        Returns:
            Path to backup file

        Raises:
            DatabaseMigrationError: If backup creation fails
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = f"{self.db_service.db_path}.backup_{timestamp}"

            # Create backup using SQLite backup API
            source = self.db_service.connect()
            backup_conn = sqlite3.connect(backup_path)

            source.backup(backup_conn)
            backup_conn.close()

            return backup_path

        except Exception as e:
            raise DatabaseMigrationError(
                message="Failed to create database backup",
                technical_details=str(e),
                original_exception=e
            )

    def _restore_from_backup(self, backup_path: str):
        """
        Restore database from backup.

        Args:
            backup_path: Path to backup file

        Raises:
            DatabaseMigrationError: If restore fails
        """
        try:
            if not Path(backup_path).exists():
                raise FileNotFoundError(f"Backup file not found: {backup_path}")

            # Close current connection
            self.db_service.close()

            # Replace current database with backup
            import shutil
            shutil.copy2(backup_path, self.db_service.db_path)

            # Reconnect to restored database
            self.db_service.connect()

        except Exception as e:
            raise DatabaseMigrationError(
                message="Failed to restore from backup",
                technical_details=str(e),
                original_exception=e
            )

    def _verify_data_integrity(self):
        """
        Verify data integrity after migration.

        Raises:
            DataIntegrityError: If data integrity check fails
        """
        try:
            cursor = self.db_service.connect().cursor()

            # Check foreign key constraints
            cursor.execute('PRAGMA foreign_key_check')
            fk_violations = cursor.fetchall()
            if fk_violations:
                raise DataIntegrityError(
                    message="Foreign key constraint violations found after migration",
                    technical_details=f"Violations: {fk_violations}"
                )

            # Check that all accounts can be decrypted
            accounts = self.db_service.get_accounts()
            for account in accounts:
                if not account.get('id'):
                    raise DataIntegrityError(
                        message="Account missing required ID field",
                        technical_details=f"Account: {account}"
                    )

            # Check that historical snapshots reference valid accounts
            cursor.execute('''
                SELECT COUNT(*) FROM historical_snapshots h
                LEFT JOIN accounts a ON h.account_id = a.id
                WHERE a.id IS NULL
            ''')
            orphaned_snapshots = cursor.fetchone()[0]
            if orphaned_snapshots > 0:
                raise DataIntegrityError(
                    message=f"Found {orphaned_snapshots} orphaned historical snapshots",
                    technical_details="Historical snapshots reference non-existent accounts"
                )

            # Check that stock positions reference valid trading accounts
            cursor.execute('''
                SELECT COUNT(*) FROM stock_positions s
                LEFT JOIN accounts a ON s.trading_account_id = a.id
                WHERE a.id IS NULL OR a.type != 'TRADING'
            ''')
            orphaned_positions = cursor.fetchone()[0]
            if orphaned_positions > 0:
                raise DataIntegrityError(
                    message=f"Found {orphaned_positions} orphaned stock positions",
                    technical_details="Stock positions reference non-existent or non-trading accounts"
                )

            logger.info("Data integrity verification passed")

        except Exception as e:
            if isinstance(e, DataIntegrityError):
                raise
            raise DataIntegrityError(
                message="Data integrity verification failed",
                technical_details=str(e),
                original_exception=e
            )

    # Migration methods for specific versions

    def _migrate_to_v2_add_i_bonds_support(self):
        """
        Migration to version 2: Add I-bonds account type support.

        This migration ensures existing data remains intact while
        adding support for I-bonds accounts.
        """
        logger.info("Applying migration v2: Adding I-bonds support")

        cursor = self.db_service.connect().cursor()

        # No schema changes needed - I-bonds use existing flexible schema
        # Just verify that the accounts table supports the new type
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
        if not cursor.fetchone():
            raise DatabaseMigrationError(
                message="Accounts table not found during I-bonds migration",
                technical_details="Database schema appears corrupted"
            )

        # Add any I-bonds specific indexes if needed
        # NOTE: Disabled because json_extract doesn't work with encrypted data
        # cursor.execute('''
        #     CREATE INDEX IF NOT EXISTS idx_accounts_maturity_date
        #     ON accounts (json_extract(encrypted_data, '$.maturity_date'))
        #     WHERE type = 'I_BONDS'
        # ''')

        self.db_service.connection.commit()
        logger.info("I-bonds support migration completed")

    def _migrate_to_v3_add_metadata_column(self):
        """
        Migration to version 3: Add metadata column for flexible account attributes.

        This migration adds a metadata column to support future investment
        product types without breaking existing functionality.
        """
        logger.info("Applying migration v3: Adding metadata column")

        cursor = self.db_service.connection.cursor()

        # Check if metadata column already exists
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'metadata' not in columns:
            # Add metadata column for flexible attributes
            cursor.execute('ALTER TABLE accounts ADD COLUMN metadata BLOB')
            logger.info("Added metadata column to accounts table")

        # Add metadata column to historical snapshots if not exists
        cursor.execute("PRAGMA table_info(historical_snapshots)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'metadata' not in columns:
            cursor.execute('ALTER TABLE historical_snapshots ADD COLUMN metadata BLOB')
            logger.info("Added metadata column to historical_snapshots table")

        self.db_service.connection.commit()
        logger.info("Metadata column migration completed")

    def _migrate_to_v4_add_broker_support(self):
        """
        Migration to version 4: Enhanced broker support for trading accounts.

        This migration adds better support for multiple brokers and
        broker-specific metadata.
        """
        logger.info("Applying migration v4: Adding enhanced broker support")

        cursor = self.db_service.connection.cursor()

        # Add broker-specific indexes for better performance
        # NOTE: Disabled because json_extract doesn't work with encrypted data
        # cursor.execute('''
        #     CREATE INDEX IF NOT EXISTS idx_accounts_broker
        #     ON accounts (json_extract(encrypted_data, '$.broker_name'))
        #     WHERE type = 'TRADING'
        # ''')

        # Add index for account numbers (encrypted)
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_accounts_institution_type
            ON accounts (institution, type)
        ''')

        self.db_service.connection.commit()
        logger.info("Enhanced broker support migration completed")

    def _migrate_to_v5_add_watchlist_support(self):
        """
        Migration to version 5: Add watchlist table for stock tracking.

        This migration adds the watchlist table to support tracking stocks
        without owning them, with encrypted storage for user notes.
        """
        logger.info("Applying migration v5: Adding watchlist support")

        cursor = self.db_service.connection.cursor()

        # Check if watchlist table already exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'")
        if not cursor.fetchone():
            # Create watchlist table
            cursor.execute('''
                CREATE TABLE watchlist (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL UNIQUE,
                    encrypted_data BLOB NOT NULL,
                    added_date INTEGER NOT NULL,
                    last_price_update INTEGER,
                    is_demo BOOLEAN DEFAULT FALSE
                )
            ''')
            logger.info("Created watchlist table")

            # Add indexes for efficient watchlist queries
            cursor.execute('CREATE INDEX idx_watchlist_symbol ON watchlist (symbol)')
            cursor.execute('CREATE INDEX idx_watchlist_added_date ON watchlist (added_date)')
            cursor.execute('CREATE INDEX idx_watchlist_is_demo ON watchlist (is_demo)')
            logger.info("Created watchlist indexes")

        self.db_service.connection.commit()
        logger.info("Watchlist support migration completed")

    def add_custom_migration(self, version: int, migration_func: Callable):
        """
        Add custom migration for future use.

        Args:
            version: Migration version number
            migration_func: Function to execute for this migration

        Raises:
            ValueError: If version already exists
        """
        if version in self.migrations:
            raise ValueError(f"Migration version {version} already exists")

        self.migrations[version] = migration_func
        logger.info(f"Added custom migration for version {version}")

    def get_migration_history(self) -> List[Dict[str, Any]]:
        """
        Get migration history information.

        Returns:
            List of migration history entries
        """
        current_version = self.get_current_schema_version()
        target_version = self.get_target_schema_version()

        history = []
        for version in sorted(self.migrations.keys()):
            status = "completed" if version <= current_version else "pending"
            history.append({
                'version': version,
                'status': status,
                'description': self.migrations[version].__doc__.strip() if self.migrations[version].__doc__ else f"Migration to version {version}"
            })

        return history

    def rollback_to_version(self, target_version: int):
        """
        Rollback database to a specific version.

        Note: This is a destructive operation and should be used with caution.
        Only supports rollback to immediately previous version.

        Args:
            target_version: Version to rollback to

        Raises:
            DatabaseMigrationError: If rollback is not supported or fails
        """
        current_version = self.get_current_schema_version()

        if target_version >= current_version:
            raise DatabaseMigrationError(
                message=f"Cannot rollback from version {current_version} to {target_version}",
                technical_details="Target version must be lower than current version"
            )

        if current_version - target_version > 1:
            raise DatabaseMigrationError(
                message="Rollback only supported to immediately previous version",
                technical_details=f"Current: {current_version}, Target: {target_version}"
            )

        # For now, rollback is only supported via backup restoration
        raise DatabaseMigrationError(
            message="Rollback not implemented - restore from backup instead",
            technical_details="Use backup files created during migration for rollback"
        )