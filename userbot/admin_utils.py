"""Admin utility functions untuk Bot Wizard."""
from __future__ import annotations

import logging
import os
from typing import Dict, List, Optional

try:
    from .database import Database
except ImportError:
    from database import Database

logger = logging.getLogger("userbot.admin_utils")


class AdminManager:
    """Manager untuk admin functions di Bot Wizard."""
    
    def __init__(self, database: Database):
        self.database = database
        
    def validate_admin_access(self, user_id: int) -> dict[str, object]:
        """
        Validate admin access (from environment owner IDs or database admin).
        
        Returns:
            dict dengan admin info dan access status
        """
        try:
            # Check owner dari environment variable first
            owner_ids_env = os.getenv("OWNER_TELEGRAM_IDS") or os.getenv("ADMIN_TELEGRAM_IDS")
            is_owner = False
            
            if owner_ids_env:
                try:
                    owner_ids = [int(id_str.strip()) for id_str in owner_ids_env.split(',')]
                    is_owner = user_id in owner_ids
                except ValueError:
                    logger.warning("Invalid owner IDs format dalam environment")
            
            # Check database admin
            is_db_admin = self.database.is_admin(user_id)
            
            # User adalah admin jika owner dari env ATAU admin dari database
            has_access = is_owner or is_db_admin
            
            if not has_access:
                return {
                    "is_admin": False,
                    "can_access": False,
                    "error_message": "🚫 Access Denied: Anda bukan admin sistem."
                }
                
            return {
                "is_admin": True,
                "can_access": True,
                "error_message": None,
                "is_owner": is_owner,
                "is_db_admin": is_db_admin
            }
            
        except Exception as e:
            logger.exception("Error validating admin access untuk user %s", user_id)
            return {
                "is_admin": False,
                "can_access": False,
                "error_message": f"❌ Error validasi admin: {str(e)}"
            }
            
    def get_admin_dashboard(self, admin_user_id: int) -> dict[str, object]:
        """Get admin dashboard data."""
        try:
            # Validate admin access first
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            # Log admin access
            self.database.log_admin_action(admin_user_id, "view_dashboard")
            
            # Get system stats
            stats = self.database.get_system_stats()
            
            # Get recent admin logs
            recent_logs = self.database.get_admin_logs(10)
            
            # Get recent configs
            recent_configs = self.database.get_all_userbot_configs(10)
            
            return {
                "error": None,
                "stats": stats,
                "recent_logs": recent_logs,
                "recent_configs": recent_configs,
                "timestamp": stats["timestamp"]
            }
            
        except Exception as e:
            logger.exception("Error getting admin dashboard untuk admin %s", admin_user_id)
            return {"error": f"❌ Error loading dashboard: {str(e)}"}
            
    def search_users_admin(self, admin_user_id: int, query: str) -> dict[str, object]:
        """Search users (admin function)."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"], "users": []}
                
            # Log search action
            self.database.log_admin_action(
                admin_user_id, 
                "search_users", 
                details={"query": query}
            )
            
            # Search users
            users = self.database.search_users(query, 20)
            
            return {
                "error": None,
                "users": users,
                "query": query,
                "count": len(users)
            }
            
        except Exception as e:
            logger.exception("Error searching users untuk admin %s", admin_user_id)
            return {"error": f"❌ Error search: {str(e)}", "users": []}
            
    def get_user_details_admin(self, admin_user_id: int, target_user_id: int) -> dict[str, object]:
        """Get user details (admin function)."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            # Log view action
            self.database.log_admin_action(
                admin_user_id, 
                "view_user_details", 
                target_user_id=target_user_id
            )
            
            # Get user details
            user_details = self.database.get_user_details(target_user_id)
            
            if not user_details:
                return {"error": f"❌ User {target_user_id} tidak ditemukan"}
                
            return {
                "error": None,
                "user": user_details
            }
            
        except Exception as e:
            logger.exception("Error getting user details untuk admin %s", admin_user_id)
            return {"error": f"❌ Error: {str(e)}"}
            
    def manage_user_config_admin(
        self,
        admin_user_id: int,
        target_user_id: int,
        action: str,  # 'enable', 'disable', 'delete'
        feature_type: Optional[str] = None
    ) -> dict[str, object]:
        """Manage user config (admin function)."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            if action == "delete" and feature_type:
                # Delete specific config
                success = self.database.delete_userbot_config(target_user_id, feature_type)
                action_msg = f"delete_{feature_type}_config"
                result_msg = f"✅ Config {feature_type} untuk user {target_user_id} berhasil dihapus" if success else "❌ Config tidak ditemukan"
                
            elif action in ["enable", "disable"]:
                # Enable/disable config (need to get existing config first)
                configs = self.database.get_userbot_configs(target_user_id, feature_type)
                if not configs:
                    return {"error": f"❌ Config {feature_type} tidak ditemukan"}
                    
                config = configs[0]
                enabled = action == "enable"
                
                self.database.save_userbot_config(
                    user_id=target_user_id,
                    feature_type=feature_type,
                    config=config["config"],
                    enabled=enabled
                )
                
                action_msg = f"{action}_{feature_type}_config"
                result_msg = f"✅ Config {feature_type} untuk user {target_user_id} berhasil {'diaktifkan' if enabled else 'dinonaktifkan'}"
                success = True
                
            else:
                return {"error": f"❌ Action tidak valid: {action}"}
                
            # Log admin action
            self.database.log_admin_action(
                admin_user_id,
                action_msg,
                target_user_id=target_user_id,
                details={"feature_type": feature_type, "success": success}
            )
            
            return {
                "success": success,
                "message": result_msg
            }
            
        except Exception as e:
            logger.exception("Error managing user config untuk admin %s", admin_user_id)
            return {"error": f"❌ Error: {str(e)}"}
            
    def add_admin_user(self, current_admin_id: int, new_admin_id: int) -> dict[str, object]:
        """Add new admin user."""
        try:
            # Validate current admin access
            access = self.validate_admin_access(current_admin_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            # Add new admin
            success = self.database.add_admin_user(new_admin_id, created_by=current_admin_id)
            
            if success:
                # Log action
                self.database.log_admin_action(
                    current_admin_id,
                    "add_admin_user",
                    target_user_id=new_admin_id
                )
                
                return {
                    "success": True,
                    "message": f"✅ User {new_admin_id} berhasil ditambahkan sebagai admin"
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ User {new_admin_id} sudah menjadi admin"
                }
                
        except Exception as e:
            logger.exception("Error adding admin user")
            return {"error": f"❌ Error: {str(e)}"}
            
    def remove_admin_user(self, current_admin_id: int, target_admin_id: int) -> dict[str, object]:
        """Remove admin user."""
        try:
            # Validate current admin access
            access = self.validate_admin_access(current_admin_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            # Prevent self-removal
            if current_admin_id == target_admin_id:
                return {"error": "❌ Tidak bisa menghapus admin access diri sendiri"}
                
            # Remove admin
            success = self.database.remove_admin_user(target_admin_id)
            
            if success:
                # Log action
                self.database.log_admin_action(
                    current_admin_id,
                    "remove_admin_user",
                    target_user_id=target_admin_id
                )
                
                return {
                    "success": True,
                    "message": f"✅ Admin access untuk user {target_admin_id} berhasil dihapus"
                }
            else:
                return {
                    "success": False,
                    "message": f"❌ User {target_admin_id} bukan admin"
                }
                
        except Exception as e:
            logger.exception("Error removing admin user")
            return {"error": f"❌ Error: {str(e)}"}
            
    def get_all_configs_admin(self, admin_user_id: int, limit: int = 50) -> dict[str, object]:
        """Get all userbot configs (admin view)."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"], "configs": []}
                
            # Log action
            self.database.log_admin_action(admin_user_id, "view_all_configs")
            
            # Get configs
            configs = self.database.get_all_userbot_configs(limit)
            
            return {
                "error": None,
                "configs": configs,
                "count": len(configs)
            }
            
        except Exception as e:
            logger.exception("Error getting all configs untuk admin %s", admin_user_id)
            return {"error": f"❌ Error: {str(e)}", "configs": []}
            
    def get_admin_logs(self, admin_user_id: int, limit: int = 50) -> dict[str, object]:
        """Get admin logs."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"], "logs": []}
                
            # Get logs
            logs = self.database.get_admin_logs(limit)
            
            return {
                "error": None,
                "logs": logs,
                "count": len(logs)
            }
            
        except Exception as e:
            logger.exception("Error getting admin logs untuk admin %s", admin_user_id)
            return {"error": f"❌ Error: {str(e)}", "logs": []}
            
    def force_disable_user_features(self, admin_user_id: int, target_user_id: int) -> dict[str, object]:
        """Emergency: disable all features untuk user tertentu."""
        try:
            # Validate admin access
            access = self.validate_admin_access(admin_user_id)
            if not access["can_access"]:
                return {"error": access["error_message"]}
                
            # Get all user configs
            configs = self.database.get_userbot_configs(target_user_id)
            
            disabled_count = 0
            for config in configs:
                if config["enabled"]:
                    # Disable config
                    self.database.save_userbot_config(
                        user_id=target_user_id,
                        feature_type=config["feature_type"],
                        config=config["config"],
                        enabled=False
                    )
                    disabled_count += 1
                    
            # Log emergency action
            self.database.log_admin_action(
                admin_user_id,
                "emergency_disable_all",
                target_user_id=target_user_id,
                details={"disabled_count": disabled_count}
            )
            
            return {
                "success": True,
                "message": f"🚨 EMERGENCY: {disabled_count} features berhasil dinonaktifkan untuk user {target_user_id}",
                "disabled_count": disabled_count
            }
            
        except Exception as e:
            logger.exception("Error force disabling user features")
            return {"error": f"❌ Error: {str(e)}"}


def create_admin_manager(database_path) -> AdminManager:
    """Helper function untuk create admin manager instance."""
    from pathlib import Path
    database = Database.get_instance(Path(database_path))
    return AdminManager(database)