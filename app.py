#!/usr/bin/env python3
"""
Networth Tracker - A secure, local financial portfolio management application
"""

import os
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps

# Import configuration management
from config import ConfigManager, get_environment

from services.auth import AuthenticationManager
from services.historical import HistoricalDataService
from models.accounts import AccountFactory, AccountType, BaseAccount, ChangeType
from datetime import date, datetime, timedelta
from typing import Dict, Any, Optional
import json

# Import comprehensive error handling system
from services.error_handler import (
    AppError, AuthenticationError, ValidationError, DatabaseError,
    MissingFieldError, InvalidValueError, InvalidDateError,
    RecordNotFoundError, SystemError,
    handle_error, create_json_error_response
)
from services.logging_config import setup_app_logging, get_logger
from services.flask_error_handlers import (
    register_error_handlers, api_endpoint, view_endpoint,
    public_api_endpoint, public_view_endpoint, log_data_operation
)

# Initialize Flask application
app = Flask(__name__)

# Get configuration based on environment
config = ConfigManager.get_config(get_environment())

# Initialize app with configuration
config.init_app(app)

# Set up comprehensive logging
app_logger = setup_app_logging(debug_mode=config.DEBUG)
app.logger = app_logger

# Initialize authentication manager
auth_manager = AuthenticationManager(config.DATABASE_PATH)
app.auth_manager = auth_manager  # Make available to error handlers



# Register comprehensive error handlers
register_error_handlers(app)

# Log application startup
app_logger.info("Networth Tracker application starting up")
app_logger.info(f"Environment: {get_environment()}")
app_logger.info(f"Debug mode: {config.DEBUG}")
app_logger.info(f"Database path: {config.DATABASE_PATH}")
app_logger.info(f"Application version: {config.VERSION}")

def require_auth(f):
    """
    Legacy decorator for backward compatibility.
    New routes should use @view_endpoint or @api_endpoint decorators.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            if not auth_manager.require_authentication():
                raise AuthenticationError(
                    message="Authentication required",
                    code="AUTH_001"
                )
            return f(*args, **kwargs)
        except AuthenticationError:
            return redirect(url_for('login'))
        except Exception as e:
            app_logger.error(f"Authentication check failed: {str(e)}")
            flash("An error occurred during authentication. Please try again.", 'error')
            return redirect(url_for('login'))
    return decorated_function


@app.route('/')
@public_view_endpoint
def index():
    """Main application entry point"""
    # Check if setup is required
    if auth_manager.is_setup_required():
        return redirect(url_for('setup'))

    # Check if user is authenticated
    if not auth_manager.is_authenticated():
        return redirect(url_for('login'))

    return redirect(url_for('dashboard'))


@app.route('/setup', methods=['GET', 'POST'])
@public_view_endpoint
def setup():
    """Initial setup for master password"""
    if not auth_manager.is_setup_required():
        return redirect(url_for('index'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        # Validate required fields
        if not password or not confirm_password:
            raise MissingFieldError(['password', 'confirm_password'])

        # Validate password match
        if password != confirm_password:
            raise ValidationError(
                message="Passwords do not match",
                code="VAL_005",
                user_action="Please ensure both password fields match"
            )

        # Validate password strength
        if len(password) < 12:
            raise ValidationError(
                message="Password must be at least 12 characters long",
                code="VAL_006",
                user_action="Please choose a stronger password with at least 12 characters"
            )

        # Set master password
        if auth_manager.set_master_password(password):
            app_logger.info("Master password set successfully during initial setup")
            flash('Master password set successfully', 'success')
            return redirect(url_for('login'))
        else:
            raise DatabaseError(
                message="Failed to set master password",
                code="DB_005",
                user_action="Please try again or check file permissions"
            )

    return render_template('setup.html')


@app.route('/login', methods=['GET', 'POST'])
@public_view_endpoint
def login():
    """Handle master password authentication"""
    if auth_manager.is_setup_required():
        return redirect(url_for('setup'))

    if auth_manager.is_authenticated():
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        password = request.form.get('password')

        # Validate required field
        if not password:
            raise MissingFieldError('password')

        # Verify password
        if auth_manager.verify_password(password):
            app_logger.info("User logged in successfully")
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            app_logger.warning("Failed login attempt")
            raise AuthenticationError(
                message="Invalid password",
                code="AUTH_002",
                user_action="Please check your password and try again"
            )

    return render_template('login.html')


@app.route('/logout', methods=['POST'])
def logout():
    """Clear session and logout user"""
    auth_manager.logout()
    flash('Logged out successfully', 'info')
    return redirect(url_for('login'))


@app.route('/dashboard')
@require_auth
def dashboard():
    """Main dashboard - placeholder for now"""
    session_info = auth_manager.get_session_info()
    return render_template('dashboard.html',
                         session_info=session_info)

@app.route('/watchlist')
@require_auth
def watchlist():
    """Watchlist page for tracking stocks"""
    session_info = auth_manager.get_session_info()
    return render_template('watchlist.html',
                         session_info=session_info)

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'version': '1.0.0'
    })





# Account Management API Endpoints

@app.route('/api/accounts', methods=['GET'])
@api_endpoint
@log_data_operation('READ', 'accounts')
def get_accounts():
    """Get all accounts for the authenticated user."""
    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Get optional account type filter
    account_type = request.args.get('type')

    # Validate account type if provided
    if account_type:
        try:
            AccountType(account_type)
        except ValueError:
            raise ValidationError(
                message=f"Invalid account type: {account_type}",
                code="VAL_007",
                user_action=f"Valid account types are: {[t.value for t in AccountType]}"
            )

    # Retrieve accounts from database
    accounts_data = db_service.get_accounts(account_type)

    # Convert to API response format
    accounts = []
    for account_data in accounts_data:
        try:
            # Map 'type' to 'account_type' for the model and remove database-specific fields
            account_data_clean = account_data.copy()
            if 'type' in account_data_clean:
                account_data_clean['account_type'] = account_data_clean['type']
                del account_data_clean['type']

            # Remove database-specific fields that aren't part of the account model
            db_fields = ['schema_version', 'is_demo']
            for field in db_fields:
                if field in account_data_clean:
                    del account_data_clean[field]

            # Convert datetime objects to ISO strings for from_dict method
            datetime_fields = ['created_date', 'last_updated']
            for field in datetime_fields:
                if field in account_data_clean and isinstance(account_data_clean[field], datetime):
                    account_data_clean[field] = account_data_clean[field].isoformat()

            # Convert date objects to ISO strings for from_dict method
            date_fields = ['maturity_date', 'purchase_date']
            for field in date_fields:
                if field in account_data_clean and isinstance(account_data_clean[field], date):
                    account_data_clean[field] = account_data_clean[field].isoformat()

            # Create account object to get current value
            account = AccountFactory.create_account_from_dict(account_data_clean)
            account_response = account.to_dict()
            account_response['current_value'] = account.get_current_value()
            # Ensure 'type' field is available for API compatibility
            account_response['type'] = account_response['account_type']
            # Add is_demo field back to response if it exists in original data
            if 'is_demo' in account_data:
                account_response['is_demo'] = account_data['is_demo']
            accounts.append(account_response)
        except Exception as e:
            # Log error but continue with other accounts
            app_logger.error(f"Error processing account {account_data.get('id', 'unknown')}: {str(e)}")
            continue

    return jsonify({
        'success': True,
        'accounts': accounts,
        'count': len(accounts)
    })


@app.route('/api/accounts', methods=['POST'])
@api_endpoint
@log_data_operation('CREATE', 'accounts')
def create_account():
    """Create a new account."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Validate request data
        if not request.is_json:
            return jsonify({
                'error': True,
                'message': 'Request must be JSON',
                'code': 'INVALID_CONTENT_TYPE'
            }), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({
                'error': True,
                'message': 'Invalid JSON format',
                'code': 'INVALID_JSON_FORMAT'
            }), 400

        if not data:
            return jsonify({
                'error': True,
                'message': 'Request body cannot be empty',
                'code': 'EMPTY_REQUEST_BODY'
            }), 400

        # Validate required fields
        required_fields = ['name', 'institution', 'type']
        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return jsonify({
                'error': True,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'code': 'MISSING_REQUIRED_FIELDS'
            }), 400

        # Validate account type
        try:
            account_type = AccountType(data['type'])
        except ValueError:
            return jsonify({
                'error': True,
                'message': f'Invalid account type: {data["type"]}. Valid types: {[t.value for t in AccountType]}',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Validate account-specific data based on type
        validation_error = _validate_account_data(account_type, data)
        if validation_error:
            return validation_error

        # Create account using factory for validation
        try:
            # Remove fields that shouldn't be passed to account constructor
            account_data = data.copy()

            # Remove form-specific fields that aren't part of account models
            form_only_fields = ['type', 'account_id', 'account_number']
            for field in form_only_fields:
                if field in account_data:
                    del account_data[field]

            # Convert string dates to date objects for account models
            date_fields = ['maturity_date', 'purchase_date']
            for field in date_fields:
                if field in account_data and isinstance(account_data[field], str):
                    try:
                        account_data[field] = date.fromisoformat(account_data[field])
                    except ValueError:
                        return jsonify({
                            'error': True,
                            'message': f'Invalid {field} format. Use YYYY-MM-DD',
                            'code': 'INVALID_DATE_FORMAT'
                        }), 400

            # Convert string numeric fields to appropriate numeric types
            numeric_fields = [
                'principal_amount', 'current_value', 'interest_rate', 'current_balance',
                'employer_match', 'contribution_limit', 'employer_contribution',
                'cash_balance', 'purchase_amount', 'fixed_rate', 'inflation_rate',
                'annual_contribution_limit', 'current_year_contributions', 'employer_contributions',
                'investment_balance'
            ]
            for field in numeric_fields:
                if field in account_data and isinstance(account_data[field], str):
                    try:
                        account_data[field] = float(account_data[field])
                    except (ValueError, TypeError):
                        return jsonify({
                            'error': True,
                            'message': f'Invalid {field} format. Must be a valid number',
                            'code': 'INVALID_NUMERIC_FORMAT'
                        }), 400

            # Create account for validation (don't use the generated ID)
            account = AccountFactory.create_account(account_type, **account_data)
        except ValueError as e:
            return jsonify({
                'error': True,
                'message': f'Account validation failed: {str(e)}',
                'code': 'ACCOUNT_VALIDATION_ERROR'
            }), 400

        # Convert account to database format (exclude the generated ID)
        account_dict = account.to_dict()
        # Map account_type to type for database storage
        account_dict['type'] = account_dict['account_type']
        # Remove the generated ID so database service can create its own
        if 'id' in account_dict:
            del account_dict['id']

        # Store in database
        account_id = db_service.create_account(account_dict)

        # Create initial historical snapshot
        db_service.create_historical_snapshot(
            account_id,
            account.get_current_value(),
            'INITIAL_ENTRY'
        )

        # Return created account
        account_dict['id'] = account_id
        account_dict['current_value'] = account.get_current_value()
        # Ensure 'type' field is available for API compatibility
        account_dict['type'] = account_dict['account_type']

        return jsonify({
            'success': True,
            'message': 'Account created successfully',
            'account': account_dict
        }), 201

    except Exception as e:
        app.logger.error(f"Error creating account: {str(e)}")
        import traceback
        app.logger.error(f"Account creation traceback: {traceback.format_exc()}")
        return jsonify({
            'error': True,
            'message': f'Failed to create account: {str(e)}',
            'code': 'ACCOUNT_CREATION_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>', methods=['GET'])
@require_auth
def get_account(account_id):
    """Get a specific account by ID."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Retrieve account from database
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Create account object and add current value
        try:
            # Map 'type' to 'account_type' for the model and remove database-specific fields
            account_data_clean = account_data.copy()
            if 'type' in account_data_clean:
                account_data_clean['account_type'] = account_data_clean['type']
                del account_data_clean['type']

            # Remove database-specific fields that aren't part of the account model
            db_fields = ['schema_version', 'is_demo']
            for field in db_fields:
                if field in account_data_clean:
                    del account_data_clean[field]

            # Convert datetime objects to ISO strings for from_dict method
            datetime_fields = ['created_date', 'last_updated']
            for field in datetime_fields:
                if field in account_data_clean and isinstance(account_data_clean[field], datetime):
                    account_data_clean[field] = account_data_clean[field].isoformat()

            # Convert date objects to ISO strings for from_dict method
            date_fields = ['maturity_date', 'purchase_date']
            for field in date_fields:
                if field in account_data_clean and isinstance(account_data_clean[field], date):
                    account_data_clean[field] = account_data_clean[field].isoformat()

            account = AccountFactory.create_account_from_dict(account_data_clean)
            account_response = account.to_dict()
            account_response['current_value'] = account.get_current_value()
            # Ensure 'type' field is available for API compatibility
            account_response['type'] = account_response['account_type']

            # Add stock positions for trading accounts
            if account.account_type == AccountType.TRADING:
                positions = db_service.get_stock_positions(account_id)
                account_response['positions'] = positions

            return jsonify({
                'success': True,
                'account': account_response
            })

        except Exception as e:
            app.logger.error(f"Error processing account {account_id}: {str(e)}")
            return jsonify({
                'error': True,
                'message': 'Error processing account data',
                'code': 'ACCOUNT_PROCESSING_ERROR'
            }), 500

    except Exception as e:
        app.logger.error(f"Error retrieving account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to retrieve account',
            'code': 'ACCOUNT_RETRIEVAL_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>', methods=['PUT'])
@require_auth
def update_account(account_id):
    """Update an existing account."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Validate request data
        if not request.is_json:
            return jsonify({
                'error': True,
                'message': 'Request must be JSON',
                'code': 'INVALID_CONTENT_TYPE'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'error': True,
                'message': 'Request body cannot be empty',
                'code': 'EMPTY_REQUEST_BODY'
            }), 400

        # Check if account exists
        existing_account_data = db_service.get_account(account_id)
        if not existing_account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Get current account value for historical tracking
        try:
            # Map 'type' to 'account_type' for the model and remove database-specific fields
            existing_data_copy = existing_account_data.copy()
            if 'type' in existing_data_copy:
                existing_data_copy['account_type'] = existing_data_copy['type']
                del existing_data_copy['type']

            # Remove database-specific fields that aren't part of the account model
            db_fields = ['schema_version', 'is_demo']
            for field in db_fields:
                if field in existing_data_copy:
                    del existing_data_copy[field]

            existing_account = AccountFactory.create_account_from_dict(existing_data_copy)
            old_value = existing_account.get_current_value()
        except Exception as e:
            app.logger.error(f"Error processing existing account {account_id}: {str(e)}")
            return jsonify({
                'error': True,
                'message': 'Error processing existing account data',
                'code': 'ACCOUNT_PROCESSING_ERROR'
            }), 500

        # Merge update data with existing data
        updated_data = existing_account_data.copy()
        updated_data.update(data)
        updated_data['id'] = account_id  # Ensure ID is preserved
        # Note: last_updated will be handled by the database service

        # Validate account type if provided
        if 'type' in data:
            try:
                account_type = AccountType(data['type'])
                # The account_type will be set when creating the account object
                # Remove 'type' from updated_data to avoid conflicts
                if 'type' in updated_data:
                    del updated_data['type']
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': f'Invalid account type: {data["type"]}. Valid types: {[t.value for t in AccountType]}',
                    'code': 'INVALID_ACCOUNT_TYPE'
                }), 400

            # Validate account-specific data
            validation_error = _validate_account_data(account_type, data)
            if validation_error:
                return validation_error

        # Create updated account object for validation
        try:
            # Map 'type' to 'account_type' for the model and remove database-specific fields
            updated_data_copy = updated_data.copy()
            if 'type' in updated_data_copy:
                updated_data_copy['account_type'] = updated_data_copy['type']
                del updated_data_copy['type']

            # Remove database-specific fields that aren't part of the account model
            db_fields = ['schema_version', 'is_demo']
            for field in db_fields:
                if field in updated_data_copy:
                    del updated_data_copy[field]

            # Convert datetime objects to ISO strings for from_dict method
            datetime_fields = ['created_date', 'last_updated']
            for field in datetime_fields:
                if field in updated_data_copy and isinstance(updated_data_copy[field], datetime):
                    updated_data_copy[field] = updated_data_copy[field].isoformat()

            # Convert date objects to ISO strings for from_dict method
            date_fields = ['maturity_date', 'purchase_date']
            for field in date_fields:
                if field in updated_data_copy and isinstance(updated_data_copy[field], date):
                    updated_data_copy[field] = updated_data_copy[field].isoformat()

            # Convert string numeric fields to appropriate numeric types
            numeric_fields = [
                'principal_amount', 'current_value', 'interest_rate', 'current_balance',
                'employer_match', 'contribution_limit', 'employer_contribution',
                'cash_balance', 'purchase_amount', 'fixed_rate', 'inflation_rate',
                'annual_contribution_limit', 'current_year_contributions', 'employer_contributions',
                'investment_balance'
            ]
            for field in numeric_fields:
                if field in updated_data_copy and isinstance(updated_data_copy[field], str):
                    try:
                        updated_data_copy[field] = float(updated_data_copy[field])
                    except (ValueError, TypeError):
                        return jsonify({
                            'error': True,
                            'message': f'Invalid {field} format. Must be a valid number',
                            'code': 'INVALID_NUMERIC_FORMAT'
                        }), 400

            updated_account = AccountFactory.create_account_from_dict(updated_data_copy)
            new_value = updated_account.get_current_value()
        except ValueError as e:
            return jsonify({
                'error': True,
                'message': f'Account validation failed: {str(e)}',
                'code': 'ACCOUNT_VALIDATION_ERROR'
            }), 400

        # Update in database
        # Map account_type to type for database storage if present
        if 'account_type' in updated_data:
            updated_data['type'] = updated_data['account_type'].value if hasattr(updated_data['account_type'], 'value') else updated_data['account_type']

        success = db_service.update_account(account_id, updated_data)
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to update account in database',
                'code': 'DATABASE_UPDATE_ERROR'
            }), 500

        # Create historical snapshot if value changed using HistoricalDataService
        if abs(new_value - old_value) > 0.01:  # Avoid floating point precision issues
            historical_service = HistoricalDataService(db_service)
            # Create a temporary account object with the correct ID for the snapshot
            temp_account = updated_account
            temp_account.id = account_id
            historical_service.create_snapshot(temp_account, ChangeType.MANUAL_UPDATE)

        # Return updated account
        account_response = updated_account.to_dict()
        account_response['current_value'] = new_value
        # Ensure 'type' field is available for API compatibility
        account_response['type'] = account_response['account_type']

        return jsonify({
            'success': True,
            'message': 'Account updated successfully',
            'account': account_response
        })

    except Exception as e:
        app.logger.error(f"Error updating account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to update account',
            'code': 'ACCOUNT_UPDATE_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>', methods=['DELETE'])
@require_auth
def delete_account(account_id):
    """Delete an account and all related data."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        existing_account = db_service.get_account(account_id)
        if not existing_account:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Delete account (cascading deletes will handle related data)
        success = db_service.delete_account(account_id)
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to delete account from database',
                'code': 'DATABASE_DELETE_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Account deleted successfully',
            'deleted_account_id': account_id
        })

    except Exception as e:
        app.logger.error(f"Error deleting account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to delete account',
            'code': 'ACCOUNT_DELETE_ERROR'
        }), 500


@app.route('/api/demo/accounts', methods=['DELETE'])
@api_endpoint
@log_data_operation('DELETE', 'demo_accounts')
def delete_demo_accounts():
    """Delete all demo accounts and their related data."""
    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Delete all demo accounts
    deleted_count = db_service.delete_demo_accounts()

    return jsonify({
        'success': True,
        'message': f'Successfully deleted {deleted_count} demo accounts',
        'deleted_count': deleted_count
    })


def _validate_account_data(account_type: AccountType, data: Dict[str, Any]) -> Optional[tuple]:
    """
    Validate account-specific data based on account type.

    Args:
        account_type: Type of account to validate
        data: Account data dictionary

    Returns:
        JSON error response tuple if validation fails, None if valid
    """
    try:
        if account_type == AccountType.CD:
            required_fields = ['principal_amount', 'interest_rate', 'maturity_date', 'current_value']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'CD account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_CD_FIELDS'
                }), 400

            # Validate numeric fields (convert to float for comparison)
            try:
                principal_amount = float(data.get('principal_amount', 0))
                if principal_amount <= 0:
                    return jsonify({
                        'error': True,
                        'message': 'Principal amount must be positive',
                        'code': 'INVALID_PRINCIPAL_AMOUNT'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Principal amount must be a valid number',
                    'code': 'INVALID_PRINCIPAL_AMOUNT'
                }), 400

            try:
                interest_rate = float(data.get('interest_rate', -1))
                if interest_rate < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Interest rate cannot be negative',
                        'code': 'INVALID_INTEREST_RATE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Interest rate must be a valid number',
                    'code': 'INVALID_INTEREST_RATE'
                }), 400

            try:
                current_value = float(data.get('current_value', -1))
                if current_value < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Current value cannot be negative',
                        'code': 'INVALID_CURRENT_VALUE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Current value must be a valid number',
                    'code': 'INVALID_CURRENT_VALUE'
                }), 400

            # Validate maturity date
            if 'maturity_date' in data:
                if isinstance(data['maturity_date'], str):
                    try:
                        maturity_date = date.fromisoformat(data['maturity_date'])
                        if maturity_date <= date.today():
                            return jsonify({
                                'error': True,
                                'message': 'Maturity date must be in the future',
                                'code': 'INVALID_MATURITY_DATE'
                            }), 400
                    except ValueError:
                        return jsonify({
                            'error': True,
                            'message': 'Invalid maturity date format. Use YYYY-MM-DD',
                            'code': 'INVALID_DATE_FORMAT'
                        }), 400
                elif isinstance(data['maturity_date'], date):
                    if data['maturity_date'] <= date.today():
                        return jsonify({
                            'error': True,
                            'message': 'Maturity date must be in the future',
                            'code': 'INVALID_MATURITY_DATE'
                        }), 400

        elif account_type == AccountType.SAVINGS:
            required_fields = ['current_balance', 'interest_rate']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'Savings account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_SAVINGS_FIELDS'
                }), 400

            try:
                current_balance = float(data.get('current_balance', -1))
                if current_balance < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Current balance cannot be negative',
                        'code': 'INVALID_CURRENT_BALANCE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Current balance must be a valid number',
                    'code': 'INVALID_CURRENT_BALANCE'
                }), 400

            try:
                interest_rate = float(data.get('interest_rate', -1))
                if interest_rate < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Interest rate cannot be negative',
                        'code': 'INVALID_INTEREST_RATE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Interest rate must be a valid number',
                    'code': 'INVALID_INTEREST_RATE'
                }), 400

        elif account_type == AccountType.ACCOUNT_401K:
            required_fields = ['current_balance', 'employer_match', 'contribution_limit', 'employer_contribution']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'401k account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_401K_FIELDS'
                }), 400

            try:
                current_balance = float(data.get('current_balance', -1))
                if current_balance < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Current balance cannot be negative',
                        'code': 'INVALID_CURRENT_BALANCE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Current balance must be a valid number',
                    'code': 'INVALID_CURRENT_BALANCE'
                }), 400

            try:
                employer_match = float(data.get('employer_match', -1))
                if employer_match < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Employer match cannot be negative',
                        'code': 'INVALID_EMPLOYER_MATCH'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Employer match must be a valid number',
                    'code': 'INVALID_EMPLOYER_MATCH'
                }), 400

            try:
                contribution_limit = float(data.get('contribution_limit', 0))
                if contribution_limit <= 0:
                    return jsonify({
                        'error': True,
                        'message': 'Contribution limit must be positive',
                        'code': 'INVALID_CONTRIBUTION_LIMIT'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Contribution limit must be a valid number',
                    'code': 'INVALID_CONTRIBUTION_LIMIT'
                }), 400

            try:
                employer_contribution = float(data.get('employer_contribution', -1))
                if employer_contribution < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Employer contribution cannot be negative',
                        'code': 'INVALID_EMPLOYER_CONTRIBUTION'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Employer contribution must be a valid number',
                    'code': 'INVALID_EMPLOYER_CONTRIBUTION'
                }), 400

        elif account_type == AccountType.TRADING:
            required_fields = ['broker_name', 'cash_balance']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'Trading account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_TRADING_FIELDS'
                }), 400

            if not data.get('broker_name', '').strip():
                return jsonify({
                    'error': True,
                    'message': 'Broker name cannot be empty',
                    'code': 'INVALID_BROKER_NAME'
                }), 400

            try:
                cash_balance = float(data.get('cash_balance', -1))
                if cash_balance < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Cash balance cannot be negative',
                        'code': 'INVALID_CASH_BALANCE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Cash balance must be a valid number',
                    'code': 'INVALID_CASH_BALANCE'
                }), 400

        elif account_type == AccountType.I_BONDS:
            required_fields = ['purchase_amount', 'purchase_date', 'current_value', 'fixed_rate', 'inflation_rate', 'maturity_date']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'I-bonds account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_IBONDS_FIELDS'
                }), 400

            try:
                purchase_amount = float(data.get('purchase_amount', 0))
                if purchase_amount <= 0:
                    return jsonify({
                        'error': True,
                        'message': 'Purchase amount must be positive',
                        'code': 'INVALID_PURCHASE_AMOUNT'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Purchase amount must be a valid number',
                    'code': 'INVALID_PURCHASE_AMOUNT'
                }), 400

            try:
                current_value = float(data.get('current_value', -1))
                if current_value < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Current value cannot be negative',
                        'code': 'INVALID_CURRENT_VALUE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Current value must be a valid number',
                    'code': 'INVALID_CURRENT_VALUE'
                }), 400

            try:
                fixed_rate = float(data.get('fixed_rate', -1))
                if fixed_rate < 0:
                    return jsonify({
                        'error': True,
                        'message': 'Fixed rate cannot be negative',
                        'code': 'INVALID_FIXED_RATE'
                    }), 400
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Fixed rate must be a valid number',
                    'code': 'INVALID_FIXED_RATE'
                }), 400

            # Validate dates
            for date_field in ['purchase_date', 'maturity_date']:
                if isinstance(data.get(date_field), str):
                    try:
                        parsed_date = date.fromisoformat(data[date_field])
                        if date_field == 'purchase_date' and parsed_date > date.today():
                            return jsonify({
                                'error': True,
                                'message': 'Purchase date cannot be in the future',
                                'code': 'INVALID_PURCHASE_DATE'
                            }), 400
                    except ValueError:
                        return jsonify({
                            'error': True,
                            'message': f'Invalid {date_field} format. Use YYYY-MM-DD',
                            'code': 'INVALID_DATE_FORMAT'
                        }), 400

        elif account_type == AccountType.HSA:
            required_fields = ['current_balance', 'annual_contribution_limit', 'current_year_contributions',
                             'employer_contributions', 'investment_balance', 'cash_balance']
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                return jsonify({
                    'error': True,
                    'message': f'HSA account missing required fields: {", ".join(missing_fields)}',
                    'code': 'MISSING_HSA_FIELDS'
                }), 400

            # Validate all numeric fields are non-negative
            numeric_fields = ['current_balance', 'annual_contribution_limit', 'current_year_contributions',
                            'employer_contributions', 'investment_balance', 'cash_balance']

            for field in numeric_fields:
                try:
                    value = float(data.get(field, -1))
                    if value < 0:
                        return jsonify({
                            'error': True,
                            'message': f'{field.replace("_", " ").title()} cannot be negative',
                            'code': f'INVALID_{field.upper()}'
                        }), 400
                except (ValueError, TypeError):
                    return jsonify({
                        'error': True,
                        'message': f'{field.replace("_", " ").title()} must be a valid number',
                        'code': f'INVALID_{field.upper()}'
                    }), 400

            # Validate that investment + cash balance equals current balance
            try:
                current_balance = float(data.get('current_balance', 0))
                investment_balance = float(data.get('investment_balance', 0))
                cash_balance = float(data.get('cash_balance', 0))

                total_balance = investment_balance + cash_balance
                if abs(total_balance - current_balance) > 0.01:  # Allow for small floating point differences
                    return jsonify({
                        'error': True,
                        'message': 'Investment balance plus cash balance must equal current balance',
                        'code': 'INVALID_HSA_BALANCE_MISMATCH'
                    }), 400
            except (ValueError, TypeError):
                # Individual field validation above will catch specific field errors
                pass

            # Validate contribution limits
            try:
                annual_limit = float(data.get('annual_contribution_limit', 0))
                current_contributions = float(data.get('current_year_contributions', 0))

                if current_contributions > annual_limit:
                    return jsonify({
                        'error': True,
                        'message': 'Current year contributions cannot exceed annual contribution limit',
                        'code': 'INVALID_HSA_CONTRIBUTION_LIMIT'
                    }), 400
            except (ValueError, TypeError):
                # Individual field validation above will catch specific field errors
                pass

        return None  # No validation errors

    except Exception as e:
        return jsonify({
            'error': True,
            'message': f'Validation error: {str(e)}',
            'code': 'VALIDATION_ERROR'
        }), 400


# Historical Data API Endpoints

@app.route('/api/accounts/<account_id>/history', methods=['GET'])
@require_auth
def get_account_history(account_id):
    """Get historical snapshots for an account with optional filtering."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Initialize historical data service
        historical_service = HistoricalDataService(db_service)

        # Parse query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')
        limit_str = request.args.get('limit')

        start_date = None
        end_date = None
        limit = None

        # Parse start_date
        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid start_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_START_DATE'
                }), 400

        # Parse end_date
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid end_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_END_DATE'
                }), 400

        # Parse limit
        if limit_str:
            try:
                limit = int(limit_str)
                if limit <= 0:
                    return jsonify({
                        'error': True,
                        'message': 'Limit must be a positive integer',
                        'code': 'INVALID_LIMIT'
                    }), 400
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Limit must be a valid integer',
                    'code': 'INVALID_LIMIT'
                }), 400

        # Get historical snapshots
        snapshots = historical_service.get_historical_snapshots(
            account_id, start_date, end_date, limit
        )

        # Convert snapshots to API response format
        snapshots_data = []
        for snapshot in snapshots:
            snapshot_dict = snapshot.to_dict()
            snapshots_data.append(snapshot_dict)

        return jsonify({
            'success': True,
            'account_id': account_id,
            'snapshots': snapshots_data,
            'count': len(snapshots_data),
            'filters': {
                'start_date': start_date_str,
                'end_date': end_date_str,
                'limit': limit
            }
        })

    except Exception as e:
        app.logger.error(f"Error retrieving account history for {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to retrieve account history',
            'code': 'HISTORY_RETRIEVAL_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/performance', methods=['GET'])
@require_auth
def get_account_performance(account_id):
    """Get performance metrics for an account over a time period."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Initialize historical data service
        historical_service = HistoricalDataService(db_service)

        # Parse query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = None
        end_date = None

        # Parse start_date
        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid start_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_START_DATE'
                }), 400

        # Parse end_date
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid end_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_END_DATE'
                }), 400

        # Calculate performance metrics
        performance = historical_service.calculate_performance_metrics(
            account_id, start_date, end_date
        )

        if performance is None:
            return jsonify({
                'error': True,
                'message': 'Insufficient historical data for performance calculation',
                'code': 'INSUFFICIENT_DATA'
            }), 400

        # Convert performance metrics to API response format
        performance_data = {
            'start_value': performance.start_value,
            'end_value': performance.end_value,
            'absolute_change': performance.absolute_change,
            'percentage_change': performance.percentage_change,
            'trend_direction': performance.trend_direction.value,
            'volatility': performance.volatility,
            'average_value': performance.average_value,
            'min_value': performance.min_value,
            'max_value': performance.max_value,
            'total_snapshots': performance.total_snapshots
        }

        return jsonify({
            'success': True,
            'account_id': account_id,
            'performance': performance_data,
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            }
        })

    except Exception as e:
        app.logger.error(f"Error calculating performance for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to calculate account performance',
            'code': 'PERFORMANCE_CALCULATION_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/trend', methods=['GET'])
@require_auth
def get_account_trend(account_id):
    """Get trend analysis for an account over a time period."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Initialize historical data service
        historical_service = HistoricalDataService(db_service)

        # Parse query parameters
        start_date_str = request.args.get('start_date')
        end_date_str = request.args.get('end_date')

        start_date = None
        end_date = None

        # Parse start_date
        if start_date_str:
            try:
                start_date = date.fromisoformat(start_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid start_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_START_DATE'
                }), 400

        # Parse end_date
        if end_date_str:
            try:
                end_date = date.fromisoformat(end_date_str)
            except ValueError:
                return jsonify({
                    'error': True,
                    'message': 'Invalid end_date format. Use YYYY-MM-DD',
                    'code': 'INVALID_END_DATE'
                }), 400

        # Analyze trend
        trend = historical_service.analyze_trend(account_id, start_date, end_date)

        if trend is None:
            return jsonify({
                'error': True,
                'message': 'Insufficient historical data for trend analysis (minimum 3 data points required)',
                'code': 'INSUFFICIENT_DATA'
            }), 400

        # Convert trend analysis to API response format
        trend_data = {
            'direction': trend.direction.value,
            'slope': trend.slope,
            'r_squared': trend.r_squared,
            'confidence': trend.confidence
        }

        return jsonify({
            'success': True,
            'account_id': account_id,
            'trend': trend_data,
            'period': {
                'start_date': start_date_str,
                'end_date': end_date_str
            }
        })

    except Exception as e:
        app.logger.error(f"Error analyzing trend for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to analyze account trend',
            'code': 'TREND_ANALYSIS_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/gains-losses', methods=['GET'])
@require_auth
def get_account_gains_losses(account_id):
    """Get gains and losses for an account over a specified period."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Initialize historical data service
        historical_service = HistoricalDataService(db_service)

        # Parse query parameters
        period_days_str = request.args.get('period_days', '30')

        try:
            period_days = int(period_days_str)
            if period_days <= 0:
                return jsonify({
                    'error': True,
                    'message': 'Period days must be a positive integer',
                    'code': 'INVALID_PERIOD_DAYS'
                }), 400
        except ValueError:
            return jsonify({
                'error': True,
                'message': 'Period days must be a valid integer',
                'code': 'INVALID_PERIOD_DAYS'
            }), 400

        # Calculate gains and losses
        gains_losses = historical_service.calculate_gains_losses(account_id, period_days)

        return jsonify({
            'success': True,
            'account_id': account_id,
            'gains_losses': gains_losses
        })

    except Exception as e:
        app.logger.error(f"Error calculating gains/losses for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to calculate gains and losses',
            'code': 'GAINS_LOSSES_CALCULATION_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/monthly-summary/<int:year>', methods=['GET'])
@require_auth
def get_account_monthly_summary(account_id, year):
    """Get monthly summary of account values for a specific year."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Check if account exists
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        # Validate year
        current_year = datetime.now().year
        if year < 2000 or year > current_year + 1:
            return jsonify({
                'error': True,
                'message': f'Year must be between 2000 and {current_year + 1}',
                'code': 'INVALID_YEAR'
            }), 400

        # Initialize historical data service
        historical_service = HistoricalDataService(db_service)

        # Get monthly summary
        monthly_summary = historical_service.get_monthly_summary(account_id, year)

        return jsonify({
            'success': True,
            'account_id': account_id,
            'year': year,
            'monthly_summary': monthly_summary
        })

    except Exception as e:
        app.logger.error(f"Error getting monthly summary for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to get monthly summary',
            'code': 'MONTHLY_SUMMARY_ERROR'
        }), 500


@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    return render_template('base.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return render_template('base.html'), 500

# Stock Position Management API Endpoints

@app.route('/api/accounts/<account_id>/positions', methods=['GET'])
@require_auth
def get_stock_positions(account_id):
    """Get all stock positions for a trading account."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Get stock positions
        positions = db_service.get_stock_positions(account_id)

        # Convert datetime objects to ISO strings for JSON serialization
        for position in positions:
            if isinstance(position.get('purchase_date'), datetime):
                position['purchase_date'] = position['purchase_date'].isoformat()
            if isinstance(position.get('last_price_update'), datetime):
                position['last_price_update'] = position['last_price_update'].isoformat()

        return jsonify({
            'success': True,
            'positions': positions,
            'count': len(positions)
        })

    except Exception as e:
        app.logger.error(f"Error retrieving stock positions for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to retrieve stock positions',
            'code': 'POSITIONS_RETRIEVAL_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/positions', methods=['POST'])
@require_auth
def add_stock_position(account_id):
    """Add a new stock position to a trading account."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Validate request data
        if not request.is_json:
            return jsonify({
                'error': True,
                'message': 'Request must be JSON',
                'code': 'INVALID_CONTENT_TYPE'
            }), 400

        try:
            data = request.get_json()
        except Exception:
            return jsonify({
                'error': True,
                'message': 'Invalid JSON format',
                'code': 'INVALID_JSON_FORMAT'
            }), 400

        if not data:
            return jsonify({
                'error': True,
                'message': 'Request body cannot be empty',
                'code': 'EMPTY_REQUEST_BODY'
            }), 400

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Validate required fields
        required_fields = ['symbol', 'shares', 'purchase_price', 'purchase_date']
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            return jsonify({
                'error': True,
                'message': f'Missing required fields: {", ".join(missing_fields)}',
                'code': 'MISSING_REQUIRED_FIELDS'
            }), 400

        # Validate field values
        try:
            symbol = data['symbol'].upper().strip()
            shares = float(data['shares'])
            purchase_price = float(data['purchase_price'])
            purchase_date_str = data['purchase_date']

            if not symbol:
                raise ValueError("Symbol cannot be empty")
            if shares <= 0:
                raise ValueError("Shares must be positive")
            if purchase_price <= 0:
                raise ValueError("Purchase price must be positive")

            # Parse purchase date
            try:
                purchase_date = date.fromisoformat(purchase_date_str)
                if purchase_date > date.today():
                    raise ValueError("Purchase date cannot be in the future")
            except ValueError as e:
                if "Purchase date cannot be in the future" in str(e):
                    raise e
                raise ValueError("Invalid purchase date format. Use YYYY-MM-DD")

        except (ValueError, TypeError) as e:
            return jsonify({
                'error': True,
                'message': f'Invalid field value: {str(e)}',
                'code': 'INVALID_FIELD_VALUE'
            }), 400

        # Check if position with same symbol already exists
        existing_positions = db_service.get_stock_positions(account_id)
        for pos in existing_positions:
            if pos['symbol'] == symbol:
                return jsonify({
                    'error': True,
                    'message': f'Position for symbol {symbol} already exists',
                    'code': 'POSITION_ALREADY_EXISTS'
                }), 409

        # Create stock position
        purchase_date_timestamp = int(purchase_date.strftime('%s'))
        position_id = db_service.create_stock_position(
            account_id, symbol, shares, purchase_price, purchase_date_timestamp
        )

        # Get the created position
        positions = db_service.get_stock_positions(account_id)
        created_position = next((p for p in positions if p['id'] == position_id), None)

        if created_position:
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(created_position.get('purchase_date'), datetime):
                created_position['purchase_date'] = created_position['purchase_date'].isoformat()
            if isinstance(created_position.get('last_price_update'), datetime):
                created_position['last_price_update'] = created_position['last_price_update'].isoformat()

        return jsonify({
            'success': True,
            'message': 'Stock position added successfully',
            'position': created_position
        }), 201

    except Exception as e:
        app.logger.error(f"Error adding stock position to account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to add stock position',
            'code': 'POSITION_CREATION_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/positions/<position_id>', methods=['PUT'])
@require_auth
def update_stock_position(account_id, position_id):
    """Update an existing stock position."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Validate request data
        if not request.is_json:
            return jsonify({
                'error': True,
                'message': 'Request must be JSON',
                'code': 'INVALID_CONTENT_TYPE'
            }), 400

        data = request.get_json()
        if not data:
            return jsonify({
                'error': True,
                'message': 'Request body cannot be empty',
                'code': 'EMPTY_REQUEST_BODY'
            }), 400

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Check if position exists
        positions = db_service.get_stock_positions(account_id)
        existing_position = next((p for p in positions if p['id'] == position_id), None)
        if not existing_position:
            return jsonify({
                'error': True,
                'message': 'Stock position not found',
                'code': 'POSITION_NOT_FOUND'
            }), 404

        # Validate and process update data
        update_data = {}

        if 'shares' in data:
            try:
                shares = float(data['shares'])
                if shares <= 0:
                    raise ValueError("Shares must be positive")
                update_data['shares'] = shares
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Invalid shares value',
                    'code': 'INVALID_SHARES'
                }), 400

        if 'purchase_price' in data:
            try:
                purchase_price = float(data['purchase_price'])
                if purchase_price <= 0:
                    raise ValueError("Purchase price must be positive")
                update_data['purchase_price'] = purchase_price
            except (ValueError, TypeError):
                return jsonify({
                    'error': True,
                    'message': 'Invalid purchase price value',
                    'code': 'INVALID_PURCHASE_PRICE'
                }), 400

        if 'purchase_date' in data:
            try:
                purchase_date = date.fromisoformat(data['purchase_date'])
                if purchase_date > date.today():
                    raise ValueError("Purchase date cannot be in the future")
                update_data['purchase_date'] = int(datetime.combine(purchase_date, datetime.min.time()).timestamp())
            except ValueError as e:
                if "Purchase date cannot be in the future" in str(e):
                    return jsonify({
                        'error': True,
                        'message': str(e),
                        'code': 'INVALID_PURCHASE_DATE'
                    }), 400
                return jsonify({
                    'error': True,
                    'message': 'Invalid purchase date format. Use YYYY-MM-DD',
                    'code': 'INVALID_DATE_FORMAT'
                }), 400

        if not update_data:
            return jsonify({
                'error': True,
                'message': 'No valid fields to update',
                'code': 'NO_UPDATE_FIELDS'
            }), 400

        # Update position in database
        # Note: This requires extending the database service to support position updates
        # For now, we'll implement a basic update by recreating the position

        # Get current position data and merge with updates
        current_data = existing_position.copy()
        current_data.update(update_data)

        # Delete old position and create new one with updated data
        db_service.delete_stock_position(position_id)

        # Handle purchase_date conversion
        purchase_date_timestamp = current_data.get('purchase_date')
        if purchase_date_timestamp is None:
            # Use existing purchase_date
            existing_date = existing_position['purchase_date']

            if isinstance(existing_date, datetime):
                purchase_date_timestamp = int(existing_date.timestamp())
            elif isinstance(existing_date, str):
                # Parse ISO format string to datetime then to timestamp
                try:
                    purchase_date_obj = datetime.fromisoformat(existing_date.replace('Z', '+00:00'))
                    purchase_date_timestamp = int(purchase_date_obj.timestamp())
                except ValueError:
                    # Try parsing as date only
                    purchase_date_obj = date.fromisoformat(existing_date)
                    purchase_date_dt = datetime.combine(purchase_date_obj, datetime.min.time())
                    purchase_date_timestamp = int(purchase_date_dt.timestamp())
            else:
                purchase_date_timestamp = int(existing_date)

        # Ensure timestamp is always an integer
        if isinstance(purchase_date_timestamp, datetime):
            purchase_date_timestamp = int(purchase_date_timestamp.timestamp())
        elif isinstance(purchase_date_timestamp, str):
            # Parse ISO string to timestamp
            try:
                dt_obj = datetime.fromisoformat(purchase_date_timestamp.replace('Z', '+00:00'))
                purchase_date_timestamp = int(dt_obj.timestamp())
            except ValueError:
                # Try as date only
                date_obj = date.fromisoformat(purchase_date_timestamp)
                dt_obj = datetime.combine(date_obj, datetime.min.time())
                purchase_date_timestamp = int(dt_obj.timestamp())

        new_position_id = db_service.create_stock_position(
            account_id,
            existing_position['symbol'],  # Use existing symbol, not from update data
            current_data['shares'],
            current_data['purchase_price'],
            purchase_date_timestamp
        )

        # Get the updated position
        positions = db_service.get_stock_positions(account_id)
        updated_position = next((p for p in positions if p['id'] == new_position_id), None)

        if updated_position:
            # Convert datetime objects to ISO strings for JSON serialization
            if isinstance(updated_position.get('purchase_date'), datetime):
                updated_position['purchase_date'] = updated_position['purchase_date'].isoformat()
            if isinstance(updated_position.get('last_price_update'), datetime):
                updated_position['last_price_update'] = updated_position['last_price_update'].isoformat()

        return jsonify({
            'success': True,
            'message': 'Stock position updated successfully',
            'position': updated_position
        })

    except Exception as e:
        app.logger.error(f"Error updating stock position {position_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to update stock position',
            'code': 'POSITION_UPDATE_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/positions/<position_id>', methods=['DELETE'])
@require_auth
def delete_stock_position(account_id, position_id):
    """Delete a stock position from a trading account."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Check if position exists
        positions = db_service.get_stock_positions(account_id)
        existing_position = next((p for p in positions if p['id'] == position_id), None)
        if not existing_position:
            return jsonify({
                'error': True,
                'message': 'Stock position not found',
                'code': 'POSITION_NOT_FOUND'
            }), 404

        # Delete the position
        success = db_service.delete_stock_position(position_id)
        if not success:
            return jsonify({
                'error': True,
                'message': 'Failed to delete stock position from database',
                'code': 'DATABASE_DELETE_ERROR'
            }), 500

        return jsonify({
            'success': True,
            'message': 'Stock position deleted successfully',
            'deleted_position_id': position_id
        })

    except Exception as e:
        app.logger.error(f"Error deleting stock position {position_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to delete stock position',
            'code': 'POSITION_DELETE_ERROR'
        }), 500


@app.route('/api/accounts/<account_id>/positions/update-prices', methods=['POST'])
@require_auth
def update_stock_prices(account_id):
    """Update stock prices for all positions in a trading account."""
    try:
        from services.stock_prices import StockPriceService

        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Get stock positions
        positions = db_service.get_stock_positions(account_id)
        if not positions:
            return jsonify({
                'success': True,
                'message': 'No positions to update',
                'updated_positions': [],
                'update_results': []
            })

        # Initialize stock price service
        stock_service = StockPriceService()

        # Extract symbols from positions
        symbols = [pos['symbol'] for pos in positions]

        # Fetch current prices
        price_results = stock_service.get_batch_prices(symbols)

        # Update positions with new prices
        updated_positions = []
        update_results = []

        for position in positions:
            symbol = position['symbol']
            price_result = price_results.get(symbol)

            if price_result and price_result.success:
                # Update price in database
                success = db_service.update_stock_price(position['id'], price_result.price)
                if success:
                    # Get updated position data
                    updated_positions_data = db_service.get_stock_positions(account_id)
                    updated_position = next((p for p in updated_positions_data if p['id'] == position['id']), None)

                    if updated_position:
                        # Convert datetime objects to ISO strings for JSON serialization
                        if isinstance(updated_position.get('purchase_date'), datetime):
                            updated_position['purchase_date'] = updated_position['purchase_date'].isoformat()
                        if isinstance(updated_position.get('last_price_update'), datetime):
                            updated_position['last_price_update'] = updated_position['last_price_update'].isoformat()

                        # Calculate portfolio metrics
                        current_value = updated_position['current_price'] * updated_position['shares']
                        cost_basis = updated_position['purchase_price'] * updated_position['shares']
                        unrealized_gain_loss = current_value - cost_basis
                        unrealized_gain_loss_pct = (unrealized_gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

                        updated_position['current_value'] = current_value
                        updated_position['unrealized_gain_loss'] = unrealized_gain_loss
                        updated_position['unrealized_gain_loss_pct'] = unrealized_gain_loss_pct

                        updated_positions.append(updated_position)

                    update_results.append({
                        'symbol': symbol,
                        'success': True,
                        'price': price_result.price,
                        'timestamp': price_result.timestamp.isoformat() if price_result.timestamp else None
                    })
                else:
                    update_results.append({
                        'symbol': symbol,
                        'success': False,
                        'error': 'Failed to update price in database'
                    })
            else:
                update_results.append({
                    'symbol': symbol,
                    'success': False,
                    'error': price_result.error if price_result else 'Unknown error'
                })

        # Create historical snapshot for account value change if any prices were updated
        successful_updates = [r for r in update_results if r['success']]
        if successful_updates:
            from services.historical import HistoricalDataService
            historical_service = HistoricalDataService(db_service)

            # Create a temporary account object to calculate new value
            account_data_clean = account_data.copy()
            if 'type' in account_data_clean:
                account_data_clean['account_type'] = account_data_clean['type']
                del account_data_clean['type']

            # Remove database-specific fields
            db_fields = ['schema_version', 'is_demo']
            for field in db_fields:
                if field in account_data_clean:
                    del account_data_clean[field]

            # Convert datetime objects to ISO strings for from_dict method
            datetime_fields = ['created_date', 'last_updated']
            for field in datetime_fields:
                if field in account_data_clean and isinstance(account_data_clean[field], datetime):
                    account_data_clean[field] = account_data_clean[field].isoformat()

            account = AccountFactory.create_account_from_dict(account_data_clean)
            historical_service.create_snapshot(account, ChangeType.STOCK_PRICE_UPDATE)

        return jsonify({
            'success': True,
            'message': f'Updated prices for {len(successful_updates)} out of {len(positions)} positions',
            'updated_positions': updated_positions,
            'update_results': update_results,
            'total_positions': len(positions),
            'successful_updates': len(successful_updates)
        })

    except Exception as e:
        app.logger.error(f"Error updating stock prices for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to update stock prices',
            'code': 'PRICE_UPDATE_ERROR'
        }), 500


# Global Stock Price Management API Endpoints

@app.route('/api/stocks/prices', methods=['POST'])
@api_endpoint
@log_data_operation('UPDATE', 'stock_prices')
def update_all_stock_prices():
    """Update stock prices for all trading account positions across all accounts."""
    from services.stock_prices import StockPriceService

    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    try:
        # Get all trading accounts
        all_accounts = db_service.get_accounts('TRADING')

        if not all_accounts:
            return jsonify({
                'success': True,
                'message': 'No trading accounts found',
                'updated_positions': 0,
                'failed_positions': 0,
                'results': []
            })

        stock_service = StockPriceService()
        total_updated = 0
        total_failed = 0
        all_results = []

        # Process each trading account
        for account in all_accounts:
            account_id = account['id']

            try:
                # Get stock positions for this account
                positions = db_service.get_stock_positions(account_id)

                if not positions:
                    continue

                # Extract symbols and update prices
                symbols = [pos['symbol'] for pos in positions if pos.get('symbol')]

                if not symbols:
                    continue

                # Get updated prices
                price_results = stock_service.get_batch_prices(symbols)

                # Update each position
                for position in positions:
                    symbol = position.get('symbol')
                    if not symbol:
                        continue

                    price_result = price_results.get(symbol.upper())

                    if price_result and price_result.success:
                        # Update position in database
                        update_data = {
                            'current_price': price_result.price,
                            'last_updated': price_result.timestamp
                        }

                        success = db_service.update_stock_position(
                            account_id,
                            position['id'],
                            update_data
                        )

                        if success:
                            total_updated += 1
                            all_results.append({
                                'account_id': account_id,
                                'position_id': position['id'],
                                'symbol': symbol,
                                'success': True,
                                'price': price_result.price,
                                'timestamp': price_result.timestamp.isoformat()
                            })
                        else:
                            total_failed += 1
                            all_results.append({
                                'account_id': account_id,
                                'position_id': position['id'],
                                'symbol': symbol,
                                'success': False,
                                'error': 'Database update failed'
                            })
                    else:
                        total_failed += 1
                        error_msg = price_result.error if price_result else 'Price fetch failed'
                        all_results.append({
                            'account_id': account_id,
                            'position_id': position['id'],
                            'symbol': symbol,
                            'success': False,
                            'error': error_msg
                        })

            except Exception as e:
                app_logger.error(f"Error updating prices for account {account_id}: {str(e)}")
                # Continue with other accounts
                continue

        return jsonify({
            'success': True,
            'message': f'Stock price update completed. Updated: {total_updated}, Failed: {total_failed}',
            'updated_positions': total_updated,
            'failed_positions': total_failed,
            'results': all_results
        })

    except Exception as e:
        app_logger.error(f"Error in global stock price update: {str(e)}")
        raise SystemError(
            message="Failed to update stock prices",
            code="SYS_003",
            user_action="Please try again later or check your internet connection"
        )


@app.route('/api/accounts/<account_id>/portfolio-summary', methods=['GET'])
@require_auth
def get_account_portfolio_summary(account_id):
    """Get portfolio summary with total value and unrealized gains/losses."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Verify account exists and is a trading account
        account_data = db_service.get_account(account_id)
        if not account_data:
            return jsonify({
                'error': True,
                'message': 'Account not found',
                'code': 'ACCOUNT_NOT_FOUND'
            }), 404

        if account_data.get('type') != AccountType.TRADING.value:
            return jsonify({
                'error': True,
                'message': 'Account is not a trading account',
                'code': 'INVALID_ACCOUNT_TYPE'
            }), 400

        # Get stock positions
        positions = db_service.get_stock_positions(account_id)

        # Calculate portfolio metrics
        total_stock_value = 0.0
        total_cost_basis = 0.0
        total_unrealized_gain_loss = 0.0
        position_count = len(positions)

        position_summaries = []

        for position in positions:
            current_price = position.get('current_price') or position['purchase_price']
            shares = position['shares']
            purchase_price = position['purchase_price']

            current_value = current_price * shares
            cost_basis = purchase_price * shares
            unrealized_gain_loss = current_value - cost_basis
            unrealized_gain_loss_pct = (unrealized_gain_loss / cost_basis) * 100 if cost_basis > 0 else 0

            total_stock_value += current_value
            total_cost_basis += cost_basis
            total_unrealized_gain_loss += unrealized_gain_loss

            position_summaries.append({
                'symbol': position['symbol'],
                'shares': shares,
                'purchase_price': purchase_price,
                'current_price': current_price,
                'current_value': current_value,
                'cost_basis': cost_basis,
                'unrealized_gain_loss': unrealized_gain_loss,
                'unrealized_gain_loss_pct': unrealized_gain_loss_pct,
                'last_price_update': position.get('last_price_update').isoformat() if position.get('last_price_update') else None
            })

        # Calculate total portfolio percentage
        total_unrealized_gain_loss_pct = (total_unrealized_gain_loss / total_cost_basis) * 100 if total_cost_basis > 0 else 0

        # Get cash balance from account
        cash_balance = account_data.get('cash_balance', 0.0)
        total_portfolio_value = cash_balance + total_stock_value

        return jsonify({
            'success': True,
            'portfolio_summary': {
                'account_id': account_id,
                'account_name': account_data.get('name'),
                'broker_name': account_data.get('broker_name'),
                'cash_balance': cash_balance,
                'total_stock_value': total_stock_value,
                'total_portfolio_value': total_portfolio_value,
                'total_cost_basis': total_cost_basis,
                'total_unrealized_gain_loss': total_unrealized_gain_loss,
                'total_unrealized_gain_loss_pct': total_unrealized_gain_loss_pct,
                'position_count': position_count,
                'positions': position_summaries
            }
        })

    except Exception as e:
        app.logger.error(f"Error getting portfolio summary for account {account_id}: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to get portfolio summary',
            'code': 'PORTFOLIO_SUMMARY_ERROR'
        }), 500


@app.route('/api/portfolio/summary', methods=['GET'])
@api_endpoint
@log_data_operation('READ', 'portfolio_summary')
def get_portfolio_summary():
    """Get consolidated portfolio summary with performance metrics."""
    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Get all accounts
        accounts_data = db_service.get_accounts()
        if not accounts_data:
            return jsonify({
                'success': True,
                'total_networth': 0.0,
                'account_types': {},
                'institutions': [],
                'total_accounts': 0,
                'performance': None
            })

        # Calculate totals by account type
        account_totals = {
            'CD': {'count': 0, 'value': 0.0, 'accounts': []},
            'SAVINGS': {'count': 0, 'value': 0.0, 'accounts': []},
            '401K': {'count': 0, 'value': 0.0, 'accounts': []},
            'TRADING': {'count': 0, 'value': 0.0, 'accounts': []},
            'I_BONDS': {'count': 0, 'value': 0.0, 'accounts': []}
        }

        total_networth = 0.0
        institutions = set()
        historical_service = HistoricalDataService(db_service)

        for account_data in accounts_data:
            try:
                # Create account object to get current value
                account_data_clean = account_data.copy()
                if 'type' in account_data_clean:
                    account_data_clean['account_type'] = account_data_clean['type']
                    del account_data_clean['type']

                # Remove database-specific fields
                db_fields = ['schema_version', 'is_demo']
                for field in db_fields:
                    if field in account_data_clean:
                        del account_data_clean[field]

                # Convert datetime objects to ISO strings
                datetime_fields = ['created_date', 'last_updated']
                for field in datetime_fields:
                    if field in account_data_clean and isinstance(account_data_clean[field], datetime):
                        account_data_clean[field] = account_data_clean[field].isoformat()

                # Convert date objects to ISO strings
                date_fields = ['maturity_date', 'purchase_date']
                for field in date_fields:
                    if field in account_data_clean and isinstance(account_data_clean[field], date):
                        account_data_clean[field] = account_data_clean[field].isoformat()

                account = AccountFactory.create_account_from_dict(account_data_clean)
                current_value = account.get_current_value()
                account_type = account.account_type.value

                # Add to totals
                if account_type in account_totals:
                    account_totals[account_type]['count'] += 1
                    account_totals[account_type]['value'] += current_value

                    # Get recent performance for this account
                    gains_losses = historical_service.calculate_gains_losses(account.id, 30)

                    account_summary = {
                        'id': account.id,
                        'name': account.name,
                        'institution': account.institution,
                        'current_value': current_value,
                        'monthly_change': gains_losses.get('absolute_gain_loss', 0.0),
                        'monthly_change_percent': gains_losses.get('percentage_gain_loss', 0.0)
                    }
                    account_totals[account_type]['accounts'].append(account_summary)

                total_networth += current_value
                institutions.add(account.institution)

            except Exception as e:
                app.logger.error(f"Error processing account {account_data.get('id', 'unknown')}: {str(e)}")
                continue

        # Calculate portfolio-level performance
        # Get historical snapshots for all accounts to calculate overall performance
        end_date = date.today()
        start_date = end_date - timedelta(days=30)

        portfolio_start_value = 0.0
        portfolio_end_value = total_networth

        for account_data in accounts_data:
            account_id = account_data.get('id')
            if account_id:
                start_value = historical_service.get_value_at_date(account_id, start_date)
                if start_value:
                    portfolio_start_value += start_value

        # Calculate portfolio performance
        portfolio_change = portfolio_end_value - portfolio_start_value
        portfolio_change_percent = (portfolio_change / portfolio_start_value * 100) if portfolio_start_value > 0 else 0.0

        return jsonify({
            'success': True,
            'total_networth': total_networth,
            'account_types': account_totals,
            'institutions': list(institutions),
            'total_accounts': len(accounts_data),
            'total_institutions': len(institutions),
            'performance': {
                'monthly_change': portfolio_change,
                'monthly_change_percent': portfolio_change_percent,
                'start_value': portfolio_start_value,
                'end_value': portfolio_end_value
            }
        })

    except Exception as e:
        app.logger.error(f"Error retrieving portfolio summary: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to retrieve portfolio summary',
            'code': 'PORTFOLIO_SUMMARY_ERROR'
        }), 500


# Watchlist API Endpoints

@app.route('/api/watchlist', methods=['GET'])
@api_endpoint
@log_data_operation('READ', 'watchlist')
def get_watchlist():
    """Get all watchlist items for the authenticated user."""
    from services.watchlist import WatchlistService
    from services.stock_prices import StockPriceService

    try:
        db_service = auth_manager.get_database_service()
        if not db_service:
            app.logger.error("Database service not available for watchlist request")
            raise DatabaseError(
                message="Database service not available",
                code="DB_001",
                user_action="Please try logging in again"
            )

        # Initialize services
        stock_service = StockPriceService()
        watchlist_service = WatchlistService(db_service, stock_service)

        # Retrieve watchlist items
        app.logger.info("Fetching watchlist items...")
        watchlist_items = watchlist_service.get_watchlist()
        app.logger.info(f"Found {len(watchlist_items)} watchlist items")

        # Convert to API response format
        items = []
        for item in watchlist_items:
            try:
                item_dict = item.to_dict()
                items.append(item_dict)
            except Exception as e:
                app.logger.error(f"Error converting watchlist item to dict: {e}")
                continue

        app.logger.info(f"Returning {len(items)} watchlist items")
        return jsonify({
            'success': True,
            'watchlist': items,
            'count': len(items)
        })

    except Exception as e:
        app.logger.error(f"Error in get_watchlist: {e}")
        return jsonify({
            'success': False,
            'error': str(e),
            'watchlist': [],
            'count': 0
        }), 500


@app.route('/api/watchlist', methods=['POST'])
@api_endpoint
@log_data_operation('CREATE', 'watchlist')
def add_to_watchlist():
    """Add a stock to the watchlist with comprehensive error handling."""
    from services.watchlist import WatchlistService, WatchlistServiceError
    from services.stock_prices import StockPriceService
    from services.error_handler import (
        WatchlistDuplicateError, WatchlistLimitExceededError,
        StockValidationError, ValidationError, MissingFieldError
    )

    # Validate request data
    if not request.is_json:
        raise ValidationError(
            message="Request must be JSON",
            code="VAL_001",
            user_action="Please send request with Content-Type: application/json"
        )

    data = request.get_json()
    if not data:
        raise ValidationError(
            message="Request body cannot be empty",
            code="VAL_002",
            user_action="Please provide stock symbol in request body"
        )

    # Validate required fields
    symbol = data.get('symbol')
    if not symbol:
        raise MissingFieldError('symbol')

    notes = data.get('notes', '')

    # Validate notes length if provided
    if notes and len(notes) > 500:
        raise ValidationError(
            message="Notes cannot exceed 500 characters",
            code="VAL_NOTES_TOO_LONG",
            user_action="Please shorten your notes to 500 characters or less"
        )

    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Initialize services
    stock_service = StockPriceService()
    watchlist_service = WatchlistService(db_service, stock_service)

    try:
        # Add stock to watchlist
        item_id = watchlist_service.add_stock(symbol, notes)

        # Get the created item for response
        created_item = watchlist_service.get_stock_details(symbol)
        if not created_item:
            raise SystemError(
                "Failed to retrieve created watchlist item",
                "SYS_001"
            )

        return jsonify({
            'success': True,
            'message': f'Stock {symbol.upper()} added to watchlist',
            'item': created_item.to_dict()
        }), 201

    except (WatchlistDuplicateError, WatchlistLimitExceededError, StockValidationError):
        # Re-raise specific watchlist errors
        raise
    except WatchlistServiceError as e:
        # Handle generic watchlist service errors
        raise SystemError(
            f"Watchlist operation failed: {str(e)}",
            "SYS_WATCHLIST_001"
        )


@app.route('/api/watchlist/<symbol>', methods=['DELETE'])
@api_endpoint
@log_data_operation('DELETE', 'watchlist')
def remove_from_watchlist(symbol):
    """Remove a stock from the watchlist."""
    from services.watchlist import WatchlistService, WatchlistServiceError
    from services.stock_prices import StockPriceService

    if not symbol:
        raise ValidationError(
            message="Stock symbol is required",
            code="VAL_003",
            user_action="Please provide a valid stock symbol"
        )

    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Initialize services
    stock_service = StockPriceService()
    watchlist_service = WatchlistService(db_service, stock_service)

    try:
        # Remove stock from watchlist
        removed = watchlist_service.remove_stock(symbol)

        if not removed:
            raise ValidationError(
                f"Stock {symbol.upper()} not found in watchlist",
                "VAL_009",
                user_action="Please check the stock symbol"
            )

        return jsonify({
            'success': True,
            'message': f'Stock {symbol.upper()} removed from watchlist',
            'removed_symbol': symbol.upper()
        })

    except WatchlistServiceError as e:
        raise SystemError(
            str(e),
            "SYS_003"
        )


@app.route('/api/watchlist/<symbol>', methods=['GET'])
@api_endpoint
@log_data_operation('READ', 'watchlist')
def get_watchlist_stock(symbol):
    """Get details for a specific stock in the watchlist."""
    from services.watchlist import WatchlistService, WatchlistServiceError
    from services.stock_prices import StockPriceService

    if not symbol:
        raise ValidationError(
            message="Stock symbol is required",
            code="VAL_003",
            user_action="Please provide a valid stock symbol"
        )

    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Initialize services
    stock_service = StockPriceService()
    watchlist_service = WatchlistService(db_service, stock_service)

    try:
        # Get stock details
        item = watchlist_service.get_stock_details(symbol)

        if not item:
            raise ValidationError(
                f"Stock {symbol.upper()} not found in watchlist",
                "VAL_010",
                user_action="Please check the stock symbol"
            )

        return jsonify({
            'success': True,
            'item': item.to_dict()
        })

    except WatchlistServiceError as e:
        raise SystemError(
            str(e),
            "SYS_004"
        )


@app.route('/debug/update-prices')
@require_auth
def debug_update_prices():
    """Debug endpoint to force update watchlist prices."""
    try:
        from services.watchlist import WatchlistService
        from services.stock_prices import StockPriceService

        db_service = auth_manager.get_database_service()
        if not db_service:
            return "Database service not available", 500

        stock_service = StockPriceService()
        watchlist_service = WatchlistService(db_service, stock_service)

        # Get current watchlist
        watchlist = watchlist_service.get_watchlist()

        if not watchlist:
            return "No items in watchlist", 200

        result_html = "<h2>Watchlist Price Update Debug</h2>"
        result_html += f"<p>Found {len(watchlist)} items in watchlist:</p><ul>"

        for item in watchlist:
            result_html += f"<li>{item.symbol}: ${item.current_price or 0:.2f} (last updated: {item.last_price_update or 'Never'})</li>"

        result_html += "</ul><h3>Updating prices...</h3><ul>"

        # Update each item individually for better debugging
        for item in watchlist:
            try:
                current_price = stock_service.get_current_price(item.symbol)

                # Calculate daily change
                daily_change = None
                daily_change_percent = None
                if item.current_price is not None:
                    daily_change = current_price - item.current_price
                    if item.current_price > 0:
                        daily_change_percent = (daily_change / item.current_price) * 100

                # Update the item
                item.update_price(
                    current_price=current_price,
                    daily_change=daily_change,
                    daily_change_percent=daily_change_percent
                )

                # Store it
                watchlist_service._store_watchlist_item(item)

                result_html += f"<li>✓ {item.symbol}: Updated to ${current_price:.2f}"
                if daily_change is not None:
                    change_sign = "+" if daily_change >= 0 else ""
                    result_html += f" ({change_sign}{daily_change:.2f}, {change_sign}{daily_change_percent:.2f}%)"
                result_html += "</li>"

            except Exception as e:
                result_html += f"<li>✗ {item.symbol}: Failed - {str(e)}</li>"

        result_html += "</ul><p><a href='/watchlist'>← Back to Watchlist</a></p>"
        return result_html

    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/api/watchlist/prices', methods=['PUT'])
@api_endpoint
@log_data_operation('UPDATE', 'watchlist_prices')
def update_watchlist_prices():
    """Update prices for all watchlist items in batch with comprehensive error handling."""
    from services.watchlist import WatchlistService, WatchlistServiceError
    from services.stock_prices import StockPriceService
    from services.error_handler import WatchlistPriceUpdateError

    db_service = auth_manager.get_database_service()
    if not db_service:
        raise DatabaseError(
            message="Database service not available",
            code="DB_001",
            user_action="Please try logging in again"
        )

    # Initialize services
    stock_service = StockPriceService()
    watchlist_service = WatchlistService(db_service, stock_service)

    try:
        # Update prices for all watchlist items
        update_result = watchlist_service.update_prices()

        summary = update_result.get('summary', {})
        total_items = summary.get('total_items', 0)
        successful_updates = summary.get('successful_updates', 0)
        failed_updates = summary.get('failed_updates', 0)
        failed_symbols = summary.get('failed_symbols', [])

        # Determine response status based on results
        if total_items == 0:
            message = "No stocks in watchlist to update"
        elif failed_updates == 0:
            message = f"All {successful_updates} stock prices updated successfully"
        elif successful_updates == 0:
            message = f"Failed to update any stock prices ({failed_updates} failures)"
        else:
            message = f"Price update completed: {successful_updates}/{total_items} successful"

        # If significant failures occurred, include warning in response
        response_data = {
            'success': True,
            'message': message,
            'summary': summary,
            'results': update_result.get('results', {}),
            'timestamp': update_result.get('timestamp', datetime.now().isoformat())
        }

        # Add warnings for partial failures
        if failed_updates > 0:
            response_data['warnings'] = []

            if failed_updates > successful_updates and total_items > 1:
                response_data['warnings'].append("Majority of price updates failed. This may indicate a network or API issue.")

            if len(failed_symbols) <= 5:
                response_data['warnings'].append(f"Failed to update prices for: {', '.join(failed_symbols)}")
            else:
                response_data['warnings'].append(f"Failed to update prices for {len(failed_symbols)} stocks")

        return jsonify(response_data)

    except WatchlistServiceError as e:
        # Handle specific watchlist service errors
        if "network" in str(e).lower() or "timeout" in str(e).lower():
            raise SystemError(
                "Network error during price update. Please check your internet connection and try again.",
                "SYS_NETWORK_001"
            )
        elif "rate limit" in str(e).lower():
            raise SystemError(
                "Rate limit exceeded for stock price API. Please wait a moment before trying again.",
                "SYS_RATE_LIMIT_001"
            )
        else:
            raise SystemError(
                f"Failed to update watchlist prices: {str(e)}",
                "SYS_WATCHLIST_PRICE_001"
            )


# Data Export/Import API Endpoints

@app.route('/api/export', methods=['GET'])
@api_endpoint
@log_data_operation('READ', 'export')
def export_data():
    """Export encrypted backup of all application data."""
    try:
        db_service = auth_manager.get_database_service()
        encryption_service = auth_manager.get_encryption_service()

        if not db_service or not encryption_service:
            return jsonify({
                'error': True,
                'message': 'Required services not available',
                'code': 'SERVICES_NOT_AVAILABLE'
            }), 500

        from services.export_import import ExportImportService
        export_service = ExportImportService(db_service, encryption_service)

        # Get export options from query parameters
        include_historical = request.args.get('include_historical', 'true').lower() == 'true'

        # Export data
        export_data = export_service.export_data(include_historical=include_historical)

        # Create encrypted backup
        encrypted_backup = export_service.create_encrypted_backup(export_data)

        # Generate filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'networth_backup_{timestamp}.nwb'

        # Return encrypted backup as downloadable file using secure method
        from flask import Response
        from werkzeug.http import dump_header

        # Use Werkzeug's secure header generation to prevent injection
        response = Response(
            encrypted_backup,
            mimetype='application/octet-stream',
            headers={
                'Content-Disposition': dump_header('attachment', filename=filename),
                'Content-Length': len(encrypted_backup)
            }
        )

        return response

    except Exception as e:
        app.logger.error(f"Error exporting data: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to export data',
            'code': 'EXPORT_ERROR',
            'details': str(e)
        }), 500


@app.route('/api/export/info', methods=['GET'])
@require_auth
def export_info():
    """Get information about exportable data without performing export."""
    try:
        db_service = auth_manager.get_database_service()

        if not db_service:
            return jsonify({
                'error': True,
                'message': 'Database service not available',
                'code': 'DB_SERVICE_ERROR'
            }), 500

        # Get data counts
        accounts = db_service.get_accounts()
        accounts_count = len(accounts)

        # Count stock positions
        stock_positions_count = 0
        for account in accounts:
            if account.get('type') == 'TRADING':
                positions = db_service.get_stock_positions(account['id'])
                stock_positions_count += len(positions)

        # Count historical snapshots
        historical_snapshots_count = 0
        for account in accounts:
            snapshots = db_service.get_historical_snapshots(account['id'])
            historical_snapshots_count += len(snapshots)

        return jsonify({
            'success': True,
            'export_info': {
                'accounts_count': accounts_count,
                'stock_positions_count': stock_positions_count,
                'historical_snapshots_count': historical_snapshots_count,
                'estimated_backup_size': 'Variable based on data volume',
                'supported_formats': ['.nwb (Networth Backup)'],
                'encryption': 'AES-128 with master password'
            }
        })

    except Exception as e:
        app.logger.error(f"Error getting export info: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to get export information',
            'code': 'EXPORT_INFO_ERROR'
        }), 500


@app.route('/api/import', methods=['POST'])
@api_endpoint
@log_data_operation('CREATE', 'import')
def import_data():
    """Import data from encrypted backup file."""
    try:
        db_service = auth_manager.get_database_service()
        encryption_service = auth_manager.get_encryption_service()

        if not db_service or not encryption_service:
            return jsonify({
                'error': True,
                'message': 'Required services not available',
                'code': 'SERVICES_NOT_AVAILABLE'
            }), 500

        # Check if file was uploaded
        if 'backup_file' not in request.files:
            return jsonify({
                'error': True,
                'message': 'No backup file provided',
                'code': 'NO_FILE_PROVIDED'
            }), 400

        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            return jsonify({
                'error': True,
                'message': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400

        # Get import options
        overwrite_existing = request.form.get('overwrite_existing', 'false').lower() == 'true'
        validate_only = request.form.get('validate_only', 'false').lower() == 'true'
        backup_password = request.form.get('backup_password', '').strip()

        # Read backup file
        try:
            encrypted_backup = backup_file.read()
        except Exception as e:
            return jsonify({
                'error': True,
                'message': 'Failed to read backup file',
                'code': 'FILE_READ_ERROR',
                'details': str(e)
            }), 400

        from services.export_import import ExportImportService

        # Use backup password if provided, otherwise use current session's encryption service
        if backup_password:
            # Create temporary encryption service with backup password
            from services.encryption import EncryptionService
            backup_encryption_service = EncryptionService()

            # Use the same salt as demo database for demo backups
            demo_salt = b'demo_salt_123456'
            backup_encryption_service.derive_key(backup_password, demo_salt)

            import_service = ExportImportService(db_service, backup_encryption_service)
        else:
            import_service = ExportImportService(db_service, encryption_service)

        # Decrypt and validate backup
        try:
            backup_data = import_service.decrypt_backup(encrypted_backup)
        except Exception as e:
            error_message = 'Failed to decrypt backup file.'
            if backup_password:
                error_message += ' Please check the backup password.'
            else:
                error_message += ' Please check your master password or provide the backup password.'

            return jsonify({
                'error': True,
                'message': error_message,
                'code': 'DECRYPTION_ERROR',
                'details': str(e)
            }), 400

        # Validate backup integrity
        validation_results = import_service.validate_backup_integrity(backup_data)

        if not validation_results['valid']:
            return jsonify({
                'error': True,
                'message': 'Backup file validation failed',
                'code': 'BACKUP_VALIDATION_ERROR',
                'validation_results': validation_results
            }), 400

        # If validation only, return validation results
        if validate_only:
            return jsonify({
                'success': True,
                'message': 'Backup file validation successful',
                'validation_results': validation_results
            })

        # Import data
        try:
            import_results = import_service.import_data(backup_data, overwrite_existing=overwrite_existing)

            return jsonify({
                'success': True,
                'message': 'Data import completed',
                'import_results': import_results,
                'validation_results': validation_results
            })

        except Exception as e:
            return jsonify({
                'error': True,
                'message': 'Failed to import data',
                'code': 'IMPORT_ERROR',
                'details': str(e)
            }), 500

    except Exception as e:
        app.logger.error(f"Error importing data: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to import data',
            'code': 'IMPORT_ERROR',
            'details': str(e)
        }), 500


@app.route('/api/import/validate', methods=['POST'])
@require_auth
def validate_backup():
    """Validate backup file without importing data."""
    try:
        db_service = auth_manager.get_database_service()
        encryption_service = auth_manager.get_encryption_service()

        if not db_service or not encryption_service:
            return jsonify({
                'error': True,
                'message': 'Required services not available',
                'code': 'SERVICES_NOT_AVAILABLE'
            }), 500

        # Check if file was uploaded
        if 'backup_file' not in request.files:
            return jsonify({
                'error': True,
                'message': 'No backup file provided',
                'code': 'NO_FILE_PROVIDED'
            }), 400

        backup_file = request.files['backup_file']
        if backup_file.filename == '':
            return jsonify({
                'error': True,
                'message': 'No file selected',
                'code': 'NO_FILE_SELECTED'
            }), 400

        # Read backup file
        try:
            encrypted_backup = backup_file.read()
        except Exception as e:
            return jsonify({
                'error': True,
                'message': 'Failed to read backup file',
                'code': 'FILE_READ_ERROR',
                'details': str(e)
            }), 400

        from services.export_import import ExportImportService
        import_service = ExportImportService(db_service, encryption_service)

        # Decrypt and validate backup
        try:
            backup_data = import_service.decrypt_backup(encrypted_backup)
            validation_results = import_service.validate_backup_integrity(backup_data)

            return jsonify({
                'success': True,
                'message': 'Backup file validation completed',
                'validation_results': validation_results
            })

        except Exception as e:
            return jsonify({
                'error': True,
                'message': 'Failed to validate backup file',
                'code': 'VALIDATION_ERROR',
                'details': str(e)
            }), 400

    except Exception as e:
        app.logger.error(f"Error validating backup: {str(e)}")
        return jsonify({
            'error': True,
            'message': 'Failed to validate backup',
            'code': 'VALIDATION_ERROR',
            'details': str(e)
        }), 500


@app.route('/templates/accounts/<account_type>_form.html')
@public_view_endpoint
def get_account_form_template(account_type):
    """Serve account form templates for dynamic loading."""
    valid_types = ['cd', 'savings', '401k', 'trading', 'ibonds', 'hsa']

    if account_type not in valid_types:
        return "Form template not found", 404

    template_name = f'accounts/{account_type}_form.html'

    try:
        return render_template(template_name)
    except Exception as e:
        app.logger.error(f"Error loading form template {template_name}: {str(e)}")
        return "Error loading form template", 500


@app.route('/templates/accounts/<template_name>')
@public_view_endpoint
def serve_account_template(template_name):
    """Serve account form templates."""
    try:
        # Validate template name to prevent directory traversal
        allowed_templates = [
            'cd_form.html',
            'savings_form.html',
            '401k_form.html',
            'trading_form.html',
            'ibonds_form.html'
        ]

        if template_name not in allowed_templates:
            return "Template not found", 404

        return render_template(f'accounts/{template_name}')
    except Exception as e:
        app_logger.error(f"Error serving template {template_name}: {str(e)}")
        return "Template not found", 404


if __name__ == '__main__':
    # Ensure database directory exists
    os.makedirs(os.path.dirname(config.DATABASE_PATH) if os.path.dirname(config.DATABASE_PATH) else '.', exist_ok=True)

    # Run Flask development server
    app.run(
        host='127.0.0.1',  # Localhost only for security
        port=5000,
        debug=True,
        threaded=True
    )