# Comprehensive Error Handling System

This document describes the comprehensive error handling and logging system implemented for the Networth Tracker application.

## Overview

The error handling system provides:
- **Custom exception classes** for different error types
- **Structured error responses** for all API endpoints
- **Comprehensive logging** with multiple levels and file rotation
- **User-friendly error messages** with recovery suggestions
- **Flask integration** with decorators and middleware
- **Security-focused logging** for audit trails

## Architecture

### Core Components

1. **Error Handler Module** (`services/error_handler.py`)
   - Custom exception classes
   - Error context management
   - Structured error responses

2. **Logging Configuration** (`services/logging_config.py`)
   - Multi-level logging setup
   - File rotation and management
   - Colored console output

3. **Flask Integration** (`services/flask_error_handlers.py`)
   - Route decorators
   - Global error handlers
   - Request/response middleware

## Error Types and Classes

### Base Error Class

```python
class AppError(Exception):
    """Base application error with structured information."""

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
```

### Error Categories

#### Authentication Errors
- `AuthenticationError` - Base authentication error
- `InvalidPasswordError` - Invalid password provided
- `SessionExpiredError` - User session has expired
- `SetupRequiredError` - Initial setup required

#### Database Errors
- `DatabaseError` - Base database error
- `DatabaseConnectionError` - Cannot connect to database
- `DatabaseCorruptionError` - Database corruption detected
- `RecordNotFoundError` - Requested record not found

#### Validation Errors
- `ValidationError` - Base validation error
- `MissingFieldError` - Required fields missing
- `InvalidValueError` - Invalid field value
- `InvalidDateError` - Invalid date format

#### Encryption Errors
- `EncryptionError` - Base encryption error
- `DecryptionError` - Failed to decrypt data
- `KeyDerivationError` - Key derivation failed

#### Network/API Errors
- `NetworkError` - Network connectivity issues
- `StockAPIError` - Stock price API errors
- `StockAPIRateLimitError` - API rate limit exceeded
- `StockNotFoundError` - Stock symbol not found

#### System Errors
- `SystemError` - System-level errors
- `FilePermissionError` - File permission issues
- `DiskSpaceError` - Insufficient disk space

## Usage Examples

### Basic Error Handling

```python
from services.error_handler import ValidationError, MissingFieldError

# Raise a validation error
if not user_input:
    raise MissingFieldError(['username', 'password'])

# Raise a custom validation error
if len(password) < 12:
    raise ValidationError(
        message="Password must be at least 12 characters long",
        code="VAL_006",
        user_action="Please choose a stronger password"
    )
```

### Using Flask Decorators

```python
from services.flask_error_handlers import api_endpoint, view_endpoint

# For API endpoints (returns JSON)
@app.route('/api/accounts', methods=['GET'])
@api_endpoint
def get_accounts():
    # Any AppError raised here will be converted to JSON response
    if not accounts:
        raise RecordNotFoundError("accounts")
    return jsonify(accounts)

# For view endpoints (returns HTML)
@app.route('/dashboard')
@view_endpoint
def dashboard():
    # Any AppError raised here will flash message and redirect
    if not user_authenticated:
        raise AuthenticationError("Please log in")
    return render_template('dashboard.html')
```

### Error Context

```python
from services.error_handler import ErrorContext, DatabaseError

context = ErrorContext(
    user_id="user123",
    account_id="acc456",
    operation="create_account",
    additional_data={"ip": "127.0.0.1"}
)

raise DatabaseError(
    message="Failed to create account",
    code="DB_001",
    context=context
)
```

## Logging System

### Configuration

The logging system is configured in `services/logging_config.py` and provides:

- **Multiple log levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL
- **File rotation**: Automatic rotation when files exceed 10MB
- **Separate error log**: Errors and above go to a separate file
- **Colored console output**: Different colors for different log levels
- **Structured logging**: Consistent format with timestamps and context

### Log Files

- `logs/networth_tracker.log` - Main application log
- `logs/networth_tracker_errors.log` - Error-only log

### Usage

```python
from services.logging_config import get_logger, log_security_event

logger = get_logger(__name__)

# Basic logging
logger.info("User logged in successfully")
logger.error("Database connection failed")

# Security event logging
log_security_event(
    logger,
    "UNAUTHORIZED_ACCESS_ATTEMPT",
    {"endpoint": "/api/accounts", "ip": "192.168.1.1"},
    "WARNING"
)
```

## Flask Integration

### Route Decorators

The system provides several decorators for different route types:

```python
# API endpoints with authentication
@api_endpoint
def my_api_route():
    pass

# View endpoints with authentication
@view_endpoint
def my_view_route():
    pass

# Public API endpoints (no auth)
@public_api_endpoint
def public_api():
    pass

# Public view endpoints (no auth)
@public_view_endpoint
def public_view():
    pass
```

### Data Operation Logging

```python
@log_data_operation('CREATE', 'account')
def create_account():
    # This will automatically log the data access operation
    pass
```

### Global Error Handlers

The system registers global error handlers for:
- 404 Not Found
- 500 Internal Server Error
- Custom AppError exceptions
- HTTP exceptions

## Error Response Format

### API Responses (JSON)

```json
{
  "error": true,
  "type": "VALIDATION",
  "message": "Missing required fields: name, email",
  "code": "VAL_002",
  "severity": "MEDIUM",
  "recoverable": true,
  "timestamp": "2025-08-09T10:42:31.231141",
  "user_action": "Please provide all required fields",
  "context": {
    "ip": "127.0.0.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### View Responses (HTML)

For view endpoints, errors are:
1. Flashed as messages to the user
2. User is redirected to appropriate page
3. Error is logged for debugging

## Security Features

### Sensitive Data Protection

- Passwords and keys are automatically redacted from logs
- Technical details only shown in debug mode
- Security events are specially logged for audit trails

### Audit Logging

```python
# Automatically logs data access operations
log_data_access(logger, "READ", "account", "acc123", "user456")
```

## Best Practices

### 1. Use Specific Error Types

```python
# Good
raise MissingFieldError(['username', 'password'])

# Avoid
raise ValidationError("Missing fields")
```

### 2. Provide User Actions

```python
raise AuthenticationError(
    message="Session expired",
    code="AUTH_003",
    user_action="Please log in again to continue"
)
```

### 3. Include Technical Details for Debugging

```python
raise DatabaseError(
    message="Connection failed",
    code="DB_002",
    technical_details=f"Connection timeout after {timeout}s",
    original_exception=e
)
```

### 4. Use Appropriate Severity Levels

- `CRITICAL`: System is unusable
- `HIGH`: Major functionality broken
- `MEDIUM`: Feature impaired but workarounds exist
- `LOW`: Minor issues or informational

### 5. Add Context for Complex Operations

```python
context = ErrorContext(
    user_id=current_user.id,
    operation="stock_price_update",
    additional_data={"symbols": ["AAPL", "GOOGL"]}
)
```

## Testing

Run the error handling tests:

```bash
./venv/bin/python test_error_handling.py
```

This will test:
- Custom exception classes
- Error handler functionality
- Error context management
- Logging configuration
- JSON response creation

## Monitoring and Debugging

### Log Analysis

Monitor the log files for:
- Error patterns and frequency
- Security events
- Performance issues
- User behavior patterns

### Error Tracking

The system provides:
- Unique request IDs for tracking
- Structured error codes for categorization
- Context information for debugging
- Stack traces for technical errors

## Configuration

### Environment Variables

- `FLASK_DEBUG=true` - Enable debug mode and technical details
- `LOG_LEVEL=DEBUG` - Set logging level
- `LOG_DIR=/path/to/logs` - Custom log directory

### Application Settings

```python
# In app.py
debug_mode = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
app_logger = setup_app_logging(debug_mode=debug_mode)
```

## Future Enhancements

Potential improvements:
- Integration with external monitoring services
- Error rate limiting and throttling
- Automated error reporting and alerting
- Error analytics and trending
- Custom error pages with recovery suggestions