"""Aplikasi utama userbot."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telethon import TelegramClient, events
from telethon.sessions import StringSession

from common.config import UserbotSettings
from common.logging_config import forward_to_telegram, setup_logging
from common.storage import ScrapeStorage

from .router import CommandRouter
from .scheduler import BroadcastScheduler
from .scraper import ScrapeController
from .state import UserbotRuntime

logger = logging.getLogger("userbot")


class UserbotApp:
    def __init__(self, settings: UserbotSettings) -> None:
        self.settings = settings
        self.logger = setup_logging("userbot", settings.log_level, settings.log_dir)
        self.client: TelegramClient | None = None
        self.runtime = UserbotRuntime()
        self.router: CommandRouter | None = None
        self.scheduler: BroadcastScheduler | None = None
        self.scraper: ScrapeController | None = None
        self.storage = ScrapeStorage(settings.storage_dir / "scrape_output")
        self.me_id: int | None = None

    async def start(self) -> None:
        session_string = self._load_session_string()
        self.client = TelegramClient(StringSession(session_string), self.settings.api_id, self.settings.api_hash)
        await self.client.connect()
        if not await self.client.is_user_authorized():
            raise RuntimeError("Session tidak terotorisasi. Jalankan wizard untuk membuat session baru.")
        me = await self.client.get_me()
        self.me_id = me.id
        self.scheduler = BroadcastScheduler(self.client, self.settings.rate_limit_interval)
        self.scraper = ScrapeController(self.client, self.storage)
        self.runtime.scheduler = self.scheduler
        self.runtime.scraper = self.scraper
        self.router = CommandRouter(
            client=self.client,
            runtime=self.runtime,
            scheduler=self.scheduler,
            scraper=self.scraper,
            storage=self.storage,
            me_id=self.me_id,
            rate_limit_seconds=self.settings.rate_limit_interval,
        )
        self.client.add_event_handler(self._handle_command, events.NewMessage(outgoing=True))
        forward_to_telegram(self.logger, self._build_forwarder())
        self.logger.info("Userbot siap. Ketik !help dari Telegram untuk melihat perintah.")
        await self.client.run_until_disconnected()

    async def _handle_command(self, event: events.NewMessage.Event) -> None:
        if event.sender_id != self.me_id:
            return
        if not self.router:
            return
        await self.router.dispatch(event)

    def _load_session_string(self) -> str:
        path = Path(self.settings.session_file)
        if not path.exists():
            raise FileNotFoundError(f"Session file tidak ditemukan: {path}")
        session = path.read_text(encoding="utf-8").strip()
        if not session:
            raise ValueError("Session file kosong.")
        return session

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


async def run_userbot(settings: UserbotSettings) -> None:
    app = UserbotApp(settings)
    await app.start()

