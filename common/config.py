"""Loader konfigurasi berbasis .env."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(slots=True)
class BaseSettings:
    log_level: str = "INFO"
    log_dir: str = "./logs"
    telegram_log_chat_id: Optional[int] = None
    database_path: Path = Path("./data/userbotmaker.db")


@dataclass(slots=True)
class BotSettings(BaseSettings):
    bot_token: str = ""
    secret_key: Optional[str] = None
    rate_limit_interval: int = 30
    data_dir: Path = Path("./data")
    session_output_file: Optional[str] = None
    qr_timeout: int = 180


@dataclass(slots=True)
class SessionGenSettings(BaseSettings):
    bot_token: str = ""
    secret_key: Optional[str] = None
    data_dir: Path = Path("./data")


@dataclass(slots=True)
class UserbotSettings(BaseSettings):
    api_id: int = 0
    api_hash: str = ""
    session_file: str = "session.session"
    rate_limit_interval: int = 30
    storage_dir: Path = Path("./data")


PYTHON_VERSION = os.getenv("PYTHON_VERSION", "3.11")


def _get_int(name: str, default: Optional[int]) -> Optional[int]:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        raise ValueError(f"Env {name} harus berupa angka.")


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
    database_path = Path(os.getenv("DATABASE_PATH", str(data_dir / "userbotmaker.db")))
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
        database_path=database_path,
    )


def load_sessiongen_settings() -> SessionGenSettings:
    token = os.getenv("SESSIONGEN_BOT_TOKEN", "")
    secret_key = os.getenv("SECRET_KEY")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "./logs")
    chat_id = _get_int("TELEGRAM_LOG_CHAT_ID", None)
    data_dir = Path(os.getenv("DATA_DIR", "./data"))
    database_path = Path(os.getenv("DATABASE_PATH", str(data_dir / "userbotmaker.db")))
    return SessionGenSettings(
        bot_token=token,
        secret_key=secret_key,
        log_level=log_level,
        log_dir=log_dir,
        telegram_log_chat_id=chat_id,
        data_dir=data_dir,
        database_path=database_path,
    )


def load_userbot_settings() -> UserbotSettings:
    api_id = _get_int("API_ID", None) or 0
    api_hash = os.getenv("API_HASH", "")
    session_file = os.getenv("SESSION_FILE", "session.session")
    log_level = os.getenv("LOG_LEVEL", "INFO")
    log_dir = os.getenv("LOG_DIR", "./logs")
    chat_id = _get_int("TELEGRAM_LOG_CHAT_ID", None)
    rate_limit_interval = _get_int("RATE_LIMIT_INTERVAL", 30) or 30
    storage_dir = Path(os.getenv("DATA_DIR", "./data"))
    database_path = Path(os.getenv("DATABASE_PATH", str(storage_dir / "userbotmaker.db")))
    return UserbotSettings(
        api_id=api_id,
        api_hash=api_hash,
        session_file=session_file,
        log_level=log_level,
        log_dir=log_dir,
        telegram_log_chat_id=chat_id,
        rate_limit_interval=rate_limit_interval,
        storage_dir=storage_dir,
        database_path=database_path,
    )
