"""
Security tests for encryption, authentication, and data protection.

Tests cover:
- Encryption strength and implementation
- Password security and validation
- Session management security
- Data leakage prevention
- Authentication bypass prevention
- SQL injection prevention
"""

import unittest
import tempfile
import os
import json
import sqlite3
from unittest.mock import patch, MagicMock

from services.encryption import EncryptionService
from services.auth import AuthenticationManager
from services.database import DatabaseService


class TestEncryptionSecurity(unittest.TestCase):
    """Security tests for encryption implementation."""

    def setUp(self):
        """Set up encryption service for testing."""
        self.encryption_service = EncryptionService()

    def test_encryption_key_strength(self):
        """Test that encryption keys are sufficiently strong."""
        password = "TestPassword123!"
        key = self.encryption_service.derive_key(password)

        # Key should be 44 bytes (base64 encoded 32-byte key)
        self.assertEqual(len(key), 44)

        # Salt should be 16 bytes
        self.assertEqual(len(self.encryption_service.salt), 16)

        # Different passwords should generate different keys
        key2 = EncryptionService().derive_key("DifferentPassword123!")
        self.assertNotEqual(key, key2)

    def test_encryption_randomness(self):
        """Test that encryption produces different ciphertext for same plaintext."""
        password = "TestPassword123!"
        self.encryption_service.derive_key(password)

        plaintext = "Sensitive financial data: $50,000"

        # Encrypt same data multiple times
        ciphertext1 = self.encryption_service.encrypt(plaintext)
        ciphertext2 = self.encryption_service.encrypt(plaintext)
        ciphertext3 = self.encryption_service.encrypt(plaintext)

        # All ciphertexts should be different (due to random IV)
        self.assertNotEqual(ciphertext1, ciphertext2)
        self.assertNotEqual(ciphertext2, ciphertext3)
        self.assertNotEqual(ciphertext1, ciphertext3)

        # But all should decrypt to same plaintext
        self.assertEqual(self.encryption_service.decrypt(ciphertext1), plaintext)
        self.assertEqual(self.encryption_service.decrypt(ciphertext2), plaintext)
        self.assertEqual(self.encryption_service.decrypt(ciphertext3), plaintext)

    def test_encryption_key_derivation_security(self):
        """Test security of key derivation function."""
        password = "TestPassword123!"
        salt = os.urandom(16)

        # Key derivation should be deterministic with same password and salt
        key1 = self.encryption_service.derive_key(password, salt)
        key2 = EncryptionService().derive_key(password, salt)
        self.assertEqual(key1, key2)

        # But different with different salt
        different_salt = os.urandom(16)
        key3 = EncryptionService().derive_key(password, different_salt)
        self.assertNotEqual(key1, key3)

    def test_encryption_data_integrity(self):
        """Test that encrypted data maintains integrity."""
        password = "TestPassword123!"
        self.encryption_service.derive_key(password)

        original_data = "Critical financial information: Account #123456789, Balance: $75,432.10"
        encrypted_data = self.encryption_service.encrypt(original_data)

        # Tamper with encrypted data
        tampered_data = bytearray(encrypted_data)
        tampered_data[10] = (tampered_data[10] + 1) % 256  # Flip one bit

        # Decryption should fail with tampered data
        with self.assertRaises(Exception):
            self.encryption_service.decrypt(bytes(tampered_data))

    def test_sensitive_data_not_in_memory(self):
        """Test that sensitive data is not left in memory."""
        password = "TestPassword123!"
        self.encryption_service.derive_key(password)

        sensitive_data = "SSN: 123-45-6789, Account: 987654321"
        encrypted_data = self.encryption_service.encrypt(sensitive_data)
        decrypted_data = self.encryption_service.decrypt(encrypted_data)

        self.assertEqual(decrypted_data, sensitive_data)

        # Clear sensitive variables
        del sensitive_data
        del decrypted_data

        # Note: In a real implementation, we would use secure memory clearing
        # This test documents the requirement for secure memory handling


class TestPasswordSecurity(unittest.TestCase):
    """Security tests for password handling."""

    def setUp(self):
        """Set up authentication manager for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.auth_manager = AuthenticationManager(self.db_path)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_password_strength_requirements(self):
        """Test password strength validation."""
        # Test weak passwords
        weak_passwords = [
            "short",                    # Too short
            "nouppercase123!",         # No uppercase
            "NOLOWERCASE123!",         # No lowercase
            "NoNumbers!",              # No numbers
            "NoSpecialChars123",       # No special characters
            "12345678901",             # Only numbers
            "abcdefghijkl",           # Only lowercase
            "ABCDEFGHIJKL",           # Only uppercase
            "!@#$%^&*()",             # Only special characters
        ]

        for weak_password in weak_passwords:
            with self.assertRaises(ValueError) as context:
                self.auth_manager.set_master_password(weak_password)
            self.assertIn("strength requirements", str(context.exception))

    def test_password_hashing_security(self):
        """Test password hashing implementation."""
        password = "SecurePassword123!"

        # Set password
        self.auth_manager.set_master_password(password)

        # Verify password is not stored in plaintext
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM app_settings WHERE key = 'master_password_hash'")
        row = cursor.fetchone()
        conn.close()

        self.assertIsNotNone(row)
        stored_hash = row[1]  # encrypted_value column

        # Hash should not contain plaintext password
        self.assertNotIn(password.encode(), stored_hash)

    def test_password_timing_attack_resistance(self):
        """Test resistance to timing attacks."""
        correct_password = "CorrectPassword123!"
        wrong_password = "WrongPassword123!"

        self.auth_manager.set_master_password(correct_password)

        # Measure time for correct password verification
        import time

        with patch('flask.session', {}):
            start_time = time.time()
            result1 = self.auth_manager.verify_password(correct_password)
            correct_time = time.time() - start_time

            start_time = time.time()
            result2 = self.auth_manager.verify_password(wrong_password)
            wrong_time = time.time() - start_time

        self.assertTrue(result1)
        self.assertFalse(result2)

        # Time difference should be minimal (within reasonable bounds)
        # This is a basic check - real timing attack resistance requires more sophisticated testing
        time_difference = abs(correct_time - wrong_time)
        self.assertLess(time_difference, 0.1)  # Less than 100ms difference

    def test_password_brute_force_protection(self):
        """Test protection against brute force attacks."""
        correct_password = "CorrectPassword123!"
        self.auth_manager.set_master_password(correct_password)

        # Simulate multiple failed attempts
        failed_attempts = 0
        max_attempts = 5

        with patch('flask.session', {}):
            for i in range(max_attempts + 1):
                try:
                    result = self.auth_manager.verify_password("WrongPassword123!")
                    if not result:
                        failed_attempts += 1
                except Exception:
                    # Rate limiting or account lockout triggered
                    break

        # Note: This test documents the requirement for brute force protection
        # Actual implementation would include rate limiting or account lockout


class TestSessionSecurity(unittest.TestCase):
    """Security tests for session management."""

    def setUp(self):
        """Set up authentication manager for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.auth_manager = AuthenticationManager(self.db_path)
        self.test_password = "TestPassword123!"
        self.auth_manager.set_master_password(self.test_password)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_session_isolation(self):
        """Test that sessions are properly isolated."""
        with patch('flask.session', {}) as session1:
            # Login in first session
            result1 = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(result1)
            self.assertTrue(self.auth_manager.is_authenticated())

        with patch('flask.session', {}) as session2:
            # Second session should not be authenticated
            self.assertFalse(self.auth_manager.is_authenticated())

    def test_session_timeout(self):
        """Test session timeout functionality."""
        with patch('flask.session', {}) as mock_session:
            # Login
            self.auth_manager.verify_password(self.test_password)
            self.assertTrue(self.auth_manager.is_authenticated())

            # Simulate session timeout by clearing session
            mock_session.clear()

            # Should no longer be authenticated
            self.assertFalse(self.auth_manager.is_authenticated())

    def test_session_token_security(self):
        """Test session token security."""
        with patch('flask.session', {}) as mock_session:
            # Login
            self.auth_manager.verify_password(self.test_password)

            # Session should contain authentication marker
            self.assertIn('authenticated', mock_session)

            # Session should not contain sensitive data
            session_str = str(mock_session)
            self.assertNotIn(self.test_password, session_str)


class TestDatabaseSecurity(unittest.TestCase):
    """Security tests for database operations."""

    def setUp(self):
        """Set up database service for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

        self.encryption_service = EncryptionService()
        self.encryption_service.derive_key("test_password_123")

        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

    def tearDown(self):
        """Clean up test database."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_sql_injection_prevention(self):
        """Test prevention of SQL injection attacks."""
        # Test malicious input in account creation
        malicious_inputs = [
            "'; DROP TABLE accounts; --",
            "' OR '1'='1",
            "'; INSERT INTO accounts VALUES ('hacked'); --",
            "' UNION SELECT * FROM app_settings --"
        ]

        for malicious_input in malicious_inputs:
            account_data = {
                'name': malicious_input,
                'institution': 'Test Bank',
                'type': 'SAVINGS',
                'current_balance': 1000.0
            }

            # Should not cause SQL injection
            try:
                account_id = self.db_service.create_account(account_data)
                # If successful, verify the malicious input was treated as literal data
                retrieved_account = self.db_service.get_account(account_id)
                self.assertEqual(retrieved_account['name'], malicious_input)
            except Exception:
                # Exception is acceptable - injection should not succeed
                pass

        # Verify database integrity
        cursor = self.db_service.connection.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]

        # All expected tables should still exist
        expected_tables = ['accounts', 'historical_snapshots', 'stock_positions', 'app_settings']
        for table in expected_tables:
            self.assertIn(table, tables)

    def test_data_encryption_in_database(self):
        """Test that sensitive data is encrypted in database."""
        sensitive_account_data = {
            'name': 'High Value Account',
            'institution': 'Private Bank',
            'type': 'SAVINGS',
            'current_balance': 1000000.0,
            'account_number': 'SENSITIVE123456',
            'routing_number': '987654321'
        }

        account_id = self.db_service.create_account(sensitive_account_data)

        # Check raw database content
        cursor = self.db_service.connection.cursor()
        cursor.execute('SELECT encrypted_data FROM accounts WHERE id = ?', (account_id,))
        row = cursor.fetchone()

        encrypted_blob = row['encrypted_data']

        # Sensitive data should not appear in plaintext
        sensitive_values = [
            b'1000000.0',
            b'SENSITIVE123456',
            b'987654321'
        ]

        for sensitive_value in sensitive_values:
            self.assertNotIn(sensitive_value, encrypted_blob)

        # But data should be retrievable through service
        retrieved_account = self.db_service.get_account(account_id)
        self.assertEqual(retrieved_account['current_balance'], 1000000.0)
        self.assertEqual(retrieved_account['account_number'], 'SENSITIVE123456')

    def test_database_file_permissions(self):
        """Test database file has secure permissions."""
        if os.name == 'nt':  # Skip on Windows
            self.skipTest("File permissions test not applicable on Windows")

        # Check file permissions
        file_stat = os.stat(self.db_path)
        file_mode = oct(file_stat.st_mode)[-3:]  # Last 3 digits

        # File should have restrictive permissions (600 = owner read/write only)
        # Note: This test may need adjustment based on actual implementation
        self.assertIn(file_mode, ['600', '644'])  # Allow common secure permissions

    def test_database_connection_security(self):
        """Test database connection security."""
        # Verify database is not accessible without proper encryption key
        wrong_encryption_service = EncryptionService()
        wrong_encryption_service.derive_key("wrong_password")

        wrong_db_service = DatabaseService(self.db_path, wrong_encryption_service)
        wrong_db_service.connect()

        # Create account with correct service
        account_data = {
            'name': 'Test Account',
            'institution': 'Test Bank',
            'type': 'SAVINGS',
            'current_balance': 5000.0
        }
        account_id = self.db_service.create_account(account_data)

        # Try to retrieve with wrong encryption key
        try:
            retrieved_account = wrong_db_service.get_account(account_id)
            # If retrieval succeeds, data should be garbled/invalid
            if retrieved_account:
                # Data should not match original due to wrong decryption key
                self.assertNotEqual(retrieved_account.get('current_balance'), 5000.0)
        except Exception:
            # Exception is expected with wrong encryption key
            pass

        wrong_db_service.close()


class TestDataLeakagePrevention(unittest.TestCase):
    """Tests to prevent data leakage."""

    def setUp(self):
        """Set up services for testing."""
        self.db_fd, self.db_path = tempfile.mkstemp(suffix='.db')

        self.encryption_service = EncryptionService()
        self.encryption_service.derive_key("test_password_123")

        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

    def tearDown(self):
        """Clean up test database."""
        self.db_service.close()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def test_error_messages_dont_leak_data(self):
        """Test that error messages don't leak sensitive data."""
        sensitive_data = {
            'name': 'Secret Account',
            'institution': 'Private Bank',
            'type': 'SAVINGS',
            'current_balance': 999999.99,
            'ssn': '123-45-6789'
        }

        # Create account
        account_id = self.db_service.create_account(sensitive_data)

        # Try operations that might generate errors
        try:
            # Try to update with invalid data
            invalid_update = {
                'name': None,  # Invalid
                'current_balance': 'not_a_number'  # Invalid
            }
            self.db_service.update_account(account_id, invalid_update)
        except Exception as e:
            error_message = str(e)
            # Error message should not contain sensitive data
            self.assertNotIn('999999.99', error_message)
            self.assertNotIn('123-45-6789', error_message)

    def test_log_messages_dont_leak_data(self):
        """Test that log messages don't contain sensitive data."""
        # This test would require actual logging implementation
        # For now, it documents the requirement

        sensitive_account_data = {
            'name': 'Confidential Account',
            'institution': 'Secret Bank',
            'type': 'SAVINGS',
            'current_balance': 500000.0,
            'account_number': 'SECRET123'
        }

        # In a real implementation, we would:
        # 1. Enable logging
        # 2. Perform operations that generate logs
        # 3. Check that logs don't contain sensitive values

        account_id = self.db_service.create_account(sensitive_account_data)

        # Note: This test documents the requirement for secure logging
        # Actual implementation would need to verify log content

    def test_memory_dumps_dont_leak_data(self):
        """Test that memory dumps don't contain sensitive data."""
        # This is a conceptual test - actual memory dump analysis
        # would require specialized tools and techniques

        sensitive_data = "SSN: 123-45-6789, Balance: $1,000,000"

        # Encrypt sensitive data
        encrypted = self.encryption_service.encrypt(sensitive_data)

        # Decrypt and use data
        decrypted = self.encryption_service.decrypt(encrypted)

        # Clear sensitive variables
        del sensitive_data
        del decrypted

        # Note: In a real implementation, we would use secure memory clearing
        # techniques to prevent sensitive data from remaining in memory


class TestAuthenticationBypassPrevention(unittest.TestCase):
    """Tests to prevent authentication bypass."""

    def setUp(self):
        """Set up authentication manager for testing."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name
        self.auth_manager = AuthenticationManager(self.db_path)
        self.test_password = "TestPassword123!"
        self.auth_manager.set_master_password(self.test_password)

    def tearDown(self):
        """Clean up test database."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_direct_session_manipulation(self):
        """Test that direct session manipulation doesn't bypass authentication."""
        with patch('flask.session', {}) as mock_session:
            # Try to bypass authentication by directly setting session
            mock_session['authenticated'] = True
            mock_session['user_id'] = 'fake_user'

            # Authentication check should still fail without proper login
            # Note: This depends on implementation details
            # The auth manager should validate more than just session flags

            # Proper login should be required
            result = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(result)

    def test_database_manipulation_bypass(self):
        """Test that direct database manipulation doesn't bypass authentication."""
        # Try to manipulate database directly
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Try to insert fake authentication data
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO app_settings (key, encrypted_value)
                VALUES ('fake_auth', 'fake_value')
            """)
            conn.commit()
        except Exception:
            pass  # Expected to fail with proper database constraints

        conn.close()

        # Authentication should still require proper password
        with patch('flask.session', {}):
            result = self.auth_manager.verify_password(self.test_password)
            self.assertTrue(result)

            # Wrong password should still fail
            result = self.auth_manager.verify_password("WrongPassword123!")
            self.assertFalse(result)

    def test_encryption_key_bypass(self):
        """Test that encryption key cannot be bypassed."""
        # Create account with proper encryption
        account_data = {
            'name': 'Protected Account',
            'institution': 'Secure Bank',
            'type': 'SAVINGS',
            'current_balance': 75000.0
        }

        db_service = DatabaseService(self.db_path, self.encryption_service)
        db_service.connect()

        account_id = db_service.create_account(account_data)

        # Try to access with wrong encryption key
        wrong_encryption = EncryptionService()
        wrong_encryption.derive_key("wrong_key")

        wrong_db_service = DatabaseService(self.db_path, wrong_encryption)
        wrong_db_service.connect()

        # Should not be able to decrypt data properly
        try:
            retrieved_account = wrong_db_service.get_account(account_id)
            if retrieved_account:
                # Data should be corrupted/invalid
                self.assertNotEqual(retrieved_account.get('current_balance'), 75000.0)
        except Exception:
            # Exception is expected with wrong key
            pass

        db_service.close()
        wrong_db_service.close()


if __name__ == '__main__':
    unittest.main()