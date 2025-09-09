#!/usr/bin/env python3
"""
Startup script for Networth Tracker application.
Handles initialization, configuration validation, and application startup.
"""

import os
import sys
import argparse
import signal
import atexit
import time
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import ConfigManager, validate_config, get_environment
from services.logging_config import setup_app_logging


class ApplicationStarter:
    """Handles application startup and initialization."""

    def __init__(self):
        self.app = None
        self.config = None
        self.logger = None
        self.pid_file = None

    def parse_arguments(self):
        """Parse command line arguments."""
        parser = argparse.ArgumentParser(description='Networth Tracker Application')
        parser.add_argument(
            '--env',
            choices=['development', 'production', 'testing'],
            default=get_environment(),
            help='Environment to run in (default: production)'
        )
        parser.add_argument(
            '--host',
            default='127.0.0.1',
            help='Host to bind to (default: 127.0.0.1)'
        )
        parser.add_argument(
            '--port',
            type=int,
            default=5000,
            help='Port to bind to (default: 5000)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable debug mode'
        )
        parser.add_argument(
            '--validate-only',
            action='store_true',
            help='Only validate configuration and exit'
        )
        parser.add_argument(
            '--create-dirs',
            action='store_true',
            help='Create necessary directories and exit'
        )
        parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (Unix/Linux/macOS only)'
        )
        parser.add_argument(
            '--pid-file',
            default='networth_tracker.pid',
            help='PID file for daemon mode (default: networth_tracker.pid)'
        )
        parser.add_argument(
            '--restart',
            action='store_true',
            help='Restart the application (stop if running, then start)'
        )
        parser.add_argument(
            '--stop',
            action='store_true',
            help='Stop the running application'
        )
        parser.add_argument(
            '--status',
            action='store_true',
            help='Check if the application is running'
        )

        return parser.parse_args()

    def setup_environment(self, env_name):
        """Set up the environment configuration."""
        os.environ['FLASK_ENV'] = env_name
        self.config = ConfigManager.get_config(env_name)

        # Initialize directories
        ConfigManager.create_directories()

        # Set up logging
        self.logger = setup_app_logging(debug_mode=(env_name == 'development'))

        return self.config

    def validate_configuration(self):
        """Validate the current configuration."""
        validation_results = validate_config(self.config)

        if validation_results['errors']:
            self.logger.error("Configuration validation failed:")
            for error in validation_results['errors']:
                self.logger.error(f"  ERROR: {error}")
            return False

        if validation_results['warnings']:
            self.logger.warning("Configuration warnings:")
            for warning in validation_results['warnings']:
                self.logger.warning(f"  WARNING: {warning}")

        self.logger.info("Configuration validation passed")
        return True

    def create_flask_app(self):
        """Create and configure the Flask application."""
        from app import app

        # Initialize app with configuration
        self.config.init_app(app)

        self.app = app
        return app

    def setup_signal_handlers(self):
        """Set up signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, shutting down gracefully...")
            self.cleanup()
            sys.exit(0)

        # Register signal handlers (Unix/Linux/macOS only)
        if os.name != 'nt':
            signal.signal(signal.SIGTERM, signal_handler)
            signal.signal(signal.SIGINT, signal_handler)

    def create_pid_file(self, pid_file_path):
        """Create PID file for daemon mode."""
        try:
            with open(pid_file_path, 'w') as f:
                f.write(str(os.getpid()))
            self.pid_file = pid_file_path
            self.logger.info(f"PID file created: {pid_file_path}")
        except Exception as e:
            self.logger.error(f"Failed to create PID file: {e}")
            return False
        return True

    def cleanup(self):
        """Clean up resources on shutdown."""
        if self.pid_file and os.path.exists(self.pid_file):
            try:
                os.remove(self.pid_file)
                self.logger.info(f"PID file removed: {self.pid_file}")
            except Exception as e:
                self.logger.error(f"Failed to remove PID file: {e}")

    def is_running(self, pid_file_path):
        """Check if the application is currently running."""
        if not os.path.exists(pid_file_path):
            return False, None

        try:
            with open(pid_file_path, 'r') as f:
                pid = int(f.read().strip())

            # Check if process is running
            try:
                os.kill(pid, 0)  # Signal 0 doesn't kill, just checks if process exists
                return True, pid
            except OSError:
                # Process doesn't exist, remove stale PID file
                os.remove(pid_file_path)
                return False, None

        except (ValueError, IOError):
            # Invalid PID file, remove it
            try:
                os.remove(pid_file_path)
            except OSError:
                pass
            return False, None

    def stop_application(self, pid_file_path, timeout=30):
        """Stop the running application."""
        is_running, pid = self.is_running(pid_file_path)

        if not is_running:
            print("Application is not running")
            return True

        print(f"Stopping application (PID: {pid})...")

        try:
            # Send SIGTERM for graceful shutdown
            os.kill(pid, signal.SIGTERM)

            # Wait for graceful shutdown
            for i in range(timeout):
                if not self.is_running(pid_file_path)[0]:
                    print("Application stopped successfully")
                    return True
                time.sleep(1)

            # If still running, force kill
            print("Graceful shutdown timeout, forcing termination...")
            os.kill(pid, signal.SIGKILL)

            # Wait a bit more
            time.sleep(2)
            if not self.is_running(pid_file_path)[0]:
                print("Application forcefully terminated")
                return True
            else:
                print("Failed to stop application")
                return False

        except OSError as e:
            print(f"Error stopping application: {e}")
            return False

    def show_status(self, pid_file_path):
        """Show the current status of the application."""
        is_running, pid = self.is_running(pid_file_path)

        if is_running:
            print(f"Application is running (PID: {pid})")
            return 0
        else:
            print("Application is not running")
            return 1

    def run_daemon(self, host, port):
        """Run the application as a daemon (Unix/Linux/macOS only)."""
        if os.name == 'nt':
            self.logger.error("Daemon mode not supported on Windows")
            return False

        try:
            # Fork the process
            pid = os.fork()
            if pid > 0:
                # Parent process
                print(f"Daemon started with PID: {pid}")
                sys.exit(0)

            # Child process
            os.setsid()  # Create new session
            os.chdir('/')  # Change to root directory

            # Redirect standard file descriptors
            sys.stdin.close()
            sys.stdout.close()
            sys.stderr.close()

            # Run the application
            self.logger.info("Starting application in daemon mode")
            self.app.run(host=host, port=port, debug=False)

        except Exception as e:
            self.logger.error(f"Failed to start daemon: {e}")
            return False

        return True

    def run(self):
        """Main entry point for the application."""
        args = self.parse_arguments()

        # Handle control operations first (before setting up environment)
        if args.stop:
            return 0 if self.stop_application(args.pid_file) else 1

        if args.status:
            return self.show_status(args.pid_file)

        if args.restart:
            print("Restarting application...")
            # Stop if running
            if self.is_running(args.pid_file)[0]:
                if not self.stop_application(args.pid_file):
                    print("Failed to stop application for restart")
                    return 1
                # Wait a moment before starting
                time.sleep(2)
            print("Starting application...")
            # Continue with normal startup

        # Set up environment
        config = self.setup_environment(args.env)

        # Handle special modes
        if args.create_dirs:
            print("Creating necessary directories...")
            ConfigManager.create_directories()
            print("Directories created successfully")
            return 0

        if args.validate_only:
            print("Validating configuration...")
            if self.validate_configuration():
                print("Configuration is valid")
                return 0
            else:
                print("Configuration validation failed")
                return 1

        # Validate configuration
        if not self.validate_configuration():
            return 1

        # Check if already running (unless this is a restart)
        if not args.restart:
            is_running, pid = self.is_running(args.pid_file)
            if is_running:
                print(f"Application is already running (PID: {pid})")
                print("Use --stop to stop it, or --restart to restart it")
                return 1

        # Create Flask app
        app = self.create_flask_app()

        # Set up signal handlers
        self.setup_signal_handlers()
        atexit.register(self.cleanup)

        # Handle daemon mode
        if args.daemon:
            if not self.create_pid_file(args.pid_file):
                return 1
            return 0 if self.run_daemon(args.host, args.port) else 1

        # Create PID file for regular mode too
        if not self.create_pid_file(args.pid_file):
            return 1

        # Start the application
        try:
            self.logger.info(f"Starting Networth Tracker on {args.host}:{args.port}")
            self.logger.info(f"Environment: {args.env}")
            self.logger.info(f"Debug mode: {args.debug or config.DEBUG}")

            app.run(
                host=args.host,
                port=args.port,
                debug=args.debug or config.DEBUG
            )

        except KeyboardInterrupt:
            self.logger.info("Application interrupted by user")
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            return 1
        finally:
            self.cleanup()

        return 0


def main():
    """Main entry point."""
    starter = ApplicationStarter()
    return starter.run()


if __name__ == '__main__':
    sys.exit(main())