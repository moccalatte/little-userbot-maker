"""Helper untuk menyamarkan data sensitif sebelum logging."""
from __future__ import annotations

from hashlib import sha256


def mask_phone(phone: str) -> str:
    """Kembalikan hash singkat dari nomor telepon untuk log tanpa bocor data."""
    digest = sha256(phone.encode("utf-8")).hexdigest()
    return f"hash:{digest[:8]}"


def mask_session(session: str) -> str:
    """Potong session string agar tidak muncul penuh di log."""
    if len(session) <= 10:
        return "***"
    return session[:5] + "..." + session[-5:]


def mask_api_hash(api_hash: str) -> str:
    """Masking hash API agar log tetap berguna."""
    if not api_hash:
        return ""
    return api_hash[:4] + "***" + api_hash[-4:]

