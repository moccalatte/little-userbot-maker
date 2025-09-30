"""Logging utilities for the bot wizard."""
from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


class RealTimeLogger:
    """Real-time logging helper that mirrors logs to the terminal log file."""

    def __init__(self, log_file: str = "terminal.log") -> None:
        self.log_file = Path(log_file)
        self._setup_realtime_logging()

    def _setup_realtime_logging(self) -> None:
        formatter = logging.Formatter(
            "\033[92m%(asctime)s\033[0m | \033[94m%(levelname)s\033[0m | "
            "\033[96m%(name)s\033[0m | %(message)s",
            datefmt="%H:%M:%S",
        )

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(logging.INFO)

        root_logger = logging.getLogger()
        root_logger.addHandler(console_handler)

        self.info("🚀 Real-time terminal logging started")

    def info(self, message: str, *args: Any) -> None:
        logging.getLogger("bot").info(message, *args)
        self._write_line("INFO", message, *args)

    def warning(self, message: str, *args: Any) -> None:
        logging.getLogger("bot").warning(message, *args)
        self._write_line("WARNING", message, *args)

    def error(self, message: str, *args: Any) -> None:
        logging.getLogger("bot").error(message, *args)
        self._write_line("ERROR", message, *args)

    def _write_line(self, level: str, message: str, *args: Any) -> None:
        rendered = message % args if args else message
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.log_file, "a", encoding="utf-8") as handle:
            handle.write(f"{timestamp} | {level} | {rendered}\n")


class UserActivityLogger:
    """Structured logger that records per-user activity to disk."""

    def __init__(self, log_dir: str = "logs") -> None:
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _write_entry(self, user_id: int, payload: Dict[str, Any]) -> None:
        log_entry_path = self.log_dir / f"user_{user_id}.log"
        with open(log_entry_path, "a", encoding="utf-8") as handle:
            handle.write(json_dumps(payload) + "\n")

    def log_user_activity(self, user_id: int, activity: str, details: Dict[str, Any] | None = None) -> None:
        self._write_entry(
            user_id,
            {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "activity": activity,
                "details": details or {},
            },
        )

    def log_command_usage(self, user_id: int, command: str, success: bool, details: Dict[str, Any] | None = None) -> None:
        self.log_user_activity(
            user_id,
            "command_usage",
            {
                "command": command,
                "success": success,
                "details": details or {},
            },
        )

    def log_session_creation(self, user_id: int, method: str, success: bool, details: Dict[str, Any] | None = None) -> None:
        self.log_user_activity(
            user_id,
            "session_creation",
            {
                "method": method,
                "success": success,
                "details": details or {},
            },
        )

    def log_menu_navigation(
        self,
        user_id: int,
        from_menu: str,
        to_menu: str,
        action: str | None = None,
    ) -> None:
        self.log_user_activity(
            user_id,
            "menu_navigation",
            {
                "from_menu": from_menu,
                "to_menu": to_menu,
                "action": action,
            },
        )


def json_dumps(payload: Dict[str, Any]) -> str:
    """Compact JSON dump helper with UTF-8 support."""
    import json

    return json.dumps(payload, ensure_ascii=False)

