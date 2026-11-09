#!/bin/bash
# TalabaGo — barcha servislarni ishga tushirish (macOS).
#   bash scripts/mac/start.sh              # backend + Mini App + Support + tezkor Cloudflare tunnel (https://*.trycloudflare.com) + bot
#   bash scripts/mac/start.sh --named      # doimiy domen: deploy/cloudflared/config.yml (FRONTEND_URL/SUPPORT_URL .env da)
#   bash scripts/mac/start.sh --local      # tunnelsiz, faqat http://localhost (Telegram Mini App tugmasi ishlamaydi)
#   bash scripts/mac/start.sh --dev        # frontendlar Vite dev server’da (hot reload; faqat dasturlash uchun)
# Standart: frontendlar production build qilinadi (npm run build) va tayyor fayllar beriladi — Telegram’da tez ochiladi.
# To‘xtatish: bash scripts/mac/stop.sh     Loglar: .run/logs/
set -uo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN="$ROOT/.run"; LOGS="$RUN/logs"; mkdir -p "$LOGS"
MODE="quick"; DEV=0
for a in "$@"; do
  case "$a" in
    --named) MODE="named" ;; --local) MODE="local" ;; --dev) DEV=1 ;;
    *) printf 'Noma’lum parametr: %s (--named | --local | --dev)\n' "$a"; exit 1 ;;
  esac
done
PYBIN="$ROOT/backend/.venv/bin/python"
say() { printf '\033[1;32m▶ %s\033[0m\n' "$1"; }
warn() { printf '\033[1;33m! %s\033[0m\n' "$1"; }
die() { printf '\033[1;31m✖ %s\033[0m\n' "$1"; exit 1; }
[ -x "$PYBIN" ] || die "Avval o‘rnating: bash scripts/mac/setup.sh"
bash "$ROOT/scripts/mac/stop.sh" --quiet

start_bg() { # nom, papka, buyruq... — fon jarayoni terminaldan to‘liq ajratiladi (stdin/stdout/stderr → log)
  local name="$1" dir="$2"; shift 2
  ( cd "$dir" || exit 1; nohup "$@" < /dev/null > "$LOGS/$name.log" 2>&1 & echo $! > "$RUN/$name.pid" )
}
wait_http() { # url, soniya
  for _ in $(seq 1 "$2"); do curl -fs -o /dev/null --max-time 3 "$1" 2>/dev/null && return 0; sleep 1; done; return 1
}
env_get() { /usr/bin/grep -E "^$1=" "$ROOT/backend/.env" | tail -1 | cut -d= -f2-; }

if [ "$DEV" = 1 ]; then
  say "Frontendlar (dev server, hot reload): Mini App (5173), TalabaGo Support (5174)"
  start_bg frontend "$ROOT/frontend" npx vite
  start_bg frontend2 "$ROOT/frontend2" npx vite
else
  # Dev server tunnel orqali yuzlab alohida modul yuboradi — telefonda uzoq oq ekran. Production build: bir necha siqilgan fayl.
  say "Frontendlar production build qilinmoqda (Mini App va TalabaGo Support)"
  for d in frontend frontend2; do
    ( cd "$ROOT/$d" && npx vite build > "$LOGS/$d-build.log" 2>&1 ) || die "$d build xatosi: $LOGS/$d-build.log"
  done
  say "Frontendlar: Mini App (5173), TalabaGo Support (5174)"
  start_bg frontend "$ROOT/frontend" npx vite preview --port 5173
  start_bg frontend2 "$ROOT/frontend2" npx vite preview --port 5174
fi
wait_http http://127.0.0.1:5173 40 || die "Mini App ishga tushmadi: $LOGS/frontend.log"
wait_http http://127.0.0.1:5174 40 || die "Support ishga tushmadi: $LOGS/frontend2.log"

APP_URL="http://localhost:5173"; SUP_URL="http://localhost:5174"
if [ "$MODE" = "quick" ]; then
  command -v cloudflared >/dev/null || die "cloudflared yo‘q: brew install cloudflared"
  say "Cloudflare tezkor tunnellari (HTTP/2 — QUIC timeout’siz)"
  for spec in "tunnel-app:5173" "tunnel-support:5174"; do
    n="${spec%%:*}"; port="${spec##*:}"
    start_bg "$n" "$ROOT" cloudflared tunnel --no-autoupdate --protocol http2 --edge-ip-version auto --url "http://127.0.0.1:$port"
  done
  # “api.trycloudflare.com” — xizmat manzili (xato xabarlarida ham uchraydi), tunnel manzili emas
  find_url() { /usr/bin/grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$LOGS/$1.log" 2>/dev/null | /usr/bin/grep -v '^https://api\.' | head -1; }
  tunnel_error() { /usr/bin/grep -E 'failed to request quick Tunnel|no such host|i/o timeout|failed to dial' "$LOGS/$1.log" 2>/dev/null | tail -1; }
  for _ in $(seq 1 45); do APP_URL="$(find_url tunnel-app)"; SUP_URL="$(find_url tunnel-support)"; [ -n "$APP_URL" ] && [ -n "$SUP_URL" ] && break; sleep 1; done
  if [ -z "$APP_URL" ] || [ -z "$SUP_URL" ]; then
    printf '%s\n' "$(tunnel_error tunnel-app)"
    die "Tunnel manzili olinmadi (DNS/tarmoq). Yechim: README → “Cloudflare muammolari”. Log: $LOGS/tunnel-app.log"
  fi
  # Yangi trycloudflare manzili DNS’da paydo bo‘lishini kutish (aks holda “DNS_PROBE_FINISHED_NXDOMAIN”)
  say "Tunnel DNS tayyor bo‘lishi kutilmoqda: $APP_URL"
  wait_http "$APP_URL" 90 || warn "Tunnel hali javob bermayapti — DNS keshini tozalang: sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder"
  wait_http "$SUP_URL" 60 || true
  ( cd "$ROOT/backend" && "$PYBIN" -m app.cli set-env "FRONTEND_URL=$APP_URL" "SUPPORT_URL=$SUP_URL" COOKIE_SECURE=true )
elif [ "$MODE" = "named" ]; then
  CFG="$ROOT/deploy/cloudflared/config.yml"
  [ -f "$CFG" ] || die "Yo‘q: $CFG (config.example.yml dan nusxa oling)"
  say "Cloudflare doimiy tunnel (HTTP/2)"
  start_bg tunnel "$ROOT" cloudflared tunnel --config "$CFG" --protocol http2 run
  APP_URL="$(env_get FRONTEND_URL)"; SUP_URL="$(env_get SUPPORT_URL)"
  wait_http "$APP_URL" 60 || warn "Domen javob bermayapti: $LOGS/tunnel.log"
else
  ( cd "$ROOT/backend" && "$PYBIN" -m app.cli set-env FRONTEND_URL=http://localhost:5173 SUPPORT_URL=http://localhost:5174 COOKIE_SECURE=false >/dev/null )
fi

say "Backend (FastAPI, 8000)"
start_bg backend "$ROOT/backend" "$PYBIN" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --proxy-headers --forwarded-allow-ips 127.0.0.1
wait_http http://127.0.0.1:8000/api/v1/health 30 || die "Backend ishga tushmadi: $LOGS/backend.log"

if [ -n "$(env_get BOT_TOKEN)" ]; then
  if [ "$MODE" = "local" ]; then
    warn "Telegram Mini App https talab qiladi — --local rejimda bot tugmasi yuborilmaydi"
  fi
  say "Telegram bot (polling) + menyu tugmasi"
  start_bg bot "$ROOT/backend" "$PYBIN" -m app.bot
  sleep 3
  ( cd "$ROOT/backend" && "$PYBIN" -m app.cli bot-check ) || true
else
  warn "BOT_TOKEN bo‘sh — bot ishga tushirilmadi (backend/.env)"
fi

printf '\n\033[1m TalabaGo ishlayapti\033[0m\n'
printf '  Mini App:          %s\n' "$APP_URL"
printf '  TalabaGo Support:  %s\n' "$SUP_URL"
printf '  API hujjati:       http://127.0.0.1:8000/api/docs\n'
printf '  Loglar:            %s\n  To‘xtatish:        bash scripts/mac/stop.sh\n\n' "$LOGS"
[ "$MODE" = "quick" ] && warn "Tezkor tunnel manzili har ishga tushganda o‘zgaradi. Bot menyu tugmasi avtomatik yangilanadi; BotFather’dagi Main Mini App URL’ini esa qo‘lda yangilang (yoki --named ishlating)."
exit 0
