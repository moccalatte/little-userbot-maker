#!/usr/bin/env python3
"""
Live test Reply Guard dengan mengirim test message.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add userbot directory to path
project_root = Path(__file__).parent.parent
userbot_dir = project_root / "userbot"
sys.path.append(str(userbot_dir))
os.chdir(str(project_root))

async def live_test_reply_guard():
    """Test Reply Guard dengan mengirim message langsung."""
    print("🧪 LIVE REPLY GUARD TEST")
    print("=" * 40)
    
    try:
        # Load simple env
        def load_simple_env():
            env_vars = {}
            env_file = "userbot/.env"
            if os.path.exists(env_file):
                with open(env_file, 'r') as f:
                    for line in f:
                        if '=' in line and not line.strip().startswith('#'):
                            key, value = line.strip().split('=', 1)
                            env_vars[key] = value
            return env_vars

        env_vars = load_simple_env()
        for key, value in env_vars.items():
            os.environ[key] = value

        from database import Database
        from telethon import TelegramClient
        from telethon.sessions import StringSession
        from utils import build_cipher, decrypt_text
        
        owner_id = 5473468582
        target_group = -1002406400543
        
        # Get current rules
        database = Database()
        rules = database.list_reply_guard_rules(owner_id)
        
        if not rules:
            print("❌ No Reply Guard rules found!")
            return
            
        rule = rules[0]
        keyword = rule['include'][0] if rule['include'] else "test"
        
        print(f"✅ Current rule: '{keyword}' -> '{rule['reply_text']}'")
        print(f"✅ Target group: {rule['targets'][0]}")
        print(f"✅ Self-reply test mode: {env_vars.get('ALLOW_SELF_REPLY_FOR_TESTING', 'false')}")
        
        # Setup Telegram client
        record = database.get_latest_session(owner_id)
        session_string = record.get("session_string", "").strip()
        
        if record.get("encrypted"):
            secret_key = os.getenv("SECRET_KEY")
            if secret_key:
                cipher = build_cipher(secret_key)
                session_string = decrypt_text(cipher, session_string)
                
        api_id = int(os.getenv("API_ID", 13311218))
        api_hash = os.getenv("API_HASH", "f24f2481bc05f704033308eae0dd9bc2")
        
        client = TelegramClient(StringSession(session_string), api_id, api_hash)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session not authorized")
            return
            
        me = await client.get_me()
        print(f"✅ Connected as: {me.first_name} (@{me.username})")
        
        # Send test message
        test_message = f"🧪 LIVE TEST: {keyword} - automated testing"
        
        try:
            print(f"📤 Sending test message: '{test_message}'")
            sent_msg = await client.send_message(target_group, test_message)
            print(f"✅ Test message sent (ID: {sent_msg.id})")
            
            # Wait and check for reply
            print("⏳ Waiting 15 seconds for Reply Guard response...")
            await asyncio.sleep(15)
            
            # Check for replies
            reply_found = False
            print("🔍 Checking for replies...")
            
            async for msg in client.iter_messages(target_group, limit=20):
                if msg.id > sent_msg.id:
                    print(f"📨 Message after test: ID={msg.id} sender={msg.sender_id} text='{msg.message[:50]}...'")
                    
                    if msg.sender_id == owner_id:
                        if hasattr(msg, 'reply_to') and msg.reply_to and msg.reply_to.reply_to_msg_id == sent_msg.id:
                            print(f"🎯 ✅ DIRECT REPLY FOUND!")
                            print(f"   📨 Reply: '{msg.message}'")
                            reply_found = True
                            break
                        else:
                            print(f"📨 Userbot message (may be auto-reply): '{msg.message[:50]}...'")
                            if keyword.lower() in rule['reply_text'].lower():
                                print(f"🎯 ✅ LIKELY AUTO-REPLY FOUND!")
                                reply_found = True
                                break
                                
            if not reply_found:
                print("❌ No Reply Guard response detected")
                print("💡 Possible causes:")
                print("   - Self-message filtering still active")
                print("   - Rate limiting")
                print("   - Wrong target group")
                print("   - Rule matching issue")
                
                # Show latest log entries
                print("\\n📋 Latest userbot logs:")
                try:
                    with open("userbot/logs/userbot_reply_guard.log", "r") as f:
                        lines = f.readlines()[-3:]
                    for line in lines:
                        print(f"   {line.strip()}")
                except:
                    print("   (Could not read log file)")
            else:
                print("🎉 ✅ REPLY GUARD TEST SUCCESSFUL!")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        await client.disconnect()
        
        print("\\n" + "="*40)
        print("📋 TEST SUMMARY:")
        print(f"   Keyword tested: '{keyword}'")
        print(f"   Target group: {target_group}")
        print(f"   Self-reply mode: {env_vars.get('ALLOW_SELF_REPLY_FOR_TESTING', 'false')}")
        print(f"   Reply found: {'YES' if reply_found else 'NO'}")
        print("="*40)
        
    except Exception as e:
        print(f"❌ Live test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(live_test_reply_guard())