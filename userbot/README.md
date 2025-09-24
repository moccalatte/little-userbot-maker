# userbot/ – Telethon Userbot

Userbot berbasis Telethon dengan prefix `!`.

## Cara Jalan
Pastikan `SESSION_FILE` berisi string session (misal `session.session`).
```bash
python userbot/main.py
```

Atau jika session sudah tersimpan di database hasil wizard, jalankan:
```bash
python -m userbot.main --owner-id <telegram_user_id>
```
(`SECRET_KEY` harus terisi agar session terenkripsi bisa didekripsi.)

## Perintah
- `!help` – daftar perintah.
- `!sg "pesan" <interval_menit> <target|allgroup>` – jadwalkan broadcast (bisa banyak job; cek dengan `!sg status`, hentikan satu job via `!sg stop <id>` atau semua dengan `!sg stop`).
- `!gg [next|prev|refresh]` – daftar ID grup dengan paginasi 50 entri.
- `!scr '<rules_json>'` – aktifkan listener pesan grup (bisa banyak session; `!scr status` menampilkan ID, hentikan dengan `!scr stop <id>` atau `!scr stop`).
- `!rg <include> <exclude> <regex> <target|allgroup> <reply_text>` – auto-reply; lampirkan gambar pada pesan perintah jika ingin balasan ikut mengirim foto (`!rg status` menampilkan daftar rule, `!rg stop <id>` memadamkan rule tertentu).
- `!info` – tampilkan status singkat seluruh menu yang sedang berjalan.

Hasil listener disimpan ke CSV di `data/scrape_output/`. Log berada di `logs/userbot.log`.
Konfigurasi multi-user (rule/jadwal/listener) tersimpan secara terpusat di database SQLite `data/userbotmaker.db`.

### Variabel lingkungan tambahan
- `SESSION_OWNER_ID` — ID Telegram (user wizard) pemilik session yang ingin dijalankan. Jika diisi, userbot mengambil session langsung dari database dan tidak membutuhkan file `SESSION_FILE`.
- `SECRET_KEY` — kunci untuk men-dekripsi session terenkripsi yang disimpan wizard. Wajib diisi bila `SESSION_OWNER_ID` digunakan dan session tersimpan terenkripsi.
