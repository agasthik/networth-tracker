"""Tests for restore chronology preservation and atomic (transactional) imports.

These use real (temp-file) DatabaseService instances rather than mocks so that
the actual SQLite timestamp storage and transaction rollback behavior are
exercised end to end.
"""

import os
import tempfile
import unittest
from datetime import datetime

from services.auth import AuthenticationManager
from services.export_import import ExportImportService
from models.accounts import AccountFactory, AccountType


class TestImportChronologyAndAtomicity(unittest.TestCase):
    """Restore must preserve historical timestamps/IDs and be all-or-nothing."""

    PASSWORD = "TestPassword123!"

    def _make_db(self):
        fd, path = tempfile.mkstemp(suffix='.db')
        auth = AuthenticationManager(path)
        auth.set_master_password(self.PASSWORD)
        db = auth.db_service
        db.connect()
        service = ExportImportService(db, auth.encryption_service)
        self._cleanup.append((db, fd, path))
        return db, service

    def setUp(self):
        self._cleanup = []
        self.src_db, self.src_service = self._make_db()
        self.dst_db, self.dst_service = self._make_db()

    def tearDown(self):
        for db, fd, path in self._cleanup:
            db.close()
            os.close(fd)
            os.unlink(path)

    def _seed_account_with_history(self):
        """Create a savings account with two dated snapshots in the source DB."""
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="History Account",
            institution="Test Bank",
            current_balance=1000.0,
            interest_rate=1.5,
        )
        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        account_dict.pop('id', None)
        account_id = self.src_db.create_account(account_dict)

        old_ts = datetime(2024, 1, 1, 12, 0, 0)
        recent_ts = datetime(2024, 6, 1, 12, 0, 0)
        snap_id_1 = self.src_db.create_historical_snapshot(
            account_id, 900.0, 'INITIAL_ENTRY', None, timestamp=old_ts
        )
        snap_id_2 = self.src_db.create_historical_snapshot(
            account_id, 1000.0, 'MANUAL_UPDATE', None, timestamp=recent_ts
        )
        return {
            'old_ts': old_ts,
            'recent_ts': recent_ts,
            'snap_ids': {snap_id_1, snap_id_2},
        }

    def test_import_preserves_snapshot_timestamps_and_ids(self):
        """Restored snapshots keep their original timestamp and ID, not import time."""
        seeded = self._seed_account_with_history()

        backup = self.src_service.export_data(include_historical=True)
        results = self.dst_service.import_data(backup, overwrite_existing=False)

        self.assertEqual(results['historical_snapshots_imported'], 2)
        self.assertEqual(len(results['errors']), 0)

        accounts = self.dst_db.get_accounts()
        self.assertEqual(len(accounts), 1)
        new_account_id = accounts[0]['id']

        snapshots = self.dst_db.get_historical_snapshots(new_account_id)
        self.assertEqual(len(snapshots), 2)

        imported_timestamps = {s['timestamp'] for s in snapshots}
        self.assertEqual(
            imported_timestamps, {seeded['old_ts'], seeded['recent_ts']},
            "Imported snapshots did not preserve their original chronology",
        )

        imported_ids = {s['id'] for s in snapshots}
        self.assertEqual(
            imported_ids, seeded['snap_ids'],
            "Imported snapshots did not preserve their original IDs",
        )

    def test_transaction_rolls_back_on_failure(self):
        """A failure inside a transaction() block persists none of its writes."""
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Rollback Account",
            institution="Test Bank",
            current_balance=500.0,
            interest_rate=1.0,
        )
        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        account_dict.pop('id', None)
        account_id = self.dst_db.create_account(account_dict)

        with self.assertRaises(ValueError):
            with self.dst_db.transaction():
                self.dst_db.create_historical_snapshot(
                    account_id, 500.0, 'INITIAL_ENTRY', None,
                    timestamp=datetime(2024, 1, 1, 12, 0, 0),
                )
                # Simulate a hard failure part-way through the batch.
                raise ValueError("boom")

        # Nothing from the rolled-back block should have been committed.
        snapshots = self.dst_db.get_historical_snapshots(account_id)
        self.assertEqual(len(snapshots), 0)

    def test_transaction_commits_on_success(self):
        """A transaction() block that completes commits all of its writes atomically."""
        account = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Commit Account",
            institution="Test Bank",
            current_balance=500.0,
            interest_rate=1.0,
        )
        account_dict = account.to_dict()
        account_dict['type'] = account_dict['account_type']
        account_dict.pop('id', None)
        account_id = self.dst_db.create_account(account_dict)

        with self.dst_db.transaction():
            self.dst_db.create_historical_snapshot(account_id, 500.0, 'INITIAL_ENTRY')
            self.dst_db.create_historical_snapshot(account_id, 550.0, 'MANUAL_UPDATE')

        snapshots = self.dst_db.get_historical_snapshots(account_id)
        self.assertEqual(len(snapshots), 2)


if __name__ == '__main__':
    unittest.main()
