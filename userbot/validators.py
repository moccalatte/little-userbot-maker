"""
Validators for subscription and session health monitoring
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from telethon import TelegramClient
from telethon.errors import AuthKeyUnregisteredError, PhoneNumberBannedError
try:
    from .database import Database
except ImportError:
    from database import Database

logger = logging.getLogger(__name__)


class SubscriptionValidator:
    """Validates user subscriptions and manages subscription status"""
    
    def __init__(self, database: Database):
        self.db = database
    
    def is_subscription_active(self, user_id: int) -> bool:
        """
        Check if user has active subscription
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            bool: True if subscription is active and not expired
        """
        try:
            query = """
                SELECT status_subscription, tanggal_subs_selesai
                FROM users 
                WHERE id = %s
            """
            
            result = self.db.adapter.execute_one(query, (user_id,))
            
            if not result:
                logger.warning(f"User {user_id} not found in database")
                return False
            
            status, end_date = result["status_subscription"], result["tanggal_subs_selesai"]
            
            # Check status
            if status != 'active':
                logger.debug(f"User {user_id} subscription status: {status}")
                return False
            
            # Check expiry date
            if end_date:
                if isinstance(end_date, str):
                    # Parse string date
                    try:
                        end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                    except ValueError:
                        logger.error(f"Invalid date format for user {user_id}: {end_date}")
                        return False
                
                # Ensure timezone awareness
                if end_date.tzinfo is None:
                    end_date = end_date.replace(tzinfo=timezone.utc)
                
                current_time = datetime.now(timezone.utc)
                
                if current_time > end_date:
                    logger.info(f"User {user_id} subscription expired on {end_date}")
                    # Auto-update status to expired
                    self._update_subscription_status(user_id, 'expired')
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking subscription for user {user_id}: {e}")
            return False
    
    def _update_subscription_status(self, user_id: int, status: str):
        """Update user subscription status"""
        try:
            query = """
                UPDATE users 
                SET status_subscription = %s, updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """
            self.db.adapter.execute(query, (status, user_id))
            self.db.adapter.commit()
            logger.info(f"Updated user {user_id} subscription status to: {status}")
        except Exception as e:
            logger.error(f"Error updating subscription status for user {user_id}: {e}")
    
    def get_subscription_info(self, user_id: int) -> Dict:
        """Get detailed subscription information"""
        try:
            query = """
                SELECT 
                    username, tipe_paket_subs, status_subscription,
                    tanggal_subs_dimulai, tanggal_subs_selesai,
                    created_at, updated_at
                FROM users 
                WHERE id = %s
            """
            
            result = self.db.adapter.execute_one(query, (user_id,))
            
            if not result:
                return {}
            
            return {
                'user_id': user_id,
                'username': result["username"],
                'package_type': result["tipe_paket_subs"],
                'status': result["status_subscription"],
                'start_date': result["tanggal_subs_dimulai"],
                'end_date': result["tanggal_subs_selesai"],
                'created_at': result["created_at"],
                'updated_at': result["updated_at"],
                'is_active': self.is_subscription_active(user_id)
            }
            
        except Exception as e:
            logger.error(f"Error getting subscription info for user {user_id}: {e}")
            return {}
    
    def get_active_subscriptions_count(self) -> int:
        """Get count of active subscriptions"""
        try:
            query = """
                SELECT COUNT(*) FROM users 
                WHERE status_subscription = 'active' 
                AND (tanggal_subs_selesai IS NULL OR tanggal_subs_selesai > CURRENT_TIMESTAMP)
            """
            result = self.db.adapter.execute_one(query)
            return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Error counting active subscriptions: {e}")
            return 0


class SessionHealthValidator:
    """Validates session health and manages client connections"""
    
    def __init__(self, database: Database):
        self.db = database
        self.subscription_validator = SubscriptionValidator(database)
    
    async def validate_client_health(self, client: TelegramClient, user_id: int) -> Tuple[bool, str]:
        """
        Validate if a Telegram client is healthy and functional
        
        Args:
            client: TelegramClient instance
            user_id: User ID associated with the client
            
        Returns:
            Tuple[bool, str]: (is_healthy, reason)
        """
        try:
            # Check if subscription is still active
            if not self.subscription_validator.is_subscription_active(user_id):
                return False, "Subscription expired or inactive"
            
            # Check if client is connected
            if not client.is_connected():
                try:
                    await client.connect()
                except Exception as e:
                    return False, f"Failed to connect: {str(e)}"
            
            # Test authorization by getting self info
            try:
                me = await client.get_me()
                if not me:
                    return False, "Failed to get user info - unauthorized"
                
                # Update session metadata with account info
                self._update_session_metadata(user_id, {
                    'account_id': me.id,
                    'username': me.username,
                    'phone': me.phone,
                    'last_health_check': datetime.now(timezone.utc).isoformat()
                })
                
                return True, "Client is healthy"
                
            except AuthKeyUnregisteredError:
                return False, "Session expired - auth key unregistered"
            except PhoneNumberBannedError:
                return False, "Phone number banned by Telegram"
            except Exception as e:
                return False, f"Authorization test failed: {str(e)}"
                
        except Exception as e:
            logger.error(f"Error validating client health for user {user_id}: {e}")
            return False, f"Health check error: {str(e)}"
    
    def _update_session_metadata(self, user_id: int, metadata: Dict):
        """Update session metadata with health check info"""
        try:
            # Get existing metadata
            query = "SELECT metadata FROM sessions WHERE user_id = %s"
            result = self.db.adapter.execute_one(query, (user_id,))
            
            existing_metadata = {}
            if result and result["metadata"]:
                import json
                try:
                    existing_metadata = json.loads(result["metadata"])
                except json.JSONDecodeError:
                    pass
            
            # Merge metadata
            existing_metadata.update(metadata)
            
            # Update database
            import json
            update_query = """
                UPDATE sessions 
                SET metadata = %s, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = %s
            """
            self.db.adapter.execute(update_query, (json.dumps(existing_metadata), user_id))
            self.db.adapter.commit()
            
        except Exception as e:
            logger.error(f"Error updating session metadata for user {user_id}: {e}")
    
    async def validate_all_sessions(self, active_clients: Dict[int, TelegramClient]) -> Dict:
        """
        Validate health of all active sessions
        
        Args:
            active_clients: Dict of user_id -> TelegramClient
            
        Returns:
            Dict with validation results and statistics
        """
        results = {
            'total_clients': len(active_clients),
            'healthy_clients': 0,
            'unhealthy_clients': 0,
            'clients_to_remove': [],
            'validation_details': {}
        }
        
        for user_id, client in active_clients.items():
            is_healthy, reason = await self.validate_client_health(client, user_id)
            
            results['validation_details'][user_id] = {
                'healthy': is_healthy,
                'reason': reason,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            if is_healthy:
                results['healthy_clients'] += 1
            else:
                results['unhealthy_clients'] += 1
                results['clients_to_remove'].append(user_id)
                logger.warning(f"Client {user_id} marked for removal: {reason}")
        
        return results
    
    def get_session_statistics(self) -> Dict:
        """Get comprehensive session statistics"""
        try:
            stats = {}
            
            # Total sessions
            query = "SELECT COUNT(*) as count FROM sessions"
            result = self.db.adapter.execute_one(query)
            stats['total_sessions'] = result["count"] if result else 0
            
            # Sessions by encryption status
            query = "SELECT encrypted, COUNT(*) as count FROM sessions GROUP BY encrypted"
            results = self.db.adapter.execute(query)
            stats['encrypted_sessions'] = 0
            stats['unencrypted_sessions'] = 0
            
            for row in results:
                if row["encrypted"]:
                    stats['encrypted_sessions'] = row["count"]
                else:
                    stats['unencrypted_sessions'] = row["count"]
            
            # Active subscriptions with sessions
            query = """
                SELECT COUNT(DISTINCT s.user_id) 
                FROM sessions s
                JOIN users u ON s.user_id = u.id
                WHERE u.status_subscription = 'active'
                AND (u.tanggal_subs_selesai IS NULL OR u.tanggal_subs_selesai > CURRENT_TIMESTAMP)
            """
            result = self.db.adapter.execute_one(query)
            stats['active_sessions_with_valid_subscription'] = result["count"] if result else 0
            
            # Recent sessions (last 24 hours)
            query = """
                SELECT COUNT(*) FROM sessions 
                WHERE created_at > CURRENT_TIMESTAMP - INTERVAL '24 hours'
            """
            result = self.db.adapter.execute_one(query)
            stats['recent_sessions_24h'] = result["count"] if result else 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting session statistics: {e}")
            return {}


class SystemHealthMonitor:
    """Overall system health monitoring"""
    
    def __init__(self, database: Database):
        self.db = database
        self.subscription_validator = SubscriptionValidator(database)
        self.session_validator = SessionHealthValidator(database)
    
    async def get_system_health_report(self, active_clients: Dict[int, TelegramClient]) -> Dict:
        """Generate comprehensive system health report"""
        
        report = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'database_status': 'unknown',
            'subscription_stats': {},
            'session_stats': {},
            'client_validation': {},
            'recommendations': []
        }
        
        try:
            # Test database connectivity
            self.db.adapter.execute_one("SELECT 1")
            report['database_status'] = 'healthy'
        except Exception as e:
            report['database_status'] = f'error: {str(e)}'
            report['recommendations'].append('Check database connection')
        
        # Get subscription statistics
        try:
            report['subscription_stats'] = {
                'active_count': self.subscription_validator.get_active_subscriptions_count(),
                'total_users': self._get_total_users_count()
            }
        except Exception as e:
            logger.error(f"Error getting subscription stats: {e}")
            report['recommendations'].append('Check subscription data integrity')
        
        # Get session statistics
        try:
            report['session_stats'] = self.session_validator.get_session_statistics()
        except Exception as e:
            logger.error(f"Error getting session stats: {e}")
            report['recommendations'].append('Check session data integrity')
        
        # Validate active clients
        if active_clients:
            try:
                report['client_validation'] = await self.session_validator.validate_all_sessions(active_clients)
                
                # Add recommendations based on validation
                if report['client_validation']['unhealthy_clients'] > 0:
                    report['recommendations'].append(f"Remove {report['client_validation']['unhealthy_clients']} unhealthy clients")
                
                if report['client_validation']['healthy_clients'] == 0 and len(active_clients) > 0:
                    report['recommendations'].append('All clients are unhealthy - investigate system issues')
                    
            except Exception as e:
                logger.error(f"Error validating clients: {e}")
                report['recommendations'].append('Client validation failed - check session validity')
        
        return report
    
    def _get_total_users_count(self) -> int:
        """Get total number of users"""
        try:
            query = "SELECT COUNT(*) as count FROM users"
            result = self.db.adapter.execute_one(query)
            return result["count"] if result else 0
        except Exception as e:
            logger.error(f"Error counting total users: {e}")
            return 0