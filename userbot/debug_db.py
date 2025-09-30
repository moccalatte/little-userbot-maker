#!/usr/bin/env python3
"""Debug script untuk melihat isi database."""
import os
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from database import Database
from config import load_userbot_settings


def main():
    print("🔍 Debug Database Content")
    print("=" * 40)
    
    try:
        settings = load_userbot_settings()
        print(f"📊 DATABASE_URL: {settings.database_url[:50]}...")
        
        db = Database.get_instance(settings.database_url)
        print("✅ Database connection successful")
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return
    
    print("\n📋 Checking Tables...")
    
    # Check users table
    try:
        query = "SELECT COUNT(*) as count FROM users"
        result = db.adapter.execute_one(query)
        user_count = result["count"] if result else 0
        print(f"👥 Users: {user_count}")
        
        if user_count > 0:
            query = "SELECT id, username, first_name, status_subscription FROM users LIMIT 5"
            users = db.adapter.execute(query)
            print("   Recent users:")
            for user in users:
                print(f"     - {user['id']} (@{user.get('username', 'N/A')}) - {user.get('first_name', 'N/A')} - {user.get('status_subscription', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Error checking users: {e}")
    
    # Check sessions table  
    try:
        query = "SELECT COUNT(*) as count FROM sessions"
        result = db.adapter.execute_one(query)
        session_count = result["count"] if result else 0
        print(f"📱 Sessions: {session_count}")
        
        if session_count > 0:
            query = "SELECT user_id, encrypted, created_at FROM sessions ORDER BY created_at DESC LIMIT 5"
            sessions = db.adapter.execute(query)
            print("   Recent sessions:")
            for session in sessions:
                print(f"     - User {session['user_id']} - Encrypted: {session.get('encrypted', False)} - {session.get('created_at', 'N/A')}")
                
    except Exception as e:
        print(f"❌ Error checking sessions: {e}")
    
    # Check active userbot sessions
    try:
        active_sessions = db.get_active_userbot_sessions()
        print(f"🤖 Active userbot sessions: {len(active_sessions)}")
        
        for session in active_sessions[:5]:
            print(f"     - User {session['user_id']} (@{session.get('username', 'N/A')}) - {session.get('tipe_paket_subs', 'N/A')}")
            
    except Exception as e:
        print(f"❌ Error checking active sessions: {e}")
    
    # Check feature configs
    try:
        query = "SELECT user_id, feature_type, enabled FROM feature_configs LIMIT 5"
        configs = db.adapter.execute(query)
        print(f"⚙️  Feature configs: {len(configs)}")
        
    except Exception as e:
        print(f"⚙️  Feature configs table may not exist yet")
    
    print("\n💡 Tips:")
    print("- Jika tidak ada users/sessions, jalankan Bot Wizard terlebih dahulu")
    print("- User harus registrasi dan buat session via bot")
    print("- Pastikan user punya subscription aktif")
    

if __name__ == "__main__":
    main()