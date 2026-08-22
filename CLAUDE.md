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

**Stack:** Python 3.10+ (runtime floor enforced in `scripts/start.py`) / Flask, SQLite with selected sensitive fields encrypted (see Encryption Model), server-rendered Jinja2 + Bootstrap + Chart.js, vanilla JS.

### Request Lifecycle

Routes in [app.py](app.py) are wrapped with endpoint decorators from [services/flask_error_handlers.py](services/flask_error_handlers.py), which handle authentication and format errors into a consistent JSON envelope or redirect:

- `@api_endpoint` — authenticated JSON API routes (**use this for new API routes**)
- `@view_endpoint` — authenticated HTML view routes
- `@public_api_endpoint` / `@public_view_endpoint` — intentionally unauthenticated endpoints only
- `@require_auth` (defined in `app.py`) is a **legacy** decorator still used by some routes; do not add new uses of it

Route handlers parse/validate the request, delegate to services, and format the response — they must not contain business logic.

### Service Layer

Business logic lives entirely in `services/`. Routes in `app.py` delegate to services and return their results — routes do not contain business logic.

| Service | Role |
|---|---|
| [services/database.py](services/database.py) | All SQLite read/write — encrypts/decrypts transparently |
| [services/encryption.py](services/encryption.py) | Fernet (AES-128-CBC + HMAC-SHA256), PBKDF2-HMAC-SHA256 key derivation (100k iterations) |
| [services/auth.py](services/auth.py) | Master password setup, verification, session management |
| [services/historical.py](services/historical.py) | Creates `HistoricalSnapshot` on every value change |
| [services/stock_prices.py](services/stock_prices.py) | yfinance integration with rate limiting |
| [services/export_import.py](services/export_import.py) | Encrypted backup and restore |
| [services/watchlist.py](services/watchlist.py) | Stock watchlist management |
| [services/migration.py](services/migration.py) | Schema migrations (current `DatabaseService.SCHEMA_VERSION` is 6) |
| [services/error_handler.py](services/error_handler.py) | Custom exception hierarchy with error codes |
| [services/flask_error_handlers.py](services/flask_error_handlers.py) | Endpoint decorators + Flask error-to-envelope formatting |
| [services/contribution_limits.py](services/contribution_limits.py) | Versioned IRS 401k/HSA contribution limits |
| [services/logging_config.py](services/logging_config.py) | Structured/colored logging setup and helpers |

### Data Models

All account types are defined in [models/accounts.py](models/accounts.py):
- `BaseAccount` → `CDAccount`, `SavingsAccount`, `Account401k`, `TradingAccount`, `IBondsAccount`, `HSAAccount`
- `AccountFactory.create_account_from_dict()` is the single entry point for constructing any account from raw data
- `HistoricalSnapshot` records value changes; `ChangeType` enum distinguishes `MANUAL_UPDATE`, `STOCK_PRICE_UPDATE`, and `INITIAL_ENTRY`
- `TradingAccount` contains a list of `StockPosition` objects; stock prices are updated separately via `StockPriceService`
- `StockPosition` rows live in the `stock_positions` table, which is the persistent source of truth (schema version 6 migrated legacy positions out of encrypted account payloads). Models/API responses may hydrate positions transiently — do not add another persistent representation.

### Encryption Model

The master password never leaves the process. On login, `EncryptionService` derives an in-memory key using PBKDF2-HMAC-SHA256 (100k iterations, random 16-byte salt stored in the DB) and wraps it in a `Fernet` cipher (**AES-128-CBC + HMAC-SHA256**, not AES-256 — the 32-byte derived key is split into separate encryption and signing halves).

Encryption is **field/payload-level, not whole-file**. Sensitive data is serialized to JSON and stored in `encrypted_data` blobs (accounts, stock positions) and `encrypted_metadata` (snapshots). Indexing/routing columns — `name`, `institution`, `type`, timestamps, `is_demo`, snapshot `value`/`change_type` — are stored in **plaintext**, so the raw SQLite file is not fully opaque. Keep any security documentation consistent with this.

### Configuration

[config.py](config.py) defines a `BaseConfig` and the `DevelopmentConfig`, `ProductionConfig`, and `TestingConfig` subclasses, resolved by `ConfigManager.get_config()`. `TestingConfig` uses an in-memory SQLite database (`:memory:`). Select the environment via `--env development|production|testing` when starting or through the `FLASK_ENV` environment variable. `DATABASE_PATH` (and `TEST_DATABASE_PATH`) can override the database location.
