"""Penyimpanan rules listener ke JSON."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from common.storage import ScrapeStorage


class RulesStore:
    def __init__(self, storage: ScrapeStorage) -> None:
        self.path = storage.directory / "rules.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_rules(self, rules: Dict[str, List[str]]) -> None:
        with self.path.open("w", encoding="utf-8") as handle:
            json.dump(rules, handle, ensure_ascii=False, indent=2)

    def load_rules(self) -> Dict[str, List[str]]:
        if not self.path.exists():
            return {"include": [], "exclude": [], "regex": []}
        with self.path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

