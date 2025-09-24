"""Implementasi !sg untuk broadcast terjadwal."""
from __future__ import annotations

from typing import Optional

from ..scheduler import BroadcastScheduler, SchedulerError, resolve_targets
from .base import CommandContext, CommandSpec
from .registry import register
from .utils import build_target_name_map, format_target_names
from common.validators import validate_interval_minutes


async def handle_sg(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply("Usage: !sg status | stop [id]|off | \"pesan\" <interval_menit> <target|allgroup>")
        return
    command = args[0].lower()
    if command == "status":
        status = ctx.scheduler.get_status()
        jobs = status.get("jobs", [])
        if not jobs:
            await ctx.reply("Belum ada jadwal broadcast aktif.")
            return
        target_lists = [job.get("targets") for job in jobs if job.get("targets")]
        name_map = (
            await build_target_name_map(ctx.client, target_lists)
            if target_lists
            else {}
        )
        lines = ["Status Scheduler (rate limit %ss):" % status.get("rate_limit_seconds", ctx.rate_limit_seconds)]
        for job in jobs:
            targets = job.get("targets", [])
            if targets:
                preview = ", ".join(str(item) for item in targets[:5])
                if len(targets) > 5:
                    preview += f", +{len(targets) - 5}"
                target_desc = preview
            else:
                target_desc = "-"
            lines.extend(
                [
                    "",
                    f"ID #{job.get('id')}",
                    f"  Pesan: {job.get('message') or '(kosong)'}",
                    f"  Interval: {job.get('interval_minutes', 0)} menit",
                    f"  Target: {target_desc}",
                    f"  Group: {format_target_names(targets, name_map)}",
                ]
            )
        await ctx.reply("\n".join(lines))
        return
    if command in {"stop", "off"}:
        job_id: Optional[int] = None
        if len(args) > 1:
            try:
                job_id = int(args[1])
            except ValueError:
                await ctx.reply("Format: !sg stop <id_job> atau !sg stop untuk memadamkan semua jadwal.")
                return
        changed = await ctx.scheduler.stop(job_id)
        if job_id is None:
            if changed:
                await ctx.reply("Semua jadwal broadcast dihentikan.")
            else:
                await ctx.reply("Tidak ada jadwal broadcast yang aktif.")
        else:
            if changed:
                await ctx.reply(f"Jadwal broadcast #{job_id} dihentikan.")
            else:
                await ctx.reply(f"Jadwal broadcast #{job_id} tidak ditemukan.")
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
        job_id = await ctx.scheduler.start(message, interval, targets)
    except SchedulerError as exc:
        await ctx.reply(str(exc))
        return
    await ctx.reply(
        "Broadcast #{0} dimulai setiap {1} menit ke {2} target.".format(job_id, interval, len(targets))
    )


register(
    CommandSpec(
        name="sg",
        description="Jadwalkan broadcast ke grup dengan interval menit.",
        usage='status | stop [id]|off | "pesan" <interval_menit> <target|allgroup>',
        handler=handle_sg,
        help_text=(
            "Fungsi: mengirim pesan otomatis berulang ke grup/channel tertentu.\n\n"
            "Langkah singkat:\n"
            "1. Siapkan isi pesan. Gunakan tanda petik jika kalimat memiliki spasi.\n"
            "2. Tentukan jeda kirim dalam menit. Gunakan angka bulat di atas 0.\n"
            "3. Pilih target: tulis 'allgroup' atau daftar ID dipisah koma.\n\n"
            "Contoh:\n"
            "!sg \"Reminder standup jam 9\" 30 allgroup\n"
            "!sg \"Promo spesial siang ini\" 60 123456789,987654321\n\n"
            "Perintah tambahan:\n"
            "- !sg status — melihat daftar job aktif beserta ID-nya.\n"
            "- !sg stop — memadamkan semua job.\n"
            "- !sg stop <id> — memadamkan job tertentu."
        ),
    )
)
