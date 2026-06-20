# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

Always use the virtual environment at `./venv/` — never call `python`, `python3`, or `pip` directly.

```bash
# Run the application
./venv/bin/python scripts/start.py
./venv/bin/python scripts/start.py --env development
./venv/bin/python scripts/start.py --debug

# Run all tests
./venv/bin/python -m pytest

# Run a single test file
./venv/bin/python -m pytest tests/test_accounts.py

# Run with coverage
./venv/bin/python -m pytest --cov

# Initialize database
./venv/bin/python scripts/init_db.py

# Generate demo data
./venv/bin/python scripts/generate_demo_database.py

# Validate configuration only
./venv/bin/python scripts/start.py --validate-only

# Install a dependency
./venv/bin/pip install package_name
```

Keep CLI commands simple — no more than 3 arguments, no chaining with `&&`, `||`, or `;`. For complex multi-step operations, write a temporary script in `scripts/` rather than a long one-liner.

## Architecture

**Stack:** Python 3.8+ / Flask, SQLite (AES-256 encrypted), Jinja2 templates, vanilla JS.

### Request Lifecycle

All routes in [app.py](app.py) are wrapped with `@api_endpoint` or `@public_view_endpoint` decorators from [services/flask_error_handlers.py](services/flask_error_handlers.py). These decorators handle authentication checks and format errors into consistent JSON or redirect responses.

### Service Layer

Business logic lives entirely in `services/`. Routes in `app.py` delegate to services and return their results — routes do not contain business logic.

| Service | Role |
|---|---|
| [services/database.py](services/database.py) | All SQLite read/write — encrypts/decrypts transparently |
| [services/encryption.py](services/encryption.py) | Fernet AES-256, PBKDF2 key derivation (100k iterations) |
| [services/auth.py](services/auth.py) | Master password setup, verification, session management |
| [services/historical.py](services/historical.py) | Creates `HistoricalSnapshot` on every value change |
| [services/stock_prices.py](services/stock_prices.py) | yfinance integration with rate limiting |
| [services/export_import.py](services/export_import.py) | Encrypted backup and restore |
| [services/watchlist.py](services/watchlist.py) | Stock watchlist management |
| [services/migration.py](services/migration.py) | Schema migrations |
| [services/error_handler.py](services/error_handler.py) | Custom exception hierarchy with error codes |

### Data Models

All account types are defined in [models/accounts.py](models/accounts.py):
- `BaseAccount` → `CDAccount`, `SavingsAccount`, `Account401k`, `TradingAccount`, `IBondsAccount`, `HSAAccount`
- `AccountFactory.create_account_from_dict()` is the single entry point for constructing any account from raw data
- `HistoricalSnapshot` records value changes; `ChangeType` enum distinguishes `MANUAL_UPDATE`, `STOCK_PRICE_UPDATE`, and `INITIAL_ENTRY`
- `TradingAccount` contains a list of `StockPosition` objects; stock prices are updated separately via `StockPriceService`

### Encryption Model

The master password never leaves the process. On login, `EncryptionService` derives an in-memory key using PBKDF2 (random salt stored in DB). Every field written to SQLite passes through this key. The database file is meaningless without the master password.

### Configuration

[config.py](config.py) defines `DevelopmentConfig`, `ProductionConfig`, and `TestingConfig`. `TestingConfig` uses an in-memory SQLite database. Select the environment via `--env development|production|testing` when starting or through the `FLASK_ENV` environment variable.
