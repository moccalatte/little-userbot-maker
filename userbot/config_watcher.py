"""Config watcher untuk userbot - monitoring database changes dari Bot Wizard."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Optional

try:
    from .database import Database
except ImportError:
    from database import Database

logger = logging.getLogger("userbot.config_watcher")


@dataclass
class ConfigState:
    """Current config state per feature type."""
    version: int
    enabled: bool
    config: dict
    
    
class ConfigWatcher:
    """Watcher untuk monitoring config changes dari Bot Wizard."""
    
    def __init__(
        self,
        database: Database,
        user_id: int,
        check_interval: int = 30,
    ) -> None:
        self.database = database
        self.user_id = user_id
        self.check_interval = check_interval
        self._current_states: Dict[str, ConfigState] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._callbacks: Dict[str, list] = {
            "broadcast": [],
            "auto_reply": [],
            "group_management": [],
        }
        
    def register_callback(self, feature_type: str, callback) -> None:
        """Register callback untuk feature type tertentu."""
        if feature_type in self._callbacks:
            self._callbacks[feature_type].append(callback)
            logger.info("Callback registered untuk feature %s", feature_type)
        else:
            logger.warning("Unknown feature type: %s", feature_type)
            
    async def start(self) -> None:
        """Start config watcher."""
        if self._running:
            logger.warning("Config watcher sudah running")
            return
            
        self._running = True
        # Load initial state
        await self._load_current_states()
        
        # Start monitoring task
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("Config watcher started untuk user %s (interval: %ss)", self.user_id, self.check_interval)
        
    async def stop(self) -> None:
        """Stop config watcher."""
        if not self._running:
            return
            
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
                
        logger.info("Config watcher stopped untuk user %s", self.user_id)
        
    async def _load_current_states(self) -> None:
        """Load current config states from database."""
        try:
            configs = self.database.get_userbot_configs(self.user_id)
            for config in configs:
                feature_type = config["feature_type"]
                self._current_states[feature_type] = ConfigState(
                    version=config["version"],
                    enabled=config["enabled"],
                    config=config["config"]
                )
            logger.info("Loaded %s config states untuk user %s", len(configs), self.user_id)
        except Exception:
            logger.exception("Failed to load current config states")
            
    async def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        while self._running:
            try:
                await self._check_config_changes()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Error in config monitoring loop")
                await asyncio.sleep(5)  # Short delay on error
                
    async def _check_config_changes(self) -> None:
        """Check for config changes dan trigger callbacks."""
        try:
            current_configs = self.database.get_userbot_configs(self.user_id)
            
            for config in current_configs:
                feature_type = config["feature_type"]
                new_state = ConfigState(
                    version=config["version"],
                    enabled=config["enabled"],
                    config=config["config"]
                )
                
                current_state = self._current_states.get(feature_type)
                
                # Check if this is new or changed config
                if (current_state is None or 
                    current_state.version != new_state.version or
                    current_state.enabled != new_state.enabled):
                    
                    logger.info(
                        "Config change detected untuk %s: version %s→%s, enabled %s→%s",
                        feature_type,
                        current_state.version if current_state else "new",
                        new_state.version,
                        current_state.enabled if current_state else "new",
                        new_state.enabled
                    )
                    
                    # Update state
                    self._current_states[feature_type] = new_state
                    
                    # Trigger callbacks
                    await self._trigger_callbacks(feature_type, new_state, current_state)
                    
            # Check for deleted configs
            for feature_type in list(self._current_states.keys()):
                if not any(c["feature_type"] == feature_type for c in current_configs):
                    logger.info("Config deleted untuk feature %s", feature_type)
                    old_state = self._current_states.pop(feature_type)
                    await self._trigger_callbacks(feature_type, None, old_state)
                    
        except Exception:
            logger.exception("Error checking config changes")
            
    async def _trigger_callbacks(
        self, 
        feature_type: str, 
        new_state: Optional[ConfigState], 
        old_state: Optional[ConfigState]
    ) -> None:
        """Trigger registered callbacks untuk feature type."""
        callbacks = self._callbacks.get(feature_type, [])
        if not callbacks:
            logger.debug("No callbacks registered untuk feature %s", feature_type)
            return
            
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(feature_type, new_state, old_state)
                else:
                    callback(feature_type, new_state, old_state)
            except Exception:
                logger.exception("Error in callback untuk feature %s", feature_type)
                
    def get_current_config(self, feature_type: str) -> Optional[ConfigState]:
        """Get current config state untuk feature type."""
        return self._current_states.get(feature_type)
        
    def is_running(self) -> bool:
        """Check if watcher is running."""
        return self._running