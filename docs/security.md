# Security Guide

This document describes the controls implemented by the current application and
their limits. Networth Tracker is intended to run as a single-user application
on a trusted computer and bind only to `127.0.0.1`.

## Security Model

The application reduces exposure by storing data locally, requiring a master
password, encrypting selected record payloads, and restricting sensitive files
on Unix-like systems. It is not a hardened multi-user service, an encrypted
database product, or a substitute for full-disk encryption.

Do not bind the server to a public or LAN interface. The application currently
uses Flask's built-in server and does not implement the controls required for an
internet-facing financial application.

## Encryption

`EncryptionService` derives a Fernet key from the master password and a random
16-byte database salt using PBKDF2-HMAC-SHA256 with 100,000 iterations. Fernet
uses AES-128-CBC for confidentiality and HMAC-SHA256 for authentication.

The iteration count is fixed in the implementation. It is not configurable.

### Encrypted fields

- Account-type-specific payload fields, including balances and account-specific
  settings
- Watchlist payload fields such as notes and cached price details
- Historical snapshot metadata
- Export payloads created by the Export Data action

### Plaintext SQLite fields

- Account IDs, names, institutions, types, timestamps, schema versions, and
  demo markers
- Stock symbols, share quantities, purchase prices, purchase dates, current
  prices, and update timestamps
- Historical account IDs, timestamps, values, and change types
- Watchlist IDs, symbols, dates, and demo markers
- The password salt and salted password-verification hash
- Database schema, indexes, and row counts

The SQLite file itself is not encrypted. Someone who can read it can inspect
the plaintext fields and encrypted blobs. Use operating-system full-disk
encryption if whole-file protection is required.

## Master Password

Initial setup requires at least 12 characters and at least one uppercase
letter, lowercase letter, digit, and character from:

```text
!@#$%^&*()_+-=[]{}|;:,.<>?
```

There is no password recovery or reset workflow. The password is not stored,
but the database stores a random salt and a PBKDF2-HMAC-SHA256 verification
hash using 600,000 iterations. The same database salt is used to derive the
Fernet key. Legacy salted SHA-256 verifier records are upgraded after a
successful login.

Secret verification uses constant-time comparison.

Logout clears the browser session, closes the active database service, and
drops the application's references to the derived key, salt, and Fernet
object. Python does not guarantee physical memory zeroization, so stop the
process when finished on a shared or untrusted computer.

## Sessions and Browser Requests

- Sessions expire after two hours of inactivity.
- Session cookies are `HttpOnly` and `SameSite=Lax`.
- `Secure` is false because the supported local URL uses HTTP.
- State-changing requests require a session CSRF token and reject a mismatched
  `Origin` or `Referer` when the browser supplies one.
- Login failures are limited to five attempts per client address in a rolling
  five-minute in-process window.
- Backup uploads require the `.nwb` extension (or legacy `.enc`) and are limited
  to 10 MiB. The global request limit is 16 MiB by default.
- Logout clears the Flask session and active key references.

Current limitations:

- Concurrent sessions are not restricted.
- Login throttling is process-local and resets when the application restarts.

Keep the application bound to `127.0.0.1`, do not browse untrusted sites while
an authenticated session is open, and log out when finished.

## External Network Calls

Stock quote refreshes use `StockPriceService` and may contact yfinance/Yahoo
Finance providers. Requests identify stock symbols. Account names, quantities,
balances, purchase prices, and the master password are not intentionally sent
to quote providers.

The application is usable without quote refreshes, but cached prices can become
stale when the network or provider is unavailable.

## File Permissions

On Unix-like systems, configuration initialization attempts to apply:

| Resource | Mode |
| --- | --- |
| Database, backup, log, and temporary files | `0600` |
| `data/`, `backups/`, `logs/`, and `temp/` directories | `0700` |

Windows permissions are managed by Windows ACLs; the application does not
change them.

Verify permissions when data is stored outside the repository:

```bash
chmod 700 /path/to/networth-data
chmod 600 /path/to/networth-data/*.db
```

## Backups and Recovery

The web Export Data action encrypts its output with the key active in the
current session. The export does not contain the database salt needed to derive
that key on a new database.

Consequences:

- An export can be imported back into the same database while authenticated
  with the same key.
- A normal export is not currently a standalone disaster-recovery or
  cross-computer backup.
- Entering a backup password in the import dialog supports generated demo
  backups, which use a fixed demo salt. It does not reconstruct the key for a
  normal export.
- An export cannot recover data after the master password or original database
  salt is lost.
- Imports are transactional. Any invalid account, holding, watchlist item,
  snapshot, relationship, or setting rolls back the complete import.
- Successful restores preserve record IDs, account and watchlist timestamps,
  position IDs, snapshot IDs, snapshot timestamps, relationships, and demo
  markers.

For recoverable backups, stop the application and copy the entire SQLite
database file. That file contains the salt, password-verification data, and
encrypted records:

```bash
./venv/bin/python scripts/start.py --stop
cp /path/to/networth.db /secure/backup/networth-$(date +%Y%m%d-%H%M%S).db
chmod 600 /secure/backup/networth-*.db
```

Do not copy a live database. Test recovery with a separate `DATABASE_PATH`
before relying on a backup.

## Logs

Logs may include operation names, IDs, errors, paths, and request information.
The `log_function_call` helper redacts argument values when their key names
contain `password`, `key`, `token`, or `secret`; arbitrary log messages are not
automatically scrubbed.

Do not add logs containing passwords, keys, decrypted payloads, account
numbers, or backup contents.

## Threats and Limits

The design helps against casual inspection of selected payload fields and
reduces remote exposure through localhost binding. It does not protect against:

- Malware, keyloggers, debuggers, or an attacker controlling the running user
  account
- Memory inspection while the process is authenticated
- Plaintext-field disclosure from a copied SQLite file
- Compromise caused by exposing the built-in server to a network
- Loss of the database and salt when only normal export files remain

No GDPR, CCPA, PIPEDA, OWASP, or other compliance certification is claimed.
