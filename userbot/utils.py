"""Userbot utilities: crypto and validators."""
from __future__ import annotations

import base64
import json
from typing import Any, Optional

from cryptography.fernet import Fernet, InvalidToken


# ============================================================================
# CRYPTO FUNCTIONS
# ============================================================================

class EncryptionError(RuntimeError):
    """Dilempar saat enkripsi/dekripsi gagal."""


def build_cipher(secret_key: Optional[str]) -> Optional[Fernet]:
    if not secret_key:
        return None
    key = secret_key.encode("utf-8")
    try:
        # Validasi panjang kunci Fernet
        Fernet(key)
    except Exception as exc:  # broad: validasi internal fernet
        raise EncryptionError("SECRET_KEY tidak valid untuk Fernet.") from exc
    return Fernet(key)


def ensure_secret_key(secret_key: Optional[str]) -> str:
    if not secret_key:
        raise EncryptionError("SECRET_KEY wajib diisi jika ingin menyimpan rahasia.")
    return secret_key


def encrypt_text(cipher: Fernet, text: str) -> str:
    try:
        return cipher.encrypt(text.encode("utf-8")).decode("utf-8")
    except Exception as exc:
        raise EncryptionError("Gagal mengenkripsi data.") from exc


def decrypt_text(cipher: Fernet, token: str) -> str:
    try:
        return cipher.decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise EncryptionError("Token enkripsi tidak valid.") from exc


def derive_fernet_key(source: str) -> str:
    """Konversi string pendek jadi key fernet base64 32 byte jika user belum punya."""
    raw = source.encode("utf-8")
    padded = raw.ljust(32, b"0")[:32]
    return base64.urlsafe_b64encode(padded).decode("utf-8")


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

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