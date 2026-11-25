# Research-Hub Portal

Automated, two-Mac downloader and archive for a licensed **Research Data Portal**.
A scheduled Claude task downloads statistics (XLSX + PDF) per topic into a shared NAS archive.
Two Macs cooperate through the NAS: one is the **primary**, the other a **standby that takes over**
when the primary is down. A small non-AI "bot" on each Mac keeps it healthy, and a local dashboard shows
what has been downloaded.

> **Free version, MIT licensed.** Not affiliated with, endorsed by, or sponsored by any data portal.
> **You are responsible for compliance.** Many data portals restrict automated or bulk downloading in
> their terms. Use this only with your own valid licence and explicit permission. See [DISCLAIMER](#disclaimer).

## Features

- **Scheduled downloads** of XLSX and PDF per topic, with per-topic and per-day caps and a rotation queue
- **Two-Mac failover**: roles (`auto`, `primary-only`, `alternate-only`) and a lock on the NAS prevent double runs
- **Bots (no AI tokens)**: heartbeat, self-heal (remount NAS, reopen Chrome and Claude), peer watching, a shared message channel
- **Self-updating**: each Mac pulls code, task text and the login link from the NAS
- **Dashboards rebuilt automatically** by each bot whenever the archive changes, so both machines show the same numbers
- **Sync check twice a day** (morning before the first download, evening after the last) with auto-repair, a cross-check between both machines and a report on the message channel
- **Dashboard** (local web server, optional tailnet access): archive summary, library view, bot status
- **Duplicate protection**: an ID ledger plus title matching so nothing is downloaded twice
- Optional mirror to cloud storage (rclone) and optional document indexing (Paperless-ngx consume folder)

## How it works (short)

```
 Mac A (primary) ──┐                          ┌── Mac B (alternate)
  scheduled task   │   NAS share (SMB)        │   scheduled task
  hub bot (2 min)  ├─► _hub/  runs, ledger,   ├── hub bot (2 min)
  dashboard :8787  │          bots/, lock.d   │   dashboard :8787
                   └─► <Portal>/  archive  ◄──┘
```

1. Every hour each Mac runs the **gate** (`should-run.py`). It prints `RUN` or `SKIP`.
2. The primary runs. The alternate only runs if the primary is silent or unhealthy, or its last run is too old.
3. A run takes the NAS lock, downloads, writes `runs.jsonl` and `ledger.jsonl`, and releases the lock.
4. Bots exchange heartbeats and messages through `_hub/bots/`.

Details: [docs/architecture.md](docs/architecture.md) and [docs/how-it-works.md](docs/how-it-works.md).

## Requirements

- Two macOS machines (Apple Silicon or Intel), Chrome, and a Claude desktop app with the Claude in Chrome extension
- A NAS (or any SMB share) mounted at `/Volumes/YOUR_NAS_SHARE`
- Python 3.9+ (a real Python, see [docs/macos-permissions.md](docs/macos-permissions.md))
- A valid licence for the data portal

## Quick start

1. Read [docs/install.md](docs/install.md).
2. Create the NAS layout and copy this repository into `_hub/install` (see the install guide).
3. On each Mac run `bash install.sh`.
4. Grant the permissions in [docs/macos-permissions.md](docs/macos-permissions.md).
5. Open the dashboard at http://127.0.0.1:8787/.

## Repository layout

| Path | Purpose |
| --- | --- |
| `src/` | Python and shell scripts, dashboard assets |
| `launchd/` | launchd job templates (`__HOME__`, `__PYTHON__` placeholders) |
| `task/SKILL.template.md` | The scheduled task prompt for Claude |
| `docs/` | Architecture, install, configuration, permissions, troubleshooting |
| `examples/` | Sample config files |

## Documentation

- [Architecture](docs/architecture.md)
- [Install](docs/install.md)
- [Configuration](docs/configuration.md)
- [How it works](docs/how-it-works.md)
- [macOS permissions](docs/macos-permissions.md)
- [Troubleshooting](docs/troubleshooting.md)
- [Security and privacy](docs/security.md)

## Disclaimer

This software is provided as is. It automates a web browser; it does not bypass logins, paywalls or
CAPTCHAs, and it never enters passwords. Using it may violate the terms of the data portal you use.
Obtain permission first. The authors accept no liability for how you use it.

## License

[MIT](LICENSE) © 2026 Research-Hub Portal Contributors
