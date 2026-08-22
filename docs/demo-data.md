# Demo Environment Guide

This guide explains how to run Networth Tracker with synthetic data in an
isolated local database.

## Overview

The demo tooling has two stages:

1. `scripts/generate_demo_database.py` creates a standalone SQLite source
   database containing synthetic data.
2. `scripts/create_demo_backup.py` converts that source database into an
   encrypted backup that the application's Import Data workflow can read.

The application does not import a raw `.db` file. Import the generated
`demo_backup.enc` file instead.

For isolation, keep both the generated files and the demo application's
database outside the repository. This prevents the demo workflow from changing
the tracked `networth.db` and `networth_demo.db` files.

## Generated Data

A fresh generation currently includes:

- 3 certificates of deposit
- 2 savings accounts
- 1 401(k) account
- 2 trading accounts with stock positions
- 2 I Bond accounts
- 2 health savings accounts
- 24 monthly value snapshots per account (288 total)

All generated accounts have the `is_demo` marker used by the dashboard's demo
filter and bulk-delete workflow. Values are synthetic and vary between runs.

The source database also contains a synthetic watchlist. The current
`create_demo_backup.py` converter does not include that watchlist in the
encrypted backup, so it will not appear after import.

## Prerequisites

- Python 3.10 or newer
- A repository virtual environment with dependencies installed

Create the virtual environment only if it does not already exist:

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt
```

## Create Demo Files

From the repository root:

```bash
DEMO_HOME="$HOME/.local/share/networth-tracker-demo"
mkdir -p "$DEMO_HOME"
chmod 700 "$DEMO_HOME"

./venv/bin/python scripts/generate_demo_database.py \
  "$DEMO_HOME/source.db" \
  demo123

./venv/bin/python scripts/create_demo_backup.py \
  "$DEMO_HOME/source.db" \
  "$DEMO_HOME/demo_backup.enc" \
  demo123

chmod 600 "$DEMO_HOME/source.db" "$DEMO_HOME/demo_backup.enc"
```

`demo123` is the demo backup password. It is separate from the master password
you create for the isolated application.

The generator deletes and recreates its destination file. Always pass an
explicit path as shown above. Running it without a path would overwrite the
tracked `networth_demo.db` file in the repository.

## Start an Isolated Application

Use an explicit `DATABASE_PATH` so the demo application cannot modify the
normal `networth.db` database:

```bash
DEMO_HOME="$HOME/.local/share/networth-tracker-demo"

FLASK_ENV=production \
DATABASE_PATH="$DEMO_HOME/app.db" \
./venv/bin/python scripts/start.py \
  --env production \
  --host 127.0.0.1 \
  --port 5001
```

The `production` setting here disables Flask's debug server behavior; the
application remains local because it is bound to `127.0.0.1`. The explicit
database path, rather than the environment name, provides the data isolation.

Open `http://127.0.0.1:5001`. On first use, create a master password with at
least 12 characters containing uppercase, lowercase, numeric, and special
characters.

## Import Demo Data

After initial setup:

1. Open **Import Data** from the application navigation.
2. Select
   `$HOME/.local/share/networth-tracker-demo/demo_backup.enc`.
3. Enter `demo123` in **Backup password**.
4. Leave **Overwrite existing accounts** clear for a fresh demo database.
5. Start the import and refresh the dashboard when it completes.

The imported accounts, positions, and historical value snapshots are
re-encrypted with the isolated application's master-password-derived key.

## Start the Demo Again

Always provide the same database path on later starts:

```bash
DATABASE_PATH="$HOME/.local/share/networth-tracker-demo/app.db" \
./venv/bin/python scripts/start.py --env production --port 5001
```

Omitting `DATABASE_PATH` in production mode selects the repository's default
`networth.db` file instead.

## Remove or Reset Demo Data

To remove imported demo accounts while the application is running, use the
dashboard's **Delete Demo Accounts** action. This removes accounts marked as
demo and their related account data.

To reset the entire isolated environment:

1. Stop the demo application.
2. Delete `$HOME/.local/share/networth-tracker-demo/app.db`.
3. Start the application with the isolated `DATABASE_PATH`.
4. Create a new master password and import `demo_backup.enc` again.

Regenerate `source.db` and `demo_backup.enc` only when you want a new randomized
demo dataset.

## Security Notes

- Demo records are synthetic, but the files use the same local encryption and
  database mechanisms as normal records.
- The raw SQLite source and encrypted backup should both remain owner-readable
  only.
- Do not reuse `demo123` as the application's master password. It does not meet
  the master-password strength requirements.
- Stock quote refreshes can contact configured market-price providers. Initial
  demo generation itself does not require those network calls.

## Troubleshooting

### The import cannot decrypt the file

Confirm that `demo123` was entered as the backup password. The application's
master password cannot decrypt the generated demo backup.

### The file picker does not show the SQLite file

This is expected. Convert `source.db` with `create_demo_backup.py` and select
`demo_backup.enc`.

### The application opens the wrong data

Stop it and restart with the explicit demo path:

```bash
DATABASE_PATH="$HOME/.local/share/networth-tracker-demo/app.db" \
./venv/bin/python scripts/start.py --env production --port 5001
```

### Demo accounts are missing

Check `logs/networth_tracker.log` for import errors, confirm that the dashboard
is not filtering out demo records, and rerun the import against a fresh
isolated application database if necessary.
