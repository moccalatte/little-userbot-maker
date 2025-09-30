"""Userbot configuration."""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


# ============================================================================
# CONFIGURATION
# ============================================================================

@dataclass(slots=True)
class BaseSettings:
    log_level: str = "INFO"
    log_dir: str = "./logs"
    telegram_log_chat_id: Optional[int] = None
    database_url: Optional[str] = None


@dataclass(slots=True)
class UserbotSettings(BaseSettings):
    api_id: int = 0
    api_hash: str = ""
    rate_limit_interval: int = 30
    storage_dir: Path = Path("./data")
    secret_key: Optional[str] = None
    session_owner_id: Optional[int] = None


PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11")


def _get_int(name: str, default: Optional[int]) -> Optional[int]:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Env {name} harus berupa angka.")


def load_userbot_settings() -> UserbotSettings:
    # Try shared API credentials first, fallback to individual
    api_id = _get_int("SHARED_API_ID", None) or _get_int("API_ID", None) or 0
    api_hash = os.getenv("SHARED_API_HASH") or os.getenv("API_HASH", "")
    
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "./logs")
    chat_id = _get_int("TELEGRAM_LOG_CHAT_ID", None)
    rate_limit_interval = _get_int("RATE_LIMIT_INTERVAL", 30) or 30
    storage_dir = Path(os.getenv("DATA_DIR", "./data"))
    database_url = os.getenv("DATABASE_URL")
    secret_key = os.getenv("SECRET_KEY")
    return UserbotSettings(
        api_id=api_id,
        api_hash=api_hash,
        log_level=log_level,
        log_dir=log_dir,
        telegram_log_chat_id=chat_id,
        rate_limit_interval=rate_limit_interval,
        storage_dir=storage_dir,
        secret_key=secret_key,
        session_owner_id=None,  # Will be set by main.py argument
        database_url=database_url,
    )


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(component: str, level: str = "INFO", log_dir: str = "./logs") -> logging.Logger:
    logger = logging.getLogger(component)

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / f"{component}.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Ensure component file handler exists
    def _has_file_handler(path: Path) -> bool:
        for h in logger.handlers:
            if isinstance(h, RotatingFileHandler) and getattr(h, "baseFilename", None) == str(path):
                return True
        return False

    if not _has_file_handler(file_path):
        file_handler = RotatingFileHandler(file_path, maxBytes=10 * 1024 * 1024, backupCount=2)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Combined aggregator for all userbot.* logs (attach to any userbot* logger)
    if component.startswith("userbot"):
        combined_path = log_path / "all_userbot.log"
        if not _has_file_handler(combined_path):
            combined_handler = RotatingFileHandler(combined_path, maxBytes=20 * 1024 * 1024, backupCount=3)
            combined_handler.setFormatter(formatter)
            logger.addHandler(combined_handler)

    # Ensure a stream handler exists
    if not any(isinstance(h, logging.StreamHandler) for h in logger.handlers):
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

    logger.setLevel(level.upper())
    logger.propagate = False
    logger.debug("Logger %s siap dengan level %s", component, level)
    return logger


def forward_to_telegram(logger: logging.Logger, send_func: Optional[callable]) -> None:
    """Attach handler opsional untuk broadcast log penting via Telegram."""
    if send_func is None:
        return

    class TelegramHandler(logging.Handler):
        def emit(self, record: logging.LogRecord) -> None:
            if record.levelno < logging.WARNING:
                return
            try:
                message = self.format(record)
                send_func(message)
            except Exception:
                logger.debug("Gagal kirim log ke Telegram", exc_info=True)

    tg_handler = TelegramHandler()
    tg_handler.setLevel(logging.WARNING)
    tg_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    logger.addHandler(tg_handler)