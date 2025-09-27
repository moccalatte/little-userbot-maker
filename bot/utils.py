"""Bot utilities: crypto, masking, and validators."""
from __future__ import annotations

import base64
import re
from hashlib import sha256
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken

# Validation patterns
E164_PATTERN = re.compile(r"^\+[1-9]\d{7,14}$")
API_HASH_PATTERN = re.compile(r"^[0-9a-fA-F]{32}$")


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
# MASKING FUNCTIONS
# ============================================================================

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


# ============================================================================
# VALIDATION FUNCTIONS
# ============================================================================

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