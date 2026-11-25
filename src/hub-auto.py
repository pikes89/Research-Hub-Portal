#!/usr/bin/env python3
"""Research Hub automation, called by hub-bot.py every run (no AI tokens). Keeps both Macs identical and self-testing:
1) login link: synced both ways through the NAS (_hub/secrets), so a Mac can log itself back in to Portal
2) code self-update from _hub/install/researchhub-code.tgz (skipped if data/no-autoupdate exists)
3) task text self-update from _hub/install/SKILL.md (only if data/auto-skill.flag exists)
4) sync check twice a day (morning before the first download, evening after the last) that repairs what it can, compares both Macs and reports to the shared channel."""
import os, sys, json, time, shutil, tarfile, tempfile, datetime, importlib.util, glob, re, subprocess
H = os.path.dirname(os.path.abspath(__file__)); D = os.path.join(H, "data")
sp = importlib.util.spec_from_file_location("hub_lock", os.path.join(H, "hub-lock.py")); hl = importlib.util.module_from_spec(sp); sp.loader.exec_module(hl)
ME = hl.me(); T = os.path.expanduser("~/.claude/scheduled-tasks/portal-topic-downloads"); I = os.path.join(hl.HUB, "install")
STATE = os.path.join(D, "auto-state.json"); MSG = os.path.join(hl.HUB, "bots", "messages.jsonl")
def load(p, d):
    try: return json.load(open(p))
    except Exception: return d
def say(kind, text):
    try: open(MSG, "a").write(json.dumps({"ts": int(time.time()), "from": ME, "to": "all", "kind": kind, "text": text}) + "\n")
    except Exception: pass
def rd(p):
    try: return open(p).read()
    except Exception: return None
def sig(p):
    try: s = os.stat(p); return "%d:%d" % (s.st_mtime, s.st_size)
    except Exception: return ""
def login_link():
    loc = os.path.join(T, "login-link.txt"); nas = os.path.join(hl.HUB, "secrets", "login-link.txt"); a, b = rd(loc), rd(nas)
    if b and not a: os.makedirs(T, exist_ok=True); open(loc, "w").write(b); os.chmod(loc, 0o600); return "login link restored from the NAS"
    if a and not b: os.makedirs(os.path.dirname(nas), exist_ok=True); open(nas, "w").write(a); os.chmod(nas, 0o600); return "login link saved to the NAS"
    if a and b and a != b:
        if os.path.getmtime(loc) > os.path.getmtime(nas): open(nas, "w").write(a); return "newer login link pushed to the NAS"
        open(loc, "w").write(b); os.chmod(loc, 0o600); return "newer login link pulled from the NAS"
def self_update(st):
    if os.path.exists(os.path.join(D, "no-autoupdate")): return
    tgz = os.path.join(I, "researchhub-code.tgz"); s = sig(tgz)
    if not s: return
    if st.get("code_sig") is None: st["code_sig"] = s; return
    if s == st["code_sig"]: return
    tmp = tempfile.mkdtemp(); n = 0
    with tarfile.open(tgz) as t: t.extractall(tmp)
    for f in glob.glob(os.path.join(tmp, "ResearchHub", "*")):
        if os.path.isfile(f) and f.endswith((".py", ".sh", ".html", ".js", ".css")):
            shutil.copy2(f, os.path.join(H, os.path.basename(f))); n += 1
    shutil.rmtree(tmp, ignore_errors=True); st["code_sig"] = s
    return "updated %d code files from the NAS bundle" % n
def skill_update(st):
    if not os.path.exists(os.path.join(D, "auto-skill.flag")): return
    tpl = os.path.join(I, "SKILL.md"); s = sig(tpl)
    if not s or s == st.get("skill_sig"): return
    new = rd(tpl)
    if not new: return
    p = os.path.join(T, "SKILL.md"); shutil.copy2(p, p + ".bak-auto") if os.path.exists(p) else None
    open(p, "w").write(new.replace("/Users/YOURUSER", os.path.expanduser("~"))); st["skill_sig"] = s
    return "task text updated from the NAS template"
def snapshot():
    """Numbers that must be identical on both Macs (all read from the shared NAS state)."""
    n = lambda p: sum(1 for _ in open(p)) if os.path.exists(p) else -1
    sch = load(os.path.join(hl.HUB, "schedule.json"), {}) or {}
    sp3 = importlib.util.spec_from_file_location("ah", os.path.join(H, "already-have.py")); ah_ = importlib.util.module_from_spec(sp3)
    try: sp3.loader.exec_module(ah_)
    except Exception: pass
    try: arch = sum(len(f) for _, _, f in os.walk(ah_.ARCH))
    except Exception: arch = -1
    return {"runs": n(os.path.join(hl.HUB, "runs.jsonl")), "ledger": n(os.path.join(hl.HUB, "ledger.jsonl")), "schedule_saved": sch.get("saved", 0), "archive_files": arch}
def selftest(st):
    """Twice a day: SLOT am = first bot run after 07:00 (before the first download window at 07:40); SLOT pm = first run after 20:30
    (after the last download at 20:15). Each checks and repairs sync, then compares with the other Mac and reports to the shared channel."""
    now = datetime.datetime.now(); day = now.strftime("%Y%m%d"); hm = (now.hour, now.minute)
    slot = "pm" if hm >= (20, 30) else "am" if hm >= (7, 0) else None
    if not slot or st.get("check_" + slot) == day: return
    ok, fixed, bad = [], [], []
    # shared state files must be live links into the NAS
    for f in ("runs.jsonl", "schedule.json", "reminder.json", "ledger.jsonl"):
        p = os.path.join(D, f)
        if not os.path.exists(os.path.join(hl.HUB, f)): continue
        if os.path.realpath(p) != os.path.realpath(os.path.join(hl.HUB, f)) and not os.path.exists(p + ".keep"):
            try:
                if os.path.exists(p): os.rename(p, p + ".local-bak")
                os.symlink(os.path.join(hl.HUB, f), p); fixed.append("relinked " + f)
            except Exception as e: bad.append("cannot link %s: %s" % (f, e))
    q = os.path.join(T, "topic-queue.json")
    if os.path.exists(os.path.join(hl.HUB, "topic-queue.json")) and not os.path.exists(q): os.symlink(os.path.join(hl.HUB, "topic-queue.json"), q); fixed.append("relinked topic queue")
    # login link
    if not rd(os.path.join(T, "login-link.txt")): bad.append("no Portal login link on this Mac")
    peer = hl.role().get("alternate") if ME == hl.role().get("primary") else hl.role().get("primary")
    # both bots alive, last runs
    for h in (ME, peer):
        b = load(os.path.join(hl.HUB, "bots", (h or "") + ".json"), None)
        if not b: bad.append("no heartbeat from %s" % h); continue
        if time.time() - b.get("ts", 0) > 1800 and not hl.ran_recently(h, 150): bad.append("%s silent for %d min" % (h, (time.time() - b["ts"]) // 60))
        for i in b.get("issues", []): bad.append("%s: %s" % (h, i[:100]))
    # recent runs: real failures only
    try: runs = [json.loads(l) for l in open(os.path.join(hl.HUB, "runs.jsonl"))][-6:]
    except Exception: runs = []
    isreal = lambda r: r.get("result") == "error" and not re.search(r"already|nothing new", (r.get("note") or "").lower())
    real = [r for r in runs if isreal(r) and not any(x.get("host") == r.get("host") and x.get("started", 0) > r.get("started", 0) and not isreal(x) for x in runs)]  # already recovered
    if real and time.time() - real[-1].get("started", 0) / 1000 < 26 * 3600: bad.append("recent failed run on %s: %s" % (real[-1].get("host"), (real[-1].get("note") or "")[:90]))
    # sync local copies, then compare this Mac's view of the NAS with the other Mac's view
    try:
        subprocess.run([sys.executable, os.path.join(H, "hub-sync.py")], capture_output=True, timeout=120); fixed.append("resynced archive cache")
    except Exception: pass
    snap = snapshot()
    if snap["archive_files"] < 0: bad.append("NAS archive not readable")
    try:
        cache = load(os.path.join(D, "archive.cache.json"), {}).get("files", []); cn = len(cache)
        if snap["archive_files"] > 0 and abs(cn - snap["archive_files"]) > max(5, snap["archive_files"] // 20): bad.append("dashboard archive list has %d entries but the NAS has %d files" % (cn, snap["archive_files"]))
    except Exception: pass
    if slot == "pm":
        today = [r for r in (json.loads(l) for l in open(os.path.join(hl.HUB, "runs.jsonl")) if l.strip()) if datetime.datetime.fromtimestamp(r.get("started", 0) / 1000).strftime("%Y%m%d") == day] if snap["runs"] > 0 else []
        if not today: bad.append("no download run was recorded today")
        elif any(isreal(r) for r in today[-3:]): bad.append("last runs today had a real error")
        ok.append("%d runs today" % len(today))
    sc = os.path.join(hl.HUB, "synccheck.json"); rep = load(sc, {}); pe = rep.get(peer) or {}
    ps = pe.get("snap") or {}
    if ps and pe.get("day") == day and time.time() - pe.get("ts", 0) < 4 * 3600:
        diff = [k for k in ("runs", "ledger", "schedule_saved") if ps.get(k) != snap.get(k) and abs(ps.get(k, 0) - snap.get(k, 0)) > (0 if k == "schedule_saved" else 2)]
        if diff: bad.append("data differs from %s: %s" % (peer, ", ".join("%s %s vs %s" % (k, snap[k], ps.get(k)) for k in diff)))
        else: ok.append("matches " + str(peer))
    if not bad: ok.append("all checks passed")
    st["check_" + slot] = day; st["selftest_day"] = day
    entry = {"day": day, "slot": slot, "ts": int(time.time()), "ok": not bad, "problems": bad, "fixed": fixed, "snap": snap}
    rep[ME] = entry
    try: json.dump(rep, open(sc, "w"))
    except Exception: pass
    old = load(os.path.join(hl.HUB, "selftest.json"), {}); old[ME] = {k: entry[k] for k in ("day", "ts", "ok", "problems", "fixed")}; old[ME]["slot"] = slot
    try: json.dump(old, open(os.path.join(hl.HUB, "selftest.json"), "w"))
    except Exception: pass
    say("ok" if not bad else "alert", "%s sync check %s: %s%s" % ("Morning (before first download)" if slot == "am" else "Evening (after last download)", day, "OK" if not bad else "; ".join(bad), (" (fixed: " + ", ".join(fixed) + ")") if fixed else ""))
    return "%s sync check %s" % (slot, "ok" if not bad else "problems")
def clean_downloads(st):
    """Hourly: move portal files that landed in ~/Downloads (or Chrome's download folder) onto the NAS archive, verify, then to the Trash.
    Skips files younger than 20 min and anything while a run holds the lock. Never touches other files."""
    if time.time() - st.get("dl_clean_ts", 0) < 3600: return
    st["dl_clean_ts"] = time.time()
    try:
        if hl.info(): return          # a run is in progress
    except Exception: pass
    import hashlib
    sp2 = importlib.util.spec_from_file_location("ah", os.path.join(H, "already-have.py")); ah = importlib.util.module_from_spec(sp2); sp2.loader.exec_module(ah)
    arch = ah.ARCH
    if not os.path.isdir(arch): return
    md = lambda p: hashlib.md5(open(p, "rb").read()).hexdigest()
    inbox = os.path.realpath(os.path.join(H, "inbox"))
    dirs = {os.path.realpath(os.path.expanduser("~/Downloads"))}
    try: dirs.add(os.path.realpath(json.load(open(os.path.expanduser("~/Library/Application Support/Google/Chrome/Default/Preferences")))["download"]["default_directory"]))
    except Exception: pass
    dirs.discard(inbox)
    idx = {}
    for d in os.listdir(arch):
        p = os.path.join(arch, d)
        if os.path.isdir(p):
            for f in os.listdir(p): idx.setdefault(f, []).append(os.path.join(p, f))
    moved = copied = 0; trash = os.path.expanduser("~/.Trash")
    for D in dirs:
        try: names = sorted(os.listdir(D))
        except Exception: continue
        for f in names:
            src = os.path.join(D, f)
            if f.startswith(".") or not os.path.isfile(src) or not f.lower().endswith((".pdf", ".xlsx")) or time.time() - os.path.getmtime(src) < 1200: continue
            r = ah.check(f); isportal = f.lower().endswith(".pdf") and "-portal" in f.lower() or r.startswith("HAVE")
            if not isportal: continue
            h = md(src); exact = [p for p in idx.get(f, []) if md(p) == h]
            if exact: dst = exact[0]
            elif re.search(r" \(\d+\)\.[a-z]+$", f):
                dd = os.path.join(os.path.dirname(arch), "_duplicates-from-downloads"); os.makedirs(dd, exist_ok=True); dst = os.path.join(dd, f)
                if not os.path.exists(dst): shutil.copy2(src, dst); copied += 1
            else:
                m = re.match(r"HAVE (\w[\w-]*)/", r); tgt = os.path.join(arch, m.group(1)) if m and os.path.isdir(os.path.join(arch, m.group(1))) else os.path.join(arch, "Unsorted")
                os.makedirs(tgt, exist_ok=True); dst = os.path.join(tgt, f)
                if os.path.exists(dst) and md(dst) != h: dst = os.path.join(tgt, "dl-" + f)
                if not os.path.exists(dst): shutil.copy2(src, dst); copied += 1
            if os.path.exists(dst) and md(dst) == h:
                t = os.path.join(trash, f)
                if os.path.exists(t): t = os.path.join(trash, "%d-%s" % (time.time(), f))
                shutil.move(src, t); moved += 1
    if moved: return "cleaned %d portal files from Downloads (%d copied to the NAS archive, rest already there)" % (moved, copied)

def main():
    if not os.path.isdir(hl.HUB): return []
    st = load(STATE, {}); acts = []
    for fn in (login_link, lambda: self_update(st), lambda: skill_update(st), lambda: selftest(st), lambda: clean_downloads(st)):
        try:
            r = fn()
            if r: acts.append(r)
        except Exception as e: acts.append("auto error: %s" % e)
    json.dump(st, open(STATE, "w"))
    if acts: say("action", "; ".join(acts))
    return acts
if __name__ == "__main__": print(main())
