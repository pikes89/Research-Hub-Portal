#!/usr/bin/env python3
"""Topic rotation + low-queue reminder for the Portal task.
  queue-plan.py            -> prints this run's plan: topics in rotation order (least recently served first),
                              how many statistics each still needs, and a REMINDER line when the queue is short.
  queue-plan.py served "Topic A" "Topic B"   -> records that those topics were served now (moves them to the back).
Topics reaching cap_per_topic are set to done (reason "cap"); done-by-cap topics reopen if the cap is raised.
Topics set done for any other reason (search exhausted) are never reopened here.
"""
import json, os, re, subprocess, sys, time, datetime
Q = os.path.expanduser("~/.claude/scheduled-tasks/portal-topic-downloads/topic-queue.json")
HERE = os.path.dirname(os.path.abspath(__file__)); DATA = os.path.join(HERE, "data")
ARCH = "/Volumes/YOUR_NAS_SHARE/research-archive/Portal"
PER_TOPIC, MAX_TOPICS, MAX_STATS = 3, 12, 15
DAILY_MAX = 100  # courtesy limit: statistics saved per calendar day (counted from data/ledger.jsonl)
LOW_LEFT = 30  # remind when 30 or fewer statistics are left in the queue
FOLDERS = {"data centers": "DataCenters", "commercial satellites": "CommercialSatellites", "cybersecurity": "Cybersecurity",
           "ransomeware": "Ransomware", "ransomware": "Ransomware", "gobal warming": "GlobalWarming", "global warming": "GlobalWarming",
           "artificial intelligence": "AI", "data mining": "DataMining", "generative ai": "GenerativeAI", "ai in healthcare": "AIInHealthcare", "data breaches": "DataBreaches", "cybercrime and fraud": "CybercrimeAndFraud", "cloud computing": "CloudComputing", "data center energy and power consumption": "DataCenterEnergyAndPowerConsumption", "satellite internet and broadband": "SatelliteInternetAndBroadband", "greenhouse gas emissions": "GreenhouseGasEmissions", "extreme weather and natural disasters": "ExtremeWeatherAndNaturalDisasters", "health insurance in the philippines": "HealthInsuranceInThePhilippines",
           "trends in private local insurance companies in the philippines": "PrivateInsurancePH",
           "trends in government local insurance companies in the philippines": "GovernmentInsurancePH",
           "trends in foreign insurance companies in the philippines": "ForeignInsurancePH"}


def folder(name, t=None):
    if t and t.get("folder"): return t["folder"]
    return FOLDERS.get(name.strip().lower()) or "".join(w.capitalize() for w in re.findall(r"[A-Za-z0-9]+", name))


def have(name, t=None):
    d = os.path.join(ARCH, folder(name, t))
    if not os.path.isdir(d):
        return 0
    fs = [f.lower() for f in os.listdir(d) if not f.startswith(".")]
    return max(sum(f.endswith(".pdf") for f in fs), sum(f.endswith(".xlsx") for f in fs))  # statistics = pairs


q = json.load(open(Q))
if sys.argv[1:2] == ["served"]:
    now = int(time.time())
    for t in q["topics"]:
        if t["name"] in sys.argv[2:]:
            t["last_served"] = now
    json.dump(q, open(Q, "w"), indent=2); print("recorded", sys.argv[2:]); raise SystemExit

if not os.path.isdir(ARCH):
    print("ARCHIVE NOT MOUNTED"); raise SystemExit(1)
cap = int(q.get("cap_per_topic", 30))
for t in q["topics"]:
    n = have(t["name"], t); t["have"] = n
    if t["status"] == "active" and n >= cap:
        t["status"], t["done_reason"] = "done", "cap"
    elif t["status"] == "done" and t.get("done_reason") == "cap" and n < cap:
        t["status"] = "active"; t.pop("done_reason", None)
json.dump(q, open(Q, "w"), indent=2)

def today_count():
    try:
        n = datetime.datetime.fromtimestamp(time.time(), datetime.timezone(datetime.timedelta(hours=8))); mid = time.time() - (n.hour * 3600 + n.minute * 60 + n.second)  # Philippine midnight
        L = os.path.join(DATA, "ledger.jsonl")
        return sum(1 for l in open(L) if json.loads(l).get("t", 0) >= mid)
    except Exception:
        return 0
done_today = today_count()
if done_today >= DAILY_MAX:
    print("DAILY LIMIT REACHED: %d of %d statistics saved today; download nothing this run." % (done_today, DAILY_MAX)); raise SystemExit
MAX_STATS = min(MAX_STATS, DAILY_MAX - done_today)
act = [t for t in q["topics"] if t["status"] == "active"]
order = sorted(act, key=lambda t: t.get("last_served", 0))  # stable: queue order breaks ties
plan, stats = [], 0
for t in order:
    need = min(PER_TOPIC, cap - t["have"])
    if len(plan) >= MAX_TOPICS or stats + need > MAX_STATS:
        break
    plan.append((t["name"], t["have"], need)); stats += need
print("PLAN (rotation order) cap=%d" % cap)
for n, h, need in plan:
    print("  %s: have %d/%d, download %d" % (n, h, cap, need))
print("run total: %d statistics (%d files)" % (stats, stats * 2))

# reminder: when the statistics left in the queue drop to LOW_LEFT or fewer
try:
    iv = int(json.load(open(os.path.join(DATA, "schedule.json"))).get("interval_hours", 1))
except Exception:
    iv = 1
runs_per_day = len([h for h in range(8, 20) if (h - 8) % iv == 0])
per_run = min(MAX_STATS, PER_TOPIC * len(act)) if act else 0
day_cap = runs_per_day * per_run
remaining = sum(max(0, cap - t["have"]) for t in act)
low = remaining <= LOW_LEFT
rem = {"remaining_statistics": remaining, "day_capacity": day_cap, "runs_per_day": runs_per_day, "low": low,
       "active_topics": len(act), "checked": int(time.time() * 1000)}
if low:
    rem["message"] = ("Queue is almost empty: only %d statistics left across %d active topics (reminder at %d or fewer). Add topics or raise the cap."
                      % (remaining, len(act), LOW_LEFT))
os.makedirs(DATA, exist_ok=True)
json.dump(rem, open(os.path.join(DATA, "reminder.json"), "w"))
print("QUEUE: %d statistics left, day capacity %d (%d runs x %d)" % (remaining, day_cap, runs_per_day, per_run))
if low:
    print("REMINDER: " + rem["message"])
    stamp = os.path.join(DATA, "reminder.last")
    if not os.path.exists(stamp) or time.time() - os.path.getmtime(stamp) > 6 * 3600:  # notify at most every 6 h
        open(stamp, "w").close()
        subprocess.run(["osascript", "-e", 'display notification "%s" with title "Research Hub: add topics"' % rem["message"].replace('"', "'")])
