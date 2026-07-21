import os
import sqlite3

import pytest

from src.repositories.sqlite_foundation import INITIAL_MIGRATION_ID, SQLiteConnectionManager, resolve_app_data_dirs
from src.services.sqlite_foundation_service import LocalPersistenceService


def test_empty_database_initializes_all_required_tables(tmp_path):
    service = LocalPersistenceService.for_test_dir(tmp_path)
    service.initialize()
    assert service.data_dirs.database_path.exists()
    with sqlite3.connect(service.data_dirs.database_path) as conn:
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {
        "schema_version", "users", "app_state", "stock_holdings", "fund_holdings",
        "stock_watchlist", "fund_watchlist", "user_preferences", "stock_analysis_records",
        "fund_analysis_records", "stock_chat_sessions", "fund_chat_sessions",
        "data_migrations", "backup_records",
    } <= tables


def test_repeated_initialization_and_migration_are_idempotent(tmp_path):
    service = LocalPersistenceService.for_test_dir(tmp_path)
    service.initialize()
    service.initialize()
    with sqlite3.connect(service.data_dirs.database_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM data_migrations WHERE id=?", (INITIAL_MIGRATION_ID,)).fetchone()[0] == 1


def test_schema_version_readable(tmp_path):
    service = LocalPersistenceService.for_test_dir(tmp_path)
    service.initialize()
    assert service.schema_version() == INITIAL_MIGRATION_ID


def test_migration_transaction_rolls_back(monkeypatch, tmp_path):
    import src.repositories.sqlite_foundation as foundation
    manager = SQLiteConnectionManager(tmp_path / "broken.db")
    original = foundation._apply_initial_schema
    def fail_after_schema(conn):
        original(conn)
        raise RuntimeError("boom")
    monkeypatch.setattr(foundation, "_apply_initial_schema", fail_after_schema)
    with pytest.raises(RuntimeError):
        manager.initialize()
    with sqlite3.connect(tmp_path / "broken.db") as conn:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'").fetchall()
    assert rows == []


def test_users_and_stock_fund_holdings_are_isolated(tmp_path):
    service = LocalPersistenceService.for_test_dir(tmp_path)
    service.initialize()
    alice = service.create_user("Alice")
    bob = service.create_user("Bob")
    service.save_app_state(alice, "active_center", "stock")
    service.save_stock_holding(alice, "AAPL", "Apple", 3, 100)
    service.save_fund_holding(alice, "000001", "Fake Fund", 2000)
    service.save_stock_holding(bob, "MSFT", "Microsoft", 2, 50)
    assert [row["symbol"] for row in service.list_stock_holdings(alice)] == ["AAPL"]
    assert [row["symbol"] for row in service.list_stock_holdings(bob)] == ["MSFT"]
    assert [row["fund_code"] for row in service.list_fund_holdings(alice)] == ["000001"]
    assert service.list_fund_holdings(bob) == []


def test_temporary_data_directories_are_created_safely(tmp_path):
    dirs = resolve_app_data_dirs(tmp_path / "nested" / "data", test=True)
    service = LocalPersistenceService(dirs)
    service.initialize()
    assert dirs.user_data_dir.exists()
    assert dirs.database_path.parent == dirs.user_data_dir


def test_unwritable_database_path_returns_clear_error(tmp_path):
    bad_path = tmp_path / "as-directory.db"
    bad_path.mkdir()
    manager = SQLiteConnectionManager(bad_path)
    with pytest.raises(Exception) as excinfo:
        manager.initialize()
    assert "SQLite database error" in str(excinfo.value) or "Cannot" in str(excinfo.value)


def test_database_files_are_gitignored():
    with open(".gitignore", encoding="utf-8") as fh:
        ignored = fh.read()
    assert "*.db" in ignored
    assert "*.sqlite" in ignored
    assert "*.sqlite3" in ignored
