"""Helper functions untuk Bot Wizard dengan simplified setup."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, Optional

try:
    from .database import Database
    from .wizard_utils import get_shared_api_credentials, is_owner_or_admin
    from .admin_utils import create_admin_manager
except ImportError:
    from database import Database
    from wizard_utils import get_shared_api_credentials, is_owner_or_admin
    from admin_utils import create_admin_manager

logger = logging.getLogger("userbot.bot_wizard_helpers")


class BotWizardManager:
    """Manager untuk Bot Wizard operations dengan simplified setup."""
    
    def __init__(self, database_path: str = "../data/userbotmaker.db"):
        self.database_path = database_path
        self.database = Database.get_instance(Path(database_path))
        self.admin_manager = create_admin_manager(database_path)
        
    def check_user_access(self, user_id: int) -> dict[str, object]:
        """
        Check user access - owner gets full admin access, regular users need userbot.
        
        Returns:
            dict dengan access info dan next action
        """
        try:
            # Check if user is owner/admin (bypass payment)
            is_admin = is_owner_or_admin(user_id, self.database_path)
            
            if is_admin:
                return {
                    "access_type": "admin",
                    "can_use_features": True,
                    "needs_payment": False,
                    "message": "🛡️ Admin access - Full system control available"
                }
            
            # Regular user - check if has userbot
            has_userbot = self.database.is_userbot_active(user_id)
            
            if has_userbot:
                return {
                    "access_type": "user_with_userbot", 
                    "can_use_features": True,
                    "needs_payment": False,
                    "message": "🤖 You have active userbot - Features available"
                }
            
            # No userbot - needs to create one
            return {
                "access_type": "user_no_userbot",
                "can_use_features": False, 
                "needs_payment": True,
                "message": "💰 Payment required to create userbot"
            }
            
        except Exception as e:
            logger.exception("Error checking user access untuk user %s", user_id)
            return {
                "access_type": "error",
                "can_use_features": False,
                "needs_payment": True,
                "message": f"❌ Error: {str(e)}"
            }
            
    def create_userbot_session(
        self, 
        user_id: int, 
        session_string: str, 
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        encrypted: bool = True
    ) -> dict[str, object]:
        """
        Create userbot session with auto API credentials.
        
        Args:
            user_id: Telegram user ID
            session_string: Session string dari user
            username: Username (optional)
            first_name: First name (optional) 
            encrypted: Whether to encrypt session (default True)
        """
        try:
            # Get shared API credentials from environment
            api_creds = get_shared_api_credentials()
            
            # Ensure user exists
            self.database.ensure_user(user_id, username, first_name, None)
            
            # Get secret key for encryption if needed
            secret_key = os.getenv("SECRET_KEY")
            if encrypted and not secret_key:
                logger.warning("SECRET_KEY tidak ditemukan, session disimpan tanpa enkripsi")
                encrypted = False
                
            # Save session dengan shared API info
            metadata = {
                "api_id": api_creds["api_id"],
                "api_hash_preview": api_creds["api_hash"][:8] + "...",  # Don't store full hash
                "created_via": "bot_wizard",
                "auto_api": True
            }
            
            self.database.save_session(
                user_id=user_id,
                session_string=session_string,
                encrypted=encrypted,
                metadata=metadata
            )
            
            logger.info(
                "Session created untuk user %s via Bot Wizard (auto API: %s)", 
                user_id, api_creds["api_id"]
            )
            
            return {
                "success": True,
                "message": f"✅ Userbot berhasil dibuat dengan shared API {api_creds['api_id']}!",
                "api_id": api_creds["api_id"],
                "session_encrypted": encrypted
            }
            
        except ValueError as e:
            # API credentials error
            logger.error("API credentials error: %s", e)
            return {
                "success": False,
                "message": f"❌ Configuration error: {str(e)}",
                "error_type": "config_error"
            }
            
        except Exception as e:
            logger.exception("Error creating userbot session untuk user %s", user_id)
            return {
                "success": False,
                "message": f"❌ Error creating userbot: {str(e)}",
                "error_type": "system_error"
            }
            
    def get_user_dashboard(self, user_id: int) -> dict[str, object]:
        """Get user dashboard based on access level."""
        access = self.check_user_access(user_id)
        
        if access["access_type"] == "admin":
            # Admin dashboard
            dashboard = self.admin_manager.get_admin_dashboard(user_id)
            dashboard["access_type"] = "admin"
            return dashboard
            
        elif access["access_type"] == "user_with_userbot":
            # Regular user dashboard
            from .wizard_utils import UserbotValidator
            validator = UserbotValidator(self.database)
            
            status = validator.get_user_features_status(user_id)
            status["access_type"] = "user"
            return status
            
        else:
            # No access
            return {
                "access_type": access["access_type"],
                "error": access["message"],
                "features": {}
            }
            
    def setup_user_feature(
        self,
        user_id: int,
        feature_type: str,
        config: dict,
        enabled: bool = True
    ) -> dict[str, object]:
        """Setup user feature dengan access validation."""
        access = self.check_user_access(user_id)
        
        if not access["can_use_features"]:
            return {
                "success": False,
                "error": access["message"]
            }
            
        # Admin can setup for any user, regular users only for themselves
        if access["access_type"] == "admin":
            # Admin setup - use admin manager
            return self.admin_manager.save_feature_config(
                user_id, feature_type, config, enabled
            )
        else:
            # Regular user setup
            from .wizard_utils import UserbotValidator
            validator = UserbotValidator(self.database)
            
            result = validator.save_feature_config(
                user_id, feature_type, config, enabled
            )
            return result


def get_environment_setup_status() -> dict[str, object]:
    """Check if environment variables are properly configured."""
    status = {
        "ready": True,
        "issues": [],
        "config": {},
        "setup_instructions": "Add variables to /bot/.env file"
    }
    
    # Check API credentials
    try:
        api_creds = get_shared_api_credentials()
        status["config"]["api_configured"] = True
        status["config"]["api_id"] = api_creds["api_id"]
    except ValueError as e:
        status["ready"] = False
        status["issues"].append(f"Missing API Config in /bot/.env: {str(e)}")
        status["config"]["api_configured"] = False
        
    # Check owner/admin IDs
    owner_ids = os.getenv("OWNER_TELEGRAM_IDS") or os.getenv("ADMIN_TELEGRAM_IDS")
    if owner_ids:
        try:
            parsed_ids = [int(id_str.strip()) for id_str in owner_ids.split(',')]
            status["config"]["admin_ids"] = parsed_ids
            status["config"]["admin_configured"] = True
        except ValueError:
            status["ready"] = False
            status["issues"].append("Invalid OWNER_TELEGRAM_IDS format in /bot/.env")
            status["config"]["admin_configured"] = False
    else:
        status["ready"] = False
        status["issues"].append("OWNER_TELEGRAM_IDS not set in /bot/.env")
        status["config"]["admin_configured"] = False
        status["config"]["admin_ids"] = []
        
    # Check secret key
    secret_key = os.getenv("SECRET_KEY")
    status["config"]["secret_key_configured"] = bool(secret_key)
    if not secret_key:
        status["issues"].append("SECRET_KEY: Not configured in /bot/.env (sessions won't be encrypted)")
        
    return status


def create_bot_wizard_manager(database_path: str = "../data/userbotmaker.db") -> BotWizardManager:
    """Helper function untuk create BotWizardManager instance."""
    return BotWizardManager(database_path)