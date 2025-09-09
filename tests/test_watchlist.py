"""
Unit tests for watchlist data models.

Tests cover:
- WatchlistItem model validation and functionality
- Data validation and error handling
- Serialization/deserialization (to_dict/from_dict methods)
- Price update functionality
- Helper methods and utilities
"""

import pytest
from datetime import datetime, timedelta
from models.watchlist import WatchlistItem


class TestWatchlistItem:
    """Test WatchlistItem model."""

    def test_create_valid_watchlist_item(self):
        """Test creating a valid watchlist item."""
        item = WatchlistItem(
            id="test-id",
            symbol="AAPL",
            notes="Apple Inc.",
            added_date=datetime.now()
        )
        assert item.id == "test-id"
        assert item.symbol == "AAPL"
        assert item.notes == "Apple Inc."
        assert item.added_date is not None
        assert item.current_price is None
        assert item.last_price_update is None
        assert item.daily_change is None
        assert item.daily_change_percent is None

    def test_create_new_class_method(self):
        """Test creating a new watchlist item using class method."""
        item = WatchlistItem.create_new("GOOGL", "Google Inc.")
        assert item.id is not None
        assert len(item.id) > 0
        assert item.symbol == "GOOGL"
        assert item.notes == "Google Inc."
        assert item.added_date is not None
        assert isinstance(item.added_date, datetime)

    def test_symbol_normalization(self):
        """Test that symbols are normalized to uppercase."""
        item = WatchlistItem.create_new("aapl")
        assert item.symbol == "AAPL"

        item = WatchlistItem.create_new("  tsla  ")
        assert item.symbol == "TSLA"

    def test_empty_id_validation(self):
        """Test validation for empty ID."""
        with pytest.raises(ValueError, match="Watchlist item ID cannot be empty"):
            WatchlistItem(id="", symbol="AAPL")

        with pytest.raises(ValueError, match="Watchlist item ID cannot be empty"):
            WatchlistItem(id="   ", symbol="AAPL")

    def test_empty_symbol_validation(self):
        """Test validation for empty symbol."""
        with pytest.raises(ValueError, match="Stock symbol cannot be empty"):
            WatchlistItem(id="test-id", symbol="")

        with pytest.raises(ValueError, match="Stock symbol cannot be empty"):
            WatchlistItem(id="test-id", symbol="   ")

    def test_invalid_symbol_characters(self):
        """Test validation for invalid symbol characters."""
        with pytest.raises(ValueError, match="Stock symbol contains invalid characters"):
            WatchlistItem(id="test-id", symbol="AAPL@")

        with pytest.raises(ValueError, match="Stock symbol contains invalid characters"):
            WatchlistItem(id="test-id", symbol="TEST#")

    def test_symbol_too_long(self):
        """Test validation for symbol length."""
        with pytest.raises(ValueError, match="Stock symbol is too long"):
            WatchlistItem(id="test-id", symbol="VERYLONGSYMBOL")

    def test_valid_symbol_formats(self):
        """Test that valid symbol formats are accepted."""
        # Standard symbols
        item1 = WatchlistItem.create_new("AAPL")
        assert item1.symbol == "AAPL"

        # Symbols with dots (common for some exchanges)
        item2 = WatchlistItem.create_new("BRK.A")
        assert item2.symbol == "BRK.A"

        # Symbols with dashes
        item3 = WatchlistItem.create_new("BRK-A")
        assert item3.symbol == "BRK-A"

    def test_future_added_date_validation(self):
        """Test validation for future added date."""
        future_date = datetime.now() + timedelta(days=1)
        with pytest.raises(ValueError, match="Added date cannot be in the future"):
            WatchlistItem(id="test-id", symbol="AAPL", added_date=future_date)

    def test_negative_price_validation(self):
        """Test validation for negative current price."""
        with pytest.raises(ValueError, match="Current price cannot be negative"):
            WatchlistItem(id="test-id", symbol="AAPL", current_price=-10.0)

    def test_future_price_update_validation(self):
        """Test validation for future price update timestamp."""
        future_date = datetime.now() + timedelta(hours=1)
        with pytest.raises(ValueError, match="Last price update cannot be in the future"):
            WatchlistItem(id="test-id", symbol="AAPL", last_price_update=future_date)

    def test_default_added_date(self):
        """Test that added_date defaults to current time when None."""
        before = datetime.now()
        item = WatchlistItem(id="test-id", symbol="AAPL")
        after = datetime.now()

        assert before <= item.added_date <= after

    def test_update_price(self):
        """Test updating price information."""
        item = WatchlistItem.create_new("AAPL")

        # Update with all price data
        item.update_price(150.0, 2.5, 1.69)

        assert item.current_price == 150.0
        assert item.daily_change == 2.5
        assert item.daily_change_percent == 1.69
        assert item.last_price_update is not None
        assert isinstance(item.last_price_update, datetime)

    def test_update_price_negative_validation(self):
        """Test that update_price validates negative prices."""
        item = WatchlistItem.create_new("AAPL")

        with pytest.raises(ValueError, match="Current price cannot be negative"):
            item.update_price(-10.0)

    def test_has_price_data(self):
        """Test has_price_data method."""
        item = WatchlistItem.create_new("AAPL")

        # Initially no price data
        assert not item.has_price_data()

        # After updating price
        item.update_price(150.0)
        assert item.has_price_data()

    def test_is_price_data_stale(self):
        """Test is_price_data_stale method."""
        item = WatchlistItem.create_new("AAPL")

        # No price data is considered stale
        assert item.is_price_data_stale()

        # Fresh price data
        item.update_price(150.0)
        assert not item.is_price_data_stale()

        # Old price data
        old_time = datetime.now() - timedelta(hours=25)
        item.last_price_update = old_time
        assert item.is_price_data_stale()

        # Custom max age
        assert not item.is_price_data_stale(max_age_hours=48)

    def test_get_display_name(self):
        """Test get_display_name method."""
        # Without notes
        item1 = WatchlistItem.create_new("AAPL")
        assert item1.get_display_name() == "AAPL"

        # With notes
        item2 = WatchlistItem.create_new("AAPL", "Apple Inc.")
        assert item2.get_display_name() == "AAPL - Apple Inc."

        # With empty notes
        item3 = WatchlistItem.create_new("AAPL", "")
        assert item3.get_display_name() == "AAPL"

        # With whitespace-only notes
        item4 = WatchlistItem.create_new("AAPL", "   ")
        assert item4.get_display_name() == "AAPL"

    def test_clear_price_data(self):
        """Test clear_price_data method."""
        item = WatchlistItem.create_new("AAPL")
        item.update_price(150.0, 2.5, 1.69)

        # Verify price data exists
        assert item.has_price_data()

        # Clear price data
        item.clear_price_data()

        # Verify all price data is cleared
        assert item.current_price is None
        assert item.daily_change is None
        assert item.daily_change_percent is None
        assert item.last_price_update is None
        assert not item.has_price_data()

    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.now()
        item = WatchlistItem(
            id="test-id",
            symbol="AAPL",
            notes="Apple Inc.",
            added_date=now,
            current_price=150.0,
            last_price_update=now,
            daily_change=2.5,
            daily_change_percent=1.69
        )

        data = item.to_dict()

        assert data['id'] == "test-id"
        assert data['symbol'] == "AAPL"
        assert data['notes'] == "Apple Inc."
        assert data['added_date'] == now.isoformat()
        assert data['current_price'] == 150.0
        assert data['last_price_update'] == now.isoformat()
        assert data['daily_change'] == 2.5
        assert data['daily_change_percent'] == 1.69

    def test_to_dict_with_none_values(self):
        """Test serialization with None values."""
        item = WatchlistItem.create_new("AAPL")
        data = item.to_dict()

        assert data['id'] is not None
        assert data['symbol'] == "AAPL"
        assert data['notes'] is None
        assert data['added_date'] is not None  # Should be set by create_new
        assert data['current_price'] is None
        assert data['last_price_update'] is None
        assert data['daily_change'] is None
        assert data['daily_change_percent'] is None

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        now = datetime.now()
        data = {
            'id': 'test-id',
            'symbol': 'AAPL',
            'notes': 'Apple Inc.',
            'added_date': now.isoformat(),
            'current_price': 150.0,
            'last_price_update': now.isoformat(),
            'daily_change': 2.5,
            'daily_change_percent': 1.69
        }

        item = WatchlistItem.from_dict(data)

        assert item.id == "test-id"
        assert item.symbol == "AAPL"
        assert item.notes == "Apple Inc."
        assert item.added_date == now
        assert item.current_price == 150.0
        assert item.last_price_update == now
        assert item.daily_change == 2.5
        assert item.daily_change_percent == 1.69

    def test_from_dict_with_none_values(self):
        """Test deserialization with None values."""
        data = {
            'id': 'test-id',
            'symbol': 'AAPL',
            'notes': None,
            'added_date': None,
            'current_price': None,
            'last_price_update': None,
            'daily_change': None,
            'daily_change_percent': None
        }

        item = WatchlistItem.from_dict(data)

        assert item.id == "test-id"
        assert item.symbol == "AAPL"
        assert item.notes is None
        assert item.added_date is not None  # Should be set by __post_init__
        assert item.current_price is None
        assert item.last_price_update is None
        assert item.daily_change is None
        assert item.daily_change_percent is None

    def test_round_trip_serialization(self):
        """Test that serialization and deserialization are consistent."""
        original = WatchlistItem.create_new("AAPL", "Apple Inc.")
        original.update_price(150.0, 2.5, 1.69)

        # Serialize and deserialize
        data = original.to_dict()
        restored = WatchlistItem.from_dict(data)

        # Compare all fields
        assert restored.id == original.id
        assert restored.symbol == original.symbol
        assert restored.notes == original.notes
        assert restored.added_date == original.added_date
        assert restored.current_price == original.current_price
        assert restored.last_price_update == original.last_price_update
        assert restored.daily_change == original.daily_change
        assert restored.daily_change_percent == original.daily_change_percent