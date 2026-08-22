# AGENTS.md

This file defines the working agreement for coding agents in this repository.
It applies to the entire project unless a more specific `AGENTS.md` exists in a
subdirectory.

## Project Summary

Networth Tracker is a local-first Flask application for tracking financial
accounts, stock positions, historical values, and a stock watchlist. The
frontend is server-rendered Jinja2 plus Bootstrap, Chart.js, and vanilla
JavaScript. Data is stored in SQLite, with selected fields encrypted using a
key derived from the user's master password.

Supported account types are:

- Certificates of deposit (`CD`)
- Savings accounts (`SAVINGS`)
- 401(k) accounts (`401K`)
- Trading accounts (`TRADING`)
- I Bonds (`I_BONDS`)
- Health savings accounts (`HSA`)

## Repository Map

- `app.py`: Flask application and route handlers
- `config.py`: environment-specific configuration
- `models/`: account and watchlist domain models
- `services/`: authentication, database, encryption, historical analysis,
  stock pricing, watchlist, migration, import/export, logging, and errors
- `templates/`: Jinja2 pages and account forms
- `static/js/app.js`: dashboard and account UI behavior
- `static/css/styles.css`: application styling and themes
- `scripts/`: startup, database, and demo-data utilities
- `tests/`: unit, route, integration, security, and end-to-end tests
- `docs/`: user, installation, deployment, and security documentation

## Environment Setup

Python 3.10+ is the minimum supported version.

Create the virtual environment only when it does not already exist:

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

After bootstrap, run Python and pip only through `./venv/bin/`.

Common commands:

```bash
./venv/bin/python scripts/start.py --env development
./venv/bin/python scripts/start.py --validate-only
./venv/bin/python -m pytest -q
./venv/bin/python -m pytest tests/test_accounts.py -q
./venv/bin/python -m pytest tests/test_account_api.py -q
./venv/bin/python -m pytest --cov=services --cov=models
```

The local application normally runs at `http://127.0.0.1:5000`.

## Current Baseline

The full test suite was last verified on August 22, 2026, with Python 3.14.7:
499 tests passed. This is a point-in-time baseline, not a substitute for running
the relevant tests. Run focused tests before and after a change, and report both
the focused result and any relevant full-suite failures.

There is no established formatter, linter, type checker, or CI workflow. Keep
changes PEP 8 compatible, preserve the surrounding style, and avoid unrelated
formatting churn.

Known architectural risks:

- `app.py`, `services/database.py`, and `static/js/app.js` are large and tightly
  coupled. Prefer extracting cohesive behavior when modifying these files.
- Trading positions were historically stored both inside encrypted account
  payloads and in the `stock_positions` table. Schema version 6 migrates legacy
  embedded positions out of account payloads, and the table is now the
  persistent source of truth. Models and API responses may hydrate positions
  transiently; do not introduce another persistent representation.
- Historical snapshots are event-driven and sparse. Do not describe their
  output as investment return unless deposits and withdrawals are accounted
  for.
- Import and export behavior is security- and data-integrity-sensitive.
- `networth.db` and `networth_demo.db` are currently tracked. Do not use,
  rewrite, delete, or inspect their user data during routine development.

## Architecture Rules

The rules below define the required direction for new and modified code. Some
legacy code does not yet comply. Do not copy or expand those violations, and do
not turn an otherwise focused change into an unrelated repository-wide
refactor.

### Routes

- New API routes MUST use `@api_endpoint`.
- New authenticated view routes SHOULD use `@view_endpoint`.
- Use `@public_api_endpoint` or `@public_view_endpoint` only for endpoints that
  are intentionally available without authentication.
- Do not add new uses of the legacy `@require_auth` decorator.
- Route handlers SHOULD parse and validate requests, delegate business logic to
  services, and format responses. Move reusable business logic out of
  `app.py`.
- Preserve the existing JSON error envelope and use the exception hierarchy in
  `services/error_handler.py`.
- Never return raw exception text, stack traces, secrets, or decrypted data to
  clients.

### Models and Validation

- Construct accounts through `AccountFactory`.
- Keep account-type validation in the model or a shared service, not separately
  reimplemented in multiple routes.
- Dates crossing the HTTP boundary MUST use ISO 8601 `YYYY-MM-DD` strings.
- Datetimes SHOULD be serialized with `datetime.isoformat()`.
- Validate monetary values, percentages, symbols, and dates on the server even
  when the frontend also validates them.
- Existing code uses floats for money. Use cent-level tolerances for comparisons
  and do not introduce exact float equality checks.

### Database and Migrations

- All SQLite access MUST go through `DatabaseService` or a dedicated repository
  introduced as part of a deliberate refactor.
- Use parameterized SQL exclusively.
- Multi-record operations such as imports MUST be transactional: commit only
  after the full operation succeeds and roll back on failure.
- Balance-changing operations MUST create a historical snapshot only after the
  related data mutation succeeds.
- Restores MUST preserve original IDs, timestamps, relationships, and demo
  markers unless the import policy explicitly remaps them.
- Schema changes MUST increment `DatabaseService.SCHEMA_VERSION` and include a
  forward migration in `services/migration.py`.
- Migrations MUST be idempotent and tested against both an old schema and a
  current schema.
- Tests MUST use a temporary database or isolated in-memory database. Never run
  tests against repository database files.

### Authentication and Security

- Never log or expose master passwords, derived keys, password hashes, salts,
  decrypted account payloads, full account numbers, or backup contents.
- Clear authentication state and database handles on logout.
- State-changing browser requests MUST have CSRF protection or an equivalent
  verified same-origin control.
- File uploads MUST have explicit size limits and must be validated before use.
- Login and network-backed endpoints SHOULD have abuse and retry limits.
- Use constant-time verification for secret comparisons.
- Security documentation MUST match the implementation. Fernet uses AES-128-CBC
  with HMAC-SHA256, and the current database encrypts selected payloads rather
  than the entire SQLite file.
- Keep the default server binding on `127.0.0.1`. Do not broaden it without an
  explicit product requirement and corresponding security review.

### Stock Prices and External Calls

- `StockPriceService` is the only approved boundary for market-price providers.
- Unit and integration tests MUST mock network calls; they must not contact
  Yahoo Finance, yfinance, or fallback providers.
- A failed quote refresh MUST preserve the last known price and expose its
  staleness.
- Batch updates MUST report per-symbol success and failure accurately. Do not
  return a successful aggregate response after silently swallowing account
  failures.
- Never generate mock or random prices in a production user workflow.

### Historical Performance

- Distinguish net worth change from investment performance.
- Contributions, withdrawals, transfers, fees, and income MUST be separated
  from market gains before calculating returns.
- Period labels such as month-to-date, year-to-date, and one year MUST be backed
  by calculations for those exact periods.
- Imported snapshots MUST retain their original timestamps.
- API response contracts and frontend consumers MUST be changed together.

### Frontend

- Keep the frontend build-free unless a broader migration is explicitly
  requested.
- Reuse vendored assets in `static/vendor/`; local-first operation must not
  require a CDN.
- Use `textContent` or DOM construction for untrusted values. Avoid inserting
  account names, institutions, notes, or API errors with `innerHTML`.
- Preserve both light and dark themes and verify responsive behavior.
- Use Bootstrap components and the existing visual language before adding a new
  UI pattern.
- Forms need loading, success, validation, empty, and failure states.
- Icon-only controls need an accessible name and tooltip.
- Do not duplicate page behavior between inline template scripts and
  `static/js/app.js`; move reusable behavior into the static module.

## Testing Rules

Every behavior change requires focused tests at the lowest useful layer:

- Models and validation: `tests/test_accounts.py`
- Database behavior: `tests/test_database.py`
- Authentication: `tests/test_auth.py` and `tests/test_security.py`
- Historical calculations: `tests/test_historical.py`
- Import/export: `tests/test_export_import.py` and route tests
- Stock positions and pricing: corresponding API and service tests
- Watchlist: model, database, service, and API tests
- User workflows spanning layers: integration or end-to-end tests

For Flask route tests:

- Use a fresh temporary database per test or fixture scope.
- Replace both the module-level `auth_manager` and `app.auth_manager`; route
  decorators read from `current_app.auth_manager`.
- Do not share one Flask test client across threads.
- Assert status code, response schema, error code, and persisted state.

Regression tests SHOULD fail before the fix and pass after it. Avoid tests that
only repeat implementation details or accept misleading success responses.

## Data and Version-Control Safety

- Do not commit `*.db`, `*.sqlite`, `*.sqlite3`, backups, logs, temporary files,
  coverage output, secrets, or environment files.
- Demo data MUST be synthetic and generated by scripts.
- Treat changes to `.gitignore`, database fixtures, migrations, authentication,
  encryption, and backup formats as high-risk changes.
- Do not rewrite Git history, remove tracked databases, or rotate credentials
  unless the user explicitly requests it.
- Do not modify unrelated user changes in a dirty worktree.

## Documentation

Update documentation whenever a change affects:

- setup or startup commands
- environment variables
- supported account fields
- API or backup formats
- security guarantees
- user-visible workflows

Do not claim whole-database encryption, AES-256, offline behavior, automatic
tracking, or a passing test suite unless those claims have been verified.

## Definition of Done

A change is complete only when:

1. The requested behavior works through the relevant user or API workflow.
2. Focused tests pass and meaningful full-suite failures are reported.
3. Database mutations are atomic and preserve related history.
4. Authentication, privacy, and local-only guarantees are not weakened.
5. UI states and API error behavior are handled.
6. Documentation is updated when contracts or user behavior change.
7. No runtime data, secrets, logs, or generated artifacts are added to Git.
