#!/bin/bash
# Installs the Research Hub downloader on this Mac (run once, as the logged-in user). Needs the NAS mounted at /Volumes/YOUR_NAS_SHARE.
set -e
NAS="/Volumes/YOUR_NAS_SHARE/research-archive"; I="$NAS/_hub/install"
[ -d "$NAS/_hub" ] || { echo "Mount the NAS first (Finder > Go > Connect to Server)"; exit 1; }
command -v python3 >/dev/null || { echo "python3 missing: run xcode-select --install"; exit 1; }
mkdir -p ~/ResearchHub/data && tar xzf "$I/researchhub-code.tgz" -C ~
cd ~/ResearchHub/data
for f in runs.jsonl schedule.json reminder.json ledger.jsonl; do [ -e "$f" ] || ln -s "$NAS/_hub/$f" "$f"; done
T=~/.claude/scheduled-tasks/portal-topic-downloads; mkdir -p "$T"
[ -e "$T/topic-queue.json" ] || ln -s "$NAS/_hub/topic-queue.json" "$T/topic-queue.json"
sed "s#/Users/YOURUSER#$HOME#g" "$I/SKILL.md" > "$T/SKILL.md"
for n in server keepalive; do
  sed "s#/Users/YOURUSER#$HOME#g" "$I/$n.plist" > ~/Library/LaunchAgents/com.researchhub.$n.plist
done
mv ~/Library/LaunchAgents/com.researchhub.keepalive.plist ~/Library/LaunchAgents/com.researchhub.chrome-keepalive.plist
sed -i '' 's#com.researchhub.keepalive#com.researchhub.chrome-keepalive#' ~/Library/LaunchAgents/com.researchhub.chrome-keepalive.plist
chmod +x ~/ResearchHub/*.sh
python3 ~/ResearchHub/hub-sync.py || true
for n in server chrome-keepalive; do launchctl bootout gui/$(id -u)/com.researchhub.$n 2>/dev/null || true; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.researchhub.$n.plist; done
touch ~/ResearchHub/data/auto-skill.flag   # lets the bot keep the task text in step with the NAS template
# Bot (heartbeat + coordination). Use a python that macOS lets reach the NAS from a background job.
PY=/usr/bin/python3; for c in /Library/Frameworks/Python.framework/Versions/Current/bin/python3 /opt/homebrew/bin/python3 /usr/local/bin/python3; do [ -x "$c" ] && PY="$c" && break; done
cat > ~/Library/LaunchAgents/com.researchhub.bot.plist <<EOP
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>Label</key><string>com.researchhub.bot</string>
<key>ProgramArguments</key><array><string>$PY</string><string>$HOME/ResearchHub/hub-bot.py</string></array>
<key>RunAtLoad</key><true/><key>StartInterval</key><integer>120</integer>
<key>StandardErrorPath</key><string>$HOME/ResearchHub/data/bot.log</string></dict></plist>
EOP
launchctl bootout gui/$(id -u)/com.researchhub.bot 2>/dev/null || true; launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.researchhub.bot.plist
sleep 6; "$PY" ~/ResearchHub/hub-bot.py run || true
echo "bot python: $PY (if the bot says 'cannot write to the NAS': System Settings > Privacy & Security > Full Disk Access > add that python, or /bin/bash)"
echo "host id: $(scutil --get LocalHostName | tr A-Z a-z)"; python3 ~/ResearchHub/hub-lock.py status | head -12
python3 ~/ResearchHub/hub-auto.py >/dev/null 2>&1 || true   # fetches the Portal login link from the NAS
echo "Installed. The bot now keeps code, task text and the Portal login link up to date by itself and self-tests daily."
