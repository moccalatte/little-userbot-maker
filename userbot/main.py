"""Entrypoint userbot."""
from __future__ import annotations

import asyncio

from common.config import PYTHON_VERSION, load_userbot_settings

from .app import run_userbot


async def main() -> None:
    settings = load_userbot_settings()
    if not settings.api_id or not settings.api_hash:
        raise RuntimeError("API_ID dan API_HASH harus diisi di .env.")
    print(f"Menjalankan Userbot (Python {PYTHON_VERSION})")
    await run_userbot(settings)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Userbot dihentikan oleh pengguna.")
