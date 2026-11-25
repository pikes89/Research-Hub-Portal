# AGENTS.md — read this first (AI handoff, ~2 min)

Research-Hub Portal: two Macs download statistics (XLSX+PDF) from a licensed research data portal into a NAS archive. A scheduled Claude task does the browsing; plain Python (no AI tokens) does everything else. MIT licensed. Portal name is kept generic in public files.

## Mental model
- **Shared state** lives on the NAS in `_hub/` (role.json, schedule.json, runs.jsonl, ledger.jsonl, topic-queue.json, reminder.json, lock.d, bots/, install/, secrets/, selftest.json, synccheck.json). Each Mac links `~/ResearchHub/data/*` to it.
- **Roles:** one PRIMARY, one ALTERNATE (`role.json`; mode auto | primary-only | alternate-only). The alternate takes over only if the primary is silent >20 min in the 07:40–20:15 window with no recent run.
- **Gate:** `should-run.py` -> RUN or SKIP (uses `hub-lock.py`: role, NAS mutex `lock.d`, `ran_recently()`, `peer_down()`).
- **Task:** `task/SKILL.template.md` = the hourly Claude scheduled task (browser downloads). Result rule: "nothing new / already archived" is `success`; only real faults are `error`.
- **Bot:** `hub-bot.py` runs via launchd every ~2 min. Heartbeat -> `_hub/bots/<host>.json`; chat -> `bots/messages.jsonl`; then calls `hub-auto.py`. CLI: `hub-bot.py run|status|say "text"|inbox`.
- **Automation (`hub-auto.py`):** login-link sync (NAS<->Mac), code self-update from `install/researchhub-code.tgz` (skipped if `data/no-autoupdate`), task-text update from `install/SKILL.md` (only if `data/auto-skill.flag`), **sync check twice a day** (first run after 07:00 and after 20:30; repairs links/caches, compares both Macs' snapshots only if taken <10 min apart), hourly Downloads->NAS cleanup, dashboard rebuild when the archive size changes.
- **Dashboard:** `hub-server.py` on http://127.0.0.1:8787/ and `/bots`; reads LOCAL files only (launchd cannot read the NAS). `build-dashboard.py` makes the static `dashboard.html`.

## Invariants (do not break)
1. Never type passwords/credentials/tokens into pages; never put the login link or secrets in git (`.gitignore` covers data/, inbox/, secrets/, login-link.txt, `_private/`).
2. Verify the browser belongs to THIS Mac before driving it (identity probe in the task template). Never drive an unconfirmed browser.
3. launchd jobs need macOS Full Disk Access for the exact Python binary (use a real Python: python.org framework or Homebrew, not `/usr/bin/python3`). See `docs/macos-permissions.md`.
4. Only one Mac downloads at a time (lock.d). Don't delete the lock unless it is stale and no run is active.
5. Public repo files are sanitized with placeholders (YOUR_NAS_SHARE, YOURUSER, portal.example.com, mac-a/mac-b, NAS_USER). Re-apply when copying from a live install.
6. Confirm before outward-facing actions (publishing, messaging others, changing system/security settings). Keep subagents minimal; don't switch models without asking.

## Where to look
| Need | File |
|---|---|
| Install / new Mac | `docs/install.md`, `src/install.sh` |
| Config knobs | `docs/configuration.md`, `examples/` |
| Design | `docs/architecture.md`, `docs/how-it-works.md` |
| Fix a problem | `docs/troubleshooting.md`, `docs/macos-permissions.md` |
| The Claude task | `task/SKILL.template.md` |
| Live deployment facts (hosts, paths, open items) | NOT in git: `_private/HANDOFF.md`, mirrored on the NAS at `_hub/HANDOFF.md` |

## Cheap-start checklist for a new AI session
1. Read this file, then `_hub/HANDOFF.md` if you are on the owner's machines.
2. `python3 ~/ResearchHub/hub-bot.py status` -> heartbeat, peer, issues.
3. Read only the last ~20 lines of `_hub/bots/messages.jsonl` and `_hub/runs.jsonl`.
4. Only then open code; each script has a docstring header explaining its purpose.
5. Research first: for any new task, do a short deep-dive on the best options, report and recommend before building.
