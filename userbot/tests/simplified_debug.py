#!/usr/bin/env python3
"""
Simplified debugging tanpa Telethon dependencies.
"""
import os
import sys
import subprocess
import json
from pathlib import Path

# Add userbot directory to path
project_root = Path(__file__).parent.parent
userbot_dir = project_root / "userbot"
sys.path.append(str(userbot_dir))
os.chdir(str(project_root))

def test_database_connection():
    """Test database connection tanpa Telethon."""
    print("🔧 SIMPLIFIED REPLY GUARD DEBUG")
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

        print("✅ Environment loaded successfully")

        # Test database connection
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
            
        # Check processes
        print("\n🔍 CHECKING PROCESSES...")
        try:
            result = subprocess.run(['pgrep', '-f', f'python.*main.py.*5473468582'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                pids = result.stdout.strip().split('\n')
                print(f"✅ Userbot running (PIDs: {', '.join(pids)})")
                
                for pid in pids:
                    if pid:
                        ps_result = subprocess.run(['ps', '-p', pid, '-o', 'pid,cmd'], 
                                                 capture_output=True, text=True)
                        if ps_result.returncode == 0:
                            cmd_line = ps_result.stdout.split('\n')[1] if len(ps_result.stdout.split('\n')) > 1 else 'Unknown'
                            print(f"   Process {pid}: {cmd_line}")
            else:
                print("❌ Userbot not running")
                
        except Exception as e:
            print(f"❌ Process check failed: {e}")
            
        # Check config files
        print("\n📁 CHECKING CONFIG FILES...")
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
            
        # Check logs
        print("\n📋 CHECKING LOGS...")
        log_files = [
            "userbot/logs/userbot_reply_guard.log",
            "userbot/logs/userbot.log"
        ]
        
        for log_file in log_files:
            if os.path.exists(log_file):
                try:
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-5:]  # Last 5 lines
                        
                    print(f"✅ {log_file} (last 5 lines):")
                    for line in lines:
                        print(f"   {line.strip()}")
                        
                except Exception as e:
                    print(f"⚠️ Log read failed for {log_file}: {e}")
            else:
                print(f"❌ Log file not found: {log_file}")
                
        # Test self-reply feature status
        print("\n🧪 SELF-REPLY TEST MODE STATUS...")
        reply_guard_path = "userbot/reply_guard.py"
        if os.path.exists(reply_guard_path):
            with open(reply_guard_path, 'r') as f:
                content = f.read()
                
            if "ALLOW_SELF_REPLY_FOR_TESTING" in content:
                print("✅ Self-reply test mode available")
                
                # Check if enabled in env
                if env_vars.get("ALLOW_SELF_REPLY_FOR_TESTING", "false").lower() == "true":
                    print("✅ Self-reply test mode ENABLED")
                else:
                    print("⚠️ Self-reply test mode DISABLED")
                    print("   To enable: Add 'ALLOW_SELF_REPLY_FOR_TESTING=true' to userbot/.env")
            else:
                print("❌ Self-reply test mode not available")
        else:
            print("❌ reply_guard.py not found")
            
        print("\n" + "="*50)
        print("🎯 DIAGNOSIS SUMMARY:")
        print("1. Database connection: Check above")
        print("2. Userbot process: Check above") 
        print("3. Config files: Check above")
        print("4. Logs: Check above")
        print("5. Self-reply mode: Check above")
        print("\n💡 NEXT STEPS:")
        print("- If database works but userbot doesn't reply:")
        print("  1. Enable self-reply testing mode")
        print("  2. Restart userbot")
        print("  3. Test with keyword from different account")
        print("="*50)
        
    except Exception as e:
        print(f"❌ Simplified test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_database_connection()