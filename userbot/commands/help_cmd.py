"""Implementasi !help."""
from __future__ import annotations

from .base import CommandContext, CommandSpec
from .registry import get_commands, register


async def handle_help(ctx: CommandContext, args: list[str]) -> None:
    lines = ["Daftar perintah:"]
    for spec in get_commands().values():
        lines.append(f"- !{spec.name} {spec.usage} — {spec.description}")
    await ctx.reply("\n".join(lines))


register(
    CommandSpec(
        name="help",
        description="Tampilkan bantuan dan usage perintah.",
        usage="",
        handler=handle_help,
    )
)
