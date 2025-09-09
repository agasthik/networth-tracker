# Design Document

## Overview

This design extends the Net Worth Tracker application to support HSA (Health Savings Account) tracking and a Watchlist feature for monitoring stocks without owning them. The implementation follows the existing architectural patterns using the Factory pattern for account creation, encrypted SQLite storage, and Flask API endpoints.

## Architecture

### HSA Account Integration

The HSA account will be integrated into the existing account system by:

1. **Account Model Extension**: Adding `HSAAccount` class to `models/accounts.py` following the same pattern as other account types
2. **Account Type Enum**: Adding `HSA` to the `AccountType` enum
3. **Factory Registration**: Registering the HSA account type in `AccountFactory`
4. **Database Schema**: Using existing encrypted account storage with HSA-specific fields in the encrypted data blob

### Watchlist System Architecture

The Watchlist will be implemented as a separate system alongside accounts:

1. **New Data Model**: `WatchlistItem` class for individual stock entries
2. **Database Table**: New `watchlist` table with encrypted stock data
3. **Service Layer**: `WatchlistService` for CRUD operations and price updates
4. **API Endpoints**: RESTful endpoints for watchlist management
5. **Integration**: Leverage existing `StockPriceService` for real-time price data

## Components and Interfaces

### HSA Account Model

```python
@dataclass
class HSAAccount(BaseAccount):
    """HSA account with contribution tracking and tax advantages."""
    current_balance: float = 0.0
    annual_contribution_limit: float = 0.0
    current_year_contributions: float = 0.0
    employer_contributions: float = 0.0
    investment_balance: float = 0.0  # For HSAs that allow investments
    cash_balance: float = 0.0        # Cash portion of HSA
```

### Watchlist Data Model

```python
@dataclass
class WatchlistItem:
    """Individual stock item in the watchlist."""
    id: str
    symbol: str
    notes: Optional[str] = None
    added_date: datetime = None
    current_price: Optional[float] = None
    last_price_update: Optional[datetime] = None
    daily_change: Optional[float] = None
    daily_change_percent: Optional[float] = None
```

### Database Schema Extensions

#### HSA Account Storage
- Uses existing `accounts` table with `type = 'HSA'`
- HSA-specific data stored in encrypted `encrypted_data` blob
- Follows same pattern as other account types

#### Watchlist Table
```sql
CREATE TABLE watchlist (
    id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL UNIQUE,
    encrypted_data BLOB NOT NULL,
    added_date INTEGER NOT NULL,
    last_price_update INTEGER,
    is_demo BOOLEAN DEFAULT FALSE
);
```

### Service Layer Components

#### WatchlistService
```python
class WatchlistService:
    def __init__(self, db_service: DatabaseService, stock_service: StockPriceService)
    def add_stock(self, symbol: str, notes: str = None) -> str
    def remove_stock(self, symbol: str) -> bool
    def get_watchlist(self) -> List[WatchlistItem]
    def update_prices(self) -> Dict[str, bool]
    def get_stock_details(self, symbol: str) -> Optional[WatchlistItem]
```

#### HSA Account Integration
- Extend existing `AccountFactory` to support HSA accounts
- Use existing `DatabaseService` for encrypted storage
- Integrate with existing historical tracking via `HistoricalDataService`

### API Endpoints

#### HSA Account Endpoints
- Leverage existing account API endpoints (`/api/accounts`)
- HSA accounts handled through existing CRUD operations
- Account type validation extended to include `HSA`

#### Watchlist Endpoints
```
GET    /api/watchlist           - Get all watchlist items
POST   /api/watchlist           - Add stock to watchlist
DELETE /api/watchlist/{symbol}  - Remove stock from watchlist
PUT    /api/watchlist/prices    - Update all stock prices
GET    /api/watchlist/{symbol}  - Get specific stock details
```

## Data Models

### HSA Account Fields
- `current_balance`: Total HSA balance
- `annual_contribution_limit`: IRS contribution limit for current year
- `current_year_contributions`: Contributions made in current tax year
- `employer_contributions`: Employer contribution amount
- `investment_balance`: Portion invested in securities (if applicable)
- `cash_balance`: Cash portion available for medical expenses

### Watchlist Item Fields
- `id`: Unique identifier
- `symbol`: Stock ticker symbol (validated via yfinance)
- `notes`: Optional user notes about the stock
- `added_date`: When stock was added to watchlist
- `current_price`: Latest fetched price
- `last_price_update`: Timestamp of last price update
- `daily_change`: Price change from previous day
- `daily_change_percent`: Percentage change from previous day

## Error Handling

### HSA Account Validation
- Contribution limits validation against IRS limits
- Balance validation (non-negative values)
- Contribution year tracking validation

### Watchlist Validation
- Stock symbol validation using yfinance API
- Duplicate symbol prevention
- Price update error handling with graceful degradation

### Error Response Patterns
Following existing error handling patterns:
- Use existing `AppError` hierarchy
- Consistent JSON error responses
- Proper HTTP status codes
- User-friendly error messages

## Testing Strategy

### Unit Tests
- `test_hsa_account.py`: HSA account model validation and calculations
- `test_watchlist_service.py`: Watchlist CRUD operations and price updates
- `test_watchlist_api.py`: API endpoint testing

### Integration Tests
- HSA account creation and database storage
- Watchlist price update integration with StockPriceService
- End-to-end API testing for both features

### Demo Data Integration
- Extend `generate_demo_database.py` to include sample HSA accounts
- Add diverse watchlist with popular stocks for demo mode
- Ensure demo data follows realistic patterns

## Security Considerations

### Data Encryption
- HSA account data encrypted using existing AES-256 encryption
- Watchlist data (including notes) encrypted in database
- Stock symbols stored in plaintext for indexing efficiency

### API Security
- All endpoints require authentication via existing auth system
- Input validation for stock symbols and HSA data
- Rate limiting for price update operations

## Performance Considerations

### Stock Price Updates
- Batch price updates for watchlist items
- Rate limiting to respect yfinance API limits
- Caching strategy for recent price data
- Asynchronous price updates where possible

### Database Optimization
- Index on watchlist symbol for fast lookups
- Efficient queries for price update operations
- Minimal impact on existing account operations

## User Interface Integration

### HSA Account Forms
- Extend existing account form templates
- HSA-specific form fields for contribution tracking
- Integration with existing account management UI

### Watchlist Interface
- New dedicated watchlist page/section
- Real-time price display with color coding for gains/losses
- Add/remove stock functionality
- Notes editing capability

### Dashboard Integration
- HSA accounts displayed in portfolio overview
- Optional watchlist summary widget
- Consistent styling with existing UI components