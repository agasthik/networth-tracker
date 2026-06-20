# Networth Tracker - Installation Guide

This guide provides step-by-step instructions for installing and setting up the Networth Tracker application on different operating systems.

## Table of Contents

- [System Requirements](#system-requirements)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
  - [Windows](#windows)
  - [macOS](#macos)
  - [Linux](#linux)
- [Configuration](#configuration)
- [First Run](#first-run)
- [Troubleshooting](#troubleshooting)

## System Requirements

### Minimum Requirements
- **Python**: 3.8 or higher
- **Operating System**: Windows 10+, macOS 10.14+, or Linux (Ubuntu 18.04+, CentOS 7+)
- **RAM**: 512 MB available memory
- **Storage**: 100 MB free disk space
- **Network**: Internet connection for stock price updates (optional)

### Recommended Requirements
- **Python**: 3.9 or higher
- **RAM**: 1 GB available memory
- **Storage**: 500 MB free disk space for data and backups

## Quick Start

For users familiar with Python development:

```bash
# Clone or download the application
git clone <repository-url> networth-tracker
cd networth-tracker

# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the application
python scripts/start.py
```

Open your browser and navigate to `http://127.0.0.1:5000`

## Detailed Installation

### Windows

#### Step 1: Install Python
1. Download Python 3.8+ from [python.org](https://www.python.org/downloads/)
2. Run the installer and **check "Add Python to PATH"**
3. Verify installation:
   ```cmd
   python --version
   ```

#### Step 2: Download Application
1. Download the Networth Tracker application files
2. Extract to a folder (e.g., `C:\networth-tracker`)

#### Step 3: Set Up Environment
1. Open Command Prompt as Administrator
2. Navigate to the application folder:
   ```cmd
   cd C:\networth-tracker
   ```
3. Create virtual environment:
   ```cmd
   python -m venv venv
   ```
4. Activate virtual environment:
   ```cmd
   venv\Scripts\activate
   ```
5. Install dependencies:
   ```cmd
   pip install -r requirements.txt
   ```

#### Step 4: Start Application
```cmd
scripts\start.bat
```

### macOS

#### Step 1: Install Python
1. Install Homebrew (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```
2. Install Python:
   ```bash
   brew install python@3.9
   ```
3. Verify installation:
   ```bash
   python3 --version
   ```

#### Step 2: Download Application
1. Download the Networth Tracker application files
2. Extract to a folder (e.g., `~/networth-tracker`)

#### Step 3: Set Up Environment
1. Open Terminal
2. Navigate to the application folder:
   ```bash
   cd ~/networth-tracker
   ```
3. Create virtual environment:
   ```bash
   python3 -m venv venv
   ```
4. Activate virtual environment:
   ```bash
   source venv/bin/activate
   ```
5. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Step 4: Set Permissions and Start
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

### Linux

#### Step 1: Install Python
**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv
```

**CentOS/RHEL/Fedora:**
```bash
sudo yum install python3 python3-pip
# or for newer versions:
sudo dnf install python3 python3-pip
```

#### Step 2: Download Application
1. Download the Networth Tracker application files
2. Extract to a folder (e.g., `~/networth-tracker`)

#### Step 3: Set Up Environment
```bash
cd ~/networth-tracker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Step 4: Set Permissions and Start
```bash
chmod +x scripts/start.sh
./scripts/start.sh
```

## Configuration

### Environment Configuration

The application supports three environments:

1. **Production** (default): Optimized for regular use
2. **Development**: Enhanced logging and debugging
3. **Testing**: For running tests

Set the environment using:
```bash
# Windows
set FLASK_ENV=development
scripts\start.bat

# macOS/Linux
export FLASK_ENV=development
./scripts/start.sh
```

### Configuration Files

The application uses environment variables for configuration. Create a `.env` file in the project root for custom settings:

```bash
# Database settings
DATABASE_PATH=networth.db

# Logging settings
LOG_LEVEL=INFO
LOG_DIR=logs
MAX_LOG_SIZE=10485760

# Security settings
SECRET_KEY=your-secret-key-here

# Stock API settings
STOCK_API_RATE_LIMIT=1.0
STOCK_API_TIMEOUT=30
```

### Advanced Configuration

For advanced users, modify `config.py` to customize:
- Session timeout
- File permissions
- Backup settings
- Logging configuration

## First Run

### Initial Setup

1. Start the application using the appropriate startup script
2. Open your browser and navigate to `http://127.0.0.1:5000`
3. You'll be prompted to set up a master password
4. Choose a strong password (minimum 12 characters)
5. Complete the setup and log in

### Demo Database

To explore the application with sample data:

1. Generate or download a demo database (see [Demo Database Guide](demo-data.md))
2. Use the Import functionality to load the demo database
3. Explore all features with realistic synthetic financial data
4. Remove demo accounts when ready to use real data

### Adding Your First Account

1. From the dashboard, click "Add Account"
2. Choose an account type (CD, Savings, 401k, Trading, I-bonds)
3. Fill in the required information
4. Save the account

## Troubleshooting

### Common Issues

#### Python Not Found
**Error**: `'python' is not recognized as an internal or external command`

**Solution**:
- Ensure Python is installed and added to PATH
- Try using `python3` instead of `python`

#### Permission Denied (macOS/Linux)
**Error**: `Permission denied` when running scripts

**Solution**:
```bash
chmod +x scripts/start.sh
chmod +x scripts/init_db.py
```

#### Port Already in Use
**Error**: `Address already in use`

**Solution**:
- Check if another instance is running
- Use a different port: `./scripts/start.sh --port 5001`
- Stop the existing process

#### Database Locked
**Error**: `database is locked`

**Solution**:
- Ensure no other instances are running
- Check file permissions
- Restart the application

#### Virtual Environment Issues
**Error**: Problems with virtual environment

**Solution**:
```bash
# Remove existing virtual environment
rm -rf venv  # macOS/Linux
rmdir /s venv  # Windows

# Create new virtual environment
python3 -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate  # Windows

# Reinstall dependencies
pip install -r requirements.txt
```

### Getting Help

1. **Check Logs**: Look in the `logs/` directory for error messages
2. **Validate Configuration**: Run `./scripts/start.sh --validate`
3. **Database Issues**: Use `python scripts/init_db.py --verify`
4. **File Permissions**: Ensure proper permissions are set

### Log Files

The application creates log files in the `logs/` directory:
- `networth_tracker.log`: General application logs
- `networth_tracker_errors.log`: Error-specific logs

### Support

For additional support:
1. Check the log files for detailed error messages
2. Verify your system meets the minimum requirements
3. Ensure all dependencies are properly installed
4. Try running in development mode for more detailed logging

## Security Notes

- The application stores all data locally on your machine
- Database files are encrypted with your master password
- No financial data is transmitted to external servers (except stock symbols for price updates)
- Ensure your master password is strong and memorable
- Regular backups are recommended (use the export feature)

## Next Steps

After successful installation:
1. Read the [User Guide](user-guide.md) for detailed usage instructions
2. Set up regular backups using the export feature
3. Use the [Demo Database Guide](demo-data.md) to explore features with sample data
4. Consider setting up the application to start automatically on system boot