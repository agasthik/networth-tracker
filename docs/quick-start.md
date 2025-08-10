# Quick Start Guide

Get up and running with Networth Tracker in under 5 minutes.

## Prerequisites

- Python 3.8 or higher
- 100 MB free disk space
- Internet connection (for stock price updates)

## Installation

### 1. Download and Extract
Download the Networth Tracker application and extract it to your desired location.

### 2. Set Up Environment
```bash
# Navigate to the application directory
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
```

### 3. Start the Application
```bash
# On Windows:
scripts\start.bat

# On macOS/Linux:
./scripts/start.sh

# Or directly with Python:
python scripts/start.py
```

### 4. Access the Application
Open your web browser and go to: `http://127.0.0.1:5000`

## First Time Setup

1. **Set Master Password**: Choose a strong password (minimum 12 characters)
2. **Login**: Use your master password to access the application
3. **Explore with Demo Data**: Import the demo database to explore with sample data (see [Demo Database Guide](demo-data.md))

## Add Your First Account

1. From the dashboard, click **"Add Account"**
2. Choose an account type (CD, Savings, 401k, Trading, I-bonds)
3. Fill in the required information
4. Click **"Save"**

## Quick Tips

- **Demo Database**: Perfect for exploring features without real data (see [Demo Database Guide](demo-data.md))
- **Backup**: Use the export feature to create regular backups
- **Security**: All data is stored locally and encrypted
- **Stock Updates**: Trading account stock prices update automatically

## Next Steps

- Read the [User Guide](user-guide.md) for detailed feature explanations
- Check the [Installation Guide](installation.md) for advanced setup options
- Review the [Security Guide](security.md) for best practices

## Need Help?

- Check the [FAQ](faq.md) for common questions
- Review the [Troubleshooting](troubleshooting.md) guide
- Look at the log files in the `logs/` directory for error details

---

**Estimated Setup Time**: 5 minutes
**Difficulty Level**: Beginner