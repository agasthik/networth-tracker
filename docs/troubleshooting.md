# Troubleshooting

Run commands from the repository root and use the repository virtual
environment.

## Installation Problems

Check Python and recreate the environment if needed:

```bash
python3 --version
./venv/bin/python --version
./venv/bin/python -m pip install -r requirements.txt
```

Python 3.10 or newer is required. On Windows, use
`venv\Scripts\python.exe`.

If `venv` was copied from another machine or moved with the project, recreate
it. Python virtual environments are not generally portable.

## Application Does Not Start

Validate the limited configuration checks:

```bash
./venv/bin/python scripts/start.py --validate-only
```

Then start in non-debug mode:

```bash
./venv/bin/python scripts/start.py --env production
```

Development/debug mode can fail because Flask's reloader starts another process
that collides with PID-file detection.

### Stale PID file

Check status:

```bash
./venv/bin/python scripts/start.py --status
```

If no process with the recorded PID exists, the status command removes the
stale file. Verify the process before manually removing
`networth_tracker.pid`; never terminate an unrelated process based only on a
stale PID file.

### Port already in use

Use another local port:

```bash
./venv/bin/python scripts/start.py --env production --port 5001
```

Or identify the listener:

```bash
lsof -nP -iTCP:5000 -sTCP:LISTEN
```

On Windows:

```cmd
netstat -ano | findstr :5000
```

## Browser Cannot Connect

Confirm the process is running and open the exact HTTP URL:

```text
http://127.0.0.1:5000
```

Test the health route:

```bash
curl --fail http://127.0.0.1:5000/health
```

Do not switch to `https://`, `0.0.0.0`, or a LAN address.

## Wrong or Empty Database

The application uses the `DATABASE_PATH` present when Python starts. Confirm
the value in the same shell:

```bash
printf '%s\n' "$DATABASE_PATH"
```

If unset, production mode uses `networth.db` in the current working directory.
Always use the same absolute path on later starts.

The application does not load `.env` files. Export the variable in the shell or
configure it in the service manager.

## Cannot Log In

Check keyboard layout, Caps Lock, and the selected database path. Passwords
belong to a particular database because its random salt is used for password
verification and key derivation.

There is no password reset or recovery. A normal exported `.enc` file cannot
recover a forgotten password. Restore a complete database backup and use its
original password, or start with a new database.

## Session Expires

The authentication manager enforces two hours of inactivity. Development
configuration declares eight hours, but the current authentication manager
still initializes its own two-hour timeout, so do not rely on the longer
configuration value.

Frequent immediate redirects usually indicate the process restarted with a new
random `SECRET_KEY`. Set a stable value of at least 32 random characters before
startup.

## Account Validation Errors

Common constraints include:

- CD principal must be positive and maturity must be in the future.
- Savings, retirement, trading, and HSA balances cannot be negative.
- Trading positions require a symbol, positive shares and purchase price, and a
  purchase date that is not in the future.
- HSA cash plus investment balance must equal current balance within one cent.
- HSA current-year contributions cannot exceed the annual limit.

Dates sent through forms and APIs use `YYYY-MM-DD`.

## Stock Prices Do Not Refresh

Quote refresh requires network access and a responsive market-data provider.
The effective `StockPriceService` defaults are:

- Three seconds between requests
- Two retries

`STOCK_API_RATE_LIMIT` and `STOCK_API_TIMEOUT` in `config.py` are not currently
passed to service instances. Changing those environment variables does not
change the effective service defaults.

Provider failure can leave a prior price displayed. Check the last-update time
and application logs rather than assuming a successful refresh.

## Export or Import Fails

The browser export is encrypted with the current session key. Reimport a normal
export into the same database while authenticated and leave Backup password
empty.

The Backup password field is for generated demo backups. Use `demo123` for the
file produced by `scripts/create_demo_backup.py`.

The UI downloads `.enc`; the API response uses `.nwb`. The file contents use
the same format, but the browser file picker currently advertises `.enc`.

Normal exports omit the database salt and are not portable disaster-recovery
backups. See [Security Guide](security.md#backups-and-recovery).

## Database Errors

First stop the application:

```bash
./venv/bin/python scripts/start.py --stop
```

Preserve the file before attempting repair:

```bash
install -m 600 "$DATABASE_PATH" "$DATABASE_PATH.before-repair"
```

If SQLite is installed, inspect a stopped copy:

```bash
sqlite3 "$DATABASE_PATH.before-repair" "PRAGMA integrity_check;"
```

Do not run tests, `VACUUM`, recovery tools, or ad hoc writes against repository
database files or the only copy of user data.

`scripts/init_db.py --create`, `--migrate`, `--verify`, `--reset`, and `--demo`
are incompatible with the current database service. There is no `--restore`
option. Schema setup and migrations normally run when an authenticated
database service connects.

## Demo Data Problems

Import `demo_backup.enc`, not the raw generated `.db` file. Enter `demo123` as
the backup password and ensure the application uses the isolated
`DATABASE_PATH` described in [Demo Environment Guide](demo-data.md).

The current converter omits generated watchlist entries, so an empty watchlist
after demo import is expected.

## Logs

Default files:

```text
logs/networth_tracker.log
logs/networth_tracker_errors.log
```

Search without posting sensitive contents:

```bash
rg -n "ERROR|CRITICAL|migration|traceback" logs/
```

Logs are not universally scrubbed. Remove passwords, keys, account data, paths,
and backup contents before sharing excerpts.

## Platform Notes

### Windows

Use Windows paths and `venv\Scripts\python.exe`. The Windows stop command uses
`taskkill /F`, so stop the application before copying data.

### macOS

Do not globally disable Gatekeeper. If a downloaded checkout has quarantine
metadata, inspect it and remove quarantine only from files you trust:

```bash
xattr -l /path/to/networth-tracker
```

### Linux

Keep data under a user-owned private directory. If a service manager is used,
confirm that its user, working directory, environment, and file permissions
match the interactive setup.

## Collecting Diagnostics

Useful non-sensitive details include:

```bash
./venv/bin/python --version
./venv/bin/python -m pip show Flask cryptography yfinance
./venv/bin/python scripts/start.py --validate-only
```

Do not attach database files, encrypted exports, secrets, or unredacted logs to
an issue.
