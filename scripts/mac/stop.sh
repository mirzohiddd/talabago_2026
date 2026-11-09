#!/bin/bash
# TalabaGo — barcha servislarni to‘xtatish (npm → node kabi bola jarayonlar bilan birga).
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
RUN="$ROOT/.run"
kill_tree() {
  local pid="$1" child
  for child in $(pgrep -P "$pid" 2>/dev/null); do kill_tree "$child"; done
  kill "$pid" 2>/dev/null
}
for f in "$RUN"/*.pid; do
  [ -e "$f" ] || continue
  pid="$(cat "$f")"
  if kill -0 "$pid" 2>/dev/null; then
    kill_tree "$pid"
    [ "${1:-}" = "--quiet" ] || echo "to‘xtatildi: $(basename "$f" .pid)"
  fi
  rm -f "$f"
done
exit 0
