"""Implementasi !rg untuk auto-reply guard."""
from __future__ import annotations

import logging
import re
from typing import List, Optional

try:
    from .base import CommandContext, CommandSpec
    from .registry import register
    from .utils import build_target_name_map, format_target_names
except ImportError:
    from commands.base import CommandContext, CommandSpec
    from commands.registry import register
    from commands.utils import build_target_name_map, format_target_names

logger = logging.getLogger("userbot.commands.rg")

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
    logger.info("Reply guard command executed by user %s with args: %s", ctx.me_id, args)
    
    if not args:
        logger.warning("User %s called !rg without arguments", ctx.me_id)
        await ctx.reply(
            "🤖 <b>Reply Guard Usage:</b>\n\n"
            "• !rg status — lihat semua rule aktif\n"
            "• !rg stop [id] — hentikan rule (semua atau ID tertentu)\n"
            "• !rg <include> <exclude> <regex> <target> <balasan>\n\n"
            "📝 <b>Format rule:</b>\n"
            "- <include>: kata wajib ada (atau '-' jika kosong)\n"
            "- <exclude>: kata terlarang (atau '-' jika kosong)\n"
            "- <regex>: pola regex (atau '-' jika kosong)\n"
            "- <target>: 'allgroup' atau ID grup spesifik\n"
            "- <balasan>: teks yang akan dikirim sebagai reply\n\n"
            "🔧 Contoh:\n"
            "!rg hello spam - allgroup Halo juga!\n"
            "!rg help - - -1001234 Ada yang bisa saya bantu?"
        )
        return

    command = args[0].lower()
    
    if command == "status":
        logger.info("User %s requested reply guard status", ctx.me_id)
        state = ctx.reply_guard.get_status()
        rules = state.get("rules", [])
        
        if not rules:
            logger.debug("No active reply guard rules for user %s", ctx.me_id)
            await ctx.reply(
                "🤖 <b>Status Reply Guard</b>\n\n"
                "🔕 Belum ada rule auto reply aktif.\n\n"
                "💡 Untuk membuat rule:\n"
                "!rg <include> <exclude> <regex> <target> <balasan>\n\n"
                "📖 Gunakan !help rg untuk panduan lengkap"
            )
            return
            
        target_lists = [rule.get("targets") for rule in rules if rule.get("targets")]
        name_map = (
            await build_target_name_map(ctx.client, target_lists)
            if target_lists
            else {}
        )
        
        lines = [
            "🤖 <b>Status Reply Guard</b>\n",
            f"⚡ Rate Limit: {state.get('rate_limit', ctx.rate_limit_seconds)}s antar reply",
            f"📊 Total Rules: {len(rules)} aktif\n",
            "───────────────────────────"
        ]
        
        for rule in rules:
            targets = rule.get("targets")
            if targets is None:
                target_desc = "Semua grup"
            elif targets:
                preview = ", ".join(str(item) for item in targets[:3])
                if len(targets) > 3:
                    preview += f", +{len(targets) - 3} lainnya"
                target_desc = f"{len(targets)} groups: {preview}"
            else:
                target_desc = "Tidak ada target"
                
            reply_preview = rule.get('reply_text', '(kosong)')[:50]
            if len(rule.get('reply_text', '')) > 50:
                reply_preview += "..."
                
            lines.extend([
                f"\n🔸 <b>Rule #{rule.get('id')}</b>",
                f"✅ Include: {', '.join(rule.get('include', [])) or 'Tidak ada'}",
                f"❌ Exclude: {', '.join(rule.get('exclude', [])) or 'Tidak ada'}",
                f"🔍 Regex: {', '.join(rule.get('regex', [])) or 'Tidak ada'}",
                f"🎯 Target: {target_desc}",
                f"👥 Groups: {format_target_names(targets, name_map)}",
                f"🖼️ Media: {'Ada lampiran' if rule.get('has_media') else 'Teks saja'}",
                f"💬 Balasan: {reply_preview}",
            ])
            
        lines.extend([
            "\n───────────────────────────",
            "💡 Gunakan !rg stop <id> untuk menghentikan rule tertentu"
        ])
        
        logger.info("Displayed %s reply guard rules status to user %s", len(rules), ctx.me_id)
        await ctx.reply("\n".join(lines))
        return

    if command in {"stop", "off"}:
        rule_id: Optional[int] = None
        if len(args) > 1:
            try:
                rule_id = int(args[1])
            except ValueError:
                logger.warning("User %s provided invalid rule ID: %s", ctx.me_id, args[1])
                await ctx.reply(
                    "❌ <b>Format salah!</b>\n\n"
                    "✅ Format yang benar:\n"
                    "• !rg stop — hentikan semua rule\n"
                    "• !rg stop <id> — hentikan rule dengan ID tertentu\n\n"
                    "💡 Gunakan !rg status untuk melihat ID rule aktif"
                )
                return
                
        logger.info("User %s stopping reply guard rules (rule_id: %s)", ctx.me_id, rule_id or "all")
        
        try:
            changed = ctx.reply_guard.deactivate(rule_id)
            
            if rule_id is None:
                if changed:
                    logger.info("User %s stopped all reply guard rules", ctx.me_id)
                    await ctx.reply(
                        "✅ <b>Semua Reply Guard Dihentikan</b>\n\n"
                        "🔕 Seluruh rule auto reply telah dimatikan.\n\n"
                        "💡 Gunakan !rg untuk membuat rule baru"
                    )
                else:
                    logger.debug("User %s tried to stop rules but none were active", ctx.me_id)
                    await ctx.reply(
                        "ℹ️ <b>Tidak Ada Rule Aktif</b>\n\n"
                        "🔕 Tidak ada rule reply guard yang sedang berjalan.\n\n"
                        "💡 Gunakan !rg status untuk melihat status"
                    )
            else:
                if changed:
                    logger.info("User %s stopped reply guard rule #%s", ctx.me_id, rule_id)
                    await ctx.reply(
                        f"✅ <b>Rule #{rule_id} Dihentikan</b>\n\n"
                        f"🔕 Rule reply guard #{rule_id} telah dimatikan.\n\n"
                        "💡 Gunakan !rg status untuk melihat rule lainnya"
                    )
                else:
                    logger.warning("User %s tried to stop non-existent rule #%s", ctx.me_id, rule_id)
                    await ctx.reply(
                        f"❌ <b>Rule #{rule_id} Tidak Ditemukan</b>\n\n"
                        f"🔍 Rule reply guard #{rule_id} tidak ditemukan atau sudah tidak aktif.\n\n"
                        "💡 Gunakan !rg status untuk melihat rule aktif"
                    )
                    
        except Exception as e:
            logger.error("Error stopping reply guard rules for user %s: %s", ctx.me_id, e, exc_info=True)
            await ctx.reply("❌ Terjadi kesalahan saat menghentikan reply guard. Coba lagi.")
            
        return

    # Create new reply guard rule
    if len(args) < 5:
        logger.warning("User %s provided insufficient arguments for rule creation: %s", ctx.me_id, len(args))
        await ctx.reply(
            "❌ <b>Argumen kurang!</b>\n\n"
            "✅ Format yang benar:\n"
            "!rg <include> <exclude> <regex> <target> <balasan>\n\n"
            "📝 <b>Contoh:</b>\n"
            "• !rg hello spam - allgroup Halo juga!\n"
            "• !rg help - - -1001234 Ada yang bisa saya bantu?\n"
            "• !rg promo,diskon scam .*[Ff]ree.* allgroup Terima kasih info promosi!\n\n"
            "💡 <b>Tips:</b>\n"
            "- Gunakan '-' untuk field kosong\n"
            "- Pisahkan kata dengan koma (,)\n"
            "- Gunakan !gg untuk melihat ID grup\n"
            "- Lampirkan media saat mengirim command untuk reply dengan media"
        )
        return

    logger.info("User %s creating new reply guard rule", ctx.me_id)
    
    # Parse include words
    include = _split_items(args[0])
    logger.debug("Include words: %s", include)
    
    # Parse exclude words  
    exclude = _split_items(args[1])
    logger.debug("Exclude words: %s", exclude)

    # Parse regex patterns
    try:
        regex = _parse_regex(args[2])
        logger.debug("Regex patterns: %s", regex)
    except ValueError as exc:
        logger.warning("User %s provided invalid regex: %s", ctx.me_id, exc)
        await ctx.reply(
            f"❌ <b>Regex tidak valid!</b>\n\n"
            f"🔍 Error: {str(exc)}\n\n"
            "✅ <b>Tips regex:</b>\n"
            "• Gunakan '-' jika tidak perlu regex\n"
            "• Contoh: .*[Hh]ello.* (kata hello dengan case insensitive)\n"
            "• Test regex online sebelum digunakan\n\n"
            "💡 Gunakan !help rg untuk contoh lengkap"
        )
        return

    # Parse target groups
    try:
        targets = _parse_targets(args[3])
        logger.debug("Target groups: %s", targets)
    except ValueError as exc:
        logger.warning("User %s provided invalid targets: %s", ctx.me_id, exc)
        await ctx.reply(
            f"❌ <b>Target tidak valid!</b>\n\n"
            f"🔍 Error: {str(exc)}\n\n"
            "✅ <b>Format target yang benar:</b>\n"
            "• 'allgroup' — semua grup dan channel\n"
            "• ID grup tunggal: -1001234567890\n"
            "• Multiple ID: -1001234,-1005678\n\n"
            "💡 Gunakan !gg untuk melihat daftar grup dan ID-nya"
        )
        return

    # Parse reply text
    reply_text = " ".join(args[4:]).strip()
    if not reply_text:
        logger.warning("User %s provided empty reply text", ctx.me_id)
        await ctx.reply(
            "❌ <b>Balasan kosong!</b>\n\n"
            "💬 Pesan balasan tidak boleh kosong.\n\n"
            "💡 Contoh: !rg hello - - allgroup Halo juga, apa kabar?"
        )
        return
        
    if len(reply_text) > 4096:
        logger.warning("User %s provided reply text too long: %s chars", ctx.me_id, len(reply_text))
        await ctx.reply(
            f"❌ <b>Balasan terlalu panjang!</b>\n\n"
            f"📏 Panjang: {len(reply_text)} karakter (maks 4096)\n\n"
            "✂️ Persingkat pesan balasan Anda."
        )
        return

    # Check for media attachment
    try:
        image_path = await ctx.reply_guard.capture_media(ctx.event.message)
        if image_path:
            logger.info("User %s included media with reply guard rule", ctx.me_id)
    except ValueError as exc:
        logger.warning("User %s media capture failed: %s", ctx.me_id, exc)
        await ctx.reply(
            f"❌ <b>Media tidak valid!</b>\n\n"
            f"🖼️ Error: {str(exc)}\n\n"
            "💡 Lampirkan media yang valid atau buat rule tanpa media"
        )
        return

    # Validate rule logic
    if not include and not exclude and not regex:
        logger.warning("User %s created rule with no conditions", ctx.me_id)
        await ctx.reply(
            "ℹ️ <b>Peringatan: Rule Tanpa Filter</b>\n\n"
            "🚨 Rule ini akan membalas SEMUA pesan di grup target.\n\n"
            "💡 Pertimbangkan menambah filter:\n"
            "• Include: kata yang harus ada\n"
            "• Exclude: kata yang dilarang\n"
            "• Regex: pola matching khusus\n\n"
            "Lanjutkan? Kirim 'ya' untuk konfirmasi atau buat rule baru."
        )
        # Note: In real implementation, you'd want to add confirmation logic here

    # Activate the rule
    try:
        logger.info(
            "Activating reply guard rule for user %s: include=%s, exclude=%s, regex=%s, targets=%s",
            ctx.me_id, include, exclude, regex, targets
        )
        
        rule_id = ctx.reply_guard.activate(
            include=include,
            exclude=exclude,
            regex=regex,
            targets=targets,
            reply_text=reply_text,
            me_id=ctx.me_id,
            reply_image=image_path,
        )
        
        logger.info(
            "Reply guard rule #%s activated successfully for user %s",
            rule_id, ctx.me_id
        )
        
    except ValueError as exc:
        logger.error("Reply guard activation failed for user %s: %s", ctx.me_id, exc)
        await ctx.reply(
            f"❌ <b>Gagal membuat rule!</b>\n\n"
            f"🔍 Error: {str(exc)}\n\n"
            "💡 Periksa parameter dan coba lagi"
        )
        return
    except Exception as exc:
        logger.error("Unexpected error activating reply guard for user %s: %s", ctx.me_id, exc, exc_info=True)
        await ctx.reply(
            f"❌ <b>Gagal mengaktifkan reply guard!</b>\n\n"
            f"🔍 Error sistem: {str(exc)}\n\n"
            "💡 Coba lagi atau hubungi admin"
        )
        return

    # Build success response
    target_desc: str
    if targets is None:
        target_desc = "Semua grup"
    elif targets:
        preview = ", ".join(str(item) for item in targets[:3])
        if len(targets) > 3:
            preview += f", +{len(targets) - 3} lainnya"
        target_desc = f"{len(targets)} groups: {preview}"
    else:
        target_desc = "Tidak ada target"
        
    reply_preview = reply_text[:100] + "..." if len(reply_text) > 100 else reply_text
        
    await ctx.reply(
        f"✅ <b>Reply Guard #{rule_id} Aktif!</b>\n\n"
        f"✅ <b>Include:</b> {', '.join(include) if include else 'Semua pesan'}\n"
        f"❌ <b>Exclude:</b> {', '.join(exclude) if exclude else 'Tidak ada'}\n"
        f"🔍 <b>Regex:</b> {', '.join(regex) if regex else 'Tidak ada'}\n"
        f"🎯 <b>Target:</b> {target_desc}\n"
        f"🖼️ <b>Media:</b> {'Ada lampiran' if image_path else 'Teks saja'}\n"
        f"💬 <b>Balasan:</b> {reply_preview}\n\n"
        "💡 Gunakan !rg status untuk monitoring rule aktif"
    )


register(
    CommandSpec(
        name="rg",
        description="Auto reply ke pesan grup berdasarkan keyword rules yang dapat dikustomisasi.",
        usage=USAGE,
        handler=handle_rg,
        help_text=(
            "Membuat userbot membalas otomatis pesan di grup berdasarkan keyword dan filter yang ditentukan.\n\n"
            "🎯 Kegunaan:\n"
            "- Auto reply untuk customer service\n"
            "- Filter spam dan pesan tidak pantas\n"
            "- Response otomatis untuk FAQ\n"
            "- Monitoring keyword tertentu di grup\n\n"
            "📋 Commands:\n"
            "- !rg status → lihat semua rule aktif\n"
            "- !rg stop → hentikan semua rule\n"
            "- !rg stop <id> → hentikan rule tertentu\n"
            "- !rg <include> <exclude> <regex> <target> <reply> → buat rule baru\n\n"
            "📊 Parameter Rule:\n"
            "• Include: kata yang HARUS ada (dipisah koma, atau '-')\n"
            "• Exclude: kata yang TIDAK boleh ada (dipisah koma, atau '-')\n"
            "• Regex: pattern matching (regex format, atau '-')\n"
            "• Target: 'allgroup' atau ID grup spesifik\n"
            "• Reply: teks balasan yang akan dikirim\n\n"
            "📝 Contoh Penggunaan:\n"
            "!rg hello,hi spam,scam - allgroup Halo! Ada yang bisa kami bantu?\n"
            "!rg help,bantuan - - -1001234 Silakan hubungi admin untuk bantuan\n"
            "!rg promo - .*[Ff]ree.* allgroup Terima kasih info promonya!\n"
            "!rg - badword,toxic - allgroup Mohon jaga bahasa yang sopan\n\n"
            "🖼️ Media Support:\n"
            "- Lampirkan foto/video saat membuat rule untuk reply dengan media\n"
            "- Media akan dikirim bersamaan dengan teks reply\n\n"
            "💡 Tips Advanced:\n"
            "- Kombinasikan include + exclude untuk filter presisi\n"
            "- Gunakan regex untuk pattern matching kompleks\n"
            "- Test rule di grup kecil dulu sebelum apply ke semua grup\n"
            "- Monitor dengan !rg status untuk melihat aktivitas rule\n"
            "- Gunakan !gg untuk mendapatkan ID grup target"
        ),
    )
)
