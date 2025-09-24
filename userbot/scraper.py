"""Controller listener untuk command !scr dengan multi session."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set

from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User

from common.database import Database
from common.storage import ScrapeStorage

logger = logging.getLogger("userbot.scr")


@dataclass(slots=True)
class ScrapeSession:
    session_id: int
    rules: Dict[str, List[str]]
    compiled_regex: List[re.Pattern[str]]
    allowed_chats: Optional[Set[int]]
    raw_chat_ids: Optional[List[int]]
    output_path: Path
    matched_count: int = 0
    buffer: List[Dict[str, str]] = field(default_factory=list)
    buffer_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    flush_task: Optional[asyncio.Task] = None


class ScrapeController:
    def __init__(
        self,
        client: TelegramClient,
        database: Database,
        user_id: int,
        storage: ScrapeStorage,
        log_dir: str | Path | None = None,
    ) -> None:
        self.client = client
        self._database = database
        self._user_id = user_id
        self.storage = storage
        self._sessions: Dict[int, ScrapeSession] = {}
        self._event_builder: Optional[events.NewMessage] = None
        self._setup_logger(log_dir)

    # ------------------------------------------------------------------
    def is_active(self) -> bool:
        return bool(self._sessions)

    async def start(self, rules: Dict[str, List[str]], chat_ids: Optional[List[int]] = None) -> int:
        compiled: List[re.Pattern[str]] = []
        for pattern in rules.get("regex", []) or []:
            try:
                compiled.append(re.compile(pattern, re.IGNORECASE))
            except re.error as exc:
                raise ValueError(f"Regex tidak valid: {pattern} ({exc})") from exc
        normalized_ids = list(dict.fromkeys(int(chat) for chat in chat_ids)) if chat_ids else None
        allowed = self._build_allowed_chats(normalized_ids) if normalized_ids else None
        raw_ids = normalized_ids
        output_path = self.storage.allocate_file()
        session_id = self._database.add_scraper_session(
            user_id=self._user_id,
            include=rules.get("include", []),
            exclude=rules.get("exclude", []),
            regex=rules.get("regex", []),
            targets=raw_ids,
            output_path=str(output_path),
        )
        session = ScrapeSession(
            session_id=session_id,
            rules={
                "include": list(rules.get("include", [])),
                "exclude": list(rules.get("exclude", [])),
                "regex": list(rules.get("regex", [])),
            },
            compiled_regex=compiled,
            allowed_chats=allowed,
            raw_chat_ids=raw_ids,
            output_path=output_path,
        )
        self._sessions[session_id] = session
        self._ensure_handler()
        logger.info(
            "Scrape session aktif id=%s rules=%s targets=%s output=%s",
            session_id,
            session.rules,
            raw_ids if raw_ids is not None else "allgroup",
            output_path,
        )
        return session_id

    async def stop(self, session_id: Optional[int] = None) -> bool:
        if session_id is None:
            sessions = list(self._sessions.values())
            self._sessions.clear()
            changed = bool(sessions)
        else:
            session = self._sessions.pop(session_id, None)
            sessions = [session] if session else []
            changed = session is not None
        remove_all = session_id is None
        for session in sessions:
            if session is None:
                continue
            await self._flush_session(session)
            logger.info(
                "Scrape session dihentikan id=%s matched=%s file=%s",
                session.session_id,
                session.matched_count,
                session.output_path,
            )
            if not remove_all:
                self._database.delete_scraper_session(session.session_id, self._user_id)
        if remove_all and changed:
            self._database.delete_all_scraper_sessions(self._user_id)
        if not self._sessions:
            self._remove_handler()
        return changed

    def get_status(self) -> dict[str, object]:
        sessions = []
        for session in sorted(self._sessions.values(), key=lambda item: item.session_id):
            targets = session.raw_chat_ids
            if targets is None:
                target_desc = None
            else:
                target_desc = list(targets)
            sessions.append(
                {
                    "id": session.session_id,
                    "rules": session.rules,
                    "targets": target_desc,
                    "matched_count": session.matched_count,
                    "output_available": session.output_path.exists(),
                }
            )
        return {"sessions": sessions}

    # ------------------------------------------------------------------
    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._sessions:
            return
        if not (event.is_group or event.is_channel):
            return
        chat_id = event.chat_id
        if chat_id is None:
            return
        message_text = event.raw_text or ""
        if not message_text:
            return
        for session in list(self._sessions.values()):
            if session.allowed_chats and session.allowed_chats.isdisjoint(self._chat_id_variants(chat_id)):
                continue
            if not self._match_rules(session, message_text):
                continue
            await self._record_message(session, event, message_text)

    async def _record_message(self, session: ScrapeSession, event: events.NewMessage.Event, text: str) -> None:
        sender = await self._resolve_sender(event)
        row = {
            "timestamp": event.date.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "chat_id": str(event.chat_id),
            "chat_title": getattr(event.chat, "title", ""),
            "sender_username": sender,
            "message_text": text.replace("\n", " "),
            "rule_tag": ",".join(session.rules.get("include", [])),
        }
        async with session.buffer_lock:
            session.buffer.append(row)
            session.matched_count += 1
            if len(session.buffer) >= 50:
                await self._flush_session_locked(session)
                return
            if not session.flush_task or session.flush_task.done():
                session.flush_task = asyncio.create_task(self._delayed_flush(session))

    async def _delayed_flush(self, session: ScrapeSession) -> None:
        await asyncio.sleep(1)
        async with session.buffer_lock:
            await self._flush_session_locked(session)

    async def _flush_session_locked(self, session: ScrapeSession) -> None:
        if not session.buffer:
            return
        rows = list(session.buffer)
        session.buffer.clear()
        loop = asyncio.get_running_loop()
        output_path = await loop.run_in_executor(
            None, self.storage.append_rows, rows, session.output_path
        )
        session.output_path = output_path
        self._database.update_scraper_session(
            session_id=session.session_id,
            user_id=self._user_id,
            matched_count=session.matched_count,
            output_path=str(output_path),
        )
        logger.info(
            "Menulis %s baris hasil scrape ke %s (session=%s)",
            len(rows),
            output_path,
            session.session_id,
        )

    async def _flush_session(self, session: ScrapeSession) -> None:
        if session.flush_task and not session.flush_task.done():
            session.flush_task.cancel()
            try:
                await session.flush_task
            except asyncio.CancelledError:
                pass
        async with session.buffer_lock:
            await self._flush_session_locked(session)

    async def restore(self) -> None:
        records = self._database.list_scraper_sessions(self._user_id)
        if not records:
            return
        for record in records:
            session_id = int(record["id"])
            rules = record.get("rules", {})
            include = rules.get("include", [])
            exclude = rules.get("exclude", [])
            regex = rules.get("regex", [])
            targets = record.get("targets")
            if targets is not None:
                targets = [int(t) for t in targets]
            compiled: List[re.Pattern[str]] = []
            for pattern in regex:
                try:
                    compiled.append(re.compile(pattern, re.IGNORECASE))
                except re.error as exc:
                    logger.warning("Lewati regex invalid saat restore session %s: %s", session_id, exc)
            allowed = self._build_allowed_chats(targets) if targets else None
            output_path_str = record.get("output_path") or str(self.storage.allocate_file())
            output_path = Path(output_path_str)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            session = ScrapeSession(
                session_id=session_id,
                rules={
                    "include": include,
                    "exclude": exclude,
                    "regex": regex,
                },
                compiled_regex=compiled,
                allowed_chats=allowed,
                raw_chat_ids=list(targets) if targets else None,
                output_path=output_path,
                matched_count=record.get("matched_count", 0),
            )
            self._sessions[session_id] = session
        if self._sessions:
            self._ensure_handler()
            logger.info("Memulihkan %s scrape session dari database", len(self._sessions))

    # ------------------------------------------------------------------
    def _match_rules(self, session: ScrapeSession, text: str) -> bool:
        lower_text = text.lower()
        includes = session.rules.get("include", [])
        if includes and not any(keyword.lower() in lower_text for keyword in includes):
            return False
        excludes = session.rules.get("exclude", [])
        if excludes and any(keyword.lower() in lower_text for keyword in excludes):
            return False
        if session.compiled_regex:
            return any(pattern.search(text) for pattern in session.compiled_regex)
        return True

    async def _resolve_sender(self, event: events.NewMessage.Event) -> str:
        try:
            sender = await event.get_sender()
        except Exception:
            logger.debug("Tidak bisa resolve sender", exc_info=True)
            return ""
        if isinstance(sender, User):
            username = sender.username or sender.first_name or ""
        elif isinstance(sender, Channel):
            username = sender.username or sender.title or ""
        elif isinstance(sender, Chat):
            username = sender.title or ""
        else:
            username = getattr(sender, "title", "") or getattr(sender, "username", "")
        return username or ""

    # ------------------------------------------------------------------
    def _ensure_handler(self) -> None:
        if self._event_builder is None:
            self._event_builder = events.NewMessage(incoming=True, outgoing=True)
            self.client.add_event_handler(self._on_new_message, self._event_builder)

    def _remove_handler(self) -> None:
        if self._event_builder is not None:
            try:
                self.client.remove_event_handler(self._on_new_message, self._event_builder)
            except Exception:
                logger.debug("Gagal remove handler", exc_info=True)
        self._event_builder = None

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
