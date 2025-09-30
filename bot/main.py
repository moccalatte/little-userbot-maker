"""Entrypoint bot wizard UserbotMaker."""
from __future__ import annotations

try:
    from .config import load_bot_settings, PYTHON_VERSION
    from .conversation import run_bot
except ImportError:
    # Direct execution fallback
    from config import load_bot_settings, PYTHON_VERSION
    from conversation import run_bot

def main() -> None:
    settings = load_bot_settings()
    
    # Colorful startup message
    print("\033[92m" + "=" * 60 + "\033[0m")
    print(f"\033[96m🤖 UserbotMaker Bot Wizard\033[0m")
    print(f"\033[94m📱 Python {PYTHON_VERSION}\033[0m")
    print(f"\033[93m📊 Real-time Terminal Logging: ENABLED\033[0m")
    print(f"\033[95m📍 Working Directory: {settings.data_dir}\033[0m")
    print("\033[92m" + "=" * 60 + "\033[0m")
    print("\033[97m💡 All activities will be logged in real-time below:\033[0m")
    print()
    
    run_bot(settings)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Dihentikan oleh pengguna.")
