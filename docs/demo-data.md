# Demo Database Guide

This guide explains how to use the demo database to explore the Networth Tracker application with realistic sample data.

## Overview

The demo database is a pre-generated SQLite database containing synthetic financial data that demonstrates all features of the Networth Tracker application. It includes various account types with realistic values and 24 months of historical data.

## What's Included

The demo database contains:

### Account Types
- **3 Certificate of Deposit (CD) accounts** with varying terms and interest rates
- **2 Savings accounts** from different institutions with realistic balances
- **1 401k retirement account** with employer matching and contribution history
- **2 Trading accounts** with diverse stock positions and real-time price tracking
- **2 I-bonds accounts** with different purchase dates and inflation adjustments

### Historical Data
- **24 months** of historical performance data
- **Monthly snapshots** showing account growth over time
- **Account-specific volatility patterns** that reflect realistic market behavior
- **Growth trajectories** appropriate for each account type

### Sample Data Characteristics
- **Realistic institutions**: Chase Bank, Ally Bank, Fidelity, Vanguard, etc.
- **Diverse stock positions**: Mix of large-cap, mid-cap, and sector ETFs
- **Appropriate values**: Account balances ranging from $5,000 to $75,000
- **Current market data**: Stock positions with realistic symbols and quantities

## Getting the Demo Database

### Option 1: Generate Demo Database
If you have the application installed, you can generate a fresh demo database:

```bash
# Navigate to your networth-tracker directory
cd networth-tracker

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Generate demo database
./venv/bin/python scripts/generate_demo_database.py
```

This creates a file called `demo_networth.db` in your project directory.

### Option 2: Download Pre-generated Database
If available, you can download a pre-generated demo database file and place it in your networth-tracker directory.

## Importing Demo Data

### Step 1: Start the Application
```bash
# Start the networth tracker
./scripts/start.sh  # macOS/Linux
# or
scripts\start.bat   # Windows

# Or manually
./venv/bin/python scripts/start.py
```

### Step 2: Access Import Functionality
1. Open your browser to `http://127.0.0.1:5000`
2. Log in with your master password
3. Navigate to **Settings** → **Import/Export**
4. Click **Import Data**

### Step 3: Import Demo Database
1. Click **Choose File** and select `demo_networth.db`
2. Choose import options:
   - **Merge with existing data**: Adds demo accounts to your current data
   - **Replace all data**: Replaces your data with demo data (use with caution)
3. Click **Import Database**
4. Wait for the import to complete

### Step 4: Verify Import
After import, you should see:
- Demo accounts marked with a **"DEMO"** badge in the account list
- Historical data spanning 24 months
- Realistic account balances and stock positions
- All account types represented

## Using Demo Data

### Exploring Features
With demo data imported, you can:

1. **View Dashboard**: See portfolio overview with realistic data
2. **Account Management**: Edit, update, and manage demo accounts
3. **Historical Analysis**: Review 24 months of performance data
4. **Stock Tracking**: See real-time prices for demo stock positions
5. **Export/Import**: Practice backup and restore procedures

### Demo Account Identification
Demo accounts are clearly marked:
- **Dashboard**: Demo accounts show a "DEMO" badge
- **Account Lists**: Demo indicator appears next to account names
- **Account Details**: Demo status is displayed in account information

### Safe Experimentation
Demo data allows you to:
- Test all application features without risk
- Learn the interface with realistic data
- Practice account management workflows
- Understand reporting and analysis features

## Managing Demo Data

### Filtering Demo Accounts
You can filter your account views to:
- **Show only real accounts**: Hide demo data from main views
- **Show only demo accounts**: Focus on demo data for testing
- **Show all accounts**: View real and demo data together

### Removing Demo Data
When you're ready to remove demo data:

1. Navigate to **Settings** → **Account Management**
2. Click **Manage Demo Data**
3. Select **Delete All Demo Accounts**
4. Confirm the deletion

This removes all demo accounts while preserving your real financial data.

### Refreshing Demo Data
To get fresh demo data:
1. Delete existing demo accounts (see above)
2. Generate a new demo database
3. Import the new demo database

## Best Practices

### Learning Workflow
1. **Start with demo data**: Import demo database before adding real accounts
2. **Explore thoroughly**: Test all features with demo data first
3. **Practice workflows**: Use demo data to learn account management
4. **Clean up**: Remove demo data before adding real financial information

### Data Safety
- **Backup first**: Always backup your real data before importing demo data
- **Use merge option**: Choose "merge" instead of "replace" to preserve real data
- **Verify import**: Check that demo accounts are properly marked
- **Regular cleanup**: Remove demo data periodically to avoid confusion

### Testing Scenarios
Use demo data to test:
- **Account creation and editing**
- **Historical data analysis**
- **Export and import procedures**
- **Stock price updates**
- **Portfolio performance calculations**

## Troubleshooting

### Import Issues
If demo database import fails:
1. **Check file format**: Ensure you're importing a valid SQLite database
2. **Verify file size**: Demo database should be 2-5 MB
3. **Check permissions**: Ensure the application can read the demo database file
4. **Review logs**: Check `logs/networth_tracker.log` for error details

### Demo Account Issues
If demo accounts don't appear correctly:
1. **Refresh the page**: Sometimes a browser refresh is needed
2. **Check account filters**: Ensure demo accounts aren't filtered out
3. **Verify import**: Confirm the import completed successfully
4. **Check database**: Verify demo accounts exist in the database

### Performance Considerations
- **Large datasets**: Demo data includes 24 months of history, which may slow some operations
- **Stock updates**: Demo stock positions will fetch real-time prices
- **Database size**: Demo data increases your database size by 2-3 MB

## Technical Details

### Database Structure
Demo accounts include:
- **is_demo flag**: Boolean field marking accounts as demo data
- **Realistic IDs**: Account numbers and institution codes
- **Historical snapshots**: Monthly performance data
- **Stock positions**: Realistic ticker symbols and quantities

### Data Generation
Demo data is generated using:
- **Algorithmic patterns**: Realistic growth and volatility patterns
- **Market data**: Current stock symbols and realistic prices
- **Institution data**: Real bank and brokerage names
- **Compliance**: No real account numbers or personal information

### Security
Demo data maintains the same security as real data:
- **Encryption**: Demo accounts are encrypted with your master password
- **Access control**: Same authentication required
- **Local storage**: Demo data stays on your local machine

---

**Note**: Demo data is for exploration and testing purposes only. It contains no real financial information and should not be used for actual financial planning or decision-making.