#!/bin/bash
# Switch the ResearchHub bot launchd job to a Homebrew Python (works around macOS blocking /usr/bin/python3 from the NAS)
P=""
for c in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$c" ] && P="$c" && break; done
if [ -z "$P" ]; then echo "NO_REAL_PYTHON: python.org/Homebrew Python not found. Stop and tell the admin."; exit 1; fi
PL="$HOME/Library/LaunchAgents/com.researchhub.bot.plist"
cp "$PL" "$PL.bak-py" || exit 1
sed -i '' "s#<string>/usr/bin/python3</string>#<string>$P</string>#" "$PL"
launchctl bootout gui/$(id -u) "$PL" 2>/dev/null
launchctl bootstrap gui/$(id -u) "$PL"
launchctl kickstart -k gui/$(id -u)/com.researchhub.bot
echo "Add this app to Full Disk Access: /Library/Frameworks/Python.framework/Versions/Current/Resources/Python.app"
echo "Bot now uses $P. Wait 3 minutes, then run: tail -n 5 ~/ResearchHub/data/bot.log"
