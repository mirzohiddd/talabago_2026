#!/bin/bash
# TalabaGo — macOS’da bir martalik o‘rnatish.  Ishlatish:  bash scripts/mac/setup.sh
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
say() { printf '\n\033[1;32m▶ %s\033[0m\n' "$1"; }
die() { printf '\n\033[1;31m✖ %s\033[0m\n' "$1"; exit 1; }

say "Talablar tekshirilmoqda"
command -v brew >/dev/null || die "Homebrew yo‘q: https://brew.sh"
PY=""
for c in python3.13 python3.12 python3.11 python3; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then PY="$c"; break; fi
done
[ -n "$PY" ] || { echo "Python 3.11+ o‘rnatilmoqda..."; brew install python@3.12; PY=python3.12; }
command -v node >/dev/null || { echo "Node.js o‘rnatilmoqda..."; brew install node; }
node -e 'process.exit(+process.versions.node.split(".")[0] >= 20 ? 0 : 1)' || die "Node.js 20+ kerak: brew upgrade node"
command -v cloudflared >/dev/null || { echo "cloudflared o‘rnatilmoqda..."; brew install cloudflared; }
echo "Python: $($PY --version) · Node: $(node --version) · $(cloudflared --version 2>/dev/null | head -1)"

say "Backend (venv + kutubxonalar)"
cd "$ROOT/backend"
[ -d .venv ] || "$PY" -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements-dev.txt
if [ ! -f .env ]; then
  cp .env.example .env
  SECRET="$(.venv/bin/python -m app.cli secret)"
  /usr/bin/sed -i '' "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$SECRET|; s|^COOKIE_SECURE=.*|COOKIE_SECURE=false|" .env
  echo ".env yaratildi (JWT_SECRET_KEY generatsiya qilindi). BOT_TOKEN va ADMIN_ID ni o‘zingiz yozing: open -e \"$ROOT/backend/.env\""
fi

say "Frontendlar (npm install)"
for app in frontend frontend2; do
  cd "$ROOT/$app"
  [ -f .env ] || cp .env.example .env
  npm install --no-fund --no-audit --silent
done

say "Administrator"
cd "$ROOT/backend"
if .venv/bin/python - <<'PY'
import json, pathlib, sys
from app.config import get_settings
p = pathlib.Path(get_settings().DATA_DIR) / 'db' / 'admins.json'
s = get_settings()
sys.exit(0 if (p.exists() and json.loads(p.read_text() or '[]')) or (s.ADMIN_USERNAME and s.ADMIN_PASSWORD_HASH) else 1)
PY
then echo "Administrator sozlangan."
else
  read -r -p "Administrator login (masalan, admin): " ADMIN_LOGIN
  .venv/bin/python -m app.cli create-admin --username "$ADMIN_LOGIN"
fi

say "Tayyor. Ishga tushirish:  bash scripts/mac/start.sh"
