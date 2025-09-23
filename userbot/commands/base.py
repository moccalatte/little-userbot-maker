"""Definisi dasar command userbot."""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Awaitable, Callable, List, Optional

from telethon import TelegramClient
from telethon.events import NewMessage

from common.storage import ScrapeStorage

from ..scheduler import BroadcastScheduler
from ..scraper import ScrapeController
from ..state import UserbotRuntime


command_logger = logging.getLogger("userbot.commands")


@dataclass(slots=True)
class CommandContext:
    client: TelegramClient
    event: NewMessage.Event
    runtime: UserbotRuntime
    scheduler: BroadcastScheduler
    scraper: ScrapeController
    storage: ScrapeStorage
    me_id: int
    rate_limit_seconds: int
    chat_id: Optional[int]
    reply_to_msg_id: Optional[int]

    async def reply(self, message: str, **kwargs) -> None:
        target_chat = self.chat_id if self.chat_id is not None else getattr(self.event, "chat_id", None)
        command_logger.info(
            "Mengirim balasan ke chat=%s reply_to=%s: %s",
            target_chat,
            self.reply_to_msg_id,
            message,
        )
        try:
            await self.event.reply(message, **kwargs)
        except Exception:
            command_logger.exception("Gagal balas via event.reply; mencoba fallback send_message")
        else:
            command_logger.info("Balasan terkirim via event.reply")
            return

        if target_chat is None:
            command_logger.error("Chat ID tidak tersedia; tidak bisa mengirim balasan")
            raise RuntimeError("Chat ID tidak tersedia untuk mengirim balasan.")

        send_kwargs = dict(kwargs)
        if self.reply_to_msg_id is not None and "reply_to" not in send_kwargs:
            send_kwargs["reply_to"] = self.reply_to_msg_id
        try:
            await self.client.send_message(entity=target_chat, message=message, **send_kwargs)
        except Exception:
            command_logger.exception("Gagal mengirim balasan via fallback send_message")
            raise
        command_logger.info("Balasan terkirim via fallback send_message")


CommandHandlerType = Callable[[CommandContext, List[str]], Awaitable[None]]


@dataclass(slots=True)
class CommandSpec:
    name: str
    description: str
    usage: str
    handler: CommandHandlerType
    help_text: Optional[str] = None
