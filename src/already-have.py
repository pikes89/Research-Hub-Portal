#!/usr/bin/env python3
"""Duplicate check for Portal downloads (archive files carry no IDs, so match by ID ledger or title words).
  already-have.py check "<statistic title>" [statistic_id]   -> prints HAVE <folder>/<file> or NEW
  already-have.py add <Folder> "<statistic title>" [statistic_id]  -> records it in data/ledger.jsonl
"""
import json, os, re, sys, time
H = os.path.dirname(os.path.abspath(__file__)); LED = os.path.join(H, "data", "ledger.jsonl")
ARCH = "/Volumes/YOUR_NAS_SHARE/research-archive/Portal"
STOP = set("the of in and by for to a an on at from as is are with worldwide global portal pdf xlsx".split())
def toks(s):
    s = re.sub(r"\.(pdf|xlsx)$", "", s.lower()); s = re.sub(r"statistic_id\d+_?", "", s)
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and not re.fullmatch(r"20\d\d", w)} | {w for w in re.findall(r"20\d\d", s)}
def overlap(a, b):
    return len(a & b) / max(1, min(len(a), len(b)))
def check(title, sid=None):
    if sid and os.path.exists(LED):
        for l in open(LED):
            r = json.loads(l)
            if r.get("id") and str(r["id"]) == str(sid): return "HAVE ledger id %s (%s)" % (sid, r["folder"])
    t = toks(title)
    for d in sorted(os.listdir(ARCH)):
        p = os.path.join(ARCH, d)
        if not os.path.isdir(p): continue
        for f in os.listdir(p):
            if f.startswith(".") or not f.lower().endswith((".pdf", ".xlsx")): continue
            if sid and ("id%s" % sid) in f: return "HAVE %s/%s" % (d, f)
            if len(t) >= 3 and overlap(t, toks(f)) >= 0.8: return "HAVE %s/%s" % (d, f)
    if os.path.exists(LED):
        for l in open(LED):
            r = json.loads(l)
            if overlap(t, toks(r["title"])) >= 0.9: return "HAVE ledger title (%s)" % r["folder"]
    return "NEW"
if __name__ == "__main__":
    a = sys.argv[1:]
    if not os.path.isdir(ARCH): print("ARCHIVE NOT MOUNTED"); sys.exit(1)
    if a[:1] == ["check"]: print(check(a[1], a[2] if len(a) > 2 else None))
    elif a[:1] == ["add"]:
        os.makedirs(os.path.dirname(LED), exist_ok=True)
        open(LED, "a").write(json.dumps({"t": int(time.time()), "folder": a[1], "title": a[2], "id": a[3] if len(a) > 3 else None}) + "\n"); print("added")
    else: print(__doc__)
