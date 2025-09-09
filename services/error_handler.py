"""
Comprehensive error handling and logging system for the networth tracker application.
Provides custom exception classes, structured error responses, and logging configuration.
"""

import logging
import traceback
import os
from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any, Union
from flask import jsonify
from datetime import datetime


class ErrorType(Enum):
    """Categories of application errors."""
    AUTHENTICATION = "AUTHENTICATION"
    DATABASE = "DATABASE"
    NETWORK = "NETWORK"
    VALIDATION = "VALIDATION"
    ENCRYPTION = "ENCRYPTION"
    STOCK_API = "STOCK_API"
    EXPORT_IMPORT = "EXPORT_IMPORT"
    DEMO_MODE = "DEMO_MODE"
    SYSTEM = "SYSTEM"


class ErrorSeverity(Enum):
    """Error severity levels."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class ErrorContext:
    """Additional context information for errors."""
    user_id: Optional[str] = None
    account_id: Optional[str] = None
    operation: Optional[str] = None
    request_id: Optional[str] = None
    timestamp: Optional[datetime] = None
    additional_data: Optional[Dict[str, Any]] = None


class AppError(Exception):
    """Base application error class with structured error information."""

    def __init__(
        self,
        error_type: ErrorType,
        message: str,
        code: str,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        recoverable: bool = True,
        user_action: Optional[str] = None,
        technical_details: Optional[str] = None,
        context: Optional[ErrorContext] = None,
        original_exception: Optional[Exception] = None
    ):
        """
        Initialize application error.

        Args:
            error_type: Category of error
            message: User-friendly error message
            code: Unique error code for identification
            severity: Error severity level
            recoverable: Whether the error is recoverable
            user_action: Suggested action for the user
            technical_details: Technical details for debugging
            context: Additional context information
            original_exception: Original exception that caused this error
        """
        super().__init__(message)
        self.error_type = error_type
        self.message = message
        self.code = code
        self.severity = severity
        self.recoverable = recoverable
        self.user_action = user_action
        self.technical_details = technical_details
        self.context = context or ErrorContext()
        self.original_exception = original_exception
        self.timestamp = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary for JSON responses."""
        error_dict = {
            'error': True,
            'type': self.error_type.value,
            'message': self.message,
            'code': self.code,
            'severity': self.severity.value,
            'recoverable': self.recoverable,
            'timestamp': self.timestamp.isoformat()
        }

        if self.user_action:
            error_dict['user_action'] = self.user_action

        # Only include technical details if in debug mode and Flask context is available
        try:
            from flask import current_app
            if self.technical_details and current_app.debug:
                error_dict['technical_details'] = self.technical_details
        except RuntimeError:
            # Flask context not available, include technical details in non-production environments
            if self.technical_details and os.environ.get('FLASK_DEBUG', 'False').lower() == 'true':
                error_dict['technical_details'] = self.technical_details

        if self.context and self.context.additional_data:
            error_dict['context'] = self.context.additional_data

        return error_dict


# Authentication Errors
class AuthenticationError(AppError):
    """Authentication-related errors."""

    def __init__(self, message: str, code: str = "AUTH_001", **kwargs):
        super().__init__(
            ErrorType.AUTHENTICATION,
            message,
            code,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class InvalidPasswordError(AuthenticationError):
    """Invalid password error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Invalid password provided",
            code="AUTH_002",
            user_action="Please check your password and try again",
            **kwargs
        )


class SessionExpiredError(AuthenticationError):
    """Session expired error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Your session has expired",
            code="AUTH_003",
            user_action="Please log in again to continue",
            **kwargs
        )


class SetupRequiredError(AuthenticationError):
    """Setup required error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Initial setup is required",
            code="AUTH_004",
            user_action="Please complete the initial setup to continue",
            **kwargs
        )


# Database Errors
class DatabaseError(AppError):
    """Database-related errors."""

    def __init__(self, message: str, code: str = "DB_001", **kwargs):
        super().__init__(
            ErrorType.DATABASE,
            message,
            code,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class DatabaseConnectionError(DatabaseError):
    """Database connection error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Unable to connect to database",
            code="DB_002",
            user_action="Please check if the application has proper file permissions",
            **kwargs
        )


class DatabaseCorruptionError(DatabaseError):
    """Database corruption error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Database appears to be corrupted",
            code="DB_003",
            severity=ErrorSeverity.CRITICAL,
            user_action="Please restore from a backup or contact support",
            **kwargs
        )


class RecordNotFoundError(DatabaseError):
    """Record not found error."""

    def __init__(self, resource_type: str = "record", resource_id: str = "", **kwargs):
        message = f"{resource_type.capitalize()} not found"
        if resource_id:
            message += f" (ID: {resource_id})"

        super().__init__(
            message=message,
            code="DB_004",
            severity=ErrorSeverity.MEDIUM,
            recoverable=True,
            user_action="Please verify the resource exists and try again",
            **kwargs
        )


class DatabaseMigrationError(DatabaseError):
    """Database migration error."""

    def __init__(self, message: str = "Database migration failed", code: str = "DB_005", **kwargs):
        kwargs.setdefault('user_action', "Please restore from backup or contact support")
        super().__init__(message=message, code=code, **kwargs)


class DataIntegrityError(DatabaseError):
    """Data integrity error."""

    def __init__(self, message: str = "Data integrity check failed", code: str = "DB_006", **kwargs):
        kwargs.setdefault('user_action', "Please restore from backup or contact support")
        super().__init__(message=message, code=code, **kwargs)


# Validation Errors
class ValidationError(AppError):
    """Data validation errors."""

    def __init__(self, message: str, code: str = "VAL_001", **kwargs):
        super().__init__(
            ErrorType.VALIDATION,
            message,
            code,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class MissingFieldError(ValidationError):
    """Missing required field error."""

    def __init__(self, fields: Union[str, list], **kwargs):
        if isinstance(fields, list):
            field_str = ", ".join(fields)
            message = f"Missing required fields: {field_str}"
        else:
            message = f"Missing required field: {fields}"

        super().__init__(
            message=message,
            code="VAL_002",
            user_action="Please provide all required fields",
            **kwargs
        )


class InvalidValueError(ValidationError):
    """Invalid field value error."""

    def __init__(self, field: str, value: Any = None, expected: str = "", **kwargs):
        message = f"Invalid value for field '{field}'"
        if value is not None:
            message += f": {value}"
        if expected:
            message += f". Expected: {expected}"

        super().__init__(
            message=message,
            code="VAL_003",
            user_action=f"Please provide a valid value for {field}",
            **kwargs
        )


class InvalidDateError(ValidationError):
    """Invalid date format error."""

    def __init__(self, field: str, **kwargs):
        super().__init__(
            message=f"Invalid date format for field '{field}'",
            code="VAL_004",
            user_action="Please use YYYY-MM-DD format for dates",
            **kwargs
        )


# Encryption Errors
class EncryptionError(AppError):
    """Encryption-related errors."""

    def __init__(self, message: str, code: str = "ENC_001", **kwargs):
        super().__init__(
            ErrorType.ENCRYPTION,
            message,
            code,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class DecryptionError(EncryptionError):
    """Decryption failure error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Failed to decrypt data",
            code="ENC_002",
            user_action="Please verify your password is correct",
            **kwargs
        )


class KeyDerivationError(EncryptionError):
    """Key derivation error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Failed to derive encryption key",
            code="ENC_003",
            user_action="Please try logging in again",
            **kwargs
        )


# Network/API Errors
class NetworkError(AppError):
    """Network-related errors."""

    def __init__(self, message: str, code: str = "NET_001", **kwargs):
        super().__init__(
            ErrorType.NETWORK,
            message,
            code,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class StockAPIError(AppError):
    """Stock API-related errors."""

    def __init__(self, message: str, code: str = "STOCK_001", **kwargs):
        super().__init__(
            ErrorType.STOCK_API,
            message,
            code,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


class StockAPIRateLimitError(StockAPIError):
    """Stock API rate limit error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Stock price API rate limit exceeded",
            code="STOCK_002",
            user_action="Please wait a moment before updating stock prices again",
            **kwargs
        )


class StockNotFoundError(StockAPIError):
    """Stock symbol not found error."""

    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            message=f"Stock symbol '{symbol}' not found",
            code="STOCK_003",
            user_action="Please verify the stock symbol is correct",
            **kwargs
        )


class StockPriceUnavailableError(StockAPIError):
    """Stock price temporarily unavailable error."""

    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            message=f"Stock price for '{symbol}' is temporarily unavailable",
            code="STOCK_004",
            user_action="Please try again later or check if the market is open",
            **kwargs
        )


class StockValidationError(StockAPIError):
    """Stock symbol validation error."""

    def __init__(self, symbol: str, reason: str = "", **kwargs):
        message = f"Invalid stock symbol '{symbol}'"
        if reason:
            message += f": {reason}"

        super().__init__(
            message=message,
            code="STOCK_005",
            user_action="Please provide a valid stock ticker symbol",
            **kwargs
        )


# Watchlist Errors
class WatchlistError(AppError):
    """Watchlist-related errors."""

    def __init__(self, message: str, code: str = "WATCH_001", **kwargs):
        super().__init__(
            ErrorType.VALIDATION,  # Most watchlist errors are validation-related
            message,
            code,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class WatchlistDuplicateError(WatchlistError):
    """Duplicate stock in watchlist error."""

    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            message=f"Stock '{symbol}' is already in your watchlist",
            code="WATCH_002",
            user_action="Stock is already being tracked in your watchlist",
            **kwargs
        )


class WatchlistNotFoundError(WatchlistError):
    """Stock not found in watchlist error."""

    def __init__(self, symbol: str, **kwargs):
        super().__init__(
            message=f"Stock '{symbol}' not found in watchlist",
            code="WATCH_003",
            user_action="Please verify the stock symbol exists in your watchlist",
            **kwargs
        )


class WatchlistLimitExceededError(WatchlistError):
    """Watchlist size limit exceeded error."""

    def __init__(self, limit: int, **kwargs):
        super().__init__(
            message=f"Watchlist limit of {limit} stocks exceeded",
            code="WATCH_004",
            user_action="Please remove some stocks before adding new ones",
            **kwargs
        )


class WatchlistPriceUpdateError(WatchlistError):
    """Watchlist price update error."""

    def __init__(self, failed_symbols: list = None, **kwargs):
        if failed_symbols:
            symbols_str = ", ".join(failed_symbols)
            message = f"Failed to update prices for: {symbols_str}"
        else:
            message = "Failed to update watchlist prices"

        super().__init__(
            message=message,
            code="WATCH_005",
            user_action="Some stock prices could not be updated. Please try again later",
            severity=ErrorSeverity.LOW,
            **kwargs
        )


# HSA Account Errors
class HSAError(AppError):
    """HSA account-related errors."""

    def __init__(self, message: str, code: str = "HSA_001", **kwargs):
        super().__init__(
            ErrorType.VALIDATION,
            message,
            code,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class HSAContributionLimitError(HSAError):
    """HSA contribution limit exceeded error."""

    def __init__(self, attempted_amount: float, remaining_capacity: float, **kwargs):
        super().__init__(
            message=f"Contribution of ${attempted_amount:.2f} exceeds remaining capacity of ${remaining_capacity:.2f}",
            code="HSA_002",
            user_action=f"Maximum additional contribution allowed is ${remaining_capacity:.2f}",
            **kwargs
        )


class HSABalanceValidationError(HSAError):
    """HSA balance validation error."""

    def __init__(self, field: str, value: float, **kwargs):
        super().__init__(
            message=f"Invalid {field}: ${value:.2f}. HSA balances cannot be negative",
            code="HSA_003",
            user_action=f"Please enter a valid positive amount for {field}",
            **kwargs
        )


class HSABalanceMismatchError(HSAError):
    """HSA balance components don't match total error."""

    def __init__(self, total_balance: float, cash_balance: float, investment_balance: float, **kwargs):
        super().__init__(
            message=f"Balance mismatch: Total (${total_balance:.2f}) ≠ Cash (${cash_balance:.2f}) + Investment (${investment_balance:.2f})",
            code="HSA_004",
            user_action="Please ensure cash balance plus investment balance equals total balance",
            **kwargs
        )


class HSAContributionValidationError(HSAError):
    """HSA contribution validation error."""

    def __init__(self, current_contributions: float, annual_limit: float, **kwargs):
        super().__init__(
            message=f"Current year contributions (${current_contributions:.2f}) exceed annual limit (${annual_limit:.2f})",
            code="HSA_005",
            user_action="Please verify your contribution amounts and annual limit",
            **kwargs
        )


# Export/Import Errors
class ExportImportError(AppError):
    """Export/import operation errors."""

    def __init__(self, message: str, code: str = "EXP_001", **kwargs):
        super().__init__(
            ErrorType.EXPORT_IMPORT,
            message,
            code,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class InvalidBackupFileError(ExportImportError):
    """Invalid backup file error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Invalid or corrupted backup file",
            code="EXP_002",
            user_action="Please select a valid backup file",
            **kwargs
        )


# Demo Mode Errors
class DemoModeError(AppError):
    """Demo mode-related errors."""

    def __init__(self, message: str, code: str = "DEMO_001", **kwargs):
        super().__init__(
            ErrorType.DEMO_MODE,
            message,
            code,
            severity=ErrorSeverity.LOW,
            **kwargs
        )


# System Errors
class SystemError(AppError):
    """System-level errors."""

    def __init__(self, message: str, code: str = "SYS_001", **kwargs):
        super().__init__(
            ErrorType.SYSTEM,
            message,
            code,
            severity=ErrorSeverity.HIGH,
            recoverable=False,
            **kwargs
        )


class FilePermissionError(SystemError):
    """File permission error."""

    def __init__(self, file_path: str, **kwargs):
        super().__init__(
            message=f"Insufficient permissions to access file: {file_path}",
            code="SYS_002",
            user_action="Please check file permissions and try again",
            **kwargs
        )


class DiskSpaceError(SystemError):
    """Disk space error."""

    def __init__(self, **kwargs):
        super().__init__(
            message="Insufficient disk space",
            code="SYS_003",
            user_action="Please free up disk space and try again",
            **kwargs
        )


class ErrorHandler:
    """Central error handler for the application."""

    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        Initialize error handler.

        Args:
            logger: Logger instance to use for error logging
        """
        self.logger = logger or logging.getLogger(__name__)

    def handle_error(self, error: Union[AppError, Exception], context: Optional[ErrorContext] = None) -> Dict[str, Any]:
        """
        Handle application errors and return structured response.

        Args:
            error: Error to handle
            context: Additional context information

        Returns:
            Dictionary containing structured error response
        """
        if isinstance(error, AppError):
            app_error = error
            if context:
                app_error.context = context
        else:
            # Convert generic exception to AppError
            app_error = SystemError(
                message="An unexpected error occurred",
                code="SYS_999",
                technical_details=str(error),
                original_exception=error,
                context=context
            )

        # Log the error
        self._log_error(app_error)

        # Return structured response
        return app_error.to_dict()

    def _log_error(self, error: AppError):
        """
        Log error with appropriate level and details.

        Args:
            error: Error to log
        """
        log_message = f"[{error.error_type.value}] {error.code}: {error.message}"

        # Add context information if available
        if error.context:
            context_info = []
            if error.context.user_id:
                context_info.append(f"user_id={error.context.user_id}")
            if error.context.account_id:
                context_info.append(f"account_id={error.context.account_id}")
            if error.context.operation:
                context_info.append(f"operation={error.context.operation}")
            if error.context.request_id:
                context_info.append(f"request_id={error.context.request_id}")

            if context_info:
                log_message += f" | Context: {', '.join(context_info)}"

        # Add technical details if available
        if error.technical_details:
            log_message += f" | Technical: {error.technical_details}"

        # Log with appropriate level based on severity
        if error.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(log_message)
            if error.original_exception:
                self.logger.critical("Stack trace:", exc_info=error.original_exception)
        elif error.severity == ErrorSeverity.HIGH:
            self.logger.error(log_message)
            if error.original_exception:
                self.logger.error("Stack trace:", exc_info=error.original_exception)
        elif error.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(log_message)
        else:  # LOW severity
            self.logger.info(log_message)

    def create_json_response(self, error: Union[AppError, Exception], status_code: int = 500) -> tuple:
        """
        Create Flask JSON response for an error.

        Args:
            error: Error to convert to response
            status_code: HTTP status code

        Returns:
            Tuple of (JSON response, status code)
        """
        error_dict = self.handle_error(error)
        return jsonify(error_dict), status_code


# Global error handler instance
error_handler = ErrorHandler()


def handle_error(error: Union[AppError, Exception], context: Optional[ErrorContext] = None) -> Dict[str, Any]:
    """
    Convenience function to handle errors using the global error handler.

    Args:
        error: Error to handle
        context: Additional context information

    Returns:
        Dictionary containing structured error response
    """
    return error_handler.handle_error(error, context)


def create_json_error_response(error: Union[AppError, Exception], status_code: int = 500) -> tuple:
    """
    Convenience function to create JSON error response.

    Args:
        error: Error to convert to response
        status_code: HTTP status code

    Returns:
        Tuple of (JSON response, status code)
    """
    return error_handler.create_json_response(error, status_code)