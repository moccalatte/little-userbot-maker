"""Implementasi !gg untuk daftar grup."""
from __future__ import annotations

from ..state import PaginationState
from .base import CommandContext, CommandSpec
from .registry import register


async def handle_gg(ctx: CommandContext, args: list[str]) -> None:
    owner_state = ctx.runtime.pagination.setdefault(ctx.me_id, PaginationState())
    command = args[0].lower() if args else ""
    if command in {"refresh", ""} and not owner_state.items:
        await _refresh_groups(ctx, owner_state)
    elif command == "refresh":
        await _refresh_groups(ctx, owner_state)
    elif command == "next":
        if not owner_state.items:
            await ctx.event.reply("Belum ada data. Jalankan !gg dulu.")
            return
        owner_state.next_page()
    elif command == "prev":
        if not owner_state.items:
            await ctx.event.reply("Belum ada data. Jalankan !gg dulu.")
            return
        owner_state.prev_page()
    else:
        if owner_state.items:
            owner_state.page = 0
        else:
            await _refresh_groups(ctx, owner_state)

    await _send_page(ctx, owner_state)


async def _refresh_groups(ctx: CommandContext, state: PaginationState) -> None:
    dialogs = await ctx.client.get_dialogs()
    items: list[str] = []
    for dialog in dialogs:
        entity = getattr(dialog, "entity", None)
        if entity is None:
            continue
        if getattr(dialog, "is_group", False) or getattr(dialog, "is_channel", False):
            title = dialog.name or getattr(entity, "title", "(tanpa nama)")
            items.append(f"{entity.id} — {title}")
    state.items = items
    state.page = 0


async def _send_page(ctx: CommandContext, state: PaginationState) -> None:
    if not state.items:
        await ctx.event.reply("Tidak ada grup yang ditemukan. Gunakan Telegram untuk bergabung.")
        return
    page_items = state.current_page_items()
    total_pages = max(1, (len(state.items) + state.page_size - 1) // state.page_size)
    header = f"Halaman {state.page + 1}/{total_pages}. Gunakan !gg next/prev untuk navigasi."
    footer = "Ketik !gg refresh untuk memuat ulang. Untuk ekspor, salin daftar ini ke CSV manual."
    await ctx.event.reply("\n".join([header, *page_items, footer]))


register(
    CommandSpec(
        name="gg",
        description="Tampilkan ID grup yang tergabung.",
        usage="[next|prev|refresh]",
        handler=handle_gg,
    )
)

