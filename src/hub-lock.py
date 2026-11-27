#!/usr/bin/env python3
"""Shared lock + role for two downloader Macs. State lives on the NAS (_hub/), so only one Mac downloads at a time.
  hub-lock.py status | acquire | renew | release | mode auto|primary-only|alternate-only
Library use: decide(iv_hours, force) -> (ok, reason)."""
import json, os, subprocess, sys, time
HUB = "/Volumes/YOUR_NAS_SHARE/research-archive/_hub"
LOCK = os.path.join(HUB, "lock.d"); INFO = os.path.join(LOCK, "info.json"); ROLE = os.path.join(HUB, "role.json")
def ph_now():
    """Philippine time (UTC+8, no daylight saving). The schedule always follows it, wherever the Mac is."""
    import datetime
    return datetime.datetime.fromtimestamp(time.time(), datetime.timezone(datetime.timedelta(hours=8))).replace(tzinfo=None)
def ph_date(ts):
    import datetime
    return datetime.datetime.fromtimestamp(ts, datetime.timezone(datetime.timedelta(hours=8))).date()
def me():
    try: return subprocess.check_output(["scutil", "--get", "LocalHostName"], text=True).strip().lower()
    except Exception: return os.uname().nodename.split(".")[0].lower()
def role():
    try: return json.load(open(ROLE))
    except Exception: return {"mode": "auto", "primary": "", "alternate": "", "lock_minutes": 25}
def info():
    try: return json.load(open(INFO))
    except Exception: return None
def expired(i, r): return (not i) or time.time() > i.get("renewed", 0) + int(r.get("lock_minutes", 25)) * 60
def _write(host):
    json.dump({"host": host, "renewed": time.time(), "since": (info() or {}).get("since", time.time()) if (info() or {}).get("host") == host else time.time()}, open(INFO, "w"))
def acquire():
    if not os.path.isdir(HUB): return False, "NAS hub folder not reachable"
    h, r = me(), role()
    try:
        os.mkdir(LOCK); _write(h); return True, "lock acquired"
    except FileExistsError:
        i = info()
        if i and i.get("host") == h: _write(h); return True, "lock renewed"
        if expired(i, r):
            try: os.rename(LOCK, LOCK + ".stale.%d" % time.time()); os.mkdir(LOCK); _write(h); return True, "stale lock taken over from %s" % (i or {}).get("host")
            except OSError: return False, "lost the race for the lock"
        return False, "lock held by %s" % i.get("host")
def renew():
    i = info()
    if i and i.get("host") == me(): _write(me()); return True
    return acquire()[0]
def release():
    i = info()
    if i and i.get("host") == me():
        try: os.remove(INFO); os.rmdir(LOCK)
        except OSError: pass
def last_started():
    try:
        L = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "runs.jsonl")).read().strip().splitlines()
        return json.loads(L[-1]).get("started", 0) / 1000.0
    except Exception: return 0
def ran_recently(host, mins=100):
    """True if `host` finished a run in the last `mins` minutes (runs log, NAS copy then local cache). Proves it is alive even if its bot is silent."""
    base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    for f in ("runs.jsonl", "runs.cache.jsonl"):
        try:
            for l in reversed(open(os.path.join(base, f)).read().strip().splitlines()[-30:]):
                x = json.loads(l)
                if x.get("host") == host: 
                    if time.time() - x.get("finished", 0) / 1000.0 <= mins * 60: return True
                    break
        except Exception: pass
    return False
def peer_down():
    """Reason string if the primary's bot reports it offline or unhealthy during working hours, else ''. Used so the alternate takes over fast."""
    r = role(); pr = r.get("primary")
    try: b = json.load(open(os.path.join(HUB, "bots", pr + ".json")))
    except Exception: return ""
    n = ph_now()
    if not (7 * 60 + 40 <= n.hour * 60 + n.minute <= 20 * 60 + 15): return ""
    if ran_recently(pr): return ""
    if time.time() - b.get("ts", 0) > 1200: return "primary bot silent for %d min" % ((time.time() - b.get("ts", 0)) // 60)
    if b.get("issues"): return "primary unhealthy: " + "; ".join(b["issues"])[:120]
    return ""
def decide(iv, force=False):
    h, r = me(), role(); mode = r.get("mode", "auto")
    if not os.path.isdir(HUB): return False, "SKIP (NAS hub folder not reachable, shared state unavailable)"
    if mode == "primary-only" and h != r.get("primary"): return False, "SKIP (mode primary-only; this Mac is not the primary)"
    if mode == "alternate-only" and h != r.get("alternate"): return False, "SKIP (mode alternate-only; this Mac is not the alternate)"
    i = info()
    if i and i.get("host") != h and not expired(i, r): return False, "SKIP (%s is running)" % i["host"]
    if mode == "auto" and h == r.get("alternate") and not force:
        age = time.time() - last_started()
        down = peer_down()
        if age <= iv * 3600 + 25 * 60 and not down: return False, "SKIP (alternate: primary %s ran %d min ago)" % (r.get("primary"), age // 60)
    ok, why = acquire()
    return ok, ("RUN (%s)" % why) if ok else "SKIP (%s)" % why
if __name__ == "__main__":
    a = sys.argv[1:2]
    if a == ["status"]: print(json.dumps({"me": me(), "role": role(), "lock": info()}, indent=1))
    elif a == ["acquire"]: print(acquire())
    elif a == ["renew"]: print(renew())
    elif a == ["release"]: release(); print("released")
    elif a == ["mode"]:
        r = role(); r["mode"] = sys.argv[2]; json.dump(r, open(ROLE, "w")); print("mode =", sys.argv[2])
    else: print(__doc__)
