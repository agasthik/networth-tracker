# Troubleshooting Guide

Comprehensive troubleshooting guide for common issues with the Networth Tracker application.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Installation Issues](#installation-issues)
- [Startup Problems](#startup-problems)
- [Authentication Issues](#authentication-issues)
- [Database Problems](#database-problems)
- [Network and API Issues](#network-and-api-issues)
- [Performance Issues](#performance-issues)
- [Data Issues](#data-issues)
- [Platform-Specific Issues](#platform-specific-issues)
- [Advanced Troubleshooting](#advanced-troubleshooting)

## Quick Diagnostics

### Health Check Commands

Run these commands to quickly diagnose common issues:

```bash
# Check application status
./scripts/start.sh --status  # macOS/Linux
scripts\start.bat --status   # Windows

# Validate configuration
./venv/bin/python scripts/start.py --validate-only

# Verify database
./venv/bin/python scripts/init_db.py --verify

# Or using startup scripts
./scripts/start.sh --validate  # macOS/Linux
scripts\start.bat --validate   # Windows

# Verify database integrity
./venv/bin/python scripts/init_db.py --verify

# Check recent logs
tail -20 logs/networth_tracker.log  # macOS/Linux
type logs\networth_tracker.log | more  # Windows
tail -10 logs/networth_tracker_errors.log  # macOS/Linux
type logs\networth_tracker_errors.log | more  # Windows
```

### System Requirements Check

```bash
# Check Python version (should be 3.8+)
python3 --version  # macOS/Linux
python --version   # Windows

# Check available disk space
df -h .  # macOS/Linux
dir      # Windows

# Check memory usage
free -h    # Linux
vm_stat    # macOS
tasklist   # Windows

# Check if port is available
netstat -an | grep :5000      # macOS/Linux
netstat -an | findstr :5000   # Windows
```

## Installation Issues

### Python Not Found

**Symptoms:**
- `'python' is not recognized as an internal or external command`
- `python3: command not found`

**Solutions:**

**Windows:**
```cmd
# Check if Python is installed
where python
where python3

# If not found, download from python.org
# During installation, check "Add Python to PATH"

# Verify installation
python --version
```

**macOS:**
```bash
# Install using Homebrew
brew install python@3.9

# Or use system Python
python3 --version

# Add to PATH if needed
echo 'export PATH="/usr/local/opt/python@3.9/bin:$PATH"' >> ~/.zshrc
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip

# Verify installation
python3 --version
```

### Virtual Environment Issues

**Symptoms:**
- `No module named 'flask'`
- Import errors for required packages

**Solutions:**

```bash
# Remove existing virtual environment
rm -rf venv

# Create new virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Verify installation
pip list
```

### Permission Denied Errors

**Symptoms:**
- `Permission denied` when running scripts
- Cannot create files or directories

**Solutions:**

**macOS/Linux:**
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Check directory permissions
ls -la

# Fix ownership if needed
sudo chown -R $USER:$USER .

# Set proper permissions
chmod 755 .
chmod 600 *.db
chmod 644 logs/*.log
```

**Windows:**
```cmd
# Run as Administrator
# Right-click Command Prompt -> "Run as administrator"

# Check file permissions
icacls networth-tracker

# Fix permissions if needed
icacls networth-tracker /grant %USERNAME%:F /T
```

## Startup Problems

### Port Already in Use

**Symptoms:**
- `Address already in use`
- `Port 5000 is already in use`

**Solutions:**

```bash
# Check what's using the port
lsof -i :5000  # macOS/Linux
netstat -ano | findstr :5000  # Windows

# Kill the process if it's a zombie
kill <PID>  # macOS/Linux
taskkill /PID <PID> /F  # Windows

# Use a different port
./venv/bin/python scripts/start.py --port 5001
./scripts/start.sh --port 5001  # macOS/Linux
scripts\start.bat --port 5001   # Windows
```

### Application Won't Start

**Symptoms:**
- Script exits immediately
- No error messages
- Browser can't connect

**Diagnostic Steps:**

```bash
# Check for Python errors
./venv/bin/python scripts/start.py --env development --debug

# Check configuration
./venv/bin/python scripts/start.py --validate-only

# Check logs
cat logs/networth_tracker_errors.log

# Try minimal startup
python -c "from app import app; app.run(debug=True)"
```

### Import Errors

**Symptoms:**
- `ModuleNotFoundError`
- `ImportError`

**Solutions:**

```bash
# Ensure virtual environment is activated
which python  # Should point to venv/bin/python

# Check if modules are installed
pip list | grep flask
pip list | grep cryptography

# Reinstall requirements
pip install -r requirements.txt --force-reinstall

# Check Python path
python -c "import sys; print(sys.path)"
```

## Authentication Issues

### Forgot Master Password

**Symptoms:**
- Cannot log into the application
- "Invalid password" error

**Solutions:**

Unfortunately, there is **no password recovery mechanism** by design for security. Your options are:

1. **Try variations**: Common typos, caps lock, different keyboards
2. **Restore from backup**: If you have an exported backup file
3. **Start fresh**: Create new database (loses all data)

```bash
# Create new database (WARNING: Deletes all data)
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows

# Backup existing database
mv networth.db networth.db.backup  # macOS/Linux
move networth.db networth.db.backup  # Windows

# Create new database
./venv/bin/python scripts/init_db.py --create --force
```

### Session Timeout Issues

**Symptoms:**
- Frequent logouts
- Session expires quickly

**Solutions:**

The session timeout is configured in the application code, not through environment files. To extend session timeout:

```bash
# Check current configuration
./venv/bin/python scripts/start.py --validate-only

# Session timeout is controlled by PERMANENT_SESSION_LIFETIME in config.py
# Default is 2 hours for production, 8 hours for development

# Use development mode for longer sessions
export FLASK_ENV=development  # macOS/Linux
set FLASK_ENV=development     # Windows

# Restart application
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows
```

### Authentication Loops

**Symptoms:**
- Redirected to login repeatedly
- Cannot stay logged in

**Solutions:**

```bash
# Clear browser cache and cookies
# Try incognito/private browsing mode

# Restart application with fresh session
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows

# If problem persists, check logs for authentication errors
tail -20 logs/networth_tracker_errors.log  # macOS/Linux
type logs\networth_tracker_errors.log | more  # Windows
```

## Database Problems

### Database Locked

**Symptoms:**
- `database is locked`
- Cannot save changes
- Application hangs on database operations

**Solutions:**

```bash
# Stop all application instances
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows

# Kill any remaining processes
pkill -f "python.*start.py"  # macOS/Linux
taskkill /F /IM python.exe   # Windows

# Check for database connections (macOS/Linux only)
lsof networth.db  # macOS/Linux

# Wait and restart
sleep 5  # macOS/Linux
timeout 5  # Windows
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows

# If still locked, check file permissions
ls -la networth.db  # macOS/Linux
dir networth.db     # Windows
chmod 600 networth.db  # macOS/Linux only
```

### Database Corruption

**Symptoms:**
- `database disk image is malformed`
- SQLite errors in logs
- Data appears corrupted

**Solutions:**

```bash
# Stop application
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows

# Backup current database
cp networth.db networth.db.corrupt  # macOS/Linux
copy networth.db networth.db.corrupt  # Windows

# Try SQLite recovery (if sqlite3 is available)
sqlite3 networth.db ".recover" | sqlite3 networth_recovered.db

# Verify recovered database
./venv/bin/python scripts/init_db.py --verify

# If recovery successful, replace original
mv networth_recovered.db networth.db  # macOS/Linux
move networth_recovered.db networth.db  # Windows

# If recovery fails, restore from backup using the application's import feature
# 1. Start the application
# 2. Use Import Data feature to restore from backup file
```

### Migration Failures

**Symptoms:**
- Database version errors
- Schema mismatch errors
- Migration script failures

**Solutions:**

```bash
# Check current database version
./venv/bin/python scripts/init_db.py --verify

# Backup before migration
./venv/bin/python scripts/init_db.py --backup

# Run migration manually
./venv/bin/python scripts/init_db.py --migrate

# If migration fails, restore backup
cp backups/latest_backup.db networth.db

# Check logs for specific errors
grep -i migration logs/networth_tracker_errors.log
```

## Network and API Issues

### Stock Prices Not Updating

**Symptoms:**
- Stock prices show as "N/A"
- Old prices displayed
- API timeout errors

**Solutions:**

```bash
# Check internet connection
ping google.com

# Test API manually (if curl is available)
curl "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"

# Check API rate limiting in logs
grep -i "rate limit" logs/networth_tracker.log  # macOS/Linux
findstr /i "rate limit" logs\networth_tracker.log  # Windows

# Stock API settings are configured in config.py
# Default timeout is 30 seconds, rate limit is 1 second between requests
# To modify, set environment variables:
export STOCK_API_TIMEOUT=60  # macOS/Linux
set STOCK_API_TIMEOUT=60     # Windows

# Restart application
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows
```

### Cannot Access Application in Browser

**Symptoms:**
- "This site can't be reached"
- Connection refused errors
- Page won't load

**Solutions:**

```bash
# Verify application is running
./scripts/start.sh --status  # macOS/Linux
scripts\start.bat --status   # Windows

# Check correct URL
echo "Try: http://127.0.0.1:5000"
echo "NOT: https://127.0.0.1:5000"

# Check firewall settings
# Ensure localhost traffic is allowed

# Try different browser
# Try incognito/private mode

# Check for proxy settings
# Disable proxy for localhost

# Check if application is bound to correct interface
netstat -an | grep :5000      # macOS/Linux
netstat -an | findstr :5000   # Windows
```

### SSL/TLS Errors

**Symptoms:**
- Certificate errors
- SSL handshake failures

**Solutions:**

The application runs on HTTP (not HTTPS) for localhost:

```bash
# Use HTTP, not HTTPS
http://127.0.0.1:5000  # Correct
# https://127.0.0.1:5000  # Wrong

# If browser forces HTTPS, clear HSTS settings
# Chrome: chrome://net-internals/#hsts
# Firefox: about:config -> security.tls.insecure_fallback_hosts
```

## Performance Issues

### Slow Application Response

**Symptoms:**
- Pages load slowly
- Database operations timeout
- High CPU usage

**Solutions:**

```bash
# Check system resources
top     # Linux/macOS
taskmgr # Windows (or Task Manager GUI)

# Check database size
ls -lh *.db  # macOS/Linux
dir *.db     # Windows

# Optimize database (if sqlite3 is available)
sqlite3 networth.db "VACUUM;"
sqlite3 networth.db "ANALYZE;"

# Check for large log files
ls -lh logs/  # macOS/Linux
dir logs\     # Windows

# Log rotation is handled automatically by the application
# Check log configuration in config.py:
# MAX_LOG_SIZE = 10MB (default)
# LOG_BACKUP_COUNT = 5 (default)
```

### Memory Issues

**Symptoms:**
- Out of memory errors
- Application crashes
- System becomes unresponsive

**Solutions:**

```bash
# Check memory usage
ps aux | grep python  # Linux/macOS
tasklist | findstr python  # Windows

# The application is designed to be lightweight
# Memory usage is typically under 100MB for normal operation

# If experiencing memory issues:
# 1. Check for memory leaks in logs
# 2. Restart the application periodically
# 3. Ensure adequate system RAM (minimum 512MB)

# Restart application
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows
```

### Disk Space Issues

**Symptoms:**
- "No space left on device"
- Cannot save data
- Backup failures

**Solutions:**

```bash
# Check disk space
df -h .  # Linux/macOS
dir  # Windows

# Clean up log files
find logs/ -name "*.log.*" -mtime +30 -delete

# Clean up old backups
find backups/ -name "*.db" -mtime +90 -delete

# Compress old logs
gzip logs/*.log.old
```

## Data Issues

### Missing or Incorrect Data

**Symptoms:**
- Accounts not displaying
- Incorrect balances
- Missing historical data

**Solutions:**

```bash
# Check database integrity
python scripts/init_db.py --verify

# Check for data corruption (if sqlite3 is available)
sqlite3 networth.db "PRAGMA integrity_check;"

# Restore from backup using the application's import feature:
# 1. Start the application
# 2. Go to Import Data
# 3. Select your backup file
# 4. Enter master password
# 5. Confirm import

# Check logs for data errors
grep -i "data" logs/networth_tracker_errors.log  # macOS/Linux
findstr /i "data" logs\networth_tracker_errors.log  # Windows
```

### Export/Import Issues

**Symptoms:**
- Export fails
- Import errors
- Corrupted backup files

**Solutions:**

```bash
# Check file permissions
ls -la backups/  # macOS/Linux
dir backups\     # Windows

# Export/Import should be done through the web interface:
# 1. Log into the application
# 2. Use Export Data feature to create backups
# 3. Use Import Data feature to restore backups

# Check backup files (they are encrypted)
ls -la backups/  # macOS/Linux
dir backups\     # Windows

# Backup files have .enc extension and are encrypted
# They cannot be read directly without the application
```

## Platform-Specific Issues

### Windows Issues

**Common Problems:**
- Path separator issues
- Permission problems
- Antivirus interference

**Solutions:**

```cmd
# Use Windows-style paths
set DATABASE_PATH=data\networth.db

# Disable antivirus scanning for app directory
# Add exclusion in Windows Defender

# Use Windows batch files
scripts\start.bat instead of scripts/start.sh

# Check Windows event logs
eventvwr.msc
```

### macOS Issues

**Common Problems:**
- Gatekeeper blocking execution
- Permission issues with newer macOS versions

**Solutions:**

```bash
# Allow execution of unsigned binaries
sudo spctl --master-disable

# Fix permission issues
sudo xattr -rd com.apple.quarantine networth-tracker/

# Use Homebrew Python
brew install python@3.9
export PATH="/opt/homebrew/bin:$PATH"
```

### Linux Issues

**Common Problems:**
- Missing system dependencies
- SELinux restrictions
- Distribution-specific issues

**Solutions:**

```bash
# Install system dependencies
# Ubuntu/Debian
sudo apt install python3-dev libffi-dev libssl-dev

# CentOS/RHEL
sudo yum install python3-devel libffi-devel openssl-devel

# Check SELinux (if applicable)
getenforce
# If enforcing, may need to set permissive mode or create policy

# Check distribution-specific Python
which python3
python3 --version
```

## Advanced Troubleshooting

### Debug Mode

Enable debug mode for detailed error information:

```bash
# Start in debug mode
export FLASK_ENV=development  # macOS/Linux
set FLASK_ENV=development     # Windows

python scripts/start.py --env development --debug

# Or use startup scripts
./scripts/start.sh --env development --debug  # macOS/Linux
scripts\start.bat --env development --debug   # Windows

# Check debug logs
tail -f logs/networth_tracker.log  # macOS/Linux
# On Windows, use a text editor to view logs or:
type logs\networth_tracker.log
```

### Database Debugging

```bash
# Connect to database directly
sqlite3 networth.db

# Check tables
.tables

# Check schema
.schema accounts

# Check data
SELECT COUNT(*) FROM accounts;
SELECT * FROM accounts LIMIT 5;

# Check for locks
.timeout 1000
```

### Network Debugging

```bash
# Check network connectivity
netstat -an | grep :5000

# Test local connection (if curl is available)
curl -v http://127.0.0.1:5000

# Check DNS resolution
nslookup 127.0.0.1

# Test with different tools (if available)
wget http://127.0.0.1:5000  # Linux/macOS
telnet 127.0.0.1 5000       # All platforms

# Simple browser test
# Open http://127.0.0.1:5000 in your browser
```

### Log Analysis

```bash
# Search for specific errors
grep -i "error" logs/networth_tracker_errors.log  # macOS/Linux
findstr /i "error" logs\networth_tracker_errors.log  # Windows

# Check for patterns
grep -i "database" logs/networth_tracker.log | tail -20  # macOS/Linux
findstr /i "database" logs\networth_tracker.log  # Windows

# Monitor logs in real-time
tail -f logs/networth_tracker.log  # macOS/Linux
# On Windows, use a text editor or PowerShell:
Get-Content logs\networth_tracker.log -Wait  # PowerShell

# Analyze log timestamps (macOS/Linux only)
awk '{print $1, $2}' logs/networth_tracker.log | sort | uniq -c
```

### System Information Collection

For complex issues, collect system information:

**macOS/Linux:**
```bash
# Create diagnostic report
cat > diagnostic_report.txt << EOF
System Information:
$(uname -a)

Python Version:
$(python3 --version)

Disk Space:
$(df -h .)

Memory:
$(free -h 2>/dev/null || vm_stat)

Process List:
$(ps aux | grep python)

Network:
$(netstat -an | grep :5000)

Recent Errors:
$(tail -20 logs/networth_tracker_errors.log)
EOF
```

**Windows:**
```cmd
# Create diagnostic report
echo System Information: > diagnostic_report.txt
systeminfo | findstr /C:"OS Name" /C:"OS Version" >> diagnostic_report.txt
echo. >> diagnostic_report.txt
echo Python Version: >> diagnostic_report.txt
python --version >> diagnostic_report.txt
echo. >> diagnostic_report.txt
echo Disk Space: >> diagnostic_report.txt
dir >> diagnostic_report.txt
echo. >> diagnostic_report.txt
echo Process List: >> diagnostic_report.txt
tasklist | findstr python >> diagnostic_report.txt
echo. >> diagnostic_report.txt
echo Network: >> diagnostic_report.txt
netstat -an | findstr :5000 >> diagnostic_report.txt
```

## Getting Help

If you're still experiencing issues after trying these solutions:

1. **Collect Information:**
   - Error messages from logs
   - System information
   - Steps to reproduce the issue
   - Screenshots if applicable

2. **Check Documentation:**
   - [Installation Guide](installation.md)
   - [User Guide](user-guide.md)
   - [Configuration Reference](configuration.md)
   - [FAQ](faq.md)

3. **Try Workarounds:**
   - Import demo database to test functionality (see [Demo Database Guide](demo-data.md))
   - Try different browsers
   - Test on a different user account
   - Use portable installation

4. **Last Resort Options:**
   - Fresh installation
   - Restore from backup
   - Start with new database

---

**Remember:** Always backup your data before attempting major troubleshooting steps!