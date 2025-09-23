"""Definisi dasar command userbot."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable, List

from telethon import TelegramClient
from telethon.events import NewMessage

from common.storage import ScrapeStorage

from ..scheduler import BroadcastScheduler
from ..scraper import ScrapeController
from ..state import UserbotRuntime


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


CommandHandlerType = Callable[[CommandContext, List[str]], Awaitable[None]]


@dataclass(slots=True)
class CommandSpec:
    name: str
    description: str
    usage: str
    handler: CommandHandlerType

