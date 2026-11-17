#!/bin/bash
set -euo pipefail
PLIST="$HOME/Library/LaunchAgents/local.paperclip.gmail-review.plist"
launchctl bootout "gui/$(id -u)" "$PLIST" >/dev/null 2>&1 || true
rm -f "$PLIST"
echo 'Automatische Scans gestoppt. Datenbank und OAuth-Daten bleiben erhalten.'
