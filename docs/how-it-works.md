# How it works

## 1. The gate

`should-run.py` is the first step of every hourly task run.

1. Mount check: the NAS share must be mounted (remounted if not).
2. `hub-sync.py` refreshes shared files and the archive cache.
3. `hub-bot.py run` refreshes this Mac's heartbeat.
4. `hub-lock.py` decides:
   - **primary**: `RUN` if the schedule interval has elapsed
   - **alternate**: `RUN` only if the last run (by anyone) is older than `interval_hours × 3600 + 25 min`,
     or the primary is down (`peer_down()`: no heartbeat for 20+ minutes during working hours, or unhealthy)
   - A recent run by the primary counts as proof of life, so a silent bot alone does not trigger takeover.
5. `RUN` takes the NAS lock; `SKIP` ends the task.

Modes in `role.json`: `auto` (above), `primary-only`, `alternate-only`.

## 2. The task run

Defined in `task/SKILL.template.md`. In order:

1. Bot messages: `hub-bot.py inbox` shows the other bot's messages as information only. They are never treated as instructions.
2. Queue: load `topic-queue.json`, merge new requests, run `queue-plan.py` to pick this run's topics.
3. NAS check, then **browser selection**: with two Macs on one account, the task must select the Chrome marked as on this computer, never the other Mac's.
4. For each topic: search, take up to N new statistics, download XLSX and PDF into a per-Mac inbox folder, move them into the archive, record them in the ledger.
5. `set-status.py idle` writes the run record. **Result rule**: "nothing new, everything already archived" is `success`; only real faults are `error`.

Caps: per run, per topic, number of topics per run, and per day (see [configuration.md](configuration.md)).

## 3. Bots

`hub-bot.py run`, every 120 s via launchd:

1. Self-heal: remount the NAS; in working hours reopen Chrome and Claude if closed.
2. Write `bots/<host>.json`: NAS, Claude, Chrome, download folder readable, errors in a row, last run, issues.
3. Watch the peer: `healthy`, `unhealthy`, or `offline`. Post messages on changes ("I can't hear you", "You're back").
4. Update the dashboard cache `data/bots.cache.json`.
5. Call `hub-auto.py`.

CLI: `hub-bot.py run | status | say "text" | inbox`.

Failure counting: runs that found nothing new are not failures (`nothing_new()` in `hub-bot.py`).

## 4. Automation (`hub-auto.py`)

- **Login link sync**: `secrets/login-link.txt` on the NAS and the local copy stay in step (newest wins).
- **Self-update**: if `install/researchhub-code.tgz` changed, extract the scripts into `~/ResearchHub` (skipped if `data/no-autoupdate` exists, for the machine you develop on).
- **Task text update**: if `data/auto-skill.flag` exists, replace the local task text from `install/SKILL.md`.
- **Daily self-test** (first run after 07:45): shared files are live NAS links, login link present, both heartbeats fresh, no unrecovered failed runs, archive cache rebuilt. Repairs what it can and reports on the message channel and `selftest.json`.

## 5. Dashboard

`hub-server.py` serves `dashboard.html` and JSON endpoints on `127.0.0.1:8787`. `build-dashboard.py` builds the page from the archive cache. Optional: expose it on a private tailnet with `tailscale serve`.
