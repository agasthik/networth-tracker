# Restart and Process Control

`scripts/start.py`, `scripts/start.sh`, and `scripts/start.bat` support start,
status, stop, and restart operations through a PID file.

## Commands

Python:

```bash
./venv/bin/python scripts/start.py --status
./venv/bin/python scripts/start.py --stop
./venv/bin/python scripts/start.py --restart --env production
```

Unix-like wrapper:

```bash
./scripts/start.sh --status
./scripts/start.sh --stop
./scripts/start.sh --restart -e production
```

Windows:

```cmd
scripts\start.bat --status
scripts\start.bat --stop
scripts\start.bat --restart -e production
```

## Configuration on Restart

Restart stops the PID recorded in the selected PID file and then performs a new
startup. It does not remember the previous host, port, environment, database
path, secret, or other command-line options.

Supply the desired settings again:

```bash
DATABASE_PATH=/absolute/private/path/networth.db \
./scripts/start.sh --restart -e production -p 5001
```

Use the same PID-file path and working directory as the original startup. The
wrappers use the repository-root `networth_tracker.pid`; direct `start.py`
invocations use the path supplied with `--pid-file`.

## Stop Behavior

On Unix-like systems, the Python control path sends `SIGTERM`, waits up to 30
seconds, and can then send `SIGKILL`. The shell wrapper intends to follow the
same sequence; use the Python command when predictable stop handling is
required.

The Windows batch script uses `taskkill /T /F` immediately. It does not perform
a graceful shutdown.

Always stop the application before copying or replacing its SQLite database.

## Known Limitations

- Development/debug mode can conflict with PID tracking when Flask's reloader
  creates a child process.
- Daemon mode writes the PID before forking and changes to `/`; its PID and
  relative-path behavior is unreliable.
- A stale PID file could refer to a reused PID. Verify the target process before
  manually killing it.
- Restart is process control, not a database integrity or health check.

For long-running local operation, prefer foreground mode supervised by a
user-level service manager.
