"""Bot configuration."""
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
    database_url: str = "../data/userbotmaker.db"


@dataclass(slots=True)
class BotSettings(BaseSettings):
    bot_token: str = ""
    secret_key: Optional[str] = None
    rate_limit_interval: int = 30
    data_dir: Path = Path("./data")
    session_output_file: Optional[str] = None
    qr_timeout: int = 180
    shared_api_id: int = 0
    shared_api_hash: str = ""
    owner_ids: list[int] = None
    admin_ids: list[int] = None


PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11")


def _get_int(name: str, default: Optional[int]) -> Optional[int]:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Env {name} harus berupa angka.")


def _get_int_list(name: str) -> list[int]:
    """Parse comma-separated list of integers from environment variable."""
    value = os.getenv(name, "").strip()
    if not value:
        return []
    try:
        return [int(x.strip()) for x in value.split(",") if x.strip()]
    except ValueError:
        raise ValueError(f"Env {name} harus berupa daftar angka dipisah koma (contoh: 123456,789012).")


def load_bot_settings() -> BotSettings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    secret_key = os.getenv("SECRET_KEY")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "./logs")
    rate_limit_interval = _get_int("RATE_LIMIT_INTERVAL", 30) or 30
    chat_id = _get_int("TELEGRAM_LOG_CHAT_ID", None)
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    session_output_file = os.getenv("SESSION_OUTPUT_FILE") or os.getenv("SESSION_FILE")
    qr_timeout = _get_int("QR_TIMEOUT", 180) or 180
    shared_api_id = _get_int("SHARED_API_ID", 0) or 0
    shared_api_hash = os.getenv("SHARED_API_HASH", "")
    owner_ids = _get_int_list("OWNER_IDS")
    admin_ids = _get_int_list("ADMIN_IDS")
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable harus di-set. "
            "Format: postgresql://username:password@host/database?sslmode=require"
        )
    if not shared_api_id or not shared_api_hash:
        raise ValueError(
            "SHARED_API_ID dan SHARED_API_HASH environment variables harus di-set. "
            "Dapatkan dari https://my.telegram.org"
        )
    return BotSettings(
        bot_token=token,
        secret_key=secret_key,
        log_level=log_level,
        log_dir=log_dir,
        rate_limit_interval=rate_limit_interval,
        telegram_log_chat_id=chat_id,
        data_dir=data_dir,
        session_output_file=session_output_file,
        qr_timeout=qr_timeout,
        shared_api_id=shared_api_id,
        shared_api_hash=shared_api_hash,
        owner_ids=owner_ids or [],
        admin_ids=admin_ids or [],
        database_url=database_url,
    )


# ============================================================================
# LOGGING
# ============================================================================

def setup_logging(component: str, level: str = "INFO", log_dir: str = "./logs") -> logging.Logger:
    logger = logging.getLogger(component)
    if logger.handlers:
        return logger

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / f"{component}.log"
    
    # Add terminal.log untuk easy monitoring
    terminal_log_path = Path(".") / "terminal.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Regular component log file
    file_handler = RotatingFileHandler(file_path, maxBytes=10 * 1024 * 1024, backupCount=2)
    file_handler.setFormatter(formatter)
    
    # Terminal log file untuk easy monitoring (shared across all components)
    terminal_handler = RotatingFileHandler(terminal_log_path, maxBytes=50 * 1024 * 1024, backupCount=5)
    terminal_handler.setFormatter(formatter)
    terminal_handler.setLevel(logging.INFO)  # Only INFO and above untuk terminal.log

    # Console output
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.setLevel(level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(terminal_handler)  # Add terminal.log handler
    logger.addHandler(stream_handler)
    logger.propagate = False
    logger.info("Logger %s siap dengan level %s (terminal.log enabled)", component, level)
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