#!/usr/bin/env python3
"""Live run status + run log for the dashboard.
  set-status.py start --total N [--topic T]
  set-status.py progress --done K [--total N] --current "text" [--topic T]
  set-status.py idle [--result success|partial|error] [--note "text"]
Writes status.js (here and on the NAS copy) and appends a record to data/runs.jsonl when a run ends.
"""
import argparse, json, os, time, importlib.util
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
NAS = "/Volumes/YOUR_NAS_SHARE/research-archive"
_sp = importlib.util.spec_from_file_location("hub_lock", os.path.join(HERE, "hub-lock.py")); hl = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(hl)
ap = argparse.ArgumentParser()
ap.add_argument("state", choices=["start", "progress", "idle"])
ap.add_argument("--total", type=int); ap.add_argument("--done", type=int)
ap.add_argument("--current", default=""); ap.add_argument("--topic", default=""); ap.add_argument("--note", default="")
ap.add_argument("--result", default="success", choices=["success", "partial", "error"])
a = ap.parse_args()
os.makedirs(DATA, exist_ok=True)
p = os.path.join(HERE, "status.js")
old = {}
try:
    old = json.loads(open(p).read().split("=", 1)[1].rstrip().rstrip(";"))
except Exception:
    pass
now = int(time.time() * 1000)
topics = list(old.get("topics", [])) if old.get("state") == "running" else []
if a.topic and a.topic not in topics:
    topics.append(a.topic)
try:
    if a.state in ("start", "progress"): hl.renew()
except Exception:
    pass
if a.state == "start":
    s = {"state": "running", "started": now, "total": a.total or 0, "done": 0, "current": "Starting…", "topic": a.topic, "topics": topics}
elif a.state == "progress":
    s = {"state": "running", "started": old.get("started", now), "total": a.total or old.get("total", 0),
         "done": a.done or 0, "current": a.current, "topic": a.topic or old.get("topic", ""), "topics": topics}
else:
    s = {"state": "idle", "finished": now, "last": {"done": old.get("done", 0), "total": old.get("total", 0)}, "note": a.note}
    if old.get("state") == "running" or a.result != "success":
        # also log runs that stopped early (before any download started), e.g. NAS not mounted
        run = old.get("state") == "running"
        rec = {"started": old.get("started", now) if run else now, "finished": now, "result": a.result,
               "files": old.get("done", 0) if run else 0,
               "planned": old.get("total", 0) if run else 0, "topics": old.get("topics", []) if run else [], "note": a.note, "host": hl.me()}
        with open(os.path.join(DATA, "runs.jsonl"), "a") as f:
            f.write(json.dumps(rec) + "\n")
if a.state == "idle":
    try: hl.release()
    except Exception: pass
    try:
        import importlib.util as _u
        _s = _u.spec_from_file_location("hub_sync", os.path.join(os.path.dirname(os.path.abspath(__file__)), "hub-sync.py")); _m = _u.module_from_spec(_s); _s.loader.exec_module(_m); _m.sync()
    except Exception: pass
s["updated"] = now
txt = "window.RH_STATUS=" + json.dumps(s) + ";\n"
for d in (HERE, NAS):
    if os.path.isdir(d):
        open(os.path.join(d, "status.js"), "w").write(txt)
print(txt.strip())
