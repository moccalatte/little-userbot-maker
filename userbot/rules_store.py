"""Penyimpanan rules listener ke JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from common.storage import ScrapeStorage


class RulesStore:
    def __init__(self, storage: ScrapeStorage) -> None:
        self.path = storage.directory / "rules.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_rules(self, rules: Dict[str, List[str]], chat_ids: List[int] | None = None) -> None:
        payload: Dict[str, Any] = {"rules": rules}
        if chat_ids is not None:
            payload["chat_ids"] = list(dict.fromkeys(chat_ids))
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def load_rules(self) -> Dict[str, List[str]]:
        data = self._read_json()
        if isinstance(data, dict) and "rules" in data:
            return data["rules"]
        if isinstance(data, dict):
            return data
        return {"include": [], "exclude": [], "regex": []}

    def load_chat_ids(self) -> List[int]:
        data = self._read_json()
        if isinstance(data, dict):
            raw = data.get("chat_ids", [])
            if isinstance(raw, list):
                result: List[int] = []
                for item in raw:
                    try:
                        result.append(int(item))
                    except (TypeError, ValueError):
                        continue
                return list(dict.fromkeys(result))
        return []

    def _read_json(self) -> Any:
        if not self.path.exists():
            return None
        with self.path.open("r", encoding="utf-8") as handle:
            try:
                return json.load(handle)
            except json.JSONDecodeError:
                return None
