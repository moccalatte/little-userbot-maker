"""Bot storage: database and session management."""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Dict, Optional

try:
    from .db_adapter import DatabaseAdapter, create_database_adapter
    from .utils import mask_phone
except ImportError:
    from db_adapter import DatabaseAdapter, create_database_adapter
    from utils import mask_phone


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
    """Database wrapper untuk PostgreSQL/Neon database pada bot."""

    _instances: Dict[str, "Database"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.logger = logging.getLogger("bot.storage")
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError("DATABASE_URL harus di-set untuk koneksi Neon PostgreSQL")
        self.logger.info("Initializing bot database connection to: %s", self.database_url[:50] + "...")
        self.adapter = create_database_adapter(self.database_url)
        self._init_schema()
        self.logger.info("Bot database initialized successfully")

    @classmethod
    def get_instance(cls, database_url: Optional[str] = None) -> "Database":
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise ValueError("DATABASE_URL harus di-set untuk koneksi Neon PostgreSQL")
        with cls._instances_lock:
            instance = cls._instances.get(url)
            if instance is None:
                instance = cls(url)
                cls._instances[url] = instance
            return instance

    def _init_schema(self) -> None:
        """Initialize basic database schema for bot dengan PostgreSQL."""
        # Create basic tables for bot (simpler than userbot schema)
        statements = [
            """
            CREATE TABLE IF NOT EXISTS users (
                id BIGINT PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                is_active INTEGER DEFAULT 1,
                tipe_paket_subs TEXT DEFAULT 'free',
                tanggal_subs_dimulai TIMESTAMP DEFAULT NULL,
                tanggal_subs_selesai TIMESTAMP DEFAULT NULL,
                status_subscription TEXT DEFAULT 'inactive',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                session_string TEXT NOT NULL,
                encrypted INTEGER DEFAULT 0,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                account_id BIGINT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reply_guard_configs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                keywords_json TEXT NOT NULL,
                target_type TEXT NOT NULL DEFAULT 'allgroup',
                target_groups_json TEXT,
                reply_text TEXT NOT NULL,
                created_via TEXT DEFAULT 'bot_wizard',
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        ]
        
        for stmt in statements:
            self.adapter.execute(stmt)
        self.adapter.commit()
        
        # Migration: Update account_id column to BIGINT if it exists as INTEGER
        try:
            self.adapter.execute("ALTER TABLE sessions ALTER COLUMN account_id TYPE BIGINT")
            self.adapter.commit()
            self.logger.info("Successfully migrated account_id column to BIGINT")
        except Exception as e:
            self.logger.debug("Migration not needed or failed (account_id already BIGINT): %s", e)
            # Rollback any failed transaction
            try:
                self.adapter.rollback()
            except Exception:
                pass

    def _format_query(self, query: str) -> str:
        """Format query untuk PostgreSQL (ubah ? ke %s)."""
        return query.replace("?", "%s")
    
    def ensure_user(self, user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> None:
        """Ensure user exists in database with updated info."""
        self.logger.debug("Ensuring user exists: %s (@%s)", user_id, username or "N/A")
        query = """
            INSERT INTO users (id, username, first_name, last_name)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT(id) DO UPDATE SET
                username=EXCLUDED.username,
                first_name=EXCLUDED.first_name,
                last_name=EXCLUDED.last_name,
                updated_at=CURRENT_TIMESTAMP
        """
        self.adapter.execute(query, (user_id, username, first_name, last_name))
        self.adapter.commit()
        self.logger.info("User %s ensured in database", user_id)

    def save_session(
        self,
        user_id: int,
        session_string: str,
        encrypted: bool,
        metadata: Optional[dict[str, Any]],
        account_id: Optional[int] = None,
    ) -> None:
        """Save session to database with logging."""
        self.logger.info(
            "Saving session for user %s (encrypted: %s, account_id: %s)", 
            user_id, encrypted, account_id
        )
        payload = json.dumps(metadata or {})
        query = self._format_query("""
            INSERT INTO sessions (user_id, session_string, encrypted, metadata, account_id)
            VALUES (?, ?, ?, ?, ?)
        """)
        self.adapter.execute(query, (user_id, session_string, 1 if encrypted else 0, payload, account_id))
        self.adapter.commit()
        self.logger.info("Session saved successfully for user %s", user_id)

    def delete_sessions(self, user_id: int) -> int:
        query = self._format_query("DELETE FROM sessions WHERE user_id=?")
        return self.adapter.execute(query, (user_id,))

    def list_sessions(self, user_id: int) -> list[dict[str, Any]]:
        query = self._format_query(
            "SELECT id, session_string, encrypted, metadata, created_at, account_id FROM sessions WHERE user_id=? ORDER BY id DESC"
        )
        rows = self.adapter.execute(query, (user_id,))
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
    
    def has_active_userbot_session(self, user_id: int) -> bool:
        """Check if user has at least one active userbot session."""
        query = self._format_query(
            "SELECT COUNT(*) as count FROM sessions WHERE user_id = ?"
        )
        rows = self.adapter.execute(query, (user_id,))
        count = rows[0]["count"] if rows and rows[0] else 0
        return count > 0
        
    def get_user_session_info(self, user_id: int) -> dict[str, Any] | None:
        """Get basic session info for userbot owner verification."""
        query = self._format_query(
            "SELECT s.created_at, s.account_id, u.username, u.first_name FROM sessions s "
            "JOIN users u ON s.user_id = u.id WHERE s.user_id = ? "
            "ORDER BY s.created_at DESC LIMIT 1"
        )
        rows = self.adapter.execute(query, (user_id,))
        if not rows:
            return None
        
        row = rows[0]
        return {
            "user_id": user_id,
            "created_at": row.get("created_at"),
            "account_id": row.get("account_id"),
            "username": row.get("username"),
            "first_name": row.get("first_name")
        }


# ============================================================================
# SESSION REPOSITORY
# ============================================================================

ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


class SessionRepository:
    """Kelola penyimpanan session dalam Database (PostgreSQL/Neon only)."""

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.logger = logging.getLogger("bot.session_repo")
        self._lock = Lock()
        self._database = Database.get_instance(database_url)
        if self._database is None:
            raise RuntimeError(
                "Database connection required. Set DATABASE_URL environment variable."
            )
        self.logger.info("SessionRepository initialized with database connection")

    def save(self, record: SessionRecord) -> None:
        """Save session record to database."""
        self.logger.info(
            "Saving session record for user %s (phone: %s, encrypted: %s)", 
            record.owner_id, record.phone_hash, record.encrypted
        )
        self._database.ensure_user(record.owner_id, None, None, None)
        self._database.save_session(
            user_id=record.owner_id,
            session_string=record.session,
            encrypted=record.encrypted,
            metadata={"phone_hash": record.phone_hash, **record.metadata},
            account_id=record.account_id,
        )
        self.logger.info("Session record saved successfully for user %s", record.owner_id)

    def delete_by_owner(self, owner_id: int) -> int:
        """Delete all sessions for a user from database."""
        return self._database.delete_sessions(owner_id)

    def list_by_owner(self, owner_id: int) -> list[SessionRecord]:
        """List all sessions for a user from database."""
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



# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def hash_phone_for_storage(phone: str) -> str:
    return mask_phone(phone)


def get_database_connection():
    """Get direct database connection untuk raw SQL queries."""
    database_instance = Database.get_instance()
    return database_instance.adapter._conn


def _now_utc() -> str:
    """Return current UTC time as ISO formatted string."""
    return datetime.now(timezone.utc).strftime(ISO_FORMAT)
