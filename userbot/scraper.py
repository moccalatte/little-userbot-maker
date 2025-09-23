"""Controller listener untuk command !scr."""
from __future__ import annotations

import asyncio
import logging
import re
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from telethon import TelegramClient, events

from common.storage import ScrapeStorage

logger = logging.getLogger("userbot.scr")


class ScrapeController:
    def __init__(self, client: TelegramClient, storage: ScrapeStorage, log_dir: str | Path | None = None) -> None:
        self.client = client
        self.storage = storage
        self.rules: Dict[str, List[str]] = {"include": [], "exclude": [], "regex": []}
        self._compiled_regex: List[re.Pattern[str]] = []
        self._event_builder: Optional[events.NewMessage] = None
        self._buffer: List[Dict[str, str]] = []
        self._buffer_lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._active = False
        self._allowed_chats: Optional[Set[int]] = None
        self._matched_count = 0
        self._output_path: Optional[Path] = None
        self._setup_logger(log_dir)

    def is_active(self) -> bool:
        return self._active

    async def start(self, rules: Dict[str, List[str]], chat_ids: Optional[List[int]] = None) -> None:
        self.rules = rules
        self._compiled_regex = [re.compile(pattern, re.IGNORECASE) for pattern in rules.get("regex", [])]
        self._allowed_chats = self._build_allowed_chats(chat_ids) if chat_ids else None
        self._matched_count = 0
        self._output_path = self.storage.allocate_file()
        if not self._event_builder:
            self._event_builder = events.NewMessage(incoming=True, outgoing=True)
            self.client.add_event_handler(self._on_new_message, self._event_builder)
        self._active = True
        logger.info(
            "Scrape listener aktif dengan rules %s untuk chats %s",
            rules,
            sorted(self._allowed_chats) if self._allowed_chats else "semua grup",
        )
        if self._output_path:
            logger.info("Hasil scrape akan ditulis ke %s", self._output_path)

    async def stop(self) -> None:
        self._active = False
        if self._event_builder:
            try:
                self.client.remove_event_handler(self._on_new_message, self._event_builder)
            except Exception:
                logger.debug("Gagal remove handler", exc_info=True)
            self._event_builder = None
        self._allowed_chats = None
        if self._flush_task and not self._flush_task.done():
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        self._flush_task = None
        async with self._buffer_lock:
            await self._flush_buffer_locked()
        output_path = self._output_path
        self._output_path = None
        logger.info("Scrape listener dihentikan setelah menangkap %s pesan", self._matched_count)
        if output_path:
            logger.info("Scrape listener dihentikan. Hasil terakhir tercatat di %s", output_path)
        else:
            logger.info("Scrape listener dihentikan")

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._active:
            return
        if not (event.is_group or event.is_channel):
            return
        chat_id_variants = self._chat_id_variants(event.chat_id)
        if self._allowed_chats and self._allowed_chats.isdisjoint(chat_id_variants):
            logger.info(
                "Pesan diabaikan karena chat %s tidak ada di daftar target %s",
                event.chat_id,
                sorted(self._allowed_chats),
            )
            return
        try:
            message_text = event.raw_text or ""
            if not message_text:
                return
            logger.info(
                "Memeriksa pesan di chat %s: %s",
                event.chat_id,
                message_text,
            )
            if not self._match_rules(message_text):
                logger.info(
                    "Pesan dari chat %s tidak cocok dengan rules %s",
                    event.chat_id,
                    self.rules,
                )
                return
            row = {
                "timestamp": event.date.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "chat_id": str(event.chat_id),
                "chat_title": getattr(event.chat, "title", ""),
                "message_text": message_text.replace("\n", " "),
                "rule_tag": ",".join(self.rules.get("include", [])),
            }
            logger.info(
                "Pesan cocok ditangkap dari chat %s: %s",
                event.chat_id,
                message_text,
            )
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
            self._matched_count += 1
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
        output_path = await loop.run_in_executor(
            None, self.storage.append_rows, rows, self._output_path
        )
        logger.info("Menulis %s baris hasil scrape ke %s", len(rows), output_path)

    def _build_allowed_chats(self, chat_ids: Iterable[int]) -> Set[int]:
        result: Set[int] = set()
        for chat_id in chat_ids:
            result.update(self._chat_id_variants(chat_id))
        return result

    def _chat_id_variants(self, chat_id: int) -> Set[int]:
        variants = {chat_id}
        if chat_id is None:
            return variants
        if chat_id > 0:
            variants.add(self._to_supergroup_id(chat_id))
        elif chat_id < 0 and str(chat_id).startswith("-100"):
            try:
                variants.add(int(str(chat_id)[4:]))
            except ValueError:
                pass
        return variants

    @staticmethod
    def _to_supergroup_id(channel_id: int) -> int:
        return -1000000000000 - channel_id

    def _setup_logger(self, log_dir: str | Path | None) -> None:
        if log_dir is None:
            return
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_path = log_path / "userbot_scr.log"
        already = any(
            getattr(handler, "baseFilename", None) == str(file_path)
            for handler in logger.handlers
        )
        if not already:
            handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=2)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False
