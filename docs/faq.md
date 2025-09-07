# Frequently Asked Questions (FAQ)

Common questions and answers about the Networth Tracker application.

## Table of Contents

- [General Questions](#general-questions)
- [Installation and Setup](#installation-and-setup)
- [Security and Privacy](#security-and-privacy)
- [Features and Functionality](#features-and-functionality)
- [Troubleshooting](#troubleshooting)
- [Data Management](#data-management)
- [Technical Questions](#technical-questions)

## General Questions

### What is Networth Tracker?

Networth Tracker is a secure, local financial portfolio management application that helps you track your investments across multiple account types including CDs, savings accounts, 401k accounts, trading accounts, and I-bonds. All data is stored locally on your machine with encryption for maximum privacy.

### Why choose Networth Tracker over online alternatives?

**Privacy and Security:**
- All data stored locally on your machine
- No cloud synchronization or external data transmission
- Military-grade encryption protects your financial information
- No third-party access to your sensitive data

**Offline Functionality:**
- Works completely offline (except for stock price updates)
- No internet dependency for core functionality
- Your data is always accessible

**Cost:**
- Free to use with no subscription fees
- No premium features locked behind paywalls
- Complete functionality available to all users

### What types of accounts can I track?

- **Certificate of Deposit (CD)**: Principal, interest rate, maturity date
- **Savings Accounts**: Current balance, interest rate
- **401k Retirement Accounts**: Balance, employer match, contributions
- **Trading Accounts**: Stock positions, cash balance, multiple brokers
- **I-bonds**: Purchase amount, fixed rate, inflation adjustments

### Is my financial data safe?

Yes, your data is extremely secure:
- **Local Storage**: Data never leaves your computer
- **Encryption**: All financial data encrypted with AES-256
- **Master Password**: Only you have access to your data
- **No Cloud**: No external servers or cloud storage
- **Open Source**: Code can be audited for security

## Installation and Setup

### What are the system requirements?

**Minimum Requirements:**
- Python 3.8 or higher
- 512 MB RAM
- 100 MB free disk space
- Any modern operating system (Windows, macOS, Linux)

**Recommended:**
- Python 3.9 or higher
- 1 GB RAM
- 500 MB free disk space
- SSD storage for better performance

### How do I install Python?

**Windows:**
1. Visit [python.org](https://www.python.org/downloads/)
2. Download Python 3.9 or higher
3. Run installer and check "Add Python to PATH"

**macOS:**
```bash
# Using Homebrew (recommended)
brew install python@3.9

# Or download from python.org
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL/Fedora
sudo yum install python3 python3-pip
```

### Can I install it on a USB drive?

Yes! The application supports portable installation:
1. Copy all files to your USB drive
2. Create virtual environment on the USB drive
3. Use the portable launcher scripts
4. All data and settings travel with the USB drive

### Do I need administrator privileges?

**For regular installation:** No, you can install in your user directory

**For system-wide installation:** Yes, administrator privileges are needed

**For portable installation:** No privileges required

## Security and Privacy

### How secure is my master password?

Your master password is extremely secure:
- **Never stored**: Password is never saved anywhere
- **Key derivation**: Used only to derive encryption keys
- **PBKDF2**: 100,000 iterations make brute force attacks impractical
- **Salt protection**: Unique salt prevents rainbow table attacks

### What happens if I forget my master password?

**Unfortunately, there is no password recovery mechanism.** This is by design for maximum security:
- No password hints or recovery questions
- No backdoor access methods
- Your data becomes permanently inaccessible

**Prevention strategies:**
- Use a memorable but strong password
- Consider using a password manager
- Create regular encrypted backups
- Write down the password and store it securely

### Can anyone else access my data?

No, your data is protected by multiple security layers:
- **Encryption**: All data encrypted with your master password
- **File permissions**: Database files accessible only to your user account
- **Local-only**: Application runs on localhost only
- **No network access**: No external access to your computer

### What data is sent to external services?

**Only stock symbols** are sent to external APIs for price updates:
- **Sent**: Stock symbols like "AAPL", "GOOGL"
- **NOT sent**: Quantities, purchase prices, account values, personal information

**No other data** leaves your computer.

## Features and Functionality

### How do I add my first account?

1. Start the application and log in
2. Click "Add Account" from the dashboard
3. Choose your account type (CD, Savings, 401k, Trading, I-bonds)
4. Fill in the required information
5. Click "Save"

### Can I track multiple brokers?

Yes! The trading account feature supports multiple brokers:
- Add separate trading accounts for each broker
- Track positions across all brokers
- View consolidated portfolio performance
- Maintain separate cash balances per broker

### How often are stock prices updated?

- **Automatic updates**: When you view trading accounts
- **Manual updates**: Click "Refresh Prices" button
- **Rate limiting**: Respects API limits (1 request per second)
- **Offline mode**: Last known prices displayed when offline

### Can I export my data?

Yes, comprehensive export functionality is available:
- **Full export**: All accounts and historical data
- **Selective export**: Choose specific account types or date ranges
- **Encrypted backups**: Export files are encrypted
- **Multiple formats**: JSON format for data portability

### Does it support multiple currencies?

Currently, the application assumes a single base currency. All values should be entered in your preferred currency (USD, EUR, etc.). Currency conversion is not automatically handled.

## Troubleshooting

### The application won't start

**Check Python installation:**
```bash
python3 --version
# Should show Python 3.8 or higher
```

**Check virtual environment:**
```bash
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
pip list  # Should show installed packages
```

**Check for port conflicts:**
```bash
# Try a different port
./venv/bin/python scripts/start.py --port 5001
# Or use the startup scripts
./scripts/start.sh --port 5001  # macOS/Linux
scripts\start.bat --port 5001   # Windows
```

### I get "Permission Denied" errors

**On macOS/Linux:**
```bash
# Make scripts executable
chmod +x scripts/*.sh scripts/*.py

# Check file permissions
ls -la *.db
# Should show -rw------- (600 permissions)
```

**On Windows:**
- Run Command Prompt as Administrator
- Check antivirus software isn't blocking files

### Stock prices aren't updating

**Check internet connection:**
- Ensure you have internet access
- Try accessing a website in your browser

**Check API limits:**
- Wait a few minutes and try again
- The application respects rate limits

**Manual refresh:**
- Click the "Refresh Prices" button
- Check the logs for error messages

### The database is locked

**Stop all instances:**
```bash
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows
```

**Check for zombie processes:**
```bash
# macOS/Linux
ps aux | grep python
kill <process_id>  # If found

# Windows
tasklist | findstr python
taskkill /PID <process_id>  # If found
```

### I can't access the application in my browser

**Check the application is running:**
```bash
./scripts/start.sh --status  # macOS/Linux
scripts\start.bat --status   # Windows
```

**Try different browsers:**
- Chrome, Firefox, Safari, Edge all supported
- Try incognito/private mode

**Check the URL:**
- Should be `http://127.0.0.1:5000`
- Not `https://` (no SSL for localhost)
- Check the port number in the startup messages

## Data Management

### How do I backup my data?

**Using the export feature:**
1. Log into the application
2. Go to "Export Data"
3. Choose "Full Export"
4. Save the encrypted backup file securely

**Manual backup:**
```bash
# Copy database files
cp networth.db networth_backup_$(date +%Y%m%d).db
```

### How do I restore from a backup?

**Using the import feature:**
1. Log into the application
2. Go to "Import Data"
3. Select your backup file
4. Enter your master password
5. Confirm the import

**Manual restore:**
```bash
# Stop the application
./scripts/start.sh --stop  # macOS/Linux
scripts\start.bat --stop   # Windows

# Replace database file
cp networth_backup_20250109.db networth.db

# Start the application
./scripts/start.sh  # macOS/Linux
scripts\start.bat   # Windows
```

### Can I migrate to a different computer?

Yes, migration is straightforward:

**Method 1: Export/Import**
1. Export data from old computer
2. Install application on new computer
3. Import data using the backup file

**Method 2: File Copy**
1. Copy the entire application directory
2. Ensure Python and dependencies are installed
3. Start the application

### How much disk space does it use?

**Application size:** ~50 MB (including Python dependencies)
**Database size:** Varies by usage:
- Small portfolio (10 accounts): ~1 MB
- Medium portfolio (50 accounts): ~5 MB
- Large portfolio (100+ accounts): ~10-20 MB
- Historical data adds ~1 MB per year of tracking

## Technical Questions

### What technology is it built with?

**Backend:**
- Python 3.8+ with Flask web framework
- SQLite database with encryption
- Cryptography library for security

**Frontend:**
- HTML5, CSS3, JavaScript
- Bootstrap for responsive design
- No external JavaScript dependencies

### Can I run it on a server?

The application is designed for local use only:
- **Security**: Binding to localhost only
- **Privacy**: No multi-user support
- **Architecture**: Single-user design

For server deployment, significant security modifications would be required.

### Is the source code available?

The application is designed with transparency in mind. All source code is included with the application and can be reviewed for security auditing purposes.

### Can I contribute to development?

The application is designed to be maintainable and extensible. Check the main documentation for information about the codebase structure and development practices.

### What Python packages does it use?

Key dependencies include:
- **Flask**: Web framework
- **SQLite3**: Database (built into Python)
- **Cryptography**: Encryption and security
- **yfinance**: Stock price data
- **Requests**: HTTP client for APIs

See `requirements.txt` for the complete list with specific versions.

### How do I update to a new version?

**For regular installations:**
1. **Backup first**: Export your data using the application's export feature
2. Download the new version
3. Replace application files (keep your database files)
4. Update dependencies: `pip install -r requirements.txt`
5. Run database migrations if needed: `./venv/bin/python scripts/init_db.py --migrate`
6. Test the application with your existing data

**For portable installations:**
1. **Backup first**: Copy your entire portable directory
2. Replace application files (keep data, logs, and backups directories)
3. Update dependencies in the virtual environment
4. Test the application

---

## Still Have Questions?

If your question isn't answered here:

1. **Check the logs**: Look in the `logs/` directory for error messages
2. **Review documentation**: Check the [User Guide](user-guide.md) and [Installation Guide](installation.md)
3. **Try demo database**: Import demo database to test functionality (see [Demo Database Guide](demo-data.md))
4. **Validate configuration**: Run `./venv/bin/python scripts/start.py --validate-only`

**Common log locations:**
- `logs/networth_tracker.log`: General application logs
- `logs/networth_tracker_errors.log`: Error-specific logs

**Useful commands:**
```bash
# Check application status
./scripts/start.sh --status  # macOS/Linux
scripts\start.bat --status   # Windows

# Validate configuration
./venv/bin/python scripts/start.py --validate-only
# Or use startup scripts
./scripts/start.sh --validate  # macOS/Linux
scripts\start.bat --validate   # Windows

# Verify database
./venv/bin/python scripts/init_db.py --verify

# View recent logs
tail -20 logs/networth_tracker.log  # macOS/Linux
type logs\networth_tracker.log | more  # Windows
```