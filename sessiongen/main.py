"""Entrypoint session generator."""
from __future__ import annotations

from common.config import PYTHON_VERSION, load_sessiongen_settings

from .bot import run_session_generator


def main() -> None:
    settings = load_sessiongen_settings()
    print(f"Menjalankan Session Generator (Python {PYTHON_VERSION})")
    run_session_generator(settings)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Dihentikan oleh pengguna.")
