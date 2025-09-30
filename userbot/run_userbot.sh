#!/bin/bash
# Helper script untuk menjalankan userbot dengan owner ID

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🤖 UserbotMaker - Userbot Runner${NC}"
echo "=================================="

# Check if owner ID is provided, allow auto-detection
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}⚠️  No Owner ID specified, trying auto-detection...${NC}"
    echo ""
    
    # Try to run without owner-id (auto-detection mode)
    if ! python main.py; then
        echo ""
        echo -e "${RED}❌ Auto-detection failed${NC}"
        echo ""
        echo "Usage: $0 <telegram_owner_id>"
        echo "Contoh: $0 123456789"
        echo ""
        echo "💡 Cara mendapatkan Telegram ID:"
        echo "1. Chat ke bot @userinfobot di Telegram" 
        echo "2. Kirim pesan apa saja, bot akan reply dengan ID kamu"
        echo ""
        echo -e "${BLUE}🔍 Debug database:${NC}"
        echo "  python debug_db.py"
        exit 1
    fi
    exit 0
fi

OWNER_ID=$1

# Validate owner ID is numeric
if ! [[ "$OWNER_ID" =~ ^[0-9]+$ ]]; then
    echo -e "${RED}❌ Error: Owner ID harus berupa angka${NC}"
    echo "Contoh yang benar: 123456789"
    exit 1
fi

echo -e "${YELLOW}👤 Owner ID: ${OWNER_ID}${NC}"

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

echo -e "${BLUE}📁 Working directory: ${SCRIPT_DIR}${NC}"

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo -e "${YELLOW}⚠️  Virtual environment tidak ditemukan. Membuat .venv...${NC}"
    python3 -m venv .venv
    echo -e "${GREEN}✅ Virtual environment dibuat${NC}"
fi

# Activate virtual environment
echo -e "${BLUE}🔄 Activating virtual environment...${NC}"
source .venv/bin/activate

# Check if requirements are installed
if ! python -c "import telethon" 2>/dev/null; then
    echo -e "${YELLOW}⚠️  Dependencies belum terinstall. Installing...${NC}"
    pip install -r requirements.txt
    echo -e "${GREEN}✅ Dependencies terinstall${NC}"
fi

# Check environment variables
if [ -z "$DATABASE_URL" ] && [ ! -f ".env" ]; then
    echo -e "${RED}❌ Error: DATABASE_URL tidak ditemukan${NC}"
    echo ""
    echo "Solusi:"
    echo "1. Set environment variable:"
    echo "   export DATABASE_URL='postgresql://...'"
    echo "2. Atau buat file .env dengan DATABASE_URL"
    exit 1
fi

echo -e "${GREEN}🚀 Starting userbot for owner ${OWNER_ID}...${NC}"
echo -e "${YELLOW}💡 Tekan Ctrl+C untuk menghentikan${NC}"
echo ""

# Run the userbot with better error handling
if ! python main.py --owner-id "$OWNER_ID"; then
    echo ""
    echo -e "${RED}❌ Userbot gagal start${NC}"
    echo -e "${YELLOW}💡 Troubleshooting:${NC}"
    echo "1. Pastikan Bot Wizard sedang berjalan"
    echo "2. User dengan ID ${OWNER_ID} sudah registrasi via bot wizard"
    echo "3. User sudah membuat session (QR/OTP) dan punya subscription aktif"
    echo ""
    echo -e "${BLUE}🔍 Debug database:${NC}"
    echo "  python debug_db.py"
    exit 1
fi
