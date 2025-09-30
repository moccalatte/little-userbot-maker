"""Monitoring dan debugging utilities untuk Bot Wizard."""

import json
import logging
import os
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


class AdvancedLogger:
    """Enhanced logging dengan monitoring features."""
    
    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.error_log_path = self.log_dir / "bot_errors.log"
        self.performance_log_path = self.log_dir / "bot_performance.log"
        
    def log_error_with_context(self, error: Exception, context: Dict[str, Any] = None):
        """Log error dengan detailed context untuk debugging."""
        error_entry = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
            "context": context or {},
            "python_version": os.sys.version,
            "process_id": os.getpid()
        }
        
        with open(self.error_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(error_entry, ensure_ascii=False, indent=2) + "\n")
            
    def log_performance_metric(self, operation: str, duration: float, details: Dict[str, Any] = None):
        """Log performance metrics untuk monitoring."""
        perf_entry = {
            "timestamp": datetime.now().isoformat(),
            "operation": operation,
            "duration_seconds": duration,
            "details": details or {}
        }
        
        with open(self.performance_log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(perf_entry, ensure_ascii=False) + "\n")


class BotHealthChecker:
    """Health check utilities untuk monitor bot status."""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.advanced_logger = AdvancedLogger()
        
    def check_database_connectivity(self) -> Dict[str, Any]:
        """Check database connectivity dan health."""
        try:
            # Import database with proper path handling
            import sys
            sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
            from userbot.wizard_utils import create_validator
            
            validator = create_validator(self.database_path)
            
            # Try basic database operation
            status = validator.validate_userbot_access(1)  # Test dengan dummy user_id
            
            return {
                "status": "healthy",
                "database_accessible": True,
                "error": None,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            error_details = {
                "status": "unhealthy", 
                "database_accessible": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "timestamp": datetime.now().isoformat()
            }
            
            self.advanced_logger.log_error_with_context(e, {
                "operation": "database_connectivity_check",
                "database_path": self.database_path
            })
            
            return error_details
    
    def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics untuk monitoring."""
        import psutil
        
        try:
            return {
                "cpu_usage": psutil.cpu_percent(interval=1),
                "memory_usage": psutil.virtual_memory()._asdict(),
                "disk_usage": psutil.disk_usage('/')._asdict(),
                "bot_process": {
                    "pid": os.getpid(),
                    "memory_info": psutil.Process().memory_info()._asdict()
                },
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            self.advanced_logger.log_error_with_context(e, {
                "operation": "system_stats_collection"
            })
            return {"error": str(e), "timestamp": datetime.now().isoformat()}
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent errors untuk debugging."""
        try:
            if not self.advanced_logger.error_log_path.exists():
                return []
                
            errors = []
            with open(self.advanced_logger.error_log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                
            # Get last N error entries (each error might span multiple lines)
            recent_lines = lines[-limit*10:]  # Rough estimate
            
            for line in recent_lines:
                try:
                    error_entry = json.loads(line.strip())
                    errors.append(error_entry)
                except json.JSONDecodeError:
                    continue
                    
            return errors[-limit:]  # Return last N entries
            
        except Exception as e:
            self.advanced_logger.log_error_with_context(e, {
                "operation": "get_recent_errors"
            })
            return [{"error": f"Failed to get recent errors: {str(e)}"}]


class ConfigValidator:
    """Validate Bot Wizard configurations."""
    
    @staticmethod
    def validate_environment() -> Dict[str, Any]:
        """Validate environment variables dan configuration."""
        validation_results = {
            "valid": True,
            "issues": [],
            "recommendations": [],
            "timestamp": datetime.now().isoformat()
        }
        
        # Check required environment variables
        required_vars = [
            "TELEGRAM_BOT_TOKEN", 
            "DATABASE_URL", 
            "SHARED_API_ID", 
            "SHARED_API_HASH"
        ]
        
        for var in required_vars:
            if not os.getenv(var):
                validation_results["valid"] = False
                validation_results["issues"].append(f"Missing required environment variable: {var}")
        
        # Check optional but recommended vars
        optional_vars = [
            "SECRET_KEY", 
            "OWNER_TELEGRAM_IDS", 
            "TELEGRAM_LOG_CHAT_ID"
        ]
        
        for var in optional_vars:
            if not os.getenv(var):
                validation_results["recommendations"].append(f"Consider setting {var} for enhanced functionality")
        
        # Validate database URL format
        database_url = os.getenv("DATABASE_URL")
        if database_url and not database_url.startswith(("postgresql://", "sqlite:///")):
            validation_results["issues"].append("DATABASE_URL format might be invalid (should start with postgresql:// or sqlite:///)")
        
        return validation_results


def create_debug_report(user_id: Optional[int] = None, include_system_stats: bool = True) -> Dict[str, Any]:
    """Create comprehensive debug report untuk troubleshooting."""
    database_path = "../data/userbotmaker.db"
    health_checker = BotHealthChecker(database_path)
    
    report = {
        "timestamp": datetime.now().isoformat(),
        "report_type": "bot_wizard_debug",
        "user_id": user_id,
        "environment_validation": ConfigValidator.validate_environment(),
        "database_health": health_checker.check_database_connectivity(),
        "recent_errors": health_checker.get_recent_errors(5)
    }
    
    if include_system_stats:
        report["system_stats"] = health_checker.get_system_stats()
    
    return report


def log_user_interaction(user_id: int, interaction_type: str, details: Dict[str, Any] = None):
    """Log user interaction untuk analytics dan debugging."""
    interaction_log = Path("logs") / "user_interactions.log"
    interaction_log.parent.mkdir(exist_ok=True)
    
    entry = {
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "interaction_type": interaction_type,
        "details": details or {}
    }
    
    with open(interaction_log, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# Decorator untuk automatic error logging
def with_error_logging(operation_name: str):
    """Decorator untuk automatic error logging dan monitoring."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            advanced_logger = AdvancedLogger()
            start_time = datetime.now()
            
            try:
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                
                advanced_logger.log_performance_metric(
                    operation_name, 
                    duration, 
                    {"function": func.__name__, "success": True}
                )
                
                return result
                
            except Exception as e:
                duration = (datetime.now() - start_time).total_seconds()
                
                advanced_logger.log_error_with_context(e, {
                    "operation": operation_name,
                    "function": func.__name__,
                    "args": str(args)[:200],  # Limit args length
                    "kwargs": str(kwargs)[:200],
                    "duration": duration
                })
                
                raise  # Re-raise the exception
                
        return wrapper
    return decorator