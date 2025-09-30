"""Utility untuk menghasilkan file .env per user dan menjalankan userbot."""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
from pathlib import Path
from typing import Dict, Iterable, List

# PostgreSQL dependencies
try:
    import psycopg2
except ImportError:
    raise ImportError(
        "PostgreSQL dependencies tidak tersedia. "
        "Install dengan: pip install psycopg2-binary"
    )

BASE_ENV_KEYS = [
    "PYTHON_VERSION",
    "LOG_LEVEL",
    "LOG_DIR",
    "DATA_DIR",
    "TELEGRAM_LOG_CHAT_ID",
    "RATE_LIMIT_INTERVAL",
    "SECRET_KEY",
    "API_ID",
    "API_HASH",
    "DATABASE_URL",
]


def load_env_file(path: Path) -> Dict[str, str]:
    env: Dict[str, str] = {}
    if not path.exists():
        return env
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            env[key.strip()] = value.strip()
    return env


def write_env_file(path: Path, data: Dict[str, str]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        for key, value in data.items():
            handle.write(f"{key}={value}\n")
    print(f"[autoterminal] Menulis {path}")


def fetch_session_owner_ids(database_url: str) -> List[int]:
    """Fetch unique user IDs from sessions in PostgreSQL database."""
    conn = psycopg2.connect(database_url)
    try:
        cur = conn.cursor()
        # Only get users with active subscriptions
        cur.execute("""
            SELECT DISTINCT s.user_id 
            FROM sessions s 
            JOIN users u ON s.user_id = u.id 
            WHERE u.status_subscription = 'active' 
            AND (u.tanggal_subs_selesai IS NULL OR u.tanggal_subs_selesai > CURRENT_TIMESTAMP)
            ORDER BY s.user_id
        """)
        results = [int(row[0]) for row in cur.fetchall()]
    finally:
        conn.close()
    return results


def generate_env_files(base_env: Dict[str, str], owners: Iterable[int], output_dir: Path) -> List[Path]:
    env_files: List[Path] = []
    for owner_id in owners:
        env_data = {key: base_env[key] for key in BASE_ENV_KEYS if key in base_env}
        env_data["SESSION_OWNER_ID"] = str(owner_id)
        env_file = output_dir / f".env.user_{owner_id}"
        write_env_file(env_file, env_data)
        env_files.append(env_file)
    return env_files


def run_userbot(env_path: Path) -> subprocess.Popen[bytes]:
    env = dict(os.environ)
    env.update(load_env_file(env_path))
    cmd = shlex.split("python -m userbot.main")
    print(f"[autoterminal] Menjalankan userbot dengan {env_path}")
    return subprocess.Popen(cmd, env=env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate env per user dan jalankan userbot.")
    parser.add_argument("--base-env", default=".env", help="Path file .env dasar (default: .env)")
    parser.add_argument("--database-url", help="PostgreSQL database URL (opsional, override)")
    parser.add_argument("--output-dir", default=".", help="Folder menyimpan env user")
    parser.add_argument("--run", action="store_true", help="Langsung jalankan userbot untuk setiap user")
    args = parser.parse_args()

    base_env_path = Path(args.base_env)
    base_env = load_env_file(base_env_path)
    
    # Get database URL from args or environment
    database_url = args.database_url or base_env.get("DATABASE_URL")
    if not database_url:
        raise ValueError(
            "DATABASE_URL harus tersedia di .env file atau lewat --database-url argument. "
            "Format: postgresql://username:password@host/database?sslmode=require"
        )

    owners = fetch_session_owner_ids(database_url)
    if not owners:
        print("[autoterminal] Tidak menemukan session dengan subscription aktif. Pastikan ada user dengan subscription aktif.")
        return

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    env_files = generate_env_files(base_env, owners, output_dir)

    if args.run:
        processes = [run_userbot(env_path) for env_path in env_files]
        try:
            for proc in processes:
                proc.wait()
        except KeyboardInterrupt:
            print("[autoterminal] Dihentikan oleh pengguna, mengakhiri proses...")
            for proc in processes:
                proc.terminate()


if __name__ == "__main__":
    main()
