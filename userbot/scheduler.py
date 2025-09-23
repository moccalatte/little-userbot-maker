"""Scheduler broadcast sederhana untuk command !sg."""
from __future__ import annotations

import asyncio
import logging
from typing import Iterable, List

from telethon import TelegramClient
from telethon.errors import FloodWaitError
logger = logging.getLogger("userbot")


class SchedulerError(RuntimeError):
    pass


class BroadcastScheduler:
    def __init__(self, client: TelegramClient, rate_limit_seconds: int = 30) -> None:
        self.client = client
        self.rate_limit_seconds = rate_limit_seconds
        self._task: asyncio.Task | None = None
        self._interval_seconds: int = 0
        self._message: str = ""
        self._targets: List[int] = []
        self._active = asyncio.Event()

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, message: str, interval_minutes: int, targets: Iterable[int]) -> None:
        if self.running:
            raise SchedulerError("Scheduler sudah berjalan. Gunakan !sg stop dulu.")
        self._message = message
        self._interval_seconds = interval_minutes * 60
        self._targets = list(targets)
        if not self._targets:
            raise SchedulerError("Daftar target kosong.")
        self._active.set()
        self._task = asyncio.create_task(self._run())
        logger.info("Broadcast scheduler dimulai ke %s target", len(self._targets))

    async def stop(self) -> None:
        if not self.running:
            return
        self._active.clear()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("Broadcast scheduler dihentikan")

    async def _run(self) -> None:
        try:
            while self._active.is_set():
                await self._broadcast_once()
                await asyncio.sleep(self._interval_seconds)
        except asyncio.CancelledError:
            logger.debug("Task broadcast dibatalkan")
            raise
        except Exception:
            logger.exception("Terjadi error saat broadcast loop")
            await asyncio.sleep(self.rate_limit_seconds)
            raise

    async def _broadcast_once(self) -> None:
        for target in self._targets:
            try:
                await self.client.send_message(target, self._message)
            except FloodWaitError as exc:
                wait = max(self.rate_limit_seconds, int(getattr(exc, "seconds", self.rate_limit_seconds)))
                logger.warning("Flood wait saat kirim pesan ke %s. Tidur %s detik.", target, wait)
                await asyncio.sleep(wait)
            except Exception:
                logger.exception("Gagal mengirim pesan ke %s", target)
                await asyncio.sleep(self.rate_limit_seconds)
            else:
                await asyncio.sleep(self.rate_limit_seconds)


async def resolve_targets(client: TelegramClient, target_spec: str) -> List[int]:
    target_spec = target_spec.strip()
    if not target_spec:
        raise SchedulerError("Target tidak boleh kosong.")
    if target_spec.lower() == "allgroup":
        dialogs = await client.get_dialogs()
        results: List[int] = []
        for dialog in dialogs:
            entity = getattr(dialog, "entity", None)
            if entity is None:
                continue
            if getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False):
                results.append(entity.id)
        return list(dict.fromkeys(results))
    targets: List[int] = []
    for item in target_spec.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            targets.append(int(item))
        except ValueError:
            raise SchedulerError(f"ID target tidak valid: {item}")
    return list(dict.fromkeys(targets))
