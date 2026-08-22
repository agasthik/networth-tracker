# Scripts Reference

Run scripts from the repository root. After setup, invoke Python through the
repository virtual environment.

## `start.py`

Primary startup and process-control script:

```bash
./venv/bin/python scripts/start.py --help
```

Common commands:

```bash
./venv/bin/python scripts/start.py --env production
./venv/bin/python scripts/start.py --env production --port 5001
./venv/bin/python scripts/start.py --validate-only
./venv/bin/python scripts/start.py --create-dirs
./venv/bin/python scripts/start.py --status
./venv/bin/python scripts/start.py --stop
./venv/bin/python scripts/start.py --restart --env production
```

Important behavior:

- Default host is `127.0.0.1`; keep it local.
- Default environment is `production`.
- The PID file defaults to `networth_tracker.pid`.
- Restart uses options and environment supplied to that invocation. It does not
  recover the previous command line.
- Development/debug mode currently conflicts with PID handling when Flask's
  reloader starts a child process.
- Daemon mode currently has unreliable PID cleanup and changes its working
  directory to `/`; use foreground mode under a service manager instead.
- Configuration validation does not test database connectivity or schema.

## `start.sh`

Unix-like wrapper that checks Python 3.10+, creates or repairs `venv`, installs
requirements when Flask is absent, sets selected permissions, and delegates to
`start.py`.

```bash
./scripts/start.sh
./scripts/start.sh -p 5001
./scripts/start.sh --status
./scripts/start.sh --stop
./scripts/start.sh --restart -e production
```

The wrapper defaults to production regardless of an existing `FLASK_ENV`
unless `-e`/`--env` is supplied. Environment variables such as
`DATABASE_PATH` are otherwise inherited.

Avoid `-d`/`--daemon` and development/debug mode for the limitations described
above.

## `start.bat`

Windows wrapper with similar environment setup and process controls:

```cmd
scripts\start.bat
scripts\start.bat -p 5001
scripts\start.bat --status
scripts\start.bat --stop
scripts\start.bat --restart -e production
```

Windows stop uses `taskkill /T /F`; it is forced termination, not a graceful
SIGTERM workflow.

## `generate_demo_database.py`

Creates a raw SQLite source database containing randomized synthetic accounts,
positions, historical snapshots, and watchlist records.

The script has positional arguments rather than an argparse `--help` interface:

```bash
./venv/bin/python scripts/generate_demo_database.py \
  /private/demo/source.db \
  demo123
```

If no path is supplied, it overwrites `networth_demo.db`. Always provide an
isolated destination path. The generated raw database is not accepted by the
web import form.

## `create_demo_backup.py`

Converts the raw demo database to the encrypted format accepted by Import Data:

```bash
./venv/bin/python scripts/create_demo_backup.py \
  /private/demo/source.db \
  /private/demo/demo_backup.enc \
  demo123
```

The converter includes demo accounts, positions, and historical snapshots. It
does not currently include the generated watchlist.

See [Demo Environment Guide](../demo-data.md).

## `init_db.py`

Do not use its database-management operations with the current application.
The script still parses `--create`, `--migrate`, `--verify`, `--reset`,
`--backup`, and `--demo`, but most operations call obsolete
`DatabaseService`/migration APIs, and `--demo` references an undefined
configuration value. It has no `--restore` option.

Normal schema creation occurs during master-password setup. Migrations run when
the encrypted database service connects.

For recoverable backup, stop the application and copy the entire configured
SQLite file as described in the [Security Guide](../security.md).

## Environment Configuration

Scripts inherit environment variables from the process. The repository does
not load `.env.*` files.

```bash
DATABASE_PATH=/absolute/private/path/networth.db \
./venv/bin/python scripts/start.py --env production
```

See [Configuration Reference](../configuration.md).

## Tests

Tests must use their temporary or in-memory fixtures, never repository database
files:

```bash
./venv/bin/python -m pytest -q
./venv/bin/python -m pytest tests/test_accounts.py -q
./venv/bin/python -m pytest tests/test_account_api.py -q
./venv/bin/python -m pytest --cov=services --cov=models
```
