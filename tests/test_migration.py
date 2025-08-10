"""
Unit tests for database migration system.
Tests migration operations, data integrity, and error handling.
"""

import pytest
import sqlite3
import tempfile
import os
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from services.migration import DatabaseMigration
from services.database import DatabaseService
from services.encryption import EncryptionService
from services.error_handler import (
    DatabaseMigrationError, DataIntegrityError, DatabaseError
)


class TestDatabaseMigration:
    """Test cases for DatabaseMigration class."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        service = EncryptionService()
        service.derive_key("test_password_123")
        return service

    @pytest.fixture
    def db_service(self, temp_db_path, encryption_service):
        """Create database service for testing."""
        service = DatabaseService(temp_db_path, encryption_service)
        service.connect()
        return service

    @pytest.fixture
    def migration_service(self, db_service):
        """Create migration service for testing."""
        return DatabaseMigration(db_service)

    def test_get_current_schema_version_default(self, migration_service):
        """Test getting current schema version when not set."""
        # Remove schema version setting to test default
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute('DELETE FROM app_settings WHERE key = ?', ('schema_version',))
        migration_service.db_service.connection.commit()

        # Should return 1 as default
        version = migration_service.get_current_schema_version()
        assert version == 1

    def test_get_current_schema_version_set(self, migration_service):
        """Test getting current schema version when set."""
        # Set version to 2
        migration_service.db_service.set_setting('schema_version', '2')

        version = migration_service.get_current_schema_version()
        assert version == 2

    def test_get_target_schema_version(self, migration_service):
        """Test getting target schema version."""
        target = migration_service.get_target_schema_version()
        # Should be the highest migration version available
        assert target >= 2  # At least v2 for I-bonds support

    def test_needs_migration_true(self, migration_service):
        """Test needs_migration when migration is needed."""
        # Set current version to 1, target should be higher
        migration_service.db_service.set_setting('schema_version', '1')

        needs_migration = migration_service.needs_migration()
        assert needs_migration is True

    def test_needs_migration_false(self, migration_service):
        """Test needs_migration when no migration is needed."""
        # Set current version to target version
        target = migration_service.get_target_schema_version()
        migration_service.db_service.set_setting('schema_version', str(target))

        needs_migration = migration_service.needs_migration()
        assert needs_migration is False

    def test_create_backup_success(self, migration_service, temp_db_path):
        """Test successful backup creation."""
        # Add some test data
        migration_service.db_service.set_setting('test_key', 'test_value')

        backup_path = migration_service._create_backup()

        # Verify backup file exists
        assert os.path.exists(backup_path)
        assert backup_path.startswith(temp_db_path + '.backup_')

        # Verify backup contains data
        backup_conn = sqlite3.connect(backup_path)
        cursor = backup_conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM app_settings")
        count = cursor.fetchone()[0]
        backup_conn.close()

        assert count > 0

        # Cleanup
        os.unlink(backup_path)

    def test_create_backup_failure(self, migration_service):
        """Test backup creation failure."""
        # Mock database connection to raise error
        with patch.object(migration_service.db_service, 'connect', side_effect=sqlite3.Error("Test error")):
            with pytest.raises(DatabaseMigrationError) as exc_info:
                migration_service._create_backup()

            assert "Failed to create database backup" in str(exc_info.value)

    def test_restore_from_backup_success(self, migration_service, temp_db_path):
        """Test successful backup restoration."""
        # Create backup first
        migration_service.db_service.set_setting('original_key', 'original_value')
        backup_path = migration_service._create_backup()

        # Modify original database
        migration_service.db_service.set_setting('modified_key', 'modified_value')

        # Restore from backup
        migration_service._restore_from_backup(backup_path)

        # Verify restoration
        try:
            value = migration_service.db_service.get_setting('original_key')
            assert value == 'original_value'
        except KeyError:
            pytest.fail("Original data not restored")

        # Verify modified data is gone
        with pytest.raises(KeyError):
            migration_service.db_service.get_setting('modified_key')

        # Cleanup
        os.unlink(backup_path)

    def test_restore_from_backup_file_not_found(self, migration_service):
        """Test backup restoration with missing backup file."""
        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service._restore_from_backup('/nonexistent/backup.db')

        assert "Failed to restore from backup" in str(exc_info.value)

    def test_verify_data_integrity_success(self, migration_service):
        """Test successful data integrity verification."""
        # Add valid test data
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 1000.0,
            'interest_rate': 2.5
        }
        account_id = migration_service.db_service.create_account(account_data)

        # Add historical snapshot
        migration_service.db_service.create_historical_snapshot(
            account_id, 1000.0, 'INITIAL_ENTRY'
        )

        # Should not raise any exceptions
        migration_service._verify_data_integrity()

    def test_verify_data_integrity_orphaned_snapshots(self, migration_service):
        """Test data integrity check with orphaned historical snapshots."""
        # Create orphaned historical snapshot by temporarily disabling foreign keys
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute('PRAGMA foreign_keys = OFF')
        cursor.execute('''
            INSERT INTO historical_snapshots (id, account_id, timestamp, value, change_type)
            VALUES (?, ?, ?, ?, ?)
        ''', ('test-snapshot', 'nonexistent-account', int(datetime.now().timestamp()), 1000.0, 'TEST'))
        migration_service.db_service.connection.commit()
        cursor.execute('PRAGMA foreign_keys = ON')

        with pytest.raises(DataIntegrityError) as exc_info:
            migration_service._verify_data_integrity()

        assert "Foreign key constraint violations" in str(exc_info.value)

    def test_verify_data_integrity_orphaned_positions(self, migration_service):
        """Test data integrity check with orphaned stock positions."""
        # Create orphaned stock position by temporarily disabling foreign keys
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute('PRAGMA foreign_keys = OFF')
        cursor.execute('''
            INSERT INTO stock_positions (id, trading_account_id, symbol, shares, purchase_price, purchase_date)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', ('test-position', 'nonexistent-account', 'TEST', 100.0, 50.0, int(datetime.now().timestamp())))
        migration_service.db_service.connection.commit()
        cursor.execute('PRAGMA foreign_keys = ON')

        with pytest.raises(DataIntegrityError) as exc_info:
            migration_service._verify_data_integrity()

        assert "Foreign key constraint violations" in str(exc_info.value)

    def test_apply_migration_success(self, migration_service):
        """Test successful migration application."""
        # Mock migration function
        mock_migration = Mock()
        migration_service.migrations[99] = mock_migration

        migration_service._apply_migration(99)

        mock_migration.assert_called_once()

    def test_apply_migration_not_found(self, migration_service):
        """Test migration application with non-existent version."""
        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service._apply_migration(999)

        assert "No migration available for version 999" in str(exc_info.value)

    def test_apply_migration_failure(self, migration_service):
        """Test migration application failure."""
        # Mock migration function that raises error
        def failing_migration():
            raise Exception("Migration failed")

        migration_service.migrations[99] = failing_migration

        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service._apply_migration(99)

        assert "Failed to apply migration to version 99" in str(exc_info.value)

    def test_update_schema_version(self, migration_service):
        """Test schema version update."""
        migration_service._update_schema_version(5)

        version = migration_service.get_current_schema_version()
        assert version == 5

    def test_migrate_to_latest_no_migration_needed(self, migration_service):
        """Test migrate_to_latest when no migration is needed."""
        # Set current version to target
        target = migration_service.get_target_schema_version()
        migration_service.db_service.set_setting('schema_version', str(target))

        result = migration_service.migrate_to_latest()
        assert result is False

    def test_migrate_to_latest_success(self, migration_service):
        """Test successful migration to latest version."""
        # Set current version to 1
        migration_service.db_service.set_setting('schema_version', '1')

        # Mock backup creation and migrations
        with patch.object(migration_service, '_create_backup', return_value='/tmp/backup.db'):
            with patch.object(migration_service, '_apply_migration'):
                with patch.object(migration_service, '_verify_data_integrity'):
                    result = migration_service.migrate_to_latest()

        assert result is True

    def test_migrate_to_latest_failure_with_restore(self, migration_service):
        """Test migration failure with successful backup restore."""
        # Set current version to 1
        migration_service.db_service.set_setting('schema_version', '1')

        backup_path = '/tmp/backup.db'

        with patch.object(migration_service, '_create_backup', return_value=backup_path):
            with patch.object(migration_service, '_apply_migration', side_effect=Exception("Migration failed")):
                with patch.object(migration_service, '_restore_from_backup') as mock_restore:
                    with pytest.raises(DatabaseMigrationError):
                        migration_service.migrate_to_latest()

                    mock_restore.assert_called_once_with(backup_path)

    def test_migrate_to_latest_failure_with_restore_failure(self, migration_service):
        """Test migration failure with backup restore failure."""
        # Set current version to 1
        migration_service.db_service.set_setting('schema_version', '1')

        backup_path = '/tmp/backup.db'

        with patch.object(migration_service, '_create_backup', return_value=backup_path):
            with patch.object(migration_service, '_apply_migration', side_effect=Exception("Migration failed")):
                with patch.object(migration_service, '_restore_from_backup', side_effect=Exception("Restore failed")):
                    with pytest.raises(DatabaseMigrationError) as exc_info:
                        migration_service.migrate_to_latest()

                    assert "Migration failed and backup restoration failed" in str(exc_info.value)

    def test_migration_v2_i_bonds_support(self, migration_service):
        """Test migration to version 2 (I-bonds support)."""
        # Should not raise any exceptions
        migration_service._migrate_to_v2_add_i_bonds_support()

        # Verify index was created
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_accounts_maturity_date'")
        result = cursor.fetchone()
        assert result is not None

    def test_migration_v2_missing_accounts_table(self, migration_service):
        """Test migration v2 with missing accounts table."""
        # Drop accounts table to simulate corruption
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute("DROP TABLE accounts")
        migration_service.db_service.connection.commit()

        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service._migrate_to_v2_add_i_bonds_support()

        assert "Accounts table not found" in str(exc_info.value)

    def test_migration_v3_metadata_column(self, migration_service):
        """Test migration to version 3 (metadata column)."""
        # Should not raise any exceptions
        migration_service._migrate_to_v3_add_metadata_column()

        # Verify metadata column was added to accounts table
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute("PRAGMA table_info(accounts)")
        columns = [column[1] for column in cursor.fetchall()]
        assert 'metadata' in columns

        # Verify metadata column was added to historical_snapshots table
        cursor.execute("PRAGMA table_info(historical_snapshots)")
        columns = [column[1] for column in cursor.fetchall()]
        assert 'metadata' in columns

    def test_migration_v4_broker_support(self, migration_service):
        """Test migration to version 4 (enhanced broker support)."""
        # Should not raise any exceptions
        migration_service._migrate_to_v4_add_broker_support()

        # Verify broker index was created
        cursor = migration_service.db_service.connect().cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_accounts_broker'")
        result = cursor.fetchone()
        assert result is not None

        # Verify institution-type index was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index' AND name='idx_accounts_institution_type'")
        result = cursor.fetchone()
        assert result is not None

    def test_add_custom_migration(self, migration_service):
        """Test adding custom migration."""
        def custom_migration():
            pass

        migration_service.add_custom_migration(10, custom_migration)

        assert 10 in migration_service.migrations
        assert migration_service.migrations[10] == custom_migration

    def test_add_custom_migration_duplicate_version(self, migration_service):
        """Test adding custom migration with duplicate version."""
        def custom_migration():
            pass

        with pytest.raises(ValueError) as exc_info:
            migration_service.add_custom_migration(2, custom_migration)  # Version 2 already exists

        assert "Migration version 2 already exists" in str(exc_info.value)

    def test_get_migration_history(self, migration_service):
        """Test getting migration history."""
        # Set current version to 2
        migration_service.db_service.set_setting('schema_version', '2')

        history = migration_service.get_migration_history()

        assert len(history) > 0
        assert all('version' in entry for entry in history)
        assert all('status' in entry for entry in history)
        assert all('description' in entry for entry in history)

        # Check that completed migrations are marked as such
        completed_migrations = [entry for entry in history if entry['status'] == 'completed']
        assert len(completed_migrations) >= 1  # At least version 2 should be completed

    def test_rollback_to_version_not_supported(self, migration_service):
        """Test rollback functionality (not implemented)."""
        # Set current version to 2 so we can test rollback to 1 (single version)
        migration_service.db_service.set_setting('schema_version', '2')

        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service.rollback_to_version(1)

        assert "Rollback not implemented" in str(exc_info.value)

    def test_rollback_invalid_target_version(self, migration_service):
        """Test rollback with invalid target version."""
        # Set current version to 2
        migration_service.db_service.set_setting('schema_version', '2')

        # Try to rollback to same or higher version
        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service.rollback_to_version(2)

        assert "Cannot rollback from version 2 to 2" in str(exc_info.value)

    def test_rollback_multiple_versions(self, migration_service):
        """Test rollback across multiple versions (not supported)."""
        # Set current version to 4
        migration_service.db_service.set_setting('schema_version', '4')

        # Try to rollback multiple versions
        with pytest.raises(DatabaseMigrationError) as exc_info:
            migration_service.rollback_to_version(2)

        assert "Rollback only supported to immediately previous version" in str(exc_info.value)


class TestMigrationIntegration:
    """Integration tests for migration system with database service."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        service = EncryptionService()
        service.derive_key("test_password_123")
        return service

    def test_database_service_runs_migrations_on_init(self, temp_db_path, encryption_service):
        """Test that database service runs migrations during initialization."""
        # Create database service - should trigger migration check
        db_service = DatabaseService(temp_db_path, encryption_service)

        with patch('services.migration.DatabaseMigration') as mock_migration_class:
            mock_migration = Mock()
            mock_migration.needs_migration.return_value = True
            mock_migration.migrate_to_latest.return_value = True
            mock_migration_class.return_value = mock_migration

            db_service.connect()

            # Verify migration was checked and executed
            mock_migration_class.assert_called_once_with(db_service)
            mock_migration.needs_migration.assert_called_once()
            mock_migration.migrate_to_latest.assert_called_once()

    def test_database_service_handles_migration_failure(self, temp_db_path, encryption_service):
        """Test that database service handles migration failures gracefully."""
        db_service = DatabaseService(temp_db_path, encryption_service)

        with patch('services.migration.DatabaseMigration') as mock_migration_class:
            mock_migration = Mock()
            mock_migration.needs_migration.return_value = True
            mock_migration.migrate_to_latest.side_effect = DatabaseMigrationError("Migration failed")
            mock_migration_class.return_value = mock_migration

            # Should not raise exception - migration failure is logged but doesn't prevent startup
            db_service.connect()

            # Database should still be functional
            assert db_service.connection is not None

    def test_end_to_end_migration_with_data_preservation(self, temp_db_path, encryption_service):
        """Test end-to-end migration with actual data preservation."""
        # Create database with initial data
        db_service = DatabaseService(temp_db_path, encryption_service)
        db_service.connect()

        # Add test account
        account_data = {
            'name': 'Test Savings',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0,
            'interest_rate': 2.5
        }
        account_id = db_service.create_account(account_data)

        # Add historical snapshot
        snapshot_id = db_service.create_historical_snapshot(
            account_id, 5000.0, 'INITIAL_ENTRY'
        )

        # Set schema version to 1 to trigger migration
        db_service.set_setting('schema_version', '1')

        # Create migration service and run migration
        migration = DatabaseMigration(db_service)
        result = migration.migrate_to_latest()

        # Verify migration ran
        assert result is True

        # Verify data is preserved
        retrieved_account = db_service.get_account(account_id)
        assert retrieved_account is not None
        assert retrieved_account['name'] == 'Test Savings'
        assert retrieved_account['current_balance'] == 5000.0

        # Verify historical data is preserved
        snapshots = db_service.get_historical_snapshots(account_id)
        assert len(snapshots) == 1
        assert snapshots[0]['value'] == 5000.0

        # Verify schema version was updated
        final_version = migration.get_current_schema_version()
        assert final_version > 1


if __name__ == '__main__':
    pytest.main([__file__])