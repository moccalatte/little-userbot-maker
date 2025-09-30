"""Bot wizard subscription handler untuk manage user subscriptions."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from telegram import Update
from telegram.ext import CallbackContext

try:
    from .storage import Database
    from .config import load_bot_settings
except ImportError:
    from storage import Database
    from config import load_bot_settings

logger = logging.getLogger("bot.subscription_handler")


class SubscriptionManager:
    """Manager untuk handle user subscriptions di bot wizard."""
    
    def __init__(self):
        self.database = Database()
        self.settings = load_bot_settings()
        
    def create_subscription(
        self, 
        user_id: int, 
        username: Optional[str],
        first_name: Optional[str],
        last_name: Optional[str],
        tipe_paket: str, 
        duration_days: int = 30
    ) -> bool:
        """Create new subscription untuk user."""
        try:
            # Ensure user exists first in bot database
            self.database.ensure_user(user_id, username, first_name, last_name)
            
            # Calculate subscription dates
            tanggal_mulai = datetime.now()
            tanggal_selesai = tanggal_mulai + timedelta(days=duration_days)
            
            # Update subscription in userbot database  
            from userbot.database import Database as UserbotDB
            userbot_db = UserbotDB()
            
            # Ensure user exists in userbot database too
            userbot_db.ensure_user(user_id, username, first_name, last_name)
            
            success = userbot_db.update_user_subscription(
                user_id=user_id,
                tipe_paket=tipe_paket,
                tanggal_mulai=tanggal_mulai.isoformat(),
                tanggal_selesai=tanggal_selesai.isoformat(),
                status='active'
            )
            
            if success:
                logger.info(f"Created {tipe_paket} subscription for user {user_id} ({duration_days} days)")
                
                # Log admin action if this was done by admin
                if hasattr(self, '_admin_user_id'):
                    userbot_db.log_admin_action(
                        admin_user_id=self._admin_user_id,
                        action="create_subscription",
                        target_user_id=user_id,
                        details={
                            "tipe_paket": tipe_paket,
                            "duration_days": duration_days,
                            "tanggal_mulai": tanggal_mulai.isoformat(),
                            "tanggal_selesai": tanggal_selesai.isoformat()
                        }
                    )
                    
            return success
            
        except Exception as e:
            logger.error(f"Error creating subscription for user {user_id}: {e}")
            return False
            
    def check_subscription_status(self, user_id: int) -> Dict[str, Any]:
        """Check current subscription status untuk user."""
        try:
            from userbot.database import Database as UserbotDB
            userbot_db = UserbotDB()
            
            sub_info = userbot_db.get_user_subscription(user_id)
            if not sub_info:
                return {
                    "exists": False,
                    "active": False,
                    "message": "No subscription found"
                }
                
            is_active = userbot_db.is_subscription_active(user_id)
            
            # Calculate days remaining
            days_remaining = 0
            if sub_info['tanggal_subs_selesai']:
                end_date = sub_info['tanggal_subs_selesai']
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                days_remaining = max(0, (end_date - datetime.now()).days)
                
            return {
                "exists": True,
                "active": is_active,
                "tipe_paket": sub_info['tipe_paket_subs'],
                "status": sub_info['status_subscription'],
                "tanggal_mulai": sub_info['tanggal_subs_dimulai'],
                "tanggal_selesai": sub_info['tanggal_subs_selesai'],
                "days_remaining": days_remaining,
                "message": f"Subscription: {sub_info['tipe_paket_subs']} ({'Active' if is_active else 'Inactive'}) - {days_remaining} days remaining"
            }
            
        except Exception as e:
            logger.error(f"Error checking subscription status for user {user_id}: {e}")
            return {
                "exists": False,
                "active": False,
                "message": f"Error checking subscription: {str(e)}"
            }
            
    def get_subscription_packages(self) -> Dict[str, Dict[str, Any]]:
        """Get available subscription packages."""
        return {
            "trial": {
                "name": "Trial",
                "duration_days": 3,
                "price": 0,
                "features": ["Basic userbot features", "Limited to 3 days"]
            },
            "basic": {
                "name": "Basic",
                "duration_days": 30,
                "price": 50000,
                "features": ["All userbot features", "30 days access", "Email support"]
            },
            "premium": {
                "name": "Premium",
                "duration_days": 90,
                "price": 120000,
                "features": ["All userbot features", "90 days access", "Priority support", "Advanced features"]
            }
        }
        
    async def handle_payment_success(
        self, 
        update: Update, 
        context: CallbackContext, 
        user_id: int, 
        package_type: str
    ) -> bool:
        """Handle successful payment dan create subscription."""
        try:
            packages = self.get_subscription_packages()
            if package_type not in packages:
                await update.message.reply_text("❌ Invalid package type")
                return False
                
            package = packages[package_type]
            user = update.effective_user
            
            success = self.create_subscription(
                user_id=user_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                tipe_paket=package_type,
                duration_days=package['duration_days']
            )
            
            if success:
                await update.message.reply_text(
                    f"🎉 Subscription activated!\n\n"
                    f"📦 Package: {package['name']}\n"
                    f"⏰ Duration: {package['duration_days']} days\n\n"
                    f"You can now create your userbot session!"
                )
                return True
            else:
                await update.message.reply_text("❌ Failed to activate subscription. Please contact admin.")
                return False
                
        except Exception as e:
            logger.error(f"Error handling payment success: {e}")
            await update.message.reply_text("❌ Error processing payment. Please contact admin.")
            return False
            
    def set_admin_context(self, admin_user_id: int):
        """Set admin context untuk logging purposes."""
        self._admin_user_id = admin_user_id


def create_subscription_manager() -> SubscriptionManager:
    """Factory function untuk create subscription manager."""
    return SubscriptionManager()