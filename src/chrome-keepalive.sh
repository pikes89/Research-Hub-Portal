#!/bin/bash
# Keeps Chrome running and "awake" so the Claude in Chrome extension reconnects before a scheduled slot.
# Usage: chrome-keepalive.sh [always]   (always = used at login)
# Slots follow Philippine time (UTC+8) wherever the Mac is; wake Chrome if this or the next PH hour is a slot
H=$(TZ=Asia/Manila date +%-H); N=$(( (H+1) % 24 ))
IV=$(python3 -c "import json;print(json.load(open('$HOME/ResearchHub/data/schedule.local.json')).get('interval_hours',3))" 2>/dev/null || echo 3)
SLOT=0
for X in $H $N; do if [ "$X" -ge 8 ] && [ "$X" -lt 20 ] && [ $(( (X-8) % IV )) -eq 0 ]; then SLOT=1; fi; done
UP=$(( $(date +%s) - $(sysctl -n kern.boottime | sed "s/.*sec = \([0-9]*\).*/\1/") ))
if [ "$UP" -lt 900 ] || [ "$1" = "always" ] || [ "$SLOT" = 1 ] || [ -e "$HOME/ResearchHub/data/run-now" ]; then
  pgrep -qx "Claude" || open -g -a "Claude"
  open -a "Google Chrome"
  sleep 20
  open -g -a "Claude"
fi
