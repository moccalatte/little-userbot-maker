# 🤖 Userbot Engine - Core UserbotMaker

**🚀 Otomatis & Powerful**: Engine yang menjalankan semua userbot dari database. Beginner-friendly dengan setup minimal!

> 🎆 **Magic**: Engine otomatis membaca database, load session yang aktif, dan menjalankan userbot dengan all features. Tidak perlu manual setup per user!

## 📋 Yang Dibutuhkan

- **Python 3.11+** terinstall
- **Neon PostgreSQL** database (setup di [neon.tech](https://neon.tech))
- **Bot Wizard** sudah running (yang handle user registration)
- **Valid environment** dengan `DATABASE_URL`

## 🚀 Setup Userbot Engine

### **🐍 Langkah 1: Setup Virtual Environment**
```bash
cd userbot/

# Buat virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### **💾 Langkah 2: Setup Database (Neon)**
1. **Copy connection string** dari Neon dashboard
2. **Set environment variable:**
```bash
export DATABASE_URL="postgresql://username:password@host/database?sslmode=require"
```

### **⚙️ Langkah 3: Konfigurasi (Opsional)**
```bash
# Copy environment template (jika perlu custom config)
cp .env.example .env
nano .env  # Edit sesuai kebutuhan
```

**File .env (minimal):**
```env
# Database URL (WAJIB)
DATABASE_URL=postgresql://username:password@host/database?sslmode=require

# API credentials (WAJIB - sama dengan Bot Wizard)
API_ID=12345678
API_HASH=abcd1234567890abcd1234567890abcd

# Logging (opsional)
LOG_LEVEL=INFO
LOG_DIR=../logs
```

> 📋 **Note**: Engine otomatis detect session dari database. Tidak perlu manual session setup!

## 🚀 Menjalankan Userbot Engine

### **⚡ Metode Utama (Helper Script)**
```bash
# Jalankan dengan helper script (recommended)
cd userbot/
./run_userbot.sh 123456789  # Ganti dengan Telegram ID user
```

### **🔧 Metode Manual**
```bash
# Jalankan userbot untuk user tertentu (ambil dari database)
cd userbot/
source .venv/bin/activate  # SELALU activate venv dulu
python main.py --owner-id 123456789  # Ganti dengan Telegram ID user
```

> 📋 **Penting**: `--owner-id` adalah Telegram ID user yang sessionnya sudah dibuat melalui Bot Wizard

**Apa yang terjadi:**
1. ✅ Engine connect ke Neon database
2. ✅ Load semua session dengan subscription aktif
3. ✅ Start userbot untuk setiap user
4. ✅ Monitor health dan auto-reconnect

### **🛠️ Metode Advanced (Multi-Process)**
Untuk server dengan traffic tinggi:
```bash
# Pastikan venv active
source .venv/bin/activate

# Generate individual configs untuk setiap user
python autoterminal.py

# Jalankan semua userbot dalam process terpisah
python autoterminal.py --run
```

### **🧪 Test Mode**
```bash
# Test basic connectivity (dari tests folder)
cd ../tests
source ../.venv/bin/activate  # Use shared venv untuk tests
python run_tests.py quick

# Test with specific user session
cd ../userbot
source .venv/bin/activate
python main.py --owner-id 123456789
```

## 🐍 **Virtual Environment Management**

### **🚀 Quick Setup**
```bash
cd userbot/

# Buat venv (sekali aja)
python3 -m venv .venv

# Activate (setiap kali mau run)
source .venv/bin/activate

# Install deps (sekali aja atau kalo ada update)
pip install -r requirements.txt
```

### **⚙️ Daily Usage**
```bash
# Setiap kali mau run userbot engine:
cd userbot/
source .venv/bin/activate  # ⚡ WAJIB!
python main.py
```

### **🔄 Auto-start Script (Optional)**
```bash
#!/bin/bash
# File: start_userbot.sh
cd userbot/
source .venv/bin/activate
python main.py

# Make executable:
# chmod +x start_userbot.sh
# ./start_userbot.sh
```

### **🧪 Check Venv Status**
```bash
# Check apakah venv aktif
which python  # Harus show path ke .venv/bin/python

# Check installed packages
pip list | grep -E "telethon|psycopg2|python-telegram-bot"

# Check Python version
python --version  # Harus 3.11+

# Deactivate venv (kalo perlu)
deactivate
```

### **🐛 Troubleshooting Venv**
- ✅ **Venv not found**: Buat ulang dengan `python3 -m venv .venv`
- ✅ **Permission denied**: Pakai `python3 -m venv .venv --clear`
- ✅ **Import errors**: Re-install dengan `pip install -r requirements.txt`
- ✅ **Database errors**: Check `DATABASE_URL` di `.env`
- ✅ **Telethon errors**: Check `API_ID` dan `API_HASH` di `.env`

### **🛠️ Production Tips**
```bash
# Pakai screen untuk background process
screen -S userbot
source .venv/bin/activate
python main.py
# Ctrl+A, D untuk detach

# Atau pakai systemd service (advanced)
# /etc/systemd/system/userbot.service
```

## 🤔 **Cara Kerja Engine**

### **🔄 Automatic Flow:**
1. **Database Polling**: Engine baca Neon database setiap X detik
2. **Session Loading**: Load session user dengan subscription aktif
3. **Client Creation**: Buat TelegramClient untuk setiap session
4. **Feature Application**: Apply configs (broadcast, auto-reply, etc)
5. **Health Monitoring**: Monitor kesehatan session dan reconnect jika perlu

### **📊 User Session Lifecycle:**
```
User daftar via Bot Wizard → Payment success → Session saved → Engine detect → Userbot active
```

### **🚑 Error Handling:**
- 🔄 **Auto Reconnect**: Session terputus otomatis reconnect
- 📋 **Subscription Check**: Expired subscription otomatis disabled
- 📝 **Logging**: Semua error logged untuk debugging
- 📧 **Health Reports**: Real-time monitoring status

## 📱 Commands untuk User

**Beginner-friendly**: User chat di grup dengan prefix `!`

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

## 🛡️ Owner/Admin Detection

**Auto-detected dari Bot Wizard environment - tidak perlu setup manual!**

### Cara Kerja:
1. **Bot Wizard** set `OWNER_TELEGRAM_IDS` di `/bot/.env`
2. **Userbot** auto-detect owner dari environment
3. **Owner** mendapat admin access tanpa setup database

### Environment Detection:
```bash
# Userbot akan cek environment variables ini:
OWNER_TELEGRAM_IDS=123456789,987654321  # dari Bot Wizard
ADMIN_TELEGRAM_IDS=123456789            # alternatif
```

### Validation Priority:
1. **Environment Owner** (dari OWNER_TELEGRAM_IDS)
2. **Database Admin** (manual added via database)
3. **Regular User** (perlu bayar di Bot Wizard)

**💡 Tidak perlu script manual lagi! Semua auto-detected dari Bot Wizard environment.**

## 📂 File Structure
```
userbot/
├── commands/           # Command handlers
│   ├── base.py         # Base command classes
│   ├── gg.py           # Group management
│   ├── sg.py           # Broadcast scheduler
│   ├── rg.py           # Auto reply
│   └── info.py         # Status info
├── main.py             # Entry point
├── app.py              # Main application
├── config.py           # Configuration
├── router.py           # Command router
├── scheduler.py        # Broadcast scheduler
├── reply_guard.py      # Auto reply system
├── database.py         # Database operations
├── admin_utils.py      # Admin management functions
├── wizard_utils.py     # Bot Wizard integration
└── requirements.txt    # Dependencies
```

## 📁 Data & Outputs

### Database
- **Location**: `../data/userbotmaker.db`
- **Contains**: Sessions, broadcast jobs, reply rules

### Logs
- **Console**: Real-time output
- **File**: `../logs/userbot.log`
- **Components**: 
  - `userbot_commands.log` - Command executions
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

## 🔄 Integration dengan Bot Wizard

**Userbot terintegrasi penuh dengan Bot Wizard - config dan control via Web UI!**

### Auto Config dari Bot Wizard:
1. User create userbot di Bot Wizard
2. Bot Wizard save config ke database dengan shared API
3. Userbot auto-polling database setiap 30 detik
4. Config changes langsung apply ke userbot!

### Config Sync Flow:
```
Bot Wizard UI → Database → Userbot (auto-apply)
```

### Features yang Bisa Dikontrol:
- 📢 **Broadcast Scheduler**: Message, interval, target groups
- 🤖 **Auto Reply Rules**: Keywords, responses, targets
- ⚙️ **Feature Toggle**: Enable/disable via Bot Wizard

### No Manual Commands Needed:
- ❌ **Old**: User harus manual `!sg`, `!rg` commands
- ✅ **New**: User setup via Bot Wizard UI, userbot auto-apply

### Database Session Mode:
```env
# Di userbot/.env
SESSION_OWNER_ID=123456789
SECRET_KEY=same_key_as_bot_wizard
SHARED_API_ID=12345678  # fallback jika bot wizard ga ada
SHARED_API_HASH=abcd... # fallback
```

### Code Integration:
```python
# Config watcher otomatis running
# Cek database setiap 30s untuk changes
# Apply broadcast/reply configs otomatis
```

**🎉 Result: User-friendly web control + powerful userbot automation!**
