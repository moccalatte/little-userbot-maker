"""Database adapter khusus untuk PostgreSQL/Neon."""
from __future__ import annotations

import json
import logging
import os
import threading
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse

logger = logging.getLogger("userbot.db_adapter")

# Import PostgreSQL dependencies (required)
try:
    import psycopg2
    import psycopg2.extras
except ImportError:
    raise ImportError(
        "PostgreSQL dependencies tidak tersedia. "
        "Install dengan: pip install psycopg2-binary"
    )


class DatabaseAdapter:
    """Database adapter khusus untuk PostgreSQL/Neon."""
    
    def __init__(self, database_url: str):
        if not database_url.startswith(('postgresql://', 'postgres://')):
            raise ValueError(
                f"Hanya PostgreSQL URLs yang didukung. Got: {database_url[:30]}..."
            )
            
        self.database_url = database_url
        self.db_type = "postgresql"
        self._conn = None
        self._lock = threading.Lock()
        
        logger.info(f"Database adapter initialized: {self.db_type}")
        self._connect()
            
    def _connect(self):
        """Connect ke PostgreSQL database."""
        self._conn = psycopg2.connect(
            self.database_url,
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        self._conn.autocommit = True
        logger.info("Connected to PostgreSQL database")
            
    def execute(self, query: str, params: Optional[tuple] = None) -> Any:
        """Execute query dengan parameter."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(query, params or ())
            try:
                return cursor.fetchall()
            except psycopg2.ProgrammingError:
                # Query tidak return results (INSERT, UPDATE, DELETE)
                return cursor.rowcount
                    
    def execute_one(self, query: str, params: Optional[tuple] = None) -> Optional[Any]:
        """Execute query dan return satu result."""
        with self._lock:
            cursor = self._conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
                
    def execute_insert(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT dan return last inserted ID."""
        with self._lock:
            # PostgreSQL menggunakan RETURNING untuk get ID
            if "RETURNING" not in query.upper():
                query += " RETURNING id"
            cursor = self._conn.cursor()
            cursor.execute(query, params or ())
            result = cursor.fetchone()
            return result['id'] if result else 0
                
    def commit(self):
        """Commit transaction."""
        # PostgreSQL autocommit sudah enabled, tidak perlu manual commit
        pass
        
    def close(self):
        """Close database connection."""
        if self._conn:
            self._conn.close()
            
    def get_schema_queries(self) -> List[str]:
        """Get PostgreSQL schema queries untuk Neon database."""
        return [
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
                account_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS reply_guard_rules (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                include_json TEXT,
                exclude_json TEXT,
                regex_json TEXT,
                targets_json TEXT,
                reply_text TEXT NOT NULL,
                reply_image TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS scheduler_jobs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                message TEXT NOT NULL,
                interval_minutes INTEGER NOT NULL,
                targets_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS userbot_configs (
                id SERIAL PRIMARY KEY,
                user_id BIGINT NOT NULL,
                feature_type TEXT NOT NULL,
                enabled INTEGER DEFAULT 1,
                config_json TEXT NOT NULL,
                version INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admin_users (
                id SERIAL PRIMARY KEY,
                user_id BIGINT UNIQUE NOT NULL,
                role TEXT DEFAULT 'admin',
                permissions_json TEXT DEFAULT '{}',
                created_by BIGINT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS admin_logs (
                id SERIAL PRIMARY KEY,
                admin_user_id BIGINT NOT NULL,
                action TEXT NOT NULL,
                target_user_id BIGINT,
                details_json TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(admin_user_id) REFERENCES users(id),
                FOREIGN KEY(target_user_id) REFERENCES users(id)
            )
            """
        ]


def create_database_adapter(database_url: Optional[str] = None) -> DatabaseAdapter:
    """Factory function untuk create Neon PostgreSQL database adapter."""
    if not database_url:
        database_url = os.getenv("DATABASE_URL")
        
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable harus di-set untuk koneksi Neon PostgreSQL. "
            "Format: postgresql://username:password@host/database?sslmode=require"
        )
        
    return DatabaseAdapter(database_url)


def is_neon_url(url: str) -> bool:
    """Check apakah URL adalah Neon database URL."""
    try:
        parsed = urlparse(url)
        return (parsed.scheme in ('postgresql', 'postgres') and 
                'neon.tech' in (parsed.hostname or ''))
    except:
        return False