"""
Account data models for the networth tracker application.

This module contains all account types and related data models including:
- BaseAccount and all account type subclasses
- StockPosition for trading accounts
- HistoricalSnapshot for tracking value changes over time
- AccountFactory for extensible account creation
"""

from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any, Type
from datetime import date, datetime
from enum import Enum
import uuid


class AccountType(Enum):
    """Enumeration of supported account types."""
    CD = "CD"
    SAVINGS = "SAVINGS"
    ACCOUNT_401K = "401K"
    TRADING = "TRADING"
    I_BONDS = "I_BONDS"
    HSA = "HSA"


class ChangeType(Enum):
    """Enumeration of change types for historical tracking."""
    MANUAL_UPDATE = "MANUAL_UPDATE"
    STOCK_PRICE_UPDATE = "STOCK_PRICE_UPDATE"
    INITIAL_ENTRY = "INITIAL_ENTRY"


@dataclass
class BaseAccount:
    """Base account class with common fields for all account types."""
    id: str
    name: str
    institution: str
    account_type: AccountType
    created_date: datetime
    last_updated: datetime
    # Flexible metadata field for future investment product attributes
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert account to dictionary representation."""
        data = asdict(self)
        # Convert enum to string for serialization
        data['account_type'] = self.account_type.value
        # Convert datetime objects to ISO format strings
        data['created_date'] = self.created_date.isoformat()
        data['last_updated'] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseAccount':
        """Create account instance from dictionary."""
        # Convert string back to enum
        data['account_type'] = AccountType(data['account_type'])
        # Convert ISO format strings back to datetime objects
        data['created_date'] = datetime.fromisoformat(data['created_date'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)

    def get_current_value(self) -> float:
        """Get current value of the account. Must be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement get_current_value()")


@dataclass
class CDAccount(BaseAccount):
    """Certificate of Deposit account with fixed term and interest rate."""
    principal_amount: float = 0.0
    interest_rate: float = 0.0
    maturity_date: Optional[date] = None
    current_value: float = 0.0

    def __post_init__(self):
        """Validate CD account data after initialization."""
        if self.principal_amount <= 0:
            raise ValueError("Principal amount must be positive")
        if self.interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")
        if self.maturity_date is None or self.maturity_date <= date.today():
            raise ValueError("Maturity date must be in the future")
        if self.current_value < 0:
            raise ValueError("Current value cannot be negative")

    def get_current_value(self) -> float:
        """Return the current value of the CD."""
        return self.current_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert CD account to dictionary representation."""
        data = super().to_dict()
        # Convert date to ISO format string
        if self.maturity_date:
            data['maturity_date'] = self.maturity_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CDAccount':
        """Create CD account instance from dictionary."""
        # Convert ISO format string back to date object
        if data.get('maturity_date'):
            data['maturity_date'] = date.fromisoformat(data['maturity_date'])
        # Handle base class conversions
        data['account_type'] = AccountType(data['account_type'])
        data['created_date'] = datetime.fromisoformat(data['created_date'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


@dataclass
class SavingsAccount(BaseAccount):
    """Savings account with current balance and interest rate."""
    current_balance: float = 0.0
    interest_rate: float = 0.0

    def __post_init__(self):
        """Validate savings account data after initialization."""
        if self.current_balance < 0:
            raise ValueError("Current balance cannot be negative")
        if self.interest_rate < 0:
            raise ValueError("Interest rate cannot be negative")

    def get_current_value(self) -> float:
        """Return the current balance of the savings account."""
        return self.current_balance


@dataclass
class Account401k(BaseAccount):
    """401k retirement account with employer matching and contribution limits."""
    current_balance: float = 0.0
    employer_match: float = 0.0
    contribution_limit: float = 0.0
    employer_contribution: float = 0.0

    def __post_init__(self):
        """Validate 401k account data after initialization."""
        if self.current_balance < 0:
            raise ValueError("Current balance cannot be negative")
        if self.employer_match < 0:
            raise ValueError("Employer match cannot be negative")
        if self.contribution_limit <= 0:
            raise ValueError("Contribution limit must be positive")
        if self.employer_contribution < 0:
            raise ValueError("Employer contribution cannot be negative")

    def get_current_value(self) -> float:
        """Return the current balance of the 401k account."""
        return self.current_balance


@dataclass
class StockPosition:
    """Individual stock position within a trading account."""
    symbol: str = ""
    shares: float = 0.0
    purchase_price: float = 0.0
    purchase_date: Optional[date] = None
    current_price: Optional[float] = None
    last_updated: Optional[datetime] = None

    def __post_init__(self):
        """Validate stock position data after initialization."""
        if not self.symbol or not self.symbol.strip():
            raise ValueError("Stock symbol cannot be empty")
        if self.shares <= 0:
            raise ValueError("Number of shares must be positive")
        if self.purchase_price <= 0:
            raise ValueError("Purchase price must be positive")
        if self.purchase_date is None or self.purchase_date > date.today():
            raise ValueError("Purchase date cannot be in the future")
        if self.current_price is not None and self.current_price <= 0:
            raise ValueError("Current price must be positive")

    def get_current_value(self) -> float:
        """Calculate current value of the stock position."""
        price = self.current_price if self.current_price is not None else self.purchase_price
        return self.shares * price

    def get_unrealized_gain_loss(self) -> float:
        """Calculate unrealized gain/loss for the position."""
        if self.current_price is None:
            return 0.0
        return (self.current_price - self.purchase_price) * self.shares

    def get_unrealized_gain_loss_percentage(self) -> float:
        """Calculate unrealized gain/loss percentage for the position."""
        if self.current_price is None:
            return 0.0
        return ((self.current_price - self.purchase_price) / self.purchase_price) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert stock position to dictionary representation."""
        data = asdict(self)
        # Convert date to ISO format string
        if self.purchase_date:
            data['purchase_date'] = self.purchase_date.isoformat()
        # Convert datetime to ISO format string if present
        if self.last_updated:
            data['last_updated'] = self.last_updated.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StockPosition':
        """Create stock position instance from dictionary."""
        # Convert ISO format string back to date object
        if data.get('purchase_date'):
            data['purchase_date'] = date.fromisoformat(data['purchase_date'])
        # Convert ISO format string back to datetime object if present
        if data.get('last_updated'):
            data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


@dataclass
class TradingAccount(BaseAccount):
    """Trading account with broker information and stock positions."""
    broker_name: str = ""
    cash_balance: float = 0.0
    positions: List[StockPosition] = None

    def __post_init__(self):
        """Validate trading account data after initialization."""
        if self.positions is None:
            self.positions = []
        if not self.broker_name or not self.broker_name.strip():
            raise ValueError("Broker name cannot be empty")
        if self.cash_balance < 0:
            raise ValueError("Cash balance cannot be negative")
        if not isinstance(self.positions, list):
            raise ValueError("Positions must be a list")

    def get_current_value(self) -> float:
        """Calculate total current value including cash and stock positions."""
        stock_value = sum(position.get_current_value() for position in self.positions)
        return self.cash_balance + stock_value

    def get_total_unrealized_gain_loss(self) -> float:
        """Calculate total unrealized gain/loss for all positions."""
        return sum(position.get_unrealized_gain_loss() for position in self.positions)

    def add_position(self, position: StockPosition) -> None:
        """Add a new stock position to the account."""
        if not isinstance(position, StockPosition):
            raise ValueError("Position must be a StockPosition instance")
        self.positions.append(position)

    def remove_position(self, symbol: str) -> bool:
        """Remove a stock position by symbol. Returns True if removed, False if not found."""
        for i, position in enumerate(self.positions):
            if position.symbol == symbol:
                del self.positions[i]
                return True
        return False

    def get_position(self, symbol: str) -> Optional[StockPosition]:
        """Get a stock position by symbol."""
        for position in self.positions:
            if position.symbol == symbol:
                return position
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert trading account to dictionary representation."""
        data = super().to_dict()
        # Convert positions to dictionaries
        data['positions'] = [position.to_dict() for position in self.positions]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TradingAccount':
        """Create trading account instance from dictionary."""
        # Convert positions from dictionaries
        positions_data = data.pop('positions', [])
        positions = [StockPosition.from_dict(pos_data) for pos_data in positions_data]

        # Handle base class conversions
        data['account_type'] = AccountType(data['account_type'])
        data['created_date'] = datetime.fromisoformat(data['created_date'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])

        return cls(positions=positions, **data)


@dataclass
class IBondsAccount(BaseAccount):
    """I-bonds account with purchase information and interest rates."""
    purchase_amount: float = 0.0
    purchase_date: Optional[date] = None
    current_value: float = 0.0
    fixed_rate: float = 0.0
    inflation_rate: float = 0.0
    maturity_date: Optional[date] = None  # 30 years from purchase

    def __post_init__(self):
        """Validate I-bonds account data after initialization."""
        if self.purchase_amount <= 0:
            raise ValueError("Purchase amount must be positive")
        if self.purchase_date is None or self.purchase_date > date.today():
            raise ValueError("Purchase date cannot be in the future")
        if self.current_value < 0:
            raise ValueError("Current value cannot be negative")
        if self.fixed_rate < 0:
            raise ValueError("Fixed rate cannot be negative")
        # Inflation rate can be negative
        if self.maturity_date is None or self.purchase_date is None or self.maturity_date <= self.purchase_date:
            raise ValueError("Maturity date must be after purchase date")

    def get_current_value(self) -> float:
        """Return the current value of the I-bonds."""
        return self.current_value

    def to_dict(self) -> Dict[str, Any]:
        """Convert I-bonds account to dictionary representation."""
        data = super().to_dict()
        # Convert dates to ISO format strings
        if self.purchase_date:
            data['purchase_date'] = self.purchase_date.isoformat()
        if self.maturity_date:
            data['maturity_date'] = self.maturity_date.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'IBondsAccount':
        """Create I-bonds account instance from dictionary."""
        # Convert ISO format strings back to date objects
        if data.get('purchase_date'):
            data['purchase_date'] = date.fromisoformat(data['purchase_date'])
        if data.get('maturity_date'):
            data['maturity_date'] = date.fromisoformat(data['maturity_date'])
        # Handle base class conversions
        data['account_type'] = AccountType(data['account_type'])
        data['created_date'] = datetime.fromisoformat(data['created_date'])
        data['last_updated'] = datetime.fromisoformat(data['last_updated'])
        return cls(**data)


@dataclass
class HSAAccount(BaseAccount):
    """HSA (Health Savings Account) with contribution tracking and tax advantages."""
    current_balance: float = 0.0
    annual_contribution_limit: float = 0.0
    current_year_contributions: float = 0.0
    employer_contributions: float = 0.0
    investment_balance: float = 0.0  # For HSAs that allow investments
    cash_balance: float = 0.0        # Cash portion of HSA

    def __post_init__(self):
        """Validate HSA account data after initialization with comprehensive error handling."""
        from services.error_handler import (
            HSABalanceValidationError, HSABalanceMismatchError,
            HSAContributionValidationError
        )

        # Validate all balance fields are non-negative
        balance_fields = {
            'current_balance': self.current_balance,
            'annual_contribution_limit': self.annual_contribution_limit,
            'current_year_contributions': self.current_year_contributions,
            'employer_contributions': self.employer_contributions,
            'investment_balance': self.investment_balance,
            'cash_balance': self.cash_balance
        }

        for field_name, value in balance_fields.items():
            if value < 0:
                raise HSABalanceValidationError(field_name, value)

        # Validate that investment + cash balance equals current balance
        total_balance = self.investment_balance + self.cash_balance
        if abs(total_balance - self.current_balance) > 0.01:  # Allow for small floating point differences
            raise HSABalanceMismatchError(self.current_balance, self.cash_balance, self.investment_balance)

        # Validate contribution limits
        if self.current_year_contributions > self.annual_contribution_limit:
            raise HSAContributionValidationError(self.current_year_contributions, self.annual_contribution_limit)

    def get_current_value(self) -> float:
        """Return the current balance of the HSA account."""
        return self.current_balance

    def get_remaining_contribution_capacity(self) -> float:
        """Calculate remaining contribution capacity for the current year."""
        return max(0.0, self.annual_contribution_limit - self.current_year_contributions)

    def get_contribution_progress_percentage(self) -> float:
        """Calculate contribution progress as a percentage of the annual limit."""
        if self.annual_contribution_limit == 0:
            return 0.0
        return (self.current_year_contributions / self.annual_contribution_limit) * 100

    def can_contribute(self, amount: float) -> bool:
        """Check if a contribution amount is within the remaining capacity."""
        return amount <= self.get_remaining_contribution_capacity()

    def validate_contribution(self, amount: float) -> None:
        """
        Validate a contribution amount and raise appropriate errors.

        Args:
            amount: Contribution amount to validate

        Raises:
            HSAContributionLimitError: If contribution exceeds remaining capacity
            HSABalanceValidationError: If contribution amount is invalid
        """
        from services.error_handler import HSAContributionLimitError, HSABalanceValidationError

        if amount <= 0:
            raise HSABalanceValidationError("contribution amount", amount)

        remaining_capacity = self.get_remaining_contribution_capacity()
        if amount > remaining_capacity:
            raise HSAContributionLimitError(amount, remaining_capacity)

    def validate_balance_update(self, new_current_balance: float, new_cash_balance: float, new_investment_balance: float) -> None:
        """
        Validate balance update to ensure consistency.

        Args:
            new_current_balance: New total balance
            new_cash_balance: New cash balance
            new_investment_balance: New investment balance

        Raises:
            HSABalanceValidationError: If any balance is negative
            HSABalanceMismatchError: If balances don't add up correctly
        """
        from services.error_handler import HSABalanceValidationError, HSABalanceMismatchError

        # Check for negative values
        if new_current_balance < 0:
            raise HSABalanceValidationError("current_balance", new_current_balance)
        if new_cash_balance < 0:
            raise HSABalanceValidationError("cash_balance", new_cash_balance)
        if new_investment_balance < 0:
            raise HSABalanceValidationError("investment_balance", new_investment_balance)

        # Check balance consistency
        total_balance = new_cash_balance + new_investment_balance
        if abs(total_balance - new_current_balance) > 0.01:
            raise HSABalanceMismatchError(new_current_balance, new_cash_balance, new_investment_balance)


@dataclass
class HistoricalSnapshot:
    """Historical snapshot of account value at a specific point in time."""
    id: str = ""
    account_id: str = ""
    timestamp: Optional[datetime] = None
    value: float = 0.0
    change_type: Optional[ChangeType] = None
    metadata: Optional[Dict[str, Any]] = None

    def __post_init__(self):
        """Validate historical snapshot data after initialization."""
        if not self.id or not self.id.strip():
            raise ValueError("Snapshot ID cannot be empty")
        if not self.account_id or not self.account_id.strip():
            raise ValueError("Account ID cannot be empty")
        if self.timestamp is None or self.timestamp > datetime.now():
            raise ValueError("Timestamp cannot be in the future")
        if self.value < 0:
            raise ValueError("Value cannot be negative")
        if self.change_type is None:
            raise ValueError("Change type cannot be None")

    def to_dict(self) -> Dict[str, Any]:
        """Convert historical snapshot to dictionary representation."""
        data = asdict(self)
        # Convert enum to string for serialization
        if self.change_type:
            data['change_type'] = self.change_type.value
        # Convert datetime to ISO format string
        if self.timestamp:
            data['timestamp'] = self.timestamp.isoformat()
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'HistoricalSnapshot':
        """Create historical snapshot instance from dictionary."""
        # Convert string back to enum
        if data.get('change_type'):
            data['change_type'] = ChangeType(data['change_type'])
        # Convert ISO format string back to datetime object
        if data.get('timestamp'):
            data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)


class AccountFactory:
    """Factory class for creating account instances with extensible registration system."""

    _account_types: Dict[AccountType, Type[BaseAccount]] = {
        AccountType.CD: CDAccount,
        AccountType.SAVINGS: SavingsAccount,
        AccountType.ACCOUNT_401K: Account401k,
        AccountType.TRADING: TradingAccount,
        AccountType.I_BONDS: IBondsAccount,
        AccountType.HSA: HSAAccount,
    }

    @classmethod
    def register_account_type(cls, account_type: AccountType, account_class: Type[BaseAccount]) -> None:
        """Register a new account type for dynamic extensibility."""
        if not issubclass(account_class, BaseAccount):
            raise ValueError("Account class must inherit from BaseAccount")
        cls._account_types[account_type] = account_class

    @classmethod
    def unregister_account_type(cls, account_type: AccountType) -> None:
        """Unregister an account type."""
        if account_type in cls._account_types:
            del cls._account_types[account_type]

    @classmethod
    def get_registered_types(cls) -> List[AccountType]:
        """Get list of all registered account types."""
        return list(cls._account_types.keys())

    @classmethod
    def create_account(cls, account_type: AccountType, **kwargs) -> BaseAccount:
        """Factory method to create accounts of any registered type."""
        if account_type not in cls._account_types:
            raise ValueError(f"Unknown account type: {account_type}")

        account_class = cls._account_types[account_type]

        # Set default values if not provided
        if 'id' not in kwargs:
            kwargs['id'] = str(uuid.uuid4())
        if 'created_date' not in kwargs:
            kwargs['created_date'] = datetime.now()
        if 'last_updated' not in kwargs:
            kwargs['last_updated'] = datetime.now()
        if 'account_type' not in kwargs:
            kwargs['account_type'] = account_type

        return account_class(**kwargs)

    @classmethod
    def create_account_from_dict(cls, data: Dict[str, Any]) -> BaseAccount:
        """Create account instance from dictionary data."""
        account_type = AccountType(data['account_type'])
        if account_type not in cls._account_types:
            raise ValueError(f"Unknown account type: {account_type}")

        account_class = cls._account_types[account_type]
        return account_class.from_dict(data)