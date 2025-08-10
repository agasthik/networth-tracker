# Net Worth Tracker - Technical Stack

## Core Technologies
- **Backend**: Python 3.8+ with Flask web framework
- **Database**: SQLite with AES-256 encryption
- **Frontend**: HTML templates (Jinja2), CSS, JavaScript
- **Security**: cryptography library for encryption, PBKDF2 key derivation
- **Stock Data**: yfinance library for real-time stock prices

## Key Dependencies
```
Flask==2.3.3
cryptography==41.0.4
yfinance==0.2.18
pytest==7.4.2
Werkzeug==2.3.7
```

## Environment Management
- Uses Python virtual environments (`venv`)
- Environment-specific configurations (development, production, testing)
- Configuration managed through `config.py` with `ConfigManager`

## Common Commands

### Setup and Installation
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

### Running the Application
```bash
# Quick start (automated setup)
./scripts/start.sh        # macOS/Linux
scripts\start.bat         # Windows

# Manual start
python scripts/start.py

# With specific environment
python scripts/start.py --env development

# Debug mode
python scripts/start.py --debug
```

### Testing
```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov

# Run specific test file
python -m pytest tests/test_accounts.py

# Run integration tests
python tests/run_all_tests.py
```

### Database Operations
```bash
# Initialize database
python scripts/init_db.py

# Generate demo data
python scripts/generate_demo_database.py

# Reset demo data
python reset_demo_data.py
```

### Development Tools
```bash
# Validate configuration
python scripts/start.py --validate-only

# Create directories
python scripts/start.py --create-dirs

# Check database schema
python check_db_schema.py
```

## Build System
- No complex build system required
- Uses standard Python packaging
- Virtual environment isolation
- Cross-platform startup scripts