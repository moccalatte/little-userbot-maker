#!/usr/bin/env python3
"""Add test session to database"""
import os
import sys
import json
import psycopg2
from dotenv import load_dotenv
from cryptography.fernet import Fernet

load_dotenv()

def add_test_session():
    database_url = os.getenv("DATABASE_URL")
    secret_key = os.getenv("SECRET_KEY")
    
    if not database_url:
        print("❌ DATABASE_URL tidak ditemukan")
        return
    
    if not secret_key:
        print("❌ SECRET_KEY tidak ditemukan")
        return
    
    print("➕ Adding test session to database...")
    
    # Create a dummy session string for testing
    # This is a real Telegram session string format but with dummy data
    test_session_string = "1ApWapzMBu1vGJF8tRKQLGRLKZEZr+kMqA0Z4MHwK0Oe7B5ksXoTy8VH+K4YlzM3P5oPqRsVvFqHjKSbD6YVKl4KKT+KBdHjMa7RlNcLg8PaVw4oD+E5aFdH3q9XvFmN8Kt2CuJw3AcOm1gJlRYxZvJsZqYoTa0kRa7kZyK9tR8lZzKcSqWtFgD4oJpZzYvRvDyKoRa8ZqKtSgZ3oRqJzXwLpYtRx8KmYs5aKdH7nFxG6tRaK5oPqFmJzYvRs9CqTaYl2FxGkJdHpNaRl5oKsQ8fD3PqRvGmJyZwTaZxKcOp0FgDz4aJlNaRvCq8oNzKmSb7tRxFaYlJq3PvZgNkX6yRa5ZxWsJlKcOp0FgDz4aJlNa"
    
    try:
        # Encrypt the session string
        fernet = Fernet(secret_key.encode()[:44].ljust(44, b'='))
        encrypted_session = fernet.encrypt(test_session_string.encode()).decode()
        
        conn = psycopg2.connect(database_url)
        cursor = conn.cursor()
        conn.autocommit = True
        
        user_id = 5473468582
        metadata = json.dumps({
            "source": "test",
            "telegram_user": user_id,
            "created_for_testing": True
        })
        
        cursor.execute("""
            INSERT INTO sessions (user_id, session_string, encrypted, metadata)
            VALUES (%s, %s, 1, %s)
        """, (user_id, encrypted_session, metadata))
        
        cursor.close()
        conn.close()
        
        print(f"✅ Test session added for user {user_id}")
        print(f"🔐 Session encrypted and stored in database")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    add_test_session()