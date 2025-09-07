#!/usr/bin/env python3
"""
Create encrypted backup file from demo database for import functionality.

This script reads the demo database and creates an encrypted backup file
that can be imported through the application's import functionality.
"""

import os
import sys
import sqlite3
import json
from datetime import datetime
from pathlib import Path

# Add parent directory to path to import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from services.encryption import EncryptionService
from services.export_import import ExportImportService


def create_demo_backup(demo_db_path: str = "networth_demo.db",
                      backup_path: str = "demo_backup.enc",
                      demo_password: str = "demo123"):
    """
    Create encrypted backup file from demo database.

    Args:
        demo_db_path: Path to demo database file
        backup_path: Path for output backup file
        demo_password: Password for demo database
    """

    if not os.path.exists(demo_db_path):
        print(f"Error: Demo database file not found: {demo_db_path}")
        return False

    try:
        print(f"Creating encrypted backup from demo database: {demo_db_path}")

        # Initialize encryption service with demo password
        encryption_service = EncryptionService()
        demo_salt = b'demo_salt_123456'  # Same salt used in demo generation
        encryption_service.derive_key(demo_password, demo_salt)

        # Connect to demo database
        conn = sqlite3.connect(demo_db_path)
        conn.row_factory = sqlite3.Row

        # Read accounts data
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, institution, type, encrypted_data,
                   created_date, last_updated, is_demo
            FROM accounts
            WHERE is_demo = 1
        ''')

        accounts_data = []
        for row in cursor.fetchall():
            # Decrypt account data
            try:
                decrypted_data = encryption_service.decrypt(row['encrypted_data'])
                account_dict = json.loads(decrypted_data)

                # Add public fields
                account_dict['id'] = row['id']
                account_dict['name'] = row['name']
                account_dict['institution'] = row['institution']
                account_dict['type'] = row['type']
                account_dict['account_type'] = row['type']  # For compatibility
                account_dict['created_date'] = datetime.fromtimestamp(row['created_date']).isoformat()
                account_dict['last_updated'] = datetime.fromtimestamp(row['last_updated']).isoformat()

                # Mark as demo account for UI purposes (not part of account model)
                account_dict['is_demo'] = True

                accounts_data.append(account_dict)

            except Exception as e:
                print(f"Warning: Could not decrypt account {row['id']}: {e}")
                continue

        print(f"Found {len(accounts_data)} demo accounts")

        # Read stock positions
        cursor.execute('''
            SELECT sp.*, a.id as account_id
            FROM stock_positions sp
            JOIN accounts a ON sp.trading_account_id = a.id
            WHERE a.is_demo = 1
        ''')

        stock_positions = {}
        for row in cursor.fetchall():
            account_id = row['account_id']
            if account_id not in stock_positions:
                stock_positions[account_id] = []

            position_data = {
                'id': row['id'],
                'symbol': row['symbol'],
                'shares': row['shares'],
                'purchase_price': row['purchase_price'],
                'purchase_date': datetime.fromtimestamp(row['purchase_date']).isoformat() if row['purchase_date'] else None,
                'current_price': row['current_price'],
                'last_price_update': datetime.fromtimestamp(row['last_price_update']).isoformat() if row['last_price_update'] else None
            }
            stock_positions[account_id].append(position_data)

        print(f"Found stock positions for {len(stock_positions)} trading accounts")

        # Read historical snapshots
        cursor.execute('''
            SELECT hs.*, a.id as account_id
            FROM historical_snapshots hs
            JOIN accounts a ON hs.account_id = a.id
            WHERE a.is_demo = 1
        ''')

        historical_snapshots = {}
        for row in cursor.fetchall():
            account_id = row['account_id']
            if account_id not in historical_snapshots:
                historical_snapshots[account_id] = []

            # Decrypt metadata if present
            metadata = None
            if row['encrypted_metadata']:
                try:
                    decrypted_metadata = encryption_service.decrypt(row['encrypted_metadata'])
                    metadata = json.loads(decrypted_metadata)
                except Exception:
                    metadata = None

            snapshot_data = {
                'id': row['id'],
                'account_id': account_id,
                'timestamp': datetime.fromtimestamp(row['timestamp']).isoformat(),
                'value': row['value'],
                'change_type': row['change_type'],
                'metadata': metadata
            }
            historical_snapshots[account_id].append(snapshot_data)

        total_snapshots = sum(len(snapshots) for snapshots in historical_snapshots.values())
        print(f"Found {total_snapshots} historical snapshots")

        # Read app settings
        cursor.execute('SELECT key, encrypted_value FROM app_settings')
        app_settings = {}
        for row in cursor.fetchall():
            if row['encrypted_value']:
                try:
                    decrypted_value = encryption_service.decrypt(row['encrypted_value'])
                    app_settings[row['key']] = decrypted_value
                except Exception:
                    continue

        conn.close()

        # Create backup data structure
        backup_data = {
            'backup_metadata': {
                'backup_id': 'demo-backup-001',
                'export_timestamp': datetime.now().isoformat(),
                'backup_version': '1.0',
                'format_version': 1,
                'include_historical': True,
                'accounts_count': len(accounts_data),
                'historical_accounts_count': len(historical_snapshots),
                'source': 'demo_database'
            },
            'accounts': accounts_data,
            'stock_positions': stock_positions,
            'historical_snapshots': historical_snapshots,
            'app_settings': app_settings
        }

        # Create encrypted backup
        json_data = json.dumps(backup_data, indent=2, default=str)
        encrypted_backup = encryption_service.encrypt(json_data)

        # Write backup file
        with open(backup_path, 'wb') as f:
            f.write(encrypted_backup)

        print(f"Encrypted backup created successfully: {backup_path}")
        print(f"Backup contains:")
        print(f"  - {len(accounts_data)} accounts")
        print(f"  - {sum(len(positions) for positions in stock_positions.values())} stock positions")
        print(f"  - {total_snapshots} historical snapshots")
        print(f"  - {len(app_settings)} app settings")
        print(f"\nTo import this backup:")
        print(f"1. Use the import functionality in the application")
        print(f"2. Select the file: {backup_path}")
        print(f"3. Use password: {demo_password}")

        return True

    except Exception as e:
        print(f"Error creating demo backup: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main function to create demo backup."""
    print("Demo Database to Encrypted Backup Converter")
    print("=" * 50)

    # Default paths
    demo_db_path = "networth_demo.db"
    backup_path = "demo_backup.enc"
    demo_password = "demo123"

    # Allow custom paths from command line
    if len(sys.argv) > 1:
        demo_db_path = sys.argv[1]
    if len(sys.argv) > 2:
        backup_path = sys.argv[2]
    if len(sys.argv) > 3:
        demo_password = sys.argv[3]

    success = create_demo_backup(demo_db_path, backup_path, demo_password)

    if success:
        print("\n" + "=" * 50)
        print("Demo backup created successfully!")
    else:
        print("\nFailed to create demo backup!")
        sys.exit(1)


if __name__ == "__main__":
    main()