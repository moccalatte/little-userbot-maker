"""Scrape storage for userbot."""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional


class ScrapeStorage:
    """Menyimpan hasil listener ke CSV."""

    def __init__(self, directory: Path) -> None:
        self._dir = directory
        self._dir.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()

    @property
    def directory(self) -> Path:
        return self._dir

    def allocate_file(self) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        with self._lock:
            existing = sorted(self._dir.glob(f"scrape_{timestamp}_*.csv"))
            index = len(existing) + 1
            file_path = self._dir / f"scrape_{timestamp}_{index}.csv"
            return file_path

    def append_rows(self, rows: Iterable[dict[str, Any]], file_path: Optional[Path] = None) -> Path:
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        with self._lock:
            if file_path is None:
                existing = sorted(self._dir.glob(f"scrape_{timestamp}_*.csv"))
                if existing:
                    file_path = existing[-1]
                else:
                    file_path = self._dir / f"scrape_{timestamp}_1.csv"
            file_exists = file_path.exists()
            with file_path.open("a", encoding="utf-8", newline="") as csvfile:
                fieldnames = [
                    "timestamp",
                    "chat_id",
                    "chat_title",
                    "sender_username",
                    "message_text",
                    "rule_tag",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return file_path