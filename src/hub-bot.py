#!/usr/bin/env python3
"""Research Hub bot: one runs on each Mac (launchd, every 5 minutes). No AI tokens used.
Each bot: (1) keeps its Mac healthy (remounts the NAS, reopens Chrome and Claude in working hours),
(2) writes a heartbeat to the NAS (_hub/bots/<host>.json), (3) reads the other Mac's heartbeat and runs,
(4) posts messages to the shared channel (_hub/bots/messages.jsonl) when something changes,
(5) feeds the dashboard (/bots) through the local cache data/bots.cache.json.
The alternate Mac's gate (hub-lock.py) takes over when this bot reports the primary down or unhealthy.
CLI: hub-bot.py [run] | status | say "text" """
import json, os, subprocess, sys, time, threading, datetime, importlib.util
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "data")
sp = importlib.util.spec_from_file_location("hub_lock", os.path.join(H, "hub-lock.py")); hl = importlib.util.module_from_spec(sp); sp.loader.exec_module(hl)
BOTS = os.path.join(hl.HUB, "bots"); MSG = os.path.join(BOTS, "messages.jsonl")
STATE = os.path.join(D, "bot-state.json"); CACHE = os.path.join(D, "bots.cache.json")
ME = hl.me(); NAS_VOL = "YOUR_NAS_SHARE"
import re as _re
def nothing_new(x):
    n = (x.get("note") or "").lower()
    if x.get("files", 0): return False
    bad = ("no file appeared", "no browser", "not connected", "unreadable", "login", "permission")
    return bool(_re.search(r"already (archived|held|have|in archive)|nothing new", n)) and not any(b in n for b in bad)

def sh(cmd, t=15):
    try: return subprocess.run(cmd, capture_output=True, text=True, timeout=t).stdout
    except Exception: return ""
def dl_dir():
    try: return json.load(open(os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Preferences")))["download"]["default_directory"]
    except Exception: return os.path.expanduser("~/Downloads")
def running(name):
    exe = {"Claude": "/Claude.app/Contents/MacOS/Claude", "Google Chrome": "/Google Chrome.app/Contents/MacOS/Google Chrome"}[name]
    return any(l.strip().endswith(exe) for l in sh(["ps", "-axo", "comm="]).splitlines())
def readable(path, t=8):
    ok = []
    th = threading.Thread(target=lambda: (lambda: (os.listdir(path), ok.append(1)))() if os.path.isdir(path) else None); th.daemon = True; th.start(); th.join(t)
    return bool(ok)
def in_window():
    n = datetime.datetime.now(); m = n.hour * 60 + n.minute
    return 7 * 60 + 40 <= m <= 20 * 60 + 15
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def say(to, kind, text):
    rec = {"ts": int(time.time()), "from": ME, "to": to, "kind": kind, "text": text}
    try:
        os.makedirs(BOTS, exist_ok=True)
        with open(MSG, "a") as f: f.write(json.dumps(rec) + "\n")
    except Exception: pass
    return rec
def my_runs(n=40):
    out = []
    try:
        for l in open(os.path.join(hl.HUB, "runs.jsonl")):
            try: out.append(json.loads(l))
            except Exception: pass
    except Exception: pass
    return out
def mount():
    for host in ("192.168.1.50", "100.64.0.10"):
        if subprocess.run(["ping", "-c1", "-W2", host], capture_output=True).returncode: continue
        sh(["osascript", "-e", 'mount volume "smb://NAS_USER@%s/%s"' % (host, NAS_VOL)], 40)
        for _ in range(6):
            if os.path.isdir(hl.HUB): return True
            time.sleep(4)
    return False
def issues(hb):
    out = []
    if not hb.get("nas"): out.append("NAS not reachable")
    if not hb.get("claude"): out.append("Claude app not running")
    if not hb.get("chrome"): out.append("Chrome not running")
    if not hb.get("downloads"): out.append("download folder unreadable (macOS permission?)")
    if hb.get("errors_in_row", 0) >= 2: out.append("last %d runs failed: %s" % (hb["errors_in_row"], hb.get("last_note", "")[:90]))
    return out
def run():
    st = load(STATE, {}); acts = []
    r = hl.role(); peer = r.get("alternate") if ME == r.get("primary") else r.get("primary")
    win = in_window()
    # 1. self-heal
    if not os.path.isdir(hl.HUB):
        if mount(): acts.append("remounted the NAS")
    if win:
        if not running("Claude"): sh(["open", "-g", "-a", "Claude"]); acts.append("reopened Claude")
        if not running("Google Chrome"): sh(["open", "-a", "Google Chrome"]); acts.append("reopened Chrome")
    nas = os.path.isdir(hl.HUB)
    # 2. heartbeat
    runs = my_runs() if nas else []
    try: cut = float(open(os.path.join(H, "data", "bot-resolved.txt")).read().strip())  # failures before this (ms) were fixed; ignore them
    except Exception: cut = 0
    mine = [x for x in runs if x.get("host") == ME and x.get("started", 0) >= cut]
    eir = 0
    for x in reversed(mine):
        if x.get("result") == "error" and not nothing_new(x): eir += 1
        elif x.get("result") == "error": continue   # "nothing new to download" is not a failure
        else: break
    hb = {"host": ME, "ts": int(time.time()), "nas": nas, "claude": running("Claude"), "chrome": running("Google Chrome"),
          "downloads": readable(dl_dir()), "errors_in_row": eir,
          "last_run": mine[-1] if mine else None, "last_note": (mine[-1].get("note") if mine else "") or "",
          "mode": r.get("mode"), "role": "primary" if ME == r.get("primary") else "alternate", "window": win}
    hb["issues"] = issues(hb)
    if nas:
        try: os.makedirs(BOTS, exist_ok=True); json.dump(hb, open(os.path.join(BOTS, ME + ".json"), "w"))
        except Exception: hb["issues"].append("cannot write to the NAS (give %s Full Disk Access)" % sys.executable); hb["nas_write"] = False
    # 3. messages about myself
    if acts and nas: say(peer, "action", "I " + " and ".join(acts) + ".")
    key = "; ".join(hb["issues"])
    if win and nas and key != st.get("my_issues", ""):  # only announce/record when the NAS is writable, so a blocked background run cannot flip the state silently
        if key: say(peer, "alert", "My problems: " + key)
        elif st.get("my_issues"): say(peer, "ok", "I'm healthy again.")
        st["my_issues"] = key
    # 4. watch the peer
    p = load(os.path.join(BOTS, (peer or "") + ".json"), None) if nas else None
    pstat = "unknown"
    if p:
        age = time.time() - p.get("ts", 0)
        if age > 1200 and hl.ran_recently(peer): pstat = "healthy"  # bot silent but its runs are landing
        elif age > 1200: pstat = "offline"
        elif p.get("issues"): pstat = "unhealthy"
        else: pstat = "healthy"
        if win and pstat != st.get("peer_stat") and st.get("peer_stat") is not None:
            txt = {"offline": "I can't hear you (no heartbeat for %d min). Taking over if a slot comes up." % (age // 60),
                   "unhealthy": "I see problems on your side: " + "; ".join(p.get("issues", [])),
                   "healthy": "You're back and healthy. I'll step back."}[pstat]
            say(peer, "alert" if pstat != "healthy" else "ok", txt)
        st["peer_stat"] = pstat
        lr = p.get("last_run")
        if lr and lr.get("started") != st.get("peer_last_run"):
            if st.get("peer_last_run") is not None:
                say(peer, "info", "Saw your run: %s, %s files%s" % (lr.get("result"), lr.get("files"), (" (" + lr["note"][:80] + ")") if lr.get("note") else ""))
            st["peer_last_run"] = lr.get("started")
    json.dump(st, open(STATE, "w"))
    # 5. dashboard cache
    msgs = []
    try: msgs = [json.loads(l) for l in open(MSG)][-60:]
    except Exception: pass
    json.dump({"me": ME, "peer": peer, "updated": int(time.time()), "lock": (hl.info() if nas else None), "mine": hb, "theirs": p, "peer_status": pstat, "messages": msgs}, open(CACHE, "w"))
    try:  # automation: login link sync, self-update, daily self-test
        spa = importlib.util.spec_from_file_location("hub_auto", os.path.join(H, "hub-auto.py")); A = importlib.util.module_from_spec(spa); spa.loader.exec_module(A); A.main()
    except Exception as e: sys.stderr.write("auto: %s\n" % e)
    return hb, pstat
if __name__ == "__main__":
    a = sys.argv[1:2]
    if a == ["say"]: say("all", "chat", sys.argv[2]); print("sent")
    elif a == ["inbox"]:  # recent messages from the other Mac's bot (last 12 h), for the task to read
        try: L = [json.loads(l) for l in open(MSG)]
        except Exception: L = []
        for m in [m for m in L if m.get("from") != ME and m.get("to") in (ME, "all", "", None) and time.time() - m.get("ts", 0) < 43200][-8:]:
            print("[%s] %s (%s): %s" % (datetime.datetime.fromtimestamp(m["ts"]).strftime("%H:%M"), m["from"], m.get("kind"), m.get("text", "")[:240]))
    elif a == ["status"]: print(json.dumps(load(CACHE, {}), indent=1)[:3000])
    else:
        hb, ps = run(); print("me:", "OK" if not hb["issues"] else hb["issues"], "| peer:", ps)
