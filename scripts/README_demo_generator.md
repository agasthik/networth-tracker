# Demo Database Generator

This script creates a standalone demo database with comprehensive synthetic financial data for the networth tracker application.

## Usage

```bash
# Create demo database with default settings
./venv/bin/python scripts/generate_demo_database.py

# Create demo database with custom path
./venv/bin/python scripts/generate_demo_database.py custom_demo.db

# Create demo database with custom path and password
./venv/bin/python scripts/generate_demo_database.py custom_demo.db mypassword
```

## Generated Data

The script creates a complete demo database with:

### Accounts (10 total)
- **3 CD Accounts**: Various terms (6-60 months) with realistic interest rates (1.5-4.5%)
- **2 Savings Accounts**: High-yield savings with competitive rates (0.1-2.5%)
- **1 401k Account**: Retirement account with employer matching and contribution limits
- **2 Trading Accounts**: Brokerage accounts with diverse stock positions (3-8 stocks each)
- **2 I-Bonds Accounts**: Treasury I-bonds with fixed and inflation rates

### Historical Data (240 snapshots)
- **24 months** of historical performance data for each account
- **Account-type specific volatility patterns**:
  - CDs: Minimal volatility (-0.5% to +1.5% monthly)
  - Savings: Low volatility (-1% to +2% monthly)
  - 401k: Market-like volatility (-6% to +10% monthly)
  - Trading: High volatility (-12% to +15% monthly)
  - I-Bonds: Steady growth (-0.5% to +2.5% monthly)

### Stock Positions
- **13+ stock positions** across trading accounts
- **Realistic symbols**: AAPL, GOOGL, MSFT, AMZN, TSLA, etc.
- **Historical purchase data** with realistic price variations

## Database Schema

The generated database includes the new `is_demo` column in the accounts table:

```sql
CREATE TABLE accounts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    institution TEXT NOT NULL,
    type TEXT NOT NULL,
    encrypted_data BLOB NOT NULL,
    created_date INTEGER NOT NULL,
    last_updated INTEGER NOT NULL,
    schema_version INTEGER DEFAULT 1,
    is_demo BOOLEAN DEFAULT FALSE  -- New column for demo identification
);
```

## Security

- All sensitive data is encrypted using the same encryption service as the main application
- Uses a fixed demo salt for consistency across demo database generations
- Default demo password: `demo123` (can be customized)

## Import Instructions

1. Run the generator script to create `networth_demo.db`
2. Use the application's import functionality to import the demo database
3. Enter the demo password when prompted (`demo123` by default)
4. All demo accounts will be clearly marked in the UI
5. Use the bulk delete functionality to remove demo data when ready

## Files Created

- `networth_demo.db`: The demo database file
- Contains encrypted financial data, historical snapshots, and stock positions
- Ready for import into the main application