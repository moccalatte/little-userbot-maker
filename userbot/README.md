# userbot/ – Telethon Userbot

Userbot berbasis Telethon dengan prefix `!`.

## Cara Jalan
Pastikan `SESSION_FILE` berisi string session (misal `session.session`).
```bash
python userbot/main.py
```

## Perintah
- `!help` – daftar perintah.
- `!sg "pesan" <interval_menit> <target|allgroup>` – jadwalkan broadcast (`!sg stop` untuk berhenti).
- `!gg [next|prev|refresh]` – daftar ID grup dengan paginasi 50 entri.
- `!scr '<rules_json>'` – aktifkan listener pesan grup; `!scr stop` untuk mematikan.

Hasil listener disimpan ke CSV di `data/scrape_output/`. Log berada di `logs/userbot.log`.
