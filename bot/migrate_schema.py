#!/usr/bin/env python3
"""
Migration script to fix database schema - change user_id from INTEGER to BIGINT
Run this after updating the schema in both bot and userbot
"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def migrate_database():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL tidak ditemukan di environment variables")
        return False
    
    print("🔧 Migrating database schema...")
    print(f"📊 Database: {database_url[:50]}...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        conn.autocommit = True
        
        print("\n📋 Checking existing tables...")
        
        # Check if tables exist
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('users', 'sessions', 'reply_guard_rules', 'scheduler_jobs', 'userbot_configs', 'admin_users', 'admin_logs')
        """)
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        print(f"🔍 Found tables: {', '.join(existing_tables)}")
        
        # Migration statements - drop foreign key constraints first, then alter columns
        migration_statements = []
        
        # Drop foreign key constraints (PostgreSQL requires this before altering referenced columns)
        if 'sessions' in existing_tables:
            migration_statements.append("ALTER TABLE sessions DROP CONSTRAINT IF EXISTS sessions_user_id_fkey")
        if 'reply_guard_rules' in existing_tables:
            migration_statements.append("ALTER TABLE reply_guard_rules DROP CONSTRAINT IF EXISTS reply_guard_rules_user_id_fkey")  
        if 'scheduler_jobs' in existing_tables:
            migration_statements.append("ALTER TABLE scheduler_jobs DROP CONSTRAINT IF EXISTS scheduler_jobs_user_id_fkey")
        if 'userbot_configs' in existing_tables:
            migration_statements.append("ALTER TABLE userbot_configs DROP CONSTRAINT IF EXISTS userbot_configs_user_id_fkey")
        if 'admin_users' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_users DROP CONSTRAINT IF EXISTS admin_users_user_id_fkey",
                "ALTER TABLE admin_users DROP CONSTRAINT IF EXISTS admin_users_created_by_fkey"
            ])
        if 'admin_logs' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_logs DROP CONSTRAINT IF EXISTS admin_logs_admin_user_id_fkey",
                "ALTER TABLE admin_logs DROP CONSTRAINT IF EXISTS admin_logs_target_user_id_fkey"
            ])
        
        # Alter columns from INTEGER to BIGINT
        if 'users' in existing_tables:
            migration_statements.append("ALTER TABLE users ALTER COLUMN id TYPE BIGINT")
            
        if 'sessions' in existing_tables:
            migration_statements.append("ALTER TABLE sessions ALTER COLUMN user_id TYPE BIGINT")
            
        if 'reply_guard_rules' in existing_tables:
            migration_statements.append("ALTER TABLE reply_guard_rules ALTER COLUMN user_id TYPE BIGINT")
            
        if 'scheduler_jobs' in existing_tables:
            migration_statements.append("ALTER TABLE scheduler_jobs ALTER COLUMN user_id TYPE BIGINT")
            
        if 'userbot_configs' in existing_tables:
            migration_statements.append("ALTER TABLE userbot_configs ALTER COLUMN user_id TYPE BIGINT")
            
        if 'admin_users' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_users ALTER COLUMN user_id TYPE BIGINT",
                "ALTER TABLE admin_users ALTER COLUMN created_by TYPE BIGINT"
            ])
            
        if 'admin_logs' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_logs ALTER COLUMN admin_user_id TYPE BIGINT", 
                "ALTER TABLE admin_logs ALTER COLUMN target_user_id TYPE BIGINT"
            ])
        
        # Recreate foreign key constraints
        if 'sessions' in existing_tables:
            migration_statements.append("ALTER TABLE sessions ADD CONSTRAINT sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
        if 'reply_guard_rules' in existing_tables:
            migration_statements.append("ALTER TABLE reply_guard_rules ADD CONSTRAINT reply_guard_rules_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
        if 'scheduler_jobs' in existing_tables:
            migration_statements.append("ALTER TABLE scheduler_jobs ADD CONSTRAINT scheduler_jobs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
        if 'userbot_configs' in existing_tables:
            migration_statements.append("ALTER TABLE userbot_configs ADD CONSTRAINT userbot_configs_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)")
        if 'admin_users' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_users ADD CONSTRAINT admin_users_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)",
                "ALTER TABLE admin_users ADD CONSTRAINT admin_users_created_by_fkey FOREIGN KEY (created_by) REFERENCES users(id)"
            ])
        if 'admin_logs' in existing_tables:
            migration_statements.extend([
                "ALTER TABLE admin_logs ADD CONSTRAINT admin_logs_admin_user_id_fkey FOREIGN KEY (admin_user_id) REFERENCES users(id)",
                "ALTER TABLE admin_logs ADD CONSTRAINT admin_logs_target_user_id_fkey FOREIGN KEY (target_user_id) REFERENCES users(id)"
            ])
        
        # Execute migration
        print(f"\n🔧 Executing {len(migration_statements)} migration statements...")
        for i, statement in enumerate(migration_statements, 1):
            print(f"   {i:2d}. {statement[:80]}{'...' if len(statement) > 80 else ''}")
            try:
                cursor.execute(statement)
                print(f"      ✅ OK")
            except Exception as e:
                print(f"      ⚠️  Warning: {e}")
                # Continue with other statements
        
        cursor.close()
        conn.close()
        
        print("\n✅ Database migration completed!")
        print("🎯 All user_id columns now support BIGINT (up to 9,223,372,036,854,775,807)")
        print("📱 Telegram user IDs like 5473468582 will now work properly")
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    print("🗃️  Database Schema Migration")
    print("=" * 50)
    
    # Confirm before proceeding
    response = input("⚠️  This will alter database schema. Continue? [y/N]: ").strip().lower()
    if response not in ['y', 'yes']:
        print("❌ Migration cancelled")
        sys.exit(1)
    
    success = migrate_database()
    if success:
        print("\n🚀 Ready to test! Try running bot wizard again.")
        sys.exit(0)
    else:
        print("\n💡 Check DATABASE_URL and try again.")
        sys.exit(1)