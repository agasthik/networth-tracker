"""
Integration tests for Flask authentication routes.
"""

import os
import tempfile
import unittest

from app import app
from services.auth import AuthenticationManager


class TestFlaskAuthRoutes(unittest.TestCase):
    """Test Flask authentication routes."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
        self.temp_db.close()
        self.db_path = self.temp_db.name

        # Configure app for testing
        app.config['TESTING'] = True
        app.config['DATABASE_PATH'] = self.db_path
        app.config['WTF_CSRF_ENABLED'] = False

        # Replace auth manager with test instance
        import app as app_module
        app_module.auth_manager = AuthenticationManager(self.db_path)

        self.client = app.test_client()
        self.test_password = "TestPassword123!"

    def tearDown(self):
        """Clean up test fixtures."""
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    def test_index_redirects_to_setup(self):
        """Test that index redirects to setup when no password is set."""
        response = self.client.get('/')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/setup', response.location)

    def test_setup_page_loads(self):
        """Test that setup page loads correctly."""
        response = self.client.get('/setup')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Initial Setup', response.data)
        self.assertIn(b'Master Password', response.data)

    def test_setup_password_success(self):
        """Test successful password setup."""
        response = self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Should redirect to login page after successful setup

    def test_setup_password_mismatch(self):
        """Test password setup with mismatched passwords."""
        response = self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': 'DifferentPassword123!'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Passwords do not match', response.data)

    def test_login_page_loads_after_setup(self):
        """Test that login page loads after setup is complete."""
        # First set up password
        self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        })

        response = self.client.get('/login')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Login', response.data)
        self.assertIn(b'Master Password', response.data)

    def test_login_success(self):
        """Test successful login."""
        # First set up password
        self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        })

        # Then login
        response = self.client.post('/login', data={
            'password': self.test_password
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        # Should redirect to dashboard after successful login

    def test_login_incorrect_password(self):
        """Test login with incorrect password."""
        # First set up password
        self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        })

        # Then try to login with wrong password
        response = self.client.post('/login', data={
            'password': 'WrongPassword123!'
        })

        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Invalid password', response.data)

    def test_dashboard_requires_authentication(self):
        """Test that dashboard requires authentication."""
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)

    def test_logout_functionality(self):
        """Test logout functionality."""
        # First set up password and login
        self.client.post('/setup', data={
            'password': self.test_password,
            'confirm_password': self.test_password
        })

        self.client.post('/login', data={
            'password': self.test_password
        })

        # Then logout
        response = self.client.post('/logout', follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Should not be able to access dashboard after logout
        response = self.client.get('/dashboard')
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login', response.location)


if __name__ == '__main__':
    unittest.main()