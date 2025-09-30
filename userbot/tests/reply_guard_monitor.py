
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
            print("\n⏹️ Monitoring stopped by user")
            
    def check_status(self):
        """Check current status."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{timestamp}] Checking Reply Guard status...")
        
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
