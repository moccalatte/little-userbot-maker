"""Implementasi !rg untuk auto-reply guard."""
from __future__ import annotations

import re
from typing import List, Optional

from .base import CommandContext, CommandSpec
from .registry import register
from .utils import build_target_name_map, format_target_names

USAGE = "status | stop [id]|off | <include|-|a,b> <exclude|-|x,y> <regex|-|pattern> <target|allgroup> <reply_text>"


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
    if command == "status":
        state = ctx.reply_guard.get_status()
        rules = state.get("rules", [])
        if not rules:
            await ctx.reply("Belum ada rule aktif. Gunakan !rg untuk menambahkan.")
            return
        target_lists = [rule.get("targets") for rule in rules if rule.get("targets")]
        name_map = (
            await build_target_name_map(ctx.client, target_lists)
            if target_lists
            else {}
        )
        lines = ["Status Reply Guard (rate limit %ss):" % state.get("rate_limit", ctx.rate_limit_seconds)]
        for rule in rules:
            targets = rule.get("targets")
            if targets is None:
                target_desc = "allgroup"
            elif targets:
                preview = ", ".join(str(item) for item in targets[:5])
                if len(targets) > 5:
                    preview += f", +{len(targets) - 5}"
                target_desc = preview
            else:
                target_desc = "-"
            lines.extend(
                [
                    "",
                    f"ID #{rule.get('id')}",
                    f"  Include: {', '.join(rule.get('include', [])) or '-'}",
                    f"  Exclude: {', '.join(rule.get('exclude', [])) or '-'}",
                    f"  Regex: {', '.join(rule.get('regex', [])) or '-'}",
                    f"  Target: {target_desc}",
                    f"  Group: {format_target_names(targets, name_map)}",
                    f"  Media: {'ADA' if rule.get('has_media') else 'TIDAK'}",
                    f"  Balasan: {rule.get('reply_text') or '(kosong)'}",
                ]
            )
        await ctx.reply("\n".join(lines))
        return

    if command in {"stop", "off"}:
        rule_id: Optional[int] = None
        if len(args) > 1:
            try:
                rule_id = int(args[1])
            except ValueError:
                await ctx.reply("Format: !rg stop <id_rule> atau !rg stop untuk memadamkan semua.")
                return
        changed = ctx.reply_guard.deactivate(rule_id)
        if rule_id is None:
            if changed:
                await ctx.reply("Seluruh rule reply guard dimatikan.")
            else:
                await ctx.reply("Tidak ada rule yang sedang aktif.")
        else:
            if changed:
                await ctx.reply(f"Rule reply guard #{rule_id} dimatikan.")
            else:
                await ctx.reply(f"Rule reply guard #{rule_id} tidak ditemukan.")
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
        rule_id = ctx.reply_guard.activate(
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

    target_desc: str
    if targets is None:
        target_desc = "allgroup"
    elif targets:
        preview = ", ".join(str(item) for item in targets[:5])
        if len(targets) > 5:
            preview += f", +{len(targets) - 5}"
        target_desc = preview
    else:
        target_desc = "-"
    await ctx.reply(
        "Reply guard aktif dengan ID #%d. Include: %s | Exclude: %s | Regex: %s | Target: %s."
        % (
            rule_id,
            ", ".join(include) if include else "-",
            ", ".join(exclude) if exclude else "-",
            ", ".join(regex) if regex else "-",
            target_desc,
        )
    )


register(
    CommandSpec(
        name="rg",
        description="Balas otomatis pesan grup berdasar kata kunci.",
        usage=USAGE,
        handler=handle_rg,
        help_text=(
            "Fungsi: membuat bot membalas otomatis pesan grup ketika mendeteksi kata kunci tertentu.\n\n"
            "Langkah cepat:\n"
            "1. Tentukan kata wajib (include), kata yang dilarang (exclude), dan pola regex bila diperlukan. Gunakan '-' jika ingin dikosongkan.\n"
            "2. Pilih target: 'allgroup' untuk semua grup/channel, atau daftar ID (pisah koma).\n"
            "3. Tulis balasan. Jika ingin menyertakan foto, lampirkan fotonya bersamaan saat mengirim perintah.\n\n"
            "Contoh tanpa foto:\n"
            "!rg need - - 2056122904 Ada yang bisa kami bantu?\n\n"
            "Contoh dengan foto (lampirkan foto, lalu kirim perintah):\n"
            "!rg promo - diskon allgroup Terima kasih infonya!\n\n"
            "Perintah tambahan:\n"
            "- !rg status — melihat daftar rule aktif beserta ID-nya.\n"
            "- !rg stop — memadamkan semua rule.\n"
            "- !rg stop <id> — memadamkan rule tertentu (lihat ID di !rg status)."
        ),
    )
)
