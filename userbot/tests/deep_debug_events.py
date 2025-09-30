#!/usr/bin/env python3
"""
Deep debugging untuk Reply Guard event handling.
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

async def debug_reply_guard_events():
    """Debug Reply Guard event handling."""
    print("🔍 DEEP DEBUG - REPLY GUARD EVENTS")
    print("=" * 50)
    
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
        from telethon import TelegramClient, events
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
        
        print(f"✅ Current rule: '{keyword}' -> '{rule['reply_text'][:50]}...'")
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
        
        # Create custom event handler untuk debugging
        message_received = False
        
        @events.register(events.NewMessage(incoming=True))
        async def debug_handler(event):
            nonlocal message_received
            message_received = True
            
            print(f"🔔 INCOMING MESSAGE DETECTED:")
            print(f"   Chat ID: {event.chat_id}")
            print(f"   Sender ID: {event.sender_id}")
            print(f"   Message: '{event.raw_text}'")
            print(f"   Is Group: {event.is_group}")
            print(f"   Is Channel: {event.is_channel}")
            print(f"   Outgoing: {event.out}")
            
            # Check if this matches our rule
            if event.chat_id == target_group:
                print(f"✅ Message is in target group!")
                
                if keyword.lower() in event.raw_text.lower():
                    print(f"✅ Keyword '{keyword}' found in message!")
                    
                    # Manual reply test
                    try:
                        await event.reply(f"🧪 DEBUG REPLY: {rule['reply_text']}")
                        print(f"✅ Debug reply sent successfully!")
                    except Exception as e:
                        print(f"❌ Failed to send debug reply: {e}")
                else:
                    print(f"⚠️ Keyword '{keyword}' not found in message")
            else:
                print(f"⚠️ Message is not in target group (expected: {target_group})")
            
        client.add_event_handler(debug_handler)
        
        # Wait for some incoming messages
        print("\\n👂 Listening for incoming messages...")
        print("Send a message to the target group to test...")
        print("Waiting 30 seconds for messages...")
        
        for i in range(30):
            await asyncio.sleep(1)
            if message_received:
                break
            if i % 5 == 0:
                print(f"   Still listening... ({30-i}s remaining)")
                
        if not message_received:
            print("⚠️ No messages received during listening period")
            
            # Let's send a test message ourselves
            print("\\n📤 Sending test message to trigger event...")
            test_message = f"🧪 DEBUG TEST: {keyword} - event debug"
            
            try:
                sent_msg = await client.send_message(target_group, test_message)
                print(f"✅ Test message sent (ID: {sent_msg.id})")
                
                # Wait a bit more
                print("⏳ Waiting 10 seconds for event...")
                await asyncio.sleep(10)
                
                if not message_received:
                    print("❌ Event handler was not triggered by our own message!")
                    print("💡 This suggests the event handler setup has issues")
                    
            except Exception as e:
                print(f"❌ Failed to send test message: {e}")
        
        await client.disconnect()
        
        print("\\n" + "="*50)
        print("🎯 DEBUG SUMMARY:")
        print(f"   Message received: {'YES' if message_received else 'NO'}")
        print(f"   Event handler working: {'YES' if message_received else 'UNKNOWN'}")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Deep debug failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_reply_guard_events())