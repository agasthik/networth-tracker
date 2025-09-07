# Networth Tracker - Deployment Guide

This guide covers deployment options and configurations for the Networth Tracker application in different environments.

## Table of Contents

- [Deployment Overview](#deployment-overview)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Security Considerations](#security-considerations)
- [Monitoring and Maintenance](#monitoring-and-maintenance)
- [Backup and Recovery](#backup-and-recovery)
- [Performance Optimization](#performance-optimization)

## Deployment Overview

The Networth Tracker is designed as a **local-first application** that runs on the user's machine. Unlike traditional web applications, it is not deployed to remote servers but rather installed and run locally for maximum privacy and security.

### Deployment Models

1. **Single User Local**: Standard installation on personal computer
2. **Portable Installation**: USB or portable drive deployment
3. **Network Isolated**: Air-gapped system deployment
4. **Development Environment**: Development and testing setup

## Local Development

### Development Environment Setup

```bash
# Clone repository
git clone <repository-url> networth-tracker
cd networth-tracker

# Set up development environment
export FLASK_ENV=development
python3 -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Initialize database
./venv/bin/python scripts/init_db.py --create --env development

# Start development server
./venv/bin/python scripts/start.py --env development --debug
```

### Development Configuration

Create a `.env.development` file:

```bash
# Development settings
FLASK_ENV=development
DEBUG=True
LOG_LEVEL=DEBUG

# Development database paths
DATABASE_PATH=networth_dev.db

# Extended session for development
SESSION_TIMEOUT=28800  # 8 hours

# Development logging
LOG_DIR=dev_logs
MAX_LOG_SIZE=52428800  # 50MB for development
```

### Hot Reloading

For development with automatic reloading:

```bash
# Enable Flask development mode
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start with auto-reload
./venv/bin/python scripts/start.py --env development --debug
```

## Production Deployment

### Production Environment Setup

#### System Requirements

**Minimum Production Requirements:**
- Python 3.8+
- 1GB RAM
- 500MB disk space
- Secure file system permissions

**Recommended Production Requirements:**
- Python 3.9+
- 2GB RAM
- 2GB disk space
- SSD storage for database
- Regular backup system

#### Production Installation

```bash
# Create production directory
sudo mkdir -p /opt/networth-tracker
sudo chown $USER:$USER /opt/networth-tracker
cd /opt/networth-tracker

# Set up production environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Set production configuration
export FLASK_ENV=production
export SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")

# Initialize production database
./venv/bin/python scripts/init_db.py --create --env production

# Set secure file permissions
chmod 700 /opt/networth-tracker
chmod 600 /opt/networth-tracker/*.db
```

#### Production Configuration

Create a `.env.production` file:

```bash
# Production settings
FLASK_ENV=production
DEBUG=False
LOG_LEVEL=INFO

# Security settings
SECRET_KEY=your-production-secret-key-here
SESSION_COOKIE_SECURE=False  # Still False for localhost
SESSION_COOKIE_HTTPONLY=True
SESSION_TIMEOUT=7200  # 2 hours

# Production database paths
DATABASE_PATH=/opt/networth-tracker/data/networth.db

# Logging configuration
LOG_DIR=/opt/networth-tracker/logs
LOG_LEVEL=INFO
MAX_LOG_SIZE=10485760  # 10MB
LOG_BACKUP_COUNT=10

# Backup configuration
BACKUP_DIR=/opt/networth-tracker/backups
MAX_BACKUP_FILES=30
```

#### Systemd Service (Linux)

Create `/etc/systemd/system/networth-tracker.service`:

```ini
[Unit]
Description=Networth Tracker Application
After=network.target

[Service]
Type=simple
User=networth
Group=networth
WorkingDirectory=/opt/networth-tracker
Environment=FLASK_ENV=production
ExecStart=/opt/networth-tracker/venv/bin/python scripts/start.py --env production --host 127.0.0.1 --port 5000
Restart=always
RestartSec=10

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/networth-tracker

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable networth-tracker
sudo systemctl start networth-tracker
sudo systemctl status networth-tracker
```

#### Windows Service

For Windows, create a service using `nssm` (Non-Sucking Service Manager):

```cmd
# Download and install NSSM
# https://nssm.cc/download

# Install service
nssm install NetworthTracker "C:\networth-tracker\venv\Scripts\python.exe"
nssm set NetworthTracker Arguments "scripts\start.py --env production"
nssm set NetworthTracker AppDirectory "C:\networth-tracker"
nssm set NetworthTracker DisplayName "Networth Tracker"
nssm set NetworthTracker Description "Personal financial portfolio tracking application"

# Start service
nssm start NetworthTracker
```

#### macOS LaunchAgent

Create `~/Library/LaunchAgents/com.networth.tracker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.networth.tracker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>/opt/networth-tracker/scripts/start.py</string>
        <string>--env</string>
        <string>production</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/opt/networth-tracker</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/opt/networth-tracker/logs/stdout.log</string>
    <key>StandardErrorPath</key>
    <string>/opt/networth-tracker/logs/stderr.log</string>
</dict>
</plist>
```

Load the service:

```bash
launchctl load ~/Library/LaunchAgents/com.networth.tracker.plist
launchctl start com.networth.tracker
```

### Portable Deployment

For portable installations (USB drives, etc.):

#### Portable Structure

```
networth-tracker-portable/
├── app/                    # Application files
├── data/                   # Database files
├── logs/                   # Log files
├── backups/               # Backup files
├── venv/                  # Virtual environment
├── start.bat              # Windows launcher
├── start.sh               # Unix launcher
└── README.txt             # Usage instructions
```

#### Portable Launcher (Windows)

Create `start.bat`:

```batch
@echo off
cd /d "%~dp0"
set FLASK_ENV=production
set DATABASE_PATH=%~dp0data\networth.db
set LOG_DIR=%~dp0logs
set BACKUP_DIR=%~dp0backups

app\venv\Scripts\python.exe app\scripts\start.py --env production
pause
```

#### Portable Launcher (Unix)

Create `start.sh`:

```bash
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

export FLASK_ENV=production
export DATABASE_PATH="$SCRIPT_DIR/data/networth.db"
export LOG_DIR="$SCRIPT_DIR/logs"
export BACKUP_DIR="$SCRIPT_DIR/backups"

app/venv/bin/python app/scripts/start.py --env production
```

## Security Considerations

### File System Security

#### Unix/Linux/macOS Permissions

```bash
# Application directory
chmod 750 /opt/networth-tracker

# Database files
chmod 600 /opt/networth-tracker/data/*.db

# Log files
chmod 644 /opt/networth-tracker/logs/*.log

# Backup files
chmod 600 /opt/networth-tracker/backups/*

# Configuration files
chmod 600 /opt/networth-tracker/.env*
```

#### Windows Security

```cmd
# Remove inheritance and set explicit permissions
icacls "C:\networth-tracker" /inheritance:r
icacls "C:\networth-tracker" /grant:r "%USERNAME%:(OI)(CI)F"
icacls "C:\networth-tracker\data" /grant:r "%USERNAME%:(OI)(CI)F"
```

### Network Security

Since the application runs locally:

- **Firewall**: No inbound rules needed
- **Binding**: Application binds to 127.0.0.1 only
- **SSL/TLS**: Not required for localhost
- **Authentication**: Master password provides access control

### Data Protection

```python
# Additional security measures in production
import os
import stat

def secure_file_creation(filepath):
    """Create file with secure permissions."""
    # Create file with restrictive permissions
    fd = os.open(filepath, os.O_CREAT | os.O_WRONLY, stat.S_IRUSR | stat.S_IWUSR)
    os.close(fd)

def validate_file_permissions(filepath):
    """Validate file has secure permissions."""
    if os.name != 'nt':  # Unix-like systems
        file_stat = os.stat(filepath)
        mode = stat.filemode(file_stat.st_mode)
        if not mode.startswith('-rw-------'):
            raise SecurityError(f"Insecure file permissions: {filepath}")
```

## Monitoring and Maintenance

### Health Monitoring

#### Health Check Endpoint

The application provides a health check endpoint:

```bash
curl http://127.0.0.1:5000/health
```

Response:
```json
{
    "status": "healthy",
    "app_mode": "production",
    "version": "1.0.0"
}
```

#### Log Monitoring

Monitor log files for issues:

```bash
# Monitor error logs
tail -f /opt/networth-tracker/logs/networth_tracker_errors.log

# Monitor application logs
tail -f /opt/networth-tracker/logs/networth_tracker.log

# Search for specific errors
grep -i "error" /opt/networth-tracker/logs/*.log
```

#### System Monitoring Script

Create `scripts/monitor.py`:

```python
#!/usr/bin/env python3
"""
System monitoring script for Networth Tracker.
Checks application health and system resources.
"""

import os
import sys
import psutil
import requests
from pathlib import Path

def check_application_health():
    """Check if application is responding."""
    try:
        response = requests.get('http://127.0.0.1:5000/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def check_disk_space(path, min_free_gb=1):
    """Check available disk space."""
    usage = psutil.disk_usage(path)
    free_gb = usage.free / (1024**3)
    return free_gb >= min_free_gb

def check_database_size(db_path, max_size_mb=100):
    """Check database file size."""
    if os.path.exists(db_path):
        size_mb = os.path.getsize(db_path) / (1024**2)
        return size_mb <= max_size_mb
    return True

def main():
    """Main monitoring function."""
    issues = []

    # Check application health
    if not check_application_health():
        issues.append("Application not responding")

    # Check disk space
    if not check_disk_space('/opt/networth-tracker'):
        issues.append("Low disk space")

    # Check database size
    if not check_database_size('/opt/networth-tracker/data/networth.db'):
        issues.append("Database file too large")

    if issues:
        print("ISSUES FOUND:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    else:
        print("All checks passed")
        return 0

if __name__ == '__main__':
    sys.exit(main())
```

### Automated Maintenance

#### Log Rotation

Create `scripts/rotate_logs.py`:

```python
#!/usr/bin/env python3
"""
Log rotation script for Networth Tracker.
"""

import os
import gzip
import shutil
from datetime import datetime
from pathlib import Path

def rotate_log_file(log_path, max_size_mb=10, max_files=5):
    """Rotate log file if it exceeds size limit."""
    if not os.path.exists(log_path):
        return

    size_mb = os.path.getsize(log_path) / (1024**2)
    if size_mb < max_size_mb:
        return

    # Create rotated filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotated_path = f"{log_path}.{timestamp}.gz"

    # Compress and rotate
    with open(log_path, 'rb') as f_in:
        with gzip.open(rotated_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)

    # Clear original log
    open(log_path, 'w').close()

    # Clean up old rotated files
    cleanup_old_logs(log_path, max_files)

def cleanup_old_logs(log_path, max_files):
    """Remove old rotated log files."""
    log_dir = Path(log_path).parent
    pattern = f"{Path(log_path).name}.*.gz"

    rotated_files = sorted(log_dir.glob(pattern))
    if len(rotated_files) > max_files:
        for old_file in rotated_files[:-max_files]:
            old_file.unlink()

def main():
    """Main log rotation function."""
    log_dir = Path('/opt/networth-tracker/logs')

    for log_file in ['networth_tracker.log', 'networth_tracker_errors.log']:
        log_path = log_dir / log_file
        rotate_log_file(str(log_path))

if __name__ == '__main__':
    main()
```

#### Cron Jobs (Linux/macOS)

Add to crontab (`crontab -e`):

```bash
# Monitor application every 5 minutes
*/5 * * * * /opt/networth-tracker/venv/bin/python /opt/networth-tracker/scripts/monitor.py

# Rotate logs daily at 2 AM
0 2 * * * /opt/networth-tracker/venv/bin/python /opt/networth-tracker/scripts/rotate_logs.py

# Create backup weekly on Sunday at 3 AM
0 3 * * 0 /opt/networth-tracker/venv/bin/python /opt/networth-tracker/scripts/backup.py
```

## Backup and Recovery

### Automated Backup Script

Create `scripts/backup.py`:

```python
#!/usr/bin/env python3
"""
Automated backup script for Networth Tracker.
"""

import os
import shutil
import gzip
from datetime import datetime
from pathlib import Path

def create_backup(source_dir, backup_dir, compress=True):
    """Create backup of application data."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"networth_backup_{timestamp}"

    if compress:
        backup_path = Path(backup_dir) / f"{backup_name}.tar.gz"
        shutil.make_archive(str(backup_path)[:-7], 'gztar', source_dir)
    else:
        backup_path = Path(backup_dir) / backup_name
        shutil.copytree(source_dir, backup_path)

    return backup_path

def cleanup_old_backups(backup_dir, max_backups=10):
    """Remove old backup files."""
    backup_files = sorted(Path(backup_dir).glob("networth_backup_*.tar.gz"))

    if len(backup_files) > max_backups:
        for old_backup in backup_files[:-max_backups]:
            old_backup.unlink()

def main():
    """Main backup function."""
    source_dir = '/opt/networth-tracker/data'
    backup_dir = '/opt/networth-tracker/backups'

    # Create backup
    backup_path = create_backup(source_dir, backup_dir)
    print(f"Backup created: {backup_path}")

    # Cleanup old backups
    cleanup_old_backups(backup_dir)
    print("Old backups cleaned up")

if __name__ == '__main__':
    main()
```

### Recovery Procedures

#### Database Recovery

```bash
# Stop application
sudo systemctl stop networth-tracker

# Backup current database (if recoverable)
cp /opt/networth-tracker/data/networth.db /opt/networth-tracker/data/networth.db.backup

# Restore from backup
tar -xzf /opt/networth-tracker/backups/networth_backup_YYYYMMDD_HHMMSS.tar.gz -C /opt/networth-tracker/

# Verify database integrity
python /opt/networth-tracker/scripts/init_db.py --verify

# Start application
sudo systemctl start networth-tracker
```

## Performance Optimization

### Database Optimization

```python
# Database performance settings
SQLITE_PRAGMAS = {
    'journal_mode': 'WAL',
    'cache_size': -64000,  # 64MB cache
    'temp_store': 'memory',
    'synchronous': 'NORMAL',
    'mmap_size': 268435456,  # 256MB memory map
}
```

### System Resource Optimization

#### Memory Usage

```python
# Monitor memory usage
import psutil
import gc

def optimize_memory():
    """Optimize memory usage."""
    # Force garbage collection
    gc.collect()

    # Get memory info
    process = psutil.Process()
    memory_info = process.memory_info()

    return {
        'rss': memory_info.rss / 1024 / 1024,  # MB
        'vms': memory_info.vms / 1024 / 1024   # MB
    }
```

#### Disk I/O Optimization

```bash
# Use SSD for database files
# Mount with appropriate options for SSDs
mount -o noatime,discard /dev/ssd1 /opt/networth-tracker/data

# Set appropriate I/O scheduler
echo noop > /sys/block/ssd1/queue/scheduler
```

### Application Performance

#### Caching Strategy

```python
from functools import lru_cache
from datetime import datetime, timedelta

class PerformanceOptimizer:
    def __init__(self):
        self.cache_timeout = timedelta(minutes=5)
        self.last_stock_update = None

    @lru_cache(maxsize=128)
    def get_cached_stock_price(self, symbol, cache_key):
        """Cache stock prices with timeout."""
        # Implementation here
        pass

    def should_update_stocks(self):
        """Check if stock prices need updating."""
        if not self.last_stock_update:
            return True
        return datetime.now() - self.last_stock_update > self.cache_timeout
```

This deployment guide provides comprehensive instructions for deploying the Networth Tracker application in various environments while maintaining security and performance standards.