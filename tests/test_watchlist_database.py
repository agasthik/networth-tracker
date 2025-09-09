"""
Unit tests for watchlist database operations in the networth tracker application.
Tests the DatabaseService watchlist CRUD operations with encryption.
"""

import pytest
import tempfile
import os
from datetime import datetime
from unittest.mock import Mock, patch

from services.database import DatabaseService
from services.encryption import EncryptionService
from services.error_handler import DatabaseError


class TestWatchlistDatabase:
    """Test watchlist database operations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database file."""
        fd, path = tempfile.mkstemp(suffix='.db')
        os.close(fd)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def encryption_service(self):
        """Create encryption service for testing."""
        service = EncryptionService()
        service.derive_key("test_password")
        return service

    @pytest.fixture
    def db_service(self, temp_db_path, encryption_service):
        """Create database service for testing."""
        service = DatabaseService(temp_db_path, encryption_service)
        service.connect()
        return service

    @pytest.fixture
    def sample_watchlist_data(self):
        """Sample watchlist item data for testing."""
        return {
            'symbol': 'AAPL',
            'notes': 'Apple Inc. - Technology stock',
            'current_price': 150.25,
            'daily_change': 2.50,
            'daily_change_percent': 1.69
        }

    def test_create_watchlist_item(self, db_service, sample_watchlist_data):
        """Test creating a new watchlist item."""
        item_id = db_service.create_watchlist_item(sample_watchlist_data)

        assert item_id is not None
        assert len(item_id) > 0

        # Verify item was created
        item = db_service.get_watchlist_item('AAPL')
        assert item is not None
        assert item['symbol'] == 'AAPL'
        assert item['notes'] == 'Apple Inc. - Technology stock'
        assert item['current_price'] == 150.25
        assert item['is_demo'] is False

    def test_create_watchlist_item_with_demo_flag(self, db_service, sample_watchlist_data):
        """Test creating a demo watchlist item."""
        sample_watchlist_data['is_demo'] = True
        item_id = db_service.create_watchlist_item(sample_watchlist_data)

        item = db_service.get_watchlist_item('AAPL')
        assert item['is_demo'] is True

    def test_create_watchlist_item_normalizes_symbol(self, db_service, sample_watchlist_data):
        """Test that stock symbols are normalized to uppercase."""
        sample_watchlist_data['symbol'] = 'aapl'
        item_id = db_service.create_watchlist_item(sample_watchlist_data)

        item = db_service.get_watchlist_item('AAPL')
        assert item is not None
        assert item['symbol'] == 'AAPL'

    def test_create_duplicate_watchlist_item_fails(self, db_service, sample_watchlist_data):
        """Test that creating duplicate watchlist items fails."""
        db_service.create_watchlist_item(sample_watchlist_data)

        with pytest.raises(DatabaseError) as exc_info:
            db_service.create_watchlist_item(sample_watchlist_data)

        assert "already in watchlist" in str(exc_info.value)

    def test_get_watchlist_item_not_found(self, db_service):
        """Test getting non-existent watchlist item returns None."""
        item = db_service.get_watchlist_item('NONEXISTENT')
        assert item is None

    def test_get_watchlist_items_empty(self, db_service):
        """Test getting watchlist items when none exist."""
        items = db_service.get_watchlist_items()
        assert items == []

    def test_get_watchlist_items_multiple(self, db_service):
        """Test getting multiple watchlist items."""
        # Create multiple items
        items_data = [
            {'symbol': 'AAPL', 'notes': 'Apple'},
            {'symbol': 'GOOGL', 'notes': 'Google'},
            {'symbol': 'TSLA', 'notes': 'Tesla', 'is_demo': True}
        ]

        for item_data in items_data:
            db_service.create_watchlist_item(item_data)

        # Get all items
        items = db_service.get_watchlist_items()
        assert len(items) == 3

        # Verify sorting by symbol
        symbols = [item['symbol'] for item in items]
        assert symbols == ['AAPL', 'GOOGL', 'TSLA']

    def test_get_demo_watchlist_items(self, db_service):
        """Test getting only demo watchlist items."""
        # Create mixed demo and real items
        db_service.create_watchlist_item({'symbol': 'AAPL', 'notes': 'Real'})
        db_service.create_watchlist_item({'symbol': 'GOOGL', 'notes': 'Demo', 'is_demo': True})
        db_service.create_watchlist_item({'symbol': 'TSLA', 'notes': 'Demo', 'is_demo': True})

        demo_items = db_service.get_demo_watchlist_items()
        assert len(demo_items) == 2
        assert all(item['is_demo'] for item in demo_items)

        symbols = [item['symbol'] for item in demo_items]
        assert 'GOOGL' in symbols
        assert 'TSLA' in symbols
        assert 'AAPL' not in symbols

    def test_get_real_watchlist_items(self, db_service):
        """Test getting only real (non-demo) watchlist items."""
        # Create mixed demo and real items
        db_service.create_watchlist_item({'symbol': 'AAPL', 'notes': 'Real'})
        db_service.create_watchlist_item({'symbol': 'GOOGL', 'notes': 'Real'})
        db_service.create_watchlist_item({'symbol': 'TSLA', 'notes': 'Demo', 'is_demo': True})

        real_items = db_service.get_real_watchlist_items()
        assert len(real_items) == 2
        assert all(not item['is_demo'] for item in real_items)

        symbols = [item['symbol'] for item in real_items]
        assert 'AAPL' in symbols
        assert 'GOOGL' in symbols
        assert 'TSLA' not in symbols

    def test_update_watchlist_item(self, db_service, sample_watchlist_data):
        """Test updating an existing watchlist item."""
        # Create item
        db_service.create_watchlist_item(sample_watchlist_data)

        # Update item
        update_data = {
            'notes': 'Updated notes',
            'current_price': 155.75,
            'daily_change': -1.25,
            'daily_change_percent': -0.80
        }

        result = db_service.update_watchlist_item('AAPL', update_data)
        assert result is True

        # Verify update
        item = db_service.get_watchlist_item('AAPL')
        assert item['notes'] == 'Updated notes'
        assert item['current_price'] == 155.75
        assert item['daily_change'] == -1.25
        assert item['last_price_update'] is not None

    def test_update_watchlist_item_not_found(self, db_service):
        """Test updating non-existent watchlist item returns False."""
        result = db_service.update_watchlist_item('NONEXISTENT', {'notes': 'test'})
        assert result is False

    def test_update_watchlist_item_preserves_demo_flag(self, db_service):
        """Test that updating preserves demo flag when not specified."""
        # Create demo item
        db_service.create_watchlist_item({'symbol': 'AAPL', 'notes': 'Demo', 'is_demo': True})

        # Update without specifying demo flag
        db_service.update_watchlist_item('AAPL', {'notes': 'Updated'})

        # Verify demo flag preserved
        item = db_service.get_watchlist_item('AAPL')
        assert item['is_demo'] is True

    def test_delete_watchlist_item(self, db_service, sample_watchlist_data):
        """Test deleting a watchlist item."""
        # Create item
        db_service.create_watchlist_item(sample_watchlist_data)

        # Verify item exists
        assert db_service.get_watchlist_item('AAPL') is not None

        # Delete item
        result = db_service.delete_watchlist_item('AAPL')
        assert result is True

        # Verify item deleted
        assert db_service.get_watchlist_item('AAPL') is None

    def test_delete_watchlist_item_not_found(self, db_service):
        """Test deleting non-existent watchlist item returns False."""
        result = db_service.delete_watchlist_item('NONEXISTENT')
        assert result is False

    def test_delete_demo_watchlist_items(self, db_service):
        """Test bulk deleting demo watchlist items."""
        # Create mixed demo and real items
        db_service.create_watchlist_item({'symbol': 'AAPL', 'notes': 'Real'})
        db_service.create_watchlist_item({'symbol': 'GOOGL', 'notes': 'Demo', 'is_demo': True})
        db_service.create_watchlist_item({'symbol': 'TSLA', 'notes': 'Demo', 'is_demo': True})

        # Delete demo items
        deleted_count = db_service.delete_demo_watchlist_items()
        assert deleted_count == 2

        # Verify only real items remain
        remaining_items = db_service.get_watchlist_items()
        assert len(remaining_items) == 1
        assert remaining_items[0]['symbol'] == 'AAPL'
        assert not remaining_items[0]['is_demo']

    def test_save_watchlist_item_create_new(self, db_service, sample_watchlist_data):
        """Test saving new watchlist item."""
        item_id = db_service.save_watchlist_item(sample_watchlist_data)

        assert item_id is not None
        item = db_service.get_watchlist_item('AAPL')
        assert item is not None
        assert item['symbol'] == 'AAPL'

    def test_save_watchlist_item_update_existing(self, db_service, sample_watchlist_data):
        """Test saving existing watchlist item updates it."""
        # Create initial item
        original_id = db_service.create_watchlist_item(sample_watchlist_data)

        # Save updated item
        updated_data = sample_watchlist_data.copy()
        updated_data['notes'] = 'Updated notes'

        saved_id = db_service.save_watchlist_item(updated_data)

        # Should return same ID
        assert saved_id == original_id

        # Verify update
        item = db_service.get_watchlist_item('AAPL')
        assert item['notes'] == 'Updated notes'

    def test_save_watchlist_item_with_demo_flag(self, db_service, sample_watchlist_data):
        """Test saving watchlist item with demo flag."""
        item_id = db_service.save_watchlist_item(sample_watchlist_data, is_demo=True)

        item = db_service.get_watchlist_item('AAPL')
        assert item['is_demo'] is True

    def test_watchlist_data_encryption(self, db_service, sample_watchlist_data):
        """Test that sensitive watchlist data is encrypted in database."""
        db_service.create_watchlist_item(sample_watchlist_data)

        # Query raw database to verify encryption
        cursor = db_service.connect().cursor()
        cursor.execute('SELECT encrypted_data FROM watchlist WHERE symbol = ?', ('AAPL',))
        row = cursor.fetchone()

        # Encrypted data should not contain plaintext notes
        encrypted_blob = row['encrypted_data']
        assert b'Apple Inc.' not in encrypted_blob
        assert b'Technology stock' not in encrypted_blob

    def test_watchlist_item_timestamps(self, db_service, sample_watchlist_data):
        """Test that timestamps are properly handled."""
        # Create item
        db_service.create_watchlist_item(sample_watchlist_data)
        item = db_service.get_watchlist_item('AAPL')

        # Should have added_date
        assert item['added_date'] is not None
        assert isinstance(item['added_date'], datetime)

        # Should not have last_price_update initially
        assert item['last_price_update'] is None

        # Update with price data
        db_service.update_watchlist_item('AAPL', {'current_price': 160.00})
        updated_item = db_service.get_watchlist_item('AAPL')

        # Should now have last_price_update
        assert updated_item['last_price_update'] is not None
        assert isinstance(updated_item['last_price_update'], datetime)

    def test_watchlist_database_error_handling(self, db_service):
        """Test database error handling for watchlist operations."""
        # Test with invalid data that should cause database error
        with patch.object(db_service, 'connect') as mock_connect:
            mock_cursor = Mock()
            mock_cursor.execute.side_effect = Exception("Database error")
            mock_connect.return_value.cursor.return_value = mock_cursor

            with pytest.raises(DatabaseError):
                db_service.create_watchlist_item({'symbol': 'TEST'})

    def test_watchlist_symbol_case_insensitive_retrieval(self, db_service, sample_watchlist_data):
        """Test that watchlist retrieval is case-insensitive."""
        db_service.create_watchlist_item(sample_watchlist_data)

        # Should be able to retrieve with different cases
        item1 = db_service.get_watchlist_item('AAPL')
        item2 = db_service.get_watchlist_item('aapl')
        item3 = db_service.get_watchlist_item('Aapl')

        assert item1 is not None
        assert item2 is not None
        assert item3 is not None
        assert item1['symbol'] == item2['symbol'] == item3['symbol'] == 'AAPL'