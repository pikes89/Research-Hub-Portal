#!/bin/bash
# Hourly Google Drive mirror (copy only, never deletes). Runs on ONE Mac regardless of who downloads.
A="/Volumes/YOUR_NAS_SHARE/research-archive"
[ -d "$A/Portal" ] || { echo "$(date) NAS not mounted" >> $HOME/ResearchHub/data/mirror.log; exit 0; }
mkdir "$HOME/ResearchHub/data/.mirror.lock" 2>/dev/null || exit 0
trap 'rmdir "$HOME/ResearchHub/data/.mirror.lock"' EXIT
for d in Portal OpenData; do
  [ -d "$A/$d" ] && /opt/homebrew/bin/rclone copy "$A/$d" "gdrive:research-archive/$d" --exclude ".*" >> $HOME/ResearchHub/data/mirror.log 2>&1
done
echo "$(date) mirror done" >> $HOME/ResearchHub/data/mirror.log
