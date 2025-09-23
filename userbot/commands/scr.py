"""Implementasi !scr untuk listener."""
from __future__ import annotations

from common.validators import parse_rules_json

from ..rules_store import RulesStore
from ..scheduler import SchedulerError, resolve_targets
from .base import CommandContext, CommandSpec
from .registry import register


async def handle_scr(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply(
            "Usage: !scr '<rules_json>' <target|allgroup> atau !scr stop"
        )
        return
    command = args[0].lower()
    if command in {"stop", "off"}:
        await ctx.scraper.stop()
        await ctx.reply("Mode scrape dihentikan dan buffer disimpan.")
        return
    if len(args) < 2:
        await ctx.reply(
            "Argumen kurang. Format: !scr '<rules_json>' <target|allgroup>"
        )
        return
    raw_rules = " ".join(args[:-1])
    target_spec = args[-1]
    try:
        rules = parse_rules_json(raw_rules)
    except ValueError as exc:
        await ctx.reply(str(exc))
        return
    try:
        targets = await resolve_targets(ctx.client, target_spec)
    except SchedulerError as exc:
        await ctx.reply(str(exc))
        return
    if not targets:
        await ctx.reply("Tidak ditemukan target group.")
        return
    try:
        await ctx.scraper.start(rules, targets)
    except Exception as exc:
        await ctx.reply(f"Gagal mengaktifkan listener: {exc}")
        return
    RulesStore(ctx.storage).save_rules(rules, targets)
    await ctx.reply(
        "Listener aktif untuk %s target. Pesan yang cocok akan dicatat ke CSV di folder data/. "
        "Gunakan !scr stop untuk menghentikan."
        % len(targets)
    )


register(
    CommandSpec(
        name="scr",
        description="Aktifkan listener pesan grup dengan rules JSON.",
        usage="'<rules_json>' <target|allgroup> | stop|off",
        handler=handle_scr,
        help_text=(
            "Aktifkan mode scraping pesan grup berbasis rules JSON.\n\n"
            "Argumen rules_json mendukung tiga kunci:\n"
            "- include: daftar kata kunci yang wajib ada dalam pesan.\n"
            "- exclude: daftar kata kunci yang jika muncul akan menolak pesan.\n"
            "- regex: daftar pola regex opsional untuk filter lanjutan.\n"
            "Semua pencocokan tidak peka huruf besar kecil.\n\n"
            "Target mendukung kata kunci allgroup atau daftar ID dipisah koma.\n\n"
            "Contoh:\n"
            "!scr '{\"include\": [\"promo\", \"diskon\"], \"exclude\": [\"hoax\"], \"regex\": []}' allgroup\n"
            "!scr '{\"include\": [\"need\"], \"exclude\": [], \"regex\": []}' 123456789\n\n"
            "Gunakan !scr stop atau !scr off untuk menghentikan listener dan menyimpan buffer ke file."
        ),
    )
)
