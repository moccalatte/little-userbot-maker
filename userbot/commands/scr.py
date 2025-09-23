"""Implementasi !scr untuk listener."""
from __future__ import annotations

from common.validators import parse_rules_json

from ..rules_store import RulesStore
from .base import CommandContext, CommandSpec
from .registry import register


async def handle_scr(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply(
            "Usage: !scr '{\"include\":[\"keyword\"],\"exclude\":[],\"regex\":[]}' atau !scr stop"
        )
        return
    command = args[0].lower()
    if command in {"stop", "off"}:
        await ctx.scraper.stop()
        await ctx.reply("Mode scrape dihentikan dan buffer disimpan.")
        return
    raw_rules = " ".join(args)
    try:
        rules = parse_rules_json(raw_rules)
    except ValueError as exc:
        await ctx.reply(str(exc))
        return
    try:
        await ctx.scraper.start(rules)
    except Exception as exc:
        await ctx.reply(f"Gagal mengaktifkan listener: {exc}")
        return
    RulesStore(ctx.storage).save_rules(rules)
    await ctx.reply(
        "Listener aktif. Pesan yang cocok akan dicatat ke CSV di folder data/. Gunakan !scr stop untuk menghentikan."
    )


register(
    CommandSpec(
        name="scr",
        description="Aktifkan listener pesan grup dengan rules JSON.",
        usage="'<rules_json>' | stop|off",
        handler=handle_scr,
        help_text=(
            "Aktifkan mode scraping pesan grup berbasis rules JSON.\n\n"
            "Argumen rules_json mendukung tiga kunci:\n"
            "- include: daftar kata kunci yang wajib ada dalam pesan.\n"
            "- exclude: daftar kata kunci yang jika muncul akan menolak pesan.\n"
            "- regex: daftar pola regex opsional untuk filter lanjutan.\n"
            "Semua pencocokan tidak peka huruf besar kecil.\n\n"
            "Contoh:\n"
            "!scr '{\"include\": [\"promo\", \"diskon\"], \"exclude\": [\"hoax\"], \"regex\": []}'\n\n"
            "Gunakan !scr stop atau !scr off untuk menghentikan listener dan menyimpan buffer ke file."
        ),
    )
)
