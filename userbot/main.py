"""Entrypoint userbot."""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path
from typing import Sequence

try:
    from .config import PYTHON_VERSION, load_userbot_settings, setup_logging
    from .app import run_userbot
except ImportError:
    # Direct execution fallback
    from config import PYTHON_VERSION, load_userbot_settings, setup_logging
    from app import run_userbot


def setup_terminal_logging():
    """Setup terminal logging to capture stdout/stderr to file."""
    log_dir = Path("./logs")
    log_dir.mkdir(parents=True, exist_ok=True)
    terminal_log_file = log_dir / "terminal.log"
    
    # Setup terminal logger
    terminal_logger = logging.getLogger("terminal")
    
    # Remove existing handlers
    for handler in terminal_logger.handlers[:]:
        terminal_logger.removeHandler(handler)
        
    terminal_logger.setLevel(logging.INFO)
    
    # File handler for terminal output
    file_handler = logging.FileHandler(terminal_log_file)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | terminal | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(formatter)
    terminal_logger.addHandler(file_handler)
    
    # Console handler (keep stdout visible)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    terminal_logger.addHandler(console_handler)
    
    return terminal_logger


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jalankan Telethon userbot.")
    parser.add_argument(
        "--owner-id",
        type=int,
        help="Telegram user ID pemilik session (diambil dari database).",
    )
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> None:
    # Setup terminal logging first
    terminal_logger = setup_terminal_logging()
    
    try:
        args = _parse_args(argv)
        settings = load_userbot_settings()
        if args.owner_id is not None:
            settings.session_owner_id = args.owner_id
        if not settings.api_id or not settings.api_hash:
            raise RuntimeError("API_ID dan API_HASH harus diisi di .env.")
        
        startup_msg = f"Menjalankan Userbot (Python {PYTHON_VERSION})"
        print(startup_msg)  # Print to console
        terminal_logger.info(startup_msg)  # Log to file
        
        await run_userbot(settings)
        
    except Exception as e:
        error_msg = f"Userbot error: {e}"
        print(error_msg)
        terminal_logger.error(error_msg, exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Userbot dihentikan oleh pengguna.")
        # Log to terminal.log if possible
        try:
            terminal_logger = logging.getLogger("terminal")
            terminal_logger.info("Userbot dihentikan oleh pengguna.")
        except:
            pass  # Ignore if logger not setup yet
