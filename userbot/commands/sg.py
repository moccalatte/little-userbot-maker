"""Implementasi !sg untuk broadcast terjadwal."""
from __future__ import annotations

from ..scheduler import BroadcastScheduler, SchedulerError, resolve_targets
from .base import CommandContext, CommandSpec
from .registry import register
from common.validators import validate_interval_minutes


async def handle_sg(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply("Usage: !sg \"pesan\" <interval_menit> <target|allgroup> atau !sg stop")
        return
    command = args[0].lower()
    if command in {"stop", "off"}:
        await ctx.scheduler.stop()
        await ctx.reply("Broadcast dihentikan.")
        return
    if len(args) < 3:
        await ctx.reply("Argumen kurang. Format: !sg \"pesan\" <interval_menit> <target|allgroup>")
        return
    message = args[0]
    try:
        interval = validate_interval_minutes(args[1])
    except ValueError as exc:
        await ctx.reply(str(exc))
        return
    target_spec = args[2]
    try:
        targets = await resolve_targets(ctx.client, target_spec)
    except SchedulerError as exc:
        await ctx.reply(str(exc))
        return
    if not targets:
        await ctx.reply("Tidak ditemukan target group.")
        return
    try:
        await ctx.scheduler.start(message, interval, targets)
    except SchedulerError as exc:
        await ctx.reply(str(exc))
        return
    await ctx.reply(f"Broadcast dimulai setiap {interval} menit ke {len(targets)} target.")


register(
    CommandSpec(
        name="sg",
        description="Jadwalkan broadcast ke grup dengan interval menit.",
        usage='"pesan" <interval_menit> <target|allgroup> | stop|off',
        handler=handle_sg,
    )
)
