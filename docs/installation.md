# Installation Guide

Networth Tracker requires Python 3.10 or newer. It is a local Flask application
and should remain bound to `127.0.0.1`.

## Install

From the repository root, create the virtual environment only when it does not
already exist:

### macOS or Linux

```bash
python3 --version
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

### Windows

```cmd
python --version
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
```

The startup wrappers can create the virtual environment and install missing
requirements, but an explicit installation makes failures easier to diagnose.

## Choose a Database Location

The configuration default is a repository-root `networth.db`. For normal use,
select a private location outside the checkout.

### macOS or Linux

```bash
mkdir -p "$HOME/.local/share/networth-tracker"
chmod 700 "$HOME/.local/share/networth-tracker"
export DATABASE_PATH="$HOME/.local/share/networth-tracker/networth.db"
```

### Windows

```cmd
mkdir "%LOCALAPPDATA%\NetworthTracker"
set "DATABASE_PATH=%LOCALAPPDATA%\NetworthTracker\networth.db"
```

Set `DATABASE_PATH` again in each new shell or configure it in your local
service manager. The application does not load `.env` files.

## Start

### macOS or Linux

```bash
./venv/bin/python scripts/start.py --env production
```

### Windows

```cmd
venv\Scripts\python.exe scripts\start.py --env production
```

Open `http://127.0.0.1:5000`.

The application creates its schema during initial master-password setup and
runs schema migrations when the encrypted database service connects. Do not
use `scripts/init_db.py`; its create, migrate, verify, reset, and demo
operations are not compatible with the current `DatabaseService` API.

## Initial Setup

Create a master password containing:

- At least 12 characters
- An uppercase letter
- A lowercase letter
- A digit
- A special character from `!@#$%^&*()_+-=[]{}|;:,.<>?`

There is no password recovery. Preserve a stopped copy of the complete database
file in a secure backup location.

## Stop and Check Status

Use the same PID-file location and working directory used for startup:

```bash
./venv/bin/python scripts/start.py --status
./venv/bin/python scripts/start.py --stop
```

On Windows, `--stop` uses forced process termination. On Unix-like systems it
first sends `SIGTERM` and waits up to 30 seconds.

## Configuration

Set environment variables before starting:

```bash
export DATABASE_PATH="$HOME/.local/share/networth-tracker/networth.db"
export SECRET_KEY='replace-with-at-least-32-random-characters'
./venv/bin/python scripts/start.py --env production
```

See [Configuration Reference](configuration.md) for implemented variables and
known limitations. In particular, current logging environment variables are not
passed to the application logger.

## Verify the Installation

With the application running:

```bash
curl http://127.0.0.1:5000/health
```

Expected response:

```json
{"status":"healthy","version":"1.0.0"}
```

Then log in, create a temporary account, edit it, and delete it. Review
`logs/networth_tracker.log` if the workflow fails.

## Demo Environment

Do not generate or import demo data into the database used for real records.
Follow the [Demo Environment Guide](demo-data.md) to create a separate database
and import the generated encrypted demo backup.

## Upgrading

1. Stop the application.
2. Copy the complete SQLite database to a secure backup location.
3. Update the source checkout.
4. Refresh dependencies:

   ```bash
   ./venv/bin/python -m pip install -r requirements.txt
   ```

5. Start with the same `DATABASE_PATH`.

Migrations run when the database opens. Check logs for migration errors before
making additional changes.

## Uninstall

Stop the process, remove the source checkout and virtual environment, and
remove the configured data directory only after confirming that retained
backups are usable.

The master database, logs, and generated exports can contain sensitive
information. Delete them according to the storage device and operating system's
secure-erasure capabilities.
