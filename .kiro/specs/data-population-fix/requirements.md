# Requirements Document

## Introduction

The Net Worth Tracker dashboard is currently showing $0.00 for all account types because there are data validation errors preventing accounts from being displayed. The logs show that there's an account with a maturity date in the past, which is causing validation failures and preventing the portfolio summary from calculating correctly. This feature will fix the data population issues and ensure the dashboard displays account data properly.

## Requirements

### Requirement 1

**User Story:** As a user, I want to see my actual account balances on the dashboard, so that I can track my net worth accurately.

#### Acceptance Criteria

1. WHEN the dashboard loads THEN the system SHALL display actual account balances instead of $0.00
2. WHEN there are accounts in the database THEN the system SHALL calculate and display the correct total net worth
3. WHEN account data exists THEN each account type section SHALL show the appropriate balance

### Requirement 2

**User Story:** As a user, I want the system to handle invalid account data gracefully, so that one bad record doesn't break the entire dashboard.

#### Acceptance Criteria

1. WHEN an account has invalid data THEN the system SHALL log the error but continue processing other accounts
2. WHEN validation fails for an account THEN the system SHALL exclude that account from calculations but not crash
3. WHEN there are data validation errors THEN the system SHALL provide clear error messages in the logs

### Requirement 3

**User Story:** As a user, I want to be able to fix or remove accounts with invalid data, so that my dashboard works correctly.

#### Acceptance Criteria

1. WHEN an account has a maturity date in the past THEN the system SHALL either update it to a valid future date or remove the account
2. WHEN fixing account data THEN the system SHALL preserve other valid account information
3. WHEN accounts are corrected THEN the dashboard SHALL immediately reflect the updated data

### Requirement 4

**User Story:** As a user, I want the demo data to work properly, so that I can explore the application features without issues.

#### Acceptance Criteria

1. WHEN using demo mode THEN all demo accounts SHALL have valid data that passes validation
2. WHEN demo data is generated THEN all dates SHALL be set to appropriate future values
3. WHEN switching between demo and production data THEN the dashboard SHALL display correctly for both modes