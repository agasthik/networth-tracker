"""
Authentication service for the networth tracker application.
Handles master password authentication, session management, and initial setup.
"""

import os
import hashlib
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from flask import session, current_app

from .encryption import EncryptionService
from .database import DatabaseService


class AuthenticationManager:
    """Manages authentication and session handling for the application."""

    def __init__(self, db_path: str):
        """
        Initialize authentication manager.

        Args:
            db_path: Path to the SQLite database
        """
        self.db_path = db_path
        self.encryption_service = EncryptionService()
        self.db_service: Optional[DatabaseService] = None
        self.session_timeout = timedelta(hours=2)

    def is_setup_required(self) -> bool:
        """
        Check if initial setup is required (no master password set).

        Returns:
            True if setup is required, False otherwise
        """
        if not os.path.exists(self.db_path):
            return True

        try:
            # Check if database has the required tables and settings
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Check if app_settings table exists
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='app_settings'
            """)
            if not cursor.fetchone():
                conn.close()
                return True

            # Check if master password hash exists (stored as plain text for verification)
            cursor.execute("SELECT value FROM app_settings WHERE key='master_password_hash'")
            has_password = cursor.fetchone() is not None
            conn.close()

            return not has_password
        except Exception:
            return True

    def set_master_password(self, password: str) -> bool:
        """
        Set initial master password during setup.

        Args:
            password: Master password to set

        Returns:
            True if password was set successfully

        Raises:
            ValueError: If setup is not required or password is invalid
        """
        if not self.is_setup_required():
            raise ValueError("Master password already set")

        if not self._validate_password_strength(password):
            raise ValueError("Password does not meet strength requirements")

        # Generate salt and derive encryption key
        salt = os.urandom(16)
        self.encryption_service.derive_key(password, salt)

        # Initialize database with basic structure first
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Create app_settings table for storing auth info (compatible with database service)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                encrypted_value BLOB
            )
        ''')

        # Store password hash and salt as plain text for auth verification
        password_hash = self._hash_password(password, salt)
        cursor.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)',
                      ('master_password_hash', password_hash))
        cursor.execute('INSERT OR REPLACE INTO app_settings (key, value) VALUES (?, ?)',
                      ('password_salt', salt.hex()))

        conn.commit()
        conn.close()

        # Now initialize database service with encryption
        self.db_service = DatabaseService(self.db_path, self.encryption_service)
        self.db_service.connect()

        return True

    def verify_password(self, password: str) -> bool:
        """
        Verify master password and initialize session.

        Args:
            password: Password to verify

        Returns:
            True if password is correct and session initialized
        """
        if self.is_setup_required():
            return False

        try:
            # Get stored salt and hash directly from database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("SELECT value FROM app_settings WHERE key='password_salt'")
            salt_row = cursor.fetchone()
            cursor.execute("SELECT value FROM app_settings WHERE key='master_password_hash'")
            hash_row = cursor.fetchone()
            conn.close()

            if not salt_row or not hash_row:
                return False

            stored_salt = bytes.fromhex(salt_row[0])
            stored_hash = hash_row[0]

            # Derive key with stored salt and verify password
            self.encryption_service.derive_key(password, stored_salt)

            # Verify password hash
            if not self._verify_password_hash(password, stored_hash, stored_salt):
                return False

            # Initialize database service with correct encryption
            self.db_service = DatabaseService(self.db_path, self.encryption_service)
            self.db_service.connect()

            # Create session
            self._create_session()
            return True

        except Exception:
            return False

    def logout(self):
        """Clear session and cleanup resources."""
        self._clear_session()
        if self.db_service:
            self.db_service.close()
            self.db_service = None

    def is_authenticated(self) -> bool:
        """
        Check if user is currently authenticated.

        Returns:
            True if user has valid session
        """
        if not session.get('authenticated'):
            return False

        # Check session timeout
        last_activity = session.get('last_activity')
        if not last_activity:
            return False

        last_activity_time = datetime.fromisoformat(last_activity)
        if datetime.now() - last_activity_time > self.session_timeout:
            self.logout()
            return False

        # Update last activity
        session['last_activity'] = datetime.now().isoformat()
        return True

    def require_authentication(self) -> bool:
        """
        Check authentication and extend session if valid.

        Returns:
            True if authenticated, False otherwise
        """
        if not self.is_authenticated():
            return False

        # Extend session
        session.permanent = True
        return True

    def get_database_service(self) -> Optional[DatabaseService]:
        """
        Get initialized database service.

        Returns:
            DatabaseService instance if authenticated, None otherwise
        """
        if self.is_authenticated() and self.db_service:
            return self.db_service
        return None

    def get_encryption_service(self) -> Optional[EncryptionService]:
        """
        Get initialized encryption service.

        Returns:
            EncryptionService instance if authenticated, None otherwise
        """
        if self.is_authenticated() and self.encryption_service:
            return self.encryption_service
        return None

    def _validate_password_strength(self, password: str) -> bool:
        """
        Validate password meets strength requirements.

        Args:
            password: Password to validate

        Returns:
            True if password meets requirements
        """
        if len(password) < 12:
            return False

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        return has_upper and has_lower and has_digit and has_special

    def _hash_password(self, password: str, salt: bytes) -> str:
        """
        Hash password using SHA-256 with salt.

        Args:
            password: Password to hash
            salt: Salt bytes

        Returns:
            Hexadecimal hash string
        """
        return hashlib.sha256(password.encode() + salt).hexdigest()

    def _verify_password_hash(self, password: str, stored_hash: str, salt: bytes) -> bool:
        """
        Verify password against stored hash.

        Args:
            password: Password to verify
            stored_hash: Stored password hash
            salt: Salt bytes

        Returns:
            True if password matches hash
        """
        return self._hash_password(password, salt) == stored_hash

    def _create_session(self):
        """Create authenticated session."""
        session.permanent = True
        session['authenticated'] = True
        session['session_id'] = secrets.token_hex(16)
        session['last_activity'] = datetime.now().isoformat()
        session['created_at'] = datetime.now().isoformat()

    def _clear_session(self):
        """Clear session data."""
        session.clear()

    def get_session_info(self) -> Dict[str, Any]:
        """
        Get current session information.

        Returns:
            Dictionary with session details
        """
        if not self.is_authenticated():
            return {'authenticated': False}

        return {
            'authenticated': True,
            'session_id': session.get('session_id'),
            'created_at': session.get('created_at'),
            'last_activity': session.get('last_activity'),
            'expires_at': (datetime.now() + self.session_timeout).isoformat()
        }