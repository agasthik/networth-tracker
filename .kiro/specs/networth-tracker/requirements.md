# Requirements Document

## Introduction

A browser-based networth tracking application that allows users to monitor their financial portfolio across multiple investment types including CDs, savings accounts, 401k accounts, and trading accounts with stocks. The application will store all data locally on the user's machine using file-based storage, ensuring privacy and offline functionality.

## Requirements

### Requirement 1

**User Story:** As a user, I want to add and manage different types of investment accounts, so that I can track my complete financial portfolio in one place.

#### Acceptance Criteria

1. WHEN the user accesses the application THEN the system SHALL display options to add CD accounts, savings accounts, 401k accounts, trading accounts, and I-bonds accounts
2. WHEN the user adds a new account THEN the system SHALL require account name, institution name, and account type
3. WHEN the user adds a CD account THEN the system SHALL additionally require principal amount, interest rate, maturity date, and current value
4. WHEN the user adds a savings account THEN the system SHALL additionally require current balance and interest rate
5. WHEN the user adds a 401k account THEN the system SHALL additionally require current balance, employer match details, and contribution limits
6. WHEN the user adds a trading account THEN the system SHALL additionally require broker name, account balance and allow adding individual stock holdings
7. WHEN the user adds an I-bonds account THEN the system SHALL additionally require purchase amount, purchase date, fixed rate, and current inflation rate

### Requirement 2

**User Story:** As a user, I want to track individual stocks within my trading accounts, so that I can monitor my equity investments performance.

#### Acceptance Criteria

1. WHEN the user selects a trading account THEN the system SHALL allow adding individual stock positions
2. WHEN the user adds a stock position THEN the system SHALL require stock symbol, number of shares, purchase price, and purchase date
3. WHEN the user views stock holdings THEN the system SHALL display current value, gain/loss, and percentage change
4. WHEN the user updates stock information THEN the system SHALL recalculate portfolio totals automatically

### Requirement 3

**User Story:** As a user, I want all my financial data stored locally in an encrypted SQLite database, so that my sensitive information remains private and accessible offline.

#### Acceptance Criteria

1. WHEN the user enters financial data THEN the system SHALL store all information in an encrypted SQLite database on the user's machine
2. WHEN the user closes and reopens the application THEN the system SHALL load all previously entered data from the local database
3. WHEN the user is offline THEN the system SHALL continue to function with full read/write capabilities except for stock price updates
4. WHEN the user accesses the application THEN the system SHALL NOT transmit any financial data to external servers except for stock price API calls

### Requirement 4

**User Story:** As a user, I want to view my total networth and account summaries, so that I can understand my overall financial position.

#### Acceptance Criteria

1. WHEN the user opens the dashboard THEN the system SHALL display total networth across all accounts
2. WHEN the user views the dashboard THEN the system SHALL show breakdown by account type (CDs, savings, 401k, trading)
3. WHEN the user views account details THEN the system SHALL display individual account balances and performance metrics
4. WHEN account values change THEN the system SHALL update networth calculations automatically

### Requirement 5

**User Story:** As a user, I want to update account balances and have stock prices automatically fetched, so that my networth tracking remains current and accurate.

#### Acceptance Criteria

1. WHEN the user selects an account THEN the system SHALL allow editing current balance or value
2. WHEN the user views stock positions THEN the system SHALL automatically fetch current market prices
3. WHEN stock prices are updated THEN the system SHALL recalculate the total value of positions automatically
4. WHEN the user saves changes THEN the system SHALL persist updates to encrypted SQLite database immediately
5. WHEN the user views updated accounts THEN the system SHALL reflect changes in dashboard totals

### Requirement 6

**User Story:** As a user, I want to track historical performance of my investments over time, so that I can analyze trends and make informed decisions.

#### Acceptance Criteria

1. WHEN the user adds or updates account values THEN the system SHALL store historical snapshots with timestamps
2. WHEN the user views an account THEN the system SHALL display historical value charts and performance metrics
3. WHEN the user accesses the dashboard THEN the system SHALL show networth trends over time
4. WHEN historical data is stored THEN the system SHALL maintain data integrity in the encrypted database

### Requirement 7

**User Story:** As a user, I want to export my financial data for backup purposes, so that I can protect against data loss and maintain records.

#### Acceptance Criteria

1. WHEN the user selects export functionality THEN the system SHALL provide options to export data in multiple formats
2. WHEN the user exports data THEN the system SHALL include all account information, historical data, and current values
3. WHEN the user exports data THEN the system SHALL create encrypted backup files
4. WHEN the user needs to restore data THEN the system SHALL allow importing from previously exported backup files

### Requirement 8

**User Story:** As a user, I want my financial data secured with encryption, so that my sensitive information is protected even if stored locally.

#### Acceptance Criteria

1. WHEN the user first accesses the application THEN the system SHALL require setting up a master password
2. WHEN the user enters the master password THEN the system SHALL decrypt and provide access to the SQLite database
3. WHEN the user saves any data THEN the system SHALL encrypt all information before storing in the database
4. WHEN the user closes the application THEN the system SHALL ensure all data remains encrypted at rest

### Requirement 9

**User Story:** As a user, I want to manually input current investment values and have the system track changes over time, so that I can maintain accurate records of my portfolio state.

#### Acceptance Criteria

1. WHEN the user adds a new account THEN the system SHALL require entering the current balance or value as the initial state
2. WHEN the user wants to update account values THEN the system SHALL provide manual input fields for current balances
3. WHEN the user updates CD accounts THEN the system SHALL allow updating current value while maintaining original principal and maturity information
4. WHEN the user updates 401k accounts THEN the system SHALL allow updating current balance and contribution amounts
5. WHEN the user updates savings accounts THEN the system SHALL allow updating current balance
6. WHEN the user updates trading accounts THEN the system SHALL allow updating account cash balance while stock values update automatically via market prices
7. WHEN the user saves updated values THEN the system SHALL create a historical snapshot with timestamp before applying changes

### Requirement 10

**User Story:** As a user, I want a tabbed interface with consolidated summary, so that I can easily navigate between different investment types and view overall portfolio performance.

#### Acceptance Criteria

1. WHEN the user opens the application THEN the system SHALL display a consolidated summary tab showing total networth
2. WHEN the user navigates tabs THEN the system SHALL provide separate tabs for CDs, Savings, 401k, Trading, and I-bonds accounts
3. WHEN the user views any tab THEN the system SHALL display relevant account details and performance metrics for that investment type
4. WHEN the user switches between tabs THEN the system SHALL maintain real-time data consistency across all views

### Requirement 11

**User Story:** As a user, I want the system to support future investment products without affecting my existing data, so that I can adapt to new investment opportunities over time.

#### Acceptance Criteria

1. WHEN new investment product types are added to the system THEN the system SHALL preserve all existing account data and functionality
2. WHEN the user adds accounts with multiple brokers THEN the system SHALL track broker information separately for each trading account
3. WHEN new account types are introduced THEN the system SHALL provide appropriate input forms and validation rules
4. WHEN the database schema needs updates THEN the system SHALL migrate existing data without loss or corruption
5. WHEN the user views accounts of new types THEN the system SHALL display them appropriately in the dashboard and relevant tabs

### Requirement 12

**User Story:** As a user, I want a demo mode with synthetic data, so that I can explore the application interface and reporting features without using my actual financial information.

#### Acceptance Criteria

1. WHEN the user starts the application THEN the system SHALL provide an option to run in demo mode or production mode
2. WHEN the user selects demo mode THEN the system SHALL create a separate demo database with realistic synthetic financial data
3. WHEN the user uses demo mode THEN the system SHALL populate sample accounts including CDs, savings, 401k, trading accounts, and I-bonds with different institutions and brokers
4. WHEN the user views demo data THEN the system SHALL display realistic account balances, stock positions, and historical performance data
5. WHEN the user switches between demo and production modes THEN the system SHALL maintain completely separate databases and sessions
6. WHEN the user explores demo mode THEN the system SHALL provide full functionality including adding, editing, and deleting demo accounts
7. WHEN the user exits demo mode THEN the system SHALL clearly indicate they are returning to production mode with real data