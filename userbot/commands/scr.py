"""Implementasi !scr untuk listener."""
from __future__ import annotations

from typing import Optional

from telethon.tl.types import Channel, Chat, User

from common.validators import parse_rules_json

from ..rules_store import RulesStore
from ..scheduler import SchedulerError, resolve_targets
from .base import CommandContext, CommandSpec
from .registry import register


async def handle_scr(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply(
            "Usage: !scr status | stop [id]|off | '<rules_json>' <target|allgroup>"
        )
        return
    command = args[0].lower()
    if command == "status":
        status = ctx.scraper.get_status()
        sessions = status.get("sessions", [])
        if not sessions:
            await ctx.reply("Belum ada session listener aktif.")
            return
        lines = ["Status Scraper:"]
        for session in sessions:
            targets = session.get("targets")
            if targets is None:
                target_desc = "allgroup"
            elif targets:
                preview = ", ".join(str(item) for item in targets[:5])
                if len(targets) > 5:
                    preview += f", +{len(targets) - 5}"
                target_desc = preview
            else:
                target_desc = "-"
            rules = session.get("rules", {})
            lines.extend(
                [
                    "",
                    f"ID #{session.get('id')} (stored: {'ADA' if session.get('output_available') else 'TIDAK'})",
                    f"  Include: {', '.join(rules.get('include', [])) or '-'}",
                    f"  Exclude: {', '.join(rules.get('exclude', [])) or '-'}",
                    f"  Regex: {', '.join(rules.get('regex', [])) or '-'}",
                    f"  Target: {target_desc}",
                    f"  Pesan cocok: {session.get('matched_count', 0)}",
                ]
            )
        await ctx.reply("\n".join(lines))
        return
    if command in {"stop", "off"}:
        target_id: Optional[int] = None
        if len(args) > 1:
            try:
                target_id = int(args[1])
            except ValueError:
                await ctx.reply("Format: !scr stop <id_session> atau !scr stop untuk memadamkan semua.")
                return
        changed = await ctx.scraper.stop(target_id)
        if target_id is None:
            if changed:
                await ctx.reply("Seluruh session listener dimatikan dan buffer disimpan.")
            else:
                await ctx.reply("Tidak ada session listener yang aktif.")
        else:
            if changed:
                await ctx.reply(f"Session listener #{target_id} dimatikan.")
            else:
                await ctx.reply(f"Session listener #{target_id} tidak ditemukan.")
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
        session_id = await ctx.scraper.start(rules, targets)
    except Exception as exc:
        await ctx.reply(f"Gagal mengaktifkan listener: {exc}")
        return
    RulesStore(ctx.storage).save_rules(rules, targets)
    target_desc = await _describe_targets(ctx, targets)
    await ctx.reply(
        "Listener ON dengan ID #%d! %s. Pesan yang cocok akan dicatat ke CSV di folder data/. "
        "Gunakan !scr stop <id> untuk menghentikan session ini."
        % (session_id, target_desc)
    )


register(
    CommandSpec(
        name="scr",
        description="Aktifkan listener pesan grup dengan rules JSON.",
        usage="status | stop [id]|off | '<rules_json>' <target|allgroup>",
        handler=handle_scr,
        help_text=(
            "Fungsi: memantau pesan grup dan menyimpan pesan yang cocok dengan kata kunci atau pola tertentu ke file CSV.\n\n"
            "Langkah singkat:\n"
            "1. Buat rules JSON dengan kunci include/exclude/regex (boleh kosong).\n"
            "   Contoh: '{\"include\": [\"promo\"], \"exclude\": [\"hoax\"], \"regex\": []}'.\n"
            "2. Tentukan target: 'allgroup' atau daftar ID dipisah koma.\n"
            "3. Jalankan perintah dengan format !scr '<rules_json>' <target>.\n\n"
            "Contoh:\n"
            "!scr '{\"include\": [\"promo\"], \"exclude\": [\"hoax\"], \"regex\": []}' allgroup\n"
            "!scr '{\"include\": [\"need\"], \"exclude\": [], \"regex\": []}' 123456789\n\n"
            "Perintah tambahan:\n"
            "- !scr status — melihat daftar session aktif beserta ID-nya.\n"
            "- !scr stop — memadamkan semua session.\n"
            "- !scr stop <id> — memadamkan session tertentu."
        ),
    )
)


async def _describe_targets(ctx: CommandContext, targets: list[int]) -> str:
    if not targets:
        return "(tanpa target)"

    dialogs = await ctx.client.get_dialogs()
    mapping: dict[int, tuple[str, str]] = {}
    for dialog in dialogs:
        entity = getattr(dialog, "entity", None)
        if entity is None:
            continue
        name = dialog.name or getattr(entity, "title", None) or getattr(entity, "first_name", "(tanpa nama)")
        if isinstance(entity, Channel):
            kind = "channel" if bool(getattr(entity, "broadcast", False)) else "group"
        elif isinstance(entity, Chat):
            kind = "group"
        elif isinstance(entity, User):
            kind = "user"
        else:
            kind = "chat"
        mapping[entity.id] = (kind, name)

    def _normalize(chat_id: int) -> int:
        if chat_id < 0 and str(chat_id).startswith("-100"):
            try:
                return int(str(chat_id)[4:])
            except ValueError:
                return chat_id
        return chat_id

    descriptions: list[str] = []
    for chat_id in targets[:3]:
        kind, name = mapping.get(_normalize(chat_id), ("chat", "(tidak diketahui)"))
        descriptions.append(f"({kind}: {name} id={chat_id})")
    if len(targets) > 3:
        descriptions.append(f"dan {len(targets) - 3} target lain")
    return ", ".join(descriptions)
