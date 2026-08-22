# Demo Database Generator

`generate_demo_database.py` creates a standalone SQLite source database with
synthetic financial data. The source database is not directly importable by
the web application. Convert it to an encrypted backup with
`create_demo_backup.py` before using **Import Data**.

See [Demo Environment Guide](../docs/demo-data.md) for the complete isolated
setup workflow.

## Usage

Use the repository virtual environment and pass an explicit destination:

```bash
DEMO_HOME="$HOME/.local/share/networth-tracker-demo"
mkdir -p "$DEMO_HOME"

./venv/bin/python scripts/generate_demo_database.py \
  "$DEMO_HOME/source.db" \
  demo123
```

Arguments are positional:

```text
generate_demo_database.py [database_path] [encryption_password]
```

The defaults are `networth_demo.db` and `demo123`. The generator removes an
existing destination before creating the new database, so using the default
path from the repository root would overwrite the tracked
`networth_demo.db`. Use a separate explicit path.

## Generated Data

The current generator creates:

- 12 accounts: 3 CDs, 2 savings, 1 401(k), 2 trading, 2 I Bonds, and 2 HSAs
- 24 monthly value snapshots per account (288 total)
- Stock positions for the trading accounts
- 12 synthetic watchlist entries
- `is_demo` markers on generated accounts and watchlist entries

Values and institutions are selected from synthetic generation rules and vary
between runs.

## Encryption

The generator encrypts selected database payloads using the supplied password
and a fixed demo salt. The default `demo123` value is a backup-conversion
password, not an application master password.

The generated database does not contain the authentication hash and salt
required for normal application login. Do not point `DATABASE_PATH` directly
at this source database.

## Convert for Import

Convert the source database into the format consumed by `/api/import`:

```bash
./venv/bin/python scripts/create_demo_backup.py \
  "$DEMO_HOME/source.db" \
  "$DEMO_HOME/demo_backup.enc" \
  demo123

chmod 600 "$DEMO_HOME/source.db" "$DEMO_HOME/demo_backup.enc"
```

In the application, select `demo_backup.enc` and enter `demo123` as the backup
password.

The current converter includes accounts, stock positions, historical
snapshots, and demo settings. It does not include the generated watchlist.
