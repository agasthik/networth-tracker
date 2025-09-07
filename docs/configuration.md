# Configuration Reference

Complete reference for configuring the Networth Tracker application.

## Table of Contents

- [Overview](#overview)
- [Environment Configuration](#environment-configuration)
- [Environment Variables](#environment-variables)
- [Configuration Classes](#configuration-classes)
- [Startup Options](#startup-options)
- [Security Settings](#security-settings)
- [File Permissions](#file-permissions)
- [Configuration Validation](#configuration-validation)

## Overview

The Networth Tracker uses a class-based configuration system with support for different environments. Configuration is managed through environment variables and Python configuration classes defined in `config.py`.

### Key Features
- **Environment-based configuration**: Development, Production, and Testing environments
- **Environment variable support**: Override defaults with environment variables
- **Automatic directory creation**: Required directories created on startup
- **File permission management**: Secure file permissions set automatically
- **Configuration validation**: Built-in validation with detailed reporting

## Environment Configuration

The application supports three environments, controlled by the `FLASK_ENV` environment variable:

### Development Environment
```bash
export FLASK_ENV=development
./venv/bin/python scripts/start.py
```

**Features:**
- Debug mode enabled
- Verbose logging (DEBUG level)
- Extended session timeout (8 hours)
- Separate development database (`networth_dev.db`)

### Production Environment (Default)
```bash
export FLASK_ENV=production  # or omit (default)
./venv/bin/python scripts/start.py
```

**Features:**
- Debug mode disabled
- Standard logging (INFO level)
- Standard session timeout (2 hours)
- Production database (`networth.db`)
- Enhanced security measures

### Testing Environment
```bash
export FLASK_ENV=testing
./venv/bin/python scripts/start.py
```

**Features:**
- Debug mode enabled
- In-memory database (`:memory:`)
- Short session timeout (30 minutes)
- Test-specific logging directory

## Environment Variables

### Core Application Settings

| Variable | Description | Default | Development | Production | Testing |
|----------|-------------|---------|-------------|------------|---------|
| `FLASK_ENV` | Environment name | `production` | `development` | `production` | `testing` |
| `SECRET_KEY` | Flask secret key | Auto-generated | Auto-generated | Auto-generated | Auto-generated |
| `APP_MODE` | Application mode | `production` | `development` | `production` | `testing` |

### Database Settings

| Variable | Description | Default | Development | Production | Testing |
|----------|-------------|---------|-------------|------------|---------|
| `DATABASE_PATH` | Database file path | `networth.db` | `networth_dev.db` | `networth.db` | `:memory:` |

### Logging Settings

| Variable | Description | Default | Development | Production | Testing |
|----------|-------------|---------|-------------|------------|---------|
| `LOG_LEVEL` | Logging level | `INFO` | `DEBUG` | `INFO` | `DEBUG` |
| `LOG_DIR` | Log directory | `logs` | `logs` | `logs` | `test_logs` |
| `LOG_FILE` | Main log file | `networth_tracker.log` | Same | Same | Same |
| `ERROR_LOG_FILE` | Error log file | `networth_tracker_errors.log` | Same | Same | Same |
| `MAX_LOG_SIZE` | Max log file size (bytes) | `10485760` (10MB) | Same | Same | Same |
| `LOG_BACKUP_COUNT` | Number of log backups | `5` | Same | Same | Same |

### Stock API Settings

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `STOCK_API_RATE_LIMIT` | Rate limit (seconds) | `1.0` | Minimum time between API calls |
| `STOCK_API_TIMEOUT` | Request timeout (seconds) | `30` | HTTP request timeout |

### Backup Settings

| Variable | Description | Default | Notes |
|----------|-------------|---------|-------|
| `BACKUP_DIR` | Backup directory | `backups` | Directory for data backups |
| `MAX_BACKUP_FILES` | Max backup files | `10` | Automatic cleanup threshold |

## Configuration Classes

### BaseConfig
The base configuration class with common settings:

```python
from config import BaseConfig

class BaseConfig:
    # Application settings
    APP_NAME = "Networth Tracker"
    VERSION = "1.0.0"

    # Security settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
    SESSION_COOKIE_SECURE = False  # HTTP for localhost
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)

    # File permissions
    DATABASE_FILE_MODE = 0o600  # Owner read/write only
    LOG_FILE_MODE = 0o644       # Owner read/write, others read
```

### DevelopmentConfig
Extends BaseConfig with development-specific settings:

```python
class DevelopmentConfig(BaseConfig):
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    DATABASE_PATH = 'networth_dev.db'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
```

### ProductionConfig
Extends BaseConfig with production-specific settings:

```python
class ProductionConfig(BaseConfig):
    DEBUG = False
    LOG_LEVEL = 'INFO'
    DATABASE_PATH = 'networth.db'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
```

### TestingConfig
Extends BaseConfig with testing-specific settings:

```python
class TestingConfig(BaseConfig):
    DEBUG = True
    TESTING = True
    DATABASE_PATH = ':memory:'
    PERMANENT_SESSION_LIFETIME = timedelta(minutes=30)
    LOG_DIR = 'test_logs'
```

### Using Configuration

```python
from config import ConfigManager

# Get configuration for current environment
config = ConfigManager.get_config()

# Get specific environment configuration
dev_config = ConfigManager.get_config('development')
prod_config = ConfigManager.get_config('production')
test_config = ConfigManager.get_config('testing')
```

## Startup Options

The `scripts/start.py` script provides several configuration options:

### Basic Usage
```bash
# Start with default settings
./venv/bin/python scripts/start.py

# Start in development mode
./venv/bin/python scripts/start.py --env development

# Start with debug mode
./venv/bin/python scripts/start.py --debug

# Start on different port
./venv/bin/python scripts/start.py --port 5001
```

### Configuration Management
```bash
# Validate configuration only
./venv/bin/python scripts/start.py --validate-only

# Create necessary directories
./venv/bin/python scripts/start.py --create-dirs

# Start in daemon mode (Unix/Linux/macOS only)
./venv/bin/python scripts/start.py --daemon --pid-file networth.pid
```

### Full Options
```bash
./venv/bin/python scripts/start.py \
    --env production \
    --host 127.0.0.1 \
    --port 5000 \
    --debug \
    --daemon \
    --pid-file /var/run/networth.pid
```

## Security Settings

### Session Security
The application uses secure session configuration:

```python
# Session cookies (configured automatically)
SESSION_COOKIE_SECURE = False      # HTTP for localhost
SESSION_COOKIE_HTTPONLY = True     # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Auto-logout
```

### Secret Key
- **Auto-generated**: 32-byte random key generated automatically
- **Environment override**: Set `SECRET_KEY` environment variable for custom key
- **Validation**: Configuration validation checks key strength

### Database Security
- **Encryption**: All financial data encrypted with master password
- **File permissions**: Database files set to 600 (owner read/write only)
- **Access control**: Master password required for access

## File Permissions

The application automatically sets secure file permissions on Unix/Linux/macOS systems:

### Database Files
```bash
chmod 600 *.db  # Owner read/write only
```

### Log Files
```bash
chmod 644 logs/*.log  # Owner read/write, others read
```

### Backup Files
```bash
chmod 600 backups/*  # Owner read/write only
```

### Directory Structure
```
networth-tracker/
├── data/           # 755 - Database directory
├── logs/           # 755 - Log files
├── backups/        # 700 - Backup files (owner only)
└── temp/           # 700 - Temporary files (owner only)
```

**Note**: File permissions are not set on Windows systems due to different permission models.

## Configuration Validation

### Validation Command
```bash
# Validate current configuration
./venv/bin/python scripts/start.py --validate-only

# Validate specific environment
./venv/bin/python scripts/start.py --env development --validate-only
```

### Validation Checks
The validation system checks:

1. **Required directories exist**
2. **File permissions are secure** (Unix/Linux/macOS)
3. **Secret key strength** (minimum 32 characters)
4. **Log file size limits** (reasonable values)
5. **Database accessibility**

### Example Validation Output
```
[INFO] Configuration validation started
[INFO] Environment: production
[INFO] Database path: networth.db
[INFO] Log directory: logs
[WARNING] Database file permissions are 644, should be 600
[INFO] Secret key strength: OK
[INFO] All required directories exist
[INFO] Configuration validation completed
```

### Validation Results
- **Errors**: Critical issues that prevent startup
- **Warnings**: Issues that should be addressed but don't prevent startup
- **Info**: Confirmation of correct settings

## Environment Variable Examples

### Development Setup
```bash
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
export DATABASE_PATH=dev_networth.db
export MAX_LOG_SIZE=52428800  # 50MB for development
./venv/bin/python scripts/start.py --debug
```

### Production Setup
```bash
export FLASK_ENV=production
export LOG_LEVEL=INFO
export DATABASE_PATH=/opt/networth/data/networth.db
export LOG_DIR=/opt/networth/logs
export BACKUP_DIR=/opt/networth/backups
export SECRET_KEY=your-production-secret-key-here
./venv/bin/python scripts/start.py --daemon --pid-file /var/run/networth.pid
```

### Testing Setup
```bash
export FLASK_ENV=testing
export DATABASE_PATH=:memory:
export LOG_LEVEL=DEBUG
./venv/bin/python scripts/start.py --validate-only
```

## Troubleshooting Configuration

### Common Issues

**Permission Denied**
```bash
# Check and fix file permissions
ls -la *.db
chmod 600 *.db
```

**Missing Directories**
```bash
# Create required directories
./venv/bin/python scripts/start.py --create-dirs
```

**Invalid Configuration**
```bash
# Validate configuration
./venv/bin/python scripts/start.py --validate-only
```

**Environment Issues**
```bash
# Check current environment
echo $FLASK_ENV

# Reset environment
unset FLASK_ENV
export FLASK_ENV=production
```

### Debug Configuration
```bash
# Start with maximum verbosity
export FLASK_ENV=development
export LOG_LEVEL=DEBUG
./venv/bin/python scripts/start.py --env development --debug
```

### Configuration Reset
```bash
# Remove custom environment variables
unset FLASK_ENV LOG_LEVEL DATABASE_PATH

# Recreate directories with defaults
./venv/bin/python scripts/start.py --create-dirs

# Validate default configuration
./venv/bin/python scripts/start.py --validate-only
```

This configuration system provides a robust, secure, and flexible foundation for the Networth Tracker application while maintaining simplicity for end users.