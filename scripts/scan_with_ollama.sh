#!/bin/bash
# Startet Ollama, falls es nicht läuft (z. B. nach einem Neustart), und führt dann den Scan aus.
# Ohne erreichbares Ollama wird NICHT gescannt, damit keine Mails ohne KI-Prüfung abgelegt werden.
set -uo pipefail
BASE="$(cd "$(dirname "$0")/.." && pwd)"
URL="$(/usr/bin/grep -E '^OLLAMA_URL=' "$BASE/.env" 2>/dev/null | /usr/bin/tail -1 | /usr/bin/cut -d= -f2-)"
URL="${OLLAMA_URL:-${URL:-http://127.0.0.1:11434}}"; URL="${URL%/}"
WAIT="${OLLAMA_WAIT_SECONDS:-90}"
stamp() { /bin/date '+%Y-%m-%d %H:%M:%S'; }
up() { /usr/bin/curl -s -o /dev/null --max-time 3 "$URL/api/version"; }

if ! up; then
  echo "$(stamp) Ollama nicht erreichbar, starte die Ollama-App …"
  /usr/bin/open -g -j -a Ollama || echo "$(stamp) Ollama-App konnte nicht geöffnet werden." >&2
  waited=0
  until up; do
    if (( waited >= WAIT )); then
      echo "$(stamp) Ollama nach ${WAIT}s nicht erreichbar. Scan übersprungen." >&2
      exit 1
    fi
    /bin/sleep 3; waited=$((waited+3))
  done
  echo "$(stamp) Ollama läuft (nach ${waited}s)."
fi
if [[ "${DRY_RUN:-0}" == "1" ]]; then echo "$(stamp) Ollama erreichbar, Probelauf ohne Scan."; exit 0; fi
echo "$(stamp) Scan startet."
exec "$BASE/.venv/bin/python" "$BASE/assistant_app.py" scan
