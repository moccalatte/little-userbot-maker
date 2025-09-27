"""Entrypoint userbot."""
from __future__ import annotations

import argparse
import asyncio
from typing import Sequence

from .config import PYTHON_VERSION, load_userbot_settings
from .app import run_userbot


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Jalankan Telethon userbot.")
    parser.add_argument(
        "--owner-id",
        type=int,
        help="Telegram user ID pemilik session (diambil dari database).",
    )
    return parser.parse_args(argv)


async def main(argv: Sequence[str] | None = None) -> None:
    args = _parse_args(argv)
    settings = load_userbot_settings()
    if args.owner_id is not None:
        settings.session_owner_id = args.owner_id
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError("API_ID dan API_HASH harus diisi di .env.")
    print(f"Menjalankan Userbot (Python {PYTHON_VERSION})")
    await run_userbot(settings)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Userbot dihentikan oleh pengguna.")
