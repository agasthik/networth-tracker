#!/usr/bin/env python3
"""
Database initialization script for Networth Tracker.
Creates database schema, sets up initial configuration, and handles migrations.
"""

import os
import sys
import argparse
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager, get_environment
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.migration import DatabaseMigration
from services.logging_config import setup_app_logging


class DatabaseInitializer:
    """Handles database initialization and setup."""

    def __init__(self, config):
        self.config = config
        self.logger = setup_app_logging(debug_mode=config.DEBUG)

    def create_database(self, db_path, force=False):
        """Create a new database with the current schema."""
        if os.path.exists(db_path) and not force:
            self.logger.error(f"Database already exists: {db_path}")
            self.logger.info("Use --force to overwrite existing database")
            return False

        try:
            # Remove existing database if force is True
            if force and os.path.exists(db_path):
                os.remove(db_path)
                self.logger.info(f"Removed existing database: {db_path}")

            # Create database service (this will create the database file)
            db_service = DatabaseService(db_path)

            # Initialize schema
            db_service.initialize_database()

            # Set file permissions
            if os.name != 'nt':  # Unix/Linux/macOS
                os.chmod(db_path, self.config.DATABASE_FILE_MODE)

            self.logger.info(f"Database created successfully: {db_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to create database: {e}")
            return False

    def migrate_database(self, db_path):
        """Run database migrations."""
        if not os.path.exists(db_path):
            self.logger.error(f"Database does not exist: {db_path}")
            return False

        try:
            # Create database service
            db_service = DatabaseService(db_path)

            # Create migration service
            migration_service = DatabaseMigration(db_service)

            # Check current version
            current_version = migration_service.get_current_version()
            latest_version = migration_service.get_latest_version()

            self.logger.info(f"Current database version: {current_version}")
            self.logger.info(f"Latest database version: {latest_version}")

            if current_version >= latest_version:
                self.logger.info("Database is already up to date")
                return True

            # Run migrations
            self.logger.info(f"Migrating database from version {current_version} to {latest_version}")
            success = migration_service.migrate_to_latest()

            if success:
                self.logger.info("Database migration completed successfully")
            else:
                self.logger.error("Database migration failed")

            return success

        except Exception as e:
            self.logger.error(f"Failed to migrate database: {e}")
            return False

    def backup_database(self, db_path, backup_path=None):
        """Create a backup of the database."""
        if not os.path.exists(db_path):
            self.logger.error(f"Database does not exist: {db_path}")
            return False

        try:
            if backup_path is None:
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_dir = Path(self.config.BACKUP_DIR)
                backup_dir.mkdir(exist_ok=True)
                backup_path = backup_dir / f"networth_backup_{timestamp}.db"

            # Copy database file
            import shutil
            shutil.copy2(db_path, backup_path)

            # Set file permissions
            if os.name != 'nt':  # Unix/Linux/macOS
                os.chmod(backup_path, self.config.DATABASE_FILE_MODE)

            self.logger.info(f"Database backup created: {backup_path}")
            return True

        except Exception as e:
            self.logger.error(f"Failed to backup database: {e}")
            return False

    def verify_database(self, db_path):
        """Verify database integrity and structure."""
        if not os.path.exists(db_path):
            self.logger.error(f"Database does not exist: {db_path}")
            return False

        try:
            # Create database service
            db_service = DatabaseService(db_path)

            # Check database connection
            if not db_service.test_connection():
                self.logger.error("Failed to connect to database")
                return False

            # Verify schema
            if not db_service.verify_schema():
                self.logger.error("Database schema verification failed")
                return False

            # Check file permissions
            if os.name != 'nt':  # Unix/Linux/macOS
                file_mode = oct(os.stat(db_path).st_mode)[-3:]
                if file_mode != '600':
                    self.logger.warning(f"Database file permissions are {file_mode}, should be 600")

            self.logger.info("Database verification completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Database verification failed: {e}")
            return False

    def reset_database(self, db_path):
        """Reset database by dropping all data but keeping schema."""
        if not os.path.exists(db_path):
            self.logger.error(f"Database does not exist: {db_path}")
            return False

        try:
            # Create backup first
            if not self.backup_database(db_path):
                self.logger.error("Failed to create backup before reset")
                return False

            # Create database service
            db_service = DatabaseService(db_path)

            # Reset database
            if db_service.reset_database():
                self.logger.info("Database reset completed successfully")
                return True
            else:
                self.logger.error("Database reset failed")
                return False

        except Exception as e:
            self.logger.error(f"Failed to reset database: {e}")
            return False


def main():
    """Main entry point for database initialization."""
    parser = argparse.ArgumentParser(description='Database initialization for Networth Tracker')
    parser.add_argument(
        '--env',
        choices=['development', 'production', 'testing'],
        default=get_environment(),
        help='Environment to use (default: production)'
    )
    parser.add_argument(
        '--database',
        help='Database path (overrides config)'
    )
    parser.add_argument(
        '--create',
        action='store_true',
        help='Create new database'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Run database migrations'
    )
    parser.add_argument(
        '--backup',
        action='store_true',
        help='Create database backup'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify database integrity'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database (removes all data)'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='Force operation (overwrite existing files)'
    )
    parser.add_argument(
        '--demo',
        action='store_true',
        help='Operate on demo database instead of production'
    )

    args = parser.parse_args()

    # Set up configuration
    os.environ['FLASK_ENV'] = args.env
    config = ConfigManager.get_config(args.env)

    # Initialize database manager
    db_init = DatabaseInitializer(config)

    # Determine database path
    if args.database:
        db_path = args.database
    elif args.demo:
        db_path = config.DEMO_DATABASE_PATH
    else:
        db_path = config.DATABASE_PATH

    # Execute requested operations
    success = True

    if args.create:
        success &= db_init.create_database(db_path, force=args.force)

    if args.migrate:
        success &= db_init.migrate_database(db_path)

    if args.backup:
        success &= db_init.backup_database(db_path)

    if args.verify:
        success &= db_init.verify_database(db_path)

    if args.reset:
        if not args.force:
            response = input("This will delete all data. Are you sure? (yes/no): ")
            if response.lower() != 'yes':
                print("Operation cancelled")
                return 0
        success &= db_init.reset_database(db_path)

    # If no specific operation was requested, create and verify
    if not any([args.create, args.migrate, args.backup, args.verify, args.reset]):
        print("No operation specified. Creating and verifying database...")
        success &= db_init.create_database(db_path, force=args.force)
        success &= db_init.verify_database(db_path)

    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())