"""Bot storage: database and session management."""
from __future__ import annotations

import json
import sqlite3
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

from .utils import mask_phone


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass(slots=True)
class SessionRecord:
    phone_hash: str
    session: str
    created_at: str
    encrypted: bool
    owner_id: int
    account_id: Optional[int] = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ============================================================================
# DATABASE
# ============================================================================

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Simple SQLite database for bot sessions."""

    _instances: Dict[Path, "Database"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, db_path: Path) -> None:
        self._path = db_path
        _ensure_parent(db_path)
        self._conn = sqlite3.connect(str(db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        self._init_schema()

    @classmethod
    def get_instance(cls, db_path: Path) -> "Database":
        resolved = db_path.resolve()
        with cls._instances_lock:
            instance = cls._instances.get(resolved)
            if instance is None:
                instance = cls(resolved)
                cls._instances[resolved] = instance
            return instance

    def _init_schema(self) -> None:
        with self._lock:
            self._conn.execute("PRAGMA foreign_keys = ON")
        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                session_string TEXT NOT NULL,
                encrypted INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                account_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        ]
        with self._lock:
            cur = self._conn.cursor()
            for stmt in statements:
                cur.execute(stmt)
            self._conn.commit()

    def ensure_user(self, user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> None:
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO users (id, username, first_name, last_name)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    updated_at=CURRENT_TIMESTAMP
                """,
                (user_id, username, first_name, last_name),
            )
            self._conn.commit()

    def save_session(
        self,
        user_id: int,
        session_string: str,
        encrypted: bool,
        metadata: Optional[dict[str, Any]],
        account_id: Optional[int] = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sessions (user_id, session_string, encrypted, metadata, account_id)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, session_string, 1 if encrypted else 0, payload, account_id),
            )
            self._conn.commit()

    def delete_sessions(self, user_id: int) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            self._conn.commit()
            return cur.rowcount

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, session_string, encrypted, metadata, created_at, account_id FROM sessions WHERE user_id=? ORDER BY id DESC",
                (user_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "session_string": row["session_string"],
                "encrypted": bool(row["encrypted"]),
                "metadata": json.loads(row["metadata"] or "{}"),
                "created_at": row["created_at"],
                "account_id": row["account_id"],
            }
            for row in rows
        ]


# ============================================================================
# SESSION REPOSITORY
# ============================================================================

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class SessionRepository:
    """Kelola penyimpanan session dalam JSON atau Database."""

    def __init__(self, data_path: Path, database_path: Optional[Path] = None) -> None:
        self._path = data_path
        self._lock = Lock()
        self._database = Database.get_instance(database_path) if database_path else None
        if self._database is None:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            if not self._path.exists():
                self._write([])

    def save(self, record: SessionRecord) -> None:
        if self._database is not None:
            self._database.ensure_user(record.owner_id, None, None, None)
            self._database.save_session(
                user_id=record.owner_id,
                session_string=record.session,
                encrypted=record.encrypted,
                metadata={"phone_hash": record.phone_hash, **record.metadata},
                account_id=record.account_id,
            )
            return
        with self._lock:
            records = self._read()
            records.append(asdict(record))
            if len(records) > 100:
                records = records[-100:]
            self._write(records)

    def delete_by_owner(self, owner_id: int) -> int:
        if self._database is not None:
            return self._database.delete_sessions(owner_id)
        with self._lock:
            records = self._read()
            filtered = [r for r in records if r.get("owner_id") != owner_id]
            removed = len(records) - len(filtered)
            self._write(filtered)
            return removed

    def list_by_owner(self, owner_id: int) -> list[SessionRecord]:
        if self._database is not None:
            rows = self._database.list_sessions(owner_id)
            result: list[SessionRecord] = []
            for row in rows:
                metadata = row.get("metadata", {}) or {}
                phone_hash = metadata.get("phone_hash", "")
                account_id = row.get("account_id")
                if account_id is not None:
                    metadata.setdefault("account_id", account_id)
                result.append(
                    SessionRecord(
                        phone_hash=phone_hash,
                        session=row["session_string"],
                        created_at=row.get("created_at") or _now_utc(),
                        encrypted=row.get("encrypted", False),
                        owner_id=owner_id,
                        account_id=account_id,
                        metadata=metadata,
                    )
                )
            return result
        with self._lock:
            records = self._read()
        result: list[SessionRecord] = []
        for r in records:
            if r.get("owner_id") != owner_id:
                continue
            if "account_id" not in r:
                r = dict(r)
                r["account_id"] = None
            result.append(SessionRecord(**r))
        return result

    def _read(self) -> list[dict[str, Any]]:
        with self._path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return []

    def _write(self, data: list[dict[str, Any]]) -> None:
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_phone_for_storage(phone: str) -> str:
    return mask_phone(phone)


def _now_utc() -> str:
    return datetime.utcnow().strftime(ISO_FORMAT)