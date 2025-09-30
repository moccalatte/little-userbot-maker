"""Wizard automation to drive @lilwizardbot menus and run tests.
All logs go to userbot/logs/wizard_automation.log and include:
- Outgoing messages sent by the userbot owner account
- Incoming messages from @lilwizardbot
- Actions in target group -1002406400543 and their outcomes
- Errors and mismatches
"""
from __future__ import annotations

import asyncio
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence

from telethon import events
from telethon.tl.custom.message import Message
from telethon.tl.custom.dialog import Dialog

try:
    from ..database import Database
except ImportError:
    from database import Database


def setup_wizard_logger(log_dir: str | Path) -> logging.Logger:
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("userbot.wizard_automation")
    logger.setLevel(logging.INFO)

    # Avoid duplicate handlers
    if not any(isinstance(h, logging.FileHandler) and getattr(h, "_wizard_log", False) for h in logger.handlers):
        fh = logging.FileHandler(str(log_dir / "wizard_automation.log"), encoding="utf-8")
        fh._wizard_log = True  # mark to avoid duplicates
        fh.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s"))
        logger.addHandler(fh)

    return logger


@dataclass
class WizardAutomationConfig:
    wizard_username: str = "lilwizardbot"  # without @
    target_group_id: int = -1002406400543
    owner_id: int = 5473468582
    max_wait_seconds: int = 20


class WizardAutomation:
    def __init__(self, client, database: Database, log_dir: str | Path, me_id: int, config: WizardAutomationConfig = WizardAutomationConfig()):
        self.client = client
        self.db = database
        self.me_id = me_id
        self.cfg = config
        self.logger = setup_wizard_logger(log_dir)
        self._incoming_handlers_added = False

    def _log_step(self, msg: str, **extra):
        if extra:
            self.logger.info("%s | %s", msg, extra)
        else:
            self.logger.info(msg)

    async def _send_and_wait(self, text: str, expect_substring: Optional[str] = None, chat: Optional[str | int] = None, wait: int = 8) -> list[Message]:
        chat = chat or self.cfg.wizard_username
        self._log_step(f"SEND → {chat}: {text}")
        await self.client.send_message(chat, text)
        await asyncio.sleep(1)

        messages: list[Message] = []
        timeout = max(1, wait)
        end = asyncio.get_event_loop().time() + timeout
        while asyncio.get_event_loop().time() < end:
            msgs = [m async for m in self.client.iter_messages(chat, limit=5)]
            if msgs:
                messages = list(reversed(msgs))  # chronological
                if not expect_substring or any(expect_substring.lower() in (m.raw_text or "").lower() for m in messages):
                    break
            await asyncio.sleep(1)
        # Log what we saw
        for m in messages[-3:]:
            origin = "BOT" if m.sender_id != self.me_id else "ME"
            self._log_step(f"RECV ← {chat} [{origin}]: {m.raw_text[:200] if m.raw_text else ''}")

        if expect_substring and not any(expect_substring.lower() in (m.raw_text or "").lower() for m in messages):
            self._log_step("EXPECTATION NOT MET", expected=expect_substring, context=f"chat={chat}")
        return messages

    async def _ensure_dialog(self, dialog_title_contains: str | None = None) -> Optional[Dialog]:
        async for d in self.client.iter_dialogs():
            if dialog_title_contains and dialog_title_contains.lower() in d.name.lower():
                return d
            if d.entity and getattr(d.entity, "username", "").lower() == self.cfg.wizard_username.lower():
                return d
        return None

    async def run_full_suite(self) -> None:
        # Verify owner/admin
        if self.me_id != self.cfg.owner_id:
            self._log_step("OWNER MISMATCH: refusing to run", me_id=self.me_id, expected_owner=self.cfg.owner_id)
            return

        self._log_step("AUTOMATION STARTED", owner_id=self.me_id, wizard=self.cfg.wizard_username)

        # Make sure we can access wizard dialog
        dialog = await self._ensure_dialog()
        if not dialog:
            self._log_step("Wizard dialog not found - trying to open by username", wizard=self.cfg.wizard_username)
            try:
                await self.client.send_message(self.cfg.wizard_username, "/start")
            except Exception as e:
                self._log_step("FAILED to open wizard dialog", error=str(e))
                return

        # Start wizard and go to admin
        await self._send_and_wait("/start", expect_substring="UserbotMaker")
        await self._send_and_wait("🔧 Admin Settings", expect_substring="Admin Settings")

        # Automated testing can be triggered either by the wizard button or we continue directly
        # Navigate basic flow to set up Reply Guard via wizard menus
        # Step: Open userbot menu
        await self._send_and_wait("⚙️ Kelola Userbot", expect_substring="Kelola Userbot")
        await self._send_and_wait("📋 Lihat Commands", expect_substring="Pilih Command")
        await self._send_and_wait("🤖 Reply Guard", expect_substring="Reply Guard")

        # From historical logs, these labels exist in your setup
        # Try both labels just in case
        msgs = await self._send_and_wait("🔧 Setup Auto Reply", expect_substring="Setup", wait=6)
        if not any("Setup" in (m.raw_text or "") for m in msgs):
            await self._send_and_wait("🔴 Setup Basic Reply", expect_substring="Setup")

        # Fill in keyword/include
        include_kw = "zazizu"
        await self._send_and_wait(include_kw, expect_substring=include_kw)

        # Select target group (specific)
        await self._send_and_wait("🎯 Grup Tertentu", expect_substring="Grup")
        await self._send_and_wait(str(self.cfg.target_group_id), expect_substring=str(self.cfg.target_group_id))

        # Provide reply text
        reply_text = "ini adalah balasan123!#%5678"
        await self._send_and_wait(reply_text, expect_substring=reply_text)

        # Activate rule if prompted
        await self._send_and_wait("✅ Aktifkan Rule", expect_substring="Aktif")

        # Status check
        await self._send_and_wait("📊 Status Reply Guard", expect_substring="Status")

        # Test in target group
        self._log_step("TEST: sending keyword to target group", group=self.cfg.target_group_id, keyword=include_kw)
        # Ensure self-reply test mode is respected if configured via env
        sent = await self.client.send_message(self.cfg.target_group_id, f"🧪 AUTO-TEST: {include_kw}")
        await asyncio.sleep(2)

        # Observe for replies for up to max_wait_seconds
        reply_found = False
        end = asyncio.get_event_loop().time() + max(10, self.cfg.max_wait_seconds)
        while asyncio.get_event_loop().time() < end and not reply_found:
            async for msg in self.client.iter_messages(self.cfg.target_group_id, limit=10):
                if msg.id > sent.id and msg.sender_id == self.me_id:
                    # Accept as reply if text contains the reply_text or is a reply to our test
                    if (msg.raw_text and reply_text.lower()[:6] in msg.raw_text.lower()) or \
                       (getattr(msg, 'reply_to', None) and msg.reply_to and msg.reply_to.reply_to_msg_id == sent.id):
                        self._log_step("GROUP REPLY DETECTED", reply_text=msg.raw_text[:120] if msg.raw_text else "")
                        reply_found = True
                        break
            await asyncio.sleep(1)

        if not reply_found:
            self._log_step("NO REPLY IN GROUP", group=self.cfg.target_group_id, sent_message_id=sent.id)

        # Final status
        await self._send_and_wait("📊 Status Reply Guard", expect_substring="Status")
        self._log_step("AUTOMATION FINISHED")
