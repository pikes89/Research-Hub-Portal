#!/usr/bin/env python3
"""Research Hub helper: serves the dashboard on http://127.0.0.1:8765 and a tiny local API
(schedule, run log, download summary). Localhost only; no internet access; no credentials."""
import json, os, datetime, time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
ARCH = "/Volumes/YOUR_NAS_SHARE/research-archive/Portal"
PORT = 8787; OK_HOSTS = {"127.0.0.1:%d" % PORT, "localhost:%d" % PORT}
TS_HOST = "your-mac.your-tailnet.ts.net"; TS_OWNER = "you@example.com"
STATIC = {"/": "dashboard.html", "/dashboard.html": "dashboard.html", "/status.js": "status.js", "/bots": "bots.html"}
os.makedirs(DATA, exist_ok=True)

def load_schedule():
    try:
        s = json.load(open(os.path.join(DATA, "schedule.local.json")))
    except Exception:
        s = {}
    return {"interval_hours": min(4, max(1, int(s.get("interval_hours", 4)))), "enabled": bool(s.get("enabled", True))}

def slots(iv): return [h for h in range(8, 20) if (h - 8) % iv == 0]

def runs(n=60):
    out = []
    try:
        for l in open(os.path.join(DATA, "runs.cache.jsonl")):
            try: out.append(json.loads(l))
            except Exception: pass
    except Exception: pass
    return out[-n:][::-1], out

def summary(all_runs):
    PH = datetime.timezone(datetime.timedelta(hours=8))  # dates follow Philippine time
    now = datetime.datetime.now(PH).replace(tzinfo=None); today = now.date()
    wk = today - datetime.timedelta(days=today.weekday()); mo = today.replace(day=1)
    B = {"today": {"files": 0, "stats": set(), "topics": {}}, "week": {"files": 0, "stats": set(), "topics": {}}, "month": {"files": 0, "stats": set(), "topics": {}}}
    src = "archive"
    try: rows = json.load(open(os.path.join(DATA, "archive.cache.json")))["files"]
    except Exception: rows = None
    if rows:
        for topic, stem, mt in rows:
            d = datetime.datetime.fromtimestamp(mt, PH).date()
            for k, lo in (("today", today), ("week", wk), ("month", mo)):
                if d >= lo:
                    B[k]["files"] += 1; B[k]["stats"].add(stem); B[k]["topics"][topic] = B[k]["topics"].get(topic, 0) + 1
    else:
        src = "log"
        for r in all_runs:
            d = datetime.datetime.fromtimestamp(r["finished"] / 1000, PH).date()
            for k, lo in (("today", today), ("week", wk), ("month", mo)):
                if d >= lo:
                    B[k]["files"] += r.get("files", 0)
                    for t in r.get("topics", []): B[k]["topics"][t] = B[k]["topics"].get(t, 0) + 0
    res = {}
    for k, lo in (("today", today), ("week", wk), ("month", mo)):
        rr = [r for r in all_runs if datetime.datetime.fromtimestamp(r["finished"] / 1000, PH).date() >= lo]
        res[k] = {"files": B[k]["files"], "statistics": len(B[k]["stats"]) if src == "archive" else B[k]["files"] // 2,
                  "topics": B[k]["topics"], "runs": len(rr), "ok": sum(1 for r in rr if r["result"] == "success"),
                  "errors": sum(1 for r in rr if r["result"] == "error"), "partial": sum(1 for r in rr if r["result"] == "partial")}
    res["source"] = src
    return res

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def _ok_origin(self):
        h = self.headers.get("Host", "")
        if h in OK_HOSTS:
            o = self.headers.get("Origin")
            return o is None or o.replace("http://", "") in OK_HOSTS
        if h == TS_HOST:  # via `tailscale serve` (tailnet only): require the owner's Tailscale identity
            if self.headers.get("Tailscale-User-Login", "") != TS_OWNER: return False
            o = self.headers.get("Origin")
            return o is None or o == "https://" + TS_HOST
        return False
    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code); self.send_header("Content-Type", ctype); self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store"); self.end_headers(); self.wfile.write(b)
    def do_GET(self):
        if not self._ok_origin(): return self._send(403, {"error": "forbidden"})
        path = self.path.split("?")[0]
        if path == "/api/state":
            recent, allr = runs(); s = load_schedule()
            return self._send(200, {"schedule": s, "slots": slots(s["interval_hours"]), "runs": recent, "summary": summary(allr),
                                    "runNowPending": os.path.exists(os.path.join(DATA, "run-now"))})
        if path == "/api/bots":
            try: return self._send(200, open(os.path.join(DATA, "bots.cache.json"), "rb").read())
            except Exception: return self._send(200, {"messages": [], "note": "bot has not run yet"})
        if path in STATIC:
            fp = os.path.join(HERE, STATIC[path])
            if os.path.exists(fp):
                ct = "text/html; charset=utf-8" if fp.endswith(".html") else "application/javascript"
                return self._send(200, open(fp, "rb").read(), ct)
        self._send(404, {"error": "not found"})
    def do_POST(self):
        if not self._ok_origin() or "application/json" not in (self.headers.get("Content-Type") or ""):
            return self._send(403, {"error": "forbidden"})
        try:
            n = int(self.headers.get("Content-Length", 0)); body = json.loads(self.rfile.read(min(n, 4096)) or b"{}")
        except Exception:
            return self._send(400, {"error": "bad request"})
        if self.path == "/api/schedule":
            iv = body.get("interval_hours")
            if iv not in (1, 2, 3, 4) or not isinstance(body.get("enabled", True), bool):
                return self._send(400, {"error": "interval_hours must be 1, 2, 3 or 4"})
            json.dump({"interval_hours": iv, "enabled": body.get("enabled", True), "saved": int(time.time() * 1000)}, open(os.path.join(DATA, "schedule.local.json"), "w"))
            return self._send(200, {"schedule": load_schedule(), "slots": slots(iv)})
        if self.path == "/api/runnow":
            open(os.path.join(DATA, "run-now"), "w").close(); return self._send(200, {"runNowPending": True})
        self._send(404, {"error": "not found"})

if __name__ == "__main__":
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
