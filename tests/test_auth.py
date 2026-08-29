"""
Unit tests for authentication service.
Tests master password handling, session management, and security features.
"""

import os
import tempfile
import unittest

# Import Flask app for testing context
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from services.auth import AuthenticationManager


class TestAuthenticationManager(unittest.TestCase):
    """Test cases for AuthenticationManager class."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix=".db")
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.auth_manager = AuthenticationManager(self.db_path)
        self.test_password = "TestPassword123!"

        # Create Flask test client
        self.app = app
        self.app.config["TESTING"] = True
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
        valid_passwords = ["ValidPassword123!", "AnotherGood1@", "Complex#Pass123"]

        for password in valid_passwords:
            self.assertTrue(self.auth_manager._validate_password_strength(password))

        # Invalid passwords
        invalid_passwords = [
            "short",  # Too short
            "nouppercase123!",  # No uppercase
            "NOLOWERCASE123!",  # No lowercase
            "NoNumbers!",  # No numbers
            "NoSpecialChars123",  # No special characters
            "Short1!",  # Less than 12 characters
        ]

        for password in invalid_passwords:
            result = self.auth_manager._validate_password_strength(password)
            self.assertFalse(
                result, f"Password '{password}' should be invalid but was accepted"
            )

    def test_hash_password_consistency(self):
        """Test password hashing consistency."""
        salt = os.urandom(16)

        hash1 = self.auth_manager._hash_password(self.test_password, salt)
        hash2 = self.auth_manager._hash_password(self.test_password, salt)

        self.assertEqual(hash1, hash2)
        self.assertIsInstance(hash1, str)
        self.assertTrue(hash1.startswith("pbkdf2_sha256$"))
        self.assertEqual(len(hash1.split("$")), 4)

    def test_login_attempt_limit_and_success_reset(self):
        """Repeated failures are throttled and a success clears the window."""
        manager = AuthenticationManager(
            self.db_path,
            login_max_attempts=2,
            login_attempt_window=300,
        )
        identifier = "127.0.0.1"

        self.assertTrue(manager.is_login_allowed(identifier))
        manager.record_login_attempt(identifier, success=False)
        self.assertTrue(manager.is_login_allowed(identifier))
        manager.record_login_attempt(identifier, success=False)
        self.assertFalse(manager.is_login_allowed(identifier))
        manager.record_login_attempt(identifier, success=True)
        self.assertTrue(manager.is_login_allowed(identifier))

    def test_logout_clears_derived_key(self):
        """Logout must release the active database and encryption key."""
        self.auth_manager.encryption_service.derive_key(
            self.test_password,
            b"0123456789abcdef",
        )

        with self.app.test_request_context():
            self.auth_manager.logout()

        self.assertIsNone(self.auth_manager.encryption_service.key)
        self.assertIsNone(self.auth_manager.encryption_service.salt)


if __name__ == "__main__":
    unittest.main()
