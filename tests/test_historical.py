"""
Unit tests for HistoricalDataService.

Tests cover:
- Automatic snapshot creation on account value updates
- Historical data retrieval with date range filtering
- Performance calculation utilities for gains/losses and trends
- Historical data analysis and reporting
"""

import unittest
import tempfile
import os
from datetime import datetime, date, timedelta
from unittest.mock import patch, MagicMock

from services.historical import (
    HistoricalDataService,
    PerformanceMetrics,
    TrendAnalysis,
    TrendDirection
)
from services.database import DatabaseService
from services.encryption import EncryptionService
from models.accounts import (
    HistoricalSnapshot,
    ChangeType,
    AccountFactory,
    AccountType,
    CDAccount
)


class TestHistoricalDataService(unittest.TestCase):
    """Test cases for HistoricalDataService class."""

    def setUp(self):
        """Set up test database and services."""
        # Create temporary database file
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

        # Initialize encryption service with test password
        self.encryption_service = EncryptionService()
        self.encryption_service.derive_key("test_password_123")

        # Initialize database service
        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

        # Initialize historical data service
        self.historical_service = HistoricalDataService(self.db_service)

        # Create test account
        self.test_account = AccountFactory.create_account(
            AccountType.CD,
            name="Test CD Account",
            institution="Test Bank",
            principal_amount=10000.0,
            interest_rate=2.5,
            maturity_date=date.today() + timedelta(days=365),
            current_value=10250.0
        )

        # Store the account in the database so foreign key constraints work
        account_dict = self.test_account.to_dict()
        account_dict['type'] = account_dict['account_type']
        if 'id' in account_dict:
            del account_dict['id']  # Let database service create its own ID

        # Create account in database and update test account ID
        account_id = self.db_service.create_account(account_dict)
        self.test_account.id = account_id

    def tearDown(self):
        """Clean up test database."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_create_snapshot(self):
        """Test creating a historical snapshot."""
        snapshot_id = self.historical_service.create_snapshot(
            self.test_account,
            ChangeType.INITIAL_ENTRY,
            {'note': 'Test snapshot'}
        )

        self.assertIsInstance(snapshot_id, str)
        self.assertTrue(len(snapshot_id) > 0)

        # Verify snapshot was created
        snapshots = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots), 1)

        snapshot = snapshots[0]
        self.assertEqual(snapshot.account_id, self.test_account.id)
        self.assertEqual(snapshot.value, 10250.0)
        self.assertEqual(snapshot.change_type, ChangeType.INITIAL_ENTRY)
        self.assertIn('note', snapshot.metadata)
        self.assertEqual(snapshot.metadata['note'], 'Test snapshot')
        self.assertEqual(snapshot.metadata['account_name'], 'Test CD Account')
        self.assertEqual(snapshot.metadata['account_type'], 'CD')

    def test_create_snapshot_if_value_changed_significant_change(self):
        """Test creating snapshot only when value changes significantly."""
        previous_value = 10000.0

        # Should create snapshot (change > threshold)
        snapshot_id = self.historical_service.create_snapshot_if_value_changed(
            self.test_account,
            previous_value,
            ChangeType.MANUAL_UPDATE,
            threshold=100.0
        )

        self.assertIsNotNone(snapshot_id)

        # Verify snapshot was created
        snapshots = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots), 1)

    def test_create_snapshot_if_value_changed_no_significant_change(self):
        """Test not creating snapshot when value change is below threshold."""
        previous_value = 10249.0  # Very close to current value of 10250.0

        # Should not create snapshot (change < threshold)
        snapshot_id = self.historical_service.create_snapshot_if_value_changed(
            self.test_account,
            previous_value,
            ChangeType.MANUAL_UPDATE,
            threshold=10.0
        )

        self.assertIsNone(snapshot_id)

        # Verify no snapshot was created
        snapshots = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots), 0)

    def test_get_historical_snapshots_no_filters(self):
        """Test retrieving all historical snapshots without filters."""
        # Create multiple snapshots
        for i in range(5):
            self.historical_service.create_snapshot(
                self.test_account,
                ChangeType.MANUAL_UPDATE,
                {'iteration': i}
            )

        snapshots = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots), 5)

        # Verify snapshots are sorted by timestamp (newest first)
        for i in range(len(snapshots) - 1):
            self.assertGreaterEqual(snapshots[i].timestamp, snapshots[i + 1].timestamp)

    def test_get_historical_snapshots_with_date_filters(self):
        """Test retrieving historical snapshots with date range filters."""
        now = datetime.now()

        # Create snapshots with different timestamps
        with patch('services.database.datetime') as mock_datetime:
            # Snapshot from 3 days ago
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=3)).timestamp()
            self.historical_service.create_snapshot(self.test_account, ChangeType.INITIAL_ENTRY)

            # Snapshot from 2 days ago
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=2)).timestamp()
            self.historical_service.create_snapshot(self.test_account, ChangeType.MANUAL_UPDATE)

            # Snapshot from 1 day ago
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=1)).timestamp()
            self.historical_service.create_snapshot(self.test_account, ChangeType.MANUAL_UPDATE)

        # Test with start date filter
        start_date = (now - timedelta(days=2)).date()
        snapshots = self.historical_service.get_historical_snapshots(
            self.test_account.id, start_date=start_date
        )
        self.assertEqual(len(snapshots), 2)

        # Test with end date filter
        end_date = (now - timedelta(days=2)).date()
        snapshots = self.historical_service.get_historical_snapshots(
            self.test_account.id, end_date=end_date
        )
        self.assertEqual(len(snapshots), 2)

        # Test with both start and end date filters
        snapshots = self.historical_service.get_historical_snapshots(
            self.test_account.id,
            start_date=(now - timedelta(days=2)).date(),
            end_date=(now - timedelta(days=1)).date()
        )
        self.assertEqual(len(snapshots), 2)

    def test_get_historical_snapshots_with_limit(self):
        """Test retrieving historical snapshots with limit."""
        # Create multiple snapshots
        for i in range(10):
            self.historical_service.create_snapshot(
                self.test_account,
                ChangeType.MANUAL_UPDATE
            )

        # Test with limit
        snapshots = self.historical_service.get_historical_snapshots(
            self.test_account.id, limit=5
        )
        self.assertEqual(len(snapshots), 5)

    def test_calculate_performance_metrics_sufficient_data(self):
        """Test calculating performance metrics with sufficient data."""
        now = datetime.now()

        # Create snapshots with different values and timestamps
        with patch('services.database.datetime') as mock_datetime:
            # Initial snapshot: $10,000
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=30)).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10000.0, 'INITIAL_ENTRY'
            )

            # Middle snapshot: $10,500
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=15)).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10500.0, 'MANUAL_UPDATE'
            )

            # Final snapshot: $11,000
            mock_datetime.now.return_value.timestamp.return_value = now.timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 11000.0, 'MANUAL_UPDATE'
            )

        performance = self.historical_service.calculate_performance_metrics(self.test_account.id)

        self.assertIsNotNone(performance)
        self.assertEqual(performance.start_value, 10000.0)
        self.assertEqual(performance.end_value, 11000.0)
        self.assertEqual(performance.absolute_change, 1000.0)
        self.assertEqual(performance.percentage_change, 10.0)
        self.assertEqual(performance.trend_direction, TrendDirection.INCREASING)
        self.assertEqual(performance.min_value, 10000.0)
        self.assertEqual(performance.max_value, 11000.0)
        self.assertEqual(performance.total_snapshots, 3)
        self.assertAlmostEqual(performance.average_value, 10500.0, places=2)

    def test_calculate_performance_metrics_insufficient_data(self):
        """Test calculating performance metrics with insufficient data."""
        # Create only one snapshot
        self.historical_service.create_snapshot(self.test_account, ChangeType.INITIAL_ENTRY)

        performance = self.historical_service.calculate_performance_metrics(self.test_account.id)
        self.assertIsNone(performance)

    def test_calculate_performance_metrics_stable_trend(self):
        """Test calculating performance metrics with stable trend."""
        now = datetime.now()

        # Create snapshots with minimal change (stable trend)
        with patch('services.database.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=30)).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10000.0, 'INITIAL_ENTRY'
            )

            mock_datetime.now.return_value.timestamp.return_value = now.timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10050.0, 'MANUAL_UPDATE'  # 0.5% change
            )

        performance = self.historical_service.calculate_performance_metrics(self.test_account.id)

        self.assertIsNotNone(performance)
        self.assertEqual(performance.trend_direction, TrendDirection.STABLE)

    def test_calculate_performance_metrics_decreasing_trend(self):
        """Test calculating performance metrics with decreasing trend."""
        now = datetime.now()

        # Create snapshots with decreasing values
        with patch('services.database.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=30)).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10000.0, 'INITIAL_ENTRY'
            )

            mock_datetime.now.return_value.timestamp.return_value = now.timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 9000.0, 'MANUAL_UPDATE'  # -10% change
            )

        performance = self.historical_service.calculate_performance_metrics(self.test_account.id)

        self.assertIsNotNone(performance)
        self.assertEqual(performance.trend_direction, TrendDirection.DECREASING)
        self.assertEqual(performance.percentage_change, -10.0)

    def test_analyze_trend_sufficient_data(self):
        """Test trend analysis with sufficient data."""
        now = datetime.now()

        # Create snapshots with clear upward trend
        with patch('services.database.datetime') as mock_datetime:
            for i in range(5):
                timestamp = now - timedelta(days=30 - i * 7)  # Weekly snapshots
                value = 10000.0 + i * 500.0  # Increasing by $500 each week

                mock_datetime.now.return_value.timestamp.return_value = timestamp.timestamp()
                self.db_service.create_historical_snapshot(
                    self.test_account.id, value, 'MANUAL_UPDATE'
                )

        trend = self.historical_service.analyze_trend(self.test_account.id)

        self.assertIsNotNone(trend)
        self.assertEqual(trend.direction, TrendDirection.INCREASING)
        self.assertGreater(trend.slope, 0)  # Positive slope for increasing trend
        self.assertGreater(trend.r_squared, 0.8)  # High correlation for linear trend
        self.assertEqual(trend.confidence, "HIGH")

    def test_analyze_trend_insufficient_data(self):
        """Test trend analysis with insufficient data."""
        # Create only 2 snapshots (need at least 3)
        for i in range(2):
            self.historical_service.create_snapshot(self.test_account, ChangeType.MANUAL_UPDATE)

        trend = self.historical_service.analyze_trend(self.test_account.id)
        self.assertIsNone(trend)

    def test_analyze_trend_stable_data(self):
        """Test trend analysis with stable data."""
        now = datetime.now()

        # Create snapshots with stable values
        with patch('services.database.datetime') as mock_datetime:
            for i in range(5):
                timestamp = now - timedelta(days=30 - i * 7)
                value = 10000.0  # Same value each time

                mock_datetime.now.return_value.timestamp.return_value = timestamp.timestamp()
                self.db_service.create_historical_snapshot(
                    self.test_account.id, value, 'MANUAL_UPDATE'
                )

        trend = self.historical_service.analyze_trend(self.test_account.id)

        self.assertIsNotNone(trend)
        self.assertEqual(trend.direction, TrendDirection.STABLE)
        self.assertAlmostEqual(trend.slope, 0.0, places=1)

    def test_get_value_at_date_exact_match(self):
        """Test getting value at a specific date with exact match."""
        target_date = date.today() - timedelta(days=5)

        with patch('services.database.datetime') as mock_datetime:
            mock_datetime.now.return_value.timestamp.return_value = datetime.combine(
                target_date, datetime.min.time()
            ).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10500.0, 'MANUAL_UPDATE'
            )

        value = self.historical_service.get_value_at_date(self.test_account.id, target_date)
        self.assertEqual(value, 10500.0)

    def test_get_value_at_date_closest_match(self):
        """Test getting value at a specific date with closest match."""
        target_date = date.today() - timedelta(days=5)

        with patch('services.database.datetime') as mock_datetime:
            # Create snapshot 2 days before target
            mock_datetime.now.return_value.timestamp.return_value = datetime.combine(
                target_date - timedelta(days=2), datetime.min.time()
            ).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10300.0, 'MANUAL_UPDATE'
            )

            # Create snapshot 3 days after target (farther away)
            mock_datetime.now.return_value.timestamp.return_value = datetime.combine(
                target_date + timedelta(days=3), datetime.min.time()
            ).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10700.0, 'MANUAL_UPDATE'
            )

        value = self.historical_service.get_value_at_date(self.test_account.id, target_date)
        self.assertEqual(value, 10300.0)  # Should return the closer snapshot

    def test_get_value_at_date_no_data(self):
        """Test getting value at a specific date with no data."""
        target_date = date.today() - timedelta(days=5)

        value = self.historical_service.get_value_at_date(self.test_account.id, target_date)
        self.assertIsNone(value)

    def test_calculate_gains_losses_with_data(self):
        """Test calculating gains and losses with available data."""
        now = datetime.now()

        with patch('services.database.datetime') as mock_datetime:
            # Snapshot 30 days ago: $10,000
            mock_datetime.now.return_value.timestamp.return_value = (now - timedelta(days=30)).timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 10000.0, 'INITIAL_ENTRY'
            )

            # Snapshot today: $11,000
            mock_datetime.now.return_value.timestamp.return_value = now.timestamp()
            self.db_service.create_historical_snapshot(
                self.test_account.id, 11000.0, 'MANUAL_UPDATE'
            )

        gains_losses = self.historical_service.calculate_gains_losses(self.test_account.id, 30)

        self.assertEqual(gains_losses['start_value'], 10000.0)
        self.assertEqual(gains_losses['end_value'], 11000.0)
        self.assertEqual(gains_losses['absolute_gain_loss'], 1000.0)
        self.assertEqual(gains_losses['percentage_gain_loss'], 10.0)
        self.assertEqual(gains_losses['period_days'], 30)

    def test_calculate_gains_losses_no_data(self):
        """Test calculating gains and losses with no data."""
        gains_losses = self.historical_service.calculate_gains_losses(self.test_account.id, 30)

        self.assertEqual(gains_losses['start_value'], 0.0)
        self.assertEqual(gains_losses['end_value'], 0.0)
        self.assertEqual(gains_losses['absolute_gain_loss'], 0.0)
        self.assertEqual(gains_losses['percentage_gain_loss'], 0.0)
        self.assertEqual(gains_losses['period_days'], 30)

    def test_get_monthly_summary_with_data(self):
        """Test getting monthly summary with data."""
        year = 2024
        now = datetime(year, 6, 15)  # June 15, 2024

        with patch('services.database.datetime') as mock_datetime:
            # Create snapshots for different months
            for month in [1, 3, 6]:  # January, March, June
                for day in [1, 15, 28]:  # Beginning, middle, end of month
                    timestamp = datetime(year, month, day)
                    value = 10000.0 + month * 100 + day * 10  # Varying values

                    mock_datetime.now.return_value.timestamp.return_value = timestamp.timestamp()
                    self.db_service.create_historical_snapshot(
                        self.test_account.id, value, 'MANUAL_UPDATE'
                    )

        monthly_summary = self.historical_service.get_monthly_summary(self.test_account.id, year)

        self.assertEqual(len(monthly_summary), 12)  # 12 months

        # Check January (has data)
        january = monthly_summary[0]
        self.assertEqual(january['month'], 1)
        self.assertEqual(january['month_name'], 'January')
        self.assertIsNotNone(january['start_value'])
        self.assertIsNotNone(january['end_value'])
        self.assertEqual(january['snapshots_count'], 3)

        # Check February (no data)
        february = monthly_summary[1]
        self.assertEqual(february['month'], 2)
        self.assertEqual(february['month_name'], 'February')
        self.assertIsNone(february['start_value'])
        self.assertEqual(february['snapshots_count'], 0)

    def test_get_monthly_summary_no_data(self):
        """Test getting monthly summary with no data."""
        year = 2024

        monthly_summary = self.historical_service.get_monthly_summary(self.test_account.id, year)

        self.assertEqual(len(monthly_summary), 12)

        # All months should have no data
        for month_data in monthly_summary:
            self.assertIsNone(month_data['start_value'])
            self.assertIsNone(month_data['end_value'])
            self.assertEqual(month_data['snapshots_count'], 0)

    def test_cleanup_old_snapshots(self):
        """Test cleaning up old historical snapshots."""
        now = datetime.now()

        with patch('services.database.datetime') as mock_datetime:
            # Create old snapshots (older than retention period)
            for i in range(3):
                timestamp = now - timedelta(days=400 + i)  # Older than 365 days
                mock_datetime.now.return_value.timestamp.return_value = timestamp.timestamp()
                self.db_service.create_historical_snapshot(
                    self.test_account.id, 10000.0 + i * 100, 'MANUAL_UPDATE'
                )

            # Create recent snapshots (within retention period)
            for i in range(2):
                timestamp = now - timedelta(days=100 + i)  # Within 365 days
                mock_datetime.now.return_value.timestamp.return_value = timestamp.timestamp()
                self.db_service.create_historical_snapshot(
                    self.test_account.id, 11000.0 + i * 100, 'MANUAL_UPDATE'
                )

        # Verify we have 5 snapshots total
        snapshots_before = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots_before), 5)

        # Clean up old snapshots (keep 365 days)
        deleted_count = self.historical_service.cleanup_old_snapshots(self.test_account.id, 365)

        self.assertEqual(deleted_count, 3)  # Should delete 3 old snapshots

        # Verify only recent snapshots remain
        snapshots_after = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots_after), 2)

    def test_cleanup_old_snapshots_no_old_data(self):
        """Test cleaning up old snapshots when there are none."""
        # Create only recent snapshots
        for i in range(3):
            self.historical_service.create_snapshot(self.test_account, ChangeType.MANUAL_UPDATE)

        deleted_count = self.historical_service.cleanup_old_snapshots(self.test_account.id, 365)

        self.assertEqual(deleted_count, 0)  # Should delete nothing

        # Verify all snapshots remain
        snapshots = self.historical_service.get_historical_snapshots(self.test_account.id)
        self.assertEqual(len(snapshots), 3)


class TestPerformanceMetrics(unittest.TestCase):
    """Test cases for PerformanceMetrics dataclass."""

    def test_performance_metrics_creation(self):
        """Test creating PerformanceMetrics instance."""
        metrics = PerformanceMetrics(
            start_value=10000.0,
            end_value=11000.0,
            absolute_change=1000.0,
            percentage_change=10.0,
            trend_direction=TrendDirection.INCREASING,
            volatility=150.0,
            average_value=10500.0,
            min_value=9800.0,
            max_value=11200.0,
            total_snapshots=10
        )

        self.assertEqual(metrics.start_value, 10000.0)
        self.assertEqual(metrics.end_value, 11000.0)
        self.assertEqual(metrics.absolute_change, 1000.0)
        self.assertEqual(metrics.percentage_change, 10.0)
        self.assertEqual(metrics.trend_direction, TrendDirection.INCREASING)
        self.assertEqual(metrics.volatility, 150.0)
        self.assertEqual(metrics.average_value, 10500.0)
        self.assertEqual(metrics.min_value, 9800.0)
        self.assertEqual(metrics.max_value, 11200.0)
        self.assertEqual(metrics.total_snapshots, 10)


class TestTrendAnalysis(unittest.TestCase):
    """Test cases for TrendAnalysis dataclass."""

    def test_trend_analysis_creation(self):
        """Test creating TrendAnalysis instance."""
        trend = TrendAnalysis(
            direction=TrendDirection.INCREASING,
            slope=15.5,
            r_squared=0.85,
            confidence="HIGH"
        )

        self.assertEqual(trend.direction, TrendDirection.INCREASING)
        self.assertEqual(trend.slope, 15.5)
        self.assertEqual(trend.r_squared, 0.85)
        self.assertEqual(trend.confidence, "HIGH")


class TestTrendDirection(unittest.TestCase):
    """Test cases for TrendDirection enum."""

    def test_trend_direction_values(self):
        """Test that all expected trend directions are defined."""
        self.assertEqual(TrendDirection.INCREASING.value, "INCREASING")
        self.assertEqual(TrendDirection.DECREASING.value, "DECREASING")
        self.assertEqual(TrendDirection.STABLE.value, "STABLE")


if __name__ == '__main__':
    unittest.main()