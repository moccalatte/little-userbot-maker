#!/usr/bin/env python3
"""
Direct test untuk target group yang tepat.
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

async def target_group_test():
    """Test target group secara langsung."""
    print("🎯 TARGET GROUP DIRECT TEST")
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
        
        print(f"✅ Testing rule: '{keyword}' -> '{rule['reply_text'][:30]}...'")
        print(f"✅ Target group: {target_group}")
        
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
        
        # Check if we can access target group
        try:
            target_chat = await client.get_entity(target_group)
            print(f"✅ Target chat accessible: {target_chat.title}")
        except Exception as e:
            print(f"❌ Cannot access target group: {e}")
            return
        
        # Create event listener specifically for target group
        reply_detected = False
        test_message_id = None
        
        @events.register(events.NewMessage(chats=[target_group]))
        async def target_handler(event):
            nonlocal reply_detected, test_message_id
            
            print(f"🔔 MESSAGE IN TARGET GROUP:")
            print(f"   Sender: {event.sender_id}")
            print(f"   Message: '{event.raw_text}'")
            print(f"   Is our account: {event.sender_id == owner_id}")
            
            # Check if this is a reply to our test message
            if (event.sender_id == owner_id and 
                test_message_id and 
                hasattr(event, 'reply_to') and
                event.reply_to and 
                event.reply_to.reply_to_msg_id == test_message_id):
                print("🎯 ✅ DETECTED REPLY FROM USERBOT!")
                reply_detected = True
                
        client.add_event_handler(target_handler)
        
        # Send test message to target group
        test_message = f"🧪 TARGET TEST: {keyword} - direct group test"
        print(f"\\n📤 Sending message to target group: '{test_message}'")
        
        try:
            sent_msg = await client.send_message(target_group, test_message)
            test_message_id = sent_msg.id
            print(f"✅ Test message sent (ID: {sent_msg.id})")
            
            # Wait for Reply Guard response
            print("⏳ Waiting 20 seconds for Reply Guard...")
            for i in range(20):
                await asyncio.sleep(1)
                if reply_detected:
                    break
                if i % 5 == 4:
                    print(f"   Still waiting... ({20-i}s remaining)")
                    
            if reply_detected:
                print("🎉 ✅ REPLY GUARD WORKING!")
            else:
                print("❌ No Reply Guard response detected")
                
                # Check recent messages in target group
                print("\\n🔍 Checking recent messages in target group:")
                async for msg in client.iter_messages(target_group, limit=5):
                    print(f"   ID:{msg.id} Sender:{msg.sender_id} Text:'{msg.message[:50]}...'")
                    
                # Check if there are any messages from us after the test
                our_messages = []
                async for msg in client.iter_messages(target_group, limit=10):
                    if msg.sender_id == owner_id and msg.id > test_message_id:
                        our_messages.append(msg)
                        
                if our_messages:
                    print(f"✅ Found {len(our_messages)} messages from userbot after test:")
                    for msg in our_messages:
                        print(f"   '{msg.message[:50]}...'")
                else:
                    print("❌ No messages from userbot found after test")
                    
        except Exception as e:
            print(f"❌ Failed to send test message: {e}")
            
        await client.disconnect()
        
        print("\\n" + "="*40)
        print("🎯 TARGET GROUP TEST SUMMARY:")
        print(f"   Target accessible: YES")
        print(f"   Message sent: YES")
        print(f"   Reply detected: {'YES' if reply_detected else 'NO'}")
        print("="*40)
        
    except Exception as e:
        print(f"❌ Target group test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(target_group_test())