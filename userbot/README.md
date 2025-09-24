# userbot/ – Telethon Userbot

Userbot berbasis Telethon dengan prefix `!`.

## Cara Jalan
Pastikan `SESSION_FILE` berisi string session (misal `session.session`).
```bash
python userbot/main.py
```

## Perintah
- `!help` – daftar perintah.
- `!sg "pesan" <interval_menit> <target|allgroup>` – jadwalkan broadcast (bisa banyak job; cek dengan `!sg status`, hentikan satu job via `!sg stop <id>` atau semua dengan `!sg stop`).
- `!gg [next|prev|refresh]` – daftar ID grup dengan paginasi 50 entri.
- `!scr '<rules_json>'` – aktifkan listener pesan grup (bisa banyak session; `!scr status` menampilkan ID, hentikan dengan `!scr stop <id>` atau `!scr stop`).
- `!rg <include> <exclude> <regex> <target|allgroup> <reply_text>` – auto-reply; lampirkan gambar pada pesan perintah jika ingin balasan ikut mengirim foto (`!rg status` menampilkan daftar rule, `!rg stop <id>` memadamkan rule tertentu).
- `!info` – tampilkan status singkat seluruh menu yang sedang berjalan.

Hasil listener disimpan ke CSV di `data/scrape_output/`. Log berada di `logs/userbot.log`.
