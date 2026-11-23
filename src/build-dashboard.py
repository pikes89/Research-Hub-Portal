#!/usr/bin/env python3
"""Build dashboard.html from the real archive (no credentials used).

Reads : external drive archive, NAS share (if mounted), Google Drive via rclone, Paperless storage on the NAS share.
Writes: dashboard.html next to this script (and a copy on the NAS share if mounted).
Run   : python3 build-dashboard.py
"""
import json, os, re, shutil, subprocess, sys, time, urllib.request
from datetime import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "dashboard-mock.html")
OUT = os.path.join(HERE, "dashboard.html")
SRC = "/Volumes/YOUR_NAS_SHARE/research-archive/Portal"
NAS_SHARE = "/Volumes/YOUR_NAS_SHARE"
NAS_ARCHIVE = NAS_SHARE + "/research-archive/Portal"
PAPERLESS = "http://192.168.1.50:8010"
SMB_BASE = "smb://192.168.1.50/YOUR_NAS_SHARE/research-archive/Portal/"
try:  # away from the home network, use the NAS's Tailscale address (pmaaai-server)
    import socket
    socket.create_connection(("192.168.1.50", 8010), timeout=2).close()
except Exception:
    PAPERLESS = "http://100.64.0.10:8010"
    SMB_BASE = "smb://100.64.0.10/YOUR_NAS_SHARE/research-archive/Portal/"
STOP = set("the of in and by from to for worldwide with a an as on until share total".split())


def words(s):
    s = re.sub(r"\.(pdf|xlsx)$", "", s.lower())
    s = s.replace("2026-portal", "").replace("artificial-intelligence", "ai").replace("artificial_intelligence", "ai")
    s = s.replace("artificial intelligence", "ai").replace("'", "")
    return {w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and len(w) > 1}


tpl = open(TEMPLATE, encoding="utf-8").read()
m = re.search(r"const D=\[(.*?)\];\nconst TAGS", tpl, re.S)
rows = json.loads("[" + m.group(1) + "]")  # [title, tags, year, urlid]
TITLE_FIX = {"941137": "AI venture capital investment by region", "1659739": "Faculty viewing AI's impact on education"}  # real title of the downloaded statistic
for r in rows:
    r[0] = TITLE_FIX.get(r[3].split("/")[0], r[0])

files = []  # relative path under Portal
mtimes = {}
if os.path.isdir(SRC):
    for root, _, fs in os.walk(SRC):
        for f in fs:
            if f.lower().endswith((".pdf", ".xlsx")) and not f.startswith("."):
                rel = os.path.relpath(os.path.join(root, f), SRC)
                files.append(rel)
                try: mtimes[rel] = int(os.path.getmtime(os.path.join(root, f)))
                except OSError: mtimes[rel] = 0
try:
    CAP = int(json.load(open(os.path.expanduser("~/.claude/scheduled-tasks/portal-topic-downloads/topic-queue.json"))).get("cap_per_topic", 100))
except Exception:
    CAP = 100


def topic_of(item):
    for x in (item["pdf"], item["xlsx"]):
        if x and os.sep in x:
            return x.split(os.sep)[0]
    return "Other"


def added_of(item):
    return max([mtimes.get(x, 0) for x in (item["pdf"], item["xlsx"]) if x] or [0])

cand = []
for ri, r in enumerate(rows):
    rw = words(r[0])
    for f in files:
        fw = words(os.path.basename(f))
        ext = f.lower().rsplit(".", 1)[-1]
        score = len(rw & fw) / max(1, len(rw)) - 0.01 * len(fw - rw) / max(1, len(fw))
        cand.append((score, ri, ext, f))
cand.sort(reverse=True)
best, used_files, taken = {}, set(), set()
for score, ri, ext, f in cand:
    if score < 0.6 or (ri, ext) in taken or f in used_files:
        continue
    best[(ri, ext)] = (score, f)
    taken.add((ri, ext))
    used_files.add(f)

nas_files = set()
if os.path.isdir(NAS_ARCHIVE):
    for root, _, fs in os.walk(NAS_ARCHIVE):
        nas_files |= {os.path.relpath(os.path.join(root, f), NAS_ARCHIVE) for f in fs}

cloud = set()
try:
    out = subprocess.run(["rclone", "lsf", "-R", "--files-only", "gdrive:research-archive/Portal"],
                         capture_output=True, text=True, timeout=60).stdout
    cloud = {l.strip() for l in out.splitlines() if l.strip()}
except Exception:
    pass

data = []
for ri, r in enumerate(rows):
    item = {"t": r[0], "tags": r[1], "y": r[2], "u": r[3], "pdf": "", "xlsx": "", "nas": False, "cloud": False}
    for ext in ("pdf", "xlsx"):
        item[ext] = best.get((ri, ext), (0, ""))[1]
    got = [x for x in (item["pdf"], item["xlsx"]) if x]
    item["nas"] = bool(got) and all(x in nas_files for x in got)
    item["cloud"] = bool(got) and all(x in cloud for x in got)
    item["got"] = len(got)
    item["topic"], item["added"] = topic_of(item), added_of(item)
    data.append(item)

# New downloads that match none of the original rows -> add them as their own rows
extra = {}
for f in files:
    if f in used_files:
        continue
    stem = re.sub(r"\.(pdf|xlsx)$", "", f, flags=re.I)
    extra.setdefault(stem, {})[f.lower().rsplit(".", 1)[-1]] = f
# Portal names the PDF "Full-title-2026-Portal.pdf" but the XLSX "snake_case_title.xlsx" (no id): pair them per folder by title words
pairs = []
for fo in {os.path.dirname(s) for s in extra}:
    pdfs = [s for s, fm in extra.items() if os.path.dirname(s) == fo and "pdf" in fm and "xlsx" not in fm]
    xls = [s for s, fm in extra.items() if os.path.dirname(s) == fo and "xlsx" in fm and "pdf" not in fm]
    for sc, ps, xs in sorted(((len(words(os.path.basename(p)) & words(os.path.basename(x))) / max(1, len(words(os.path.basename(x)))), p, x)
                              for p in pdfs for x in xls), reverse=True):
        if sc < 0.7 or ps not in pdfs or xs not in xls:
            continue
        pdfs.remove(ps); xls.remove(xs); pairs.append((ps, xs))
for ps, xs in pairs:
    extra[ps]["xlsx"] = extra[xs]["xlsx"]; del extra[xs]
for stem, fm in sorted(extra.items()):
    base = os.path.basename(stem)
    title = re.sub(r"\s+", " ", re.sub(r"[-_]+", " ", re.sub(r"(?i)\b2026[- ]portal\b", "", base))).strip()
    title = title[:1].upper() + title[1:]
    folder = os.path.dirname(stem).split(os.sep)[0] if os.path.dirname(stem) else "new"
    tag = re.sub(r"[^a-z0-9]+", "-", folder.lower()).strip("-") or "new"
    ym = re.search(r"(20\d\d)", base)
    item = {"t": title, "tags": tag, "y": ym.group(1) if ym else datetime.now().strftime("%Y"), "u": "",
            "pdf": fm.get("pdf", ""), "xlsx": fm.get("xlsx", ""), "nas": False, "cloud": False}
    got = [x for x in (item["pdf"], item["xlsx"]) if x]
    item["nas"] = all(x in nas_files for x in got)
    item["cloud"] = all(x in cloud for x in got)
    item["got"] = len(got)
    item["topic"], item["added"] = topic_of(item), added_of(item)
    data.append(item)
    used_files |= set(got)

n_have = sum(1 for d in data if d["got"] == 2)
n_nas = sum(1 for d in data if d["nas"])
n_cloud = sum(1 for d in data if d["cloud"])
unmatched = [f for f in files if f not in used_files]

# Paperless
paperless_up, paperless_docs = False, 0
try:
    code = urllib.request.urlopen(PAPERLESS + "/accounts/login/", timeout=6).getcode()
    paperless_up = code == 200
except Exception:
    pass
orig = NAS_SHARE + "/docker/research-hub/paperless/media/documents/originals"
if os.path.isdir(orig):
    paperless_docs = sum(len(fs) for _, _, fs in os.walk(orig))

# NAS usage
nas_pct, nas_txt = 0, "NAS not mounted"
if os.path.isdir(NAS_SHARE):
    u = shutil.disk_usage(NAS_SHARE)
    nas_pct = max(1, round(u.used / u.total * 100))
    nas_txt = "%.1f of %.1f TB used" % (u.used / 1e12, u.total / 1e12)

now = datetime.now().strftime("%d %b %H:%M")
cloud_label = "ONLINE" if n_cloud == len(data) else ("PARTIAL" if n_cloud else "OFFLINE")
circ = 2 * 3.14159 * 34
dash = "%.1f %.1f" % (circ * nas_pct / 100, circ - circ * nas_pct / 100)

h = tpl
h = h.replace("Research Hub – sci-fi mock (soft)", "Research Hub")
h = h.replace("<b>12</b><span>Queued</span>", "<b>%d/%d</b><span>Downloaded</span>" % (n_have, len(data)))
h = h.replace("<b>0</b><span>On NAS</span>", "<b>%d</b><span>On NAS</span>" % n_nas)
h = h.replace("<b>OFFLINE</b><span>Cloud mirror</span>", "<b>%s</b><span>Cloud mirror</span>" % cloud_label)
h = h.replace("<b>MOCK</b><span>Sample data</span>", "<b>%s</b><span>Snapshot %s</span>" % ("LIVE" if paperless_up else "FILES", now))
h = h.replace('aria-label="NAS usage 3 percent"', 'aria-label="NAS usage %d percent"' % nas_pct)
h = h.replace('stroke-dasharray="6.4 213.6"', 'stroke-dasharray="%s"' % dash)
h = h.replace('font-size="14">3%</text>', 'font-size="14">%d%%</text>' % nas_pct)
h = h.replace("NAS volume<br>Cloud: not connected",
              "NAS volume<br>%s<br>Cloud: Google Drive %d/%d" % (nas_txt, n_cloud, len(data)))
h = h.replace("Zotero → WebDAV on NAS<br>Paperless-ngx → NAS + nightly export<br>rclone / Hyper Backup → cloud",
              "Paperless-ngx: %s · %d documents<br>Search: DSM Universal Search<br>rclone + Hyper Backup → Google Drive" %
              ("online" if paperless_up else "offline", paperless_docs))
h = h.replace("<h2>// Library &amp; download queue</h2>", "<h2>// Library</h2>")
h = h.replace("<th>Status</th>", "<th>Status</th><th>Open</th>")
h = h.replace("Zotero · papers", "Zotero (later)")
h = h.replace('<a href="#">Paperless-ngx · reports</a>', '<a href="%s" target="_blank">Paperless-ngx · reports</a>' % PAPERLESS)
h = h.replace('<a href="#">Portal</a>', '<a href="https://portal.example.com/" target="_blank">Portal</a>')
h = h.replace("&gt; Download queue", "&gt; Requests")


# Portal hierarchy: Region > Industry > Topic (taxonomy.json + portal-sitemap.json) and a searchable catalogue file
TAXO = json.load(open(os.path.join(HERE, "taxonomy.json")))["industries"]
SITE = json.load(open(os.path.join(HERE, "portal-sitemap.json")))
INDUSTRIES = SITE["industries"]
_f2ind = {fo: (ind, top) for ind, tops in TAXO.items() for top, fos in tops.items() for fo in fos}
_PREF = ["Asia", "Europe", "North America", "Africa", "Australia and Oceania", "Central and South America"]
_c2r = {}
for _r in _PREF:
    for _c in SITE["regions"][_r]["countries"]:
        _c2r.setdefault(_c, _r)
_ALIAS = {"U.S.": "United States", "US": "United States", "USA": "United States", "UK": "United Kingdom", "U.K.": "United Kingdom",
          "UAE": "United Arab Emirates", "South Korea": "South Korea", "Burma": "Myanmar [Burma]"}
_REGKW = [("asia-pacific", "APAC"), ("apac", "APAC"), ("middle east", "MENA"), ("mena", "MENA"), ("latin america", "Latin America and the Caribbean"),
          ("north america", "North America"), ("europe", "Europe"), ("african", "Africa"), ("africa", "Africa"), ("oecd", "OECD"), ("worldwide", "Worldwide"), ("global", "Worldwide")]
def region_of(title):
    low = " " + title.lower() + " "
    best = None
    for c, r in list(_c2r.items()) + [(a, _c2r.get(v, "")) for a, v in _ALIAS.items()]:
        m = re.search(r"(?<![A-Za-z])" + re.escape(c.lower() if len(c) > 3 else c) + r"(?![A-Za-z])", low if len(c) > 3 else " " + title + " ")
        if m and (best is None or m.start() < best[0]):
            best = (m.start(), _ALIAS.get(c, c), r or _c2r.get(_ALIAS.get(c, c), ""))
    if best:
        return best[2], best[1]
    for kw, r in _REGKW:
        if re.search(r"(?<![a-z])" + re.escape(kw) + r"(?![a-z])", low):
            return r, ""
    return "Unspecified", ""
import csv as _csv
for r in data:
    r["ind"], r["topicname"] = _f2ind.get(r["topic"], ("Other", r["topic"]))
    r["reg"], r["ctry"] = region_of(r["t"])
_rows = [["region", "country", "industry", "topic", "folder", "year", "title", "pdf", "xlsx", "statistic_id", "added"]]
for r in data:
    _rows.append([r["reg"], r["ctry"], r["ind"], r["topicname"], r["topic"], r["y"], r["t"], r["pdf"], r["xlsx"], (r["u"] or "").split("/")[0], datetime.fromtimestamp(r["added"]).strftime("%Y-%m-%d") if r.get("added") else ""])
_rows[1:] = sorted(_rows[1:], key=lambda x: (x[0], x[2], x[3], x[5], x[6]))
with open(os.path.join(HERE, "data", "portal-catalog.csv"), "w", newline="", encoding="utf-8") as _fh:
    _csv.writer(_fh).writerows(_rows)
if os.path.isdir(NAS_SHARE + "/research-archive/Portal"):
    shutil.copy(os.path.join(HERE, "data", "portal-catalog.csv"), NAS_SHARE + "/research-archive/Portal/_catalog.csv")

# data block
new_d = "const D=" + json.dumps(data, ensure_ascii=False).replace("</", "<\\/") + ";\n"
_regc = {k: list(v["countries"]) for k, v in SITE["regions"].items()}
_regc["APAC"] = SITE["regions"]["Asia"]["countries"] + SITE["regions"]["Australia and Oceania"]["countries"]
new_d += "const REGC=" + json.dumps(_regc, ensure_ascii=False) + ";\n"
new_d += "const IND=" + json.dumps(INDUSTRIES) + ",REGS=" + json.dumps(list(SITE["regions"].keys())) + ";\n"
new_d += ("const PL=%s,SMB=%s;\n" % (json.dumps(PAPERLESS), json.dumps(SMB_BASE)))
h = re.sub(r"const D=\[.*?\];\n(?=const TAGS)", lambda _: new_d, h, flags=re.S)
# adapt code that read D as arrays
h = h.replace("D.forEach(r=>{const k=r[1].split(' ')[0]", "D.forEach(r=>{const k=r.tags.split(' ')[0]")
h = h.replace("D.forEach(r=>y[r[2]]=(y[r[2]]||0)+1)", "D.forEach(r=>y[r.y]=(y[r.y]||0)+1)")
LIB_JS = open(os.path.join(HERE, "library-view.js"), encoding="utf-8").read().replace("__CAP__", str(CAP))
h = re.sub(r"function f\(\)\{.*?(?=\nf\(\);)", lambda _: LIB_JS, h, flags=re.S)
h = re.sub(r'<div class="chips" id="chips"></div>\s*<table>.*?</table>', '<div id="lib"></div>', h, flags=re.S)
h = h.replace("</style>", open(os.path.join(HERE, "library-view.css"), encoding="utf-8").read() + "</style>", 1)
h = h.replace(".note{color:var(--mut)", ".st.ok{color:var(--sage)}.st.ok:before{background:var(--sage)}.note a{color:var(--teal);margin-right:6px}.note{color:var(--mut)", 1)


# open-data panel (second layer: replicable public data), built by opendata/ingest.py
OD_JS = ""
try:
    OD_JS = open(os.path.join(HERE, "data", "opendata.js"), encoding="utf-8").read()
except Exception:
    pass
if OD_JS:
    panel = ('<div class="card" style="margin-bottom:14px"><h2>// Open data (reusable, with attribution)</h2>'
             '<div class="prov"><div><b>Portal library</b><br><span class="note">Licensed reading copy. Keep for reference; do not redistribute or build a derived database from it. Use it to find the original publisher.</span></div>'
             '<div><b>Open data layer</b><br><span class="note">Fetched straight from the original publishers (World Bank, OWID, Eurostat, PSA). Free to reuse with attribution; licence shown on each card.</span></div></div>'
             '<div id="od"></div></div>')
    h = h.replace('<div class="row2"><div class="card">\n<h2>// Library</h2>', panel + '\n<div class="row2"><div class="card">\n<h2>// Library</h2>', 1)
    h = h.replace("</style>", open(os.path.join(HERE, "opendata-view.css"), encoding="utf-8").read() + "</style>", 1)
    h = h.replace("</body>", '<a href="/bots" style="position:fixed;right:14px;bottom:14px;background:#1a212b;border:1px solid #2b3542;border-radius:20px;padding:7px 14px;color:#5fd1c1;text-decoration:none;font:13px system-ui;z-index:50">Hub bots</a></body>', 1)
    h = h.replace("</body>", "<script>" + OD_JS.replace("</", "<\\/") + "\n" + open(os.path.join(HERE, "opendata-view.js"), encoding="utf-8").read() + "</script></body>", 1)

h = h.replace("</style>", open(os.path.join(HERE, "host-view.css"), encoding="utf-8").read() + "</style>", 1)
h = h.replace("</head>", "<script>try{var _h=localStorage.getItem('rh_host');if(_h)document.documentElement.dataset.host=_h}catch(e){}</script></head>", 1)
h = h.replace("</body>", "<script>" + open(os.path.join(HERE, "host-view.js"), encoding="utf-8").read().replace("</", "<\\/") + "</script></body>", 1)
open(OUT, "w", encoding="utf-8").write(h)
if os.path.isdir(NAS_SHARE + "/research-archive"):
    shutil.copy(OUT, NAS_SHARE + "/research-archive/dashboard.html")

print("rows=%d complete=%d on_nas=%d on_cloud=%d paperless=%s docs=%d nas=%s%%" %
      (len(data), n_have, n_nas, n_cloud, paperless_up, paperless_docs, nas_pct))
for d in data:
    if d["got"] != 2:
        print("INCOMPLETE:", d["t"], d["pdf"] or "-", d["xlsx"] or "-")
if unmatched:
    print("UNMATCHED FILES:", unmatched)
