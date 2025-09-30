#!/usr/bin/env python3
"""Clean dummy session data from database"""
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def clean_dummy_data():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL tidak ditemukan")
        return
    
    print("🧹 Cleaning dummy data from database...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        
        # Check what we have
        cursor.execute("SELECT COUNT(*) FROM sessions")
        session_count = cursor.fetchone()[0]
        print(f"📱 Current sessions: {session_count}")
        
        # Delete all dummy sessions
        cursor.execute("DELETE FROM sessions")
        deleted_sessions = cursor.rowcount
        
        # Delete test users but keep if they're real users  
        cursor.execute("DELETE FROM users WHERE first_name = 'Test User'")
        deleted_users = cursor.rowcount
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Cleaned database:")
        print(f"   🗑️ Deleted {deleted_sessions} dummy sessions")
        print(f"   🗑️ Deleted {deleted_users} test users")
        print("📊 Database now clean - ready for real sessions")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    clean_dummy_data()