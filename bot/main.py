"""Entrypoint bot wizard UserbotMaker."""
from __future__ import annotations

from common.config import load_bot_settings, PYTHON_VERSION

from .conversation import run_bot


def main() -> None:
    settings = load_bot_settings()
    print(f"Menjalankan UserbotMaker (Python {PYTHON_VERSION})")
    run_bot(settings)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Dihentikan oleh pengguna.")
