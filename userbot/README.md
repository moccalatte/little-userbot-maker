# 🤖 Userbot - Telegram Automation

Userbot berbasis Telethon yang powerful untuk automasi Telegram dengan berbagai fitur seperti broadcast, scraping, auto-reply, dan management grup.

## 📋 Prerequisites

1. **Python 3.11+** installed
2. **Session string** dari Bot Wizard atau file session
3. **Telegram API credentials** dari [my.telegram.org](https://my.telegram.org)

## ⚙️ Installation & Setup

### 1. Install Dependencies
```bash
cd userbot/
pip install -r requirements.txt
```

### 2. Setup Configuration
```bash
# Copy template konfigurasi
cp .env.example .env

# Edit file .env
nano .env
```

### 3. Fill Configuration
Edit file `.env` dan pilih salah satu metode session:

#### Method A: Using Session File
```env
# API dari my.telegram.org
API_ID=12345678
API_HASH=abcd1234567890abcd1234567890abcd

# Path ke file session
SESSION_FILE=../session.session
```

#### Method B: Using Database Session (dari Bot Wizard)
```env
# API dari my.telegram.org
API_ID=12345678
API_HASH=abcd1234567890abcd1234567890abcd

# ID user yang buat session via bot wizard
SESSION_OWNER_ID=123456789

# Secret key untuk dekripsi (sama dengan bot wizard)
SECRET_KEY=abcd1234567890abcd1234567890abcd1234567890abcd==
```

## 🚀 Running the Userbot

### Single User Mode
```bash
# Method 1: Direct run
cd userbot/
python main.py

# Method 2: From root directory
python -m userbot.main

# Method 3: With specific user ID (database mode)
python -m userbot.main --owner-id 123456789
```

### Multi User Mode (Advanced)
Untuk menjalankan banyak userbot sekaligus:
```bash
# Generate config files untuk semua user di database
python autoterminal.py

# Generate + jalankan semua userbot
python autoterminal.py --run
```

## 📱 Available Commands

Semua command menggunakan prefix `!`

### 💬 Basic Commands
- `!help` - Daftar semua command
- `!info` - Status semua fitur yang sedang berjalan

### 📢 Broadcast Scheduler (`!sg`)
Jadwalkan pesan broadcast otomatis:
```
# Broadcast ke grup tertentu setiap 60 menit
!sg "Hello World!" 60 -1001234567890

# Broadcast ke semua grup setiap 120 menit
!sg "Selamat pagi!" 120 allgroup

# Cek status broadcast
!sg status

# Stop broadcast tertentu
!sg stop 1

# Stop semua broadcast
!sg stop
```

### 📊 Group Management (`!gg`)
Manage dan lihat daftar grup:
```
# Lihat daftar grup (50 per halaman)
!gg

# Halaman berikutnya
!gg next

# Halaman sebelumnya
!gg prev

# Refresh daftar
!gg refresh
```

### 🔍 Message Scraper (`!scr`)
Scrape pesan dari grup dengan aturan tertentu:
```
# Scrape dengan aturan JSON
!scr '{"keywords": ["bitcoin", "crypto"], "min_length": 10}'

# Cek status scraper
!scr status

# Stop scraper tertentu
!scr stop 1

# Stop semua scraper
!scr stop
```

### 🤖 Auto Reply (`!rg`)
Buat rule auto-reply untuk pesan:
```
# Auto reply dengan kondisi
!rg "hello" "spam" ".*greeting.*" -1001234567890 "Hi there!"

# Auto reply ke semua grup
!rg "help" "" ".*bantuan.*" allgroup "Silakan hubungi admin"

# Cek status auto-reply
!rg status

# Stop rule tertentu
!rg stop 1
```

**Parameters:**
- `include`: Kata yang harus ada dalam pesan
- `exclude`: Kata yang tidak boleh ada
- `regex`: Pattern regex untuk matching
- `target`: ID grup atau "allgroup"
- `reply_text`: Teks balasan

## 📂 File Structure
```
userbot/
├── commands/           # Command handlers
│   ├── base.py         # Base command classes
│   ├── gg.py           # Group management
│   ├── sg.py           # Broadcast scheduler
│   ├── scr.py          # Message scraper
│   ├── rg.py           # Auto reply
│   └── info.py         # Status info
├── main.py             # Entry point
├── app.py              # Main application
├── config.py           # Configuration
├── router.py           # Command router
├── scheduler.py        # Broadcast scheduler
├── scraper.py          # Message scraper
├── reply_guard.py      # Auto reply system
├── database.py         # Database operations
└── requirements.txt    # Dependencies
```

## 📁 Data & Outputs

### Database
- **Location**: `../data/userbotmaker.db`
- **Contains**: Sessions, broadcast jobs, scraper rules, reply rules

### Scraper Output
- **Location**: `../data/scrape_output/`
- **Format**: CSV files dengan timestamp
- **Columns**: Date, Chat, User, Message, etc.

### Logs
- **Console**: Real-time output
- **File**: `../logs/userbot.log`
- **Components**: 
  - `userbot_commands.log` - Command executions
  - `userbot_scr.log` - Scraper activities
  - `userbot_reply_guard.log` - Auto-reply activities

## 🐛 Troubleshooting

### Userbot tidak connect
- ✅ Pastikan `API_ID` dan `API_HASH` benar
- ✅ Cek session string atau file session valid
- ✅ Untuk database mode, pastikan `SECRET_KEY` sama dengan bot wizard

### Commands tidak bekerja
- ✅ Pastikan menggunakan prefix `!`
- ✅ Cek rate limit (default 30 detik antar command)
- ✅ Lihat log untuk error messages

### Broadcast tidak jalan
- ✅ Pastikan userbot adalah admin di grup target
- ✅ Cek apakah grup ID benar
- ✅ Lihat log scheduler untuk error

### Scraper tidak capture pesan
- ✅ Pastikan JSON rules valid
- ✅ Cek apakah userbot ada di grup target
- ✅ Periksa folder output `../data/scrape_output/`

## ⚡ Advanced Features

### Rate Limiting
Untuk mencegah spam, userbot memiliki rate limit default 30 detik antar command. Bisa diubah di `.env`:
```env
RATE_LIMIT_INTERVAL=15  # 15 detik
```

### Telegram Logging
Error penting bisa dikirim ke chat Telegram:
```env
TELEGRAM_LOG_CHAT_ID=-1001234567890
```

### Multi-Session Management
Gunakan `autoterminal.py` untuk:
- Generate file config per user
- Run multiple userbot instances
- Centralized management

## 🔄 Integration with Bot Wizard

1. Buat session dengan Bot Wizard
2. Set `SESSION_OWNER_ID` dengan user ID Anda
3. Set `SECRET_KEY` yang sama di kedua komponen
4. Userbot otomatis load session dari database
