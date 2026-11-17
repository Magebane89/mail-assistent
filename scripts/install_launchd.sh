#!/bin/bash
# Richtet unter macOS einen LaunchAgent ein, der regelmäßig scannt.
# Standard: täglich alle 30 Minuten zwischen 08:00 und 18:00.
# Anderes Zeitfenster:  SCAN_FROM=7 SCAN_TO=20 scripts/install_launchd.sh
# Rund um die Uhr:      SCAN_FROM=0 SCAN_TO=23 scripts/install_launchd.sh
set -euo pipefail
BASE="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="local.paperclip.gmail-review"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
FROM="${SCAN_FROM:-8}"; TO="${SCAN_TO:-18}"
if [[ ! -x "$BASE/.venv/bin/python" ]]; then echo 'Bitte zuerst .venv installieren.' >&2; exit 1; fi
if ! [[ "$FROM" =~ ^[0-9]+$ && "$TO" =~ ^[0-9]+$ ]] || (( FROM > TO || TO > 23 )); then
  echo 'SCAN_FROM und SCAN_TO müssen Stunden zwischen 0 und 23 sein (SCAN_FROM <= SCAN_TO).' >&2; exit 1
fi
mkdir -p "$HOME/Library/LaunchAgents" "$BASE/state"
slots=""
for (( h=FROM; h<=TO; h++ )); do
  slots+="    <dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>0</integer></dict>"$'\n'
  if (( h < TO )); then
    slots+="    <dict><key>Hour</key><integer>$h</integer><key>Minute</key><integer>30</integer></dict>"$'\n'
  fi
done
cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key><array>
    <string>/bin/bash</string><string>$BASE/scripts/scan_with_ollama.sh</string>
  </array>
  <key>WorkingDirectory</key><string>$BASE</string>
  <key>StartCalendarInterval</key><array>
$slots  </array>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$BASE/state/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$BASE/state/launchd.err.log</string>
</dict></plist>
PLIST
plutil -lint "$PLIST" >/dev/null
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
printf 'Scan alle 30 Minuten zwischen %02d:00 und %02d:00 eingerichtet: %s\n' "$FROM" "$TO" "$PLIST"
echo 'Bitte NICHT gleichzeitig Paperclip-Heartbeats aktivieren, um Doppelausführung zu vermeiden.'
