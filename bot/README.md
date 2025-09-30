# 🧙‍♂️ Bot Wizard - Interface Chat untuk UserbotMaker

**👋 Untuk Pemula**: Bot Wizard adalah interface chat yang memungkinkan user membuat userbot tanpa coding. Cukup chat dengan bot, ikuti instruksi, dan userbot Anda siap!

> 🎆 **Magic**: User hanya perlu memberikan session string Telegram mereka, dan bot wizard otomatis membuat userbot dengan semua features!

## 🚀 Setup Bot Wizard (untuk Admin/Developer)

> 📋 **Note**: Bagian ini hanya untuk yang ingin setup Bot Wizard sendiri. Jika hanya ingin menggunakan userbot, cukup chat dengan bot yang sudah jadi!

### 🤖 **Langkah 1: Buat Bot Telegram**
1. Chat [@BotFather](https://t.me/BotFather) di Telegram
2. Kirim `/newbot` → ikuti instruksi penamaan
3. **Copy & Simpan** BOT_TOKEN yang diberikan

### 🔑 **Langkah 2: Dapatkan Telegram API**
1. Buka [my.telegram.org](https://my.telegram.org)
2. Login dengan nomor Telegram Anda
3. **API Development** → Create new application
4. **Copy & Simpan** API_ID dan API_HASH

### 👤 **Langkah 3: Cari User ID Anda**
1. Chat [@userinfobot](https://t.me/userinfobot)
2. Bot akan berikan **User ID** Anda (contoh: `123456789`)
3. **User ID ini otomatis jadi admin!**

### ⚙️ **Langkah 4: Setup Virtual Environment**
```bash
cd bot/

# Buat virtual environment
python3 -m venv .venv

# Activate virtual environment
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Setup environment file
cp .env.example .env
nano .env  # Edit dengan credentials Anda
```

> 📝 **Note**: Selalu activate venv sebelum run: `source .venv/bin/activate`

### Step 4a: Database Setup (Neon PostgreSQL - REQUIRED)
**🚀 Neon Database Setup:**
- ☁️ **Cloud-based PostgreSQL**: Fully managed database
- 🆓 **Free tier**: 0.5GB storage, 100 hours compute/month  
- 🔄 **Auto-scaling**: Hibernation dan auto-wake
- 📖 **Setup Guide**: [docs/NEON_SETUP.md](../docs/NEON_SETUP.md)
- ⚡ **Required**: DATABASE_URL harus di-set untuk semua operations

### Step 5: Fill Configuration
**Edit file `.env` dengan data kamu:**

```env
# Database URL - Neon PostgreSQL (REQUIRED)
DATABASE_URL=postgresql://username:password@ep-xxxx.us-east-1.aws.neon.tech/dbname?sslmode=require

# Bot Token dari @BotFather (WAJIB)
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# Secret key untuk enkripsi (generate random 32+ karakter)
SECRET_KEY=abcd1234567890abcd1234567890abcd

# SHARED API untuk semua userbot (WAJIB)
SHARED_API_ID=12345678
SHARED_API_HASH=abcd1234567890abcd1234567890abcd

# Owner/Admin ID - kamu jadi admin otomatis (WAJIB)
OWNER_TELEGRAM_IDS=123456789
```

### **🚀 Langkah 5: Run Bot**
```bash
# Pastikan masih dalam venv yang aktif
source .venv/bin/activate
python main.py
```

🎉 **Done!** Bot Wizard siap digunakan!

## 🚀 Running the Bot

### **⚡ Recommended (dengan venv)**
```bash
cd bot/
source .venv/bin/activate  # SELALU activate venv dulu
python main.py
```

### **🛠️ Alternative (shared venv dari root)**
```bash
# Dari root project
source .venv/bin/activate
cd bot && python main.py
```

> ⚠️ **Important**: Bot perlu virtual environment untuk dependencies isolation

## 🐍 **Virtual Environment Management**

### **🚀 Quick Setup**
```bash
cd bot/

# Buat venv (sekali aja)
python3 -m venv .venv

# Activate (setiap kali mau run)
source .venv/bin/activate

# Install deps (sekali aja atau kalo ada update)
pip install -r requirements.txt
```

### **⚙️ Daily Usage**
```bash
# Setiap kali mau run bot:
cd bot/
source .venv/bin/activate  # ⚡ WAJIB!
python main.py
```

### **🧪 Check Venv Status**
```bash
# Check apakah venv aktif
which python  # Harus show path ke .venv/bin/python

# Check installed packages
pip list

# Deactivate venv (kalo perlu)
deactivate
```

### **🐛 Troubleshooting Venv**
- ✅ **Venv not found**: Buat ulang dengan `python3 -m venv .venv`
- ✅ **Permission denied**: Pakai `python3 -m venv .venv --clear`
- ✅ **Wrong Python**: Check dengan `python --version` (harus 3.11+)
- ✅ **Module not found**: Re-install dengan `pip install -r requirements.txt`

## 📱 How to Use

## 💡 Cara Kerja

### Untuk Owner/Admin (kamu):
- ✅ **Admin Otomatis**: ID di `OWNER_TELEGRAM_IDS` jadi admin
- ✅ **Bypass Payment**: Tidak perlu bayar, langsung buat userbot
- ✅ **Admin Panel**: Monitor semua user dan control sistem
- ✅ **Full Access**: Bisa disable userbot user lain

### Untuk User Biasa:
- 💰 **Payment Required**: Bayar dulu sebelum bisa buat userbot
- 🔄 **Simple Flow**: Hanya perlu session string, API otomatis
- ⚡ **Fast Setup**: Tidak perlu input API_ID/API_HASH lagi

### User Experience:
1. Start chat dengan bot
2. **Owner**: Langsung akses admin panel + create userbot
3. **User biasa**: Payment → Session string → Userbot created!
4. **Features**: Broadcast, Auto Reply, Group Management

### Commands:
- `/start` - Mulai proses (admin panel atau payment flow)
- `/features` - Setup userbot features (broadcast, auto reply)
- `/dashboard` - Lihat status userbot dan configs
- `/admin` - Admin panel (owner only)

## 🔐 Security & Features

### Security:
- ✅ **Session Encrypted**: Fernet encryption untuk semua session
- ✅ **Owner Validation**: Auto-detect owner dari environment
- ✅ **Access Control**: Payment validation untuk user biasa
- ✅ **API Protection**: Shared API tersentralisasi
- ✅ **Admin Logging**: Semua admin actions ter-log

### Key Features:
- 🛡️ **Admin Panel**: Full system monitoring dan control
- 📢 **Broadcast**: Schedule message ke multiple groups
- 🤖 **Auto Reply**: Smart reply dengan keyword/regex
- 👥 **User Management**: Monitor semua users dan userbots
- 📊 **Analytics**: Usage stats dan system health
- 🚨 **Emergency Controls**: Force disable problematic userbots

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

### Admin access tidak jalan
- ✅ Pastikan `OWNER_TELEGRAM_IDS` berisi ID Telegram kamu
- ✅ Restart bot setelah ubah .env
- ✅ Test dengan: Chat `/start` ke bot, harus muncul admin panel

### Environment configuration error
- ✅ Pastikan `SHARED_API_ID` dan `SHARED_API_HASH` benar
- ✅ Generate `SECRET_KEY` random 32+ karakter
- ✅ Test environment dengan: `python -c "from userbot.bot_wizard_helpers import get_environment_setup_status; print(get_environment_setup_status())")`

### User tidak bisa buat userbot
- ✅ User biasa harus payment dulu (kecuali owner)
- ✅ Session string harus valid dari Telegram
- ✅ Cek apakah SHARED_API_* configured dengan benar

### Session tidak tersimpan
- ✅ Pastikan folder `../data/` ada dan writable
- ✅ Jika menggunakan enkripsi, pastikan `SECRET_KEY` terisi

## 📊 Logs & Monitoring

- **Console logs**: Real-time di terminal
- **File logs**: `../logs/bot.log` (rotated automatically)
- **Telegram logs**: Error penting dikirim ke `TELEGRAM_LOG_CHAT_ID` (jika diset)

## 🔄 Integration dengan Userbot System

### Data Flow:
```
Bot Wizard (.env) → Database → Userbot (auto config)
```

### Key Integration:
- **Shared Database**: `../data/userbotmaker.db` untuk bot wizard & userbot
- **Shared API**: `SHARED_API_*` digunakan untuk semua userbot
- **Owner Detection**: Userbot auto-detect owner dari environment
- **Config Sync**: Bot Wizard simpan config → Userbot polling & apply

### Code Example:
```python
# Di Bot Wizard handler
from userbot.bot_wizard_helpers import create_bot_wizard_manager

wizard_manager = create_bot_wizard_manager()

# Check user access
access = wizard_manager.check_user_access(user_id)
if access["access_type"] == "admin":
    # Show admin panel
    dashboard = wizard_manager.get_user_dashboard(user_id)
elif access["can_use_features"]:
    # Show user features
    pass
else:
    # Show payment flow
    pass

# Create userbot (auto API)
result = wizard_manager.create_userbot_session(
    user_id=user_id,
    session_string=session_string  # Only this from user!
)
```

## 📈 Admin Capabilities

### System Monitoring:
- 📊 **Real-time Stats**: Total users, active userbots, configs
- 👥 **User Search**: Find dan manage specific users
- 🔍 **User Details**: Sessions, configs, recent activity
- 📋 **Activity Logs**: Complete audit trail

### Control Features:
- ⚙️ **Config Management**: Enable/disable any user's features
- 🚨 **Emergency Stop**: Force disable problematic userbots
- 👨‍💼 **Admin Management**: Add/remove admin users
- 📊 **Health Check**: System performance monitoring

### Typical Admin Workflow:
```
1. /start → Admin Dashboard
2. View system stats
3. Search problematic user
4. Review user details
5. Take action (disable, etc)
6. Check activity logs
```

---

**🎯 Result: User-friendly bot creation + powerful admin control system!**
