# macOS permissions

macOS (TCC) blocks background jobs (launchd) from reading network volumes and protected folders such as
Downloads unless the **exact program** has permission. This caused most of the hard problems in this project.

## Symptoms

- The bot heartbeat on the NAS stops updating, but runs started from the Claude app still land.
- `bot.log` shows `PermissionError: [Errno 1] Operation not permitted: '/Users/<you>/Downloads'` or the NAS path.
- The dashboard shows 0 files even though the archive has thousands.

## Rules that work

1. **Use a real Python for the bot**, not `/usr/bin/python3`. On macOS that file is only a launcher for the Command Line Tools Python.
   Install Python from python.org (universal2) or Homebrew. `install.sh` prefers, in order:
   `/Library/Frameworks/Python.framework/Versions/Current/bin/python3`, `/opt/homebrew/bin/python3`, `/usr/local/bin/python3`.
2. **Grant Full Disk Access to the Python app**: System Settings, Privacy and Security, Full Disk Access, `+`, then Cmd+Shift+G and add
   `/Library/Frameworks/Python.framework/Versions/Current/Resources/Python.app`. Make sure its switch is on.
3. Restart the bot: `launchctl kickstart -k gui/$(id -u)/com.researchhub.bot`.
4. Use `src/fix-bot-python.sh` to point an existing install at the right Python.
5. **Keep the dashboard server off the NAS.** It reads only local files; the gate and the bot (which can reach the NAS) write local caches.
6. **Per-Mac inbox**: set Chrome's download folder to `~/ResearchHub/inbox` (Chrome Settings, Downloads). It avoids the protected Downloads folder.

## Verify

```bash
launchctl list | grep researchhub
tail -n 8 ~/ResearchHub/data/bot.log
python3 ~/ResearchHub/hub-bot.py run
```

The heartbeat in `_hub/bots/<host>.json` should refresh about every two minutes.

## Claude in Chrome, two Macs, one account

The extension registers once per Chrome profile. Tools can silently drive the **other** Mac's Chrome. The task therefore calls
`list_connected_browsers` and `select_browser` for the browser marked `onThisComputer`, and stops if none is. Never drive an unconfirmed browser,
or downloads land on the wrong Mac.
