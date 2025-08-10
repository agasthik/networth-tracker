# Networth Tracker - Scripts Directory

This directory contains startup and utility scripts for the Networth Tracker application.

## Scripts Overview

### Startup Scripts

#### `start.py`
Main Python startup script with comprehensive configuration and environment management.

**Usage:**
```bash
python scripts/start.py [OPTIONS]
```

**Options:**
- `--env {development,production,testing}`: Environment to run in
- `--host HOST`: Host to bind to (default: 127.0.0.1)
- `--port PORT`: Port to bind to (default: 5000)
- `--debug`: Enable debug mode
- `--validate-only`: Only validate configuration and exit
- `--create-dirs`: Create necessary directories and exit
- `--daemon`: Run as daemon (Unix/Linux/macOS only)
- `--pid-file FILE`: PID file for daemon mode

**Examples:**
```bash
# Start in production mode
python scripts/start.py

# Start in development mode with debug
python scripts/start.py --env development --debug

# Validate configuration only
python scripts/start.py --validate-only

# Start as daemon
python scripts/start.py --daemon
```

#### `start.sh` (Unix/Linux/macOS)
Shell script wrapper for easy startup on Unix-like systems.

**Usage:**
```bash
./scripts/start.sh [OPTIONS]
```

**Additional Options:**
- `--stop`: Stop running application
- `--status`: Check application status

**Examples:**
```bash
# Start application
./scripts/start.sh

# Start in development mode
./scripts/start.sh -e development

# Check status
./scripts/start.sh --status

# Stop application
./scripts/start.sh --stop
```

#### `start.bat` (Windows)
Batch script for Windows systems.

**Usage:**
```cmd
scripts\start.bat [OPTIONS]
```

**Examples:**
```cmd
REM Start application
scripts\start.bat

REM Start in development mode
scripts\start.bat -e development

REM Stop application
scripts\start.bat --stop
```

### Database Scripts

#### `init_db.py`
Database initialization and management script.

**Usage:**
```bash
python scripts/init_db.py [OPTIONS]
```

**Options:**
- `--env {development,production,testing}`: Environment
- `--database PATH`: Database path (overrides config)
- `--create`: Create new database
- `--migrate`: Run database migrations
- `--backup`: Create database backup
- `--verify`: Verify database integrity
- `--reset`: Reset database (removes all data)
- `--force`: Force operation (overwrite existing files)
- `--demo`: Operate on demo database

**Examples:**
```bash
# Create new database
python scripts/init_db.py --create

# Run migrations
python scripts/init_db.py --migrate

# Create backup
python scripts/init_db.py --backup

# Verify database
python scripts/init_db.py --verify

# Reset demo database
python scripts/init_db.py --reset --demo --force
```

## Quick Start

### First Time Setup

1. **Create virtual environment:**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # Unix/Linux/macOS
   # venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Initialize database:**
   ```bash
   python scripts/init_db.py --create
   ```

4. **Start application:**
   ```bash
   # Unix/Linux/macOS
   ./scripts/start.sh

   # Windows
   scripts\start.bat

   # Or directly with Python
   python scripts/start.py
   ```

### Development Setup

```bash
# Set up development environment
export FLASK_ENV=development

# Create development database
python scripts/init_db.py --create --env development

# Start in development mode
./scripts/start.sh -e development -D
```

### Production Setup

```bash
# Set up production environment
export FLASK_ENV=production

# Create production database
python scripts/init_db.py --create --env production

# Start in production mode
./scripts/start.sh -e production
```

## Environment Variables

The scripts respect the following environment variables:

### Core Settings
- `FLASK_ENV`: Environment (development/production/testing)
- `SECRET_KEY`: Flask secret key for sessions
- `DATABASE_PATH`: Path to main database file
- `DEMO_DATABASE_PATH`: Path to demo database file

### Logging Settings
- `LOG_LEVEL`: Logging level (DEBUG/INFO/WARNING/ERROR)
- `LOG_DIR`: Directory for log files
- `LOG_FILE`: Main log file name
- `ERROR_LOG_FILE`: Error log file name
- `MAX_LOG_SIZE`: Maximum log file size in bytes
- `LOG_BACKUP_COUNT`: Number of log backups to keep

### Application Settings
- `APP_MODE`: Application mode (production/demo)
- `STOCK_API_RATE_LIMIT`: Rate limit for stock API calls
- `STOCK_API_TIMEOUT`: Timeout for stock API calls
- `BACKUP_DIR`: Directory for backup files
- `MAX_BACKUP_FILES`: Maximum number of backup files to keep

## Configuration Files

### Environment-specific Configuration

Create `.env.{environment}` files for environment-specific settings:

#### `.env.development`
```bash
FLASK_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG
DATABASE_PATH=networth_dev.db
SESSION_TIMEOUT=28800
```

#### `.env.production`
```bash
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO
DATABASE_PATH=networth.db
SESSION_TIMEOUT=7200
```

#### `.env.testing`
```bash
FLASK_ENV=testing
DEBUG=True
LOG_LEVEL=DEBUG
DATABASE_PATH=:memory:
```

## Security Considerations

### File Permissions

The scripts automatically set secure file permissions:

- **Database files**: 600 (owner read/write only)
- **Log files**: 644 (owner read/write, others read)
- **Backup files**: 600 (owner read/write only)
- **Configuration files**: 600 (owner read/write only)

### Process Management

#### PID Files
- Created automatically when application starts
- Used to prevent multiple instances
- Cleaned up on graceful shutdown

#### Signal Handling
- SIGTERM: Graceful shutdown
- SIGINT: Interrupt (Ctrl+C)
- Automatic cleanup on exit

## Troubleshooting

### Common Issues

#### Permission Denied
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py
```

#### Port Already in Use
```bash
# Check what's using the port
lsof -i :5000

# Use different port
./scripts/start.sh --port 5001
```

#### Database Locked
```bash
# Stop all instances
./scripts/start.sh --stop

# Verify database
python scripts/init_db.py --verify
```

#### Virtual Environment Issues
```bash
# Recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Log Files

Check log files for detailed error information:
- `logs/networth_tracker.log`: General application logs
- `logs/networth_tracker_errors.log`: Error-specific logs

### Validation

Use the validation tools to check configuration:
```bash
# Validate configuration
python scripts/start.py --validate-only

# Verify database
python scripts/init_db.py --verify

# Check application status
./scripts/start.sh --status
```

## Advanced Usage

### Daemon Mode (Unix/Linux/macOS)

```bash
# Start as daemon
./scripts/start.sh --daemon

# Check if running
./scripts/start.sh --status

# Stop daemon
./scripts/start.sh --stop
```

### Custom Configuration

```bash
# Use custom database path
python scripts/start.py --env production
export DATABASE_PATH=/custom/path/networth.db

# Use custom port and host
./scripts/start.sh --host 0.0.0.0 --port 8080
```

### Backup and Recovery

```bash
# Create backup
python scripts/init_db.py --backup

# Reset database (with backup)
python scripts/init_db.py --reset --force

# Verify after operations
python scripts/init_db.py --verify
```

This scripts directory provides a complete toolkit for managing the Networth Tracker application across different environments and platforms.