# Security Guide

Comprehensive security guide for the Networth Tracker application, covering data protection, privacy, and security best practices.

## Table of Contents

- [Security Overview](#security-overview)
- [Data Encryption](#data-encryption)
- [Authentication and Access Control](#authentication-and-access-control)
- [File System Security](#file-system-security)
- [Network Security](#network-security)
- [Privacy Protection](#privacy-protection)
- [Security Best Practices](#security-best-practices)
- [Threat Model](#threat-model)
- [Security Monitoring](#security-monitoring)

## Security Overview

The Networth Tracker is designed with a **security-first, privacy-first** approach:

### Core Security Principles

1. **Local-First**: All data stored locally, no cloud dependencies
2. **Encryption at Rest**: All sensitive data encrypted in the database
3. **Zero-Knowledge**: No external services have access to financial data
4. **Minimal Attack Surface**: Localhost-only operation
5. **Defense in Depth**: Multiple layers of security controls

### Security Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Browser Interface                        │
├─────────────────────────────────────────────────────────────┤
│                  Flask Application                          │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Authentication │  │   Session Mgmt  │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│                  Encryption Layer                           │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  Data Encryption│  │  Key Management │                  │
│  └─────────────────┘  └─────────────────┘                  │
├─────────────────────────────────────────────────────────────┤
│                 Encrypted SQLite Database                   │
├─────────────────────────────────────────────────────────────┤
│                  File System Security                       │
│  ┌─────────────────┐  ┌─────────────────┐                  │
│  │  File Permissions│  │  Access Control │                  │
│  └─────────────────┘  └─────────────────┘                  │
└─────────────────────────────────────────────────────────────┘
```

## Data Encryption

### Encryption at Rest

All sensitive financial data is encrypted before storage using industry-standard encryption:

#### Encryption Algorithm
- **Algorithm**: Fernet (AES-128 in CBC mode with HMAC-SHA256)
- **Key Derivation**: PBKDF2 with SHA-256
- **Iterations**: 100,000 (configurable)
- **Salt**: 16-byte random salt per database

#### Implementation Details

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

class EncryptionService:
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """Derive encryption key from master password."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,  # OWASP recommended minimum
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key
```

#### What Gets Encrypted

- **Account Information**: Names, institutions, balances, values
- **Stock Positions**: Symbols, shares, prices, purchase dates
- **Historical Data**: All historical snapshots and performance data
- **Configuration Data**: Sensitive application settings

#### What Doesn't Get Encrypted

- **Database Schema**: Table structures and indexes
- **Application Logs**: System logs (no financial data included)
- **Stock Symbols**: Only symbols sent to APIs (no quantities or values)

### Key Management

#### Master Password
- **Purpose**: Derives the database encryption key
- **Requirements**: Minimum 12 characters, complexity recommended
- **Storage**: Never stored in plaintext, only used for key derivation
- **Recovery**: No password recovery mechanism (by design for security)

#### Key Derivation Process
1. User enters master password
2. Random salt retrieved from database
3. PBKDF2 derives encryption key (100,000 iterations)
4. Key used to encrypt/decrypt data
5. Key cleared from memory after use

#### Security Considerations
- **Memory Protection**: Keys cleared from memory after use
- **No Key Storage**: Encryption keys never stored on disk
- **Salt Uniqueness**: Each database has a unique random salt
- **Iteration Count**: Configurable, minimum 100,000 iterations

## Authentication and Access Control

### Master Password Authentication

#### Password Requirements
```python
# Configurable password policy
MIN_PASSWORD_LENGTH = 12
REQUIRE_UPPERCASE = True
REQUIRE_LOWERCASE = True
REQUIRE_NUMBERS = True
REQUIRE_SPECIAL_CHARS = False  # Optional but recommended
```

#### Password Validation
- **Length**: Minimum 12 characters (configurable)
- **Complexity**: Mixed case, numbers recommended
- **Common Passwords**: Checked against common password lists
- **Strength Meter**: Visual feedback during setup

#### Authentication Flow
1. User enters master password
2. Password hashed and compared with stored hash
3. If valid, encryption key derived for session
4. Session established with timeout
5. Automatic logout after inactivity

### Session Management

#### Session Security
```python
# Flask session configuration
SESSION_COOKIE_SECURE = False      # HTTP for localhost
SESSION_COOKIE_HTTPONLY = True     # No JavaScript access
SESSION_COOKIE_SAMESITE = 'Lax'    # CSRF protection
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)  # Auto-logout
```

#### Session Features
- **Automatic Timeout**: Configurable inactivity timeout
- **Secure Cookies**: HTTPOnly and SameSite protection
- **Session Invalidation**: Logout clears all session data
- **Concurrent Sessions**: Only one active session per instance

## File System Security

### File Permissions

#### Unix/Linux/macOS Permissions
```bash
# Database files (owner read/write only)
chmod 600 *.db

# Log files (owner read/write, others read)
chmod 644 logs/*.log

# Backup files (owner read/write only)
chmod 600 backups/*

# Configuration files (owner read/write only)
chmod 600 .env*

# Application directory (owner full access)
chmod 750 /opt/networth-tracker
```

#### Windows Security
```cmd
# Remove inheritance and set explicit permissions
icacls "networth-tracker" /inheritance:r
icacls "networth-tracker" /grant:r "%USERNAME%:(OI)(CI)F"

# Restrict database file access
icacls "*.db" /grant:r "%USERNAME%:F"
```

### Directory Structure Security

```
networth-tracker/
├── data/           # 700 - Database files (owner only)
├── logs/           # 755 - Log files (readable by others)
├── backups/        # 700 - Backup files (owner only)
├── temp/           # 700 - Temporary files (owner only)
└── config/         # 700 - Configuration files (owner only)
```

### Automatic Permission Setting

The application automatically sets secure permissions on startup:

```python
def set_secure_permissions():
    """Set secure file permissions on startup."""
    if os.name != 'nt':  # Unix-like systems
        # Database files
        for db_file in glob.glob('*.db'):
            os.chmod(db_file, 0o600)

        # Backup files
        for backup_file in glob.glob('backups/*'):
            os.chmod(backup_file, 0o600)

        # Configuration files
        for config_file in glob.glob('.env*'):
            os.chmod(config_file, 0o600)
```

## Network Security

### Localhost-Only Operation

#### Binding Configuration
- **Host**: 127.0.0.1 (localhost only)
- **Port**: 5000 (configurable)
- **External Access**: Explicitly disabled
- **Firewall**: No inbound rules required

#### Network Isolation
```python
# Flask application binding
app.run(
    host='127.0.0.1',  # Localhost only
    port=5000,
    debug=False
)
```

### External API Security

#### Stock Price API
- **Data Sent**: Only stock symbols (e.g., "AAPL", "GOOGL")
- **Data NOT Sent**: No quantities, values, or personal information
- **Rate Limiting**: Respects API rate limits
- **Timeout**: Configurable request timeouts
- **Error Handling**: Graceful degradation if API unavailable

#### API Security Measures
```python
class StockPriceService:
    def get_stock_price(self, symbol: str) -> float:
        """Get stock price - only symbol is transmitted."""
        # Validate symbol format (letters only)
        if not re.match(r'^[A-Z]{1,5}$', symbol):
            raise ValueError("Invalid stock symbol")

        # Make API request with timeout
        response = requests.get(
            f"https://api.example.com/quote/{symbol}",
            timeout=30,
            headers={'User-Agent': 'NetworthTracker/1.0'}
        )

        # No financial data in request or logs
        return response.json()['price']
```

## Privacy Protection

### Data Minimization

#### What We Collect
- **Financial Data**: Only what you enter for tracking
- **Usage Data**: None (no analytics or telemetry)
- **Personal Data**: None (no names, addresses, SSNs)
- **System Data**: Only local logs for debugging

#### What We Don't Collect
- **Browsing History**: No tracking of web activity
- **Location Data**: No GPS or location tracking
- **Device Information**: No device fingerprinting
- **Network Data**: No network traffic analysis

### Local-First Architecture

#### Data Storage
- **Location**: Local machine only
- **Cloud Sync**: None (by design)
- **Backups**: User-controlled local backups only
- **Sharing**: No automatic sharing or synchronization

#### Privacy Benefits
- **No Cloud Exposure**: Data never leaves your machine
- **No Third-Party Access**: No external services access your data
- **User Control**: Complete control over your data
- **Offline Operation**: Full functionality without internet

### Data Anonymization

#### Demo Database
- **Synthetic Data**: Realistic but fake financial data
- **No Real Information**: No actual financial institutions or accounts
- **Safe Exploration**: Learn features without privacy risk
- **Importable Data**: Can be imported through standard import functionality

## Security Best Practices

### For Users

#### Password Security
1. **Strong Master Password**: Use a unique, complex password
2. **Password Manager**: Consider using a password manager
3. **Regular Changes**: Change password if compromised
4. **No Sharing**: Never share your master password

#### System Security
1. **Keep Updated**: Update operating system and Python
2. **Antivirus**: Use reputable antivirus software
3. **Firewall**: Enable system firewall
4. **Physical Security**: Secure physical access to computer

#### Data Protection
1. **Regular Backups**: Export data regularly
2. **Secure Storage**: Store backups in secure locations
3. **Multiple Copies**: Keep backups in multiple locations
4. **Test Restores**: Periodically test backup restoration

### For Administrators

#### Deployment Security
1. **Secure Installation**: Follow deployment security guidelines
2. **File Permissions**: Verify correct file permissions
3. **Network Isolation**: Ensure localhost-only binding
4. **Process Security**: Run with minimal privileges

#### Monitoring
1. **Log Monitoring**: Monitor application logs for issues
2. **File Integrity**: Monitor database file integrity
3. **Access Monitoring**: Monitor file access patterns
4. **Performance Monitoring**: Monitor for unusual activity

## Threat Model

### Threats Addressed

#### Local Threats
- **Physical Access**: Database encryption protects against unauthorized access
- **Malware**: File permissions and encryption provide protection
- **Data Theft**: Encrypted storage prevents data extraction
- **Privilege Escalation**: Minimal privileges and sandboxing

#### Network Threats
- **Man-in-the-Middle**: Localhost-only operation eliminates network exposure
- **Eavesdropping**: No sensitive data transmitted over network
- **Remote Access**: No remote access capabilities
- **API Attacks**: Only stock symbols transmitted to external APIs

### Threats Not Addressed

#### Advanced Persistent Threats
- **Sophisticated Malware**: Advanced malware with keyloggers
- **State-Level Actors**: Nation-state level attacks
- **Hardware Attacks**: Physical hardware tampering
- **Social Engineering**: Attacks targeting the user directly

#### Mitigation Strategies
- **Defense in Depth**: Multiple security layers
- **User Education**: Security awareness training
- **Regular Updates**: Keep system and application updated
- **Monitoring**: Implement security monitoring

## Security Monitoring

### Log Analysis

#### Security-Relevant Events
```python
# Authentication events
logger.info(f"Login attempt from {request.remote_addr}")
logger.warning(f"Failed login attempt: {failed_attempts}")
logger.info(f"User logged out: session_duration={duration}")

# Data access events
logger.info(f"Database accessed: operation={operation}")
logger.warning(f"Database error: {error_message}")

# File system events
logger.info(f"File permissions set: {file_path}")
logger.warning(f"Permission denied: {file_path}")
```

#### Log Monitoring Script
```bash
#!/bin/bash
# Monitor security events in logs

# Check for failed login attempts
grep "Failed login" logs/networth_tracker.log | tail -10

# Check for permission errors
grep "Permission denied" logs/networth_tracker_errors.log

# Check for database errors
grep "Database error" logs/networth_tracker_errors.log
```

### Security Validation

#### Automated Security Checks
```python
def security_audit():
    """Perform automated security audit."""
    issues = []

    # Check file permissions
    for db_file in glob.glob('*.db'):
        if oct(os.stat(db_file).st_mode)[-3:] != '600':
            issues.append(f"Insecure database permissions: {db_file}")

    # Check for weak passwords (if configurable)
    if len(config.SECRET_KEY) < 32:
        issues.append("Weak secret key detected")

    # Check for outdated dependencies
    # Implementation depends on requirements

    return issues
```

### Incident Response

#### Security Incident Procedures
1. **Immediate Response**: Stop application if compromise suspected
2. **Assessment**: Determine scope and impact of incident
3. **Containment**: Isolate affected systems
4. **Recovery**: Restore from clean backups if necessary
5. **Lessons Learned**: Update security measures

#### Recovery Procedures
```bash
# Emergency shutdown
./scripts/start.sh --stop

# Backup current state
./venv/bin/python scripts/init_db.py --backup

# Restore from clean backup
./venv/bin/python scripts/init_db.py --restore backup_file.db

# Verify integrity
./venv/bin/python scripts/init_db.py --verify

# Restart with enhanced monitoring
./scripts/start.sh --env production
```

## Security Compliance

### Standards Alignment

#### OWASP Guidelines
- **A01 - Broken Access Control**: Strong authentication and session management
- **A02 - Cryptographic Failures**: Industry-standard encryption
- **A03 - Injection**: Parameterized queries and input validation
- **A04 - Insecure Design**: Security-first architecture
- **A05 - Security Misconfiguration**: Secure defaults and configuration

#### Privacy Regulations
- **GDPR Compliance**: Local storage, user control, data minimization
- **CCPA Compliance**: No data collection or sharing
- **PIPEDA Compliance**: Privacy by design principles

### Security Documentation

This security guide should be reviewed and updated regularly to address:
- New threats and vulnerabilities
- Changes in security best practices
- Updates to encryption standards
- Regulatory requirement changes

---

**Security Review Date**: 2025-01-09
**Next Review Due**: 2025-07-09
**Security Contact**: See main documentation for support