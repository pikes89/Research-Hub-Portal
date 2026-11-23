#!/usr/bin/env python3
"""Prints RUN or SKIP for the hourly check. Schedule lives in data/schedule.json (set from the dashboard).
With two Macs, the shared lock/role in hub-lock.py decides which Mac runs (only one at a time)."""
import json, os, datetime, sys, time
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "data"); sys.path.insert(0, H)
import importlib.util
sp = importlib.util.spec_from_file_location("hub_lock", os.path.join(H, "hub-lock.py")); hl = importlib.util.module_from_spec(sp); sp.loader.exec_module(hl)
flag = os.path.join(D, "run-now"); force = False
try:
    sp2 = importlib.util.spec_from_file_location("hub_sync", os.path.join(H, "hub-sync.py")); hs = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(hs); hs.sync()
except Exception:
    pass
try:  # refresh this Mac's bot heartbeat from here (this context can reach the NAS even when launchd cannot)
    import subprocess; py = "/opt/homebrew/bin/python3" if os.path.exists("/opt/homebrew/bin/python3") else sys.executable
    subprocess.run([py, os.path.join(H, "hub-bot.py")], timeout=60, capture_output=True)
except Exception:
    pass
try:
    s = json.load(open(os.path.join(D, "schedule.json")))
except Exception:
    s = {"interval_hours": 4, "enabled": True}
iv = min(4, max(1, int(s.get("interval_hours", 4)))); start, end = 8, 20
res = None
if os.path.exists(flag):
    os.remove(flag); res = "RUN (run-now requested)"; force = True
else:
    h = datetime.datetime.now().hour
    inwin = s.get("enabled", True) and start <= h <= end - 1
    ok = inwin and (h - start) % iv == 0
    if inwin and not ok:
        try:
            last = json.loads(open(os.path.join(D, "runs.jsonl")).read().strip().splitlines()[-1])
            if last.get("result") == "error" and time.time() * 1000 - last.get("finished", 0) < 3 * 3600 * 1000:
                res = "RUN (retry after failed run)"
        except Exception:
            pass
    if res is None:
        res = "RUN" if ok else "SKIP (not a scheduled slot)"
if res.startswith("RUN"):
    ok, why = hl.decide(iv, force)
    if not ok: res = why
    else: res = res + " [" + why + "]"
print(res)
