"""Kumpulan validator sederhana untuk input pengguna."""
from __future__ import annotations

import json
import re
from typing import Any

E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
API_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


def validate_phone(phone: str) -> str:
    phone = phone.strip()
    if not E164_PATTERN.fullmatch(phone):
        raise ValueError("Nomor telepon harus format E.164, contoh +6281234567890.")
    return phone


def validate_api_id(raw: str) -> int:
    raw = raw.strip()
    if not raw.isdigit():
        raise ValueError("API ID harus berupa angka.")
    value = int(raw)
    if value <= 0:
        raise ValueError("API ID harus lebih besar dari 0.")
    return value


def validate_api_hash(api_hash: str) -> str:
    api_hash = api_hash.strip()
    if not API_HASH_PATTERN.fullmatch(api_hash):
        raise ValueError("API hash harus 32 karakter hex.")
    return api_hash


def validate_interval_minutes(raw: str, minimum: int = 5) -> int:
    raw = raw.strip()
    if not raw.isdigit():
        raise ValueError("Interval harus berupa angka menit.")
    value = int(raw)
    if value < minimum:
        raise ValueError(f"Interval minimal {minimum} menit.")
    return value


def parse_rules_json(raw: str) -> dict[str, list[str]]:
    try:
        data: dict[str, Any] = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("Format rules harus JSON valid.") from exc

    include = _ensure_list_of_str(data.get("include", []), "include")
    exclude = _ensure_list_of_str(data.get("exclude", []), "exclude")
    regex = _ensure_list_of_str(data.get("regex", []), "regex")
    return {"include": include, "exclude": exclude, "regex": regex}


def _ensure_list_of_str(value: Any, key: str) -> list[str]:
    if value in (None, ""):
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Field {key} harus berupa list string.")
    return value

