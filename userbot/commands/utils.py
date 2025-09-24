"""Utility helpers for command formatting."""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Set

from telethon import TelegramClient
from telethon.tl.types import Channel, Chat, User


def _expand_chat_variants(chat_id: int) -> Set[int]:
    variants = {chat_id}
    if chat_id > 0:
        variants.add(-1000000000000 - chat_id)
    elif chat_id < 0 and str(chat_id).startswith("-100"):
        try:
            variants.add(int(str(chat_id)[4:]))
        except ValueError:
            pass
    return variants


async def build_target_name_map(
    client: TelegramClient, target_lists: Sequence[Optional[Iterable[int]]]
) -> Dict[int, str]:
    desired: Set[int] = set()
    for targets in target_lists:
        if not targets:
            continue
        for target in targets:
            desired.update(_expand_chat_variants(int(target)))
    if not desired:
        return {}

    dialogs = await client.get_dialogs()
    mapping: Dict[int, str] = {}
    for dialog in dialogs:
        entity = getattr(dialog, "entity", None)
        if entity is None:
            continue
        name = dialog.name or getattr(entity, "title", None) or getattr(entity, "first_name", "") or ""
        if not name:
            name = str(getattr(entity, "id", ""))
        entity_id = getattr(entity, "id", None)
        if entity_id is None:
            continue
        for variant in _expand_chat_variants(int(entity_id)):
            mapping[variant] = name
    result: Dict[int, str] = {}
    for item in desired:
        result[item] = mapping.get(item, str(item))
    return result


def format_target_names(
    targets: Optional[Sequence[int]], name_map: Dict[int, str], limit: int = 3
) -> str:
    if targets is None:
        return "allgroup"
    if not targets:
        return "-"
    names: List[str] = [name_map.get(int(target), str(target)) for target in targets]
    preview = names[:limit]
    summary = ", ".join(preview)
    if len(names) > limit:
        summary += f", +{len(names) - limit}"
    return summary or "-"
