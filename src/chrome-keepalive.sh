#!/bin/bash
# Keeps Chrome running and "awake" so the Claude in Chrome extension reconnects before a scheduled slot.
# Usage: chrome-keepalive.sh [always]   (always = used at login)
H=$(date +%-H); N=$(( (H+1) % 24 ))
IV=$(python3 -c "import json;print(json.load(open('$HOME/ResearchHub/data/schedule.local.json')).get('interval_hours',3))" 2>/dev/null || echo 3)
SLOT=0
if [ "$N" -ge 8 ] && [ "$N" -lt 20 ] && [ $(( (N-8) % IV )) -eq 0 ]; then SLOT=1; fi
UP=$(( $(date +%s) - $(sysctl -n kern.boottime | sed "s/.*sec = \([0-9]*\).*/\1/") ))
if [ "$UP" -lt 900 ] || [ "$1" = "always" ] || [ "$SLOT" = 1 ] || [ -e "$HOME/ResearchHub/data/run-now" ]; then
  pgrep -qx "Claude" || open -g -a "Claude"
  open -a "Google Chrome"
  sleep 20
  open -g -a "Claude"
fi
