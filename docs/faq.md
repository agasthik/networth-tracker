# Frequently Asked Questions

## What does Networth Tracker do?

It records CDs, savings accounts, 401(k) accounts, trading accounts, I Bonds,
HSAs, trading positions, historical account values, and a stock watchlist.

It does not connect to banks or automatically discover balances. Values are
entered manually, except that stock prices can be refreshed from a market-data
provider.

## What are the requirements?

- Python 3.10 or newer
- A modern browser
- Local disk space for the application and database
- Internet access only for dependency installation and stock quote refreshes

See the [Installation Guide](installation.md).

## Where is my data?

Data is stored in the SQLite file selected by `DATABASE_PATH`. If that variable
is unset, production mode uses `networth.db` in the working directory.

Use an absolute, private path outside the repository for normal data.

## Is the database encrypted?

Not as a whole. Selected account payloads, watchlist payloads, and historical
metadata are encrypted with Fernet. Account names and institutions, trading
positions, historical values and timestamps, stock symbols, and database
structure remain plaintext.

Fernet uses AES-128-CBC with HMAC-SHA256. Claims that the application uses
AES-256 or whole-database encryption are incorrect. See the
[Security Guide](security.md).

## What leaves my computer?

Stock symbols may be sent to yfinance/Yahoo Finance providers when quotes are
refreshed. Account names, balances, quantities, purchase prices, and the master
password are not intentionally sent.

The application is otherwise local, but installed dependencies and the host
operating system remain part of the security boundary.

## Can I expose it to my network?

No supported deployment does that. Keep the host at `127.0.0.1`. The
application uses Flask's built-in server and lacks controls expected from an
internet-facing financial service.

## What are the password requirements?

At least 12 characters with uppercase, lowercase, digit, and a supported
special character. The policy is fixed in code.

## What if I forget the master password?

There is no recovery or reset mechanism. A normal web export does not help
because it does not contain the database salt needed to recreate its encryption
key.

Restore a full copy of the original SQLite database and use its original
password, or start with a new database and lose access to the old encrypted
payloads.

## Does logout erase the encryption key from memory?

No. Logout clears the Flask session and closes the database service, but the
process retains its `EncryptionService` object. Stop the application when
finished on an untrusted machine.

## How are sessions protected?

Sessions expire after two hours of inactivity and use `HttpOnly` and
`SameSite=Lax` cookies. HTTPS-only cookies are disabled for the local HTTP URL.

The current application does not restrict concurrent sessions, rate-limit
login attempts, or use CSRF tokens.

## Which currencies are supported?

The application treats all money as one implicit currency and performs no
conversion. Enter all values in the same currency.

## How are historical changes calculated?

Snapshots are created on initial entry, meaningful account value changes, and
successful stock-price updates. They are sparse and event-driven.

Displayed changes compare stored values. They are not investment returns
because contributions, withdrawals, transfers, fees, and income are not
separated from market gains.

## Are stock prices real time?

No guarantee is made. Quotes come from external providers and may be delayed,
stale, rate-limited, or unavailable. Check the displayed update time. The
default service waits three seconds between requests and retries twice.

## Can I export selected accounts or date ranges?

No. The UI exports one encrypted file containing all accounts, positions,
watchlist records, and historical data. It does not expose account-type,
date-range, or multiple-format selection.

## Can I restore an export on another computer?

Not reliably. Normal exports use the current database-derived key and omit its
salt. The password field in the import dialog is implemented for generated demo
backups using their fixed demo salt.

For migration, stop the application and copy the complete SQLite database, then
start the destination with that file and the original password.

## How do I make a recoverable backup?

Stop the application and copy the entire configured database:

```bash
./venv/bin/python scripts/start.py --stop
install -m 600 "$DATABASE_PATH" "/secure/backup/networth.db"
```

On Windows, stop the process and use `copy` while the database is closed.
Periodically test the copied file with a separate `DATABASE_PATH`.

## How do imports handle duplicates?

Identity is based on record IDs. Existing account IDs are skipped unless
Overwrite existing accounts is selected. Import merges data and does not
automatically identify semantic duplicates based on account name or
institution.

## How do I use demo data?

Follow the [Demo Environment Guide](demo-data.md). It creates synthetic data,
converts it to an encrypted import file, and runs the application against a
separate database.

## Why is development mode failing to start?

Flask's debug reloader currently conflicts with the startup script's PID-file
check. Use `--env production` for local operation until PID/reloader handling is
fixed.

## Where are logs?

By default:

- `logs/networth_tracker.log`
- `logs/networth_tracker_errors.log`

Although `config.py` reads logging environment variables, the current
application logger ignores them and uses these fixed repository paths.

## Where can I get more help?

- [Troubleshooting](troubleshooting.md)
- [Configuration Reference](configuration.md)
- [Security Guide](security.md)
- [User Guide](user-guide.md)
