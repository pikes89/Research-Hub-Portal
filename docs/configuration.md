# Configuration

## Placeholders to replace before first use

| Placeholder | Meaning | Files |
| --- | --- | --- |
| `YOUR_NAS_SHARE` | SMB share name | most scripts, task template |
| `192.168.1.50` | NAS LAN address | `hub-bot.py`, `build-dashboard.py`, task template |
| `100.64.0.10` | NAS tailnet address (optional second route) | `hub-bot.py`, `build-dashboard.py` |
| `NAS_USER` | NAS login name used to remount | `hub-bot.py`, task template |
| `YOURUSER` | macOS short user name | launchd templates, task template |
| `portal.example.com` | the data portal's host | task template, dashboard |
| `Portal` | archive folder name under `research-archive/` | scripts |
| `your-mac.your-tailnet.ts.net`, `you@example.com` | optional Tailscale Serve host and owner | `hub-server.py` |
| `mac-a`, `mac-b` | host names | `src/host-view.*`, `examples/role.json` |

A quick way: `grep -rn YOUR_NAS_SHARE src task launchd` then `sed -i '' 's#YOUR_NAS_SHARE#realname#g' ...`.

## `_hub/role.json`

| Field | Values | Meaning |
| --- | --- | --- |
| `primary`, `alternate` | lower-case LocalHostName | who normally runs, who stands by |
| `mode` | `auto`, `primary-only`, `alternate-only` | `auto` = failover; the others pin one Mac |
| `lock_minutes` | number (default 25) | how long a run lock is valid |

## `_hub/schedule.json`

`interval_hours` (default 1) and `enabled`. The alternate takes over when the last run is older than `interval_hours × 60 + 25` minutes.

## `_hub/topic-queue.json`

`cap_per_topic` (default 100 statistics per topic) and `topics[]` with `name`, `status` (`active|stopped|done`) and `folder`.
New topics: drop a `topic-requests.json` (see `examples/`) in `~/ResearchHub/inbox/`; the task merges and renames it.

## Limits in the task template

Per run, per topic, topics per run and per day are written in the task text (`task/SKILL.template.md`). Keep them modest to respect the portal's terms.

## Data files

- `ledger.jsonl`: `{"t": epoch, "folder": ..., "title": ..., "id": ...}` per downloaded statistic
- `runs.jsonl`: `{"started","finished","result","files","planned","topics","note","host"}` per run
- `result` values: `success`, `partial`, `error`. "Nothing new" is `success`; real faults are `error`.

## Bot working hours

`in_window()` in `hub-bot.py` (about 07:40 to 20:15 local time) controls when the bot reopens Chrome/Claude and when takeover can fire.
