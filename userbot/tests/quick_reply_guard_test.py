#!/usr/bin/env python3
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
    print("\n📊 Current configuration:")
    print("   • Keyword: Check via Bot Wizard (@lilwizardbot)")
    print("   • Target Group: -1002406400543")
    print("   • Self-reply: Disabled by default (security feature)")
    
    print("\n🧪 TO TEST:")
    print("   1. Use different Telegram account")
    print("   2. Send message with keyword to target group")
    print("   3. Watch for auto-reply")
    
    print("\n📋 LOGS:")
    print("   • tail -f userbot/logs/userbot_reply_guard.log")
    print("   • tail -f userbot/logs/userbot.log")
    
    print("\n🔧 ADMIN TEST:")
    print("   • python3 tests/admin_reply_guard_test.py")

if __name__ == "__main__":
    quick_test()
