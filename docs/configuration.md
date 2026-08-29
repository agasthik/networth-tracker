# Configuration Reference

Configuration is defined in `config.py`. Values backed by environment
variables are read when that module is imported.

The application does not load `.env`, `.env.development`, or
`.env.production` files. Set variables in the shell, service manager, or
operating-system environment before starting Python.

## Environments

Choose an environment with `--env`:

| Environment | Debug | Default database | Configured cookie lifetime |
| --- | --- | --- | --- |
| `production` | off | `networth.db` | 2 hours |
| `development` | on | `networth_dev.db` | 8 hours |
| `testing` | on | `:memory:` or `TEST_DATABASE_PATH` | 30 minutes |

`production` means the non-debug local configuration. It does not turn Flask's
built-in server into a production WSGI server.

Development mode currently conflicts with startup PID handling when Flask's
reloader starts a child process. Use production mode for normal local use.

`AuthenticationManager` uses the configured cookie lifetime as its inactivity
timeout.

## Supported Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `FLASK_ENV` | `production` | Environment selected when `--env` is omitted |
| `DATABASE_PATH` | Environment-specific | Production or development SQLite path |
| `TEST_DATABASE_PATH` | `:memory:` | Testing SQLite path |
| `SECRET_KEY` | Random per process | Flask session-signing secret |
| `APP_MODE` | `production` | Stored in configuration; currently has no separate runtime workflow |
| `LOG_LEVEL` | `INFO` or `DEBUG` | Loaded into config but not passed to the application logger |
| `LOG_DIR` | `logs` | Created and permissioned, but not passed to the application logger |
| `LOG_FILE` | `networth_tracker.log` | Loaded but not used by the application logger |
| `ERROR_LOG_FILE` | `networth_tracker_errors.log` | Loaded but not used by the application logger |
| `MAX_LOG_SIZE` | `10485760` | Loaded but not passed to the application logger |
| `LOG_BACKUP_COUNT` | `5` | Loaded but not passed to the application logger |
| `BACKUP_DIR` | `backups` | Directory whose files receive backup permissions |
| `MAX_BACKUP_FILES` | `10` | Defined but not currently used for cleanup |
| `MAX_CONTENT_LENGTH` | `16777216` | Maximum total HTTP request size in bytes |
| `MAX_BACKUP_SIZE` | `10485760` | Maximum encrypted `.nwb` upload size in bytes |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed login attempts allowed per client address |
| `LOGIN_ATTEMPT_WINDOW` | `300` | Rolling login-attempt window in seconds |

`STOCK_API_RATE_LIMIT` and `STOCK_API_TIMEOUT` are present in `config.py`, but
current `StockPriceService` construction does not consume them. The effective
service defaults are a three-second delay and two retries; network-library
timeouts are set inside the service.

The effective application logger uses `DEBUG` only when application debug mode
is active; otherwise it uses `INFO`. It writes
`logs/networth_tracker.log` and `logs/networth_tracker_errors.log`, rotates at
10 MiB, and retains five backups. These values are currently fixed by
`setup_app_logging()`.

`DEBUG`, `SESSION_TIMEOUT`, and `SESSION_COOKIE_*` are not environment-backed
settings in the current configuration classes.

## Examples

Use a data file outside the repository:

```bash
mkdir -p "$HOME/.local/share/networth-tracker"
chmod 700 "$HOME/.local/share/networth-tracker"

DATABASE_PATH="$HOME/.local/share/networth-tracker/networth.db" \
./venv/bin/python scripts/start.py --env production
```

Set a stable session secret when a process will be restarted:

```bash
export SECRET_KEY='replace-with-at-least-32-random-characters'
./venv/bin/python scripts/start.py --env production
```

The secret signs browser sessions; it is separate from the master password and
database encryption key.

## Startup Options

Supported options can be listed with:

```bash
./venv/bin/python scripts/start.py --help
```

Common working commands:

```bash
./venv/bin/python scripts/start.py --env production
./venv/bin/python scripts/start.py --env production --port 5001
./venv/bin/python scripts/start.py --validate-only
./venv/bin/python scripts/start.py --create-dirs
./venv/bin/python scripts/start.py --status
./venv/bin/python scripts/start.py --stop
```

Keep `--host 127.0.0.1`. Do not use `--daemon` for managed operation: its
current PID and working-directory handling is unreliable. Use a local service
manager and foreground mode instead.

Restart uses the arguments and environment supplied to the restart command; it
does not remember the previous process configuration.

## File and Directory Permissions

On Unix-like systems, application configuration attempts to set:

| Resource | Mode |
| --- | --- |
| Database, log, backup, and temporary files | `0600` |
| Data, log, backup, and temporary directories | `0700` |

The Unix `start.sh` wrapper also applies its own permissions before startup and
currently creates `logs/` as `0755`; `config.py` tightens configured sensitive
directories during application initialization.

## Validation

`--validate-only` checks:

- Whether configured log and backup directories exist
- Existing database file mode on Unix-like systems
- A minimum 32-character `SECRET_KEY`
- Whether `MAX_LOG_SIZE` is at least 1 MiB

It does not open the database, verify its schema, test quote providers, or
validate every configured path.
