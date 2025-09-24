"""Implementasi !rg untuk auto-reply guard."""
from __future__ import annotations

import re
from typing import List, Optional

from .base import CommandContext, CommandSpec
from .registry import register

USAGE = "<include|-|a,b> <exclude|-|x,y> <regex|-|pattern> <target|allgroup> <reply_text>"


def _split_items(raw: str) -> List[str]:
    raw = raw.strip()
    if not raw or raw == "-":
        return []
    items = [item.strip() for item in raw.split(",")]
    return [item for item in items if item]


def _parse_regex(raw: str) -> List[str]:
    patterns = _split_items(raw)
    for pattern in patterns:
        try:
            re.compile(pattern)
        except re.error as exc:
            raise ValueError(f"Regex tidak valid: {pattern} ({exc})") from exc
    return patterns


def _parse_targets(raw: str) -> Optional[List[int]]:
    raw = raw.strip()
    if not raw:
        raise ValueError("Target tidak boleh kosong.")
    if raw.lower() == "allgroup":
        return None
    targets: List[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            targets.append(int(item))
        except ValueError as exc:
            raise ValueError(f"ID target tidak valid: {item}") from exc
    if not targets:
        raise ValueError("Tidak ada target yang valid.")
    return targets


async def handle_rg(ctx: CommandContext, args: list[str]) -> None:
    if not args:
        await ctx.reply(f"Usage: !rg {USAGE}")
        return

    command = args[0].lower()
    if command in {"stop", "off"}:
        if ctx.reply_guard.is_active:
            ctx.reply_guard.deactivate()
            await ctx.reply("Reply guard dimatikan.")
        else:
            ctx.reply_guard.deactivate()
            await ctx.reply("Reply guard sudah nonaktif.")
        return

    if len(args) < 5:
        await ctx.reply(f"Argumen kurang. Format: !rg {USAGE}")
        return

    include = _split_items(args[0])
    exclude = _split_items(args[1])

    try:
        regex = _parse_regex(args[2])
    except ValueError as exc:
        await ctx.reply(str(exc))
        return

    try:
        targets = _parse_targets(args[3])
    except ValueError as exc:
        await ctx.reply(str(exc))
        return

    reply_text = " ".join(args[4:]).strip()
    if not reply_text:
        await ctx.reply("Pesan balasan tidak boleh kosong.")
        return

    try:
        image_path = await ctx.reply_guard.capture_media(ctx.event.message)
    except ValueError as exc:
        await ctx.reply(str(exc))
        return

    try:
        ctx.reply_guard.activate(
            include=include,
            exclude=exclude,
            regex=regex,
            targets=targets,
            reply_text=reply_text,
            me_id=ctx.me_id,
            reply_image=image_path,
        )
    except ValueError as exc:
        await ctx.reply(str(exc))
        return
    except Exception as exc:
        await ctx.reply(f"Gagal mengaktifkan reply guard: {exc}")
        return

    summary = ctx.reply_guard.summarize()
    await ctx.reply(
        "Reply guard aktif. "
        f"Include: {', '.join(include) if include else '-'}, "
        f"Exclude: {', '.join(exclude) if exclude else '-'}, "
        f"Regex: {', '.join(regex) if regex else '-'}; {summary}"
    )


register(
    CommandSpec(
        name="rg",
        description="Balas otomatis pesan grup berdasar kata kunci.",
        usage=USAGE,
        handler=handle_rg,
        help_text=(
            "Aktifkan auto-reply di grup. Format: !rg <include> <exclude> <regex> <target|allgroup> <reply_text>.\n"
            "Jika ingin menyertakan gambar, lampirkan fotonya di pesan yang sama saat mengirim perintah ini. Caption balasan akan memakai reply_text.\n"
            "Gunakan tanda koma untuk banyak kata, atau '-' bila kosong. Semua kata di include wajib muncul, exclude menolak, regex dinilai cocok jika salah satu pola match.\n"
            "Contoh: lampirkan gambar lalu kirim !rg promo,deal hoax - allgroup Terima kasih infonya!\n"
            "Matikan dengan !rg stop atau !rg off."
        ),
    )
)
