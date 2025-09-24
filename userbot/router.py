"""Router command untuk userbot."""
from __future__ import annotations

import asyncio
import logging
import shlex
from logging.handlers import RotatingFileHandler
from pathlib import Path

from telethon.events import NewMessage

from common.storage import ScrapeStorage

from .commands.base import CommandContext, CommandSpec
from .commands.registry import get_commands
from .reply_guard import ReplyGuard
from .scheduler import BroadcastScheduler
from .scraper import ScrapeController
from .state import UserbotRuntime

# pastikan modul command terimport agar register berjalan
from .commands import gg, help_cmd, scr, sg, rg, info  # noqa: F401

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
        reply_guard: ReplyGuard,
        log_dir: str | Path | None = None,
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
        self.reply_guard = reply_guard
        self._tasks: set[asyncio.Task] = set()
        self.command_logger = logging.getLogger("userbot.commands")
        self._ensure_command_logger(log_dir)

    async def dispatch(self, event: NewMessage.Event) -> None:
        text = event.raw_text or ""
        if not text.startswith(self.prefix):
            return
        try:
            parts = shlex.split(text[len(self.prefix) :])
        except ValueError as exc:
            self.command_logger.warning(
                "Format perintah tidak valid: %s (text=%s)", exc, text
            )
            await event.reply(f"Format perintah tidak valid: {exc}")
            return
        if not parts:
            self.command_logger.info("Perintah kosong diabaikan")
            return
        name = parts[0].lower()
        args = parts[1:]
        commands = get_commands()
        spec = commands.get(name)
        if not spec:
            self.command_logger.warning(
                "Perintah tidak dikenal diterima: name=%s text=%s", name, event.raw_text
            )
            logger.warning("Perintah tidak dikenal diterima: %s", name)
            await event.reply("Perintah tidak dikenal. Gunakan !help.")
            return
        self.command_logger.info(
            "Command diterima name=%s sender=%s chat=%s msg_id=%s args=%s",
            name,
            event.sender_id,
            event.chat_id,
            getattr(event.message, "id", None),
            args,
        )
        logger.info("Perintah %s diterima dengan argumen %s", name, args)
        message = getattr(event, "message", None)
        reply_to_msg_id = getattr(message, "id", None)
        ctx = CommandContext(
            client=self.client,
            event=event,
            runtime=self.runtime,
            scheduler=self.scheduler,
            scraper=self.scraper,
            storage=self.storage,
            me_id=self.me_id,
            rate_limit_seconds=self.rate_limit_seconds,
            chat_id=event.chat_id,
            reply_to_msg_id=reply_to_msg_id,
            reply_guard=self.reply_guard,
        )
        self._schedule_command(spec, ctx, args)

    def _schedule_command(self, spec: CommandSpec, ctx: CommandContext, args: list[str]) -> None:
        task = asyncio.create_task(self._execute_command(spec, ctx, args), name=f"command:{spec.name}")
        self._tasks.add(task)
        task.add_done_callback(lambda finished_task, command_name=spec.name: self._on_task_done(finished_task, command_name))
        active_names = [t.get_name() or f"task-{id(t)}" for t in self._tasks]
        self.command_logger.info(
            "Task dijadwalkan command=%s task=%s total_task=%s aktif=%s",
            spec.name,
            task.get_name(),
            len(self._tasks),
            active_names,
        )

    async def _execute_command(self, spec: CommandSpec, ctx: CommandContext, args: list[str]) -> None:
        logger.info("Menjalankan perintah %s dengan argumen %s", spec.name, args)
        current_task = asyncio.current_task()
        self.command_logger.info(
            "Mulai eksekusi command=%s task=%s args=%s",
            spec.name,
            current_task.get_name() if current_task else "(unknown)",
            args,
        )
        try:
            await spec.handler(ctx, args)
        except asyncio.CancelledError:
            self.command_logger.warning("Eksekusi command dibatalkan: %s", spec.name)
            raise
        except Exception:
            logger.exception("Error saat menjalankan perintah %s", spec.name)
            try:
                await ctx.reply("Terjadi error internal saat menjalankan perintah.")
            except Exception:
                logger.exception("Gagal mengirim notifikasi error ke pengguna untuk %s", spec.name)
                self.command_logger.exception(
                    "Gagal mengirim notifikasi error ke pengguna untuk command=%s",
                    spec.name,
                )
            else:
                self.command_logger.info(
                    "Notifikasi error terkirim ke pengguna untuk command=%s",
                    spec.name,
                )
            self.command_logger.error("Command %s gagal", spec.name, exc_info=True)
            raise
        else:
            logger.info("Perintah %s selesai dieksekusi", spec.name)
            self.command_logger.info("Command selesai tanpa error: %s", spec.name)

    def _on_task_done(self, task: asyncio.Task, command_name: str) -> None:
        self._tasks.discard(task)
        if task.cancelled():
            logger.warning("Perintah %s dibatalkan sebelum selesai", command_name)
            self.command_logger.warning(
                "Task dibatalkan command=%s sisa_task=%s aktif=%s",
                command_name,
                len(self._tasks),
                [t.get_name() or f"task-{id(t)}" for t in self._tasks],
            )
            return
        exception = task.exception()
        if exception:
            logger.error(
                "Perintah %s selesai dengan error: %s",
                command_name,
                exception,
                exc_info=(exception.__class__, exception, exception.__traceback__),
            )
            self.command_logger.error(
                "Perintah %s selesai dengan error: %s (task tersisa=%s, aktif=%s)",
                command_name,
                exception,
                len(self._tasks),
                [t.get_name() or f"task-{id(t)}" for t in self._tasks],
                exc_info=(exception.__class__, exception, exception.__traceback__),
            )
        else:
            self.command_logger.info(
                "Task selesai command=%s sisa_task=%s aktif=%s",
                command_name,
                len(self._tasks),
                [t.get_name() or f"task-{id(t)}" for t in self._tasks],
            )

    def _ensure_command_logger(self, log_dir: str | Path | None) -> None:
        if log_dir is None:
            return
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_path = log_path / "userbot_commands.log"
        already_configured = any(
            getattr(handler, "baseFilename", None) == str(file_path)
            for handler in self.command_logger.handlers
        )
        if not already_configured:
            handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=2)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.command_logger.addHandler(handler)
        self.command_logger.setLevel(logging.INFO)
        self.command_logger.propagate = False
