#!/usr/bin/env python3
"""Add test user to database manually"""
import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime, timedelta

load_dotenv()

def add_test_user():
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL tidak ditemukan")
        return
    
    print("➕ Adding test user to database...")
    
    try:
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        conn.autocommit = True
        
        user_id = 5473468582
        username = "test_user"
        first_name = "Test User"
        
        # Add user with active subscription
        now = datetime.now()
        end_date = now + timedelta(days=30)
        
        cursor.execute("""
            INSERT INTO users (id, username, first_name, last_name, is_active, 
                             tipe_paket_subs, tanggal_subs_dimulai, tanggal_subs_selesai, 
                             status_subscription)
            VALUES (%s, %s, %s, %s, 1, 'premium', %s, %s, 'active')
            ON CONFLICT(id) DO UPDATE SET
                username=EXCLUDED.username,
                first_name=EXCLUDED.first_name,
                status_subscription='active'
        """, (user_id, username, first_name, None, now, end_date))
        
        cursor.close()
        conn.close()
        
        print(f"✅ User {user_id} added with active premium subscription")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_test_user()