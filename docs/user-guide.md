# Networth Tracker - User Guide

This comprehensive guide covers all features and functionality of the Networth Tracker application.

## Table of Contents

- [Getting Started](#getting-started)
- [Application Modes](#application-modes)
- [Account Management](#account-management)
- [Investment Types](#investment-types)
- [Dashboard and Reporting](#dashboard-and-reporting)
- [Data Management](#data-management)
- [Security Features](#security-features)
- [Advanced Features](#advanced-features)
- [Tips and Best Practices](#tips-and-best-practices)

## Getting Started

### First Login

1. **Initial Setup**: When you first run the application, you'll be prompted to create a master password
2. **Master Password**: Choose a strong password (minimum 12 characters) - this encrypts all your financial data
3. **Login**: Use your master password to access the application

### Main Interface

The application features a clean, tabbed interface:
- **Summary Tab**: Overview of your total networth
- **Account Type Tabs**: Separate tabs for CDs, Savings, 401k, Trading, and I-bonds
- **Navigation**: Easy switching between different investment types

## Application Modes

### Production Mode
- **Purpose**: For managing your real financial data
- **Database**: Stores your actual account information
- **Security**: Full encryption and security measures

### Demo Database
- **Purpose**: Explore the application with synthetic data
- **Import Process**: Import demo database through standard import functionality
- **Features**: Full functionality without using real financial information
- **Identification**: Demo accounts are clearly marked with badges

**Using Demo Data:**
1. Generate or download a demo database (see [Demo Database Guide](demo-data.md))
2. Use the Import functionality to load demo data
3. Demo accounts will be clearly marked in the interface
4. Remove demo accounts when ready to use real data

## Account Management

### Adding Accounts

1. **Navigate**: Go to the appropriate tab for your account type
2. **Add Account**: Click the "Add Account" button
3. **Fill Information**: Complete all required fields
4. **Save**: Click "Save" to create the account

### Editing Accounts

1. **Select Account**: Click on an existing account
2. **Edit**: Click the "Edit" button
3. **Update Information**: Modify any fields as needed
4. **Save Changes**: Click "Save" to update

### Deleting Accounts

1. **Select Account**: Click on the account to delete
2. **Delete**: Click the "Delete" button
3. **Confirm**: Confirm the deletion (this cannot be undone)

## Investment Types

### Certificate of Deposit (CD) Accounts

**Required Information:**
- Account name and institution
- Principal amount (initial investment)
- Interest rate (annual percentage)
- Maturity date
- Current value

**Features:**
- Automatic interest calculation
- Maturity date tracking
- Historical value tracking

### Savings Accounts

**Required Information:**
- Account name and institution
- Current balance
- Interest rate (if applicable)

**Features:**
- Balance tracking over time
- Interest rate monitoring
- Easy balance updates

### 401k Retirement Accounts

**Required Information:**
- Account name and institution
- Current balance
- Employer match details
- Contribution limits
- Employer contribution amounts

**Features:**
- Contribution tracking
- Employer match monitoring
- Performance analysis

### Trading Accounts

**Required Information:**
- Account name and broker
- Cash balance
- Individual stock positions

**Stock Position Information:**
- Stock symbol
- Number of shares
- Purchase price
- Purchase date

**Features:**
- Automatic stock price updates
- Gain/loss calculations
- Portfolio performance tracking
- Multiple broker support

### I-bonds (Treasury Inflation-Protected Securities)

**Required Information:**
- Purchase amount
- Purchase date
- Fixed rate
- Current inflation rate
- Current value

**Features:**
- Inflation adjustment tracking
- Maturity date calculation (30 years)
- Value appreciation monitoring

### HSA (Health Savings Account)

**Required Information:**
- Account name and institution
- Current balance
- Annual contribution limit
- Current year contributions
- Employer contributions
- Investment balance (if applicable)
- Cash balance

**Features:**
- Contribution tracking and limits
- Employer contribution monitoring
- Investment vs. cash balance tracking
- Tax-advantaged savings analysis
- Remaining contribution capacity calculations

## Dashboard and Reporting

### Summary Dashboard

**Total Networth Display:**
- Combined value of all accounts
- Breakdown by account type
- Percentage allocation

**Quick Stats:**
- Number of accounts by type
- Recent account updates
- Performance indicators

### Account Type Views

Each tab provides:
- **Account List**: All accounts of that type
- **Total Value**: Combined value for the account type
- **Individual Details**: Specific information for each account
- **Performance Metrics**: Gains, losses, and trends

### Historical Data

**Automatic Tracking:**
- Value snapshots created on updates
- Historical performance charts
- Trend analysis

**Time Periods:**
- Daily, weekly, monthly views
- Custom date ranges
- Long-term performance tracking

## Data Management

### Export Functionality

**Export Options:**
1. **Full Export**: All account data and history
2. **Account Type Export**: Specific investment types
3. **Date Range Export**: Historical data for specific periods

**Export Process:**
1. Navigate to "Export Data"
2. Choose export options
3. Download encrypted backup file
4. Store securely for backup purposes

### Import Functionality

**Import Process:**
1. Navigate to "Import Data"
2. Select previously exported backup file
3. Enter master password for decryption
4. Confirm import operation

**Important Notes:**
- Imports will merge with existing data
- Duplicate accounts are handled automatically
- Historical data is preserved

### Backup Strategy

**Recommended Approach:**
1. **Regular Exports**: Weekly or monthly full exports
2. **Secure Storage**: Store backup files in multiple locations
3. **Test Restores**: Periodically test import functionality
4. **Version Control**: Keep multiple backup versions

## Security Features

### Encryption

**Data Protection:**
- All financial data encrypted with AES-256
- Master password used for key derivation
- Database files encrypted at rest

**Key Features:**
- PBKDF2 key derivation with 100,000 iterations
- Random salt generation
- No plaintext data storage

### Privacy

**Local Storage:**
- All data stored locally on your machine
- No cloud synchronization
- No external data transmission (except stock prices)

**Network Security:**
- Application runs on localhost only
- No external access to your data
- Stock API calls use symbols only (no financial data)

### Session Management

**Security Measures:**
- Automatic session timeout (2 hours default)
- Secure session cookies
- Logout functionality

## Advanced Features

### Stock Price Updates

**Automatic Updates:**
- Real-time stock price fetching
- Batch processing for multiple positions
- Rate limiting to respect API limits

**Manual Updates:**
- Force refresh stock prices
- Individual stock updates
- Bulk update all positions

### Historical Analysis

**Performance Metrics:**
- Total return calculations
- Annualized returns
- Gain/loss analysis
- Time-weighted returns

**Trend Analysis:**
- Moving averages
- Performance comparisons
- Asset allocation changes

### Multi-Broker Support

**Trading Accounts:**
- Support for multiple brokers
- Separate tracking per broker
- Consolidated portfolio view

### Future Investment Types

**Extensible Design:**
- Easy addition of new account types
- Flexible data storage
- Backward compatibility

## Tips and Best Practices

### Account Management

1. **Consistent Naming**: Use clear, consistent account names
2. **Regular Updates**: Update account values regularly for accurate tracking
3. **Detailed Information**: Include all relevant account details
4. **Institution Tracking**: Keep institution information current

### Data Entry

1. **Accuracy**: Double-check all entered values
2. **Date Formats**: Use consistent date formats (YYYY-MM-DD)
3. **Currency**: Enter values in your base currency
4. **Precision**: Use appropriate decimal precision for values

### Security

1. **Strong Master Password**: Use a complex, memorable password
2. **Regular Backups**: Export data regularly
3. **Secure Storage**: Store backups in secure locations
4. **Access Control**: Limit access to your computer

### Performance Tracking

1. **Regular Snapshots**: Update values consistently
2. **Historical Context**: Review long-term trends
3. **Diversification**: Monitor asset allocation
4. **Goal Setting**: Set and track financial goals

### Troubleshooting

1. **Log Files**: Check logs for error messages
2. **Demo Database**: Import demo database to test features (see [Demo Database Guide](demo-data.md))
3. **Validation**: Use built-in validation tools
4. **Fresh Start**: Remove demo accounts and start with clean data

### Workflow Recommendations

**Daily:**
- Check stock price updates
- Review any account changes

**Weekly:**
- Update account balances
- Review performance metrics

**Monthly:**
- Export backup data
- Analyze trends and performance
- Update investment goals

**Quarterly:**
- Comprehensive portfolio review
- Rebalancing considerations
- Long-term strategy assessment

## Keyboard Shortcuts

- **Ctrl+S**: Save current form
- **Ctrl+N**: Add new account
- **Ctrl+E**: Export data
- **Ctrl+R**: Refresh stock prices
- **Esc**: Cancel current operation

## Getting Help

### Built-in Help

- **Tooltips**: Hover over fields for help text
- **Validation Messages**: Clear error messages
- **Status Indicators**: Visual feedback for operations

### Troubleshooting

1. **Check Logs**: Review log files in the logs/ directory
2. **Validate Configuration**: Use validation tools
3. **Demo Database**: Test functionality with sample data (see [Demo Database Guide](demo-data.md))
4. **Fresh Installation**: Reinstall if necessary

### Support Resources

- **Installation Guide**: Detailed setup instructions
- **Configuration Reference**: Advanced configuration options
- **API Documentation**: Technical implementation details

This user guide covers the core functionality of the Networth Tracker application. For technical details and advanced configuration, refer to the additional documentation files.