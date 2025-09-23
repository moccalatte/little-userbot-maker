"""Controller listener untuk command !scr."""
from __future__ import annotations

import asyncio
import logging
import re
from typing import Dict, List, Optional

from telethon import TelegramClient, events

from common.storage import ScrapeStorage

logger = logging.getLogger("userbot")


class ScrapeController:
    def __init__(self, client: TelegramClient, storage: ScrapeStorage) -> None:
        self.client = client
        self.storage = storage
        self.rules: Dict[str, List[str]] = {"include": [], "exclude": [], "regex": []}
        self._compiled_regex: List[re.Pattern[str]] = []
        self._event_builder: Optional[events.NewMessage] = None
        self._buffer: List[Dict[str, str]] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._active = False

    def is_active(self) -> bool:
        return self._active

    async def start(self, rules: Dict[str, List[str]]) -> None:
        self.rules = rules
        self._compiled_regex = [re.compile(pattern, re.IGNORECASE) for pattern in rules.get("regex", [])]
        if not self._event_builder:
            self._event_builder = events.NewMessage(incoming=True)
            self.client.add_event_handler(self._on_new_message, self._event_builder)
        self._active = True
        logger.info("Scrape listener aktif dengan rules %s", rules)

    async def stop(self) -> None:
        self._active = False
        if self._event_builder:
            try:
                self.client.remove_event_handler(self._on_new_message, self._event_builder)
            except Exception:
                logger.debug("Gagal remove handler", exc_info=True)
            self._event_builder = None
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        self._flush_task = None
        async with self._buffer_lock:
            await self._flush_buffer_locked()
        logger.info("Scrape listener dihentikan")

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._active or not event.is_group:
            return
        try:
            message_text = event.raw_text or ""
            if not message_text:
                return
            if not self._match_rules(message_text):
                return
            row = {
                "timestamp": event.date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "chat_id": str(event.chat_id),
                "chat_title": getattr(event.chat, "title", ""),
                "message_text": message_text.replace("\n", " "),
                "rule_tag": ",".join(self.rules.get("include", [])),
            }
            await self._enqueue(row)
        except Exception:
            logger.exception("Error di listener scrape")

    def _match_rules(self, text: str) -> bool:
        lower_text = text.lower()
        includes = self.rules.get("include", [])
        if includes and not any(keyword.lower() in lower_text for keyword in includes):
            return False
        excludes = self.rules.get("exclude", [])
        if excludes and any(keyword.lower() in lower_text for keyword in excludes):
            return False
        if self._compiled_regex:
            return any(pattern.search(text) for pattern in self._compiled_regex)
        return True

    async def _enqueue(self, row: Dict[str, str]) -> None:
        async with self._buffer_lock:
            self._buffer.append(row)
            if len(self._buffer) >= 50:
                await self._flush_buffer_locked()
                return
            if not self._flush_task or self._flush_task.done():
                self._flush_task = asyncio.create_task(self._delayed_flush())

    async def _delayed_flush(self) -> None:
        await asyncio.sleep(1)
        async with self._buffer_lock:
            await self._flush_buffer_locked()

    async def _flush_buffer_locked(self) -> None:
        if not self._buffer:
            return
        rows = list(self._buffer)
        self._buffer.clear()
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self.storage.append_rows, rows)
        logger.info("Menulis %s baris hasil scrape", len(rows))
