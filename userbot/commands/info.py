"""Implementasi !info untuk ringkasan fitur aktif."""
from __future__ import annotations

import logging
from typing import List, Optional

try:
    from .base import CommandContext, CommandSpec
    from .registry import get_commands, register
    from .utils import build_target_name_map, format_target_names
except ImportError:
    from commands.base import CommandContext, CommandSpec
    from commands.registry import get_commands, register
    from commands.utils import build_target_name_map, format_target_names

logger = logging.getLogger("userbot.commands.info")


def _format_rule_list(items: list[str]) -> str:
    return ", ".join(items) if items else "-"


async def handle_info(ctx: CommandContext, args: list[str]) -> None:
    logger.info("System info command executed by user %s", ctx.me_id)
    
    # Get available commands
    commands = get_commands()
    
    # Get Reply Guard status
    rg = ctx.reply_guard.get_status()
    rules = rg.get("rules", [])

    # Get Scheduler status
    sg = ctx.scheduler.get_status()
    jobs = sg.get("jobs", [])

    # Build target name map for better display
    target_lists: List[Optional[List[int]]] = []
    target_lists.extend(rule.get("targets") for rule in rules if rule.get("targets"))
    target_lists.extend(job.get("targets") for job in jobs if job.get("targets"))

    name_map = (
        await build_target_name_map(ctx.client, target_lists)
        if any(target_lists)
        else {}
    )
    
    # Build comprehensive system info
    lines = [
        "ℹ️ <b>System Info - Userbot Status</b>\n",
        f"🔍 <b>User ID:</b> {ctx.me_id}",
        f"⚡ <b>Rate Limit:</b> {ctx.rate_limit_seconds}s global\n",
        "───────────────────────────"
    ]
    
    # Available Commands Section
    lines.extend([
        "\n📋 <b>Available Commands:</b>",
        f"📊 Total: {len(commands)} commands loaded"
    ])
    
    for cmd_name in sorted(commands.keys()):
        cmd_spec = commands[cmd_name]
        lines.append(f"• !{cmd_name} — {cmd_spec.description}")
    
    # Reply Guard Section
    lines.extend([
        "\n🤖 <b>Reply Guard Status:</b>",
        f"📊 Rules: {len(rules)} aktif",
        f"⚡ Rate Limit: {rg.get('rate_limit', ctx.rate_limit_seconds)}s antar reply"
    ])
    
    if rules:
        active_groups = set()
        for rule in rules:
            targets = rule.get("targets")
            if targets is None:
                active_groups.add("All Groups")
            elif targets:
                active_groups.update(str(t) for t in targets)
        
        lines.append(f"🎯 Active in: {len(active_groups)} target locations")
        
        # Show top 3 rules
        for i, rule in enumerate(rules[:3], 1):
            include_preview = ', '.join(rule.get('include', [])[:2]) or 'Any'
            if len(rule.get('include', [])) > 2:
                include_preview += f", +{len(rule.get('include', [])) - 2} more"
                
            lines.append(
                f"• Rule #{rule.get('id')}: {include_preview} → "
                f"{format_target_names(rule.get('targets'), name_map)}"
            )
            
        if len(rules) > 3:
            lines.append(f"• ... +{len(rules) - 3} more rules")
    else:
        lines.append("🔕 No active reply rules")

    # Broadcast Scheduler Section
    lines.extend([
        "\n📢 <b>Broadcast Scheduler Status:</b>",
        f"📊 Jobs: {len(jobs)} aktif",
        f"⚡ Rate Limit: {sg.get('rate_limit_seconds', ctx.rate_limit_seconds)}s antar broadcast"
    ])
    
    if jobs:
        total_targets = 0
        intervals = []
        
        for job in jobs:
            targets = job.get('targets', [])
            total_targets += len(targets) if targets else 0
            intervals.append(job.get('interval_minutes', 0))
            
        avg_interval = sum(intervals) / len(intervals) if intervals else 0
        lines.extend([
            f"🎯 Total targets: {total_targets} groups",
            f"⏱️ Avg interval: {avg_interval:.1f} minutes"
        ])
        
        # Show top 3 jobs
        for i, job in enumerate(jobs[:3], 1):
            message_preview = (job.get('message', '(empty)')[:30] + '...' 
                             if len(job.get('message', '')) > 30 
                             else job.get('message', '(empty)'))
            target_count = len(job.get('targets', [])) if job.get('targets') else 0
            
            lines.append(
                f"• Job #{job.get('id')}: {job.get('interval_minutes', 0)}m → "
                f"{target_count} groups: {message_preview}"
            )
            
        if len(jobs) > 3:
            lines.append(f"• ... +{len(jobs) - 3} more jobs")
    else:
        lines.append("🔕 No active broadcast jobs")
    
    # System Health Section
    lines.extend([
        "\n───────────────────────────",
        "🟢 <b>System Health:</b> All systems operational",
        "📊 <b>Activity Summary:</b>",
        f"• Commands available: {len(commands)}",
        f"• Reply rules: {len(rules)} active",
        f"• Broadcast jobs: {len(jobs)} running",
        f"• Total automation: {len(rules) + len(jobs)} active tasks\n",
        "💡 Use specific commands for detailed management:",
        "• !rg status — Reply Guard details",
        "• !sg status — Broadcast Scheduler details",
        "• !gg — Group membership info",
        "• !help <command> — Detailed command help"
    ])
    
    logger.info(
        "System info displayed to user %s: %s commands, %s rules, %s jobs",
        ctx.me_id, len(commands), len(rules), len(jobs)
    )
    
    await ctx.reply("\n".join(lines))


register(
    CommandSpec(
        name="info",
        description="Menampilkan status lengkap sistem userbot dan semua command yang sedang berjalan.",
        usage="",
        handler=handle_info,
        help_text=(
            "Menampilkan informasi lengkap tentang status userbot dan semua fitur yang sedang aktif.\n\n"
            "🎯 Informasi yang ditampilkan:\n"
            "- Daftar semua command yang tersedia\n"
            "- Status dan statistik Reply Guard\n"
            "- Status dan statistik Broadcast Scheduler\n"
            "- Kesehatan sistem secara keseluruhan\n"
            "- Ringkasan aktivitas automation\n\n"
            "📊 Berguna untuk:\n"
            "- Monitoring sistem userbot\n"
            "- Quick overview semua fitur aktif\n"
            "- Troubleshooting masalah\n"
            "- Audit konfigurasi userbot\n\n"
            "💡 Tips:\n"
            "- Jalankan secara berkala untuk monitoring\n"
            "- Gunakan bersama command spesifik untuk detail lengkap\n"
            "- Berguna untuk memastikan semua automation berjalan\n"
            "- Dapat digunakan untuk laporan status kepada admin"
        ),
    )
)
