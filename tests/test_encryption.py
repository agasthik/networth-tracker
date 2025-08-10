"""
Unit tests for EncryptionService.
Tests encryption, decryption, and password hashing functionality.
"""

import unittest
import os
from services.encryption import EncryptionService


class TestEncryptionService(unittest.TestCase):
    """Test cases for EncryptionService class."""

    def setUp(self):
        """Set up encryption service for testing."""
        self.encryption_service = EncryptionService()

    def test_derive_key_with_password(self):
        """Test key derivation from password."""
        password = "test_password_123"
        key = self.encryption_service.derive_key(password)

        self.assertIsInstance(key, bytes)
        self.assertEqual(len(key), 44)  # Base64 encoded 32-byte key
        self.assertIsNotNone(self.encryption_service.salt)
        self.assertIsNotNone(self.encryption_service.key)

    def test_derive_key_with_salt(self):
        """Test key derivation with provided salt."""
        password = "test_password_123"
        salt = os.urandom(16)

        key1 = self.encryption_service.derive_key(password, salt)

        # Create new service and derive with same salt
        service2 = EncryptionService()
        key2 = service2.derive_key(password, salt)

        # Keys should be identical with same password and salt
        self.assertEqual(key1, key2)

    def test_derive_key_different_passwords(self):
        """Test that different passwords generate different keys."""
        salt = os.urandom(16)

        key1 = self.encryption_service.derive_key("password1", salt)

        service2 = EncryptionService()
        key2 = service2.derive_key("password2", salt)

        self.assertNotEqual(key1, key2)

    def test_encrypt_decrypt_cycle(self):
        """Test encryption and decryption of data."""
        password = "test_password_123"
        self.encryption_service.derive_key(password)

        original_data = "This is sensitive financial data: $10,000.00"

        # Encrypt data
        encrypted_data = self.encryption_service.encrypt(original_data)
        self.assertIsInstance(encrypted_data, bytes)
        self.assertNotEqual(encrypted_data, original_data.encode())

        # Decrypt data
        decrypted_data = self.encryption_service.decrypt(encrypted_data)
        self.assertEqual(decrypted_data, original_data)

    def test_encrypt_without_key_raises_error(self):
        """Test that encryption without key derivation raises error."""
        with self.assertRaises(ValueError) as context:
            self.encryption_service.encrypt("test data")

        self.assertIn("Encryption key not initialized", str(context.exception))

    def test_decrypt_without_key_raises_error(self):
        """Test that decryption without key derivation raises error."""
        with self.assertRaises(ValueError) as context:
            self.encryption_service.decrypt(b"fake encrypted data")

        self.assertIn("Encryption key not initialized", str(context.exception))

    def test_encrypt_empty_string(self):
        """Test encryption of empty string."""
        password = "test_password_123"
        self.encryption_service.derive_key(password)

        encrypted_data = self.encryption_service.encrypt("")
        decrypted_data = self.encryption_service.decrypt(encrypted_data)

        self.assertEqual(decrypted_data, "")

    def test_encrypt_unicode_data(self):
        """Test encryption of unicode data."""
        password = "test_password_123"
        self.encryption_service.derive_key(password)

        unicode_data = "Test with émojis 🔒💰 and special chars: ñáéíóú"

        encrypted_data = self.encryption_service.encrypt(unicode_data)
        decrypted_data = self.encryption_service.decrypt(encrypted_data)

        self.assertEqual(decrypted_data, unicode_data)

    def test_hash_password(self):
        """Test password hashing."""
        password = "test_password_123"
        hash1 = self.encryption_service.hash_password(password)

        self.assertIsInstance(hash1, str)
        self.assertEqual(len(hash1), 64)  # SHA-256 hex digest length

        # Same password should produce same hash
        hash2 = self.encryption_service.hash_password(password)
        self.assertEqual(hash1, hash2)

        # Different password should produce different hash
        hash3 = self.encryption_service.hash_password("different_password")
        self.assertNotEqual(hash1, hash3)

    def test_verify_password(self):
        """Test password verification."""
        password = "test_password_123"
        stored_hash = self.encryption_service.hash_password(password)

        # Correct password should verify
        self.assertTrue(self.encryption_service.verify_password(password, stored_hash))

        # Incorrect password should not verify
        self.assertFalse(self.encryption_service.verify_password("wrong_password", stored_hash))

    def test_multiple_encrypt_decrypt_operations(self):
        """Test multiple encryption/decryption operations."""
        password = "test_password_123"
        self.encryption_service.derive_key(password)

        test_data = [
            "Account balance: $5,000.00",
            "Interest rate: 2.5%",
            "Maturity date: 2025-12-31",
            "Stock symbol: AAPL",
            "Shares: 100"
        ]

        encrypted_data = []
        for data in test_data:
            encrypted_data.append(self.encryption_service.encrypt(data))

        # Decrypt all data
        decrypted_data = []
        for encrypted in encrypted_data:
            decrypted_data.append(self.encryption_service.decrypt(encrypted))

        self.assertEqual(decrypted_data, test_data)

    def test_encryption_produces_different_ciphertext(self):
        """Test that encrypting same data twice produces different ciphertext."""
        password = "test_password_123"
        self.encryption_service.derive_key(password)

        data = "Same data encrypted twice"

        encrypted1 = self.encryption_service.encrypt(data)
        encrypted2 = self.encryption_service.encrypt(data)

        # Ciphertext should be different due to random IV
        self.assertNotEqual(encrypted1, encrypted2)

        # But both should decrypt to same plaintext
        decrypted1 = self.encryption_service.decrypt(encrypted1)
        decrypted2 = self.encryption_service.decrypt(encrypted2)

        self.assertEqual(decrypted1, data)
        self.assertEqual(decrypted2, data)


if __name__ == '__main__':
    unittest.main()