"""State global userbot."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PaginationState:
    items: List[str] = field(default_factory=list)
    page: int = 0
    page_size: int = 50

    def current_page_items(self) -> List[str]:
        start = self.page * self.page_size
        end = start + self.page_size
        return self.items[start:end]

    def has_next(self) -> bool:
        return (self.page + 1) * self.page_size < len(self.items)

    def has_prev(self) -> bool:
        return self.page > 0

    def next_page(self) -> List[str]:
        if self.has_next():
            self.page += 1
        return self.current_page_items()

    def prev_page(self) -> List[str]:
        if self.has_prev():
            self.page -= 1
        return self.current_page_items()


@dataclass
class UserbotRuntime:
    pagination: Dict[int, PaginationState] = field(default_factory=dict)
    scheduler: Optional["BroadcastScheduler"] = None
    scraper: Optional["ScrapeController"] = None

