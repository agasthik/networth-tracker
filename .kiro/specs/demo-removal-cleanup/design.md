# Design Document

## Overview

This design outlines the comprehensive removal of embedded demo functionality from the networth tracker application and its replacement with a standalone demo database approach. The solution involves creating a separate demo database with synthetic data that can be imported through the existing export/import functionality, while simultaneously cleaning up the workspace by removing all temporary test files and debugging scripts.

## Architecture

### Current Demo Architecture (To Be Removed)
- **DemoModeManager**: Manages switching between production and demo modes
- **DemoDataGenerator**: Generates synthetic financial data in-memory
- **Mode Selection UI**: Template and routes for switching between modes
- **Embedded Demo Logic**: Demo functionality integrated throughout the application

### New Demo Architecture (Target State)
- **Standalone Demo Database**: Pre-generated SQLite database with synthetic data
- **Import-Based Demo**: Users import demo data through existing export/import functionality
- **Clean Application**: Single-mode application without demo switching logic
- **Demo Data Identification**: Clear marking of demo accounts for easy removal

## Components and Interfaces

### 1. Demo Database Generator Script
**Purpose**: Create a standalone demo database with comprehensive synthetic data

**Location**: `scripts/generate_demo_database.py`

**Key Functions**:
- `generate_demo_database()`: Main function to create demo database
- `populate_demo_accounts()`: Create realistic demo accounts across all types
- `generate_demo_historical_data()`: Create 2 years of historical performance data
- `add_demo_markers()`: Mark all accounts as demo data for identification

**Database Schema**: Uses existing database schema with additional demo markers

### 2. Demo Data Identification System
**Purpose**: Clearly identify demo accounts to allow selective removal

**Implementation**:
- Add `is_demo` boolean field to accounts table (migration required)
- Mark all demo accounts with `is_demo = true`
- Provide UI indicators for demo accounts
- Enable bulk deletion of demo accounts

### 3. Application Cleanup Components
**Purpose**: Remove demo mode functionality from main application

**Files to Modify**:
- `app.py`: Remove demo routes and mode switching logic
- `services/demo.py`: Delete entire file
- `templates/mode_selection.html`: Delete file
- `templates/dashboard.html`: Remove demo mode indicators

**Routes to Remove**:
- `/mode` (GET/POST)
- `/demo/reset` (POST)

### 4. Workspace Cleanup System
**Purpose**: Remove all temporary and test helper files

**Categories of Files to Remove**:
- Test helper files: `test_*.py` (excluding formal test suite)
- Debug scripts: `debug_*.py`, `check_*.py`
- Demo testing files: `demo_*.py`
- Temporary files: `*.backup_*`, `*.pid`, `scratchpad-*`
- Implementation summaries: `TASK_*_IMPLEMENTATION_SUMMARY.md`

**Files to Retain**:
- Core application: `app.py`, `config.py`, `requirements.txt`
- Models and services: `models/`, `services/` (except `services/demo.py`)
- Templates and static files: `templates/`, `static/`
- Formal test suite: `tests/` directory
- Documentation: `docs/`, `README.md`
- Scripts: `scripts/` directory

## Data Models

### Demo Database Schema
The demo database will use the existing schema with these additions:

```sql
-- Add demo identification to accounts table
ALTER TABLE accounts ADD COLUMN is_demo BOOLEAN DEFAULT FALSE;

-- Demo accounts will have realistic data:
-- - 3 CD accounts with varying terms and rates
-- - 2 savings accounts with different institutions
-- - 1 401k account with employer matching
-- - 2 trading accounts with diverse stock positions
-- - 2 I-bonds accounts with different purchase dates
```

### Demo Account Data Structure
```python
demo_accounts = {
    "cd_accounts": [
        {
            "name": "CD Account 1 (12mo)",
            "institution": "Chase Bank",
            "principal_amount": 15000.00,
            "interest_rate": 3.25,
            "maturity_date": "2025-08-15",
            "current_value": 15243.75,
            "is_demo": True
        }
        # ... additional CD accounts
    ],
    "savings_accounts": [
        {
            "name": "High Yield Savings 1",
            "institution": "Ally Bank",
            "current_balance": 12500.00,
            "interest_rate": 2.15,
            "is_demo": True
        }
        # ... additional savings accounts
    ],
    # ... other account types
}
```

### Historical Data Generation
- **Time Range**: 24 months of historical data
- **Frequency**: Monthly snapshots
- **Volatility**: Account-type specific volatility patterns
- **Growth Patterns**: Realistic growth trajectories based on account type

## Error Handling

### Demo Database Generation Errors
- **Database Creation Failure**: Retry with temporary directory, log detailed error
- **Data Population Failure**: Continue with partial data, report missing components
- **Encryption Errors**: Validate encryption service setup before generation

### Import Process Errors
- **Duplicate Account Handling**: Provide clear options for overwrite vs. skip
- **Data Validation Errors**: Report specific validation failures with suggestions
- **Database Integrity Issues**: Rollback partial imports, maintain data consistency

### Cleanup Process Errors
- **File Deletion Failures**: Log failures but continue cleanup, report summary
- **Permission Issues**: Provide clear instructions for manual cleanup
- **Dependency Errors**: Check for file dependencies before deletion

## Testing Strategy

### Demo Database Testing
1. **Generation Testing**: Verify demo database creation with all account types
2. **Data Integrity Testing**: Validate all demo accounts have required fields
3. **Historical Data Testing**: Confirm 24 months of realistic historical data
4. **Import Testing**: Test demo database import through existing functionality

### Application Cleanup Testing
1. **Functionality Testing**: Verify all core features work after demo removal
2. **Route Testing**: Confirm removed routes return 404 errors
3. **Template Testing**: Verify no broken template references
4. **Database Testing**: Ensure production database functionality intact

### Workspace Cleanup Testing
1. **File Removal Testing**: Verify correct files are removed and retained
2. **Dependency Testing**: Confirm no remaining code references deleted files
3. **Build Testing**: Verify application builds and runs after cleanup
4. **Test Suite Testing**: Confirm formal test suite still functions

### Integration Testing
1. **End-to-End Demo Flow**: Test complete demo import and usage workflow
2. **Demo Data Removal**: Test selective removal of demo accounts
3. **Production Data Safety**: Verify production data remains untouched
4. **Performance Testing**: Confirm no performance degradation after changes

## Implementation Phases

### Phase 1: Demo Database Generation
1. Create demo database generator script
2. Implement comprehensive synthetic data generation
3. Add demo identification markers
4. Generate standalone demo database file

### Phase 2: Application Demo Removal
1. Remove demo mode routes and logic from app.py
2. Delete demo service and related files
3. Remove mode selection template
4. Update dashboard to remove demo indicators

### Phase 3: Database Schema Updates
1. Add is_demo column to accounts table
2. Create migration script for existing installations
3. Update database service to handle demo markers
4. Implement demo account filtering and deletion

### Phase 4: Workspace Cleanup
1. Identify all temporary and test helper files
2. Create cleanup script with safety checks
3. Remove identified files systematically
4. Update documentation to reflect changes

### Phase 5: Documentation and Testing
1. Update user documentation for new demo approach
2. Create import instructions for demo database
3. Update developer documentation
4. Comprehensive testing of all changes

## Migration Strategy

### Existing Users
- **Automatic Migration**: Database schema update adds is_demo column
- **Demo Mode Users**: Provide export option before removing demo functionality
- **Documentation Updates**: Clear migration guide for new demo approach

### New Users
- **Simplified Setup**: Single-mode application with optional demo import
- **Demo Database Download**: Provide pre-generated demo database
- **Import Instructions**: Step-by-step guide for demo data import

## Security Considerations

### Demo Data Security
- **No Real Data**: Ensure all demo data is clearly synthetic
- **Encryption**: Demo database uses same encryption as production
- **Identification**: Clear marking prevents accidental use of demo data

### Cleanup Security
- **File Verification**: Verify file contents before deletion
- **Backup Recommendations**: Suggest backup before cleanup
- **Rollback Capability**: Maintain ability to restore if needed

## Performance Implications

### Positive Impacts
- **Reduced Memory Usage**: No in-memory demo data generation
- **Faster Startup**: No demo mode initialization overhead
- **Simpler Codebase**: Reduced complexity improves maintainability

### Considerations
- **Import Performance**: Demo database import is one-time operation
- **Storage**: Demo database file adds ~2MB to distribution
- **Database Size**: Demo accounts increase database size when imported