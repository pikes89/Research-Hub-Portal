# Architecture

## Components

| Component | File | Runs | Purpose |
| --- | --- | --- | --- |
| Scheduled task | `task/SKILL.template.md` | hourly, via the Claude app | Drives Chrome to search the portal and download XLSX and PDF |
| Gate | `src/should-run.py` | first step of the task | Decides `RUN` or `SKIP`; syncs shared files; refreshes the heartbeat |
| Lock and roles | `src/hub-lock.py` | gate and task | Role (primary or alternate), mode, NAS lock, takeover rules |
| Bot | `src/hub-bot.py` | launchd, every 120 s | Heartbeat, self-heal, peer watch, messages |
| Automation | `src/hub-auto.py` | called by the bot | Login-link sync, self-update, twice-daily sync check |
| Queue planner | `src/queue-plan.py` | task step 2 | Topic rotation, caps, low-queue reminder |
| Duplicate check | `src/already-have.py` | task | ID ledger plus title matching |
| Status | `src/set-status.py` | task | Live run status and the run log |
| Sync | `src/hub-sync.py` | gate, Terminal, install | Copies shared files; builds the archive cache |
| Dashboard | `src/hub-server.py`, `src/build-dashboard.py` | launchd (KeepAlive) | Local web UI on port 8787 |
| Keep-alive | `src/chrome-keepalive.sh` | launchd, hourly | Keeps Chrome open in working hours |
| Mirror (optional) | `src/mirror.sh` | cron or launchd | rclone copy to cloud storage |

## Shared state on the NAS

```
YOUR_NAS_SHARE/research-archive/
  Portal/<Topic>/            downloaded XLSX and PDF files (the archive)
  _hub/
    role.json                primary, alternate, mode, lock_minutes
    schedule.json            interval_hours, enabled
    topic-queue.json         topics with status active|stopped|done, cap_per_topic
    runs.jsonl               one JSON line per run (host, result, files, note)
    ledger.jsonl             one line per downloaded statistic (folder, title, id)
    reminder.json            low-queue reminder state
    lock.d/                  atomic directory lock, held during a run
    bots/<host>.json         heartbeat of each bot
    bots/messages.jsonl      shared message channel between bots
    selftest.json            latest sync check per host
    synccheck.json           morning and evening data snapshots per host (compared across machines)
    secrets/login-link.txt   optional one-time login link (private, see security.md)
    install/                 install.sh, code bundle, task template, launchd templates
```

Each Mac keeps `~/ResearchHub/data/` as a local cache; `runs.jsonl`, `ledger.jsonl`, `schedule.json`
and `reminder.json` are symlinks into the NAS so both Macs see one state.

## Why two Macs

A laptop sleeps, loses Wi-Fi, or gets rebooted. With two machines, the standby takes over automatically
and gives up control as soon as the primary is healthy again. The NAS is the single source of truth.

## Design decisions

- **The NAS lock is a directory** (`mkdir` is atomic over SMB), with a timeout so a crash cannot block runs forever.
- **Bots use no AI.** They cost nothing to run every two minutes. Only the hourly task uses Claude.
- **Liveness uses two signals**: a fresh heartbeat, or a recent successful run. A silent bot alone does not trigger takeover if runs keep landing.
- **The dashboard reads local files only.** macOS blocks background services from reading the NAS, so the NAS is read by the gate and the bot, which write local caches.
