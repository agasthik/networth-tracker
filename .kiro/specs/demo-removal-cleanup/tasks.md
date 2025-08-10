# Implementation Plan

- [x] 1. Create demo database generator script with schema migration
  - Create `scripts/generate_demo_database.py` with comprehensive synthetic data generation
  - Add `is_demo` boolean column to accounts table schema in generator
  - Generate 3 CD accounts, 2 savings accounts, 1 401k account, 2 trading accounts, 2 I-bonds accounts
  - Include 24 months of historical data with account-type specific volatility patterns
  - Mark all generated accounts with `is_demo = True`
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 4.1_

- [x] 2. Remove demo functionality from main application
  - Delete `services/demo.py` file completely
  - Remove demo routes (`/mode`, `/demo/reset`) from `app.py`
  - Remove demo imports and manager initialization from `app.py`
  - Delete `templates/mode_selection.html` file
  - Remove demo mode indicators from `templates/dashboard.html`
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5_

- [x] 3. Update database service for demo account handling
  - Modify `services/database.py` to handle `is_demo` column in account operations
  - Add method `delete_demo_accounts()` to bulk remove demo data
  - Update account creation and update methods to preserve demo markers
  - Create migration function to add `is_demo` column to existing databases
  - _Requirements: 3.1, 3.4, 3.5, 4.4_

- [x] 4. Add demo account identification to UI
  - Update account display templates to show demo indicators (badges/icons)
  - Add bulk demo account deletion functionality to dashboard
  - Implement demo account filtering in account lists
  - _Requirements: 3.3, 3.4, 3.5_

- [x] 5. Execute workspace cleanup
  - Remove all `test_*.py`, `check_*.py`, `debug_*.py`, `demo_*.py` files (excluding tests/ directory)
  - Remove backup files (`*.backup_*`), PID files (`*.pid`), and temporary files
  - Remove implementation summary files (`TASK_*_IMPLEMENTATION_SUMMARY.md`)
  - Clean up unused imports and configuration related to demo functionality
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 5.1, 5.2_

- [x] 6. Update documentation
  - Create `docs/demo-data.md` with demo database import instructions
  - Remove demo mode references from existing documentation
  - Update `README.md` to describe new demo database approach
  - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 7. Create tests and perform integration testing
  - Write tests for demo database generation and import workflow
  - Write tests for demo account identification and deletion functionality
  - Test that core application functionality works without demo mode
  - Verify no broken references to removed demo functionality
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5_