"""
Flask-specific error handlers and decorators for the networth tracker application.
Integrates the comprehensive error handling system with Flask routes and middleware.
"""

import functools
import uuid
from typing import Callable, Any, Optional
from flask import request, jsonify, current_app, g
from werkzeug.exceptions import HTTPException

from .error_handler import (
    AppError, ErrorHandler, ErrorContext, ErrorType, ErrorSeverity,
    AuthenticationError, ValidationError, DatabaseError, SystemError,
    create_json_error_response
)
from .logging_config import get_logger, log_security_event, log_data_access


logger = get_logger(__name__)


def generate_request_id() -> str:
    """Generate unique request ID for tracking."""
    return str(uuid.uuid4())[:8]


def get_request_context() -> ErrorContext:
    """
    Get error context from current Flask request.

    Returns:
        ErrorContext with request information
    """
    request_id = getattr(g, 'request_id', None)
    user_id = getattr(g, 'user_id', None)

    return ErrorContext(
        user_id=user_id,
        request_id=request_id,
        additional_data={
            'method': request.method,
            'endpoint': request.endpoint,
            'remote_addr': request.remote_addr,
            'user_agent': request.headers.get('User-Agent', 'Unknown')
        }
    )


def handle_api_error(func: Callable) -> Callable:
    """
    Decorator to handle errors in API endpoints with structured responses.

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Generate request ID for tracking
            g.request_id = generate_request_id()

            # Log API call
            logger.debug(f"API call: {request.method} {request.endpoint} | Request ID: {g.request_id}")

            # Call the original function
            result = func(*args, **kwargs)

            # Log successful completion
            logger.debug(f"API call completed successfully | Request ID: {g.request_id}")

            return result

        except AppError as e:
            # Handle application-specific errors
            context = get_request_context()
            context.operation = func.__name__

            logger.error(f"API error in {func.__name__}: {e.message} | Request ID: {g.request_id}")

            # Determine appropriate HTTP status code
            status_code = _get_http_status_for_error(e)

            return create_json_error_response(e, status_code)

        except HTTPException as e:
            # Handle Werkzeug HTTP exceptions
            context = get_request_context()
            app_error = ValidationError(
                message=e.description or "HTTP error occurred",
                code=f"HTTP_{e.code}",
                context=context
            )

            logger.warning(f"HTTP exception in {func.__name__}: {e.description} | Request ID: {g.request_id}")

            return create_json_error_response(app_error, e.code)

        except Exception as e:
            # Handle unexpected errors
            context = get_request_context()
            context.operation = func.__name__

            app_error = SystemError(
                message="An unexpected error occurred",
                code="SYS_999",
                technical_details=str(e),
                original_exception=e,
                context=context
            )

            logger.error(f"Unexpected error in {func.__name__}: {str(e)} | Request ID: {g.request_id}", exc_info=True)

            return create_json_error_response(app_error, 500)

    return wrapper


def handle_view_error(func: Callable) -> Callable:
    """
    Decorator to handle errors in view functions (HTML responses).

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # Generate request ID for tracking
            g.request_id = generate_request_id()

            # Log view call
            logger.debug(f"View call: {request.method} {request.endpoint} | Request ID: {g.request_id}")

            # Call the original function
            result = func(*args, **kwargs)

            # Log successful completion
            logger.debug(f"View call completed successfully | Request ID: {g.request_id}")

            return result

        except AppError as e:
            # Handle application-specific errors
            context = get_request_context()
            context.operation = func.__name__

            logger.error(f"View error in {func.__name__}: {e.message} | Request ID: {g.request_id}")

            # For view functions, we typically want to flash the error and redirect
            from flask import flash, redirect, url_for

            flash(e.message, 'error')

            # Redirect based on error type
            if isinstance(e, AuthenticationError):
                return redirect(url_for('login'))
            else:
                # Try to redirect to a safe page
                return redirect(url_for('dashboard') if 'dashboard' in current_app.view_functions else url_for('index'))

        except Exception as e:
            # Handle unexpected errors
            context = get_request_context()
            context.operation = func.__name__

            app_error = SystemError(
                message="An unexpected error occurred",
                code="SYS_999",
                technical_details=str(e),
                original_exception=e,
                context=context
            )

            logger.error(f"Unexpected error in {func.__name__}: {str(e)} | Request ID: {g.request_id}", exc_info=True)

            from flask import flash, redirect, url_for
            flash("An unexpected error occurred. Please try again.", 'error')
            return redirect(url_for('index'))

    return wrapper


def require_auth_with_error_handling(func: Callable) -> Callable:
    """
    Enhanced authentication decorator with proper error handling.

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with authentication and error handling
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            from services.auth import AuthenticationManager
            from flask import current_app

            # Get authentication manager
            auth_manager = getattr(current_app, 'auth_manager', None)
            if not auth_manager:
                raise SystemError(
                    message="Authentication system not available",
                    code="AUTH_SYS_001"
                )

            # Check if setup is required
            if auth_manager.is_setup_required():
                raise AuthenticationError(
                    message="Initial setup is required",
                    code="AUTH_004",
                    user_action="Please complete the initial setup"
                )

            # Check if user is authenticated
            if not auth_manager.is_authenticated():
                log_security_event(
                    logger,
                    "UNAUTHORIZED_ACCESS_ATTEMPT",
                    {
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'remote_addr': request.remote_addr
                    },
                    "WARNING"
                )

                raise AuthenticationError(
                    message="Authentication required",
                    code="AUTH_001",
                    user_action="Please log in to continue"
                )

            # Set user context for logging
            session_info = auth_manager.get_session_info()
            g.user_id = session_info.get('user_id', 'unknown')

            # Log successful authentication
            log_security_event(
                logger,
                "AUTHENTICATED_ACCESS",
                {
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'user_id': g.user_id
                },
                "DEBUG"
            )

            return func(*args, **kwargs)

        except AppError:
            # Re-raise application errors
            raise
        except Exception as e:
            # Convert unexpected errors
            raise SystemError(
                message="Authentication check failed",
                code="AUTH_SYS_002",
                technical_details=str(e),
                original_exception=e
            )

    return wrapper


def log_data_operation(operation: str, resource_type: str):
    """
    Decorator to log data access operations.

    Args:
        operation: Type of operation (CREATE, READ, UPDATE, DELETE)
        resource_type: Type of resource being accessed

    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Extract resource ID from arguments if available
            resource_id = None
            if 'account_id' in kwargs:
                resource_id = kwargs['account_id']
            elif len(args) > 0 and isinstance(args[0], str):
                resource_id = args[0]

            # Get user ID from context
            user_id = getattr(g, 'user_id', None)

            # Log the operation
            log_data_access(logger, operation, resource_type, resource_id, user_id)

            return func(*args, **kwargs)

        return wrapper
    return decorator


def _get_http_status_for_error(error: AppError) -> int:
    """
    Determine appropriate HTTP status code for an application error.

    Args:
        error: Application error

    Returns:
        HTTP status code
    """
    if error.error_type == ErrorType.AUTHENTICATION:
        if error.code in ["AUTH_001", "AUTH_003"]:  # Invalid password, session expired
            return 401
        elif error.code == "AUTH_004":  # Setup required
            return 403
        else:
            return 401

    elif error.error_type == ErrorType.VALIDATION:
        return 400

    elif error.error_type == ErrorType.DATABASE:
        if error.code == "DB_004":  # Record not found
            return 404
        else:
            return 500

    elif error.error_type == ErrorType.NETWORK:
        return 503

    elif error.error_type == ErrorType.STOCK_API:
        if error.code == "STOCK_002":  # Rate limit
            return 429
        elif error.code == "STOCK_003":  # Not found
            return 404
        else:
            return 503

    else:
        return 500


def register_error_handlers(app):
    """
    Register global error handlers with Flask application.

    Args:
        app: Flask application instance
    """
    error_handler = ErrorHandler(logger)

    @app.errorhandler(404)
    def handle_404(error):
        """Handle 404 Not Found errors."""
        if request.path.startswith('/api/'):
            # API endpoint - return JSON
            app_error = ValidationError(
                message="Endpoint not found",
                code="HTTP_404"
            )
            return create_json_error_response(app_error, 404)
        else:
            # Web page - render error template or redirect
            from flask import render_template
            try:
                return render_template('errors/404.html'), 404
            except:
                # Fallback if template doesn't exist
                return "Page not found", 404

    @app.errorhandler(500)
    def handle_500(error):
        """Handle 500 Internal Server Error."""
        context = get_request_context()
        app_error = SystemError(
            message="Internal server error",
            code="HTTP_500",
            context=context
        )

        logger.error(f"Internal server error: {str(error)} | Request ID: {getattr(g, 'request_id', 'unknown')}")

        if request.path.startswith('/api/'):
            # API endpoint - return JSON
            return create_json_error_response(app_error, 500)
        else:
            # Web page - render error template or redirect
            from flask import render_template
            try:
                return render_template('errors/500.html'), 500
            except:
                # Fallback if template doesn't exist
                return "Internal server error", 500

    @app.errorhandler(AppError)
    def handle_app_error(error):
        """Handle custom application errors."""
        context = get_request_context()
        error.context = context

        if request.path.startswith('/api/'):
            # API endpoint - return JSON
            status_code = _get_http_status_for_error(error)
            return create_json_error_response(error, status_code)
        else:
            # Web page - flash message and redirect
            from flask import flash, redirect, url_for
            flash(error.message, 'error')

            if isinstance(error, AuthenticationError):
                return redirect(url_for('login'))
            else:
                return redirect(url_for('dashboard') if 'dashboard' in app.view_functions else url_for('index'))

    @app.before_request
    def before_request():
        """Set up request context before each request."""
        g.request_id = generate_request_id()

        # Log request details for debugging
        logger.debug(f"Request: {request.method} {request.path} | Request ID: {g.request_id}")

    @app.after_request
    def after_request(response):
        """Log response details after each request."""
        logger.debug(f"Response: {response.status_code} | Request ID: {getattr(g, 'request_id', 'unknown')}")
        return response


# Convenience decorators combining common patterns
def api_endpoint(func: Callable) -> Callable:
    """
    Decorator combining authentication and error handling for API endpoints.

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with authentication and error handling
    """
    return handle_api_error(require_auth_with_error_handling(func))


def view_endpoint(func: Callable) -> Callable:
    """
    Decorator combining authentication and error handling for view endpoints.

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with authentication and error handling
    """
    return handle_view_error(require_auth_with_error_handling(func))


def public_api_endpoint(func: Callable) -> Callable:
    """
    Decorator for public API endpoints (no authentication required).

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with error handling only
    """
    return handle_api_error(func)


def public_view_endpoint(func: Callable) -> Callable:
    """
    Decorator for public view endpoints (no authentication required).

    Args:
        func: Flask route function to wrap

    Returns:
        Wrapped function with error handling only
    """
    return handle_view_error(func)