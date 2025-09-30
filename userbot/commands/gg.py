"""Implementasi !gg untuk daftar grup."""
from __future__ import annotations

import logging

try:
    from ..state import PaginationState
    from .base import CommandContext, CommandSpec
    from .registry import register
except ImportError:
    from state import PaginationState
    from commands.base import CommandContext, CommandSpec
    from commands.registry import register

logger = logging.getLogger("userbot.commands.gg")


async def handle_gg(ctx: CommandContext, args: list[str]) -> None:
    logger.info("Get group info command executed by user %s with args: %s", ctx.me_id, args)
    
    owner_state = ctx.runtime.pagination.setdefault(ctx.me_id, PaginationState())
    command = args[0].lower() if args else ""
    
    logger.debug("Processing gg command: '%s', current items count: %s", command, len(owner_state.items))
    
    if command in {"refresh", ""} and not owner_state.items:
        await _refresh_groups(ctx, owner_state)
    elif command == "refresh":
        logger.info("Refreshing groups list for user %s", ctx.me_id)
        await _refresh_groups(ctx, owner_state)
    elif command == "next":
        if not owner_state.items:
            logger.warning("User %s tried 'next' without data", ctx.me_id)
            await ctx.reply("Belum ada data. Jalankan !gg dulu.")
            return
        owner_state.next_page()
        logger.debug("User %s navigated to next page: %s", ctx.me_id, owner_state.page + 1)
    elif command == "prev":
        if not owner_state.items:
            logger.warning("User %s tried 'prev' without data", ctx.me_id)
            await ctx.reply("Belum ada data. Jalankan !gg dulu.")
            return
        owner_state.prev_page()
        logger.debug("User %s navigated to prev page: %s", ctx.me_id, owner_state.page + 1)
    else:
        if owner_state.items:
            owner_state.page = 0
        else:
            await _refresh_groups(ctx, owner_state)

    await _send_page(ctx, owner_state)


async def _refresh_groups(ctx: CommandContext, state: PaginationState) -> None:
    logger.info("Refreshing groups list for user %s", ctx.me_id)
    
    try:
        dialogs = await ctx.client.get_dialogs()
        logger.debug("Retrieved %s total dialogs for user %s", len(dialogs), ctx.me_id)
        
        items: list[str] = []
        group_count = 0
        channel_count = 0
        
        for dialog in dialogs:
            entity = getattr(dialog, "entity", None)
            if entity is None:
                continue
                
            if getattr(dialog, "is_group", False):
                group_count += 1
                title = dialog.name or getattr(entity, "title", "(tanpa nama)")
                items.append(f"{entity.id} — {title} [GROUP]")
            elif getattr(dialog, "is_channel", False):
                channel_count += 1
                title = dialog.name or getattr(entity, "title", "(tanpa nama)")
                items.append(f"{entity.id} — {title} [CHANNEL]")
                
        state.items = items
        state.page = 0
        
        logger.info(
            "Groups refreshed for user %s: %s groups, %s channels, %s total",
            ctx.me_id, group_count, channel_count, len(items)
        )
        
    except Exception as e:
        logger.error("Failed to refresh groups for user %s: %s", ctx.me_id, e, exc_info=True)
        raise


async def _send_page(ctx: CommandContext, state: PaginationState) -> None:
    if not state.items:
        logger.warning("No groups found for user %s", ctx.me_id)
        await ctx.reply(
            "📭 Tidak ada grup atau channel yang ditemukan.\n\n"
            "💡 Untuk menggunakan userbot:\n"
            "1. Bergabung dengan grup menggunakan akun Telegram\n"
            "2. Jalankan !gg refresh untuk memperbarui daftar"
        )
        return
        
    page_items = state.current_page_items()
    total_pages = max(1, (len(state.items) + state.page_size - 1) // state.page_size)
    
    # Count groups and channels
    groups = sum(1 for item in state.items if "[GROUP]" in item)
    channels = sum(1 for item in state.items if "[CHANNEL]" in item)
    
    header = (
        f"📋 Daftar Grup & Channel (Halaman {state.page + 1}/{total_pages})\n"
        f"📊 Total: {len(state.items)} ({groups} groups, {channels} channels)\n"
        f"───────────────────────────\n"
    )
    
    footer = (
        "\n───────────────────────────\n"
        "🔄 !gg refresh — perbarui daftar\n"
        "➡️ !gg next — halaman berikutnya\n"
        "⬅️ !gg prev — halaman sebelumnya\n\n"
        "💡 Salin ID grup untuk !sg dan !rg commands"
    )
    
    logger.info(
        "Displaying page %s/%s (%s items) to user %s",
        state.page + 1, total_pages, len(page_items), ctx.me_id
    )
    
    await ctx.reply("\n".join([header, *page_items, footer]))


register(
    CommandSpec(
        name="gg",
        description="Ambil daftar semua grup dan channel yang diikuti dengan ID dan nama.",
        usage="[next|prev|refresh]",
        handler=handle_gg,
        help_text=(
            "Mengambil daftar lengkap grup dan channel yang diikuti userbot beserta ID dan nama.\n\n"
            "🎯 Kegunaan:\n"
            "- Melihat semua grup yang bisa digunakan untuk broadcast (!sg)\n"
            "- Mendapatkan ID grup untuk reply guard rules (!rg)\n"
            "- Monitoring membership userbot\n\n"
            "📋 Commands:\n"
            "- !gg           → tampilkan halaman pertama (50 entri per halaman)\n"
            "- !gg next      → halaman berikutnya\n"
            "- !gg prev      → halaman sebelumnya\n"
            "- !gg refresh   → muat ulang daftar dari Telegram\n\n"
            "📊 Output Format:\n"
            "ID_GRUP — NAMA_GRUP [GROUP/CHANNEL]\n\n"
            "💡 Tips:\n"
            "- Salin ID grup (angka negatif) untuk digunakan di !sg dan !rg\n"
            "- Format: -1001234567890 (supergroup) atau -123456789 (basic group)\n"
            "- Refresh berkala untuk update membership"
        ),
    )
)
