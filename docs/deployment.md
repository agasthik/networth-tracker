# Deployment Guide

Networth Tracker is designed for one user on one trusted computer. The
supported network boundary is `127.0.0.1`; do not expose it to a LAN or the
internet.

The `production` configuration disables Flask debug mode. It still uses
Flask's built-in server and is not a hardened production WSGI deployment.

## Local Deployment

Install dependencies and choose a private data location as described in the
[Installation Guide](installation.md). Start in foreground mode:

```bash
export DATABASE_PATH="$HOME/.local/share/networth-tracker/networth.db"
export SECRET_KEY='replace-with-at-least-32-random-characters'
./venv/bin/python scripts/start.py \
  --env production \
  --host 127.0.0.1 \
  --port 5000
```

Do not use `--daemon`: its current PID-file and working-directory behavior is
unreliable. A local service manager may supervise the foreground command, but
the binding must remain `127.0.0.1`.

## Service-Manager Requirements

When defining a user-level service:

- Set the working directory to the repository root.
- Run `venv/bin/python scripts/start.py --env production`.
- Set an absolute `DATABASE_PATH`.
- Set a stable `SECRET_KEY` of at least 32 random characters.
- Restrict the service account and data directory to the local user.
- Keep the host at `127.0.0.1`.
- Use the service manager for stop/restart rather than `--daemon`.

The repository does not include a supported systemd, launchd, NSSM, Docker, or
reverse-proxy definition. Validate any locally created service definition
before relying on it.

## Environment

The application reads environment variables from the process environment. It
does not load `.env.production`.

Common variables:

```bash
DATABASE_PATH=/absolute/private/path/networth.db
SECRET_KEY=replace-with-at-least-32-random-characters
```

See [Configuration Reference](configuration.md) for effective settings. Some
defined values, including logging, stock timeout/rate, and backup retention
settings, are not wired into their services.

## Health Check

```bash
curl --fail http://127.0.0.1:5000/health
```

Response:

```json
{"status":"healthy","version":"1.0.0"}
```

The endpoint does not verify authentication, database readability, quote
providers, free disk space, or migration success.

## Logging

The application logger currently writes fixed rotating files under the
repository's `logs/` directory. Review:

```bash
tail -f logs/networth_tracker.log
tail -f logs/networth_tracker_errors.log
```

There are no shipped `monitor.py`, `rotate_logs.py`, or scheduled backup jobs.
Create external monitoring only after defining its dependencies, permissions,
and failure handling.

## Backups

For a recoverable backup:

1. Stop the process through its service manager or startup command.
2. Copy the complete SQLite file.
3. Restrict the copy to owner read/write.
4. Test it using a separate absolute `DATABASE_PATH`.

```bash
./venv/bin/python scripts/start.py --stop
install -m 600 \
  "$DATABASE_PATH" \
  "/secure/backup/networth-$(date +%Y%m%d-%H%M%S).db"
```

Do not archive or copy a live SQLite file. The web export is encrypted but does
not include the source database salt, so it is not currently a standalone
disaster-recovery backup.

## Restore

1. Stop the application.
2. Preserve the current database under a different name.
3. Copy the tested full-database backup into the configured path.
4. Apply owner-only file permissions.
5. Start with the same `DATABASE_PATH`.
6. Log in using the password that belonged to the restored database.

Do not use `scripts/init_db.py --restore`; that option does not exist.

## Updates

```bash
./venv/bin/python scripts/start.py --stop
install -m 600 "$DATABASE_PATH" "/secure/backup/pre-update.db"
./venv/bin/python -m pip install -r requirements.txt
./venv/bin/python scripts/start.py --env production
```

Database migrations run on connection. Inspect logs after startup. If a
migration fails, stop the application and restore the pre-update full database
before further writes.

## Portable Copies

Python virtual environments are not portable across operating systems, Python
installations, or many directory moves. Copy source and data separately, then
recreate `venv` on the destination computer.

Moving only a normal web export is insufficient. Copying the complete stopped
database preserves its salt and encrypted records.

## Current Operational Limits

- Debug/development startup can conflict with PID tracking because of Flask's
  reloader.
- Daemon mode has unreliable PID and relative-path behavior.
- Configuration validation does not test database access or schema integrity.
- No automatic database-backup retention is implemented.
- No application-level CSRF token, login throttling, or upload-size limit is
  implemented.
- SQLite performance pragmas and application caches shown in older versions of
  this guide are not configured by the current code.
