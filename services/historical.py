"""
Historical data tracking service for the networth tracker application.

This service handles:
- Automatic snapshot creation on account value updates
- Historical data retrieval with date range filtering
- Performance calculation utilities for gains/losses and trends
- Historical data analysis and reporting
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, date, timedelta
from dataclasses import dataclass
from enum import Enum

from models.accounts import HistoricalSnapshot, ChangeType, BaseAccount
from services.database import DatabaseService


class TrendDirection(Enum):
    """Enumeration for trend directions."""
    INCREASING = "INCREASING"
    DECREASING = "DECREASING"
    STABLE = "STABLE"


@dataclass
class PerformanceMetrics:
    """Performance metrics for an account over a time period."""
    start_value: float
    end_value: float
    absolute_change: float
    percentage_change: float
    trend_direction: TrendDirection
    volatility: float
    average_value: float
    min_value: float
    max_value: float
    total_snapshots: int


@dataclass
class TrendAnalysis:
    """Trend analysis for historical data."""
    direction: TrendDirection
    slope: float  # Rate of change per day
    r_squared: float  # Correlation coefficient squared (0-1)
    confidence: str  # HIGH, MEDIUM, LOW based on r_squared


class HistoricalDataService:
    """Service for managing historical data tracking and analysis."""

    def __init__(self, db_service: DatabaseService):
        """
        Initialize historical data service.

        Args:
            db_service: Database service instance
        """
        self.db_service = db_service

    def create_snapshot(self, account: BaseAccount, change_type: ChangeType,
                       metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a historical snapshot for an account.

        Args:
            account: Account to create snapshot for
            change_type: Type of change that triggered the snapshot
            metadata: Optional metadata dictionary

        Returns:
            Generated snapshot ID
        """
        current_value = account.get_current_value()

        # Add account information to metadata
        if metadata is None:
            metadata = {}

        metadata.update({
            'account_name': account.name,
            'account_type': account.account_type.value,
            'institution': account.institution
        })

        return self.db_service.create_historical_snapshot(
            account.id,
            current_value,
            change_type.value,
            metadata
        )

    def create_snapshot_if_value_changed(self, account: BaseAccount,
                                       previous_value: float,
                                       change_type: ChangeType,
                                       threshold: float = 0.01,
                                       metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """
        Create a snapshot only if the account value has changed significantly.

        Args:
            account: Account to check and potentially snapshot
            previous_value: Previous account value
            change_type: Type of change that triggered the check
            threshold: Minimum change threshold to create snapshot
            metadata: Optional metadata dictionary

        Returns:
            Snapshot ID if created, None if no significant change
        """
        current_value = account.get_current_value()

        if abs(current_value - previous_value) >= threshold:
            return self.create_snapshot(account, change_type, metadata)

        return None

    def get_historical_snapshots(self, account_id: str,
                               start_date: Optional[date] = None,
                               end_date: Optional[date] = None,
                               limit: Optional[int] = None) -> List[HistoricalSnapshot]:
        """
        Retrieve historical snapshots for an account with optional filtering.

        Args:
            account_id: Account ID to get snapshots for
            start_date: Optional start date filter
            end_date: Optional end date filter
            limit: Optional limit on number of results

        Returns:
            List of historical snapshots
        """
        # Convert dates to timestamps if provided
        start_timestamp = None
        end_timestamp = None

        if start_date:
            start_timestamp = int(datetime.combine(start_date, datetime.min.time()).timestamp())

        if end_date:
            # Include the entire end date by using end of day
            end_timestamp = int(datetime.combine(end_date, datetime.max.time()).timestamp())

        # Get snapshots from database
        snapshots_data = self.db_service.get_historical_snapshots(
            account_id, start_timestamp, end_timestamp
        )

        # Convert to HistoricalSnapshot objects
        snapshots = []
        for snapshot_data in snapshots_data:
            snapshot = HistoricalSnapshot(
                id=snapshot_data['id'],
                account_id=snapshot_data['account_id'],
                timestamp=snapshot_data['timestamp'],
                value=snapshot_data['value'],
                change_type=ChangeType(snapshot_data['change_type']),
                metadata=snapshot_data.get('metadata')
            )
            snapshots.append(snapshot)

        # Apply limit if specified
        if limit and limit > 0:
            snapshots = snapshots[:limit]

        return snapshots

    def calculate_performance_metrics(self, account_id: str,
                                    start_date: Optional[date] = None,
                                    end_date: Optional[date] = None) -> Optional[PerformanceMetrics]:
        """
        Calculate performance metrics for an account over a time period.

        Args:
            account_id: Account ID to analyze
            start_date: Optional start date (defaults to earliest snapshot)
            end_date: Optional end date (defaults to latest snapshot)

        Returns:
            PerformanceMetrics object or None if insufficient data
        """
        snapshots = self.get_historical_snapshots(account_id, start_date, end_date)

        if len(snapshots) < 2:
            return None

        # Sort snapshots by timestamp (oldest first)
        snapshots.sort(key=lambda s: s.timestamp)

        values = [s.value for s in snapshots]
        start_value = values[0]
        end_value = values[-1]

        # Calculate basic metrics
        absolute_change = end_value - start_value
        percentage_change = (absolute_change / start_value * 100) if start_value != 0 else 0.0

        # Determine trend direction
        if percentage_change > 1.0:  # More than 1% increase
            trend_direction = TrendDirection.INCREASING
        elif percentage_change < -1.0:  # More than 1% decrease
            trend_direction = TrendDirection.DECREASING
        else:
            trend_direction = TrendDirection.STABLE

        # Calculate statistical metrics
        average_value = sum(values) / len(values)
        min_value = min(values)
        max_value = max(values)

        # Calculate volatility (standard deviation)
        variance = sum((v - average_value) ** 2 for v in values) / len(values)
        volatility = variance ** 0.5

        return PerformanceMetrics(
            start_value=start_value,
            end_value=end_value,
            absolute_change=absolute_change,
            percentage_change=percentage_change,
            trend_direction=trend_direction,
            volatility=volatility,
            average_value=average_value,
            min_value=min_value,
            max_value=max_value,
            total_snapshots=len(snapshots)
        )

    def analyze_trend(self, account_id: str,
                     start_date: Optional[date] = None,
                     end_date: Optional[date] = None) -> Optional[TrendAnalysis]:
        """
        Analyze the trend of account values over time using linear regression.

        Args:
            account_id: Account ID to analyze
            start_date: Optional start date
            end_date: Optional end date

        Returns:
            TrendAnalysis object or None if insufficient data
        """
        snapshots = self.get_historical_snapshots(account_id, start_date, end_date)

        if len(snapshots) < 3:  # Need at least 3 points for meaningful trend analysis
            return None

        # Sort snapshots by timestamp
        snapshots.sort(key=lambda s: s.timestamp)

        # Prepare data for linear regression
        # Convert timestamps to days since first snapshot
        first_timestamp = snapshots[0].timestamp
        x_values = [(s.timestamp - first_timestamp).total_seconds() / 86400 for s in snapshots]  # Days
        y_values = [s.value for s in snapshots]

        # Calculate linear regression
        n = len(x_values)
        sum_x = sum(x_values)
        sum_y = sum(y_values)
        sum_xy = sum(x * y for x, y in zip(x_values, y_values))
        sum_x2 = sum(x * x for x in x_values)
        sum_y2 = sum(y * y for y in y_values)

        # Calculate slope (rate of change per day)
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            slope = 0.0
        else:
            slope = (n * sum_xy - sum_x * sum_y) / denominator

        # Calculate correlation coefficient (r-squared)
        numerator = n * sum_xy - sum_x * sum_y
        denominator_r = ((n * sum_x2 - sum_x * sum_x) * (n * sum_y2 - sum_y * sum_y)) ** 0.5

        if denominator_r == 0:
            r_squared = 0.0
        else:
            r = numerator / denominator_r
            r_squared = r * r

        # Determine trend direction
        if slope > 0.1:  # Increasing by more than $0.10 per day
            direction = TrendDirection.INCREASING
        elif slope < -0.1:  # Decreasing by more than $0.10 per day
            direction = TrendDirection.DECREASING
        else:
            direction = TrendDirection.STABLE

        # Determine confidence level based on r-squared
        if r_squared >= 0.7:
            confidence = "HIGH"
        elif r_squared >= 0.4:
            confidence = "MEDIUM"
        else:
            confidence = "LOW"

        return TrendAnalysis(
            direction=direction,
            slope=slope,
            r_squared=r_squared,
            confidence=confidence
        )

    def get_value_at_date(self, account_id: str, target_date: date) -> Optional[float]:
        """
        Get the account value closest to a specific date.

        Args:
            account_id: Account ID to query
            target_date: Target date to find value for

        Returns:
            Account value closest to the target date, or None if no data
        """
        # Get snapshots around the target date (±7 days)
        start_date = target_date - timedelta(days=7)
        end_date = target_date + timedelta(days=7)

        snapshots = self.get_historical_snapshots(account_id, start_date, end_date)

        if not snapshots:
            return None

        # Find the snapshot closest to the target date
        target_datetime = datetime.combine(target_date, datetime.min.time())
        closest_snapshot = min(snapshots,
                             key=lambda s: abs((s.timestamp - target_datetime).total_seconds()))

        return closest_snapshot.value

    def calculate_gains_losses(self, account_id: str,
                             period_days: int = 30) -> Dict[str, float]:
        """
        Calculate gains and losses over a specified period.

        Args:
            account_id: Account ID to analyze
            period_days: Number of days to look back (default 30)

        Returns:
            Dictionary with gain/loss metrics
        """
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)

        start_value = self.get_value_at_date(account_id, start_date)
        end_value = self.get_value_at_date(account_id, end_date)

        if start_value is None or end_value is None:
            return {
                'start_value': 0.0,
                'end_value': 0.0,
                'absolute_gain_loss': 0.0,
                'percentage_gain_loss': 0.0,
                'period_days': period_days
            }

        absolute_gain_loss = end_value - start_value
        percentage_gain_loss = (absolute_gain_loss / start_value * 100) if start_value != 0 else 0.0

        return {
            'start_value': start_value,
            'end_value': end_value,
            'absolute_gain_loss': absolute_gain_loss,
            'percentage_gain_loss': percentage_gain_loss,
            'period_days': period_days
        }

    def get_monthly_summary(self, account_id: str, year: int) -> List[Dict[str, Any]]:
        """
        Get monthly summary of account values for a specific year.

        Args:
            account_id: Account ID to analyze
            year: Year to get monthly summary for

        Returns:
            List of monthly summary dictionaries
        """
        monthly_summaries = []

        for month in range(1, 13):
            # Get first and last day of the month
            first_day = date(year, month, 1)
            if month == 12:
                last_day = date(year + 1, 1, 1) - timedelta(days=1)
            else:
                last_day = date(year, month + 1, 1) - timedelta(days=1)

            # Get snapshots for the month
            snapshots = self.get_historical_snapshots(account_id, first_day, last_day)

            if not snapshots:
                monthly_summaries.append({
                    'month': month,
                    'month_name': first_day.strftime('%B'),
                    'start_value': None,
                    'end_value': None,
                    'min_value': None,
                    'max_value': None,
                    'average_value': None,
                    'snapshots_count': 0
                })
                continue

            # Sort snapshots by timestamp
            snapshots.sort(key=lambda s: s.timestamp)
            values = [s.value for s in snapshots]

            monthly_summaries.append({
                'month': month,
                'month_name': first_day.strftime('%B'),
                'start_value': values[0],
                'end_value': values[-1],
                'min_value': min(values),
                'max_value': max(values),
                'average_value': sum(values) / len(values),
                'snapshots_count': len(snapshots)
            })

        return monthly_summaries

    def cleanup_old_snapshots(self, account_id: str, keep_days: int = 365) -> int:
        """
        Clean up old historical snapshots beyond the retention period.

        Args:
            account_id: Account ID to clean up
            keep_days: Number of days to keep (default 365)

        Returns:
            Number of snapshots deleted
        """
        cutoff_date = date.today() - timedelta(days=keep_days)
        cutoff_timestamp = int(datetime.combine(cutoff_date, datetime.min.time()).timestamp())

        # Get old snapshots
        cursor = self.db_service.connect().cursor()
        cursor.execute('''
            SELECT id FROM historical_snapshots
            WHERE account_id = ? AND timestamp < ?
        ''', (account_id, cutoff_timestamp))

        old_snapshot_ids = [row[0] for row in cursor.fetchall()]

        # Delete old snapshots
        if old_snapshot_ids:
            # Use individual DELETE statements for security
            for snapshot_id in old_snapshot_ids:
                cursor.execute('DELETE FROM historical_snapshots WHERE id = ?', (snapshot_id,))

            self.db_service.connection.commit()

        return len(old_snapshot_ids)