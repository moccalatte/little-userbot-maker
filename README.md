# Little Userbot Maker

✨ Proyek Python ini dirancang untuk membantumu membuat string session Telethon dan menyalakan userbot ringan tanpa repot urusan server.

## ✅ Sebelum Mulai
- Python 3.11 dan `pip` terbaru sudah terpasang.
- Sudah punya API ID & API hash dari https://my.telegram.org (ini untuk operator userbot, bukan untuk end-user).
- Salinan `.env.example` menjadi `.env` supaya konfigurasi tersusun rapi.

## 🚀 Langkah Cepat
1. **Clone & masuk folder**
   ```bash
   git clone https://github.com/moccalatte/little-userbot-maker.git
   cd little-userbot-maker
   ```
2. **Siapkan virtualenv & paket**
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. **Isi konfigurasi `.env`**
   ```bash
   cp .env.example .env
   ```
   - Buat `SECRET_KEY` sekali saja:
     ```bash
     python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
     ```
   - Lengkapi variabel penting: `TELEGRAM_BOT_TOKEN`, `SESSION_OUTPUT_FILE` (mis. `./session.session`), `QR_TIMEOUT` jika ingin mengatur timeout QR, serta `API_ID` & `API_HASH` milik operator userbot.
   - Kalau tidak mau auto-tulis session, kosongkan `SESSION_OUTPUT_FILE` dan simpan manual ke `SESSION_FILE`.
4. **Jalankan komponen** (boleh pakai terminal terpisah):
   - Wizard (Bot API): `python -m bot.main`
   - Session generator minimal: `python -m sessiongen.main`
   - Userbot Telethon: `python -m userbot.main`

## 🧠 Fitur Wizard
- Punya dua mode login:
  - **OTP** – meminta nomor, API ID/hash, lalu mengirim kode Telegram dengan retry otomatis.
  - **QR Login** – kirim QR, minta kamu scan lewat Telegram → tekan tombol *Masuk* di perangkat utama → balas `done`. Butuh QR baru? balas `retry` langsung di chat.
- Session string otomatis tulis ke `SESSION_OUTPUT_FILE` dan bisa disimpan terenkripsi (opsional).
- Log tersimpan di `logs/bot.log`, dan akan dilanjutkan ke chat jika `TELEGRAM_LOG_CHAT_ID` diisi.

## 🧰 Komponen Lain
- `sessiongen/` – cara tercepat membuat string session bagi operator yang sudah hafal alurnya.
- `userbot/` – Telethon client dengan prefix `!`. Command default: `!help`, `!sg`, `!gg`, `!scr`.
- `common/` – utilitas bersama (config loader, logging, enkripsi, storage JSON/CSV).

## 🧪 Checklist Pengujian Manual
- Jalankan wizard, coba kedua metode login (OTP & QR) termasuk flow 2FA.
- Nyalakan userbot, uji `!help`, `!sg`, `!gg`, `!scr`, dan cek output storage.
- Pastikan log tidak mencetak rahasia dan `SESSION_OUTPUT_FILE` berisi string session valid.

## ♻️ Rollback Cepat
Stop proses Python, kembalikan perubahan dari backup/git sebelumnya, lalu jalankan ulang sesuai panduan di `project_rules.md`.

Selamat mencoba, dan jangan lupa matikan userbot ketika tidak dipakai supaya akun Telegram tetap aman! 💡
