# 🚀 UserbotMaker Quick Start (Neon Database)

**Simple 5-step setup untuk UserbotMaker dengan Neon PostgreSQL.**

## Prerequisites

- Python 3.11+ 
- Neon account (gratis di [neon.tech](https://neon.tech))
- Telegram Bot Token (dari [@BotFather](https://t.me/BotFather))
- Telegram API credentials (dari [my.telegram.org](https://my.telegram.org))

## Step 1: Setup Neon Database

1. **Create Neon Account**: Sign up di [neon.tech](https://neon.tech)
2. **Create Project**: Buat project baru bernama "userbotmaker"
3. **Get Connection String**: Copy connection string format:
   ```
   postgresql://username:password@ep-xxxx.us-east-1.aws.neon.tech/dbname?sslmode=require
   ```

## Step 2: Install Dependencies

```bash
# Bot Wizard
cd bot/
pip install -r requirements.txt

# Userbot Engine  
cd ../userbot/
pip install -r requirements.txt
```

## Step 3: Configure Environment

**Bot (.env):**
```bash
cd bot/
cp .env.example .env
nano .env
```

```env
# Database - Neon PostgreSQL (REQUIRED)
DATABASE_URL=postgresql://your_connection_string_here

# Bot Token dari @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABC-DEF...

# Secret untuk enkripsi  
SECRET_KEY=your-32-char-random-key

# Shared API untuk semua userbot
SHARED_API_ID=12345678
SHARED_API_HASH=abcd1234567890abcd1234567890abcd

# Owner IDs (auto admin)
OWNER_TELEGRAM_IDS=123456789
```

**Userbot (.env):**
```bash
cd ../userbot/
cp .env.example .env  
nano .env
```

```env
# Database - Same as bot
DATABASE_URL=postgresql://your_connection_string_here

# Shared API (sama dengan bot)
SHARED_API_ID=12345678
SHARED_API_HASH=abcd1234567890abcd1234567890abcd

# Secret Key (untuk dekripsi session)
SECRET_KEY=your-32-char-random-key

# JANGAN set SESSION_OWNER_ID di .env - akan diset via argument
```

## Step 4: Run Bot Wizard

```bash
cd bot/
python main.py
```

Bot akan otomatis:
- ✅ Connect ke Neon database
- ✅ Create tables yang dibutuhkan
- ✅ Setup admin access untuk OWNER_IDS
- ✅ Ready untuk user registration

## Step 5: Run Userbot untuk User Tertentu

```bash
cd userbot/
# Ganti 123456789 dengan Telegram ID user yang sudah buat session
./run_userbot.sh 123456789

# Atau manual:
# python main.py --owner-id 123456789
```

Userbot akan:
- ✅ Connect ke Neon database
- ✅ Load session untuk user tertentu (owner-id)
- ✅ Start userbot dengan all features untuk user tersebut

## ✅ Verification

**Test Bot:**
1. Chat bot di Telegram dengan akun owner
2. Kirim `/start` - harus muncul admin panel
3. Coba buat userbot session baru

**Test Userbot:**
1. Check logs untuk connection success
2. Verify database tables di Neon dashboard
3. Test feature configurations

## 🔧 Troubleshooting

**"psycopg2 tidak tersedia":**
```bash
pip install psycopg2-binary
```

**"DATABASE_URL harus di-set":**
- Pastikan .env file benar
- Check format connection string dari Neon

**"Connection failed":**
- Check Neon database status (hibernated?)
- Verify connection string credentials
- Test network connection

**"Permission denied":**
- Verify OWNER_TELEGRAM_IDS di .env
- Restart bot after changing .env
- Check user ID dengan @userinfobot

## 📊 Monitoring

- **Neon Dashboard**: Monitor database usage dan connections
- **Bot Logs**: Check `../logs/bot.log` untuk bot activities
- **Userbot Logs**: Check `../logs/userbot.log` untuk userbot activities

## 🎯 Next Steps

1. **Admin Panel**: Use `/admin` command untuk full system control
2. **User Features**: Configure broadcast, auto-reply, scheduling
3. **Monitoring**: Setup TELEGRAM_LOG_CHAT_ID untuk log forwarding
4. **Scaling**: Monitor Neon usage dan upgrade plan bila perlu

---

**🎉 Done!** UserbotMaker sekarang running dengan Neon PostgreSQL database yang reliable dan scalable!