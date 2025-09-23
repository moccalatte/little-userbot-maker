"""Setup logging konsisten dengan file terpisah per komponen."""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional


def setup_logging(component: str, level: str = "INFO", log_dir: str = "./logs") -> logging.Logger:
    logger = logging.getLogger(component)
    if logger.handlers:
        return logger

    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)
    file_path = log_path / f"{component}.log"

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = RotatingFileHandler(file_path, maxBytes=10 * 1024 * 1024, backupCount=2)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.setLevel(level.upper())
    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
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

