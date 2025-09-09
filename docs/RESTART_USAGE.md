# Restart Functionality for Net Worth Tracker

The start scripts have been updated to include restart functionality for easier application management.

## New Options

### Python Script (`scripts/start.py`)
```bash
./venv/bin/python scripts/start.py --restart    # Restart the application
./venv/bin/python scripts/start.py --stop       # Stop the application
./venv/bin/python scripts/start.py --status     # Check if running
```

### Shell Script (`scripts/start.sh`) - Unix/Linux/macOS
```bash
./scripts/start.sh --restart    # Restart the application
./scripts/start.sh --stop       # Stop the application
./scripts/start.sh --status     # Check if running
```

### Batch Script (`scripts/start.bat`) - Windows
```cmd
scripts\start.bat --restart     # Restart the application
scripts\start.bat --stop        # Stop the application
scripts\start.bat --status      # Check if running
```

## Usage Examples

### Restart the application
```bash
# Using Python script directly
./venv/bin/python scripts/start.py --restart

# Using shell script (Unix/Linux/macOS)
./scripts/start.sh --restart

# Using batch script (Windows)
scripts\start.bat --restart
```

### Stop the application
```bash
# Using Python script directly
./venv/bin/python scripts/start.py --stop

# Using shell script (Unix/Linux/macOS)
./scripts/start.sh --stop

# Using batch script (Windows)
scripts\start.bat --stop
```

### Check application status
```bash
# Using Python script directly
./venv/bin/python scripts/start.py --status

# Using shell script (Unix/Linux/macOS)
./scripts/start.sh --status

# Using batch script (Windows)
scripts\start.bat --status
```

## How Restart Works

1. **Check if running**: The script checks if the application is currently running using the PID file
2. **Graceful shutdown**: If running, it sends a SIGTERM signal for graceful shutdown
3. **Wait for shutdown**: Waits up to 30 seconds for the application to shut down gracefully
4. **Force termination**: If graceful shutdown fails, forces termination with SIGKILL
5. **Clean start**: Starts the application fresh with the same configuration

## Benefits

- **Easy updates**: Restart after code changes without manual stop/start
- **Maintenance**: Quick restart for maintenance operations
- **Troubleshooting**: Easy way to restart if the application becomes unresponsive
- **Deployment**: Simplified deployment process with automatic restart

## Error Handling

- If the application is not running and you try to stop it, you'll get a "not running" message
- If the application is already running and you try to start it (without restart), you'll get an error
- The restart command handles both cases gracefully
- PID file management ensures clean state tracking

## Cross-Platform Support

All three scripts (Python, Shell, Batch) support the same restart functionality:
- **Python script**: Works on all platforms, requires Python environment
- **Shell script**: Optimized for Unix/Linux/macOS with better process management
- **Batch script**: Windows-specific with appropriate Windows process handling

## Integration with Existing Workflows

The restart functionality integrates seamlessly with existing options:
```bash
# Restart in development mode
./scripts/start.sh --restart -e development

# Restart with debug enabled
./scripts/start.sh --restart --debug

# Restart on different port
./scripts/start.sh --restart -p 5001
```