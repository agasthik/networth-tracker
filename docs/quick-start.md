# Quick Start

Requirements: Python 3.10 or newer and internet access only when refreshing
market prices.

## macOS or Linux

```bash
python3 -m venv venv
./venv/bin/python -m pip install -r requirements.txt

mkdir -p "$HOME/.local/share/networth-tracker"
chmod 700 "$HOME/.local/share/networth-tracker"

DATABASE_PATH="$HOME/.local/share/networth-tracker/networth.db" \
./venv/bin/python scripts/start.py --env production
```

## Windows

```cmd
python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt
mkdir "%LOCALAPPDATA%\NetworthTracker"
set "DATABASE_PATH=%LOCALAPPDATA%\NetworthTracker\networth.db"
venv\Scripts\python.exe scripts\start.py --env production
```

Open `http://127.0.0.1:5000`.

On first use, create a password with at least 12 characters, uppercase,
lowercase, numeric, and special characters. The application creates the
database schema automatically.

The SQLite file uses field-level encryption, not whole-file encryption. Keep
the file private and use operating-system full-disk encryption where needed.
See [Security Guide](security.md).

## Next Steps

1. Add an account from the dashboard.
2. Open Watchlist to track symbols without adding positions.
3. Follow the [Demo Environment Guide](demo-data.md) for isolated synthetic
   data.
4. Read the [Backup and Recovery](security.md#backups-and-recovery) limitations
   before relying on exported files.

Stop the application with:

```bash
./venv/bin/python scripts/start.py --stop
```
