"""
Encryption service for secure data storage in the networth tracker application.
Provides Fernet encryption with PBKDF2 key derivation for protecting sensitive financial data.
"""

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import hashlib
from typing import Optional


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using Fernet encryption."""

    def __init__(self):
        self.salt: Optional[bytes] = None
        self.key: Optional[bytes] = None
        self._fernet: Optional[Fernet] = None

    def derive_key(self, password: str, salt: bytes = None) -> bytes:
        """
        Derive encryption key from password using PBKDF2.

        Args:
            password: Master password for key derivation
            salt: Optional salt bytes. If None, generates new random salt

        Returns:
            Derived encryption key
        """
        if salt is None:
            salt = os.urandom(16)
        self.salt = salt

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.key = key
        self._fernet = Fernet(key)
        return key

    def encrypt(self, data: str) -> bytes:
        """
        Encrypt data using Fernet encryption.

        Args:
            data: Plain text data to encrypt

        Returns:
            Encrypted data as bytes

        Raises:
            ValueError: If encryption key not initialized
        """
        if self._fernet is None:
            raise ValueError("Encryption key not initialized. Call derive_key() first.")
        return self._fernet.encrypt(data.encode())

    def decrypt(self, encrypted_data: bytes) -> str:
        """
        Decrypt data using Fernet encryption.

        Args:
            encrypted_data: Encrypted data bytes

        Returns:
            Decrypted plain text data

        Raises:
            ValueError: If encryption key not initialized
        """
        if self._fernet is None:
            raise ValueError("Encryption key not initialized. Call derive_key() first.")
        return self._fernet.decrypt(encrypted_data).decode()

    def hash_password(self, password: str) -> str:
        """
        Hash password for storage using SHA-256.

        Args:
            password: Password to hash

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(password.encode()).hexdigest()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Password to verify
            stored_hash: Stored password hash

        Returns:
            True if password matches hash
        """
        return self.hash_password(password) == stored_hash