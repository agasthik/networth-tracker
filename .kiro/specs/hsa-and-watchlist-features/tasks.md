# Implementation Plan

- [x] 1. Extend account model system for HSA support
  - Add HSAAccount class to models/accounts.py with validation and serialization methods
  - Add HSA to AccountType enum
  - Register HSAAccount in AccountFactory
  - Write unit tests for HSAAccount model validation and calculations
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 2. Create watchlist data model and service layer
  - [x] 2.1 Implement WatchlistItem data model
    - Create WatchlistItem dataclass with validation methods
    - Implement to_dict and from_dict serialization methods
    - Write unit tests for WatchlistItem model validation
    - _Requirements: 2.2, 2.3, 2.6, 2.7_

  - [x] 2.2 Create WatchlistService for business logic
    - Implement WatchlistService class with CRUD operations
    - Add stock symbol validation using yfinance integration
    - Implement batch price update functionality with error handling
    - Write unit tests for WatchlistService operations
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7_

- [x] 3. Extend database schema and operations
  - [x] 3.1 Add watchlist table to database schema
    - Extend DatabaseService._initialize_schema() to create watchlist table
    - Add database indexes for efficient watchlist queries
    - Write database migration for existing installations
    - _Requirements: 3.1, 3.2, 3.7_

  - [x] 3.2 Implement watchlist database operations
    - Add watchlist CRUD methods to DatabaseService
    - Implement encrypted storage for watchlist data
    - Add demo data support for watchlist items
    - Write unit tests for watchlist database operations
    - _Requirements: 3.1, 3.2, 3.3, 3.4_

- [x] 4. Create watchlist API endpoints
  - [x] 4.1 Implement core watchlist REST API
    - Add GET /api/watchlist endpoint to retrieve all watchlist items
    - Add POST /api/watchlist endpoint to add stocks to watchlist
    - Add DELETE /api/watchlist/{symbol} endpoint to remove stocks
    - Add GET /api/watchlist/{symbol} endpoint for specific stock details
    - _Requirements: 2.1, 2.2, 2.3, 2.6, 2.7_

  - [x] 4.2 Implement price update API endpoint
    - Add PUT /api/watchlist/prices endpoint for batch price updates
    - Integrate with existing StockPriceService for real-time data
    - Implement error handling for failed price updates
    - Write API endpoint tests for all watchlist operations
    - _Requirements: 2.4, 2.5_

- [x] 5. Extend account API for HSA support
  - Update account validation in create_account and update_account endpoints
  - Add HSA-specific validation rules for contribution limits and balances
  - Extend account form validation to handle HSA fields
  - Write integration tests for HSA account API operations
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6_

- [x] 6. Create user interface components
  - [x] 6.1 Create HSA account form template
    - Create templates/accounts/hsa_form.html with HSA-specific fields
    - Add HSA form validation and submission handling
    - Integrate HSA form with existing account management interface
    - _Requirements: 4.1, 4.4_

  - [x] 6.2 Implement watchlist user interface
    - Create watchlist page template with stock list display
    - Add stock addition form with symbol validation
    - Implement remove stock functionality with confirmation
    - Add price update controls and status indicators
    - _Requirements: 4.2, 4.3, 4.4, 4.5_

- [x] 7. Extend demo data generation
  - [x] 7.1 Add HSA accounts to demo dataset
    - Extend generate_demo_database.py to create sample HSA accounts
    - Generate realistic HSA balances and contribution data
    - Ensure HSA demo accounts integrate with existing demo data patterns
    - _Requirements: 3.4, 3.5, 3.6_

  - [x] 7.2 Add watchlist items to demo dataset
    - Add diverse stock watchlist to demo data generation
    - Include popular stocks from different sectors for demonstration
    - Implement demo watchlist price updates for realistic data
    - _Requirements: 3.5, 3.6_

- [x] 8. Update application routing and navigation
  - Add watchlist route to main Flask application
  - Update navigation templates to include watchlist access
  - Ensure proper authentication for all new endpoints
  - Add watchlist section to dashboard if space permits
  - _Requirements: 4.1, 4.2, 4.3_

- [x] 9. Implement comprehensive error handling
  - Extend existing error handling patterns for HSA and watchlist operations
  - Add specific error messages for stock symbol validation failures
  - Implement graceful degradation for stock price update failures
  - Write error handling tests for edge cases
  - _Requirements: 2.5, 4.4, 4.5_

- [x] 10. Add data export/import support
  - Extend export functionality to include HSA accounts and watchlist data
  - Update import functionality to restore HSA and watchlist items
  - Ensure encrypted backup/restore maintains data integrity
  - Write tests for export/import operations with new data types
  - _Requirements: 3.2, 3.3_