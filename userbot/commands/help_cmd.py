"""Implementasi !help."""
from __future__ import annotations

from .base import CommandContext, CommandSpec
from .registry import get_commands, register


async def handle_help(ctx: CommandContext, args: list[str]) -> None:
    commands = get_commands()
    if args:
        target = args[0].lower()
        spec = commands.get(target)
        if not spec:
            await ctx.reply("Menu tidak dikenal. Ketik !help untuk daftar perintah yang tersedia.")
            return
        usage_part = f" {spec.usage}" if spec.usage else ""
        lines = [f"!{spec.name}{usage_part}"]
        lines.append(spec.description)
        help_text = (spec.help_text or "Panduan detail belum tersedia untuk perintah ini.").strip()
        if help_text:
            lines.append("")
            lines.append(help_text)
        await ctx.reply("\n".join(lines))
        return

    lines = ["Daftar perintah:"]
    for spec in sorted(commands.values(), key=lambda item: item.name):
        usage_part = f" {spec.usage}" if spec.usage else ""
        lines.append(f"- !{spec.name}{usage_part} — {spec.description}")
    lines.extend(
        [
            "",
            "Catatan: ketik !help <nama_menu> untuk menampilkan panduan pemakaian lengkap.",
        ]
    )
    await ctx.reply("\n".join(lines))


register(
    CommandSpec(
        name="help",
        description="Tampilkan bantuan dan usage perintah.",
        usage="",
        handler=handle_help,
        help_text=(
            "Gunakan !help tanpa argumen untuk melihat semua menu. "
            "Untuk melihat panduan rinci satu menu, kirim !help <nama_menu>."
        ),
    )
)
