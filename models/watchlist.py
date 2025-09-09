"""
Watchlist data models for the networth tracker application.

This module contains the WatchlistItem model for tracking stocks
without necessarily owning them.
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime
import uuid


@dataclass
class WatchlistItem:
    """Individual stock item in the watchlist."""
    id: str
    symbol: str
    notes: Optional[str] = None
    added_date: Optional[datetime] = None
    current_price: Optional[float] = None
    last_price_update: Optional[datetime] = None
    daily_change: Optional[float] = None
    daily_change_percent: Optional[float] = None

    def __post_init__(self):
        """Validate watchlist item data after initialization."""
        if not self.id or not self.id.strip():
            raise ValueError("Watchlist item ID cannot be empty")
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Stock symbol cannot be empty")

        # Normalize symbol to uppercase
        self.symbol = self.symbol.upper().strip()

        # Validate symbol format (basic check for common patterns)
        if not self.symbol.replace('.', '').replace('-', '').isalnum():
            raise ValueError("Stock symbol contains invalid characters")

        if len(self.symbol) > 10:  # Most stock symbols are 1-5 characters, some can be longer
            raise ValueError("Stock symbol is too long")

        if self.added_date is None:
            self.added_date = datetime.now()
        elif self.added_date > datetime.now():
            raise ValueError("Added date cannot be in the future")

        if self.current_price is not None and self.current_price < 0:
            raise ValueError("Current price cannot be negative")

        if self.last_price_update is not None and self.last_price_update > datetime.now():
            raise ValueError("Last price update cannot be in the future")

        # Validate daily change values are consistent
        if self.daily_change is not None and self.current_price is not None:
            if self.current_price == 0 and self.daily_change != 0:
                raise ValueError("Daily change must be zero when current price is zero")

        if self.daily_change_percent is not None:
            if abs(self.daily_change_percent) > 100:
                # Allow for extreme cases but warn about unrealistic values
                pass  # Could add logging here in the future

    def to_dict(self) -> Dict[str, Any]:
        """Convert watchlist item to dictionary representation."""
        data = asdict(self)
        # Convert datetime objects to ISO format strings
        if self.added_date:
            data['added_date'] = self.added_date.isoformat()
        if self.last_price_update:
            data['last_price_update'] = self.last_price_update.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WatchlistItem':
        """Create watchlist item instance from dictionary."""
        # Convert ISO format strings back to datetime objects
        if data.get('added_date'):
            data['added_date'] = datetime.fromisoformat(data['added_date'])
        if data.get('last_price_update'):
            data['last_price_update'] = datetime.fromisoformat(data['last_price_update'])
        return cls(**data)

    @classmethod
    def create_new(cls, symbol: str, notes: Optional[str] = None) -> 'WatchlistItem':
        """Create a new watchlist item with generated ID and current timestamp."""
        return cls(
            id=str(uuid.uuid4()),
            symbol=symbol,
            notes=notes,
            added_date=datetime.now()
        )

    def update_price(self, current_price: float, daily_change: Optional[float] = None,
                    daily_change_percent: Optional[float] = None) -> None:
        """Update price information for the watchlist item."""
        if current_price < 0:
            raise ValueError("Current price cannot be negative")

        self.current_price = current_price
        self.daily_change = daily_change
        self.daily_change_percent = daily_change_percent
        self.last_price_update = datetime.now()

    def has_price_data(self) -> bool:
        """Check if the item has current price data."""
        return self.current_price is not None

    def is_price_data_stale(self, max_age_hours: int = 24) -> bool:
        """Check if price data is older than the specified hours."""
        if not self.has_price_data() or self.last_price_update is None:
            return True

        age = datetime.now() - self.last_price_update
        return age.total_seconds() > (max_age_hours * 3600)

    def get_display_name(self) -> str:
        """Get a display-friendly name for the watchlist item."""
        if self.notes and self.notes.strip():
            return f"{self.symbol} - {self.notes.strip()}"
        return self.symbol

    def clear_price_data(self) -> None:
        """Clear all price-related data (useful for error handling)."""
        self.current_price = None
        self.daily_change = None
        self.daily_change_percent = None
        self.last_price_update = None