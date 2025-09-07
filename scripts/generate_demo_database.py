#!/usr/bin/env python3
"""
Demo database generator script for the networth tracker application.

This script creates a standalone demo database with comprehensive synthetic data
including all account types and 24 months of historical data. The generated
database can be imported into the main application using existing import functionality.
"""

import sqlite3
import json
import uuid
import os
import sys
import random
from datetime import datetime, timedelta, date
from pathlib import Path
from typing import List, Dict, Any, Optional

# Add parent directory to path to import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from models.accounts import (
    BaseAccount, CDAccount, SavingsAccount, Account401k, TradingAccount, IBondsAccount,
    StockPosition, HistoricalSnapshot, AccountType, ChangeType
)
from services.encryption import EncryptionService


class DemoDataGenerator:
    """Generate realistic synthetic financial data for demo database."""

    def __init__(self):
        """Initialize demo data generator with realistic financial institutions and stocks."""
        self.demo_institutions = [
            "Chase Bank", "Bank of America", "Wells Fargo", "Citi Bank",
            "Capital One", "Ally Bank", "Marcus by Goldman Sachs", "PNC Bank",
            "US Bank", "TD Bank", "HSBC", "Discover Bank"
        ]

        self.demo_brokers = [
            "Fidelity", "Charles Schwab", "E*TRADE", "TD Ameritrade",
            "Robinhood", "Interactive Brokers", "Vanguard", "Merrill Edge",
            "Webull", "Ally Invest"
        ]

        self.demo_stocks = [
            ("AAPL", "Apple Inc.", 150.0),
            ("GOOGL", "Alphabet Inc.", 2500.0),
            ("MSFT", "Microsoft Corp.", 300.0),
            ("AMZN", "Amazon.com Inc.", 3200.0),
            ("TSLA", "Tesla Inc.", 800.0),
            ("NVDA", "NVIDIA Corp.", 400.0),
            ("META", "Meta Platforms", 200.0),
            ("NFLX", "Netflix Inc.", 400.0),
            ("SPY", "SPDR S&P 500 ETF", 400.0),
            ("QQQ", "Invesco QQQ Trust", 350.0),
            ("VTI", "Vanguard Total Stock Market ETF", 220.0),
            ("BRK.B", "Berkshire Hathaway Inc.", 300.0),
            ("JNJ", "Johnson & Johnson", 160.0),
            ("V", "Visa Inc.", 220.0),
            ("JPM", "JPMorgan Chase & Co.", 140.0)
        ]

    def generate_demo_accounts(self) -> List[BaseAccount]:
        """
        Generate complete set of demo accounts with realistic data.

        Returns:
            List of demo accounts across all supported types
        """
        accounts = []
        accounts.extend(self._generate_cd_accounts(3))
        accounts.extend(self._generate_savings_accounts(2))
        accounts.extend(self._generate_401k_accounts(1))
        accounts.extend(self._generate_trading_accounts(2))
        accounts.extend(self._generate_ibonds_accounts(2))
        return accounts

    def _generate_cd_accounts(self, count: int) -> List[CDAccount]:
        """Generate sample CD accounts with realistic terms and rates."""
        accounts = []
        for i in range(count):
            maturity_months = random.choice([6, 12, 18, 24, 36, 60])
            principal = round(random.uniform(5000, 50000), 2)
            rate = round(random.uniform(1.5, 4.5), 2)

            # Calculate current value with some accrued interest
            months_elapsed = random.randint(1, min(maturity_months - 1, 12))
            current_value = principal * (1 + (rate/100) * (months_elapsed/12))

            remaining_months = maturity_months - months_elapsed
            maturity_date = date.today() + timedelta(days=max(remaining_months * 30, 30))
            created_date = datetime.now() - timedelta(days=months_elapsed * 30 + random.randint(1, 30))

            accounts.append(CDAccount(
                id=f"demo-cd-{i+1}",
                name=f"CD Account {i+1} ({maturity_months}mo)",
                institution=random.choice(self.demo_institutions),
                account_type=AccountType.CD,
                created_date=created_date,
                last_updated=datetime.now() - timedelta(days=random.randint(1, 7)),
                principal_amount=principal,
                interest_rate=rate,
                maturity_date=maturity_date,
                current_value=round(current_value, 2)
            ))
        return accounts

    def _generate_savings_accounts(self, count: int) -> List[SavingsAccount]:
        """Generate sample savings accounts with realistic balances and rates."""
        accounts = []
        for i in range(count):
            balance = round(random.uniform(1000, 25000), 2)
            rate = round(random.uniform(0.1, 2.5), 2)
            created_date = datetime.now() - timedelta(days=random.randint(30, 730))

            accounts.append(SavingsAccount(
                id=f"demo-savings-{i+1}",
                name=f"High Yield Savings {i+1}",
                institution=random.choice(self.demo_institutions),
                account_type=AccountType.SAVINGS,
                created_date=created_date,
                last_updated=datetime.now() - timedelta(days=random.randint(1, 14)),
                current_balance=balance,
                interest_rate=rate
            ))
        return accounts

    def _generate_401k_accounts(self, count: int) -> List[Account401k]:
        """Generate sample 401k accounts with realistic contribution data."""
        accounts = []
        for i in range(count):
            balance = round(random.uniform(25000, 150000), 2)
            employer_match = round(random.uniform(3.0, 6.0), 1)
            contribution_limit = 23000.0  # 2024 limit
            employer_contribution = round(random.uniform(2000, 8000), 2)
            created_date = datetime.now() - timedelta(days=random.randint(365, 2555))

            accounts.append(Account401k(
                id=f"demo-401k-{i+1}",
                name=f"401(k) Retirement Plan",
                institution=random.choice(self.demo_institutions[:5]),
                account_type=AccountType.ACCOUNT_401K,
                created_date=created_date,
                last_updated=datetime.now() - timedelta(days=random.randint(1, 30)),
                current_balance=balance,
                employer_match=employer_match,
                contribution_limit=contribution_limit,
                employer_contribution=employer_contribution
            ))
        return accounts

    def _generate_trading_accounts(self, count: int) -> List[TradingAccount]:
        """Generate sample trading accounts with stock positions."""
        accounts = []
        for i in range(count):
            positions = []
            num_positions = random.randint(3, 8)
            selected_stocks = random.sample(self.demo_stocks, min(num_positions, len(self.demo_stocks)))

            for symbol, name, current_price in selected_stocks:
                shares = random.randint(10, 200)
                purchase_price = round(current_price * random.uniform(0.7, 1.3), 2)
                purchase_date = date.today() - timedelta(days=random.randint(30, 730))

                positions.append(StockPosition(
                    symbol=symbol,
                    shares=shares,
                    purchase_price=purchase_price,
                    purchase_date=purchase_date,
                    current_price=current_price,
                    last_updated=datetime.now() - timedelta(hours=random.randint(1, 24))
                ))

            cash_balance = round(random.uniform(1000, 15000), 2)
            broker = random.choice(self.demo_brokers)
            created_date = datetime.now() - timedelta(days=random.randint(90, 1095))

            accounts.append(TradingAccount(
                id=f"demo-trading-{i+1}",
                name=f"Trading Account {i+1}",
                institution=broker,
                account_type=AccountType.TRADING,
                created_date=created_date,
                last_updated=datetime.now() - timedelta(days=random.randint(1, 7)),
                broker_name=broker,
                cash_balance=cash_balance,
                positions=positions
            ))
        return accounts

    def _generate_ibonds_accounts(self, count: int) -> List[IBondsAccount]:
        """Generate sample I-bonds accounts with realistic purchase data."""
        accounts = []
        for i in range(count):
            purchase_amount = round(random.uniform(1000, 10000), 2)
            purchase_date = date.today() - timedelta(days=random.randint(30, 1095))
            fixed_rate = round(random.uniform(0.0, 1.2), 2)
            inflation_rate = round(random.uniform(-0.5, 6.5), 2)

            # Calculate current value with compound interest
            years_held = (date.today() - purchase_date).days / 365.25
            composite_rate = fixed_rate + inflation_rate
            current_value = purchase_amount * ((1 + composite_rate/100) ** years_held)

            maturity_date = purchase_date + timedelta(days=30*365)  # 30 years
            created_date = datetime.combine(purchase_date, datetime.min.time())

            accounts.append(IBondsAccount(
                id=f"demo-ibonds-{i+1}",
                name=f"I Bonds Series {purchase_date.year}",
                institution="TreasuryDirect.gov",
                account_type=AccountType.I_BONDS,
                created_date=created_date,
                last_updated=datetime.now() - timedelta(days=random.randint(1, 30)),
                purchase_amount=purchase_amount,
                purchase_date=purchase_date,
                current_value=round(current_value, 2),
                fixed_rate=fixed_rate,
                inflation_rate=inflation_rate,
                maturity_date=maturity_date
            ))
        return accounts

    def generate_historical_data(self, accounts: List[BaseAccount]) -> List[HistoricalSnapshot]:
        """
        Generate 24 months of historical performance data for accounts.

        Args:
            accounts: List of accounts to generate history for

        Returns:
            List of historical snapshots
        """
        snapshots = []
        for account in accounts:
            snapshots.extend(self._generate_account_history(account))
        return snapshots

    def _generate_account_history(self, account: BaseAccount) -> List[HistoricalSnapshot]:
        """Generate monthly historical snapshots for an account with account-type specific volatility."""
        snapshots = []
        start_date = datetime.now() - timedelta(days=730)  # 24 months ago

        base_value = account.get_current_value()
        monthly_values = []
        current_value = base_value

        # Generate 24 months of data working backwards from current value
        for month in range(24):
            monthly_values.append(current_value)

            # Account-type specific volatility patterns
            if account.account_type == AccountType.CD:
                # CDs grow steadily with minimal volatility
                monthly_change = random.uniform(-0.005, 0.015)  # -0.5% to +1.5%
            elif account.account_type == AccountType.SAVINGS:
                # Savings accounts have very low volatility
                monthly_change = random.uniform(-0.01, 0.02)  # -1% to +2%
            elif account.account_type == AccountType.ACCOUNT_401K:
                # 401k accounts have market-like volatility with upward trend
                monthly_change = random.uniform(-0.06, 0.10)  # -6% to +10%
            elif account.account_type == AccountType.TRADING:
                # Trading accounts have high volatility
                monthly_change = random.uniform(-0.12, 0.15)  # -12% to +15%
            elif account.account_type == AccountType.I_BONDS:
                # I-bonds have steady growth with inflation adjustments
                monthly_change = random.uniform(-0.005, 0.025)  # -0.5% to +2.5%
            else:
                monthly_change = random.uniform(-0.05, 0.08)  # Default range

            current_value = current_value * (1 - monthly_change)
            if current_value < base_value * 0.1:  # Minimum 10% of current value
                current_value = base_value * 0.1

        # Reverse to get chronological order
        monthly_values.reverse()

        # Create snapshots
        for i, value in enumerate(monthly_values):
            snapshot_date = start_date + timedelta(days=i * 30)

            # Determine change type
            if i == 0:
                change_type = ChangeType.INITIAL_ENTRY
            elif account.account_type == AccountType.TRADING and random.random() < 0.3:
                change_type = ChangeType.STOCK_PRICE_UPDATE
            else:
                change_type = ChangeType.MANUAL_UPDATE

            snapshots.append(HistoricalSnapshot(
                id=f"demo-hist-{account.id}-{snapshot_date.strftime('%Y%m')}",
                account_id=account.id,
                timestamp=snapshot_date,
                value=round(value, 2),
                change_type=change_type,
                metadata={"demo_generated": True, "month": i + 1}
            ))

        return snapshots


class DemoDatabaseCreator:
    """Create standalone demo database with schema migration support."""

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str = "networth_demo.db", password: str = "demo123"):
        """
        Initialize demo database creator.

        Args:
            db_path: Path for the demo database file
            password: Password for encryption (default demo password)
        """
        self.db_path = db_path
        self.password = password
        self.encryption_service = EncryptionService()

        # Derive encryption key with fixed salt for demo consistency
        demo_salt = b'demo_salt_123456'  # Fixed salt for demo database
        self.encryption_service.derive_key(password, demo_salt)

    def create_demo_database(self) -> bool:
        """
        Create complete demo database with schema and data.

        Returns:
            True if database creation was successful
        """
        try:
            print(f"Creating demo database: {self.db_path}")

            # Remove existing demo database if it exists
            if os.path.exists(self.db_path):
                os.remove(self.db_path)
                print(f"Removed existing demo database")

            # Create database connection
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute('PRAGMA foreign_keys = ON')

            # Initialize schema with is_demo column
            self._initialize_schema(conn)
            print("Database schema initialized")

            # Generate demo data
            generator = DemoDataGenerator()
            demo_accounts = generator.generate_demo_accounts()
            demo_history = generator.generate_historical_data(demo_accounts)

            print(f"Generated {len(demo_accounts)} demo accounts")
            print(f"Generated {len(demo_history)} historical snapshots")

            # Populate database
            account_id_mapping = self._populate_accounts(conn, demo_accounts)
            self._populate_historical_data(conn, demo_history, account_id_mapping)
            self._populate_stock_positions(conn, demo_accounts, account_id_mapping)

            # Set demo password in app settings
            self._set_demo_settings(conn)

            conn.commit()
            conn.close()

            print(f"Demo database created successfully: {self.db_path}")
            print(f"Demo password: {self.password}")
            print("\nDemo database contents:")
            self._print_database_summary()

            return True

        except Exception as e:
            print(f"Error creating demo database: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

    def _initialize_schema(self, conn: sqlite3.Connection):
        """Initialize database schema with is_demo column support."""
        cursor = conn.cursor()

        # Accounts table with is_demo column
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                institution TEXT NOT NULL,
                type TEXT NOT NULL,
                encrypted_data BLOB NOT NULL,
                created_date INTEGER NOT NULL,
                last_updated INTEGER NOT NULL,
                schema_version INTEGER DEFAULT 1,
                is_demo BOOLEAN DEFAULT FALSE
            )
        ''')

        # Historical snapshots table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS historical_snapshots (
                id TEXT PRIMARY KEY,
                account_id TEXT NOT NULL,
                timestamp INTEGER NOT NULL,
                value REAL NOT NULL,
                change_type TEXT NOT NULL,
                encrypted_metadata BLOB,
                FOREIGN KEY (account_id) REFERENCES accounts (id) ON DELETE CASCADE
            )
        ''')

        # Stock positions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS stock_positions (
                id TEXT PRIMARY KEY,
                trading_account_id TEXT NOT NULL,
                symbol TEXT NOT NULL,
                shares REAL NOT NULL,
                purchase_price REAL NOT NULL,
                purchase_date INTEGER NOT NULL,
                current_price REAL,
                last_price_update INTEGER,
                FOREIGN KEY (trading_account_id) REFERENCES accounts (id) ON DELETE CASCADE
            )
        ''')

        # Application settings table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT,
                encrypted_value BLOB
            )
        ''')

        # Create indexes
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_type ON accounts (type)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_accounts_is_demo ON accounts (is_demo)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_account_id ON historical_snapshots (account_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_historical_timestamp ON historical_snapshots (timestamp)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_stock_positions_account ON stock_positions (trading_account_id)')

    def _populate_accounts(self, conn: sqlite3.Connection, accounts: List[BaseAccount]) -> Dict[str, str]:
        """
        Populate accounts table with demo data.

        Returns:
            Mapping of original account IDs to database-generated IDs
        """
        cursor = conn.cursor()
        account_id_mapping = {}

        for account in accounts:
            # Generate new UUID for database
            db_account_id = str(uuid.uuid4())
            account_id_mapping[account.id] = db_account_id

            # Prepare account data
            account_dict = account.to_dict()

            # Separate public and sensitive data
            public_data = {
                'name': account_dict['name'],
                'institution': account_dict['institution'],
                'type': account_dict['account_type']
            }

            # Encrypt sensitive data
            sensitive_data = {k: v for k, v in account_dict.items()
                            if k not in ['name', 'institution', 'account_type', 'id']}

            encrypted_data = self.encryption_service.encrypt(json.dumps(sensitive_data, default=str))

            # Insert account with is_demo = TRUE
            cursor.execute('''
                INSERT INTO accounts (id, name, institution, type, encrypted_data,
                                    created_date, last_updated, schema_version, is_demo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                db_account_id,
                public_data['name'],
                public_data['institution'],
                public_data['type'],
                encrypted_data,
                int(account.created_date.timestamp()),
                int(account.last_updated.timestamp()),
                self.SCHEMA_VERSION,
                True  # Mark as demo account
            ))

        return account_id_mapping

    def _populate_historical_data(self, conn: sqlite3.Connection,
                                 snapshots: List[HistoricalSnapshot],
                                 account_id_mapping: Dict[str, str]):
        """Populate historical snapshots with demo data."""
        cursor = conn.cursor()

        for snapshot in snapshots:
            # Map to database account ID
            db_account_id = account_id_mapping.get(snapshot.account_id)
            if not db_account_id:
                continue

            # Encrypt metadata
            encrypted_metadata = None
            if snapshot.metadata:
                encrypted_metadata = self.encryption_service.encrypt(
                    json.dumps(snapshot.metadata, default=str)
                )

            cursor.execute('''
                INSERT INTO historical_snapshots (id, account_id, timestamp, value,
                                                change_type, encrypted_metadata)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                str(uuid.uuid4()),
                db_account_id,
                int(snapshot.timestamp.timestamp()),
                snapshot.value,
                snapshot.change_type.value,
                encrypted_metadata
            ))

    def _populate_stock_positions(self, conn: sqlite3.Connection,
                                 accounts: List[BaseAccount],
                                 account_id_mapping: Dict[str, str]):
        """Populate stock positions for trading accounts."""
        cursor = conn.cursor()

        for account in accounts:
            if isinstance(account, TradingAccount) and account.positions:
                db_account_id = account_id_mapping.get(account.id)
                if not db_account_id:
                    continue

                for position in account.positions:
                    cursor.execute('''
                        INSERT INTO stock_positions (id, trading_account_id, symbol, shares,
                                                   purchase_price, purchase_date, current_price,
                                                   last_price_update)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        str(uuid.uuid4()),
                        db_account_id,
                        position.symbol,
                        position.shares,
                        position.purchase_price,
                        int(position.purchase_date.strftime('%s')) if position.purchase_date else None,
                        position.current_price,
                        int(position.last_updated.timestamp()) if position.last_updated else None
                    ))

    def _set_demo_settings(self, conn: sqlite3.Connection):
        """Set demo-specific application settings."""
        cursor = conn.cursor()

        # Set schema version
        schema_version_encrypted = self.encryption_service.encrypt(str(self.SCHEMA_VERSION))
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, encrypted_value)
            VALUES (?, ?)
        ''', ('schema_version', schema_version_encrypted))

        # Set demo database marker
        demo_marker_encrypted = self.encryption_service.encrypt('true')
        cursor.execute('''
            INSERT OR REPLACE INTO app_settings (key, encrypted_value)
            VALUES (?, ?)
        ''', ('is_demo_database', demo_marker_encrypted))

    def _print_database_summary(self):
        """Print summary of created demo database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Count accounts by type
            cursor.execute('''
                SELECT type, COUNT(*) as count
                FROM accounts
                WHERE is_demo = 1
                GROUP BY type
            ''')

            print("Account types:")
            for row in cursor.fetchall():
                print(f"  {row[0]}: {row[1]} accounts")

            # Count historical snapshots
            cursor.execute('SELECT COUNT(*) FROM historical_snapshots')
            snapshot_count = cursor.fetchone()[0]
            print(f"Historical snapshots: {snapshot_count}")

            # Count stock positions
            cursor.execute('SELECT COUNT(*) FROM stock_positions')
            position_count = cursor.fetchone()[0]
            print(f"Stock positions: {position_count}")

            conn.close()

        except Exception as e:
            print(f"Error printing database summary: {e}")


def main():
    """Main function to create demo database."""
    print("Networth Tracker Demo Database Generator")
    print("=" * 50)

    # Default demo database path
    demo_db_path = "networth_demo.db"
    demo_password = "demo123"

    # Allow custom path from command line
    if len(sys.argv) > 1:
        demo_db_path = sys.argv[1]
    if len(sys.argv) > 2:
        demo_password = sys.argv[2]

    # Create demo database
    creator = DemoDatabaseCreator(demo_db_path, demo_password)
    success = creator.create_demo_database()

    if success:
        print("\n" + "=" * 50)
        print("Demo database created successfully!")
        print(f"Database file: {demo_db_path}")
        print(f"Demo password: {demo_password}")
        print("\nTo use this demo database:")
        print("1. Import it into your main application using the import functionality")
        print("2. Use the demo password when prompted")
        print("3. All demo accounts will be clearly marked as demo data")
        print("4. You can delete all demo accounts when ready to use real data")
    else:
        print("\nFailed to create demo database!")
        sys.exit(1)


if __name__ == "__main__":
    main()