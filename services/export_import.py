"""
Export and import service for encrypted backup functionality in the networth tracker application.
Provides secure data export and import with encryption for backup and restore operations.
"""

import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

from .encryption import EncryptionService
from .database import DatabaseService


class ExportImportService:
    """Service for exporting and importing encrypted backup data."""

    BACKUP_VERSION = "1.0"
    BACKUP_FORMAT_VERSION = 1

    def __init__(self, db_service: DatabaseService, encryption_service: EncryptionService):
        """
        Initialize export/import service.

        Args:
            db_service: Database service instance
            encryption_service: Encryption service instance
        """
        self.db_service = db_service
        self.encryption_service = encryption_service

    def export_data(self, include_historical: bool = True) -> Dict[str, Any]:
        """
        Export all application data to encrypted backup format.

        Args:
            include_historical: Whether to include historical snapshots

        Returns:
            Dictionary containing encrypted backup data

        Raises:
            Exception: If export operation fails
        """
        try:
            # Create backup metadata
            backup_id = str(uuid.uuid4())
            export_timestamp = datetime.now()

            # Export all accounts
            accounts_data = self.db_service.get_accounts()

            # Export stock positions for trading accounts
            stock_positions = {}
            for account in accounts_data:
                if account.get('type') == 'TRADING':
                    positions = self.db_service.get_stock_positions(account['id'])
                    if positions:
                        stock_positions[account['id']] = positions

            # Export watchlist data
            watchlist_data = self.db_service.get_watchlist_items(include_demo=True)

            # Export historical snapshots if requested
            historical_data = {}
            if include_historical:
                for account in accounts_data:
                    snapshots = self.db_service.get_historical_snapshots(account['id'])
                    if snapshots:
                        # Convert datetime objects to ISO strings for JSON serialization
                        serializable_snapshots = []
                        for snapshot in snapshots:
                            snapshot_copy = snapshot.copy()
                            if isinstance(snapshot_copy.get('timestamp'), datetime):
                                snapshot_copy['timestamp'] = snapshot_copy['timestamp'].isoformat()
                            serializable_snapshots.append(snapshot_copy)
                        historical_data[account['id']] = serializable_snapshots

            # Export application settings
            app_settings = {}
            try:
                schema_version = self.db_service.get_setting('schema_version')
                app_settings['schema_version'] = schema_version
            except KeyError:
                app_settings['schema_version'] = '1'

            # Prepare export data structure
            export_data = {
                'backup_metadata': {
                    'backup_id': backup_id,
                    'export_timestamp': export_timestamp.isoformat(),
                    'backup_version': self.BACKUP_VERSION,
                    'format_version': self.BACKUP_FORMAT_VERSION,
                    'include_historical': include_historical,
                    'accounts_count': len(accounts_data),
                    'watchlist_count': len(watchlist_data),
                    'historical_accounts_count': len(historical_data) if include_historical else 0
                },
                'accounts': self._serialize_accounts_for_export(accounts_data),
                'stock_positions': self._serialize_stock_positions_for_export(stock_positions),
                'watchlist': self._serialize_watchlist_for_export(watchlist_data),
                'historical_snapshots': historical_data,
                'app_settings': app_settings
            }

            return export_data

        except Exception as e:
            raise Exception(f"Failed to export data: {str(e)}")

    def create_encrypted_backup(self, export_data: Dict[str, Any]) -> bytes:
        """
        Create encrypted backup file from export data.

        Args:
            export_data: Export data dictionary

        Returns:
            Encrypted backup data as bytes

        Raises:
            Exception: If encryption fails
        """
        try:
            # Convert export data to JSON string
            json_data = json.dumps(export_data, indent=2, default=str)

            # Encrypt the JSON data
            encrypted_backup = self.encryption_service.encrypt(json_data)

            return encrypted_backup

        except Exception as e:
            raise Exception(f"Failed to create encrypted backup: {str(e)}")

    def decrypt_backup(self, encrypted_backup: bytes) -> Dict[str, Any]:
        """
        Decrypt backup file and parse JSON data.

        Args:
            encrypted_backup: Encrypted backup data bytes

        Returns:
            Decrypted backup data dictionary

        Raises:
            Exception: If decryption or parsing fails
        """
        try:
            # Decrypt the backup data
            json_data = self.encryption_service.decrypt(encrypted_backup)

            # Parse JSON data
            backup_data = json.loads(json_data)

            # Validate backup format
            self._validate_backup_format(backup_data)

            return backup_data

        except Exception as e:
            raise Exception(f"Failed to decrypt backup: {str(e)}")

    def import_data(self, backup_data: Dict[str, Any], overwrite_existing: bool = False) -> Dict[str, Any]:
        """
        Import data from decrypted backup.

        Args:
            backup_data: Decrypted backup data dictionary
            overwrite_existing: Whether to overwrite existing accounts with same ID

        Returns:
            Import results summary

        Raises:
            Exception: If import operation fails
        """
        try:
            # Validate backup format first
            self._validate_backup_format(backup_data)

            import_results = {
                'accounts_imported': 0,
                'accounts_skipped': 0,
                'stock_positions_imported': 0,
                'watchlist_imported': 0,
                'watchlist_skipped': 0,
                'historical_snapshots_imported': 0,
                'settings_imported': 0,
                'errors': []
            }

            # Import accounts
            accounts_data = backup_data.get('accounts', [])
            for account_data in accounts_data:
                try:
                    account_id = account_data.get('id')

                    # Check if account already exists
                    existing_account = self.db_service.get_account(account_id) if account_id else None

                    if existing_account and not overwrite_existing:
                        import_results['accounts_skipped'] += 1
                        continue

                    # Prepare account data for database
                    db_account_data = self._prepare_account_for_import(account_data)

                    if existing_account and overwrite_existing:
                        # Update existing account
                        success = self.db_service.update_account(account_id, db_account_data)
                        if success:
                            import_results['accounts_imported'] += 1
                    else:
                        # Create new account
                        if account_id:
                            # Remove ID to let database service generate new one
                            db_account_data_copy = db_account_data.copy()
                            if 'id' in db_account_data_copy:
                                del db_account_data_copy['id']
                            new_account_id = self.db_service.create_account(db_account_data_copy)
                            import_results['accounts_imported'] += 1

                            # Update mapping for stock positions and historical data
                            if new_account_id != account_id:
                                self._update_account_id_mapping(backup_data, account_id, new_account_id)
                        else:
                            new_account_id = self.db_service.create_account(db_account_data)
                            import_results['accounts_imported'] += 1

                except Exception as e:
                    import_results['errors'].append(f"Failed to import account {account_data.get('id', 'unknown')}: {str(e)}")

            # Import stock positions
            stock_positions_data = backup_data.get('stock_positions', {})
            for account_id, positions in stock_positions_data.items():
                for position_data in positions:
                    try:
                        # Prepare position data
                        db_position_data = self._prepare_stock_position_for_import(position_data)

                        # Create stock position
                        self.db_service.create_stock_position(
                            account_id,
                            db_position_data['symbol'],
                            db_position_data['shares'],
                            db_position_data['purchase_price'],
                            db_position_data['purchase_date']
                        )

                        # Update current price if available
                        if db_position_data.get('current_price'):
                            # Get the position ID to update price
                            positions_list = self.db_service.get_stock_positions(account_id)
                            for pos in positions_list:
                                if (pos['symbol'] == db_position_data['symbol'] and
                                    pos['shares'] == db_position_data['shares'] and
                                    pos['purchase_price'] == db_position_data['purchase_price']):
                                    self.db_service.update_stock_price(pos['id'], db_position_data['current_price'])
                                    break

                        import_results['stock_positions_imported'] += 1

                    except Exception as e:
                        import_results['errors'].append(f"Failed to import stock position for account {account_id}: {str(e)}")

            # Import watchlist data
            watchlist_data = backup_data.get('watchlist', [])
            for watchlist_item in watchlist_data:
                try:
                    symbol = watchlist_item.get('symbol')
                    if not symbol:
                        import_results['errors'].append("Watchlist item missing symbol")
                        continue

                    # Check if watchlist item already exists
                    existing_item = self.db_service.get_watchlist_item(symbol)

                    if existing_item and not overwrite_existing:
                        import_results['watchlist_skipped'] += 1
                        continue

                    # Prepare watchlist data for database
                    db_watchlist_data = self._prepare_watchlist_for_import(watchlist_item)

                    if existing_item and overwrite_existing:
                        # Update existing watchlist item
                        success = self.db_service.update_watchlist_item(symbol, db_watchlist_data)
                        if success:
                            import_results['watchlist_imported'] += 1
                    else:
                        # Create new watchlist item
                        self.db_service.create_watchlist_item(db_watchlist_data)
                        import_results['watchlist_imported'] += 1

                except Exception as e:
                    import_results['errors'].append(f"Failed to import watchlist item {watchlist_item.get('symbol', 'unknown')}: {str(e)}")

            # Import historical snapshots
            historical_data = backup_data.get('historical_snapshots', {})
            for account_id, snapshots in historical_data.items():
                for snapshot_data in snapshots:
                    try:
                        # Prepare snapshot data
                        db_snapshot_data = self._prepare_historical_snapshot_for_import(snapshot_data)

                        # Create historical snapshot
                        self.db_service.create_historical_snapshot(
                            account_id,
                            db_snapshot_data['value'],
                            db_snapshot_data['change_type'],
                            db_snapshot_data.get('metadata')
                        )

                        import_results['historical_snapshots_imported'] += 1

                    except Exception as e:
                        import_results['errors'].append(f"Failed to import historical snapshot for account {account_id}: {str(e)}")

            # Import application settings
            app_settings = backup_data.get('app_settings', {})
            for key, value in app_settings.items():
                try:
                    self.db_service.set_setting(key, str(value))
                    import_results['settings_imported'] += 1
                except Exception as e:
                    import_results['errors'].append(f"Failed to import setting {key}: {str(e)}")

            return import_results

        except Exception as e:
            raise Exception(f"Failed to import data: {str(e)}")

    def _serialize_accounts_for_export(self, accounts_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Serialize accounts data for export, converting datetime objects to ISO strings.

        Args:
            accounts_data: List of account data dictionaries

        Returns:
            List of serialized account data dictionaries
        """
        serialized_accounts = []

        for account in accounts_data:
            account_copy = account.copy()

            # Convert datetime objects to ISO strings
            datetime_fields = ['created_date', 'last_updated']
            for field in datetime_fields:
                if field in account_copy and isinstance(account_copy[field], datetime):
                    account_copy[field] = account_copy[field].isoformat()

            # Convert date objects to ISO strings
            date_fields = ['maturity_date', 'purchase_date']
            for field in date_fields:
                if field in account_copy and hasattr(account_copy[field], 'isoformat'):
                    account_copy[field] = account_copy[field].isoformat()

            serialized_accounts.append(account_copy)

        return serialized_accounts

    def _serialize_stock_positions_for_export(self, stock_positions: Dict[str, List[Dict[str, Any]]]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Serialize stock positions data for export, converting datetime objects to ISO strings.

        Args:
            stock_positions: Dictionary mapping account IDs to stock positions

        Returns:
            Dictionary of serialized stock positions data
        """
        serialized_positions = {}

        for account_id, positions in stock_positions.items():
            serialized_account_positions = []

            for position in positions:
                position_copy = position.copy()

                # Convert datetime objects to ISO strings
                datetime_fields = ['purchase_date', 'last_price_update']
                for field in datetime_fields:
                    if field in position_copy and isinstance(position_copy[field], datetime):
                        position_copy[field] = position_copy[field].isoformat()

                serialized_account_positions.append(position_copy)

            serialized_positions[account_id] = serialized_account_positions

        return serialized_positions

    def _serialize_watchlist_for_export(self, watchlist_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Serialize watchlist data for export, converting datetime objects to ISO strings.

        Args:
            watchlist_data: List of watchlist item dictionaries

        Returns:
            List of serialized watchlist item dictionaries
        """
        serialized_watchlist = []

        for item in watchlist_data:
            item_copy = item.copy()

            # Convert datetime objects to ISO strings
            datetime_fields = ['added_date', 'last_price_update']
            for field in datetime_fields:
                if field in item_copy and isinstance(item_copy[field], datetime):
                    item_copy[field] = item_copy[field].isoformat()

            serialized_watchlist.append(item_copy)

        return serialized_watchlist

    def _validate_backup_format(self, backup_data: Dict[str, Any]):
        """
        Validate backup data format and version compatibility.

        Args:
            backup_data: Backup data dictionary

        Raises:
            ValueError: If backup format is invalid or incompatible
        """
        # Check for required top-level keys
        required_keys = ['backup_metadata', 'accounts']
        missing_keys = [key for key in required_keys if key not in backup_data]
        if missing_keys:
            raise ValueError(f"Invalid backup format: missing required keys: {', '.join(missing_keys)}")

        # Check backup metadata
        metadata = backup_data['backup_metadata']
        if 'format_version' not in metadata:
            raise ValueError("Invalid backup format: missing format version")

        format_version = metadata['format_version']
        if format_version > self.BACKUP_FORMAT_VERSION:
            raise ValueError(f"Incompatible backup format version: {format_version}. Maximum supported: {self.BACKUP_FORMAT_VERSION}")

        # Check backup version
        if 'backup_version' not in metadata:
            raise ValueError("Invalid backup format: missing backup version")

    def _prepare_account_for_import(self, account_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare account data for database import, converting ISO strings back to appropriate types.

        Args:
            account_data: Account data from backup

        Returns:
            Account data prepared for database import
        """
        prepared_data = account_data.copy()

        # Convert ISO date strings back to datetime objects
        datetime_fields = ['created_date', 'last_updated']
        for field in datetime_fields:
            if field in prepared_data and isinstance(prepared_data[field], str):
                try:
                    prepared_data[field] = datetime.fromisoformat(prepared_data[field])
                except ValueError:
                    # If parsing fails, use current time
                    prepared_data[field] = datetime.now()

        # Convert ISO date strings back to date objects
        from datetime import date
        date_fields = ['maturity_date', 'purchase_date']
        for field in date_fields:
            if field in prepared_data and isinstance(prepared_data[field], str):
                try:
                    prepared_data[field] = date.fromisoformat(prepared_data[field])
                except ValueError:
                    # If parsing fails, remove the field
                    del prepared_data[field]

        return prepared_data

    def _prepare_stock_position_for_import(self, position_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare stock position data for database import.

        Args:
            position_data: Stock position data from backup

        Returns:
            Stock position data prepared for database import
        """
        prepared_data = position_data.copy()

        # Convert ISO date strings back to timestamp integers
        if 'purchase_date' in prepared_data and isinstance(prepared_data['purchase_date'], str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(prepared_data['purchase_date'])
                prepared_data['purchase_date'] = int(dt.timestamp())
            except ValueError:
                # If parsing fails, use current timestamp
                prepared_data['purchase_date'] = int(datetime.now().timestamp())

        return prepared_data

    def _prepare_historical_snapshot_for_import(self, snapshot_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare historical snapshot data for database import.

        Args:
            snapshot_data: Historical snapshot data from backup

        Returns:
            Historical snapshot data prepared for database import
        """
        prepared_data = snapshot_data.copy()

        # Convert ISO timestamp strings back to datetime objects
        if 'timestamp' in prepared_data and isinstance(prepared_data['timestamp'], str):
            try:
                prepared_data['timestamp'] = datetime.fromisoformat(prepared_data['timestamp'])
            except ValueError:
                # If parsing fails, use current time
                prepared_data['timestamp'] = datetime.now()

        return prepared_data

    def _prepare_watchlist_for_import(self, watchlist_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Prepare watchlist data for database import, converting ISO strings back to appropriate types.

        Args:
            watchlist_data: Watchlist item data from backup

        Returns:
            Watchlist data prepared for database import
        """
        prepared_data = watchlist_data.copy()

        # Convert ISO date strings back to datetime objects
        datetime_fields = ['added_date', 'last_price_update']
        for field in datetime_fields:
            if field in prepared_data and isinstance(prepared_data[field], str):
                try:
                    prepared_data[field] = datetime.fromisoformat(prepared_data[field])
                except ValueError:
                    # If parsing fails, use current time for added_date, None for last_price_update
                    if field == 'added_date':
                        prepared_data[field] = datetime.now()
                    else:
                        prepared_data[field] = None

        return prepared_data

    def _update_account_id_mapping(self, backup_data: Dict[str, Any], old_id: str, new_id: str):
        """
        Update account ID mappings in backup data when account IDs change during import.

        Args:
            backup_data: Backup data dictionary
            old_id: Original account ID from backup
            new_id: New account ID assigned during import
        """
        # Update stock positions mapping
        if 'stock_positions' in backup_data and old_id in backup_data['stock_positions']:
            backup_data['stock_positions'][new_id] = backup_data['stock_positions'][old_id]
            del backup_data['stock_positions'][old_id]

        # Update historical snapshots mapping
        if 'historical_snapshots' in backup_data and old_id in backup_data['historical_snapshots']:
            backup_data['historical_snapshots'][new_id] = backup_data['historical_snapshots'][old_id]
            del backup_data['historical_snapshots'][old_id]

    def validate_backup_integrity(self, backup_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate backup data integrity and provide summary.

        Args:
            backup_data: Decrypted backup data

        Returns:
            Validation results dictionary
        """
        validation_results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'summary': {
                'accounts_count': 0,
                'stock_positions_count': 0,
                'watchlist_count': 0,
                'historical_snapshots_count': 0,
                'settings_count': 0
            }
        }

        try:
            # Validate backup format
            self._validate_backup_format(backup_data)

            # Count and validate accounts
            accounts = backup_data.get('accounts', [])
            validation_results['summary']['accounts_count'] = len(accounts)

            for account in accounts:
                if not account.get('id'):
                    validation_results['warnings'].append("Account found without ID")
                if not account.get('name'):
                    validation_results['errors'].append("Account found without name")
                if not account.get('type'):
                    validation_results['errors'].append("Account found without type")

            # Count stock positions
            stock_positions = backup_data.get('stock_positions', {})
            total_positions = sum(len(positions) for positions in stock_positions.values())
            validation_results['summary']['stock_positions_count'] = total_positions

            # Count and validate watchlist items
            watchlist = backup_data.get('watchlist', [])
            validation_results['summary']['watchlist_count'] = len(watchlist)

            for item in watchlist:
                if not item.get('symbol'):
                    validation_results['errors'].append("Watchlist item found without symbol")
                if not item.get('id'):
                    validation_results['warnings'].append("Watchlist item found without ID")

            # Count historical snapshots
            historical_snapshots = backup_data.get('historical_snapshots', {})
            total_snapshots = sum(len(snapshots) for snapshots in historical_snapshots.values())
            validation_results['summary']['historical_snapshots_count'] = total_snapshots

            # Count settings
            app_settings = backup_data.get('app_settings', {})
            validation_results['summary']['settings_count'] = len(app_settings)

            # Set validation status
            validation_results['valid'] = len(validation_results['errors']) == 0

        except Exception as e:
            validation_results['valid'] = False
            validation_results['errors'].append(f"Validation failed: {str(e)}")

        return validation_results