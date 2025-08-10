"""
Unit tests for account data models and factory pattern.

Tests cover:
- BaseAccount and all account type subclasses
- StockPosition model
- HistoricalSnapshot model
- AccountFactory registration system and account creation
- Data validation and error handling
- Serialization/deserialization (to_dict/from_dict methods)
"""

import pytest
from datetime import date, datetime, timedelta
from enum import Enum
from dataclasses import dataclass
from models.accounts import (
    AccountType,
    ChangeType,
    BaseAccount,
    CDAccount,
    SavingsAccount,
    Account401k,
    TradingAccount,
    IBondsAccount,
    StockPosition,
    HistoricalSnapshot,
    AccountFactory
)


class TestAccountType:
    """Test AccountType enum."""

    def test_account_type_values(self):
        """Test that all expected account types are defined."""
        assert AccountType.CD.value == "CD"
        assert AccountType.SAVINGS.value == "SAVINGS"
        assert AccountType.ACCOUNT_401K.value == "401K"
        assert AccountType.TRADING.value == "TRADING"
        assert AccountType.I_BONDS.value == "I_BONDS"


class TestChangeType:
    """Test ChangeType enum."""

    def test_change_type_values(self):
        """Test that all expected change types are defined."""
        assert ChangeType.MANUAL_UPDATE.value == "MANUAL_UPDATE"
        assert ChangeType.STOCK_PRICE_UPDATE.value == "STOCK_PRICE_UPDATE"
        assert ChangeType.INITIAL_ENTRY.value == "INITIAL_ENTRY"


class TestBaseAccount:
    """Test BaseAccount abstract base class."""

    def test_base_account_creation(self):
        """Test BaseAccount can be instantiated with required fields."""
        now = datetime.now()
        account = BaseAccount(
            id="test-1",
            name="Test Account",
            institution="Test Bank",
            account_type=AccountType.SAVINGS,
            created_date=now,
            last_updated=now
        )

        assert account.id == "test-1"
        assert account.name == "Test Account"
        assert account.institution == "Test Bank"
        assert account.account_type == AccountType.SAVINGS
        assert account.created_date == now
        assert account.last_updated == now
        assert account.metadata is None

    def test_base_account_with_metadata(self):
        """Test BaseAccount with metadata field."""
        now = datetime.now()
        metadata = {"custom_field": "custom_value"}
        account = BaseAccount(
            id="test-1",
            name="Test Account",
            institution="Test Bank",
            account_type=AccountType.SAVINGS,
            created_date=now,
            last_updated=now,
            metadata=metadata
        )

        assert account.metadata == metadata

    def test_base_account_to_dict(self):
        """Test BaseAccount serialization to dictionary."""
        now = datetime.now()
        account = BaseAccount(
            id="test-1",
            name="Test Account",
            institution="Test Bank",
            account_type=AccountType.SAVINGS,
            created_date=now,
            last_updated=now
        )

        data = account.to_dict()
        assert data['id'] == "test-1"
        assert data['name'] == "Test Account"
        assert data['institution'] == "Test Bank"
        assert data['account_type'] == "SAVINGS"
        assert data['created_date'] == now.isoformat()
        assert data['last_updated'] == now.isoformat()
        assert data['metadata'] is None

    def test_base_account_from_dict(self):
        """Test BaseAccount deserialization from dictionary."""
        now = datetime.now()
        data = {
            'id': "test-1",
            'name': "Test Account",
            'institution': "Test Bank",
            'account_type': "SAVINGS",
            'created_date': now.isoformat(),
            'last_updated': now.isoformat(),
            'metadata': None
        }

        account = BaseAccount.from_dict(data)
        assert account.id == "test-1"
        assert account.name == "Test Account"
        assert account.institution == "Test Bank"
        assert account.account_type == AccountType.SAVINGS
        assert account.created_date == now
        assert account.last_updated == now
        assert account.metadata is None

    def test_base_account_get_current_value_not_implemented(self):
        """Test that BaseAccount.get_current_value raises NotImplementedError."""
        now = datetime.now()
        account = BaseAccount(
            id="test-1",
            name="Test Account",
            institution="Test Bank",
            account_type=AccountType.SAVINGS,
            created_date=now,
            last_updated=now
        )

        with pytest.raises(NotImplementedError):
            account.get_current_value()


class TestCDAccount:
    """Test CDAccount model."""

    def test_cd_account_creation(self):
        """Test CDAccount creation with valid data."""
        now = datetime.now()
        maturity_date = date.today() + timedelta(days=365)

        cd = CDAccount(
            id="cd-1",
            name="Test CD",
            institution="Test Bank",
            account_type=AccountType.CD,
            created_date=now,
            last_updated=now,
            principal_amount=10000.0,
            interest_rate=2.5,
            maturity_date=maturity_date,
            current_value=10250.0
        )

        assert cd.principal_amount == 10000.0
        assert cd.interest_rate == 2.5
        assert cd.maturity_date == maturity_date
        assert cd.current_value == 10250.0
        assert cd.get_current_value() == 10250.0

    def test_cd_account_validation_negative_principal(self):
        """Test CDAccount validation for negative principal amount."""
        now = datetime.now()
        maturity_date = date.today() + timedelta(days=365)

        with pytest.raises(ValueError, match="Principal amount must be positive"):
            CDAccount(
                id="cd-1",
                name="Test CD",
                institution="Test Bank",
                account_type=AccountType.CD,
                created_date=now,
                last_updated=now,
                principal_amount=-1000.0,
                interest_rate=2.5,
                maturity_date=maturity_date,
                current_value=10250.0
            )

    def test_cd_account_validation_negative_interest_rate(self):
        """Test CDAccount validation for negative interest rate."""
        now = datetime.now()
        maturity_date = date.today() + timedelta(days=365)

        with pytest.raises(ValueError, match="Interest rate cannot be negative"):
            CDAccount(
                id="cd-1",
                name="Test CD",
                institution="Test Bank",
                account_type=AccountType.CD,
                created_date=now,
                last_updated=now,
                principal_amount=10000.0,
                interest_rate=-2.5,
                maturity_date=maturity_date,
                current_value=10250.0
            )

    def test_cd_account_validation_past_maturity_date(self):
        """Test CDAccount validation for past maturity date."""
        now = datetime.now()
        past_date = date.today() - timedelta(days=1)

        with pytest.raises(ValueError, match="Maturity date must be in the future"):
            CDAccount(
                id="cd-1",
                name="Test CD",
                institution="Test Bank",
                account_type=AccountType.CD,
                created_date=now,
                last_updated=now,
                principal_amount=10000.0,
                interest_rate=2.5,
                maturity_date=past_date,
                current_value=10250.0
            )

    def test_cd_account_validation_negative_current_value(self):
        """Test CDAccount validation for negative current value."""
        now = datetime.now()
        maturity_date = date.today() + timedelta(days=365)

        with pytest.raises(ValueError, match="Current value cannot be negative"):
            CDAccount(
                id="cd-1",
                name="Test CD",
                institution="Test Bank",
                account_type=AccountType.CD,
                created_date=now,
                last_updated=now,
                principal_amount=10000.0,
                interest_rate=2.5,
                maturity_date=maturity_date,
                current_value=-100.0
            )

    def test_cd_account_serialization(self):
        """Test CDAccount to_dict and from_dict methods."""
        now = datetime.now()
        maturity_date = date.today() + timedelta(days=365)

        cd = CDAccount(
            id="cd-1",
            name="Test CD",
            institution="Test Bank",
            account_type=AccountType.CD,
            created_date=now,
            last_updated=now,
            principal_amount=10000.0,
            interest_rate=2.5,
            maturity_date=maturity_date,
            current_value=10250.0
        )

        data = cd.to_dict()
        assert data['maturity_date'] == maturity_date.isoformat()
        assert data['principal_amount'] == 10000.0

        cd_restored = CDAccount.from_dict(data)
        assert cd_restored.maturity_date == maturity_date
        assert cd_restored.principal_amount == 10000.0
        assert cd_restored.account_type == AccountType.CD


class TestSavingsAccount:
    """Test SavingsAccount model."""

    def test_savings_account_creation(self):
        """Test SavingsAccount creation with valid data."""
        now = datetime.now()

        savings = SavingsAccount(
            id="savings-1",
            name="Test Savings",
            institution="Test Bank",
            account_type=AccountType.SAVINGS,
            created_date=now,
            last_updated=now,
            current_balance=5000.0,
            interest_rate=1.5
        )

        assert savings.current_balance == 5000.0
        assert savings.interest_rate == 1.5
        assert savings.get_current_value() == 5000.0

    def test_savings_account_validation_negative_balance(self):
        """Test SavingsAccount validation for negative balance."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Current balance cannot be negative"):
            SavingsAccount(
                id="savings-1",
                name="Test Savings",
                institution="Test Bank",
                account_type=AccountType.SAVINGS,
                created_date=now,
                last_updated=now,
                current_balance=-1000.0,
                interest_rate=1.5
            )

    def test_savings_account_validation_negative_interest_rate(self):
        """Test SavingsAccount validation for negative interest rate."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Interest rate cannot be negative"):
            SavingsAccount(
                id="savings-1",
                name="Test Savings",
                institution="Test Bank",
                account_type=AccountType.SAVINGS,
                created_date=now,
                last_updated=now,
                current_balance=5000.0,
                interest_rate=-1.5
            )


class TestAccount401k:
    """Test Account401k model."""

    def test_401k_account_creation(self):
        """Test Account401k creation with valid data."""
        now = datetime.now()

        account_401k = Account401k(
            id="401k-1",
            name="Test 401k",
            institution="Test Company",
            account_type=AccountType.ACCOUNT_401K,
            created_date=now,
            last_updated=now,
            current_balance=50000.0,
            employer_match=0.05,
            contribution_limit=22500.0,
            employer_contribution=2500.0
        )

        assert account_401k.current_balance == 50000.0
        assert account_401k.employer_match == 0.05
        assert account_401k.contribution_limit == 22500.0
        assert account_401k.employer_contribution == 2500.0
        assert account_401k.get_current_value() == 50000.0

    def test_401k_account_validation_negative_balance(self):
        """Test Account401k validation for negative balance."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Current balance cannot be negative"):
            Account401k(
                id="401k-1",
                name="Test 401k",
                institution="Test Company",
                account_type=AccountType.ACCOUNT_401K,
                created_date=now,
                last_updated=now,
                current_balance=-1000.0,
                employer_match=0.05,
                contribution_limit=22500.0,
                employer_contribution=2500.0
            )

    def test_401k_account_validation_negative_employer_match(self):
        """Test Account401k validation for negative employer match."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Employer match cannot be negative"):
            Account401k(
                id="401k-1",
                name="Test 401k",
                institution="Test Company",
                account_type=AccountType.ACCOUNT_401K,
                created_date=now,
                last_updated=now,
                current_balance=50000.0,
                employer_match=-0.05,
                contribution_limit=22500.0,
                employer_contribution=2500.0
            )

    def test_401k_account_validation_zero_contribution_limit(self):
        """Test Account401k validation for zero contribution limit."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Contribution limit must be positive"):
            Account401k(
                id="401k-1",
                name="Test 401k",
                institution="Test Company",
                account_type=AccountType.ACCOUNT_401K,
                created_date=now,
                last_updated=now,
                current_balance=50000.0,
                employer_match=0.05,
                contribution_limit=0.0,
                employer_contribution=2500.0
            )

    def test_401k_account_validation_negative_employer_contribution(self):
        """Test Account401k validation for negative employer contribution."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Employer contribution cannot be negative"):
            Account401k(
                id="401k-1",
                name="Test 401k",
                institution="Test Company",
                account_type=AccountType.ACCOUNT_401K,
                created_date=now,
                last_updated=now,
                current_balance=50000.0,
                employer_match=0.05,
                contribution_limit=22500.0,
                employer_contribution=-2500.0
            )


class TestStockPosition:
    """Test StockPosition model."""

    def test_stock_position_creation(self):
        """Test StockPosition creation with valid data."""
        purchase_date = date.today() - timedelta(days=30)
        now = datetime.now()

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0,
            last_updated=now
        )

        assert position.symbol == "AAPL"
        assert position.shares == 100.0
        assert position.purchase_price == 150.0
        assert position.purchase_date == purchase_date
        assert position.current_price == 160.0
        assert position.last_updated == now

    def test_stock_position_without_current_price(self):
        """Test StockPosition creation without current price."""
        purchase_date = date.today() - timedelta(days=30)

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date
        )

        assert position.current_price is None
        assert position.last_updated is None

    def test_stock_position_get_current_value(self):
        """Test StockPosition current value calculation."""
        purchase_date = date.today() - timedelta(days=30)

        # With current price
        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0
        )
        assert position.get_current_value() == 16000.0

        # Without current price (uses purchase price)
        position_no_current = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date
        )
        assert position_no_current.get_current_value() == 15000.0

    def test_stock_position_unrealized_gain_loss(self):
        """Test StockPosition unrealized gain/loss calculations."""
        purchase_date = date.today() - timedelta(days=30)

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0
        )

        assert position.get_unrealized_gain_loss() == 1000.0  # (160-150) * 100
        assert position.get_unrealized_gain_loss_percentage() == pytest.approx(6.67, rel=1e-2)

        # Test with loss
        position_loss = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=140.0
        )

        assert position_loss.get_unrealized_gain_loss() == -1000.0
        assert position_loss.get_unrealized_gain_loss_percentage() == pytest.approx(-6.67, rel=1e-2)

        # Test without current price
        position_no_current = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date
        )

        assert position_no_current.get_unrealized_gain_loss() == 0.0
        assert position_no_current.get_unrealized_gain_loss_percentage() == 0.0

    def test_stock_position_validation_empty_symbol(self):
        """Test StockPosition validation for empty symbol."""
        purchase_date = date.today() - timedelta(days=30)

        with pytest.raises(ValueError, match="Stock symbol cannot be empty"):
            StockPosition(
                symbol="",
                shares=100.0,
                purchase_price=150.0,
                purchase_date=purchase_date
            )

    def test_stock_position_validation_zero_shares(self):
        """Test StockPosition validation for zero shares."""
        purchase_date = date.today() - timedelta(days=30)

        with pytest.raises(ValueError, match="Number of shares must be positive"):
            StockPosition(
                symbol="AAPL",
                shares=0.0,
                purchase_price=150.0,
                purchase_date=purchase_date
            )

    def test_stock_position_validation_zero_purchase_price(self):
        """Test StockPosition validation for zero purchase price."""
        purchase_date = date.today() - timedelta(days=30)

        with pytest.raises(ValueError, match="Purchase price must be positive"):
            StockPosition(
                symbol="AAPL",
                shares=100.0,
                purchase_price=0.0,
                purchase_date=purchase_date
            )

    def test_stock_position_validation_future_purchase_date(self):
        """Test StockPosition validation for future purchase date."""
        future_date = date.today() + timedelta(days=1)

        with pytest.raises(ValueError, match="Purchase date cannot be in the future"):
            StockPosition(
                symbol="AAPL",
                shares=100.0,
                purchase_price=150.0,
                purchase_date=future_date
            )

    def test_stock_position_validation_zero_current_price(self):
        """Test StockPosition validation for zero current price."""
        purchase_date = date.today() - timedelta(days=30)

        with pytest.raises(ValueError, match="Current price must be positive"):
            StockPosition(
                symbol="AAPL",
                shares=100.0,
                purchase_price=150.0,
                purchase_date=purchase_date,
                current_price=0.0
            )

    def test_stock_position_serialization(self):
        """Test StockPosition to_dict and from_dict methods."""
        purchase_date = date.today() - timedelta(days=30)
        now = datetime.now()

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0,
            last_updated=now
        )

        data = position.to_dict()
        assert data['purchase_date'] == purchase_date.isoformat()
        assert data['last_updated'] == now.isoformat()

        position_restored = StockPosition.from_dict(data)
        assert position_restored.purchase_date == purchase_date
        assert position_restored.last_updated == now
        assert position_restored.symbol == "AAPL"


class TestTradingAccount:
    """Test TradingAccount model."""

    def test_trading_account_creation(self):
        """Test TradingAccount creation with valid data."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=30)

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0
        )

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[position]
        )

        assert trading.broker_name == "Test Broker"
        assert trading.cash_balance == 5000.0
        assert len(trading.positions) == 1
        assert trading.positions[0].symbol == "AAPL"
        assert trading.get_current_value() == 21000.0  # 5000 cash + 16000 stock value

    def test_trading_account_empty_positions(self):
        """Test TradingAccount with empty positions list."""
        now = datetime.now()

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[]
        )

        assert len(trading.positions) == 0
        assert trading.get_current_value() == 5000.0  # Only cash balance
        assert trading.get_total_unrealized_gain_loss() == 0.0

    def test_trading_account_position_management(self):
        """Test TradingAccount position management methods."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=30)

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[]
        )

        # Add position
        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0
        )
        trading.add_position(position)
        assert len(trading.positions) == 1

        # Get position
        found_position = trading.get_position("AAPL")
        assert found_position is not None
        assert found_position.symbol == "AAPL"

        # Position not found
        not_found = trading.get_position("GOOGL")
        assert not_found is None

        # Remove position
        removed = trading.remove_position("AAPL")
        assert removed is True
        assert len(trading.positions) == 0

        # Remove non-existent position
        not_removed = trading.remove_position("GOOGL")
        assert not_removed is False

    def test_trading_account_total_unrealized_gain_loss(self):
        """Test TradingAccount total unrealized gain/loss calculation."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=30)

        position1 = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0  # +1000 gain
        )

        position2 = StockPosition(
            symbol="GOOGL",
            shares=10.0,
            purchase_price=2500.0,
            purchase_date=purchase_date,
            current_price=2400.0  # -1000 loss
        )

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[position1, position2]
        )

        assert trading.get_total_unrealized_gain_loss() == 0.0  # +1000 - 1000

    def test_trading_account_validation_empty_broker_name(self):
        """Test TradingAccount validation for empty broker name."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Broker name cannot be empty"):
            TradingAccount(
                id="trading-1",
                name="Test Trading",
                institution="Test Broker",
                account_type=AccountType.TRADING,
                created_date=now,
                last_updated=now,
                broker_name="",
                cash_balance=5000.0,
                positions=[]
            )

    def test_trading_account_validation_negative_cash_balance(self):
        """Test TradingAccount validation for negative cash balance."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Cash balance cannot be negative"):
            TradingAccount(
                id="trading-1",
                name="Test Trading",
                institution="Test Broker",
                account_type=AccountType.TRADING,
                created_date=now,
                last_updated=now,
                broker_name="Test Broker",
                cash_balance=-1000.0,
                positions=[]
            )

    def test_trading_account_validation_invalid_positions_type(self):
        """Test TradingAccount validation for invalid positions type."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Positions must be a list"):
            TradingAccount(
                id="trading-1",
                name="Test Trading",
                institution="Test Broker",
                account_type=AccountType.TRADING,
                created_date=now,
                last_updated=now,
                broker_name="Test Broker",
                cash_balance=5000.0,
                positions="not a list"
            )

    def test_trading_account_add_invalid_position(self):
        """Test TradingAccount add_position with invalid position type."""
        now = datetime.now()

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[]
        )

        with pytest.raises(ValueError, match="Position must be a StockPosition instance"):
            trading.add_position("not a position")

    def test_trading_account_serialization(self):
        """Test TradingAccount to_dict and from_dict methods."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=30)

        position = StockPosition(
            symbol="AAPL",
            shares=100.0,
            purchase_price=150.0,
            purchase_date=purchase_date,
            current_price=160.0
        )

        trading = TradingAccount(
            id="trading-1",
            name="Test Trading",
            institution="Test Broker",
            account_type=AccountType.TRADING,
            created_date=now,
            last_updated=now,
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[position]
        )

        data = trading.to_dict()
        assert data['broker_name'] == "Test Broker"
        assert data['cash_balance'] == 5000.0
        assert len(data['positions']) == 1
        assert data['positions'][0]['symbol'] == "AAPL"

        trading_restored = TradingAccount.from_dict(data)
        assert trading_restored.broker_name == "Test Broker"
        assert trading_restored.cash_balance == 5000.0
        assert len(trading_restored.positions) == 1
        assert trading_restored.positions[0].symbol == "AAPL"


class TestIBondsAccount:
    """Test IBondsAccount model."""

    def test_ibonds_account_creation(self):
        """Test IBondsAccount creation with valid data."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)  # 30 years

        ibonds = IBondsAccount(
            id="ibonds-1",
            name="Test I-bonds",
            institution="Treasury Direct",
            account_type=AccountType.I_BONDS,
            created_date=now,
            last_updated=now,
            purchase_amount=10000.0,
            purchase_date=purchase_date,
            current_value=10500.0,
            fixed_rate=0.5,
            inflation_rate=3.2,
            maturity_date=maturity_date
        )

        assert ibonds.purchase_amount == 10000.0
        assert ibonds.purchase_date == purchase_date
        assert ibonds.current_value == 10500.0
        assert ibonds.fixed_rate == 0.5
        assert ibonds.inflation_rate == 3.2
        assert ibonds.maturity_date == maturity_date
        assert ibonds.get_current_value() == 10500.0

    def test_ibonds_account_validation_negative_purchase_amount(self):
        """Test IBondsAccount validation for negative purchase amount."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        with pytest.raises(ValueError, match="Purchase amount must be positive"):
            IBondsAccount(
                id="ibonds-1",
                name="Test I-bonds",
                institution="Treasury Direct",
                account_type=AccountType.I_BONDS,
                created_date=now,
                last_updated=now,
                purchase_amount=-10000.0,
                purchase_date=purchase_date,
                current_value=10500.0,
                fixed_rate=0.5,
                inflation_rate=3.2,
                maturity_date=maturity_date
            )

    def test_ibonds_account_validation_future_purchase_date(self):
        """Test IBondsAccount validation for future purchase date."""
        now = datetime.now()
        future_date = date.today() + timedelta(days=1)
        maturity_date = future_date + timedelta(days=365*30)

        with pytest.raises(ValueError, match="Purchase date cannot be in the future"):
            IBondsAccount(
                id="ibonds-1",
                name="Test I-bonds",
                institution="Treasury Direct",
                account_type=AccountType.I_BONDS,
                created_date=now,
                last_updated=now,
                purchase_amount=10000.0,
                purchase_date=future_date,
                current_value=10500.0,
                fixed_rate=0.5,
                inflation_rate=3.2,
                maturity_date=maturity_date
            )

    def test_ibonds_account_validation_negative_current_value(self):
        """Test IBondsAccount validation for negative current value."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        with pytest.raises(ValueError, match="Current value cannot be negative"):
            IBondsAccount(
                id="ibonds-1",
                name="Test I-bonds",
                institution="Treasury Direct",
                account_type=AccountType.I_BONDS,
                created_date=now,
                last_updated=now,
                purchase_amount=10000.0,
                purchase_date=purchase_date,
                current_value=-100.0,
                fixed_rate=0.5,
                inflation_rate=3.2,
                maturity_date=maturity_date
            )

    def test_ibonds_account_validation_negative_fixed_rate(self):
        """Test IBondsAccount validation for negative fixed rate."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        with pytest.raises(ValueError, match="Fixed rate cannot be negative"):
            IBondsAccount(
                id="ibonds-1",
                name="Test I-bonds",
                institution="Treasury Direct",
                account_type=AccountType.I_BONDS,
                created_date=now,
                last_updated=now,
                purchase_amount=10000.0,
                purchase_date=purchase_date,
                current_value=10500.0,
                fixed_rate=-0.5,
                inflation_rate=3.2,
                maturity_date=maturity_date
            )

    def test_ibonds_account_validation_maturity_before_purchase(self):
        """Test IBondsAccount validation for maturity date before purchase date."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date - timedelta(days=1)

        with pytest.raises(ValueError, match="Maturity date must be after purchase date"):
            IBondsAccount(
                id="ibonds-1",
                name="Test I-bonds",
                institution="Treasury Direct",
                account_type=AccountType.I_BONDS,
                created_date=now,
                last_updated=now,
                purchase_amount=10000.0,
                purchase_date=purchase_date,
                current_value=10500.0,
                fixed_rate=0.5,
                inflation_rate=3.2,
                maturity_date=maturity_date
            )

    def test_ibonds_account_negative_inflation_rate_allowed(self):
        """Test IBondsAccount allows negative inflation rate (deflation)."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        # Should not raise an exception
        ibonds = IBondsAccount(
            id="ibonds-1",
            name="Test I-bonds",
            institution="Treasury Direct",
            account_type=AccountType.I_BONDS,
            created_date=now,
            last_updated=now,
            purchase_amount=10000.0,
            purchase_date=purchase_date,
            current_value=10500.0,
            fixed_rate=0.5,
            inflation_rate=-1.0,  # Negative inflation (deflation)
            maturity_date=maturity_date
        )

        assert ibonds.inflation_rate == -1.0

    def test_ibonds_account_serialization(self):
        """Test IBondsAccount to_dict and from_dict methods."""
        now = datetime.now()
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        ibonds = IBondsAccount(
            id="ibonds-1",
            name="Test I-bonds",
            institution="Treasury Direct",
            account_type=AccountType.I_BONDS,
            created_date=now,
            last_updated=now,
            purchase_amount=10000.0,
            purchase_date=purchase_date,
            current_value=10500.0,
            fixed_rate=0.5,
            inflation_rate=3.2,
            maturity_date=maturity_date
        )

        data = ibonds.to_dict()
        assert data['purchase_date'] == purchase_date.isoformat()
        assert data['maturity_date'] == maturity_date.isoformat()

        ibonds_restored = IBondsAccount.from_dict(data)
        assert ibonds_restored.purchase_date == purchase_date
        assert ibonds_restored.maturity_date == maturity_date
        assert ibonds_restored.purchase_amount == 10000.0


class TestHistoricalSnapshot:
    """Test HistoricalSnapshot model."""

    def test_historical_snapshot_creation(self):
        """Test HistoricalSnapshot creation with valid data."""
        now = datetime.now()

        snapshot = HistoricalSnapshot(
            id="snapshot-1",
            account_id="account-1",
            timestamp=now,
            value=10000.0,
            change_type=ChangeType.MANUAL_UPDATE
        )

        assert snapshot.id == "snapshot-1"
        assert snapshot.account_id == "account-1"
        assert snapshot.timestamp == now
        assert snapshot.value == 10000.0
        assert snapshot.change_type == ChangeType.MANUAL_UPDATE
        assert snapshot.metadata is None

    def test_historical_snapshot_with_metadata(self):
        """Test HistoricalSnapshot with metadata."""
        now = datetime.now()
        metadata = {"note": "Monthly update"}

        snapshot = HistoricalSnapshot(
            id="snapshot-1",
            account_id="account-1",
            timestamp=now,
            value=10000.0,
            change_type=ChangeType.MANUAL_UPDATE,
            metadata=metadata
        )

        assert snapshot.metadata == metadata

    def test_historical_snapshot_validation_empty_id(self):
        """Test HistoricalSnapshot validation for empty ID."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Snapshot ID cannot be empty"):
            HistoricalSnapshot(
                id="",
                account_id="account-1",
                timestamp=now,
                value=10000.0,
                change_type=ChangeType.MANUAL_UPDATE
            )

    def test_historical_snapshot_validation_empty_account_id(self):
        """Test HistoricalSnapshot validation for empty account ID."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Account ID cannot be empty"):
            HistoricalSnapshot(
                id="snapshot-1",
                account_id="",
                timestamp=now,
                value=10000.0,
                change_type=ChangeType.MANUAL_UPDATE
            )

    def test_historical_snapshot_validation_future_timestamp(self):
        """Test HistoricalSnapshot validation for future timestamp."""
        future_time = datetime.now() + timedelta(hours=1)

        with pytest.raises(ValueError, match="Timestamp cannot be in the future"):
            HistoricalSnapshot(
                id="snapshot-1",
                account_id="account-1",
                timestamp=future_time,
                value=10000.0,
                change_type=ChangeType.MANUAL_UPDATE
            )

    def test_historical_snapshot_validation_negative_value(self):
        """Test HistoricalSnapshot validation for negative value."""
        now = datetime.now()

        with pytest.raises(ValueError, match="Value cannot be negative"):
            HistoricalSnapshot(
                id="snapshot-1",
                account_id="account-1",
                timestamp=now,
                value=-1000.0,
                change_type=ChangeType.MANUAL_UPDATE
            )

    def test_historical_snapshot_serialization(self):
        """Test HistoricalSnapshot to_dict and from_dict methods."""
        now = datetime.now()
        metadata = {"note": "Monthly update"}

        snapshot = HistoricalSnapshot(
            id="snapshot-1",
            account_id="account-1",
            timestamp=now,
            value=10000.0,
            change_type=ChangeType.MANUAL_UPDATE,
            metadata=metadata
        )

        data = snapshot.to_dict()
        assert data['change_type'] == "MANUAL_UPDATE"
        assert data['timestamp'] == now.isoformat()
        assert data['metadata'] == metadata

        snapshot_restored = HistoricalSnapshot.from_dict(data)
        assert snapshot_restored.change_type == ChangeType.MANUAL_UPDATE
        assert snapshot_restored.timestamp == now
        assert snapshot_restored.metadata == metadata


class TestAccountFactory:
    """Test AccountFactory registration system and account creation."""

    def test_factory_registered_types(self):
        """Test AccountFactory has all expected account types registered."""
        registered_types = AccountFactory.get_registered_types()

        assert AccountType.CD in registered_types
        assert AccountType.SAVINGS in registered_types
        assert AccountType.ACCOUNT_401K in registered_types
        assert AccountType.TRADING in registered_types
        assert AccountType.I_BONDS in registered_types

    def test_factory_create_cd_account(self):
        """Test AccountFactory creates CDAccount correctly."""
        maturity_date = date.today() + timedelta(days=365)

        cd = AccountFactory.create_account(
            AccountType.CD,
            name="Test CD",
            institution="Test Bank",
            principal_amount=10000.0,
            interest_rate=2.5,
            maturity_date=maturity_date,
            current_value=10250.0
        )

        assert isinstance(cd, CDAccount)
        assert cd.name == "Test CD"
        assert cd.institution == "Test Bank"
        assert cd.account_type == AccountType.CD
        assert cd.principal_amount == 10000.0
        assert cd.interest_rate == 2.5
        assert cd.maturity_date == maturity_date
        assert cd.current_value == 10250.0
        # Check that defaults were set
        assert cd.id is not None
        assert cd.created_date is not None
        assert cd.last_updated is not None

    def test_factory_create_savings_account(self):
        """Test AccountFactory creates SavingsAccount correctly."""
        savings = AccountFactory.create_account(
            AccountType.SAVINGS,
            name="Test Savings",
            institution="Test Bank",
            current_balance=5000.0,
            interest_rate=1.5
        )

        assert isinstance(savings, SavingsAccount)
        assert savings.name == "Test Savings"
        assert savings.account_type == AccountType.SAVINGS
        assert savings.current_balance == 5000.0
        assert savings.interest_rate == 1.5

    def test_factory_create_401k_account(self):
        """Test AccountFactory creates Account401k correctly."""
        account_401k = AccountFactory.create_account(
            AccountType.ACCOUNT_401K,
            name="Test 401k",
            institution="Test Company",
            current_balance=50000.0,
            employer_match=0.05,
            contribution_limit=22500.0,
            employer_contribution=2500.0
        )

        assert isinstance(account_401k, Account401k)
        assert account_401k.name == "Test 401k"
        assert account_401k.account_type == AccountType.ACCOUNT_401K
        assert account_401k.current_balance == 50000.0

    def test_factory_create_trading_account(self):
        """Test AccountFactory creates TradingAccount correctly."""
        trading = AccountFactory.create_account(
            AccountType.TRADING,
            name="Test Trading",
            institution="Test Broker",
            broker_name="Test Broker",
            cash_balance=5000.0,
            positions=[]
        )

        assert isinstance(trading, TradingAccount)
        assert trading.name == "Test Trading"
        assert trading.account_type == AccountType.TRADING
        assert trading.broker_name == "Test Broker"
        assert trading.cash_balance == 5000.0
        assert trading.positions == []

    def test_factory_create_ibonds_account(self):
        """Test AccountFactory creates IBondsAccount correctly."""
        purchase_date = date.today() - timedelta(days=365)
        maturity_date = purchase_date + timedelta(days=365*30)

        ibonds = AccountFactory.create_account(
            AccountType.I_BONDS,
            name="Test I-bonds",
            institution="Treasury Direct",
            purchase_amount=10000.0,
            purchase_date=purchase_date,
            current_value=10500.0,
            fixed_rate=0.5,
            inflation_rate=3.2,
            maturity_date=maturity_date
        )

        assert isinstance(ibonds, IBondsAccount)
        assert ibonds.name == "Test I-bonds"
        assert ibonds.account_type == AccountType.I_BONDS
        assert ibonds.purchase_amount == 10000.0

    def test_factory_create_unknown_account_type(self):
        """Test AccountFactory raises error for unknown account type."""
        # Create a new enum value that's not registered
        class UnknownAccountType(Enum):
            UNKNOWN = "UNKNOWN"

        with pytest.raises(ValueError, match="Unknown account type"):
            AccountFactory.create_account(
                UnknownAccountType.UNKNOWN,
                name="Test Unknown",
                institution="Test Bank"
            )

    def test_factory_create_with_custom_defaults(self):
        """Test AccountFactory respects provided default values."""
        now = datetime.now()
        custom_id = "custom-id-123"

        savings = AccountFactory.create_account(
            AccountType.SAVINGS,
            id=custom_id,
            name="Test Savings",
            institution="Test Bank",
            created_date=now,
            last_updated=now,
            current_balance=5000.0,
            interest_rate=1.5
        )

        assert savings.id == custom_id
        assert savings.created_date == now
        assert savings.last_updated == now

    def test_factory_create_account_from_dict(self):
        """Test AccountFactory creates account from dictionary data."""
        now = datetime.now()
        data = {
            'id': "savings-1",
            'name': "Test Savings",
            'institution': "Test Bank",
            'account_type': "SAVINGS",
            'created_date': now.isoformat(),
            'last_updated': now.isoformat(),
            'metadata': None,
            'current_balance': 5000.0,
            'interest_rate': 1.5
        }

        savings = AccountFactory.create_account_from_dict(data)
        assert isinstance(savings, SavingsAccount)
        assert savings.id == "savings-1"
        assert savings.name == "Test Savings"
        assert savings.account_type == AccountType.SAVINGS
        assert savings.current_balance == 5000.0

    def test_factory_create_account_from_dict_unknown_type(self):
        """Test AccountFactory raises error for unknown type in dictionary."""
        now = datetime.now()
        data = {
            'id': "unknown-1",
            'name': "Test Unknown",
            'institution': "Test Bank",
            'account_type': "UNKNOWN_TYPE",
            'created_date': now.isoformat(),
            'last_updated': now.isoformat(),
            'metadata': None
        }

        with pytest.raises(ValueError, match="is not a valid AccountType"):
            AccountFactory.create_account_from_dict(data)

    def test_factory_registration_system(self):
        """Test AccountFactory registration and unregistration system."""
        # Create a custom account type for testing
        class CustomAccountType(Enum):
            CUSTOM = "CUSTOM"

        @dataclass
        class CustomAccount(BaseAccount):
            custom_field: str = "default"

            def get_current_value(self) -> float:
                return 1000.0

        # Register new account type
        AccountFactory.register_account_type(CustomAccountType.CUSTOM, CustomAccount)

        # Verify it's registered
        registered_types = AccountFactory.get_registered_types()
        assert CustomAccountType.CUSTOM in registered_types

        # Create account of new type
        custom_account = AccountFactory.create_account(
            CustomAccountType.CUSTOM,
            name="Custom Account",
            institution="Custom Bank",
            custom_field="custom_value"
        )

        assert isinstance(custom_account, CustomAccount)
        assert custom_account.custom_field == "custom_value"

        # Unregister the type
        AccountFactory.unregister_account_type(CustomAccountType.CUSTOM)

        # Verify it's no longer registered
        registered_types = AccountFactory.get_registered_types()
        assert CustomAccountType.CUSTOM not in registered_types

        # Should raise error when trying to create
        with pytest.raises(ValueError, match="Unknown account type"):
            AccountFactory.create_account(
                CustomAccountType.CUSTOM,
                name="Custom Account",
                institution="Custom Bank"
            )

    def test_factory_registration_invalid_class(self):
        """Test AccountFactory raises error when registering invalid class."""
        class CustomAccountType(Enum):
            CUSTOM = "CUSTOM"

        class NotAnAccount:
            pass

        with pytest.raises(ValueError, match="Account class must inherit from BaseAccount"):
            AccountFactory.register_account_type(CustomAccountType.CUSTOM, NotAnAccount)


if __name__ == "__main__":
    pytest.main([__file__])