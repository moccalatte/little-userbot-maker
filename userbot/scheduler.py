"""Scheduler broadcast dengan dukungan banyak job."""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

from telethon import TelegramClient
from telethon.errors import FloodWaitError

logger = logging.getLogger("userbot")


class SchedulerError(RuntimeError):
    pass


@dataclass(slots=True)
class BroadcastJob:
    job_id: int
    message: str
    interval_seconds: int
    targets: List[int]
    active: asyncio.Event = field(default_factory=asyncio.Event)
    task: Optional[asyncio.Task] = None


class BroadcastScheduler:
    """Kelola banyak jadwal broadcast sekaligus."""

    def __init__(self, client: TelegramClient, rate_limit_seconds: int = 30) -> None:
        self.client = client
        self.rate_limit_seconds = rate_limit_seconds
        self._jobs: Dict[int, BroadcastJob] = {}
        self._next_job_id = 1
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    async def start(self, message: str, interval_minutes: int, targets: Iterable[int]) -> int:
        targets_list = list(dict.fromkeys(int(t) for t in targets))
        if not targets_list:
            raise SchedulerError("Daftar target kosong.")
        if interval_minutes <= 0:
            raise SchedulerError("Interval harus lebih besar dari 0.")
        job_id = self._next_job_id
        self._next_job_id += 1
        interval_seconds = interval_minutes * 60
        job = BroadcastJob(
            job_id=job_id,
            message=message,
            interval_seconds=interval_seconds,
            targets=targets_list,
        )
        job.active.set()
        async with self._lock:
            self._jobs[job_id] = job
            job.task = asyncio.create_task(self._run_job(job_id), name=f"broadcast:{job_id}")
        logger.info(
            "Broadcast job dimulai id=%s interval=%s target=%s",
            job_id,
            interval_minutes,
            len(targets_list),
        )
        return job_id

    async def stop(self, job_id: Optional[int] = None) -> bool:
        async with self._lock:
            if job_id is None:
                jobs = list(self._jobs.values())
                self._jobs.clear()
                changed = bool(jobs)
            else:
                job = self._jobs.pop(job_id, None)
                jobs = [job] if job else []
                changed = job is not None
        for job in jobs:
            if job is None:
                continue
            job.active.clear()
            task = job.task
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
            logger.info("Broadcast job berhenti id=%s", job.job_id)
        return changed

    def get_status(self) -> dict[str, object]:
        jobs = []
        for job in sorted(self._jobs.values(), key=lambda item: item.job_id):
            jobs.append(
                {
                    "id": job.job_id,
                    "message": job.message,
                    "interval_minutes": job.interval_seconds // 60,
                    "targets": list(job.targets),
                }
            )
        return {
            "jobs": jobs,
            "rate_limit_seconds": self.rate_limit_seconds,
        }

    @property
    def running(self) -> bool:
        return bool(self._jobs)

    # ------------------------------------------------------------------
    async def _run_job(self, job_id: int) -> None:
        job = self._jobs.get(job_id)
        if not job:
            return
        try:
            while job.active.is_set():
                await self._broadcast_once(job)
                await asyncio.sleep(job.interval_seconds)
        except asyncio.CancelledError:
            logger.debug("Task broadcast dibatalkan id=%s", job_id)
            raise
        except Exception:
            logger.exception("Terjadi error saat broadcast loop id=%s", job_id)
            await asyncio.sleep(self.rate_limit_seconds)
            raise

    async def _broadcast_once(self, job: BroadcastJob) -> None:
        for target in job.targets:
            try:
                await self.client.send_message(target, job.message)
            except FloodWaitError as exc:
                wait = max(self.rate_limit_seconds, int(getattr(exc, "seconds", self.rate_limit_seconds)))
                logger.warning("Flood wait saat kirim pesan ke %s (job=%s). Tidur %s detik.", target, job.job_id, wait)
                await asyncio.sleep(wait)
            except Exception:
                logger.exception("Gagal mengirim pesan ke %s untuk job=%s", target, job.job_id)
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
