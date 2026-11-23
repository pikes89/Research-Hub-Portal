#!/bin/zsh
# Archive now lives on the NAS (no external drive). This only feeds NEW PDFs to Paperless. Never deletes anything.
SRC="/Volumes/YOUR_NAS_SHARE/research-archive/Portal/"
[ -d "$SRC" ] || { echo "NAS share not mounted (Finder: Cmd+K, smb://192.168.1.50, YOUR_NAS_SHARE)"; exit 2; }
CONSUME="/Volumes/YOUR_NAS_SHARE/docker/research-hub/paperless/consume"
MARK="$(dirname "$0")/.last-consume-run"
if [ -d "$CONSUME" ]; then
  if [ -f "$MARK" ]; then NEW=$(find "$SRC" -name '*.pdf' -not -name '.*' -newer "$MARK"); else NEW=""; fi
  echo "$NEW" | while IFS= read -r f; do
    [ -n "$f" ] || continue
    rel="${f#$SRC}"; mkdir -p "$CONSUME/$(dirname "$rel")" && cp "$f" "$CONSUME/$rel" && echo "to Paperless: $rel"
  done
  touch "$MARK"
fi
echo "sync done"
