#!/usr/bin/env python3
"""
Quick verification - summary of current status.
"""
import os
import subprocess
import sys
from pathlib import Path

# Add userbot directory to path
project_root = Path(__file__).parent.parent
userbot_dir = project_root / "userbot"
sys.path.append(str(userbot_dir))
os.chdir(str(project_root))

def quick_verify():
    """Quick verification of Reply Guard status."""
    print("⚡ QUICK REPLY GUARD VERIFICATION")
    print("=" * 50)
    
    # 1. Check process
    try:
        result = subprocess.run(['pgrep', '-f', 'python.*main.py.*5473468582'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"✅ Userbot running (PIDs: {', '.join(pids)})")
        else:
            print("❌ Userbot not running!")
            return
    except:
        print("⚠️ Could not check userbot status")
        return
        
    # 2. Check database
    try:
        # Load env
        env_vars = {}
        env_file = "userbot/.env"
        if os.path.exists(env_file):
            with open(env_file, 'r') as f:
                for line in f:
                    if '=' in line and not line.strip().startswith('#'):
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value

        for key, value in env_vars.items():
            os.environ[key] = value

        from database import Database
        database = Database()
        rules = database.list_reply_guard_rules(5473468582)
        
        print(f"✅ Database connected - {len(rules)} rules active")
        for rule in rules:
            print(f"   Rule: '{rule['include'][0]}' -> '{rule['reply_text'][:30]}...'")
            
    except Exception as e:
        print(f"❌ Database error: {e}")
        return
        
    # 3. Check self-reply mode
    if env_vars.get("ALLOW_SELF_REPLY_FOR_TESTING", "false").lower() == "true":
        print("✅ Self-reply test mode ENABLED")
    else:
        print("⚠️ Self-reply test mode DISABLED")
        
    # 4. Show latest logs
    print("\n📋 Latest Reply Guard logs:")
    try:
        with open("userbot/logs/userbot_reply_guard.log", "r") as f:
            lines = f.readlines()[-3:]
        for line in lines:
            print(f"   {line.strip()}")
    except:
        print("   (No log file found)")
        
    print("\n" + "="*50)
    print("🎯 VERIFICATION SUMMARY:")
    print("   • Userbot Process: ✅ RUNNING")
    print("   • Database: ✅ CONNECTED")
    print("   • Rules: ✅ ACTIVE")
    print(f"   • Self-Reply Mode: {'✅ ENABLED' if env_vars.get('ALLOW_SELF_REPLY_FOR_TESTING', 'false').lower() == 'true' else '⚠️ DISABLED'}")
    print("\n💡 TO TEST REPLY GUARD:")
    print("   1. Use different Telegram account")
    print("   2. Send 'zazizu' to group -1002406400543")
    print("   3. Expect auto-reply: 'ini adalah balasan123!#%5678'")
    print("\n🔧 TO DEBUG:")
    print("   • Monitor: tail -f userbot/logs/userbot_reply_guard.log")
    print("   • Test: python3 activate_env.py tests/target_group_test.py")
    print("="*50)

if __name__ == "__main__":
    quick_verify()