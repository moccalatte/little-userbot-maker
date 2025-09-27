"""Deteksi dan logging abuse/spam untuk userbot."""
from __future__ import annotations

import logging
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Deque

from .config import setup_logging

# Logger dengan setup konsisten proyek
_logger = setup_logging("userbot_abuse", "INFO")

# Konfigurasi abuse detection
SPAM_THRESHOLD = 5
SPAM_WINDOW = 10  # detik
AUTOREPLY_THRESHOLD = 3
AUTOREPLY_WINDOW = 2  # detik

# Tipe pelanggaran yang didukung
ABUSE_TYPES = [
    "spam",
    "flood", 
    "resource_abuse",
    "illegal_content",
    "system_exploit",
    "crash_command",
    "other",
]

# State management dengan deque untuk efisiensi memory
# Deque otomatis batasi ukuran untuk mencegah memory leak
user_command_history: Dict[int, Deque[datetime]] = defaultdict(lambda: deque(maxlen=20))
user_autoreply_history: Dict[int, Deque[datetime]] = defaultdict(lambda: deque(maxlen=10))

def log_abuse(user_id: int, username: str | None, action: str, detail: str | None = None) -> None:
    """Log aktivitas abuse dari user.
    
    Args:
        user_id: Telegram user ID
        username: Username Telegram (bisa None)
        action: Jenis abuse yang terdeteksi
        detail: Detail tambahan tentang abuse
    """
    username_display = username or "Unknown"
    msg = f"ABUSE DETECTED - User @{username_display} (ID: {user_id}) - Action: {action}"
    if detail:
        msg += f" - Detail: {detail}"
    _logger.warning(msg)  # Gunakan WARNING level untuk abuse

def is_spam(user_id: int) -> bool:
    """Deteksi spam command berdasarkan frequency dalam time window.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True jika terdeteksi spam
    """
    now = datetime.now()
    history = user_command_history[user_id]
    
    # Tambahkan timestamp sekarang
    history.append(now)
    
    # Hitung command dalam window waktu
    cutoff_time = now - timedelta(seconds=SPAM_WINDOW)
    recent_commands = sum(1 for t in history if t >= cutoff_time)
    
    return recent_commands > SPAM_THRESHOLD

def is_auto_reply_abuse(user_id: int) -> bool:
    """Deteksi auto reply terlalu cepat.
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True jika auto reply terlalu cepat
    """
    now = datetime.now()
    history = user_autoreply_history[user_id]
    
    # Tambahkan timestamp sekarang
    history.append(now)
    
    # Hitung auto reply dalam window waktu
    cutoff_time = now - timedelta(seconds=AUTOREPLY_WINDOW)
    recent_replies = sum(1 for t in history if t >= cutoff_time)
    
    return recent_replies >= AUTOREPLY_THRESHOLD


def detect_command_spam(user_id: int, username: str | None = None) -> bool:
    """Deteksi dan log spam command.
    
    Args:
        user_id: Telegram user ID
        username: Username untuk logging
        
    Returns:
        True jika terdeteksi spam
    """
    if is_spam(user_id):
        log_abuse(user_id, username, "command_spam", f">{SPAM_THRESHOLD} commands dalam {SPAM_WINDOW}s")
        return True
    return False


def detect_autoreply_abuse(user_id: int, username: str | None = None) -> bool:
    """Deteksi dan log auto reply abuse.
    
    Args:
        user_id: Telegram user ID
        username: Username untuk logging
        
    Returns:
        True jika terdeteksi abuse
    """
    if is_auto_reply_abuse(user_id):
        log_abuse(user_id, username, "auto_reply_spam", f">={AUTOREPLY_THRESHOLD} replies dalam {AUTOREPLY_WINDOW}s")
        return True
    return False


def detect_abuse(user_id: int, username: str | None, action: str, detail: str | None = None) -> bool:
    """Fungsi utama untuk deteksi abuse.
    
    Args:
        user_id: Telegram user ID
        username: Username Telegram
        action: Jenis action untuk dicek ("spam", "auto_reply", atau abuse type lainnya)
        detail: Detail tambahan
        
    Returns:
        True jika terdeteksi abuse
    """
    # Deteksi spam command
    if action == "spam":
        return detect_command_spam(user_id, username)
    
    # Deteksi auto reply abuse
    if action == "auto_reply":
        return detect_autoreply_abuse(user_id, username)
    
    # Log abuse type lainnya langsung
    if action in ABUSE_TYPES:
        log_abuse(user_id, username, action, detail)
        return True
        
    return False


def clear_user_history(user_id: int) -> None:
    """Bersihkan history user (untuk admin/cleanup).
    
    Args:
        user_id: Telegram user ID
    """
    if user_id in user_command_history:
        user_command_history[user_id].clear()
    if user_id in user_autoreply_history:
        user_autoreply_history[user_id].clear()
    _logger.info(f"History cleared for user {user_id}")

