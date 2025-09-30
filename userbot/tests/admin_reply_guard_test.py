
#!/usr/bin/env python3
"""
Admin commands untuk testing dan monitoring Reply Guard.
"""
import asyncio
import os
import sys
from pathlib import Path

# Add both userbot directory and parent directory to path
project_root = Path(__file__).parent.parent
userbot_dir = project_root / "userbot"
sys.path.append(str(userbot_dir))
sys.path.append(str(project_root))
os.chdir(str(project_root))

async def admin_test_reply_guard():
    """Test Reply Guard dengan admin commands."""
    print("🔧 ADMIN REPLY GUARD TESTING")
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
        test_message = f"🧪 ADMIN TEST: {keyword} via automated admin command"
        
        try:
            sent_msg = await client.send_message(target_group, test_message)
            print(f"✅ Test message sent (ID: {sent_msg.id})")
            
            # Wait and check for reply
            print("⏳ Waiting 10 seconds for Reply Guard response...")
            await asyncio.sleep(10)
            
            # Check for replies
            reply_found = False
            async for msg in client.iter_messages(target_group, limit=10):
                if msg.id > sent_msg.id:
                    if hasattr(msg, 'reply_to') and msg.reply_to:
                        if msg.reply_to.reply_to_msg_id == sent_msg.id and msg.sender_id == owner_id:
                            print(f"🎯 ✅ REPLY GUARD WORKED!")
                            print(f"   📨 Reply: '{msg.message}'")
                            reply_found = True
                            break
                    elif msg.sender_id == owner_id:
                        print(f"📨 Userbot message (may be reply): '{msg.message[:50]}...'")
                        
            if not reply_found:
                print("❌ No direct Reply Guard response detected")
                print("💡 This may be normal if self-message filtering is active")
                
        except Exception as e:
            print(f"❌ Test failed: {e}")
            
        await client.disconnect()
        
        # Show instructions
        print("\n📋 TO ENABLE SELF-REPLY TESTING:")
        print("   1. Add 'ALLOW_SELF_REPLY_FOR_TESTING=true' to userbot/.env")
        print("   2. Restart userbot")
        print("   3. Run this command again")
        
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(admin_test_reply_guard())
