"""Router command untuk userbot."""
from __future__ import annotations

import logging
import shlex
from typing import Optional

from telethon.events import NewMessage

from common.storage import ScrapeStorage

from .commands.base import CommandContext
from .commands.registry import get_commands
from .scheduler import BroadcastScheduler
from .scraper import ScrapeController
from .state import UserbotRuntime

# pastikan modul command terimport agar register berjalan
from .commands import gg, help_cmd, scr, sg  # noqa: F401

logger = logging.getLogger("userbot")


class CommandRouter:
    def __init__(
        self,
        client,
        runtime: UserbotRuntime,
        scheduler: BroadcastScheduler,
        scraper: ScrapeController,
        storage: ScrapeStorage,
        me_id: int,
        rate_limit_seconds: int,
        prefix: str = "!",
    ) -> None:
        self.client = client
        self.runtime = runtime
        self.scheduler = scheduler
        self.scraper = scraper
        self.storage = storage
        self.prefix = prefix
        self.me_id = me_id
        self.rate_limit_seconds = rate_limit_seconds

    async def dispatch(self, event: NewMessage.Event) -> None:
        text = event.raw_text or ""
        if not text.startswith(self.prefix):
            return
        try:
            parts = shlex.split(text[len(self.prefix) :])
        except ValueError as exc:
            await event.reply(f"Format perintah tidak valid: {exc}")
            return
        if not parts:
            return
        name = parts[0].lower()
        args = parts[1:]
        commands = get_commands()
        spec = commands.get(name)
        if not spec:
            await event.reply("Perintah tidak dikenal. Gunakan !help.")
            return
        ctx = CommandContext(
            client=self.client,
            event=event,
            runtime=self.runtime,
            scheduler=self.scheduler,
            scraper=self.scraper,
            storage=self.storage,
            me_id=self.me_id,
            rate_limit_seconds=self.rate_limit_seconds,
        )
        try:
            await spec.handler(ctx, args)
        except Exception:
            logger.exception("Error saat menjalankan perintah %s", name)
            await event.reply("Terjadi error internal saat menjalankan perintah.")

