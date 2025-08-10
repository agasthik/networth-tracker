"""
Logging configuration for the networth tracker application.
Provides structured logging with different levels for debugging and monitoring.
"""

import logging
import logging.handlers
import os
import sys
from datetime import datetime
from typing import Optional
from pathlib import Path


class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels for console output."""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        """Format log record with colors."""
        if hasattr(record, 'levelname') and record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}{record.levelname}{self.COLORS['RESET']}"
            )
        return super().format(record)


class StructuredFormatter(logging.Formatter):
    """Custom formatter for structured logging with additional context."""

    def format(self, record):
        """Format log record with structured information."""
        # Add timestamp if not present
        if not hasattr(record, 'timestamp'):
            record.timestamp = datetime.now().isoformat()

        # Add process and thread info for debugging
        record.process_id = os.getpid()
        record.thread_id = record.thread

        # Format the message
        formatted = super().format(record)

        # Add any extra context if available
        if hasattr(record, 'context') and record.context:
            formatted += f" | Context: {record.context}"

        return formatted


def setup_logging(
    app_name: str = "networth_tracker",
    log_level: str = "INFO",
    log_dir: Optional[str] = None,
    enable_console: bool = True,
    enable_file: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """
    Set up comprehensive logging configuration.

    Args:
        app_name: Name of the application for log files
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir: Directory for log files (defaults to 'logs' in current directory)
        enable_console: Whether to enable console logging
        enable_file: Whether to enable file logging
        max_file_size: Maximum size of log files before rotation
        backup_count: Number of backup log files to keep

    Returns:
        Configured logger instance
    """
    # Convert log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Create logger
    logger = logging.getLogger(app_name)
    logger.setLevel(numeric_level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create log directory if file logging is enabled
    if enable_file:
        if log_dir is None:
            log_dir = "logs"

        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # Main application log file
        app_log_file = log_path / f"{app_name}.log"

        # Error-only log file
        error_log_file = log_path / f"{app_name}_errors.log"

        # Set up rotating file handler for all logs
        file_handler = logging.handlers.RotatingFileHandler(
            app_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        file_handler.setLevel(numeric_level)

        # Structured formatter for file logs
        file_formatter = StructuredFormatter(
            fmt='%(timestamp)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)

        # Set up separate error file handler
        error_handler = logging.handlers.RotatingFileHandler(
            error_log_file,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(file_formatter)
        logger.addHandler(error_handler)

    # Set up console handler
    if enable_console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)

        # Use colored formatter for console output
        console_formatter = ColoredFormatter(
            fmt='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
            datefmt='%H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

    # Log initial setup message
    logger.info(f"Logging initialized for {app_name} at level {log_level}")
    if enable_file:
        logger.info(f"Log files will be written to: {log_path.absolute()}")

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.

    Args:
        name: Logger name (typically __name__ from calling module)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


def log_function_call(logger: logging.Logger, func_name: str, args: dict = None, level: int = logging.DEBUG):
    """
    Log function call with arguments for debugging.

    Args:
        logger: Logger instance
        func_name: Name of the function being called
        args: Function arguments to log
        level: Logging level to use
    """
    message = f"Calling function: {func_name}"
    if args:
        # Filter out sensitive information
        safe_args = {}
        sensitive_keys = ['password', 'key', 'token', 'secret']

        for key, value in args.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_args[key] = "[REDACTED]"
            else:
                safe_args[key] = value

        message += f" with args: {safe_args}"

    logger.log(level, message)


def log_performance(logger: logging.Logger, operation: str, duration: float, context: dict = None):
    """
    Log performance metrics for operations.

    Args:
        logger: Logger instance
        operation: Name of the operation
        duration: Duration in seconds
        context: Additional context information
    """
    message = f"Performance: {operation} completed in {duration:.3f}s"
    if context:
        message += f" | Context: {context}"

    # Log as warning if operation took too long
    if duration > 5.0:  # More than 5 seconds
        logger.warning(message)
    elif duration > 1.0:  # More than 1 second
        logger.info(message)
    else:
        logger.debug(message)


class LoggingContext:
    """Context manager for adding structured context to log messages."""

    def __init__(self, logger: logging.Logger, **context):
        """
        Initialize logging context.

        Args:
            logger: Logger instance
            **context: Context key-value pairs
        """
        self.logger = logger
        self.context = context
        self.old_context = getattr(logger, '_context', {})

    def __enter__(self):
        """Enter context and add context to logger."""
        # Merge with existing context
        new_context = {**self.old_context, **self.context}
        self.logger._context = new_context
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context and restore previous context."""
        self.logger._context = self.old_context


def with_logging_context(logger: logging.Logger, **context):
    """
    Decorator to add logging context to function calls.

    Args:
        logger: Logger instance
        **context: Context key-value pairs

    Returns:
        Decorator function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            with LoggingContext(logger, **context):
                return func(*args, **kwargs)
        return wrapper
    return decorator


# Security-focused logging utilities
def log_security_event(logger: logging.Logger, event_type: str, details: dict = None, severity: str = "INFO"):
    """
    Log security-related events with special formatting.

    Args:
        logger: Logger instance
        event_type: Type of security event
        details: Event details (sensitive info will be filtered)
        severity: Event severity level
    """
    message = f"SECURITY EVENT: {event_type}"

    if details:
        # Filter sensitive information
        safe_details = {}
        sensitive_keys = ['password', 'key', 'token', 'secret', 'hash']

        for key, value in details.items():
            if any(sensitive in key.lower() for sensitive in sensitive_keys):
                safe_details[key] = "[REDACTED]"
            else:
                safe_details[key] = value

        message += f" | Details: {safe_details}"

    # Log with appropriate level
    level = getattr(logging, severity.upper(), logging.INFO)
    logger.log(level, message)


def log_data_access(logger: logging.Logger, operation: str, resource_type: str, resource_id: str = None, user_id: str = None):
    """
    Log data access operations for audit purposes.

    Args:
        logger: Logger instance
        operation: Type of operation (CREATE, READ, UPDATE, DELETE)
        resource_type: Type of resource being accessed
        resource_id: ID of the resource (if applicable)
        user_id: ID of the user performing the operation
    """
    message = f"DATA ACCESS: {operation} {resource_type}"

    if resource_id:
        message += f" (ID: {resource_id})"

    if user_id:
        message += f" | User: {user_id}"

    logger.info(message)


# Application-specific logging setup
def setup_app_logging(debug_mode: bool = False) -> logging.Logger:
    """
    Set up logging specifically for the networth tracker application.

    Args:
        debug_mode: Whether to enable debug logging

    Returns:
        Configured application logger
    """
    log_level = "DEBUG" if debug_mode else "INFO"

    # Create logs directory in application root
    app_root = Path(__file__).parent.parent
    log_dir = app_root / "logs"

    return setup_logging(
        app_name="networth_tracker",
        log_level=log_level,
        log_dir=str(log_dir),
        enable_console=True,
        enable_file=True
    )