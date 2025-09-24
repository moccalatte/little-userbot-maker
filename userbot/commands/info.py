"""Implementasi !info untuk ringkasan fitur aktif."""
from __future__ import annotations

from typing import List, Optional

from .base import CommandContext, CommandSpec
from .registry import register
from .utils import build_target_name_map, format_target_names


def _format_rule_list(items: list[str]) -> str:
    return ", ".join(items) if items else "-"


async def handle_info(ctx: CommandContext, args: list[str]) -> None:
    rg = ctx.reply_guard.get_status()
    rules = rg.get("rules", [])

    sg = ctx.scheduler.get_status()
    jobs = sg.get("jobs", [])

    scr = ctx.scraper.get_status()
    sessions = scr.get("sessions", [])

    target_lists: List[Optional[List[int]]] = []
    target_lists.extend(rule.get("targets") for rule in rules if rule.get("targets"))
    target_lists.extend(job.get("targets") for job in jobs if job.get("targets"))
    target_lists.extend(session.get("targets") for session in sessions if session.get("targets"))

    name_map = (
        await build_target_name_map(ctx.client, target_lists)
        if any(target_lists)
        else {}
    )

    lines: list[str] = ["Ringkasan status fitur:", "", "Reply Guard:"]
    lines.append(f"  Total rule: {len(rules)} (rate limit {rg.get('rate_limit', ctx.rate_limit_seconds)}s)")
    if rules:
        for rule in rules[:3]:
            lines.append(
                f"    #{rule.get('id')} -> include: {_format_rule_list(rule.get('include', []))}, group: {format_target_names(rule.get('targets'), name_map)}"
            )
        if len(rules) > 3:
            lines.append(f"    ... +{len(rules) - 3} rule lain")
    else:
        lines.append("    (tidak ada rule aktif)")

    lines.extend(["", "Scheduler:"])
    lines.append(f"  Total job: {len(jobs)} (rate limit {sg.get('rate_limit_seconds', ctx.rate_limit_seconds)}s)")
    if jobs:
        for job in jobs[:3]:
            lines.append(
                f"    #{job.get('id')} -> interval {job.get('interval_minutes', 0)}m, group: {format_target_names(job.get('targets'), name_map)}, pesan: {job.get('message') or '(kosong)'}"
            )
        if len(jobs) > 3:
            lines.append(f"    ... +{len(jobs) - 3} job lain")
    else:
        lines.append("    (tidak ada job broadcast)")

    lines.extend(["", "Scraper:"])
    lines.append(f"  Total session: {len(sessions)}")
    if sessions:
        for session in sessions[:3]:
            rules_data = session.get("rules", {})
            lines.append(
                "    #%s -> include: %s, group: %s, matched: %s, tersimpan: %s"
                % (
                    session.get("id"),
                    _format_rule_list(rules_data.get("include", [])),
                    format_target_names(session.get("targets"), name_map),
                    session.get("matched_count", 0),
                    "ADA" if session.get("output_available") else "TIDAK",
                )
            )
        if len(sessions) > 3:
            lines.append(f"    ... +{len(sessions) - 3} session lain")
    else:
        lines.append("    (tidak ada session aktif)")

    await ctx.reply("\n".join(lines))


register(
    CommandSpec(
        name="info",
        description="Tampilkan status singkat seluruh fitur yang berjalan.",
        usage="",
        handler=handle_info,
        help_text="Tampilkan ringkasan status Reply Guard, scheduler broadcast, dan scraper dalam satu perintah.",
    )
)
