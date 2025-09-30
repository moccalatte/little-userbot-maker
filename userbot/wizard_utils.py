"""Utility functions untuk Bot Wizard integration."""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

try:
    from .database import Database
except ImportError:
    from database import Database

logger = logging.getLogger("userbot.wizard_utils")


class UserbotValidator:
    """Validator untuk mengecek akses userbot di Bot Wizard."""
    
    def __init__(self, database: Database):
        self.database = database
        
    def validate_userbot_access(self, user_id: int) -> dict[str, object]:
        """
        Validate apakah user memiliki akses ke userbot features.
        
        Returns:
            dict dengan keys:
            - has_userbot: bool
            - session_count: int  
            - can_use_features: bool
            - error_message: str | None
        """
        try:
            # Check if user has any sessions
            has_userbot = self.database.is_userbot_active(user_id)
            
            if not has_userbot:
                return {
                    "has_userbot": False,
                    "session_count": 0,
                    "can_use_features": False,
                    "error_message": "❌ Anda belum memiliki userbot aktif. Silakan buat userbot terlebih dahulu melalui wizard."
                }
                
            # Get session count
            sessions = self.database.list_sessions(user_id)
            session_count = len(sessions)
            
            return {
                "has_userbot": True,
                "session_count": session_count,
                "can_use_features": True,
                "error_message": None
            }
            
        except Exception as e:
            logger.exception("Error validating userbot access untuk user %s", user_id)
            return {
                "has_userbot": False,
                "session_count": 0,
                "can_use_features": False,
                "error_message": f"❌ Terjadi error saat validasi: {str(e)}"
            }
            
    def get_user_features_status(self, user_id: int) -> dict[str, object]:
        """
        Get status semua features untuk user.
        
        Returns:
            dict dengan feature status dan configs
        """
        try:
            # Validate access first
            validation = self.validate_userbot_access(user_id)
            if not validation["can_use_features"]:
                return {
                    "error": validation["error_message"],
                    "features": {}
                }
                
            # Get current configs
            configs = self.database.get_userbot_configs(user_id)
            
            features = {}
            for config in configs:
                feature_type = config["feature_type"]
                features[feature_type] = {
                    "enabled": config["enabled"],
                    "config": config["config"],
                    "version": config["version"],
                    "updated_at": config["updated_at"]
                }
                
            return {
                "error": None,
                "features": features,
                "session_count": validation["session_count"]
            }
            
        except Exception as e:
            logger.exception("Error getting user features status untuk user %s", user_id)
            return {
                "error": f"❌ Terjadi error: {str(e)}",
                "features": {}
            }
            
    def save_feature_config(
        self,
        user_id: int,
        feature_type: str,
        config: dict,
        enabled: bool = True
    ) -> dict[str, object]:
        """
        Save feature config dari Bot Wizard dengan validasi.
        
        Returns:
            dict dengan result status
        """
        try:
            # Validate access first
            validation = self.validate_userbot_access(user_id)
            if not validation["can_use_features"]:
                return {
                    "success": False,
                    "error": validation["error_message"]
                }
                
            # Validate feature type
            valid_features = ["broadcast", "auto_reply", "group_management"]
            if feature_type not in valid_features:
                return {
                    "success": False,
                    "error": f"❌ Feature type tidak valid: {feature_type}. Valid: {', '.join(valid_features)}"
                }
                
            # Validate config based on feature type
            validation_result = self._validate_feature_config(feature_type, config)
            if not validation_result["valid"]:
                return {
                    "success": False,
                    "error": validation_result["error"]
                }
                
            # Save to database
            config_id = self.database.save_userbot_config(
                user_id=user_id,
                feature_type=feature_type,
                config=config,
                enabled=enabled
            )
            
            logger.info(
                "Feature config saved untuk user %s: feature=%s, config_id=%s, enabled=%s",
                user_id, feature_type, config_id, enabled
            )
            
            return {
                "success": True,
                "config_id": config_id,
                "message": f"✅ {feature_type.replace('_', ' ').title()} berhasil {'diaktifkan' if enabled else 'dinonaktifkan'}!"
            }
            
        except Exception as e:
            logger.exception("Error saving feature config untuk user %s", user_id)
            return {
                "success": False,
                "error": f"❌ Terjadi error: {str(e)}"
            }
            
    def _validate_feature_config(self, feature_type: str, config: dict) -> dict[str, object]:
        """Validate config berdasarkan feature type."""
        if feature_type == "broadcast":
            return self._validate_broadcast_config(config)
        elif feature_type == "auto_reply":
            return self._validate_reply_config(config)
        elif feature_type == "group_management":
            return self._validate_group_config(config)
        else:
            return {"valid": False, "error": "Feature type tidak dikenal"}
            
    def _validate_broadcast_config(self, config: dict) -> dict[str, object]:
        """Validate broadcast config."""
        required_fields = ["message", "interval_minutes", "targets"]
        
        for field in required_fields:
            if field not in config:
                return {"valid": False, "error": f"❌ Field wajib '{field}' tidak ada"}
                
        message = config.get("message", "").strip()
        if not message:
            return {"valid": False, "error": "❌ Message tidak boleh kosong"}
            
        try:
            interval = int(config.get("interval_minutes", 0))
            if interval < 5:
                return {"valid": False, "error": "❌ Interval minimal 5 menit"}
        except (ValueError, TypeError):
            return {"valid": False, "error": "❌ Interval harus berupa angka"}
            
        targets = config.get("targets", [])
        if not isinstance(targets, list) or len(targets) == 0:
            return {"valid": False, "error": "❌ Target groups tidak boleh kosong"}
            
        return {"valid": True, "error": None}
        
    def _validate_reply_config(self, config: dict) -> dict[str, object]:
        """Validate auto reply config."""
        required_fields = ["reply_text"]
        
        for field in required_fields:
            if field not in config:
                return {"valid": False, "error": f"❌ Field wajib '{field}' tidak ada"}
                
        reply_text = config.get("reply_text", "").strip()
        if not reply_text:
            return {"valid": False, "error": "❌ Reply text tidak boleh kosong"}
            
        # Optional validation for include/exclude/regex lists
        for field in ["include", "exclude", "regex"]:
            if field in config and not isinstance(config[field], list):
                return {"valid": False, "error": f"❌ Field '{field}' harus berupa list"}
                
        return {"valid": True, "error": None}
        
    def _validate_group_config(self, config: dict) -> dict[str, object]:
        """Validate group management config."""
        # For now, group management doesn't need specific config
        return {"valid": True, "error": None}
        
    def delete_feature_config(self, user_id: int, feature_type: str) -> dict[str, object]:
        """Delete feature config dengan validasi."""
        try:
            # Validate access first
            validation = self.validate_userbot_access(user_id)
            if not validation["can_use_features"]:
                return {
                    "success": False,
                    "error": validation["error_message"]
                }
                
            # Delete from database
            success = self.database.delete_userbot_config(user_id, feature_type)
            
            if success:
                logger.info("Feature config deleted untuk user %s: feature=%s", user_id, feature_type)
                return {
                    "success": True,
                    "message": f"✅ {feature_type.replace('_', ' ').title()} berhasil dihapus!"
                }
            else:
                return {
                    "success": False,
                    "error": f"❌ Config untuk {feature_type} tidak ditemukan"
                }
                
        except Exception as e:
            logger.exception("Error deleting feature config untuk user %s", user_id)
            return {
                "success": False,
                "error": f"❌ Terjadi error: {str(e)}"
            }


def is_owner_or_admin(user_id: int, database_path: str) -> bool:
    """Check if user is owner (from env) or admin (from database)."""
    try:
        # Check owner dari environment variable
        owner_ids_env = os.getenv("OWNER_TELEGRAM_IDS") or os.getenv("ADMIN_TELEGRAM_IDS")
        if owner_ids_env:
            try:
                owner_ids = [int(id_str.strip()) for id_str in owner_ids_env.split(',')]
                if user_id in owner_ids:
                    logger.info("User %s adalah owner dari environment", user_id)
                    return True
            except ValueError:
                logger.warning("Invalid OWNER_TELEGRAM_IDS format dalam environment")
        
        # Check admin dari database - fix path handling
        if str(database_path).endswith('.db'):
            database_url = f"sqlite:///{str(database_path)}"
        else:
            database_url = str(database_path)
            
        database = Database.get_instance(database_url)
        if database.is_admin(user_id):
            logger.info("User %s adalah admin dari database", user_id)
            return True
            
        return False
        
    except Exception as e:
        logger.exception("Error checking owner/admin status untuk user %s", user_id)
        return False


def get_shared_api_credentials() -> dict[str, str | int]:
    """Get shared API credentials dari environment."""
    api_id = os.getenv("SHARED_API_ID") or os.getenv("API_ID")
    api_hash = os.getenv("SHARED_API_HASH") or os.getenv("API_HASH")
    
    if not api_id or not api_hash:
        raise ValueError("SHARED_API_ID dan SHARED_API_HASH harus diset di environment variables")
        
    try:
        api_id = int(api_id)
    except ValueError:
        raise ValueError("SHARED_API_ID harus berupa angka")
        
    return {
        "api_id": api_id,
        "api_hash": api_hash
    }


def create_validator(database_path) -> UserbotValidator:
    """Helper function untuk membuat validator instance."""
    # For SQLite paths, convert to proper string format
    if isinstance(database_path, (str, Path)):
        if str(database_path).endswith('.db'):
            # SQLite database - convert to sqlite:// URL
            database_url = f"sqlite:///{str(database_path)}"
        else:
            # Assume it's already a database URL
            database_url = str(database_path)
    else:
        database_url = str(database_path)
        
    database = Database.get_instance(database_url)
    return UserbotValidator(database)
