"""Implementasi !sg untuk broadcast terjadwal."""
from __future__ import annotations

import logging
from typing import Optional

try:
    from ..scheduler import BroadcastScheduler, SchedulerError, resolve_targets
    from .base import CommandContext, CommandSpec
    from .registry import register
    from .utils import build_target_name_map, format_target_names
    from ..utils import validate_interval_minutes
except ImportError:
    from scheduler import BroadcastScheduler, SchedulerError, resolve_targets
    from commands.base import CommandContext, CommandSpec
    from commands.registry import register
    from commands.utils import build_target_name_map, format_target_names
    from utils import validate_interval_minutes

logger = logging.getLogger("userbot.commands.sg")


async def handle_sg(ctx: CommandContext, args: list[str]) -> None:
    logger.info("Broadcast scheduler command executed by user %s with args: %s", ctx.me_id, args)
    
    if not args:
        logger.warning("User %s called !sg without arguments", ctx.me_id)
        await ctx.reply(
            "📢 <b>Broadcast Scheduler Usage:</b>\n\n"
            "• !sg status — lihat semua broadcast aktif\n"
            "• !sg stop [id] — hentikan broadcast (semua atau ID tertentu)\n"
            "• !sg \"pesan\" <menit> allgroup — broadcast ke semua grup\n"
            "• !sg \"pesan\" <menit> -ID1,-ID2 — broadcast ke grup spesifik\n\n"
            "Contoh:\n"
            "!sg \"Reminder standup jam 9\" 30 allgroup\n"
            "!sg \"Promo spesial\" 60 -1001234,-1005678"
        )
        return
        
    command = args[0].lower()
    
    if command == "status":
        logger.info("User %s requested broadcast status", ctx.me_id)
        status = ctx.scheduler.get_status()
        jobs = status.get("jobs", [])
        
        if not jobs:
            logger.debug("No active broadcast jobs for user %s", ctx.me_id)
            await ctx.reply(
                "📢 <b>Status Broadcast Scheduler</b>\n\n"
                "🔕 Belum ada jadwal broadcast aktif.\n\n"
                "💡 Untuk membuat broadcast:\n"
                "!sg \"pesan\" <menit> allgroup"
            )
            return
            
        target_lists = [job.get("targets") for job in jobs if job.get("targets")]
        name_map = (
            await build_target_name_map(ctx.client, target_lists)
            if target_lists
            else {}
        )
        
        lines = [
            "📢 <b>Status Broadcast Scheduler</b>\n",
            f"⚡ Rate Limit: {status.get('rate_limit_seconds', ctx.rate_limit_seconds)}s antar pesan",
            f"📊 Total Jobs: {len(jobs)} aktif\n",
            "───────────────────────────"
        ]
        
        for i, job in enumerate(jobs, 1):
            targets = job.get("targets", [])
            if targets:
                preview = ", ".join(str(item) for item in targets[:3])
                if len(targets) > 3:
                    preview += f", +{len(targets) - 3} lainnya"
                target_desc = f"{len(targets)} groups: {preview}"
            else:
                target_desc = "Tidak ada target"
                
            message_preview = job.get('message', '(kosong)')[:50]
            if len(job.get('message', '')) > 50:
                message_preview += "..."
                
            lines.extend([
                f"\n🔸 <b>Job #{job.get('id')}</b>",
                f"📝 Pesan: {message_preview}",
                f"⏱️ Interval: {job.get('interval_minutes', 0)} menit",
                f"🎯 Target: {target_desc}",
                f"👥 Groups: {format_target_names(targets, name_map)}"
            ])
            
        lines.extend([
            "\n───────────────────────────",
            "💡 Gunakan !sg stop <id> untuk menghentikan job tertentu"
        ])
        
        logger.info("Displayed %s broadcast jobs status to user %s", len(jobs), ctx.me_id)
        await ctx.reply("\n".join(lines))
        return
    if command in {"stop", "off"}:
        job_id: Optional[int] = None
        if len(args) > 1:
            try:
                job_id = int(args[1])
            except ValueError:
                logger.warning("User %s provided invalid job ID: %s", ctx.me_id, args[1])
                await ctx.reply(
                    "❌ <b>Format salah!</b>\n\n"
                    "✅ Format yang benar:\n"
                    "• !sg stop — hentikan semua broadcast\n"
                    "• !sg stop <id> — hentikan broadcast dengan ID tertentu\n\n"
                    "💡 Gunakan !sg status untuk melihat ID broadcast aktif"
                )
                return
                
        logger.info("User %s stopping broadcast jobs (job_id: %s)", ctx.me_id, job_id or "all")
        
        try:
            changed = await ctx.scheduler.stop(job_id)
            
            if job_id is None:
                if changed:
                    logger.info("User %s stopped all broadcast jobs", ctx.me_id)
                    await ctx.reply(
                        "✅ <b>Semua Broadcast Dihentikan</b>\n\n"
                        "🔕 Semua jadwal broadcast telah dihentikan.\n\n"
                        "💡 Gunakan !sg untuk membuat broadcast baru"
                    )
                else:
                    logger.debug("User %s tried to stop jobs but none were active", ctx.me_id)
                    await ctx.reply(
                        "ℹ️ <b>Tidak Ada Broadcast Aktif</b>\n\n"
                        "🔕 Tidak ada jadwal broadcast yang sedang berjalan.\n\n"
                        "💡 Gunakan !sg status untuk melihat status"
                    )
            else:
                if changed:
                    logger.info("User %s stopped broadcast job #%s", ctx.me_id, job_id)
                    await ctx.reply(
                        f"✅ <b>Broadcast #{job_id} Dihentikan</b>\n\n"
                        f"🔕 Jadwal broadcast #{job_id} telah dihentikan.\n\n"
                        "💡 Gunakan !sg status untuk melihat broadcast lainnya"
                    )
                else:
                    logger.warning("User %s tried to stop non-existent job #%s", ctx.me_id, job_id)
                    await ctx.reply(
                        f"❌ <b>Job #{job_id} Tidak Ditemukan</b>\n\n"
                        f"🔍 Job broadcast #{job_id} tidak ditemukan atau sudah tidak aktif.\n\n"
                        "💡 Gunakan !sg status untuk melihat job aktif"
                    )
                    
        except Exception as e:
            logger.error("Error stopping broadcast jobs for user %s: %s", ctx.me_id, e, exc_info=True)
            await ctx.reply("❌ Terjadi kesalahan saat menghentikan broadcast. Coba lagi.")
            
        return
    if len(args) < 3:
        logger.warning("User %s provided insufficient arguments: %s", ctx.me_id, len(args))
        await ctx.reply(
            "❌ <b>Argumen kurang!</b>\n\n"
            "✅ Format yang benar:\n"
            "!sg \"pesan\" <interval_menit> <target>\n\n"
            "📝 <b>Contoh:</b>\n"
            "• !sg \"Hello World\" 30 allgroup\n"
            "• !sg \"Reminder penting\" 60 -1001234,-1005678\n\n"
            "💡 <b>Tips:</b>\n"
            "- Gunakan tanda petik untuk pesan dengan spasi\n"
            "- Interval minimal 1 menit\n"
            "- Target: 'allgroup' atau daftar ID grup\n"
            "- Gunakan !gg untuk melihat ID grup"
        )
        return
        
    message = args[0]
    
    # Validate message
    if not message or len(message.strip()) == 0:
        logger.warning("User %s provided empty message", ctx.me_id)
        await ctx.reply(
            "❌ <b>Pesan kosong!</b>\n\n"
            "📝 Pesan broadcast tidak boleh kosong.\n\n"
            "💡 Contoh: !sg \"Hello World\" 30 allgroup"
        )
        return
        
    if len(message) > 4096:
        logger.warning("User %s provided message too long: %s chars", ctx.me_id, len(message))
        await ctx.reply(
            f"❌ <b>Pesan terlalu panjang!</b>\n\n"
            f"📏 Panjang: {len(message)} karakter (maks 4096)\n\n"
            "✂️ Persingkat pesan Anda."
        )
        return
        
    try:
        interval = validate_interval_minutes(args[1])
        logger.debug("User %s set interval: %s minutes", ctx.me_id, interval)
    except ValueError as exc:
        logger.warning("User %s provided invalid interval: %s (%s)", ctx.me_id, args[1], exc)
        await ctx.reply(
            f"❌ <b>Interval tidak valid!</b>\n\n"
            f"📊 Error: {str(exc)}\n\n"
            "✅ <b>Aturan interval:</b>\n"
            "• Minimal 1 menit\n"
            "• Maksimal 10080 menit (1 minggu)\n"
            "• Harus berupa angka bulat\n\n"
            "💡 Contoh: 30 (untuk 30 menit)"
        )
        return
        
    target_spec = args[2]
    logger.debug("User %s specified targets: %s", ctx.me_id, target_spec)
    
    try:
        targets = await resolve_targets(ctx.client, target_spec)
        logger.info("Resolved %s targets for user %s broadcast", len(targets), ctx.me_id)
    except SchedulerError as exc:
        logger.error("Target resolution failed for user %s: %s", ctx.me_id, exc)
        await ctx.reply(
            f"❌ <b>Target tidak valid!</b>\n\n"
            f"🔍 Error: {str(exc)}\n\n"
            "✅ <b>Format target yang benar:</b>\n"
            "• 'allgroup' — broadcast ke semua grup\n"
            "• ID grup tunggal: -1001234567890\n"
            "• Multiple ID: -1001234,-1005678\n\n"
            "💡 Gunakan !gg untuk melihat daftar grup dan ID-nya"
        )
        return
        
    if not targets:
        logger.warning("No valid targets found for user %s broadcast", ctx.me_id)
        await ctx.reply(
            "❌ <b>Tidak ada target grup!</b>\n\n"
            "🔍 Tidak ditemukan grup yang valid untuk broadcast.\n\n"
            "💡 <b>Kemungkinan penyebab:</b>\n"
            "• ID grup salah atau tidak valid\n"
            "• Userbot bukan member grup tersebut\n"
            "• Tidak ada grup yang diikuti (untuk 'allgroup')\n\n"
            "🔧 Gunakan !gg untuk melihat grup yang tersedia"
        )
        return
        
    try:
        logger.info(
            "Starting broadcast for user %s: message=%s chars, interval=%s min, targets=%s",
            ctx.me_id, len(message), interval, len(targets)
        )
        
        job_id = await ctx.scheduler.start(message, interval, targets)
        
        logger.info(
            "Broadcast job #%s started successfully for user %s to %s targets",
            job_id, ctx.me_id, len(targets)
        )
        
        # Get target names for confirmation
        target_lists = [targets] if targets else []
        name_map = await build_target_name_map(ctx.client, target_lists) if target_lists else {}
        target_names = format_target_names(targets, name_map)
        
        await ctx.reply(
            f"✅ <b>Broadcast #{job_id} Dimulai!</b>\n\n"
            f"📝 <b>Pesan:</b> {message[:100]}{'...' if len(message) > 100 else ''}\n"
            f"⏱️ <b>Interval:</b> {interval} menit\n"
            f"🎯 <b>Target:</b> {len(targets)} grup\n"
            f"👥 <b>Groups:</b> {target_names}\n\n"
            "💡 Gunakan !sg status untuk monitoring"
        )
        
    except SchedulerError as exc:
        logger.error("Failed to start broadcast for user %s: %s", ctx.me_id, exc, exc_info=True)
        await ctx.reply(
            f"❌ <b>Gagal memulai broadcast!</b>\n\n"
            f"🔍 Error: {str(exc)}\n\n"
            "💡 Coba lagi dalam beberapa saat atau hubungi admin"
        )
        return
    except Exception as e:
        logger.error("Unexpected error starting broadcast for user %s: %s", ctx.me_id, e, exc_info=True)
        await ctx.reply("❌ Terjadi kesalahan sistem. Coba lagi nanti.")
        return


register(
    CommandSpec(
        name="sg",
        description="Jadwalkan pesan broadcast otomatis ke semua grup atau grup tertentu.",
        usage='status | stop [id] | "pesan" <menit> <target>',
        handler=handle_sg,
        help_text=(
            "Mengirim pesan otomatis berulang ke grup/channel dengan interval yang ditentukan.\n\n"
            "🎯 Kegunaan:\n"
            "- Reminder otomatis (standup, meeting, deadline)\n"
            "- Promosi dan pengumuman berkala\n"
            "- Notifikasi sistem atau status update\n\n"
            "📋 Commands:\n"
            "- !sg status → lihat semua broadcast yang sedang berjalan\n"
            "- !sg stop → hentikan semua broadcast\n"
            "- !sg stop <id> → hentikan broadcast dengan ID tertentu\n"
            "- !sg \"pesan\" <menit> <target> → buat broadcast baru\n\n"
            "📊 Parameter:\n"
            "• Pesan: teks yang akan dikirim (maks 4096 karakter)\n"
            "• Interval: jeda antar pengiriman dalam menit (min 1, maks 10080)\n"
            "• Target: 'allgroup' untuk semua grup, atau daftar ID grup\n\n"
            "📝 Contoh Penggunaan:\n"
            "!sg \"Reminder standup jam 9\" 60 allgroup\n"
            "!sg \"Promo spesial hari ini\" 30 -1001234567890\n"
            "!sg \"Update server\" 120 -1001234,-1005678\n\n"
            "💡 Tips:\n"
            "- Gunakan tanda petik untuk pesan dengan spasi\n"
            "- Gunakan !gg untuk melihat daftar grup dan ID-nya\n"
            "- Rate limit: ada jeda antar pengiriman untuk mencegah spam\n"
            "- Broadcast berjalan sampai dihentikan manual"
        ),
    )
)
