#!/usr/bin/env python3
"""
Configuration management for Networth Tracker application.
Supports different environments (development, production, testing).
"""

import os
import secrets
from datetime import timedelta
from typing import Dict, Any, Optional
from pathlib import Path


class BaseConfig:
    """Base configuration with common settings."""

    # Application settings
    APP_NAME = "Networth Tracker"
    VERSION = "1.0.0"

    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SESSION_COOKIE_SECURE = False  # HTTP for localhost
    SESSION_COOKIE_HTTPONLY = True  # No JavaScript access to session
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # Database settings
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'networth.db')

    # Application mode
    APP_MODE = os.environ.get('APP_MODE', 'production')

    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.environ.get('LOG_DIR', 'logs')
    LOG_FILE = os.environ.get('LOG_FILE', 'networth_tracker.log')
    ERROR_LOG_FILE = os.environ.get('ERROR_LOG_FILE', 'networth_tracker_errors.log')
    MAX_LOG_SIZE = int(os.environ.get('MAX_LOG_SIZE', '10485760'))  # 10MB
    LOG_BACKUP_COUNT = int(os.environ.get('LOG_BACKUP_COUNT', '5'))

    # Stock API settings
    STOCK_API_RATE_LIMIT = float(os.environ.get('STOCK_API_RATE_LIMIT', '1.0'))  # seconds
    STOCK_API_TIMEOUT = int(os.environ.get('STOCK_API_TIMEOUT', '30'))  # seconds

    # File permissions (Unix/Linux/macOS)
    DATABASE_FILE_MODE = 0o600  # Owner read/write only
    LOG_FILE_MODE = 0o600  # Owner read/write only - secure for financial data
    BACKUP_FILE_MODE = 0o600  # Owner read/write only
    TEMP_FILE_MODE = 0o600  # Owner read/write only
    SECURE_DIR_MODE = 0o700  # Owner access only

    # Backup settings
    BACKUP_DIR = os.environ.get('BACKUP_DIR', 'backups')
    MAX_BACKUP_FILES = int(os.environ.get('MAX_BACKUP_FILES', '10'))

    @classmethod
    def init_app(cls, app):
        """Initialize Flask app with configuration."""
        # Create necessary directories
        cls._create_directories()

        # Set file permissions
        cls._set_file_permissions()

        # Configure Flask app
        app.config.from_object(cls)

    @classmethod
    def _create_directories(cls):
        """Create necessary directories for the application."""
        directories = [
            cls.LOG_DIR,
            cls.BACKUP_DIR,
            'data',  # For database files
            'temp'   # For temporary files
        ]

        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)

    @classmethod
    def _set_file_permissions(cls):
        """Set appropriate file permissions for security."""
        if os.name == 'nt':  # Windows
            return  # Skip file permissions on Windows

        try:
            # Set permissions for database files if they exist
            if os.path.exists(cls.DATABASE_PATH):
                os.chmod(cls.DATABASE_PATH, cls.DATABASE_FILE_MODE)

            # Set permissions for sensitive directories
            sensitive_directories = [
                cls.LOG_DIR,
                cls.BACKUP_DIR,
                'data',  # Database files directory
                'temp'   # Temporary files directory
            ]

            for directory in sensitive_directories:
                if os.path.exists(directory):
                    os.chmod(directory, cls.SECURE_DIR_MODE)  # Owner access only

            # Set permissions for log files
            if os.path.exists(cls.LOG_DIR):
                for log_file in [cls.LOG_FILE, cls.ERROR_LOG_FILE]:
                    log_path = os.path.join(cls.LOG_DIR, log_file)
                    if os.path.exists(log_path):
                        os.chmod(log_path, cls.LOG_FILE_MODE)

            # Set permissions for backup files
            if os.path.exists(cls.BACKUP_DIR):
                import glob
                backup_files = glob.glob(os.path.join(cls.BACKUP_DIR, '*'))
                for backup_file in backup_files:
                    if os.path.isfile(backup_file):
                        os.chmod(backup_file, cls.BACKUP_FILE_MODE)  # Owner read/write only

        except PermissionError as e:
            print(f"Warning: Could not set file permissions: {e}")

    @classmethod
    def _enforce_strict_permissions(cls):
        """Enforce strict file permissions for production."""
        if os.name == 'nt':  # Windows
            return  # Skip file permissions on Windows

        try:
            # Ensure database files have strict permissions
            if os.path.exists(cls.DATABASE_PATH):
                os.chmod(cls.DATABASE_PATH, cls.DATABASE_FILE_MODE)  # Owner read/write only

            # Ensure all sensitive directories have strict permissions
            sensitive_directories = [
                cls.LOG_DIR,
                cls.BACKUP_DIR,
                'data',  # Database files directory
                'temp'   # Temporary files directory
            ]

            for directory in sensitive_directories:
                if os.path.exists(directory):
                    os.chmod(directory, cls.SECURE_DIR_MODE)  # Owner access only

            # Ensure all files in sensitive directories have strict permissions
            import glob

            # Secure log files
            if os.path.exists(cls.LOG_DIR):
                log_files = glob.glob(os.path.join(cls.LOG_DIR, '*'))
                for log_file in log_files:
                    if os.path.isfile(log_file):
                        os.chmod(log_file, cls.LOG_FILE_MODE)

            # Secure backup files
            if os.path.exists(cls.BACKUP_DIR):
                backup_files = glob.glob(os.path.join(cls.BACKUP_DIR, '*'))
                for backup_file in backup_files:
                    if os.path.isfile(backup_file):
                        os.chmod(backup_file, cls.BACKUP_FILE_MODE)

            # Secure data directory files (database files)
            if os.path.exists('data'):
                data_files = glob.glob(os.path.join('data', '*'))
                for data_file in data_files:
                    if os.path.isfile(data_file):
                        os.chmod(data_file, cls.DATABASE_FILE_MODE)

            # Secure temp directory files
            if os.path.exists('temp'):
                temp_files = glob.glob(os.path.join('temp', '*'))
                for temp_file in temp_files:
                    if os.path.isfile(temp_file):
                        os.chmod(temp_file, cls.TEMP_FILE_MODE)

        except PermissionError as e:
            print(f"Warning: Could not enforce strict permissions: {e}")


class DevelopmentConfig(BaseConfig):
    """Development environment configuration."""

    DEBUG = True
    TESTING = False

    # More verbose logging in development
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'DEBUG')

    # Development database paths
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'networth_dev.db')

    # Shorter session timeout for development
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)


class ProductionConfig(BaseConfig):
    """Production environment configuration."""

    DEBUG = False
    TESTING = False

    # Production logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')

    # Production database paths
    DATABASE_PATH = os.environ.get('DATABASE_PATH', 'networth.db')

    # Standard session timeout
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    @classmethod
    def init_app(cls, app):
        """Initialize production app with additional security measures."""
        super().init_app(app)

        # Additional production security
        app.config['SESSION_COOKIE_SECURE'] = False  # Still False for localhost

        # Ensure strict file permissions in production
        cls._enforce_strict_permissions()


class TestingConfig(BaseConfig):
    """Testing environment configuration."""

    DEBUG = True
    TESTING = True

    # Test database paths (in memory or temporary)
    DATABASE_PATH = os.environ.get('TEST_DATABASE_PATH', ':memory:')

    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False

    # Short session timeout for testing
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)

    # Test logging
    LOG_LEVEL = 'DEBUG'
    LOG_DIR = 'test_logs'


class ConfigManager:
    """Configuration manager for different environments."""

    _configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
        'default': ProductionConfig
    }

    @classmethod
    def get_config(cls, config_name: Optional[str] = None) -> BaseConfig:
        """Get configuration class for the specified environment."""
        if config_name is None:
            config_name = os.environ.get('FLASK_ENV', 'production')

        return cls._configs.get(config_name, cls._configs['default'])

    @classmethod
    def create_directories(cls):
        """Create necessary application directories."""
        BaseConfig._create_directories()


# Environment detection
def get_environment() -> str:
    """Detect the current environment."""
    return os.environ.get('FLASK_ENV', 'production')


def is_development() -> bool:
    """Check if running in development mode."""
    return get_environment() == 'development'


def is_production() -> bool:
    """Check if running in production mode."""
    return get_environment() == 'production'


def is_testing() -> bool:
    """Check if running in testing mode."""
    return get_environment() == 'testing'


# Configuration validation
def validate_config(config: BaseConfig) -> Dict[str, Any]:
    """Validate configuration settings and return status."""
    validation_results = {
        'valid': True,
        'warnings': [],
        'errors': []
    }

    # Check required directories
    required_dirs = [config.LOG_DIR, config.BACKUP_DIR]
    for directory in required_dirs:
        if not os.path.exists(directory):
            validation_results['warnings'].append(f"Directory does not exist: {directory}")

    # Check database file permissions (Unix/Linux/macOS only)
    if os.name != 'nt':
        if os.path.exists(config.DATABASE_PATH):
            file_mode = oct(os.stat(config.DATABASE_PATH).st_mode)[-3:]
            if file_mode != '600':
                validation_results['warnings'].append(
                    f"Database file {config.DATABASE_PATH} has permissions {file_mode}, should be 600"
                )

    # Check secret key strength
    if len(config.SECRET_KEY) < 32:
        validation_results['errors'].append("SECRET_KEY should be at least 32 characters long")
        validation_results['valid'] = False

    # Check log file size limits
    if config.MAX_LOG_SIZE < 1024 * 1024:  # 1MB minimum
        validation_results['warnings'].append("MAX_LOG_SIZE is very small, consider increasing")

    return validation_results


# Export the configuration classes and manager
__all__ = [
    'BaseConfig',
    'DevelopmentConfig',
    'ProductionConfig',
    'TestingConfig',
    'ConfigManager',
    'get_environment',
    'is_development',
    'is_production',
    'is_testing',
    'validate_config'
]