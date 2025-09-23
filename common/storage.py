"""Lapisan penyimpanan sederhana (JSON/CSV) sesuai PRD."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any, Iterable, Optional

from .masking import mask_phone


ISO_FORMAT = "%Y-%m-%dT%H:%M:%SZ"


@dataclass(slots=True)
class SessionRecord:
    phone_hash: str
    session: str
    created_at: str
    encrypted: bool
    owner_id: int
    metadata: dict[str, Any] = field(default_factory=dict)


class SessionRepository:
    """Kelola penyimpanan session dalam JSON."""

    def __init__(self, data_path: Path) -> None:
        self._path = data_path
        self._lock = Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write([])

    def save(self, record: SessionRecord) -> None:
        with self._lock:
            records = self._read()
            records.append(asdict(record))
            # Batasi 100 entri
            if len(records) > 100:
                records = records[-100:]
            self._write(records)

    def delete_by_owner(self, owner_id: int) -> int:
        with self._lock:
            records = self._read()
            filtered = [r for r in records if r.get("owner_id") != owner_id]
            removed = len(records) - len(filtered)
            self._write(filtered)
            return removed

    def list_by_owner(self, owner_id: int) -> list[SessionRecord]:
        with self._lock:
            records = self._read()
        return [SessionRecord(**r) for r in records if r.get("owner_id") == owner_id]

    def _read(self) -> list[dict[str, Any]]:
        with self._path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return []

    def _write(self, data: list[dict[str, Any]]) -> None:
        with self._path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)


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
                    "message_text",
                    "rule_tag",
                ]
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                if not file_exists:
                    writer.writeheader()
                for row in rows:
                    writer.writerow(row)
            return file_path


def hash_phone_for_storage(phone: str) -> str:
    return mask_phone(phone)


def now_utc() -> str:
    return datetime.utcnow().strftime(ISO_FORMAT)
