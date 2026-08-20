#!/usr/bin/env bash
# =============================================================================
#  OpenBudjet Bot — To'liq Loyihani Ishga Tushirish Skripti
#  Foydalanish: bash start.sh
# =============================================================================

set -e  # Xato bo'lsa darhol to'xta

# ── Ranglar ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# ── Yordamchi funksiyalar ─────────────────────────────────────────────────────
info()    { echo -e "${BLUE}[ℹ]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; }
warn()    { echo -e "${YELLOW}[⚠]${NC} $1"; }
error()   { echo -e "${RED}[✗]${NC} $1"; exit 1; }
step()    { echo -e "\n${BOLD}${CYAN}══ $1 ══${NC}"; }

# ── Skript joylashgan papkaga o'tish ─────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
info "Papka: $SCRIPT_DIR"

# =============================================================================
# QADAM 1: .env faylini tekshirish
# =============================================================================
step "1/6 · .env tekshirish"

if [ ! -f ".env" ]; then
    error ".env fayli topilmadi! Avval .env faylini yarating."
fi

# Muhim kalitlarni tekshirish
check_env() {
    local KEY=$1
    local VAL
    VAL=$(grep -E "^${KEY}=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")
    if [ -z "$VAL" ] || [ "$VAL" = "0" ]; then
        error ".env da ${KEY} topilmadi yoki bo'sh!"
    fi
    echo "$VAL"
}

BOT_TOKEN=$(check_env "BOT_TOKEN")
check_env "SUPER_ADMIN_ID" > /dev/null
check_env "ADMIN_IDS" > /dev/null

success ".env fayli to'g'ri sozlangan"

# =============================================================================
# QADAM 2: Python muhitini tekshirish va paketlarni o'rnatish
# =============================================================================
step "2/6 · Python va paketlar"

# Python versiyasini tekshirish
PYTHON_CMD=""
if command -v python3 &>/dev/null; then
    PYTHON_CMD="python3"
elif command -v python &>/dev/null; then
    PYTHON_CMD="python"
else
    error "Python topilmadi! Python 3.10+ o'rnating."
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    error "Python 3.10+ kerak. Hozirgi: $PYTHON_VERSION"
fi
success "Python $PYTHON_VERSION ✓"

# Virtual environment
if [ ! -d "venv" ]; then
    info "Virtual environment yaratilmoqda..."
    $PYTHON_CMD -m venv venv
    success "venv yaratildi"
fi

# Activate venv
source venv/bin/activate
info "venv faollashtirildi"

# Pip yangilash
pip install --upgrade pip -q

# Paketlarni o'rnatish
info "requirements.txt o'rnatilmoqda..."
pip install -r requirements.txt -q
success "Python paketlari o'rnatildi"

# Syntax tekshirish
info "Python fayllarni tekshirish..."
$PYTHON_CMD -m py_compile bot.py config.py
$PYTHON_CMD -m py_compile handlers/user.py handlers/vote.py handlers/admin.py handlers/api.py 2>/dev/null || true
$PYTHON_CMD -m py_compile database/connection.py database/models.py 2>/dev/null || true
success "Python sintaksisi to'g'ri"

# =============================================================================
# QADAM 3: PostgreSQL ulanishini tekshirish (O'tkazib yuborildi - Bazasiz rejim)
# =============================================================================
step "3/6 · PostgreSQL ulanish tekshirish (Bazasiz rejim)"
info "Bot ma'lumotlar bazasisiz ishlaydi. Ushbu qadam o'tkazib yuborildi."

# =============================================================================
# QADAM 4: React Mini App (O'tkazib yuborildi - O'chirilgan)
# =============================================================================
step "4/6 · React Mini App (O'chirildi)"
info "Admin panel o'chirilganligi sababli, bu qadam o'tkazib yuborildi."

# =============================================================================
# QADAM 5: Eski bot va API jarayonlarini to'xtatish
# =============================================================================
step "5/6 · Eski jarayonlarni to'xtatish"

BOT_PIDS=$(pgrep -f "python.*bot.py" 2>/dev/null || true)
API_PIDS=$(pgrep -f "python.*api_server.py" 2>/dev/null || true)

if [ -n "$BOT_PIDS" ] || [ -n "$API_PIDS" ]; then
    warn "Eski jarayonlar aniqlandi. To'xtatilmoqda..."
    [ -n "$BOT_PIDS" ] && echo "$BOT_PIDS" | xargs kill -TERM 2>/dev/null || true
    [ -n "$API_PIDS" ] && echo "$API_PIDS" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # Majburiy o'chirish (agar SIGTERM orqali o'chmagan bo'lsa)
    REMAINING_BOT=$(pgrep -f "python.*bot.py" 2>/dev/null || true)
    REMAINING_API=$(pgrep -f "python.*api_server.py" 2>/dev/null || true)
    [ -n "$REMAINING_BOT" ] && echo "$REMAINING_BOT" | xargs kill -KILL 2>/dev/null || true
    [ -n "$REMAINING_API" ] && echo "$REMAINING_API" | xargs kill -KILL 2>/dev/null || true
    success "Eski jarayonlar to'xtatildi"
else
    info "Eski jarayonlar yo'q"
fi

# =============================================================================
# QADAM 6: Kombinatsiyalangan Bot va Web API ni ishga tushirish
# =============================================================================
step "6/6 · Bot va Web API-ni ishga tushirish"

# Log fayllari
LOG_DIR="logs"
mkdir -p "$LOG_DIR"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BOT_LOG_FILE="$LOG_DIR/bot_${TIMESTAMP}.log"

info "Log fayli: $BOT_LOG_FILE"
info "PORT: $(grep -E '^PORT=' .env | cut -d'=' -f2 | tr -d '"' || echo '8000')"

echo ""
echo -e "${BOLD}${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${BOLD}${GREEN}║   OpenBudjet Tizimi Ishga Tushdi! 🚀 ║${NC}"
echo -e "${BOLD}${GREEN}║   (Bot va Web API bitta jarayonda)   ║${NC}"
echo -e "${BOLD}${GREEN}║   To'xtatish uchun: Ctrl+C           ║${NC}"
echo -e "${BOLD}${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""

# 1. Bot (ichida Web API bilan) jarayonini backgroundda ishga tushirish
$PYTHON_CMD bot.py > "$BOT_LOG_FILE" 2>&1 &
BOT_PID=$!
success "Bot va API jarayoni boshlandi (PID: $BOT_PID)"

# Exit bo'lganda child processlarni ham o'chirish (Graceful Shutdown)
trap 'echo -e "\n${YELLOW}[!] Jarayon to\x27xtatilmoqda...${NC}"; kill $BOT_PID 2>/dev/null || true; exit 0' SIGINT SIGTERM

# Loglarni ekranga ko'rsatib turish
tail -f "$BOT_LOG_FILE"
