"""Database helper untuk multi-user storage dengan support PostgreSQL/Neon dan SQLite."""
from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

try:
    from .db_adapter import DatabaseAdapter, create_database_adapter
except ImportError:
    try:
        from db_adapter import DatabaseAdapter, create_database_adapter
    except ImportError:
        import sys
        import os
        sys.path.append(os.path.dirname(__file__))
        from db_adapter import DatabaseAdapter, create_database_adapter


class Database:
    """Database wrapper dengan support PostgreSQL (Neon) dan SQLite."""

    _instances: Dict[str, "Database"] = {}
    _instances_lock = threading.Lock()

    def __init__(self, database_url: Optional[str] = None) -> None:
        self.database_url = database_url or os.getenv("DATABASE_URL")
        if not self.database_url:
            raise ValueError(
                "DATABASE_URL environment variable harus di-set untuk koneksi Neon PostgreSQL. "
                "Format: postgresql://username:password@host/database?sslmode=require"
            )
        self.adapter = create_database_adapter(self.database_url)
        self._init_schema()

    @classmethod
    def get_instance(cls, database_url: Optional[str] = None) -> "Database":
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise ValueError(
                "DATABASE_URL environment variable harus di-set untuk koneksi Neon PostgreSQL. "
                "Format: postgresql://username:password@host/database?sslmode=require"
            )
        with cls._instances_lock:
            instance = cls._instances.get(url)
            if instance is None:
                instance = cls(url)
                cls._instances[url] = instance
            return instance

    def _get_placeholder(self) -> str:
        """Get parameter placeholder berdasarkan database type."""
        return "%s" if self.adapter.db_type == "postgresql" else "?"

    def _format_query(self, query: str) -> str:
        """Format query untuk PostgreSQL (ubah ? ke %s)."""
        return query.replace("?", "%s")

    # ------------------------------------------------------------------
    def _init_schema(self) -> None:
        """Initialize database schema using PostgreSQL adapter."""
        # Create tables using PostgreSQL schema
        for query in self.adapter.get_schema_queries():
            self.adapter.execute(query)
            
        # Add account_id column if not exists (migration support)
        try:
            self.adapter.execute("ALTER TABLE sessions ADD COLUMN account_id INTEGER")
        except Exception:
            # Column already exists or other error, ignore
            pass
            
        self.adapter.commit()

    # ------------------------------------------------------------------
    def ensure_user(self, user_id: int, username: str | None, first_name: str | None, last_name: str | None) -> None:
        """Ensure user exists in database with updated info."""
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
        
    def update_user_subscription(
        self, 
        user_id: int, 
        tipe_paket: str, 
        tanggal_mulai: str, 
        tanggal_selesai: str, 
        status: str = 'active'
    ) -> bool:
        """Update user subscription info."""
        query = """
            UPDATE users 
            SET tipe_paket_subs = %s, 
                tanggal_subs_dimulai = %s, 
                tanggal_subs_selesai = %s,
                status_subscription = %s,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
        """
        rows_affected = self.adapter.execute(query, (tipe_paket, tanggal_mulai, tanggal_selesai, status, user_id))
        self.adapter.commit()
        return rows_affected > 0
        
    def get_user_subscription(self, user_id: int) -> Optional[dict[str, Any]]:
        """Get user subscription info."""
        query = """
            SELECT id, username, first_name, last_name, tipe_paket_subs, 
                   tanggal_subs_dimulai, tanggal_subs_selesai, status_subscription,
                   created_at, updated_at
            FROM users WHERE id = %s
        """
        row = self.adapter.execute_one(query, (user_id,))
        if not row:
            return None
            
        return {
            "user_id": row["id"],
            "username": row["username"],
            "first_name": row["first_name"],
            "last_name": row["last_name"],
            "tipe_paket_subs": row["tipe_paket_subs"],
            "tanggal_subs_dimulai": row["tanggal_subs_dimulai"],
            "tanggal_subs_selesai": row["tanggal_subs_selesai"],
            "status_subscription": row["status_subscription"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }
        
    def is_subscription_active(self, user_id: int) -> bool:
        """Check if user has active subscription."""
        query = """
            SELECT status_subscription, tanggal_subs_selesai 
            FROM users 
            WHERE id = %s
        """
        row = self.adapter.execute_one(query, (user_id,))
        if not row:
            return False
            
        # Check if subscription is active and not expired
        if row["status_subscription"] != 'active':
            return False
            
        # Check expiry date
        if row["tanggal_subs_selesai"]:
            from datetime import datetime
            try:
                expiry_date = row["tanggal_subs_selesai"]
                if isinstance(expiry_date, str):
                    expiry_date = datetime.fromisoformat(expiry_date.replace('Z', '+00:00'))
                return datetime.now() < expiry_date
            except:
                return False
        
        return True
        
    def get_active_userbot_sessions(self) -> List[dict[str, Any]]:
        """Get all sessions untuk users dengan active subscription."""
        query = """
            SELECT s.id, s.user_id, s.session_string, s.encrypted, s.metadata, s.account_id,
                   u.username, u.first_name, u.tipe_paket_subs, u.status_subscription
            FROM sessions s
            JOIN users u ON s.user_id = u.id
            WHERE u.status_subscription = 'active' 
            AND (u.tanggal_subs_selesai IS NULL OR u.tanggal_subs_selesai > NOW())
            ORDER BY s.created_at DESC
        """
        rows = self.adapter.execute(query)
        
        return [
            {
                "session_id": row["id"],
                "user_id": row["user_id"],
                "session_string": row["session_string"],
                "encrypted": bool(row["encrypted"]),
                "metadata": json.loads(row["metadata"] or "{}"),
                "account_id": row["account_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "tipe_paket_subs": row["tipe_paket_subs"],
                "status_subscription": row["status_subscription"],
            }
            for row in rows
        ]

    # ------------------------------------------------------------------
    # Session storage
    # ------------------------------------------------------------------
    def save_session(
        self,
        user_id: int,
        session_string: str,
        encrypted: bool,
        metadata: Optional[dict[str, Any]],
        account_id: Optional[int] = None,
    ) -> None:
        payload = json.dumps(metadata or {})
        query = self._format_query("""
            INSERT INTO sessions (user_id, session_string, encrypted, metadata, account_id)
            VALUES (?, ?, ?, ?, ?)
        """)
        self.adapter.execute(query, (user_id, session_string, 1 if encrypted else 0, payload, account_id))
        self.adapter.commit()

    def list_sessions(self, user_id: int) -> List[dict[str, Any]]:
        query = self._format_query("""
            SELECT id, session_string, encrypted, metadata, created_at, account_id 
            FROM sessions WHERE user_id=? ORDER BY id DESC
        """)
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

    def delete_sessions(self, user_id: int) -> int:
        query = self._format_query("DELETE FROM sessions WHERE user_id=?")
        return self.adapter.execute(query, (user_id,))

    def get_latest_session(self, user_id: int) -> Optional[dict[str, Any]]:
        query = self._format_query("""
            SELECT id, session_string, encrypted, metadata, account_id 
            FROM sessions WHERE user_id=? ORDER BY id DESC LIMIT 1
        """)
        row = self.adapter.execute_one(query, (user_id,))
        if row is None:
            return None
        return {
            "id": row["id"],
            "session_string": row["session_string"],
            "encrypted": bool(row["encrypted"]),
            "metadata": json.loads(row["metadata"] or "{}"),
            "account_id": row["account_id"],
        }

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
        query = self._format_query("""
            INSERT INTO reply_guard_rules (user_id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """)
        return self.adapter.execute_insert(query, (user_id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image))

    def list_reply_guard_rules(self, user_id: int) -> List[dict[str, Any]]:
        query = self._format_query("""
            SELECT id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image, created_at 
            FROM reply_guard_rules WHERE user_id=? ORDER BY id
        """)
        rows = self.adapter.execute(query, (user_id,))
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
        query = self._format_query("DELETE FROM reply_guard_rules WHERE user_id=? AND id=?")
        return self.adapter.execute(query, (user_id, rule_id)) > 0

    def delete_all_reply_guard_rules(self, user_id: int) -> int:
        query = self._format_query("DELETE FROM reply_guard_rules WHERE user_id=?")
        return self.adapter.execute(query, (user_id,))

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
        query = self._format_query("""
            INSERT INTO scheduler_jobs (user_id, message, interval_minutes, targets_json)
            VALUES (?, ?, ?, ?)
        """)
        return self.adapter.execute_insert(query, (user_id, message, interval_minutes, targets_json))

    def list_scheduler_jobs(self, user_id: int) -> List[dict[str, Any]]:
        query = self._format_query("""
            SELECT id, message, interval_minutes, targets_json, created_at 
            FROM scheduler_jobs WHERE user_id=? ORDER BY id
        """)
        rows = self.adapter.execute(query, (user_id,))
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
        query = self._format_query("DELETE FROM scheduler_jobs WHERE user_id=? AND id=?")
        return self.adapter.execute(query, (user_id, job_id)) > 0

    def delete_all_scheduler_jobs(self, user_id: int) -> int:
        query = self._format_query("DELETE FROM scheduler_jobs WHERE user_id=?")
        return self.adapter.execute(query, (user_id,))

    # ------------------------------------------------------------------
    # Userbot configs (from Bot Wizard)
    # ------------------------------------------------------------------
    def save_userbot_config(
        self,
        user_id: int,
        feature_type: str,
        config: dict[str, Any],
        enabled: bool = True,
    ) -> int:
        """Save/update userbot config from Bot Wizard."""
        config_json = json.dumps(config)
        
        # Check if config already exists
        existing_query = self._format_query("SELECT id, version FROM userbot_configs WHERE user_id=? AND feature_type=?")
        existing = self.adapter.execute_one(existing_query, (user_id, feature_type))
        
        if existing:
            # Update existing config with version bump
            new_version = existing["version"] + 1
            update_query = self._format_query("""
                UPDATE userbot_configs 
                SET config_json=?, enabled=?, version=?, updated_at=CURRENT_TIMESTAMP 
                WHERE user_id=? AND feature_type=?
            """)
            self.adapter.execute(update_query, (config_json, 1 if enabled else 0, new_version, user_id, feature_type))
            config_id = existing["id"]
        else:
            # Insert new config
            insert_query = self._format_query("""
                INSERT INTO userbot_configs (user_id, feature_type, config_json, enabled)
                VALUES (?, ?, ?, ?)
            """)
            config_id = self.adapter.execute_insert(insert_query, (user_id, feature_type, config_json, 1 if enabled else 0))
        
        self.adapter.commit()
        return config_id

    def get_userbot_configs(self, user_id: int, feature_type: Optional[str] = None) -> List[dict[str, Any]]:
        """Get userbot configs for a user."""
        if feature_type:
            query = self._format_query("""
                SELECT id, feature_type, config_json, enabled, version, updated_at 
                FROM userbot_configs WHERE user_id=? AND feature_type=?
            """)
            rows = self.adapter.execute(query, (user_id, feature_type))
        else:
            query = self._format_query("""
                SELECT id, feature_type, config_json, enabled, version, updated_at 
                FROM userbot_configs WHERE user_id=?
            """)
            rows = self.adapter.execute(query, (user_id,))
        
        return [
            {
                "id": row["id"],
                "feature_type": row["feature_type"],
                "config": json.loads(row["config_json"]),
                "enabled": bool(row["enabled"]),
                "version": row["version"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]

    def delete_userbot_config(self, user_id: int, feature_type: str) -> bool:
        """Delete userbot config."""
        query = self._format_query("DELETE FROM userbot_configs WHERE user_id=? AND feature_type=?")
        return self.adapter.execute(query, (user_id, feature_type)) > 0

    def is_userbot_active(self, user_id: int) -> bool:
        """Check if user has active userbot (has any session)."""
        query = self._format_query("SELECT COUNT(*) as count FROM sessions WHERE user_id=?")
        result = self.adapter.execute_one(query, (user_id,))
        return result["count"] > 0 if result else False

    # ------------------------------------------------------------------
    # Admin functions
    # ------------------------------------------------------------------
    def add_admin_user(self, user_id: int, created_by: Optional[int] = None, role: str = "admin") -> bool:
        """Add user sebagai admin."""
        try:
            query = self._format_query("INSERT INTO admin_users (user_id, role, created_by) VALUES (?, ?, ?)")
            self.adapter.execute(query, (user_id, role, created_by))
            self.adapter.commit()
            return True
        except Exception:  # User already admin or other error
            return False
            
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin."""
        query = self._format_query("SELECT COUNT(*) as count FROM admin_users WHERE user_id=?")
        result = self.adapter.execute_one(query, (user_id,))
        return result["count"] > 0 if result else False
            
    def remove_admin_user(self, user_id: int) -> bool:
        """Remove admin access."""
        query = self._format_query("DELETE FROM admin_users WHERE user_id=?")
        return self.adapter.execute(query, (user_id,)) > 0
            
    def list_admin_users(self) -> List[dict[str, Any]]:
        """List all admin users."""
        query = """
            SELECT a.user_id, a.role, a.created_at, 
                   u.username, u.first_name, u.last_name
            FROM admin_users a 
            JOIN users u ON a.user_id = u.id 
            ORDER BY a.created_at DESC
        """
        rows = self.adapter.execute(query)
        
        return [
            {
                "user_id": row["user_id"],
                "role": row["role"],
                "created_at": row["created_at"],
                "username": row["username"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
            }
            for row in rows
        ]
        
    def log_admin_action(
        self, 
        admin_user_id: int, 
        action: str, 
        target_user_id: Optional[int] = None, 
        details: Optional[dict] = None
    ) -> None:
        """Log admin action."""
        details_json = json.dumps(details or {})
        query = self._format_query("INSERT INTO admin_logs (admin_user_id, action, target_user_id, details_json) VALUES (?, ?, ?, ?)")
        self.adapter.execute(query, (admin_user_id, action, target_user_id, details_json))
        self.adapter.commit()
            
    def get_admin_logs(self, limit: int = 100) -> List[dict[str, Any]]:
        """Get recent admin logs."""
        query = self._format_query("""
            SELECT l.*, u1.username as admin_username, u2.username as target_username
            FROM admin_logs l
            LEFT JOIN users u1 ON l.admin_user_id = u1.id
            LEFT JOIN users u2 ON l.target_user_id = u2.id
            ORDER BY l.timestamp DESC LIMIT ?
        """)
        rows = self.adapter.execute(query, (limit,))
        
        return [
            {
                "id": row["id"],
                "admin_user_id": row["admin_user_id"],
                "admin_username": row["admin_username"],
                "action": row["action"],
                "target_user_id": row["target_user_id"],
                "target_username": row["target_username"],
                "details": json.loads(row["details_json"] or "{}"),
                "timestamp": row["timestamp"],
            }
            for row in rows
        ]
        
    # ------------------------------------------------------------------
    # Admin monitoring functions
    # ------------------------------------------------------------------
    def get_system_stats(self) -> dict[str, Any]:
        """Get overall system statistics."""
        # Total users
        result = self.adapter.execute_one("SELECT COUNT(*) as count FROM users")
        total_users = result["count"] if result else 0
        
        # Active userbots (users with sessions)
        result = self.adapter.execute_one("SELECT COUNT(DISTINCT user_id) as count FROM sessions")
        active_userbots = result["count"] if result else 0
        
        # Total configs
        result = self.adapter.execute_one("SELECT COUNT(*) as count FROM userbot_configs")
        total_configs = result["count"] if result else 0
        
        # Active configs (enabled)
        result = self.adapter.execute_one("SELECT COUNT(*) as count FROM userbot_configs WHERE enabled=1")
        active_configs = result["count"] if result else 0
        
        # Configs by type
        rows = self.adapter.execute("""
            SELECT feature_type, COUNT(*) as count, 
                   SUM(enabled) as enabled_count
            FROM userbot_configs 
            GROUP BY feature_type
        """)
        config_stats = {}
        for row in rows:
            config_stats[row["feature_type"]] = {
                "total": row["count"],
                "enabled": row["enabled_count"]
            }
            
        # Recent activity (last 24h)
        recent_query = "SELECT COUNT(*) as count FROM userbot_configs WHERE updated_at > NOW() - INTERVAL '1 day'"
        result = self.adapter.execute_one(recent_query)
        recent_activity = result["count"] if result else 0
        
        return {
            "total_users": total_users,
            "active_userbots": active_userbots,
            "total_configs": total_configs,
            "active_configs": active_configs,
            "config_stats": config_stats,
            "recent_activity_24h": recent_activity,
            "timestamp": "CURRENT_TIMESTAMP"
        }
        
    def get_user_details(self, user_id: int) -> Optional[dict[str, Any]]:
        """Get detailed info about specific user."""
        # Basic user info
        query = self._format_query("SELECT * FROM users WHERE id=?")
        user = self.adapter.execute_one(query, (user_id,))
        if not user:
            return None
            
        # Sessions
        query = self._format_query("SELECT COUNT(*) as count, MAX(created_at) as latest FROM sessions WHERE user_id=?")
        session_info = self.adapter.execute_one(query, (user_id,))
        
        # Configs
        configs = self.get_userbot_configs(user_id)
        
        # Recent activity
        query = self._format_query("""
            SELECT action, timestamp FROM admin_logs 
            WHERE target_user_id=? OR admin_user_id=?
            ORDER BY timestamp DESC LIMIT 5
        """)
        recent_actions = self.adapter.execute(query, (user_id, user_id))
        
        return {
            "user_id": user["id"],
            "username": user["username"],
            "first_name": user["first_name"],
            "last_name": user["last_name"],
            "is_active": bool(user["is_active"]),
            "created_at": user["created_at"],
            "sessions": {
                "count": session_info["count"] if session_info else 0,
                "latest": session_info["latest"] if session_info else None
            },
            "configs": configs,
            "recent_actions": [dict(row) for row in recent_actions],
            "is_admin": self.is_admin(user_id)
        }
        
    def search_users(self, query: str, limit: int = 50) -> List[dict[str, Any]]:
        """Search users by username/name."""
        search_pattern = f"%{query}%"
        search_query = self._format_query("""
            SELECT u.*, 
                   (SELECT COUNT(*) FROM sessions s WHERE s.user_id = u.id) as session_count,
                   (SELECT COUNT(*) FROM userbot_configs c WHERE c.user_id = u.id AND c.enabled = 1) as active_configs
            FROM users u 
            WHERE u.username LIKE ? OR u.first_name LIKE ? OR u.last_name LIKE ?
            ORDER BY u.updated_at DESC LIMIT ?
        """)
        rows = self.adapter.execute(search_query, (search_pattern, search_pattern, search_pattern, limit))
        
        return [
            {
                "user_id": row["id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "last_name": row["last_name"],
                "session_count": row["session_count"],
                "active_configs": row["active_configs"],
                "is_admin": self.is_admin(row["id"])
            }
            for row in rows
        ]
        
    def get_all_userbot_configs(self, limit: int = 100) -> List[dict[str, Any]]:
        """Get all userbot configs (admin view)."""
        query = self._format_query("""
            SELECT c.*, u.username, u.first_name 
            FROM userbot_configs c
            JOIN users u ON c.user_id = u.id
            ORDER BY c.updated_at DESC LIMIT ?
        """)
        rows = self.adapter.execute(query, (limit,))
        
        return [
            {
                "id": row["id"],
                "user_id": row["user_id"],
                "username": row["username"],
                "first_name": row["first_name"],
                "feature_type": row["feature_type"],
                "enabled": bool(row["enabled"]),
                "config": json.loads(row["config_json"]),
                "version": row["version"],
                "updated_at": row["updated_at"],
            }
            for row in rows
        ]