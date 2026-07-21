"""SQLite persistence foundation for the local stock/fund workspace.

This module intentionally uses the Python standard library sqlite3.  It is a
small foundation for user, holding, watchlist, preference, analysis and chat
persistence; API and UI layers must call services/repositories instead of
opening the database directly.
"""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
import os
import sqlite3
import tempfile
import uuid
from typing import Any, Iterator

APP_DIR_NAME = "ai-stock-daily-report"
DB_FILENAME = "stock_fund_quality.db"
INITIAL_MIGRATION_ID = "0001_initial_schema"


class SQLiteFoundationError(RuntimeError):
    """Raised when the local SQLite foundation cannot be initialized or used."""


@dataclass(frozen=True)
class AppDataDirs:
    program_dir: Path
    user_data_dir: Path
    cache_dir: Path
    log_dir: Path
    backup_dir: Path
    test_data_dir: Path

    @property
    def database_path(self) -> Path:
        return self.user_data_dir / DB_FILENAME


def resolve_app_data_dirs(base_dir: str | os.PathLike[str] | None = None, *, test: bool = False) -> AppDataDirs:
    """Resolve program, user-data, cache, log, backup and test-data directories.

    Tests should pass ``test=True`` or an explicit temporary ``base_dir`` so the
    production database is never shared with test databases.
    """

    program_dir = Path(__file__).resolve().parents[2]
    if base_dir is not None:
        root = Path(base_dir).expanduser().resolve()
    elif test:
        root = Path(tempfile.mkdtemp(prefix="dsa-sqlite-test-"))
    else:
        env_root = os.environ.get("DSA_USER_DATA_DIR")
        if env_root:
            root = Path(env_root).expanduser().resolve()
        elif os.name == "nt":
            root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local")) / APP_DIR_NAME
        else:
            root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    return AppDataDirs(
        program_dir=program_dir,
        user_data_dir=root,
        cache_dir=root / "cache",
        log_dir=root / "logs",
        backup_dir=root / "backups",
        test_data_dir=root / "test-data",
    )


class SQLiteConnectionManager:
    """Centralized sqlite3 connection and migration manager."""

    def __init__(self, database_path: str | os.PathLike[str]):
        self.database_path = Path(database_path)

    def ensure_parent_dir(self) -> None:
        try:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise SQLiteFoundationError(f"Cannot create SQLite data directory: {self.database_path.parent}") from exc

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        self.ensure_parent_dir()
        try:
            conn = sqlite3.connect(self.database_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            yield conn
        except sqlite3.Error as exc:
            raise SQLiteFoundationError(f"SQLite database error at {self.database_path}: {exc}") from exc
        finally:
            try:
                conn.close()  # type: ignore[name-defined]
            except UnboundLocalError:
                pass

    def initialize(self) -> None:
        with self.connect() as conn:
            try:
                conn.execute("BEGIN")
                _ensure_migration_table(conn)
                if not _migration_applied(conn, INITIAL_MIGRATION_ID):
                    _apply_initial_schema(conn)
                    conn.execute(
                        "INSERT INTO data_migrations (id, description) VALUES (?, ?)",
                        (INITIAL_MIGRATION_ID, "Create initial local stock/fund quality persistence schema"),
                    )
                    conn.execute(
                        "INSERT OR REPLACE INTO schema_version (id, version, updated_at) VALUES (1, ?, CURRENT_TIMESTAMP)",
                        (INITIAL_MIGRATION_ID,),
                    )
                conn.commit()
            except Exception:
                conn.rollback()
                raise

    def schema_version(self) -> str | None:
        with self.connect() as conn:
            try:
                row = conn.execute("SELECT version FROM schema_version WHERE id = 1").fetchone()
            except sqlite3.Error as exc:
                raise SQLiteFoundationError("schema_version is unavailable; initialize the database first") from exc
            return None if row is None else str(row["version"])


def _ensure_migration_table(conn: sqlite3.Connection) -> None:
    conn.execute("CREATE TABLE IF NOT EXISTS data_migrations (id TEXT PRIMARY KEY, description TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)")


def _migration_applied(conn: sqlite3.Connection, migration_id: str) -> bool:
    return conn.execute("SELECT 1 FROM data_migrations WHERE id = ?", (migration_id,)).fetchone() is not None


def _apply_initial_schema(conn: sqlite3.Connection) -> None:
    for sql in INITIAL_SCHEMA_SQL:
        conn.execute(sql)


INITIAL_SCHEMA_SQL = [
    "CREATE TABLE IF NOT EXISTS schema_version (id INTEGER PRIMARY KEY CHECK (id = 1), version TEXT NOT NULL, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)",
    "CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, display_name TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'local', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT)",
    "CREATE TABLE IF NOT EXISTS app_state (id TEXT PRIMARY KEY, user_id TEXT, state_key TEXT NOT NULL, state_value TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'local', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS stock_holdings (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT NOT NULL, quantity REAL NOT NULL, average_cost REAL, source TEXT NOT NULL DEFAULT 'manual', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS fund_holdings (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, fund_code TEXT NOT NULL, name TEXT NOT NULL, amount REAL NOT NULL, source TEXT NOT NULL DEFAULT 'manual', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS stock_watchlist (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL, name TEXT, source TEXT NOT NULL DEFAULT 'manual', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS fund_watchlist (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, fund_code TEXT NOT NULL, name TEXT, source TEXT NOT NULL DEFAULT 'manual', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS user_preferences (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, preference_key TEXT NOT NULL, preference_value TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'local', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS stock_analysis_records (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT NOT NULL, summary TEXT, source TEXT NOT NULL DEFAULT 'local_analysis', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS fund_analysis_records (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, fund_code TEXT NOT NULL, summary TEXT, source TEXT NOT NULL DEFAULT 'local_analysis', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS stock_chat_sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, symbol TEXT, title TEXT, source TEXT NOT NULL DEFAULT 'local_chat', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS fund_chat_sessions (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, fund_code TEXT, title TEXT, source TEXT NOT NULL DEFAULT 'local_chat', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE)",
    "CREATE TABLE IF NOT EXISTS backup_records (id TEXT PRIMARY KEY, user_id TEXT, backup_path TEXT NOT NULL, reason TEXT NOT NULL, source TEXT NOT NULL DEFAULT 'local', note TEXT, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP, deleted_at TEXT, FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE SET NULL)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_stock_holdings_user_symbol_active ON stock_holdings(user_id, symbol) WHERE deleted_at IS NULL",
    "CREATE UNIQUE INDEX IF NOT EXISTS ux_fund_holdings_user_code_active ON fund_holdings(user_id, fund_code) WHERE deleted_at IS NULL",
]


class LocalFoundationRepository:
    def __init__(self, manager: SQLiteConnectionManager):
        self.manager = manager

    def create_user(self, display_name: str, *, user_id: str | None = None) -> str:
        uid = user_id or str(uuid.uuid4())
        with self.manager.connect() as conn:
            conn.execute("INSERT INTO users (id, display_name) VALUES (?, ?)", (uid, display_name))
            conn.commit()
        return uid

    def get_user(self, user_id: str) -> dict[str, Any] | None:
        with self.manager.connect() as conn:
            row = conn.execute("SELECT * FROM users WHERE id = ? AND deleted_at IS NULL", (user_id,)).fetchone()
            return None if row is None else dict(row)

    def save_app_state(self, user_id: str, key: str, value: str) -> str:
        sid = str(uuid.uuid4())
        with self.manager.connect() as conn:
            conn.execute("INSERT INTO app_state (id, user_id, state_key, state_value) VALUES (?, ?, ?, ?)", (sid, user_id, key, value))
            conn.commit()
        return sid

    def add_stock_holding(self, user_id: str, symbol: str, name: str, quantity: float, average_cost: float | None = None) -> str:
        hid = str(uuid.uuid4())
        with self.manager.connect() as conn:
            conn.execute("INSERT INTO stock_holdings (id, user_id, symbol, name, quantity, average_cost) VALUES (?, ?, ?, ?, ?, ?)", (hid, user_id, symbol, name, quantity, average_cost))
            conn.commit()
        return hid

    def add_fund_holding(self, user_id: str, fund_code: str, name: str, amount: float) -> str:
        hid = str(uuid.uuid4())
        with self.manager.connect() as conn:
            conn.execute("INSERT INTO fund_holdings (id, user_id, fund_code, name, amount) VALUES (?, ?, ?, ?, ?)", (hid, user_id, fund_code, name, amount))
            conn.commit()
        return hid

    def list_stock_holdings(self, user_id: str) -> list[dict[str, Any]]:
        with self.manager.connect() as conn:
            rows = conn.execute("SELECT * FROM stock_holdings WHERE user_id = ? AND deleted_at IS NULL ORDER BY created_at, id", (user_id,)).fetchall()
            return [dict(row) for row in rows]

    def list_fund_holdings(self, user_id: str) -> list[dict[str, Any]]:
        with self.manager.connect() as conn:
            rows = conn.execute("SELECT * FROM fund_holdings WHERE user_id = ? AND deleted_at IS NULL ORDER BY created_at, id", (user_id,)).fetchall()
            return [dict(row) for row in rows]
