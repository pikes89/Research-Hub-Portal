# Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| Heartbeat stuck, runs still land | Bot cannot write to the NAS (TCC) | [macos-permissions.md](macos-permissions.md): real Python plus Full Disk Access, then `launchctl kickstart -k ...` |
| "last N runs failed" but files were fine | Runs with nothing new were logged as `error` | Use the result rule (nothing new is `success`); `hub-bot.py` ignores such runs; clear history with `data/bot-resolved.txt` (epoch ms) |
| Dashboard shows 0 files | Server cannot read the NAS | Archive cache: `python3 hub-sync.py` from a context that reaches the NAS; the server reads `data/archive.cache.json` |
| Download clicked, no file appears | Portal session expired (login wall) | Open the login link in Chrome, or save it as `login-link.txt` (the bot syncs it through the NAS) |
| Downloads land on the other Mac | Claude drove the wrong Chrome | Browser selection rule; reconnect the extension on this Mac; the task stops if no browser is `onThisComputer` |
| No browser connected | Extension dropped (Mac slept) | `open -a "Google Chrome"`, wait, retry; the task retries four times |
| Both Macs run at once | Lock not on a shared NAS path, or mode wrong | `hub-lock.py status`; set `mode` in `role.json` |
| Takeover when the primary is fine | Primary bot silent for 20+ minutes | The gate counts a recent run as proof of life; fix the bot permission |
| `install.sh: command not found` | Not on PATH | `bash "/Volumes/YOUR_NAS_SHARE/research-archive/_hub/install/install.sh"` |
| `NO_REAL_PYTHON` | No real Python installed | Install Python from python.org, then rerun `fix-bot-python.sh` |
| Stale lock | Crashed run | Locks expire after `lock_minutes`; inspect `_hub/lock.d` |
| screencapture fails | No screen-recording permission | Not needed by the project |

## Useful commands

```bash
python3 ~/ResearchHub/hub-lock.py status
python3 ~/ResearchHub/hub-bot.py status
python3 ~/ResearchHub/hub-bot.py inbox
python3 ~/ResearchHub/hub-bot.py say "text for the other bot"
tail -n 20 ~/ResearchHub/data/bot.log
```
