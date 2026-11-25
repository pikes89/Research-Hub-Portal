#!/bin/bash
# Deploy changed code files from this Mac to the NAS bundle; the other Mac self-updates within ~2 min.
# Usage: deploy-bundle.sh file1 [file2 ...]   (run from ~/ResearchHub)
set -e; cd ~/ResearchHub
N="/Volumes/YOUR_NAS_SHARE/research-archive/_hub/install"
cp "$N/researchhub-code.tgz" "$N/backup/researchhub-code.$(date +%Y%m%d-%H%M%S).tgz"
T=$(mktemp -d); tar -xzf "$N/researchhub-code.tgz" -C "$T"; cp "$@" "$T/ResearchHub/"
(cd "$T" && tar -czf "$N/researchhub-code.tgz.new" ResearchHub) && mv "$N/researchhub-code.tgz.new" "$N/researchhub-code.tgz"
md5 -q "$N/researchhub-code.tgz" > "$N/VERSION"; rm -rf "$T"; echo "deployed $* (VERSION $(cat "$N/VERSION"))"
