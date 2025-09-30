"""Userbot session loader yang membaca active sessions dari database."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from telethon import TelegramClient
from telethon.sessions import StringSession

try:
    from .database import Database
    from .config import load_userbot_settings  
    from .encryption_utils import decrypt_session_string
except ImportError:
    from database import Database
    from config import load_userbot_settings
    from encryption_utils import decrypt_session_string

logger = logging.getLogger("userbot.session_loader")


class UserbotSessionManager:
    """Manager untuk load dan manage multiple userbot sessions dari database."""
    
    def __init__(self):
        self.database = Database()
        self.settings = load_userbot_settings()
        self.active_clients: Dict[int, TelegramClient] = {}
        
    def load_active_sessions(self) -> List[Dict[str, Any]]:
        """Load semua active userbot sessions dari database."""
        try:
            sessions = self.database.get_active_userbot_sessions()
            logger.info(f"Loaded {len(sessions)} active userbot sessions from database")
            return sessions
        except Exception as e:
            logger.error(f"Error loading sessions from database: {e}")
            return []
            
    def create_client_from_session(self, session_data: Dict[str, Any]) -> Optional[TelegramClient]:
        """Create TelegramClient dari session data."""
        try:
            user_id = session_data["user_id"]
            session_string = session_data["session_string"]
            encrypted = session_data["encrypted"]
            
            # Decrypt session jika encrypted
            if encrypted and self.settings.secret_key:
                try:
                    session_string = decrypt_session_string(session_string, self.settings.secret_key)
                except Exception as e:
                    logger.error(f"Failed to decrypt session for user {user_id}: {e}")
                    return None
            
            # Create client dengan shared API credentials
            api_id = self.settings.shared_api_id or self.settings.api_id
            api_hash = self.settings.shared_api_hash or self.settings.api_hash
            
            if not api_id or not api_hash:
                logger.error(f"Missing API credentials for user {user_id}")
                return None
                
            client = TelegramClient(
                StringSession(session_string),
                api_id=api_id,
                api_hash=api_hash,
                device_model=f"UserbotMaker-{session_data.get('tipe_paket_subs', 'free')}",
                system_version="1.0",
                app_version="1.0",
                lang_code="id",
                system_lang_code="id"
            )
            
            logger.info(f"Created client for user {user_id} ({session_data.get('username', 'N/A')})")
            return client
            
        except Exception as e:
            logger.error(f"Error creating client from session: {e}")
            return None
            
    async def start_userbot_client(self, client: TelegramClient, session_data: Dict[str, Any]) -> bool:
        """Start userbot client dengan validation."""
        try:
            await client.start()
            
            # Validate client
            me = await client.get_me()
            if not me:
                logger.error(f"Failed to get user info for session {session_data['session_id']}")
                return False
                
            user_id = session_data["user_id"]
            logger.info(f"Successfully started userbot for user {user_id} (@{me.username or 'N/A'})")
            
            # Store active client
            self.active_clients[user_id] = client
            return True
            
        except Exception as e:
            logger.error(f"Error starting userbot client: {e}")
            return False
            
    async def load_and_start_all_userbots(self) -> int:
        """Load dan start semua active userbot sessions."""
        sessions = self.load_active_sessions()
        started_count = 0
        
        for session_data in sessions:
            try:
                # Check if subscription is still valid
                user_id = session_data["user_id"]
                if not self.database.is_subscription_active(user_id):
                    logger.warning(f"Skipping inactive subscription for user {user_id}")
                    continue
                    
                # Create and start client
                client = self.create_client_from_session(session_data)
                if not client:
                    continue
                    
                success = await self.start_userbot_client(client, session_data)
                if success:
                    started_count += 1
                else:
                    await client.disconnect()
                    
            except Exception as e:
                logger.error(f"Error starting userbot for session {session_data.get('session_id')}: {e}")
                continue
                
        logger.info(f"Successfully started {started_count}/{len(sessions)} userbot clients")
        return started_count
        
    async def stop_userbot(self, user_id: int) -> bool:
        """Stop specific userbot client."""
        if user_id in self.active_clients:
            try:
                client = self.active_clients[user_id]
                await client.disconnect()
                del self.active_clients[user_id]
                logger.info(f"Stopped userbot for user {user_id}")
                return True
            except Exception as e:
                logger.error(f"Error stopping userbot for user {user_id}: {e}")
                return False
        return False
        
    async def stop_all_userbots(self) -> int:
        """Stop semua active userbot clients."""
        stopped_count = 0
        
        for user_id in list(self.active_clients.keys()):
            if await self.stop_userbot(user_id):
                stopped_count += 1
                
        logger.info(f"Stopped {stopped_count} userbot clients")
        return stopped_count
        
    def get_active_userbot_info(self) -> List[Dict[str, Any]]:
        """Get info tentang active userbot clients."""
        info = []
        
        for user_id, client in self.active_clients.items():
            try:
                # Get subscription info
                sub_info = self.database.get_user_subscription(user_id)
                if sub_info:
                    info.append({
                        "user_id": user_id,
                        "username": sub_info.get("username"),
                        "first_name": sub_info.get("first_name"),
                        "tipe_paket_subs": sub_info.get("tipe_paket_subs"),
                        "status_subscription": sub_info.get("status_subscription"),
                        "tanggal_subs_selesai": sub_info.get("tanggal_subs_selesai"),
                        "is_connected": client.is_connected(),
                    })
            except Exception as e:
                logger.error(f"Error getting info for userbot {user_id}: {e}")
                continue
                
        return info
        
    async def reload_userbot_sessions(self) -> int:
        """Reload userbot sessions dari database (untuk config changes)."""
        logger.info("Reloading userbot sessions from database...")
        
        # Stop existing clients
        await self.stop_all_userbots()
        
        # Load and start fresh
        return await self.load_and_start_all_userbots()


def create_session_manager() -> UserbotSessionManager:
    """Factory function untuk create session manager."""
    return UserbotSessionManager()