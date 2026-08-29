# User Guide

Networth Tracker is a local, single-user application for recording account
values, trading positions, sparse historical snapshots, and a stock watchlist.

## Sign In

On the first visit, create a master password with at least 12 characters,
uppercase, lowercase, numeric, and special characters. There is no password
recovery.

Later visits require that password. Sessions expire after two hours of
inactivity. Use Logout when finished.

## Dashboard

The dashboard contains:

- A summary with total value, allocation, and value-change information
- Separate tabs for CDs, Savings, 401(k), Trading, I Bonds, and HSA accounts
- Actions to add, view, edit, and delete accounts
- Import and export actions
- Demo-account filtering and deletion when demo records exist
- A link to the stock watchlist

All currency figures use one implicit currency. The application does not label
or convert currencies, so use one currency consistently.

## Account Types

Every account has a name and institution. Account-specific fields are:

| Type | Fields |
| --- | --- |
| CD | Principal, current value, annual interest rate, future maturity date |
| Savings | Current balance, annual interest rate, optional account number |
| 401(k) | Current balance, employer-match percentage, contribution limit, employer contribution, optional vesting fields |
| Trading | Broker, cash balance, optional account type and account number, stock positions |
| I Bonds | Purchase amount/date, fixed rate, inflation rate, current value, calculated maturity date |
| HSA | Current balance, annual contribution limit, current-year and employer contributions, investment balance, cash balance |

HSA cash plus investment balances must equal the current balance within one
cent. Current-year contributions cannot exceed the configured annual limit.

The CD and savings forms display client-side interest projections. These are
form aids, not automatic balance updates. The I Bond form also displays an
approximate projection and calculates a 30-year maturity date; enter the actual
current value from the authoritative source.

## Add, Edit, and Delete

1. Select an account type tab.
2. Choose Add Account.
3. Complete the required fields and save.
4. Use the account card actions to view, edit, or delete it.

Deleting an account also deletes its related historical snapshots and trading
positions. Deletion cannot be undone except by restoring a full database
backup.

## Trading Positions

A position records symbol, share quantity, purchase price, purchase date,
current price, and last price-update time. Current value uses the latest price
when present and otherwise falls back to purchase price.

Price refreshes contact the market-data provider. The service waits three
seconds between requests by default and retries failures up to two times.
Provider failures can leave the last known price in place; check its update
time before relying on it.

Stock symbols and position fields are stored in plaintext SQLite columns. See
the [Security Guide](security.md).

## Watchlist

Open Watchlist from the navigation to:

- Add a symbol with optional notes
- View cached price and daily change data
- Refresh watchlist prices
- Remove a symbol

Watchlist entries do not create trading positions or affect net worth.

## Historical Values

Snapshots are event-driven:

- Account creation records an initial value.
- An account update records a snapshot when its value changes by at least one
  cent.
- Successful trading-price updates can record a stock-price snapshot.
- Imported snapshots retain their imported timestamp.

This produces sparse data, not guaranteed daily observations. The application
can show absolute and percentage value changes, averages, minima, maxima,
standard deviation, and a linear trend over available snapshots.

Raw absolute and percentage values are net-worth changes. Account updates can
also identify contributions, withdrawals, transfers, fees, and income with a
cash-flow amount; those labeled events produce an additional flow-adjusted gain
and return. The application does not calculate money-weighted, time-weighted,
or annualized returns.

## Export and Import

### Export

Export Data downloads one encrypted backup containing accounts, trading
positions, watchlist records, and historical snapshots. The UI does not offer
account-type or date-range selection.

The downloaded encrypted backup uses the `.nwb` extension.

### Import

Import Data accepts an encrypted backup and can overwrite records with matching
IDs when that option is selected. Without overwrite, records with existing IDs
are skipped. Import is a merge operation; it does not clear unrelated records.
The operation is all-or-nothing: validation or persistence failure rolls back
every record from that import. Successful restores preserve original IDs,
timestamps, relationships, position and snapshot identity, and demo markers.

`.nwb` and legacy `.enc` files are accepted. The default backup upload limit is
10 MiB.

Leave Backup password empty when reimporting a normal export into the same
authenticated database. Enter `demo123` only for a backup generated by the demo
scripts.

### Recovery limitation

Normal exports are encrypted with the current session key but do not contain
the source database salt. They are not portable disaster-recovery backups and
cannot recover a lost master password or lost database.

For recoverable backup and migration, stop the application and copy the entire
SQLite database. Read [Backups and Recovery](security.md#backups-and-recovery)
before relying on either workflow.

## Demo Data

Use the [Demo Environment Guide](demo-data.md) to generate an encrypted demo
backup and import it into a separate database. Demo accounts have a visible
marker, can be filtered, and can be deleted together from the dashboard.

Do not mix synthetic and real records unless that is intentional.

## Keyboard Shortcuts

On the dashboard:

| Shortcut | Action |
| --- | --- |
| `Ctrl+R` or `Cmd+R` | Refresh net-worth data |
| `Ctrl+E` or `Cmd+E` | Export data |
| `Ctrl+I` or `Cmd+I` | Open Import Data |
| `Escape` | Close open Bootstrap modals |

The application does not implement shortcuts for saving a form or adding an
account.

## Data Safety

- Keep the server on `127.0.0.1`.
- Use a private database path outside the source checkout.
- Protect the device with full-disk encryption.
- Stop the application before copying its SQLite database.
- Do not assume the SQLite file is wholly encrypted.
- Verify price timestamps and historical coverage before interpreting changes.
