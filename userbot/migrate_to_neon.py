#!/usr/bin/env python3
"""Migration script dari SQLite ke PostgreSQL/Neon untuk UserbotMaker."""

import json
import os
import sqlite3
import sys
from pathlib import Path
from typing import Optional

# Add userbot to path untuk import database
sys.path.append(str(Path(__file__).parent / "userbot"))

try:
    from database import Database
    from dotenv import load_dotenv
    
    # Try import psycopg2 to check if PostgreSQL support available
    import psycopg2
    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False
    print("❌ Error: psycopg2 tidak tersedia.")
    print("Install dengan: pip install psycopg2-binary")
    sys.exit(1)

# Load environment variables
load_dotenv(Path(__file__).parent / "bot" / ".env")
load_dotenv(Path(__file__).parent / "userbot" / ".env")


def get_sqlite_connection(db_path: str) -> sqlite3.Connection:
    """Get SQLite database connection."""
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"SQLite database tidak ditemukan: {db_path}")
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def migrate_table_data(sqlite_conn: sqlite3.Connection, neon_db: Database, table_name: str) -> int:
    """Migrate data dari table SQLite ke Neon."""
    cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
    rows = cursor.fetchall()
    
    if not rows:
        print(f"  📭 {table_name}: No data to migrate")
        return 0
    
    migrated = 0
    
    for row in rows:
        try:
            if table_name == "users":
                neon_db.ensure_user(
                    user_id=row["id"],
                    username=row["username"], 
                    first_name=row["first_name"],
                    last_name=row["last_name"]
                )
                migrated += 1
                
            elif table_name == "sessions":
                neon_db.save_session(
                    user_id=row["user_id"],
                    session_string=row["session_string"],
                    encrypted=bool(row["encrypted"]),
                    metadata=json.loads(row["metadata"] or "{}") if row["metadata"] else {},
                    account_id=row.get("account_id")
                )
                migrated += 1
                
            elif table_name == "userbot_configs":
                neon_db.save_userbot_config(
                    user_id=row["user_id"],
                    feature_type=row["feature_type"],
                    config=json.loads(row["config_json"]),
                    enabled=bool(row["enabled"])
                )
                migrated += 1
                
            elif table_name == "reply_guard_rules":
                rule_id = neon_db.add_reply_guard_rule(
                    user_id=row["user_id"],
                    include=json.loads(row["include_json"] or "[]"),
                    exclude=json.loads(row["exclude_json"] or "[]"),
                    regex=json.loads(row["regex_json"] or "[]"),
                    targets=json.loads(row["targets_json"]) if row["targets_json"] else None,
                    reply_text=row["reply_text"],
                    reply_image=row["reply_image"]
                )
                migrated += 1
                
            elif table_name == "scheduler_jobs":
                job_id = neon_db.add_scheduler_job(
                    user_id=row["user_id"],
                    message=row["message"],
                    interval_minutes=row["interval_minutes"],
                    targets=json.loads(row["targets_json"] or "[]")
                )
                migrated += 1
                
            elif table_name == "admin_users":
                neon_db.add_admin_user(
                    user_id=row["user_id"],
                    role=row["role"],
                    created_by=row.get("created_by")
                )
                migrated += 1
                
            elif table_name == "admin_logs":
                neon_db.log_admin_action(
                    admin_user_id=row["admin_user_id"],
                    action=row["action"],
                    target_user_id=row.get("target_user_id"),
                    details=json.loads(row["details_json"] or "{}")
                )
                migrated += 1
                
        except Exception as e:
            print(f"    ⚠️  Error migrating row {row.get('id', 'unknown')}: {e}")
            continue
    
    print(f"  ✅ {table_name}: {migrated}/{len(rows)} rows migrated")
    return migrated


def get_table_names(sqlite_conn: sqlite3.Connection) -> list[str]:
    """Get list of table names from SQLite database."""
    cursor = sqlite_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
    )
    return [row[0] for row in cursor.fetchall()]


def migrate_database(sqlite_path: str, neon_url: Optional[str] = None) -> None:
    """Migrate entire database dari SQLite ke Neon."""
    # Validate inputs
    if not neon_url:
        neon_url = os.getenv("DATABASE_URL")
        
    if not neon_url:
        print("❌ Error: DATABASE_URL tidak ditemukan")
        print("Set DATABASE_URL di environment atau pass sebagai parameter")
        return
        
    if not neon_url.startswith(('postgresql://', 'postgres://')):
        print("❌ Error: DATABASE_URL bukan PostgreSQL URL")
        print(f"URL: {neon_url}")
        return
    
    print(f"🔄 Starting migration from SQLite to PostgreSQL...")
    print(f"  📁 Source: {sqlite_path}")
    print(f"  🎯 Target: {neon_url[:30]}...")
    print()
    
    # Connect to databases
    try:
        sqlite_conn = get_sqlite_connection(sqlite_path)
        print("✅ Connected to SQLite database")
    except Exception as e:
        print(f"❌ Error connecting to SQLite: {e}")
        return
        
    try:
        neon_db = Database(neon_url)
        print(f"✅ Connected to PostgreSQL database ({neon_db.adapter.db_type})")
    except Exception as e:
        print(f"❌ Error connecting to PostgreSQL: {e}")
        return
    
    # Get tables to migrate
    tables = get_table_names(sqlite_conn)
    if not tables:
        print("📭 No tables found in SQLite database")
        return
        
    print(f"📋 Found {len(tables)} tables: {', '.join(tables)}")
    print()
    
    # Migrate each table
    total_migrated = 0
    migration_order = [
        "users",           # Users first (referenced by other tables)
        "sessions", 
        "userbot_configs",
        "reply_guard_rules",
        "scheduler_jobs", 
        "admin_users",
        "admin_logs"       # Logs last
    ]
    
    # Migrate tables in order
    for table_name in migration_order:
        if table_name in tables:
            try:
                migrated = migrate_table_data(sqlite_conn, neon_db, table_name)
                total_migrated += migrated
            except Exception as e:
                print(f"  ❌ {table_name}: Error - {e}")
    
    # Migrate any remaining tables not in our order
    remaining_tables = [t for t in tables if t not in migration_order]
    if remaining_tables:
        print(f"\n📋 Migrating remaining tables: {', '.join(remaining_tables)}")
        for table_name in remaining_tables:
            try:
                # Generic migration for unknown tables
                cursor = sqlite_conn.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                print(f"  ⚠️  {table_name}: {len(rows)} rows (manual migration needed)")
            except Exception as e:
                print(f"  ❌ {table_name}: Error - {e}")
    
    # Close connections
    sqlite_conn.close()
    neon_db.adapter.close()
    
    print()
    print(f"🎉 Migration completed!")
    print(f"   📊 Total rows migrated: {total_migrated}")
    print()
    print("🔧 Next steps:")
    print("1. Update your .env files to use the new DATABASE_URL")
    print("2. Test your bot and userbot with the new database")
    print("3. Backup your SQLite file as safety net")
    print("4. Monitor the Neon dashboard for usage")


def main():
    """Main migration function."""
    print("🚀 UserbotMaker Database Migration Tool")
    print("=====================================")
    print()
    
    # Check PostgreSQL support
    if not HAS_POSTGRESQL:
        return
    
    # Get SQLite database path
    default_sqlite = "./data/userbotmaker.db"
    if len(sys.argv) > 1:
        sqlite_path = sys.argv[1]
    else:
        sqlite_path = input(f"SQLite database path [{default_sqlite}]: ").strip()
        if not sqlite_path:
            sqlite_path = default_sqlite
    
    # Get Neon URL
    neon_url = os.getenv("DATABASE_URL")
    if len(sys.argv) > 2:
        neon_url = sys.argv[2]
    elif not neon_url or not neon_url.startswith(('postgresql://', 'postgres://')):
        print()
        print("Enter your Neon PostgreSQL connection string:")
        print("Format: postgresql://username:password@host/database?sslmode=require")
        neon_url = input("DATABASE_URL: ").strip()
        
    if not neon_url:
        print("❌ No DATABASE_URL provided")
        return
    
    # Confirm migration
    print()
    print("⚠️  Migration will:")
    print(f"   • Read data from: {sqlite_path}")  
    print(f"   • Write data to:  {neon_url[:50]}...")
    print("   • Create tables if they don't exist")
    print("   • Add data without removing existing data")
    print()
    
    confirm = input("Continue? [y/N]: ").strip().lower()
    if confirm != 'y':
        print("Migration cancelled")
        return
    
    # Run migration
    print()
    migrate_database(sqlite_path, neon_url)


if __name__ == "__main__":
    main()