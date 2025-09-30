"""Aplikasi utama userbot."""
from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler

from telethon import TelegramClient, events
from telethon.sessions import StringSession

try:
    from .config import UserbotSettings
    from .utils import EncryptionError, build_cipher, decrypt_text
    from .database import Database
    from .config import forward_to_telegram, setup_logging
    from .reply_guard import ReplyGuard
    from .router import CommandRouter
    from .scheduler import BroadcastScheduler
    from .state import UserbotRuntime
    from .config_watcher import ConfigWatcher
except ImportError:
    from config import UserbotSettings
    from utils import EncryptionError, build_cipher, decrypt_text
    from database import Database
    from config import forward_to_telegram, setup_logging
    from reply_guard import ReplyGuard
    from router import CommandRouter
    from scheduler import BroadcastScheduler
    from state import UserbotRuntime
    from config_watcher import ConfigWatcher

logger = logging.getLogger("userbot")


class UserbotApp:
    def __init__(self, settings: UserbotSettings) -> None:
        self.settings = settings
        self.logger = setup_logging("userbot", settings.log_level, settings.log_dir)
        # Ensure combined aggregator exists (failsafe)
        try:
            combined_path = (Path(settings.log_dir) / "all_userbot.log").resolve()
            has_combined = any(isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(combined_path)
                               for h in self.logger.handlers)
            if not has_combined:
                combined_handler = RotatingFileHandler(str(combined_path), maxBytes=20 * 1024 * 1024, backupCount=3)
                combined_handler.setFormatter(logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                ))
                self.logger.addHandler(combined_handler)
        except Exception:
            logger.debug("Failed to attach combined aggregator handler", exc_info=True)
        self.logger.info("Initializing userbot with settings: api_id=%s, rate_limit=%s", settings.api_id, settings.rate_limit_interval)
        
        self.client: TelegramClient | None = None
        self.runtime = UserbotRuntime()
        self.router: CommandRouter | None = None
        self.scheduler: BroadcastScheduler | None = None
        self.config_watcher: ConfigWatcher | None = None
        
        self.logger.info("Connecting to userbot database...")
        self.database = Database.get_instance(settings.database_url)
        self.logger.debug("Userbot database connection established")
        
        self.me_id: int | None = None
        self.reply_guard: ReplyGuard | None = None

    async def start(self) -> None:
        self.logger.info("Starting userbot application...")
        
        session_string = self._load_session_string()
        self.logger.info("Creating Telegram client with API_ID: %s", self.settings.api_id)
        
        self.client = TelegramClient(StringSession(session_string), self.settings.api_id, self.settings.api_hash)
        
        self.logger.info("Connecting to Telegram...")
        await self.client.connect()
        
        if not await self.client.is_user_authorized():
            self.logger.error("Session not authorized - session may be invalid or expired")
            raise RuntimeError("Session tidak terotorisasi. Jalankan wizard untuk membuat session baru.")
        
        self.logger.info("Getting account information...")
        me = await self.client.get_me()
        self.me_id = me.id
        
        self.logger.info(
            "Connected as: %s (@%s) - ID: %s", 
            getattr(me, "first_name", "Unknown"), 
            getattr(me, "username", "N/A"), 
            self.me_id
        )
        
        self.logger.debug("Ensuring user exists in database...")
        self.database.ensure_user(self.me_id, getattr(me, "username", None), getattr(me, "first_name", None), getattr(me, "last_name", None))
        user_data_dir = (self.settings.storage_dir / str(self.me_id)).resolve()
        user_data_dir.mkdir(parents=True, exist_ok=True)
        media_dir = user_data_dir / "reply_guard_media"
        self.scheduler = BroadcastScheduler(
            client=self.client,
            database=self.database,
            user_id=self.me_id,
            rate_limit_seconds=self.settings.rate_limit_interval,
        )
        self.reply_guard = ReplyGuard(
            client=self.client,
            database=self.database,
            user_id=self.me_id,
            media_dir=media_dir,
            rate_limit_seconds=self.settings.rate_limit_interval,
            log_dir=self.settings.log_dir,
        )
        self.config_watcher = ConfigWatcher(
            database=self.database,
            user_id=self.me_id,
            check_interval=30,
        )
        self.runtime.scheduler = self.scheduler
        
        # Register config callbacks
        self.config_watcher.register_callback("broadcast", self._handle_broadcast_config)
        self.config_watcher.register_callback("auto_reply", self._handle_reply_config)
        
        self.router = CommandRouter(
            client=self.client,
            runtime=self.runtime,
            scheduler=self.scheduler,
            me_id=self.me_id,
            rate_limit_seconds=self.settings.rate_limit_interval,
            reply_guard=self.reply_guard,
            log_dir=self.settings.log_dir,
        )
        self.reply_guard.restore(self.me_id)
        await self.scheduler.restore()
        await self.config_watcher.start()
        self.client.add_event_handler(self._handle_command, events.NewMessage(outgoing=True))

        # Register wizard automation trigger and logger for @lilwizardbot
        try:
            try:
                from .automation.wizard_automation import WizardAutomation, WizardAutomationConfig, setup_wizard_logger
            except ImportError:
                from automation.wizard_automation import WizardAutomation, WizardAutomationConfig, setup_wizard_logger
            self.wizard_logger = setup_wizard_logger(self.settings.log_dir)
            self.wizard_automation = WizardAutomation(
                client=self.client,
                database=self.database,
                log_dir=self.settings.log_dir,
                me_id=self.me_id,
                config=WizardAutomationConfig(
                    wizard_username=os.getenv("WIZARD_BOT_USERNAME", "lilwizardbot"),
                    target_group_id=int(os.getenv("TEST_GROUP_ID", "-1002406400543")),
                    owner_id=int(os.getenv("OWNER_ID", str(self.settings.session_owner_id or self.me_id))),
                    max_wait_seconds=20,
                ),
            )

            # Log all incoming messages from wizard to the automation log
            async def _wizard_logger_handler(event: events.NewMessage.Event) -> None:
                text = event.raw_text or ""
                self.wizard_logger.info(
                    "WIZARD RECV: chat=%s sender=%s text=%s",
                    event.chat_id,
                    event.sender_id,
                    text[:300]
                )
                # Trigger automation when sentinel or start text detected
                lowered = text.lower()
                if "#automate_tests_start" in lowered or "automated testing: starting" in lowered:
                    self.wizard_logger.info("AUTOMATION TRIGGER DETECTED from wizard. Starting suite...")
                    asyncio.create_task(self.wizard_automation.run_full_suite())

            # Register handler for messages from wizard bot only
            wizard_username = os.getenv("WIZARD_BOT_USERNAME", "lilwizardbot")
            self.client.add_event_handler(
                _wizard_logger_handler,
                events.NewMessage(from_users=wizard_username)
            )
        except Exception:
            logger.exception("Failed to initialize wizard automation")

        forward_to_telegram(self.logger, self._build_forwarder())
        self.logger.info("Userbot siap. Ketik !help dari Telegram untuk melihat perintah.")
        await self.client.run_until_disconnected()

    async def _handle_command(self, event: events.NewMessage.Event) -> None:
        logger.info(
            "Event diterima: sender=%s me_id=%s outgoing=%s chat=%s raw=%s",
            event.sender_id,
            self.me_id,
            getattr(event, "out", None),
            event.chat_id,
            event.raw_text,
        )
        if event.sender_id not in (None, self.me_id):
            logger.info(
                "Event diabaikan karena sender %s != me_id %s",
                event.sender_id,
                self.me_id,
            )
            return
        if not self.router:
            logger.error("Router belum tersedia saat menerima event")
            return
        await self.router.dispatch(event)

    def _load_session_string(self) -> str:
        owner_id = getattr(self.settings, "session_owner_id", None)
        
        # If no owner_id specified, try to help user
        if owner_id is None:
            return self._handle_no_owner_id()
            
        # Load session for specific owner_id
        self.logger.info("Loading session from database for owner_id: %s", owner_id)
        record = self.database.get_latest_session(owner_id)
        if not record:
            self.logger.error("No session found in database for owner_id: %s", owner_id)
            raise RuntimeError(
                f"Tidak ditemukan session di database untuk owner {owner_id}.\n"
                f"Pastikan user dengan ID {owner_id} sudah registrasi via Bot Wizard dan membuat session."
            )
            
        session_string = record.get("session_string", "").strip()
        if not session_string:
            self.logger.error("Empty session string in database for owner_id: %s", owner_id)
            raise RuntimeError("Session string kosong di database.")
            
        self.logger.debug("Found session for owner_id %s (encrypted: %s)", owner_id, record.get("encrypted", False))
        
        if record.get("encrypted"):
            self.logger.debug("Decrypting session for owner_id: %s", owner_id)
            cipher = build_cipher(self.settings.secret_key)
            if not cipher:
                self.logger.error("Cannot decrypt session: SECRET_KEY not available for owner_id: %s", owner_id)
                raise EncryptionError(
                    "SECRET_KEY wajib diisi agar bisa men-dekripsi session terenkripsi dari database."
                )
            session_string = decrypt_text(cipher, session_string)
            self.logger.debug("Session decrypted successfully for owner_id: %s", owner_id)
            
        self.logger.info("Session loaded successfully from database for owner_id: %s", owner_id)
        return session_string
        
    def _handle_no_owner_id(self) -> str:
        """Handle case when no owner_id is specified."""
        # Try to get active sessions from database
        try:
            active_sessions = self.database.get_active_userbot_sessions()
        except Exception as e:
            raise RuntimeError(
                f"Gagal mengambil data dari database: {e}\n"
                "Pastikan DATABASE_URL sudah benar dan database accessible."
            )
            
        if not active_sessions:
            raise RuntimeError(
                "Tidak ada session aktif ditemukan di database.\n\n"
                "Cara mengatasi:\n"
                "1. Pastikan ada user yang sudah registrasi via Bot Wizard\n"
                "2. User sudah membuat session (QR/OTP)\n"
                "3. User memiliki subscription aktif\n\n"
                "Jika sudah ada user, jalankan dengan: python main.py --owner-id <telegram_user_id>"
            )
            
        if len(active_sessions) == 1:
            # Auto-select the only active session
            session = active_sessions[0]
            owner_id = session["user_id"]
            self.settings.session_owner_id = owner_id  # Set for later use
            
            self.logger.info(
                "Auto-selecting session untuk user %s (%s) - satu-satunya session aktif",
                owner_id, session.get("username", "Unknown")
            )
            
            session_string = session["session_string"].strip()
            if session.get("encrypted"):
                cipher = build_cipher(self.settings.secret_key)
                if not cipher:
                    raise EncryptionError(
                        "SECRET_KEY wajib diisi agar bisa men-dekripsi session terenkripsi dari database."
                    )
                session_string = decrypt_text(cipher, session_string)
                
            return session_string
        else:
            # Multiple active sessions - user must choose
            session_list = "\n".join([
                f"  - {s['user_id']} ({s.get('username', 'N/A')}) - {s.get('first_name', 'Unknown')}"
                for s in active_sessions[:10]  # Limit to 10 for readability
            ])
            
            raise RuntimeError(
                f"Ditemukan {len(active_sessions)} session aktif. Pilih salah satu:\n\n"
                f"{session_list}\n\n"
                "Jalankan dengan: python main.py --owner-id <telegram_user_id>"
            )

    def _build_forwarder(self):
        if not self.settings.telegram_log_chat_id or not self.client:
            return None

        async def _async_send(message: str) -> None:
            try:
                await self.client.send_message(self.settings.telegram_log_chat_id, message)
            except Exception:
                self.logger.debug("Gagal kirim log userbot", exc_info=True)

        def wrapper(message: str) -> None:
            asyncio.create_task(_async_send(message))

        return wrapper

    async def _handle_broadcast_config(self, feature_type: str, new_state, old_state) -> None:
        """Handle broadcast config changes dari Bot Wizard."""
        try:
            if new_state is None:
                # Config deleted - stop all broadcast jobs
                await self.scheduler.stop()
                logger.info("All broadcast jobs stopped (config deleted)")
                return
                
            if not new_state.enabled:
                # Config disabled - stop all broadcast jobs
                await self.scheduler.stop()
                logger.info("All broadcast jobs stopped (config disabled)")
                return
                
            # Config enabled/updated
            config = new_state.config
            message = config.get("message", "")
            interval_minutes = config.get("interval_minutes", 60)
            targets = config.get("targets", [])
            
            if message and targets:
                # Stop existing jobs first
                await self.scheduler.stop()
                
                # Start new broadcast job
                job_id = await self.scheduler.start(
                    message=message,
                    interval_minutes=interval_minutes,
                    targets=targets
                )
                logger.info(
                    "Broadcast job started from Bot Wizard config: job_id=%s, interval=%sm, targets=%s",
                    job_id, interval_minutes, len(targets)
                )
            else:
                logger.warning("Invalid broadcast config: missing message or targets")
                
        except Exception:
            logger.exception("Error handling broadcast config change")
            
    async def _handle_reply_config(self, feature_type: str, new_state, old_state) -> None:
        """Handle auto reply config changes dari Bot Wizard."""
        try:
            if new_state is None:
                # Config deleted - stop all reply rules
                self.reply_guard.stop_all_rules(self.me_id)
                logger.info("All reply rules stopped (config deleted)")
                return
                
            if not new_state.enabled:
                # Config disabled - stop all reply rules
                self.reply_guard.stop_all_rules(self.me_id)
                logger.info("All reply rules stopped (config disabled)")
                return
                
            # Config enabled/updated
            config = new_state.config
            include = config.get("include", [])
            exclude = config.get("exclude", [])
            regex = config.get("regex", [])
            targets = config.get("targets")
            reply_text = config.get("reply_text", "")
            
            if reply_text:
                # Stop existing rules first
                self.reply_guard.stop_all_rules(self.me_id)
                
                # Add new reply rule
                rule_id = self.reply_guard.add_rule(
                    user_id=self.me_id,
                    include=include,
                    exclude=exclude,
                    regex=regex,
                    targets=targets,
                    reply_text=reply_text
                )
                logger.info(
                    "Auto reply rule added from Bot Wizard config: rule_id=%s, targets=%s",
                    rule_id, targets if targets else "allgroup"
                )
            else:
                logger.warning("Invalid reply config: missing reply_text")
                
        except Exception:
            logger.exception("Error handling auto reply config change")


async def run_userbot(settings: UserbotSettings) -> None:
    app = UserbotApp(settings)
    await app.start()
