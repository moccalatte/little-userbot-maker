"""Database helper for multi-user storage."""
from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Singleton SQLite database wrapper."""

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

    # ------------------------------------------------------------------
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
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reply_guard_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                include_json TEXT,
                exclude_json TEXT,
                regex_json TEXT,
                targets_json TEXT,
                reply_text TEXT NOT NULL,
                reply_image TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scheduler_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                message TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                targets_json TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scraper_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                include_json TEXT,
                exclude_json TEXT,
                regex_json TEXT,
                targets_json TEXT,
                output_path TEXT,
                matched_count INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
        ]
        with self._lock:
            cur = self._conn.cursor()
            for stmt in statements:
                cur.execute(stmt)
            self._conn.commit()

    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # Session storage
    # ------------------------------------------------------------------
    def save_session(self, user_id: int, session_string: str, encrypted: bool, metadata: Optional[dict[str, Any]]) -> None:
        payload = json.dumps(metadata or {})
        with self._lock:
            self._conn.execute(
                """
                INSERT INTO sessions (user_id, session_string, encrypted, metadata)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, session_string, 1 if encrypted else 0, payload),
            )
            self._conn.commit()

    def list_sessions(self, user_id: int) -> List[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, session_string, encrypted, metadata, created_at FROM sessions WHERE user_id=? ORDER BY id DESC",
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
            }
            for row in rows
        ]

    def delete_sessions(self, user_id: int) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # Reply guard rules
    # ------------------------------------------------------------------
    def add_reply_guard_rule(
        self,
        user_id: int,
        include: Sequence[str],
        exclude: Sequence[str],
        regex: Sequence[str],
        targets: Optional[Sequence[int]],
        reply_text: str,
        reply_image: Optional[str],
    ) -> int:
        include_json = json.dumps(list(include))
        exclude_json = json.dumps(list(exclude))
        regex_json = json.dumps(list(regex))
        targets_json = json.dumps(list(targets) if targets is not None else None)
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO reply_guard_rules (user_id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (user_id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_reply_guard_rules(self, user_id: int) -> List[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image, created_at FROM reply_guard_rules WHERE user_id=? ORDER BY id",
                (user_id,),
            )
            rows = cur.fetchall()
        results: List[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "include": json.loads(row["include_json"] or "[]"),
                    "exclude": json.loads(row["exclude_json"] or "[]"),
                    "regex": json.loads(row["regex_json"] or "[]"),
                    "targets": json.loads(row["targets_json"]) if row["targets_json"] else None,
                    "reply_text": row["reply_text"],
                    "reply_image": row["reply_image"],
                    "created_at": row["created_at"],
                }
            )
        return results

    def delete_reply_guard_rule(self, user_id: int, rule_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM reply_guard_rules WHERE user_id=? AND id=?",
                (user_id, rule_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_all_reply_guard_rules(self, user_id: int) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM reply_guard_rules WHERE user_id=?", (user_id,))
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # Scheduler jobs
    # ------------------------------------------------------------------
    def add_scheduler_job(
        self,
        user_id: int,
        message: str,
        interval_minutes: int,
        targets: Sequence[int],
    ) -> int:
        targets_json = json.dumps(list(targets))
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO scheduler_jobs (user_id, message, interval_minutes, targets_json)
                VALUES (?, ?, ?, ?)
                """,
                (user_id, message, interval_minutes, targets_json),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_scheduler_jobs(self, user_id: int) -> List[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, message, interval_minutes, targets_json, created_at FROM scheduler_jobs WHERE user_id=? ORDER BY id",
                (user_id,),
            )
            rows = cur.fetchall()
        return [
            {
                "id": row["id"],
                "message": row["message"],
                "interval_minutes": row["interval_minutes"],
                "targets": json.loads(row["targets_json"] or "[]"),
                "created_at": row["created_at"],
            }
            for row in rows
        ]

    def delete_scheduler_job(self, user_id: int, job_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM scheduler_jobs WHERE user_id=? AND id=?",
                (user_id, job_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_all_scheduler_jobs(self, user_id: int) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM scheduler_jobs WHERE user_id=?", (user_id,))
            self._conn.commit()
            return cur.rowcount

    # ------------------------------------------------------------------
    # Scraper sessions
    # ------------------------------------------------------------------
    def add_scraper_session(
        self,
        user_id: int,
        include: Sequence[str],
        exclude: Sequence[str],
        regex: Sequence[str],
        targets: Optional[Sequence[int]],
        output_path: str,
    ) -> int:
        include_json = json.dumps(list(include))
        exclude_json = json.dumps(list(exclude))
        regex_json = json.dumps(list(regex))
        targets_json = json.dumps(list(targets) if targets is not None else None)
        with self._lock:
            cur = self._conn.execute(
                """
                INSERT INTO scraper_sessions (user_id, include_json, exclude_json, regex_json, targets_json, output_path)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (user_id, include_json, exclude_json, regex_json, targets_json, output_path),
            )
            self._conn.commit()
            return int(cur.lastrowid)

    def list_scraper_sessions(self, user_id: int) -> List[dict[str, Any]]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, include_json, exclude_json, regex_json, targets_json, output_path, matched_count, created_at FROM scraper_sessions WHERE user_id=? ORDER BY id",
                (user_id,),
            )
            rows = cur.fetchall()
        results: List[dict[str, Any]] = []
        for row in rows:
            results.append(
                {
                    "id": row["id"],
                    "rules": {
                        "include": json.loads(row["include_json"] or "[]"),
                        "exclude": json.loads(row["exclude_json"] or "[]"),
                        "regex": json.loads(row["regex_json"] or "[]"),
                    },
                    "targets": json.loads(row["targets_json"]) if row["targets_json"] else None,
                    "output_path": row["output_path"],
                    "matched_count": row["matched_count"],
                    "created_at": row["created_at"],
                }
            )
        return results

    def update_scraper_session(self, session_id: int, user_id: int, matched_count: int, output_path: str) -> None:
        with self._lock:
            self._conn.execute(
                """
                UPDATE scraper_sessions
                SET matched_count=?, output_path=?, updated_at=CURRENT_TIMESTAMP
                WHERE id=? AND user_id=?
                """,
                (matched_count, output_path, session_id, user_id),
            )
            self._conn.commit()

    def delete_scraper_session(self, session_id: int, user_id: int) -> bool:
        with self._lock:
            cur = self._conn.execute(
                "DELETE FROM scraper_sessions WHERE id=? AND user_id=?",
                (session_id, user_id),
            )
            self._conn.commit()
            return cur.rowcount > 0

    def delete_all_scraper_sessions(self, user_id: int) -> int:
        with self._lock:
            cur = self._conn.execute("DELETE FROM scraper_sessions WHERE user_id=?", (user_id,))
            self._conn.commit()
            return cur.rowcount
