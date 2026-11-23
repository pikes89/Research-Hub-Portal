#!/usr/bin/env python3
"""Syncs the dashboard's local copies with the shared NAS state (_hub).
Why: the dashboard server runs as a background launchd job, which macOS blocks from reading/writing the NAS.
So the server only touches LOCAL files (data/schedule.local.json, data/runs.cache.jsonl); this script runs
from contexts that CAN reach the NAS (the scheduled task, a Terminal) and keeps both sides equal.
Schedule: the copy with the newest 'saved' time wins, so a change made on either Mac reaches both."""
import json, os, shutil
D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
LOCAL, NAS = os.path.join(D, "schedule.local.json"), os.path.join(D, "schedule.json")  # schedule.json is a link to the NAS
def rd(p):
    try: return json.load(open(p))
    except Exception: return None
def wr(p, s):
    tmp = p + ".tmp"; json.dump(s, open(tmp, "w")); os.replace(tmp, p)
def sync():
    l, n = rd(LOCAL), rd(NAS)
    if l is None and n is None: return "no schedule found (NAS not mounted?)"
    if n is None: wr(NAS if not os.path.islink(NAS) else os.path.realpath(NAS), l); return "pushed local schedule to NAS"
    if l is None or n.get("saved", 0) > l.get("saved", 0):
        wr(LOCAL, n); msg = "NAS schedule copied to local"
    elif l.get("saved", 0) > n.get("saved", 0):
        wr(os.path.realpath(NAS), l); msg = "local schedule pushed to NAS"
    else: msg = "schedule in sync"
    try: shutil.copyfile(os.path.join(D, "runs.jsonl"), os.path.join(D, "runs.cache.jsonl"))
    except Exception: pass
    return msg
ARCH = "/Volumes/YOUR_NAS_SHARE/research-archive/Portal"
def archive_cache(max_age=300):
    """File list (topic, stem, mtime) of the NAS archive -> data/archive.cache.json, so the dashboard server (which macOS blocks from the NAS) can count downloads."""
    import time
    out = os.path.join(D, "archive.cache.json")
    try:
        if time.time() - os.path.getmtime(out) < max_age: return "archive cache fresh"
    except OSError: pass
    if not os.path.isdir(ARCH): return "archive not reachable"
    rows = []
    for root, _, fs in os.walk(ARCH):
        for f in fs:
            if f.startswith(".") or not f.lower().endswith((".pdf", ".xlsx")): continue
            fp = os.path.join(root, f)
            try: rows.append([os.path.relpath(root, ARCH).split(os.sep)[0], os.path.splitext(fp)[0], os.path.getmtime(fp)])
            except OSError: pass
    if not rows: return "archive empty/unreadable: cache kept"
    wr(out, {"built": time.time(), "files": rows}); return "archive cache: %d files" % len(rows)
_sync = sync
def sync():
    m = _sync()
    try: m += "; " + archive_cache()
    except Exception as e: m += "; archive cache failed: %s" % e
    return m
if __name__ == "__main__": print(sync())
