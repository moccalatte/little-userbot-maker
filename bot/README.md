# 🤖 Bot Wizard - Session Generator

Bot Telegram yang membantu pengguna membuat session string untuk userbot Telethon. Bot ini menyediakan dua metode: **OTP via SMS** dan **QR Code**.

## 📋 Prerequisites

1. **Python 3.11+** installed
2. **Telegram Bot Token** dari [@BotFather](https://t.me/BotFather)
3. **Telegram API credentials** dari [my.telegram.org](https://my.telegram.org)

## ⚙️ Installation & Setup

### 1. Install Dependencies
```bash
cd bot/
pip install -r requirements.txt
```

### 2. Setup Configuration
```bash
# Copy template konfigurasi
cp .env.example .env

# Edit file .env dengan text editor favorit Anda
nano .env
```

### 3. Fill Configuration
Edit file `.env` dan isi nilai-nilai berikut:

```env
# WAJIB: Token bot dari @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# OPSIONAL: Secret key untuk enkripsi (auto-generate jika kosong)
SECRET_KEY=

# OPSIONAL: Chat ID untuk notifikasi error
TELEGRAM_LOG_CHAT_ID=-1001234567890
```

### 4. Generate Secret Key (Optional)
Jika ingin membuat secret key sendiri:
```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

## 🚀 Running the Bot

### Method 1: Direct Run
```bash
cd bot/
python main.py
```

### Method 2: From Root Directory
```bash
python -m bot.main
```

## 📱 How to Use

### For Regular Users:
1. Start chat dengan bot Anda
2. Kirim `/start`
3. Pilih metode:
   - **📱 OTP Method**: Masukkan nomor HP, API ID, API Hash, lalu kode OTP
   - **📷 QR Method**: Scan QR code dengan aplikasi Telegram official
4. Jika ada 2FA, masukkan password
5. **Done!** Session string akan dikirim ke chat

### Commands:
- `/start` - Mulai proses pembuatan session
- `/delete` - Hapus session tersimpan (jika ada)
- `/help` - Tampilkan bantuan

## 🔐 Security Features

- ✅ **OTP tidak disimpan** - Hanya digunakan sekali untuk autentikasi
- ✅ **Password 2FA tidak disimpan** - Langsung digunakan untuk login
- ✅ **Session terenkripsi** - Menggunakan Fernet encryption
- ✅ **Rate limiting** - Mencegah spam dan abuse
- ✅ **Auto cleanup** - Session lama otomatis terhapus

## 📂 File Structure
```
bot/
├── main.py              # Entry point
├── config.py           # Konfigurasi dan logging
├── conversation.py     # Logic percakapan bot
├── services.py         # Session generation services
├── storage.py          # Database dan storage
├── utils.py            # Utility functions
├── requirements.txt    # Dependencies
├── .env.example       # Template konfigurasi
└── README.md          # Dokumentasi ini
```

## 🐛 Troubleshooting

### Bot tidak merespon
- ✅ Pastikan `TELEGRAM_BOT_TOKEN` benar
- ✅ Cek connection internet
- ✅ Lihat log di `../logs/bot.log`

### Error saat generate session
- ✅ Pastikan API_ID dan API_HASH valid dari [my.telegram.org](https://my.telegram.org)
- ✅ Pastikan nomor telepon dalam format international (+62xxx)
- ✅ Cek apakah ada 2FA aktif di akun Telegram

### Session tidak tersimpan
- ✅ Pastikan folder `../data/` ada dan writable
- ✅ Jika menggunakan enkripsi, pastikan `SECRET_KEY` terisi

## 📊 Logs & Monitoring

- **Console logs**: Real-time di terminal
- **File logs**: `../logs/bot.log` (rotated automatically)
- **Telegram logs**: Error penting dikirim ke `TELEGRAM_LOG_CHAT_ID` (jika diset)

## 🔄 Integration with Userbot

Session yang dibuat bot ini dapat langsung digunakan oleh userbot:

1. Session tersimpan di database `../data/userbotmaker.db`
2. Userbot dapat memuat session dengan `SESSION_OWNER_ID`
3. Gunakan `SECRET_KEY` yang sama di kedua komponen
