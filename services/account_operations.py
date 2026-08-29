"""Transactional account and stock-position mutation workflows."""

from typing import Any, Dict, List, Optional

from models.accounts import ChangeType
from services.database import DatabaseService


class AccountOperationService:
    """Keep balance mutations and their historical snapshots atomic."""

    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service

    def create_account(
        self,
        account_data: Dict[str, Any],
        current_value: float,
        positions: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        with self.db_service.transaction():
            account_id = self.db_service.create_account(account_data)
            if positions is not None:
                self.db_service.replace_stock_positions(account_id, positions)
            self.db_service.create_historical_snapshot(
                account_id,
                current_value,
                ChangeType.INITIAL_ENTRY.value,
                {"event_category": "INITIAL_ENTRY"},
            )
        return account_id

    def update_account(
        self,
        account_id: str,
        account_data: Dict[str, Any],
        previous_value: float,
        current_value: float,
        positions: Optional[List[Dict[str, Any]]] = None,
        change_type: ChangeType = ChangeType.MANUAL_UPDATE,
        cash_flow_amount: float = 0.0,
    ) -> bool:
        with self.db_service.transaction():
            updated = self.db_service.update_account(account_id, account_data)
            if not updated:
                return False
            if positions is not None:
                self.db_service.replace_stock_positions(account_id, positions)
            if abs(current_value - previous_value) > 0.01:
                self.db_service.create_historical_snapshot(
                    account_id,
                    current_value,
                    change_type.value,
                    {
                        "event_category": change_type.value,
                        "cash_flow_amount": cash_flow_amount,
                    },
                )
        return True

    def add_stock_position(
        self,
        account_id: str,
        symbol: str,
        shares: float,
        purchase_price: float,
        purchase_date: int,
    ) -> str:
        with self.db_service.transaction():
            position_id = self.db_service.create_stock_position(
                account_id,
                symbol,
                shares,
                purchase_price,
                purchase_date,
            )
            self._snapshot_trading_account(
                account_id,
                {"operation": "ADD_POSITION", "position_id": position_id},
            )
        return position_id

    def update_stock_position(
        self,
        account_id: str,
        position_id: str,
        updates: Dict[str, Any],
    ) -> bool:
        with self.db_service.transaction():
            updated = self.db_service.update_stock_position(position_id, updates)
            if not updated:
                return False
            self._snapshot_trading_account(
                account_id,
                {"operation": "UPDATE_POSITION", "position_id": position_id},
            )
        return True

    def delete_stock_position(
        self,
        account_id: str,
        position_id: str,
    ) -> bool:
        with self.db_service.transaction():
            deleted = self.db_service.delete_stock_position(position_id)
            if not deleted:
                return False
            self._snapshot_trading_account(
                account_id,
                {"operation": "DELETE_POSITION", "position_id": position_id},
            )
        return True

    def update_stock_prices(
        self,
        account_id: str,
        price_updates: List[Dict[str, Any]],
    ) -> List[str]:
        """Persist a quote batch and its resulting snapshot atomically."""
        updated_position_ids = []
        with self.db_service.transaction():
            for update in price_updates:
                position_id = update["position_id"]
                if not self.db_service.update_stock_price(
                    position_id, float(update["price"])
                ):
                    raise ValueError(
                        f"Stock position not found during price update: {position_id}"
                    )
                updated_position_ids.append(position_id)

            if updated_position_ids:
                self._snapshot_trading_account(
                    account_id,
                    {
                        "operation": "UPDATE_PRICES",
                        "position_ids": updated_position_ids,
                    },
                    ChangeType.STOCK_PRICE_UPDATE,
                )
        return updated_position_ids

    def _snapshot_trading_account(
        self,
        account_id: str,
        metadata: Dict[str, Any],
        change_type: ChangeType = ChangeType.HOLDINGS_CHANGE,
    ) -> None:
        account = self.db_service.get_account(account_id)
        if not account:
            raise ValueError(f"Trading account not found: {account_id}")

        total_value = float(account.get("cash_balance", 0.0))
        for position in self.db_service.get_stock_positions(account_id):
            price = position.get("current_price")
            if price is None:
                price = position["purchase_price"]
            total_value += float(position["shares"]) * float(price)

        snapshot_metadata = {
            "event_category": change_type.value,
            "cash_flow_amount": 0.0,
            **metadata,
        }
        self.db_service.create_historical_snapshot(
            account_id,
            total_value,
            change_type.value,
            snapshot_metadata,
        )
