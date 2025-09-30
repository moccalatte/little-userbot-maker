#!/usr/bin/env python3
"""
Userbot Sync Service - Sinkronisasi config JSON ke userbot PostgreSQL database
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

# Setup paths
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger("userbot_sync")

# Change logging.basicConfig to use bot/logs/sync_service.log
LOG_DIR = os.path.join(os.path.dirname(__file__), 'logs')
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, 'sync_service.log')),
        logging.StreamHandler()
    ]
)


class UserbotSyncService:
    """Service untuk sync Reply Guard config dari JSON backup ke userbot database PostgreSQL."""
    
    def __init__(self, 
                 config_dir: str = "../data/reply_guard_configs",
                 database_url: Optional[str] = None,
                 check_interval: int = 10):
        self.config_dir = Path(config_dir).resolve()
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.check_interval = check_interval
        self.processed_configs = set()
        self.logger = self._setup_logger()
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger.info("UserbotSyncService initialized - config_dir: %s", self.config_dir)
        
    def _setup_logger(self):
        """Setup logger dengan format yang jelas."""
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        return logging.getLogger("userbot_sync")
    
    def _get_userbot_database_connection(self):
        """Get direct connection ke userbot PostgreSQL database."""
        try:
            import psycopg2
            import psycopg2.extras
            from urllib.parse import urlparse, parse_qs
            
            if not self.database_url:
                self.logger.error("DATABASE_URL not set")
                return None
            
            # Parse URL untuk fix format jika diperlukan    
            if '&' in self.database_url and 'channel_binding=' in self.database_url:
                # Fix untuk Neon URL dengan channel_binding parameter
                fixed_url = self.database_url.replace('&channel_binding=require', '')
                self.logger.debug("Fixed database URL format")
                database_url = fixed_url
            else:
                database_url = self.database_url
                
            conn = psycopg2.connect(
                database_url,
                cursor_factory=psycopg2.extras.RealDictCursor
            )
            conn.autocommit = True
            return conn
            
        except Exception as e:
            self.logger.error("Failed to connect to userbot database: %s", e)
            return None
    
    def scan_new_configs(self) -> List[Path]:
        """Scan untuk config JSON files yang belum diproses."""
        if not self.config_dir.exists():
            return []
            
        all_configs = list(self.config_dir.glob("user_*_config_*.json"))
        new_configs = [f for f in all_configs if str(f) not in self.processed_configs]
        
        # Sort by modification time (newer first)
        return sorted(new_configs, key=lambda x: x.stat().st_mtime, reverse=True)
    
    def parse_config_file(self, config_file: Path) -> Optional[Dict[str, Any]]:
        """Parse dan validate config JSON file."""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validate required fields
            required_fields = ['user_id', 'keywords', 'reply_text']
            missing = [field for field in required_fields if field not in config]
            
            if missing:
                self.logger.warning("Config file missing fields %s: %s", missing, config_file.name)
                return None
            
            # Ensure status is active
            if config.get('status', 'active') != 'active':
                self.logger.info("Skipping inactive config: %s", config_file.name)
                return None
                
            return config
            
        except Exception as e:
            self.logger.error("Failed to parse config file %s: %s", config_file, e)
            return None
    
    def sync_config_to_userbot(self, config: Dict[str, Any]) -> bool:
        """Sync config ke userbot PostgreSQL database."""
        try:
            conn = self._get_userbot_database_connection()
            if not conn:
                return False
            
            user_id = config['user_id']
            keywords = config.get('keywords', [])
            target_type = config.get('target_type', 'allgroup')
            target_groups = config.get('target_groups')
            reply_text = config.get('reply_text', '')
            
            # Convert ke format userbot
            include_keywords = keywords
            exclude_keywords = []
            regex_patterns = []
            targets = target_groups if target_type == 'specific' else None
            
            with conn.cursor() as cursor:
                # Clear existing rules untuk user ini (replace strategy)
                cursor.execute(
                    "DELETE FROM reply_guard_rules WHERE user_id = %s",
                    (user_id,)
                )
                
                # Insert new rule
                insert_query = """
                    INSERT INTO reply_guard_rules 
                    (user_id, include_json, exclude_json, regex_json, targets_json, reply_text, reply_image)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                """
                
                cursor.execute(insert_query, (
                    user_id,
                    json.dumps(include_keywords),
                    json.dumps(exclude_keywords),
                    json.dumps(regex_patterns),
                    json.dumps(targets) if targets else None,
                    reply_text,
                    None  # reply_image
                ))
                
                result = cursor.fetchone()
                rule_id = result['id'] if result else None
                
            self.logger.info(
                "Successfully synced config to userbot - User: %s, Rule ID: %s, Keywords: %s, Target: %s",
                user_id, rule_id, keywords, target_type
            )
            
            return True
            
        except Exception as e:
            self.logger.error("Failed to sync config to userbot database: %s", e)
            return False
        finally:
            if 'conn' in locals() and conn:
                conn.close()
    
    def mark_config_processed(self, config_file: Path, success: bool):
        """Mark config file sebagai sudah diproses."""
        self.processed_configs.add(str(config_file))
        
        if success:
            # Rename file ke .processed
            processed_file = config_file.with_suffix('.json.synced')
            try:
                config_file.rename(processed_file)
                self.logger.info("Config marked as synced: %s", processed_file.name)
            except Exception as e:
                self.logger.warning("Could not rename synced config file: %s", e)
        else:
            # Rename ke .failed untuk debugging
            failed_file = config_file.with_suffix('.json.failed')
            try:
                config_file.rename(failed_file)
                self.logger.warning("Config marked as failed: %s", failed_file.name)
            except Exception as e:
                self.logger.warning("Could not rename failed config file: %s", e)
    
    def process_config_file(self, config_file: Path) -> bool:
        """Process single config file."""
        self.logger.info("Processing config file: %s", config_file.name)
        
        config = self.parse_config_file(config_file)
        if not config:
            return False
        
        success = self.sync_config_to_userbot(config)
        self.mark_config_processed(config_file, success)
        
        return success
    
    async def run_sync_loop(self):
        """Main sync loop - monitor dan sync config files."""
        self.logger.info("Starting userbot sync loop (interval: %ss)", self.check_interval)
        
        iteration = 0
        while True:
            try:
                iteration += 1
                
                # Scan untuk config baru
                new_configs = self.scan_new_configs()
                
                if new_configs:
                    self.logger.info(
                        "Found %d new config files to sync (iteration %d)", 
                        len(new_configs), iteration
                    )
                    
                    synced_count = 0
                    for config_file in new_configs:
                        try:
                            if self.process_config_file(config_file):
                                synced_count += 1
                            
                            # Small delay between files
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            self.logger.error("Error processing %s: %s", config_file.name, e)
                    
                    self.logger.info("Sync completed: %d/%d configs synced successfully", 
                                   synced_count, len(new_configs))
                else:
                    # Log every 10 iterations when no work
                    if iteration % 10 == 0:
                        self.logger.debug("No new configs to sync (iteration %d)", iteration)
                
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
            self.logger.info("Userbot sync service stopped")


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Userbot Reply Guard Config Sync Service")
    parser.add_argument("--config-dir", default="../data/reply_guard_configs",
                       help="Directory containing JSON config files")
    parser.add_argument("--interval", type=int, default=10,
                       help="Check interval in seconds")
    parser.add_argument("--database-url",
                       help="PostgreSQL database URL (overrides environment)")
    
    args = parser.parse_args()
    
    service = UserbotSyncService(
        config_dir=args.config_dir,
        database_url=args.database_url,
        check_interval=args.interval
    )
    
    service.run()


if __name__ == "__main__":
    main()