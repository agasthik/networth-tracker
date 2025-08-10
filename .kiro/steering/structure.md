# Net Worth Tracker - Project Structure

## Directory Organization

```
networth-tracker/
├── app.py                 # Main Flask application entry point
├── config.py              # Configuration management (environments, settings)
├── requirements.txt       # Python dependencies
├── models/                # Data models and account types
│   ├── __init__.py
│   └── accounts.py        # Account models, enums, factory patterns
├── services/              # Business logic services
│   ├── __init__.py
│   ├── auth.py           # Authentication and session management
│   ├── database.py       # Encrypted SQLite operations
│   ├── encryption.py     # AES-256 encryption service
│   ├── demo.py           # Demo mode management
│   ├── historical.py     # Historical data tracking
│   ├── stock_prices.py   # Real-time stock price fetching
│   ├── export_import.py  # Data backup/restore
│   ├── error_handler.py  # Centralized error handling
│   ├── logging_config.py # Logging configuration
│   └── flask_error_handlers.py # Flask-specific error handling
├── templates/             # Jinja2 HTML templates
│   ├── base.html         # Base template
│   ├── dashboard.html    # Main dashboard
│   ├── login.html        # Authentication
│   ├── setup.html        # Initial setup
│   ├── accounts/         # Account-specific forms
│   └── errors/           # Error pages (404, 500)
├── static/               # Frontend assets
│   ├── css/styles.css    # Application styles
│   └── js/app.js         # Client-side JavaScript
├── scripts/              # Startup and utility scripts
│   ├── start.py          # Main startup script
│   ├── start.sh          # Unix/Linux launcher
│   ├── start.bat         # Windows launcher
│   ├── init_db.py        # Database initialization
│   └── generate_demo_database.py # Demo data generation
├── tests/                # Test suites
│   ├── __init__.py
│   ├── run_all_tests.py  # Test runner
│   ├── test_*.py         # Individual test modules
│   └── test_integration.py # Integration tests
├── docs/                 # Documentation
│   ├── README.md         # Main documentation
│   ├── installation.md   # Setup guide
│   ├── user-guide.md     # User documentation
│   └── deployment.md     # Deployment guide
├── logs/                 # Application logs
├── backups/              # Data backups
├── data/                 # Database files location
└── temp/                 # Temporary files
```

## Architecture Patterns

### Service Layer Pattern
- Business logic separated into `services/` modules
- Each service handles a specific domain (auth, database, encryption)
- Services are injected into Flask routes via dependency injection

### Factory Pattern
- `AccountFactory` in `models/accounts.py` creates account instances
- Supports extensible account types through enum-based dispatch

### Repository Pattern
- `DatabaseService` abstracts database operations
- Encryption/decryption handled transparently
- Thread-safe connection management

### Error Handling Strategy
- Centralized error handling in `services/error_handler.py`
- Custom exception hierarchy for different error types
- Flask error handlers for consistent API responses

## File Naming Conventions
- Snake_case for Python files and directories
- Descriptive module names (e.g., `flask_error_handlers.py`)
- Test files prefixed with `test_`
- Script files in `scripts/` directory
- Configuration files at root level

## Key Design Principles
- **Separation of Concerns**: Models, services, and views are clearly separated
- **Dependency Injection**: Services are passed to components that need them
- **Configuration Management**: Environment-specific settings in `config.py`
- **Security by Design**: Encryption service used throughout data layer
- **Testability**: Comprehensive test coverage with isolated test modules