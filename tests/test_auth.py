"""
Unit tests for authentication service.
Tests master password handling, session management, and security features.
"""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

# Import Flask app for testing context
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.auth import AuthenticationManager
from services.encryption import EncryptionService
from services.database import DatabaseService


class TestAuthenticationManager(unittest.TestCase):
    """Test cases for AuthenticationManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.auth_manager = AuthenticationManager(self.db_path)
        self.test_password = "TestPassword123!"

        # Create Flask test client
        self.app = app
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_is_setup_required_new_database(self):
        """Test setup required for new database."""
        self.assertTrue(self.auth_manager.is_setup_required())

    def test_set_master_password_success(self):
        """Test successful master password setup."""
        result = self.auth_manager.set_master_password(self.test_password)
        self.assertTrue(result)
        self.assertFalse(self.auth_manager.is_setup_required())

    def test_set_master_password_weak_password(self):
        """Test setting weak master password."""
        weak_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
        ]

        for weak_password in weak_passwords:
            with self.assertRaises(ValueError) as context:
                self.auth_manager.set_master_password(weak_password)
            self.assertIn("strength requirements", str(context.exception))

    def test_verify_password_success(self):
        """Test successful password verification."""
        self.auth_manager.set_master_password(self.test_password)

        with self.app.test_request_context():
            result = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(result)

    def test_verify_password_incorrect(self):
        """Test incorrect password verification."""
        self.auth_manager.set_master_password(self.test_password)

        with self.app.test_request_context():
            result = self.auth_manager.verify_password("WrongPassword123!")
            self.assertFalse(result)

    def test_is_authenticated_not_logged_in(self):
        """Test authentication check when not logged in."""
        with self.app.test_request_context():
            result = self.auth_manager.is_authenticated()
            self.assertFalse(result)

    def test_validate_password_strength(self):
        """Test password strength validation."""
        # Valid passwords
        valid_passwords = [
            "ValidPassword123!",
            "AnotherGood1@",
            "Complex#Pass123"
        ]

        for password in valid_passwords:
            self.assertTrue(self.auth_manager._validate_password_strength(password))

        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
            "Short1!"  # Less than 12 characters
        ]

        for password in invalid_passwords:
            result = self.auth_manager._validate_password_strength(password)
            self.assertFalse(result, f"Password '{password}' should be invalid but was accepted")

    def test_hash_password_consistency(self):
        """Test password hashing consistency."""
        salt = os.urandom(16)

        hash1 = self.auth_manager._hash_password(self.test_password, salt)
        hash2 = self.auth_manager._hash_password(self.test_password, salt)

        self.assertEqual(hash1, hash2)
        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex length


if __name__ == '__main__':
    unittest.main()