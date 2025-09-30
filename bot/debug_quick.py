#!/usr/bin/env python3
"""Quick debug script to check database contents"""
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def main():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL tidak ditemukan")
        return
    
    print("🔍 Database Quick Check")
    print("=" * 30)
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check users
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"👥 Users: {user_count}")
        
        if user_count > 0:
            cursor.execute("SELECT id, username, first_name FROM users ORDER BY id DESC LIMIT 3")
            users = cursor.fetchall()
            print("   Recent users:")
            for user in users:
                print(f"     - ID: {user[0]} (@{user[1] or 'N/A'}) - {user[2] or 'N/A'}")
        
        # Check sessions  
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        print(f"📱 Sessions: {session_count}")
        
        if session_count > 0:
            cursor.execute("SELECT user_id, encrypted, created_at FROM sessions ORDER BY created_at DESC LIMIT 3")
            sessions = cursor.fetchall()
            print("   Recent sessions:")
            for session in sessions:
                print(f"     - User ID: {session[0]} - Encrypted: {session[1]} - {session[2]}")
        
        # Check specific user 5473468582
        cursor.execute("SELECT * FROM users WHERE id = 5473468582")
        user_data = cursor.fetchone()
        if user_data:
            print(f"\n🎯 User 5473468582 found in database")
            cursor.execute("SELECT COUNT(*) FROM sessions WHERE user_id = 5473468582")
            user_sessions = cursor.fetchone()[0]
            print(f"   Sessions for this user: {user_sessions}")
        else:
            print(f"\n❌ User 5473468582 NOT found in database")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()