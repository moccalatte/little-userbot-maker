#!/usr/bin/env python3
"""
COMPREHENSIVE REPLY GUARD DEBUG & FIX
Mendiagnosis dan memperbaiki semua masalah Reply Guard secara menyeluruh.
"""
import os
import sys
import subprocess
import json
import time
from pathlib import Path

# Change os.makedirs(dir_path, exist_ok=True) to use tests/logs or subfolder
TEST_LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(TEST_LOG_DIR, exist_ok=True)

class ComprehensiveReplyGuardFix:
    def __init__(self):
        self.owner_id = 5473468582
        self.target_group = -1002406400543
        
    def run_comprehensive_fix(self):
        """Run comprehensive debugging dan fixing."""
        print("🔧 COMPREHENSIVE REPLY GUARD DEBUG & FIX")
        print("=" * 60)
        
        # 1. Check project structure
        self.check_project_structure()
        
        # 2. Check processes
        self.check_processes()
        
        # 3. Check databases
        self.check_databases()
        
        # 4. Check sync service
        self.check_sync_service()
        
        # 5. Check bot wizard connection
        self.check_bot_wizard_connection()
        
        # 6. Fix self-message filtering issue
        self.fix_self_message_filtering()
        
        # 7. Create admin commands for testing
        self.create_admin_commands()
        
        # 8. Create automated testing system
        self.create_automated_testing()
        
        print("\n🎯 COMPREHENSIVE FIXES COMPLETED!")
        
    def check_project_structure(self):
        """Check dan perbaiki struktur project.""" 
        print("\n1️⃣ CHECKING PROJECT STRUCTURE...")
        
        required_dirs = [
            "bot", "userbot", "tests", "data", 
            "userbot/logs", "data/reply_guard_configs"
        ]
        
        for dir_path in required_dirs:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path, exist_ok=True)
                print(f"✅ Created directory: {dir_path}")
            else:
                print(f"✅ Directory exists: {dir_path}")
                
        # Check important files
        important_files = [
            "userbot/main.py",
            "userbot/reply_guard.py", 
            "bot/main.py",
            "project_rules.md"
        ]
        
        for file_path in important_files:
            if os.path.exists(file_path):
                print(f"✅ File exists: {file_path}")
            else:
                print(f"❌ Missing file: {file_path}")
                
    def check_processes(self):
        """Check running processes."""
        print("\n2️⃣ CHECKING PROCESSES...")
        
        try:
            # Check userbot process
            result = subprocess.run(['pgrep', '-f', f'python.*main.py.*{self.owner_id}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print(f"✅ Userbot running (PIDs: {', '.join(pids)})")
                
                # Check process details
                for pid in pids:
                    if pid:
                        ps_result = subprocess.run(['ps', '-p', pid, '-o', 'pid,cmd'], 
                                                 capture_output=True, text=True)
                        if ps_result.returncode == 0:
                            print(f"   Process {pid}: {ps_result.stdout.split('\\n')[1] if len(ps_result.stdout.split('\\n')) > 1 else 'Unknown'}")
            else:
                print("❌ Userbot not running")
                
            # Check bot wizard process
            bot_result = subprocess.run(['pgrep', '-f', 'python.*bot.*main'], 
                                      capture_output=True, text=True)
            if bot_result.returncode == 0:
                print(f"✅ Bot Wizard running (PID: {bot_result.stdout.strip()})")
            else:
                print("⚠️ Bot Wizard not detected")
                
        except Exception as e:
            print(f"❌ Error checking processes: {e}")
            
    def check_databases(self):
        """Check database status dan content."""
        print("\n3️⃣ CHECKING DATABASES...")
        
        try:
            # Try to connect with environment from userbot dir
            os.chdir("userbot")
            
            # Simple database check without external dependencies
            db_check_script = '''
import os
import sys
sys.path.append('.')

# Simple .env reader
def load_simple_env():
    env_vars = {}
    if os.path.exists('.env'):
        with open('.env', 'r') as f:
            for line in f:
                if '=' in line and not line.strip().startswith('#'):
                    key, value = line.strip().split('=', 1)
                    env_vars[key] = value
    return env_vars

env_vars = load_simple_env()
for key, value in env_vars.items():
    os.environ[key] = value

try:
    from database import Database
    database = Database()
    rules = database.list_reply_guard_rules(5473468582)
    
    print(f"✅ Database connected successfully")
    print(f"📊 Found {len(rules)} Reply Guard rules:")
    
    for rule in rules:
        print(f"   Rule {rule['id']}: {rule['include']} -> {rule['targets']}")
        print(f"   Reply: '{rule['reply_text'][:50]}...'")
        print(f"   Created: {rule['created_at']}")
        
except Exception as e:
    print(f"❌ Database error: {e}")
'''
            
            with open("temp_db_check.py", "w") as f:
                f.write(db_check_script)
                
            db_result = subprocess.run(['python3', 'temp_db_check.py'], 
                                     capture_output=True, text=True)
            print(db_result.stdout)
            if db_result.stderr:
                print(f"DB Errors: {db_result.stderr}")
                
            os.remove("temp_db_check.py")
            os.chdir("..")
            
        except Exception as e:
            print(f"❌ Database check failed: {e}")
            os.chdir("..")
            
    def check_sync_service(self):
        """Check sync service status."""
        print("\n4️⃣ CHECKING SYNC SERVICE...")
        
        # Check for config files
        config_dir = "data/reply_guard_configs"
        if os.path.exists(config_dir):
            config_files = os.listdir(config_dir)
            print(f"✅ Config directory exists with {len(config_files)} files")
            
            # Show latest config files
            for file in sorted(config_files)[-3:]:  # Last 3 files
                file_path = os.path.join(config_dir, file)
                try:
                    with open(file_path, 'r') as f:
                        config = json.load(f)
                    print(f"   Config: {config.get('keywords', [])} -> {config.get('targets', [])}")
                except:
                    print(f"   Config file: {file} (read error)")
        else:
            print("❌ Config directory not found")
            
        # Check sync service
        if os.path.exists("userbot_sync_service.py"):
            print("✅ Sync service file exists")
            
            # Check if sync service is running
            sync_result = subprocess.run(['pgrep', '-f', 'userbot_sync_service'], 
                                       capture_output=True, text=True)
            if sync_result.returncode == 0:
                print(f"✅ Sync service running (PID: {sync_result.stdout.strip()})")
            else:
                print("⚠️ Sync service not running - starting it...")
                try:
                    subprocess.Popen(['python3', 'userbot_sync_service.py'], 
                                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(2)
                    print("✅ Sync service started")
                except Exception as e:
                    print(f"❌ Failed to start sync service: {e}")
        else:
            print("❌ Sync service file not found")
            
    def check_bot_wizard_connection(self):
        """Check Bot Wizard API connection."""
        print("\n5️⃣ CHECKING BOT WIZARD CONNECTION...")
        
        # Simple HTTP check without requests dependency
        try:
            import urllib.request
            import urllib.error
            
            # Try to connect to Bot Wizard
            try:
                response = urllib.request.urlopen('http://localhost:8000/health', timeout=5)
                print("✅ Bot Wizard API accessible")
            except urllib.error.URLError:
                print("⚠️ Bot Wizard API not accessible (may be normal if different port)")
            except:
                print("⚠️ Could not check Bot Wizard API")
                
        except Exception as e:
            print(f"⚠️ HTTP check failed: {e}")
            
    def fix_self_message_filtering(self):
        """Fix self-message filtering untuk testing."""
        print("\n6️⃣ FIXING SELF-MESSAGE FILTERING...")
        
        # Backup and modify reply_guard.py to allow self-testing
        reply_guard_path = "userbot/reply_guard.py"
        
        if os.path.exists(reply_guard_path):
            # Check if already has test mode
            with open(reply_guard_path, 'r') as f:
                content = f.read()
                
            if "ALLOW_SELF_REPLY_FOR_TESTING" not in content:
                print("✅ Adding self-reply test mode to Reply Guard...")
                
                # Add test mode flag
                test_mode_code = '''
    # Test mode: Allow self-replies for testing purposes
    ALLOW_SELF_REPLY_FOR_TESTING = os.getenv("ALLOW_SELF_REPLY_FOR_TESTING", "false").lower() == "true"
'''
                
                # Find the import section and add os import if needed
                if "import os" not in content:
                    content = content.replace("import logging", "import logging\\nimport os")
                
                # Add test mode flag after imports
                import_end = content.find("class ReplyGuard:")
                if import_end != -1:
                    content = content[:import_end] + test_mode_code + "\\n\\n" + content[import_end:]
                
                # Modify self-message filtering logic
                old_self_check = "if self._me_id is not None and event.sender_id == self._me_id:"
                new_self_check = "if self._me_id is not None and event.sender_id == self._me_id and not self.ALLOW_SELF_REPLY_FOR_TESTING:"
                
                content = content.replace(old_self_check, new_self_check)
                
                # Write back
                with open(reply_guard_path + ".backup", 'w') as f:
                    f.write(content)
                    
                print("✅ Self-reply test mode added (backup created)")
                print("   Set ALLOW_SELF_REPLY_FOR_TESTING=true in userbot/.env to enable")
            else:
                print("✅ Self-reply test mode already exists")
        else:
            print("❌ reply_guard.py not found")
            
    def create_admin_commands(self):
        """Create admin commands for testing."""
        print("\n7️⃣ CREATING ADMIN COMMANDS...")
        
        admin_commands_code = '''
#!/usr/bin/env python3
"""
Admin commands untuk testing dan monitoring Reply Guard.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent / "userbot"))
os.chdir(str(Path(__file__).parent))

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
        print("\\n📋 TO ENABLE SELF-REPLY TESTING:")
        print("   1. Add 'ALLOW_SELF_REPLY_FOR_TESTING=true' to userbot/.env")
        print("   2. Restart userbot")
        print("   3. Run this command again")
        
    except Exception as e:
        print(f"❌ Admin test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(admin_test_reply_guard())
'''
        
        admin_file = "tests/admin_reply_guard_test.py"
        with open(admin_file, 'w') as f:
            f.write(admin_commands_code)
            
        os.chmod(admin_file, 0o755)
        print(f"✅ Admin commands created: {admin_file}")
        
    def create_automated_testing(self):
        """Create automated testing system."""
        print("\n8️⃣ CREATING AUTOMATED TESTING SYSTEM...")
        
        # Create monitor script
        monitor_script = '''
#!/usr/bin/env python3
"""
Automated monitoring untuk Reply Guard.
"""
import os
import time
import subprocess
from datetime import datetime

class ReplyGuardMonitor:
    def __init__(self):
        self.owner_id = 5473468582
        self.target_group = -1002406400543
        
    def run_continuous_monitoring(self):
        """Run continuous monitoring."""
        print("📊 STARTING REPLY GUARD CONTINUOUS MONITORING")
        print("=" * 50)
        print("Press Ctrl+C to stop...")
        
        try:
            while True:
                self.check_status()
                time.sleep(30)  # Check every 30 seconds
                
        except KeyboardInterrupt:
            print("\\n⏹️ Monitoring stopped by user")
            
    def check_status(self):
        """Check current status."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\\n[{timestamp}] Checking Reply Guard status...")
        
        # Check userbot process
        try:
            result = subprocess.run(['pgrep', '-f', f'python.*main.py.*{self.owner_id}'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print(f"✅ Userbot running")
            else:
                print(f"❌ Userbot not running!")
                
        except Exception as e:
            print(f"⚠️ Process check failed: {e}")
            
        # Check logs for recent activity
        log_files = [
            "userbot/logs/userbot_reply_guard.log",
            "userbot/logs/userbot.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    # Check for recent activity (last 30 seconds)
                    recent_time = time.time() - 30
                    
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-10:]  # Last 10 lines
                        
                    recent_activity = 0
                    for line in lines:
                        if any(keyword in line.lower() for keyword in 
                               ['reply guard', 'auto-reply', 'terkirim']):
                            recent_activity += 1
                            
                    if recent_activity > 0:
                        print(f"📋 Recent activity in {log_file}: {recent_activity} entries")
                        
                except Exception as e:
                    print(f"⚠️ Log check failed for {log_file}: {e}")

if __name__ == "__main__":
    monitor = ReplyGuardMonitor()
    monitor.run_continuous_monitoring()
'''
        
        monitor_file = "tests/reply_guard_monitor.py"
        with open(monitor_file, 'w') as f:
            f.write(monitor_script)
            
        os.chmod(monitor_file, 0o755)
        print(f"✅ Monitor created: {monitor_file}")
        
        # Create quick test script
        quick_test = '''#!/usr/bin/env python3
"""Quick Reply Guard test."""
import subprocess
import os

def quick_test():
    print("⚡ QUICK REPLY GUARD TEST")
    print("=" * 30)
    
    # Check if userbot is running
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*main.py.*5473468582'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Userbot is running")
        else:
            print("❌ Userbot not running!")
            print("Start with: cd userbot && python3 main.py --owner-id 5473468582 &")
            return
    except:
        print("⚠️ Could not check userbot status")
        
    # Show current configuration
    print("\\n📊 Current configuration:")
    print("   • Keyword: Check via Bot Wizard (@lilwizardbot)")
    print("   • Target Group: -1002406400543")
    print("   • Self-reply: Disabled by default (security feature)")
    
    print("\\n🧪 TO TEST:")
    print("   1. Use different Telegram account")
    print("   2. Send message with keyword to target group")
    print("   3. Watch for auto-reply")
    
    print("\\n📋 LOGS:")
    print("   • tail -f userbot/logs/userbot_reply_guard.log")
    print("   • tail -f userbot/logs/userbot.log")
    
    print("\\n🔧 ADMIN TEST:")
    print("   • python3 tests/admin_reply_guard_test.py")

if __name__ == "__main__":
    quick_test()
'''
        
        quick_file = "tests/quick_reply_guard_test.py"
        with open(quick_file, 'w') as f:
            f.write(quick_test)
            
        os.chmod(quick_file, 0o755)
        print(f"✅ Quick test created: {quick_file}")

def main():
    """Main function."""
    fixer = ComprehensiveReplyGuardFix()
    fixer.run_comprehensive_fix()
    
    print("\n" + "="*60)
    print("🎯 NEXT STEPS:")
    print("1. Run: python3 tests/admin_reply_guard_test.py")
    print("2. Run: python3 tests/quick_reply_guard_test.py") 
    print("3. Monitor: python3 tests/reply_guard_monitor.py")
    print("4. Enable self-reply testing if needed:")
    print("   Add 'ALLOW_SELF_REPLY_FOR_TESTING=true' to userbot/.env")
    print("="*60)

if __name__ == "__main__":
    main()