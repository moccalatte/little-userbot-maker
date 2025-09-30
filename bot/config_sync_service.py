#!/usr/bin/env python3
"""
Config Sync Service - Sinkronisasi Reply Guard config dari Bot Wizard ke Userbot
"""

import asyncio
import json
import logging
import os
import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional, List

# Add userbot to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

# Logging configuration
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'config_sync.log')),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("config_sync")


class ConfigSyncService:
    """Service untuk sync config JSON backup ke userbot database."""
    
    def __init__(self, 
                 config_dir: str = "../data/reply_guard_configs", 
                 check_interval: int = 30,
                 database_url: Optional[str] = None):
        self.config_dir = Path(config_dir).resolve()
        self.check_interval = check_interval
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.processed_files = set()
        self.logger = self._setup_logger()
        
        # Create config dir if not exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("ConfigSyncService initialized - watching: %s", self.config_dir)
    
    def _setup_logger(self) -> logging.Logger:
        """Setup logger dengan format yang jelas."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return logging.getLogger("config_sync")
    
    def _get_userbot_database(self):
        """Get userbot database connection."""
        try:
            from userbot.database import Database
            return Database.get_instance(self.database_url)
        except Exception as e:
            self.logger.error("Failed to connect to userbot database: %s", e)
            return None
    
    def scan_new_configs(self) -> List[Path]:
        """Scan untuk config files yang belum diproses."""
        if not self.config_dir.exists():
            return []
        
        all_configs = list(self.config_dir.glob("user_*_config_*.json"))
        new_configs = [f for f in all_configs if str(f) not in self.processed_files]
        
        # Sort by timestamp (newer first)
        return sorted(new_configs, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def parse_config_file(self, config_file: Path) -> Optional[Dict[str, Any]]:
        """Parse config JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate required fields
            if not all(key in data for key in ['user_id', 'keywords', 'reply_text']):
                self.logger.warning("Invalid config file (missing required fields): %s", config_file)
                return None
            
            return data
        except Exception as e:
            self.logger.error("Failed to parse config file %s: %s", config_file, e)
            return None
    
    def sync_config_to_userbot(self, config: Dict[str, Any]) -> bool:
        """Sync config ke userbot database."""
        try:
            db = self._get_userbot_database()
            if not db:
                return False
            
            user_id = config['user_id']
            keywords = config.get('keywords', [])
            target_groups = config.get('target_groups')
            reply_text = config.get('reply_text', '')
            
            # Convert to userbot format
            include = keywords
            exclude = []
            regex = []
            targets = target_groups
            
            # Add reply guard rule ke userbot database
            rule_id = db.add_reply_guard_rule(
                user_id=user_id,
                include=include,
                exclude=exclude,
                regex=regex,
                targets=targets,
                reply_text=reply_text,
                reply_image=None
            )
            
            self.logger.info(
                "Successfully synced config to userbot - User: %s, Rule ID: %s, Keywords: %s", 
                user_id, rule_id, keywords
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to sync config to userbot: %s", e)
            return False
    
    def process_config_file(self, config_file: Path) -> bool:
        """Process satu config file."""
        self.logger.info("Processing config file: %s", config_file.name)
        
        config = self.parse_config_file(config_file)
        if not config:
            return False
        
        # Check if config should be synced
        status = config.get('status', 'active')
        if status != 'active':
            self.logger.info("Skip inactive config: %s", config_file.name)
            self.processed_files.add(str(config_file))
            return True
        
        # Sync to userbot
        success = self.sync_config_to_userbot(config)
        if success:
            self.processed_files.add(str(config_file))
            
            # Optionally rename file to mark as processed
            processed_file = config_file.with_suffix('.json.processed')
            try:
                config_file.rename(processed_file)
                self.logger.info("Marked as processed: %s", processed_file.name)
            except Exception as e:
                self.logger.warning("Could not rename processed file: %s", e)
        
        return success
    
    async def run_sync_loop(self):
        """Main sync loop."""
        self.logger.info("Starting config sync loop (interval: %ss)", self.check_interval)
        
        while True:
            try:
                # Scan for new configs
                new_configs = self.scan_new_configs()
                
                if new_configs:
                    self.logger.info("Found %d new config files to process", len(new_configs))
                    
                    for config_file in new_configs:
                        try:
                            self.process_config_file(config_file)
                            await asyncio.sleep(1)  # Small delay between processes
                        except Exception as e:
                            self.logger.error("Error processing %s: %s", config_file.name, e)
                
                # Wait for next check
                await asyncio.sleep(self.check_interval)
                
            except KeyboardInterrupt:
                self.logger.info("Sync service stopped by user")
                break
            except Exception as e:
                self.logger.error("Sync loop error: %s", e)
                await asyncio.sleep(5)  # Wait before retry
    
    def run(self):
        """Run the sync service."""
        try:
            asyncio.run(self.run_sync_loop())
        except KeyboardInterrupt:
            self.logger.info("Config sync service stopped")


async def main():
    """Main function untuk menjalankan sync service."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Reply Guard Config Sync Service")
    parser.add_argument("--config-dir", default="../data/reply_guard_configs", 
                       help="Directory containing JSON config files")
    parser.add_argument("--interval", type=int, default=30,
                       help="Check interval in seconds")
    parser.add_argument("--database-url", 
                       help="Database URL (overrides environment)")
    
    args = parser.parse_args()
    
    service = ConfigSyncService(
        config_dir=args.config_dir,
        check_interval=args.interval,
        database_url=args.database_url
    )
    
    service.run()


if __name__ == "__main__":
    asyncio.run(main())