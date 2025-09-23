# bot/ – UserbotMaker Wizard

Bot Telegram (Bot API) yang memandu pengguna membuat string session Telethon.

## Cara Jalan
```bash
python bot/main.py
```

## Alur Singkat
1. `/start` → jelaskan tujuan & format input.
2. Input nomor E.164, API ID, API hash.
3. Bot mengirim OTP dan meminta kode.
4. Jika ada 2FA, bot meminta password (tidak disimpan).
5. Setelah sukses, session string dikirim ke chat dan bisa disimpan terenkripsi jika `SECRET_KEY` tersedia.
6. `/delete` menghapus session terenkripsi milik pengguna.

## Catatan
- OTP tidak pernah disimpan.
- Data terenkripsi disimpan di `data/sessions.json` (maks 100 entri).
- Logging berada di `logs/bot.log`.
