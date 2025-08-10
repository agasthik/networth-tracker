# Requirements Document

## Introduction

A comprehensive cleanup and refactoring of the networth tracker application to remove embedded demo functionality and replace it with a standalone demo database that can be imported into the main application. This includes removing all test helper functions and retaining only core application files to create a cleaner, more maintainable codebase.

## Requirements

### Requirement 1

**User Story:** As a developer, I want to remove all embedded demo functionality from the main application, so that the codebase is cleaner and demo data is managed separately.

#### Acceptance Criteria

1. WHEN the demo functionality is removed THEN the system SHALL no longer have demo mode selection in the main application
2. WHEN the demo service is removed THEN the system SHALL remove all demo-related routes, templates, and service functions
3. WHEN demo code is removed THEN the system SHALL remove demo database creation and population logic from the main application
4. WHEN demo functionality is removed THEN the system SHALL remove the mode selection interface and related templates
5. WHEN demo code is cleaned up THEN the system SHALL remove all demo-related configuration and initialization code

### Requirement 2

**User Story:** As a user, I want a standalone demo database with synthetic data, so that I can explore the application features using realistic sample data without affecting my real financial information.

#### Acceptance Criteria

1. WHEN the demo database is created THEN the system SHALL generate a separate SQLite database file with synthetic financial data
2. WHEN the demo database is populated THEN the system SHALL include realistic sample accounts across all supported types (CDs, savings, 401k, trading, I-bonds)
3. WHEN the demo database is created THEN the system SHALL include sample stock positions with realistic symbols, quantities, and purchase dates
4. WHEN the demo database is generated THEN the system SHALL include historical data snapshots to demonstrate trending and performance features
5. WHEN the demo database is created THEN the system SHALL use realistic institution names, account numbers, and financial values
6. WHEN the demo database is complete THEN the system SHALL be importable into the main application using existing import functionality

### Requirement 3

**User Story:** As a user, I want to import the demo database into my main application, so that I can explore features with sample data and then clear it when ready to use real data.

#### Acceptance Criteria

1. WHEN the user wants to use demo data THEN the system SHALL allow importing the demo database through the existing import functionality
2. WHEN the demo database is imported THEN the system SHALL merge the synthetic data with any existing user data
3. WHEN the user imports demo data THEN the system SHALL clearly identify demo accounts to distinguish them from real accounts
4. WHEN the user wants to remove demo data THEN the system SHALL provide functionality to delete all demo accounts while preserving real user data
5. WHEN demo data is imported THEN the system SHALL maintain all existing application functionality including editing, updating, and deleting demo accounts

### Requirement 4

**User Story:** As a developer, I want to remove all test helper functions and temporary files, so that the workspace contains only core application files and proper test suites.

#### Acceptance Criteria

1. WHEN test helper functions are removed THEN the system SHALL delete all standalone test files that were created for debugging or temporary testing
2. WHEN cleanup is performed THEN the system SHALL remove all files with names starting with "test_", "check_", "debug_", or "demo_" that are not part of the formal test suite
3. WHEN temporary files are removed THEN the system SHALL delete backup files, temporary databases, and debugging scripts
4. WHEN cleanup is complete THEN the system SHALL retain only the formal test suite in the tests/ directory
5. WHEN helper functions are removed THEN the system SHALL remove any utility scripts that were created for temporary debugging or validation
6. WHEN workspace is cleaned THEN the system SHALL remove implementation summary files and other temporary documentation

### Requirement 5

**User Story:** As a developer, I want a clean workspace structure, so that the codebase is maintainable and contains only essential files for the application.

#### Acceptance Criteria

1. WHEN the workspace is cleaned THEN the system SHALL retain only core application files (app.py, models/, services/, templates/, static/)
2. WHEN cleanup is performed THEN the system SHALL retain configuration files (config.py, requirements.txt) and documentation (docs/, README.md)
3. WHEN the workspace is organized THEN the system SHALL retain the formal test suite (tests/ directory) and initialization scripts (scripts/ directory)
4. WHEN cleanup is complete THEN the system SHALL remove all temporary, backup, and debugging files
5. WHEN the workspace is finalized THEN the system SHALL ensure all remaining files serve a clear purpose in the application architecture

### Requirement 6

**User Story:** As a developer, I want updated documentation, so that the removal of demo functionality and new demo database approach is clearly documented.

#### Acceptance Criteria

1. WHEN demo functionality is removed THEN the system SHALL update user documentation to reflect the new demo database approach
2. WHEN the demo database is created THEN the system SHALL provide clear instructions on how to import and use the demo data
3. WHEN cleanup is complete THEN the system SHALL update installation and setup documentation to reflect the simplified application structure
4. WHEN documentation is updated THEN the system SHALL remove references to demo mode selection and embedded demo functionality
5. WHEN new approach is documented THEN the system SHALL provide clear instructions for developers on the cleaned workspace structure

### Requirement 7

**User Story:** As a developer, I want to ensure application functionality remains intact, so that removing demo code and cleaning up files doesn't break existing features.

#### Acceptance Criteria

1. WHEN demo functionality is removed THEN the system SHALL maintain all core application features for managing real financial data
2. WHEN cleanup is performed THEN the system SHALL ensure all existing routes, templates, and services continue to function properly
3. WHEN files are removed THEN the system SHALL verify that no remaining code depends on deleted functionality
4. WHEN the application is tested THEN the system SHALL pass all existing tests for core functionality
5. WHEN refactoring is complete THEN the system SHALL maintain database compatibility and user data integrity