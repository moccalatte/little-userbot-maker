"""Implementasi !info untuk ringkasan fitur aktif."""
from __future__ import annotations

from .base import CommandContext, CommandSpec
from .registry import register


def _format_targets(targets: list[int] | None) -> str:
    if targets is None:
        return "allgroup"
    if not targets:
        return "-"
    preview = ", ".join(str(item) for item in targets[:5])
    if len(targets) > 5:
        preview += f", +{len(targets) - 5}"
    return preview


def _format_rule_list(items: list[str]) -> str:
    return ", ".join(items) if items else "-"


async def handle_info(ctx: CommandContext, args: list[str]) -> None:
    lines: list[str] = ["Ringkasan status fitur:", "", "Reply Guard:"]

    rg = ctx.reply_guard.get_status()
    rules = rg.get("rules", [])
    lines.append(f"  Total rule: {len(rules)} (rate limit {rg.get('rate_limit', ctx.rate_limit_seconds)}s)")
    if rules:
        for rule in rules[:3]:
            lines.append(
                f"    #{rule.get('id')} -> include: {_format_rule_list(rule.get('include', []))}, target: {_format_targets(rule.get('targets'))}"
            )
        if len(rules) > 3:
            lines.append(f"    ... +{len(rules) - 3} rule lain")
    else:
        lines.append("    (tidak ada rule aktif)")

    sg = ctx.scheduler.get_status()
    jobs = sg.get("jobs", [])
    lines.extend(["", "Scheduler:"])
    lines.append(f"  Total job: {len(jobs)} (rate limit {sg.get('rate_limit_seconds', ctx.rate_limit_seconds)}s)")
    if jobs:
        for job in jobs[:3]:
            lines.append(
                f"    #{job.get('id')} -> interval {job.get('interval_minutes', 0)}m, target: {_format_targets(job.get('targets') or [])}, pesan: {job.get('message') or '(kosong)'}"
            )
        if len(jobs) > 3:
            lines.append(f"    ... +{len(jobs) - 3} job lain")
    else:
        lines.append("    (tidak ada job broadcast)")

    scr = ctx.scraper.get_status()
    sessions = scr.get("sessions", [])
    lines.extend(["", "Scraper:"])
    lines.append(f"  Total session: {len(sessions)}")
    if sessions:
        for session in sessions[:3]:
            rules = session.get("rules", {})
            lines.append(
                "    #%s -> include: %s, target: %s, matched: %s, tersimpan: %s"
                % (
                    session.get("id"),
                    _format_rule_list(rules.get("include", [])),
                    _format_targets(session.get("targets")),
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
