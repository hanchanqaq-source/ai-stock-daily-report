"""Business service boundary for the local SQLite persistence foundation."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from src.repositories.sqlite_foundation import (
    AppDataDirs,
    LocalFoundationRepository,
    SQLiteConnectionManager,
    resolve_app_data_dirs,
)


class LocalPersistenceService:
    """Small service layer used by tests and future localhost APIs.

    It owns initialization and delegates persistence to repositories.  Future E2
    UI/API work should call this service instead of opening SQLite from the
    frontend or route handlers.
    """

    def __init__(self, data_dirs: AppDataDirs):
        self.data_dirs = data_dirs
        self.manager = SQLiteConnectionManager(data_dirs.database_path)
        self.repository = LocalFoundationRepository(self.manager)

    @classmethod
    def for_test_dir(cls, base_dir: str | Path) -> "LocalPersistenceService":
        return cls(resolve_app_data_dirs(base_dir, test=True))

    def initialize(self) -> None:
        self.manager.initialize()

    def schema_version(self) -> str | None:
        return self.manager.schema_version()

    def create_user(self, display_name: str) -> str:
        if not display_name.strip():
            raise ValueError("display_name is required")
        return self.repository.create_user(display_name.strip())

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        return self.repository.get_user(user_id)

    def save_app_state(self, user_id: str, key: str, value: str) -> str:
        if self.get_user(user_id) is None:
            raise ValueError("user_id does not exist")
        return self.repository.save_app_state(user_id, key, value)

    def save_stock_holding(self, user_id: str, symbol: str, name: str, quantity: float, average_cost: float | None = None) -> str:
        if self.get_user(user_id) is None:
            raise ValueError("user_id does not exist")
        if quantity < 0:
            raise ValueError("quantity must be non-negative")
        return self.repository.add_stock_holding(user_id, symbol, name, quantity, average_cost)

    def save_fund_holding(self, user_id: str, fund_code: str, name: str, amount: float) -> str:
        if self.get_user(user_id) is None:
            raise ValueError("user_id does not exist")
        if amount < 0:
            raise ValueError("amount must be non-negative")
        return self.repository.add_fund_holding(user_id, fund_code, name, amount)

    def list_stock_holdings(self, user_id: str) -> list[dict[str, Any]]:
        return self.repository.list_stock_holdings(user_id)

    def list_fund_holdings(self, user_id: str) -> list[dict[str, Any]]:
        return self.repository.list_fund_holdings(user_id)
