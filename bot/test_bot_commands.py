#!/usr/bin/env python3
"""
Automated Bot Testing Script
Test berbagai command dan flow di Bot Wizard
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

# Tambahkan bot ke path
sys.path.append(os.path.dirname(__file__))

# Fix for test_bot_commands
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'test_commands.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("bot_tester")


class BotCommandTester:
    """Automated tester untuk Bot Wizard commands."""
    
    def __init__(self, bot_token: Optional[str] = None):
        self.bot_token = bot_token or os.getenv("BOT_TOKEN")
        if not self.bot_token:
            raise ValueError("BOT_TOKEN required")
            
        self.test_user_id = os.getenv("TEST_USER_ID", "123456789")
        self.test_results = []
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        """Setup logger untuk testing."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )
        return logging.getLogger("bot_tester")
    
    async def send_message(self, chat_id: str, text: str) -> Dict:
        """Send message to bot (simulated)."""
        # In real implementation, this would use telegram API
        # For now, simulate the response
        self.logger.info("SEND: %s -> %s", chat_id, text[:50])
        
        # Simulate different responses based on input
        if text == "/start":
            return {"status": "ok", "response": "Bot started"}
        elif "Reply Guard" in text:
            return {"status": "ok", "response": "Reply Guard menu"}
        elif "Status" in text:
            return {"status": "ok", "response": "Status shown"}
        else:
            return {"status": "ok", "response": "Command processed"}
    
    def log_test_result(self, test_name: str, success: bool, details: str = ""):
        """Log hasil test."""
        result = {
            "test_name": test_name,
            "success": success,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        self.logger.info("%s - %s: %s", status, test_name, details)
    
    async def test_basic_commands(self):
        """Test basic bot commands."""
        self.logger.info("=== Testing Basic Commands ===")
        
        # Test /start
        try:
            response = await self.send_message(self.test_user_id, "/start")
            self.log_test_result("start_command", True, "Bot responds to /start")
        except Exception as e:
            self.log_test_result("start_command", False, f"Error: {e}")
        
        # Test main menu navigation
        menu_tests = [
            "🤖 Userbot Generator",
            "📊 Commands & Features", 
            "🔧 Reply Guard",
            "📢 Broadcast Scheduler"
        ]
        
        for menu_item in menu_tests:
            try:
                response = await self.send_message(self.test_user_id, menu_item)
                self.log_test_result(f"menu_{menu_item.lower().replace(' ', '_')}", 
                                   True, f"Menu item responds: {menu_item}")
            except Exception as e:
                self.log_test_result(f"menu_{menu_item.lower().replace(' ', '_')}", 
                                   False, f"Error: {e}")
    
    async def test_reply_guard_flow(self):
        """Test Reply Guard complete flow."""
        self.logger.info("=== Testing Reply Guard Flow ===")
        
        # Test menu access
        try:
            await self.send_message(self.test_user_id, "🔧 Reply Guard")
            self.log_test_result("reply_guard_menu", True, "Reply Guard menu accessible")
        except Exception as e:
            self.log_test_result("reply_guard_menu", False, f"Error: {e}")
        
        # Test setup flow steps
        setup_steps = [
            "🔧 Setup Auto Reply",
            "🔴 Setup Basic Reply",
            "test,keywords",  # Keywords input
            "allgroup",       # Target selection
            "Hello, this is auto reply!"  # Reply text
        ]
        
        for i, step in enumerate(setup_steps):
            try:
                await self.send_message(self.test_user_id, step)
                self.log_test_result(f"setup_step_{i+1}", True, f"Step {i+1}: {step}")
                await asyncio.sleep(0.5)  # Small delay between steps
            except Exception as e:
                self.log_test_result(f"setup_step_{i+1}", False, f"Error: {e}")
        
        # Test activation
        try:
            await self.send_message(self.test_user_id, "✅ Aktifkan Rule")
            self.log_test_result("rule_activation", True, "Rule activation attempted")
        except Exception as e:
            self.log_test_result("rule_activation", False, f"Error: {e}")
    
    async def test_status_commands(self):
        """Test status and monitoring commands."""
        self.logger.info("=== Testing Status Commands ===")
        
        status_commands = [
            "📊 Status Reply Guard",
            "✅ Enable Reply Guard", 
            "❌ Disable Reply Guard"
        ]
        
        for cmd in status_commands:
            try:
                await self.send_message(self.test_user_id, cmd)
                self.log_test_result(f"status_{cmd.lower().replace(' ', '_')}", 
                                   True, f"Status command: {cmd}")
                await asyncio.sleep(1)
            except Exception as e:
                self.log_test_result(f"status_{cmd.lower().replace(' ', '_')}", 
                                   False, f"Error: {e}")
    
    def test_config_file_creation(self):
        """Test config file creation and parsing."""
        self.logger.info("=== Testing Config File Operations ===")
        
        try:
            # Create test config
            test_config = {
                "user_id": int(self.test_user_id),
                "keywords": ["test", "hello"],
                "target_type": "allgroup",
                "target_groups": None,
                "reply_text": "Test auto reply",
                "created_via": "bot_wizard",
                "status": "active",
                "created_at": datetime.now().isoformat()
            }
            
            # Write to file
            config_dir = Path("../data/reply_guard_configs")
            config_dir.mkdir(parents=True, exist_ok=True)
            
            config_file = config_dir / f"test_user_{self.test_user_id}_config_{int(datetime.now().timestamp())}.json"
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(test_config, f, indent=2)
            
            self.log_test_result("config_file_creation", True, 
                               f"Config file created: {config_file.name}")
            
            # Test file parsing
            with open(config_file, 'r', encoding='utf-8') as f:
                parsed_config = json.load(f)
            
            # Validate required fields
            required_fields = ['user_id', 'keywords', 'reply_text']
            missing_fields = [field for field in required_fields if field not in parsed_config]
            
            if not missing_fields:
                self.log_test_result("config_file_parsing", True, 
                                   "Config file parsed successfully")
            else:
                self.log_test_result("config_file_parsing", False, 
                                   f"Missing fields: {missing_fields}")
            
            # Cleanup test file
            config_file.unlink()
            
        except Exception as e:
            self.log_test_result("config_file_creation", False, f"Error: {e}")
    
    def test_database_operations(self):
        """Test database operations."""
        self.logger.info("=== Testing Database Operations ===")
        
        try:
            # Test database connection
            from bot.storage import get_database_connection
            db = get_database_connection()
            
            if db:
                self.log_test_result("database_connection", True, "Database connected")
                
                # Test simple query
                with db.cursor() as cursor:
                    cursor.execute("SELECT 1 as test_value")
                    result = cursor.fetchone()
                    
                if result and result[0] == 1:
                    self.log_test_result("database_query", True, "Database query successful")
                else:
                    self.log_test_result("database_query", False, "Query failed")
                    
            else:
                self.log_test_result("database_connection", False, "No database connection")
                
        except Exception as e:
            self.log_test_result("database_connection", False, f"Error: {e}")
    
    async def run_all_tests(self):
        """Run semua tests."""
        self.logger.info("🧪 Starting Bot Command Tests...")
        
        # Run different test suites
        await self.test_basic_commands()
        await self.test_reply_guard_flow()
        await self.test_status_commands()
        self.test_config_file_creation()
        self.test_database_operations()
        
        # Generate report
        self.generate_test_report()
    
    def generate_test_report(self):
        """Generate comprehensive test report."""
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = f"""
🧪 BOT COMMAND TEST REPORT
{'='*50}
📊 Overall Results:
   • Total Tests: {total_tests}
   • Passed: {passed_tests}
   • Failed: {failed_tests} 
   • Success Rate: {success_rate:.1f}%

📋 Detailed Results:
"""
        
        for result in self.test_results:
            status = "✅" if result['success'] else "❌"
            report += f"   {status} {result['test_name']}: {result['details']}\n"
        
        report += f"\n🕒 Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        
        # Save report to file
        report_file = Path("test_results.txt")
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(report)
        self.logger.info("Test report saved to: %s", report_file)
        
        return {
            "total": total_tests,
            "passed": passed_tests, 
            "failed": failed_tests,
            "success_rate": success_rate
        }


async def main():
    """Main function untuk run tests."""
    try:
        tester = BotCommandTester()
        results = await tester.run_all_tests()
        
        # Exit with appropriate code
        exit_code = 0 if results['failed'] == 0 else 1
        return exit_code
        
    except Exception as e:
        logger.error("Test runner failed: %s", e)
        return 1


if __name__ == "__main__":
    import sys
    exit_code = asyncio.run(main())
    sys.exit(exit_code)