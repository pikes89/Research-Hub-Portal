# Install

Do these once. Use "Mac A" for the primary and "Mac B" for the standby. The steps are identical for both.

## 0. Prerequisites

- NAS with an SMB share (called `YOUR_NAS_SHARE` here) and a user that can read and write it
- On each Mac: Chrome, the Claude desktop app signed in with the same account, the **Claude in Chrome** extension,
  Python 3.9+ (see [macos-permissions.md](macos-permissions.md)), Command Line Tools (`xcode-select --install`)
- A valid licence and a signed-in session on the data portal in each Mac's Chrome

## 1. Mount the NAS on each Mac

Finder, Go, Connect to Server: `smb://192.168.1.50/YOUR_NAS_SHARE`. Tick "Remember this password in my keychain".
It must appear as `/Volumes/YOUR_NAS_SHARE`.

## 2. Create the NAS layout (once)

```bash
NAS="/Volumes/YOUR_NAS_SHARE/research-archive"
mkdir -p "$NAS/Portal" "$NAS/_hub/bots" "$NAS/_hub/install"
cp examples/role.json examples/schedule.json examples/topic-queue.json "$NAS/_hub/"
```

Edit `role.json`: set `primary` and `alternate` to each Mac's lower-case host name (`scutil --get LocalHostName | tr A-Z a-z`).

## 3. Build the install bundle (once)

```bash
mkdir -p /tmp/rh/ResearchHub && cp src/* /tmp/rh/ResearchHub/ && tar czf "$NAS/_hub/install/researchhub-code.tgz" -C /tmp/rh ResearchHub
cp src/install.sh src/fix-bot-python.sh task/SKILL.template.md "$NAS/_hub/install/"
mv "$NAS/_hub/install/SKILL.template.md" "$NAS/_hub/install/SKILL.md"
cp launchd/com.researchhub.server.plist "$NAS/_hub/install/server.plist"
cp launchd/com.researchhub.chrome-keepalive.plist "$NAS/_hub/install/keepalive.plist"
```

Before the first install, edit the placeholders in `src/` and `task/` (see [configuration.md](configuration.md)):
`YOUR_NAS_SHARE`, `192.168.1.50`, `NAS_USER`, `YOURUSER`, `portal.example.com`.

## 4. Install on each Mac

```bash
bash "/Volumes/YOUR_NAS_SHARE/research-archive/_hub/install/install.sh"
```

It extracts the code to `~/ResearchHub`, links shared files, writes the task text and three launchd jobs
(dashboard, Chrome keep-alive, bot), and runs the bot once.

## 5. Permissions and the scheduled task

1. Grant the macOS permissions in [macos-permissions.md](macos-permissions.md).
2. In the Claude app, create a scheduled task named `portal-topic-downloads`, hourly, with the contents of
   `~/.claude/scheduled-tasks/portal-topic-downloads/SKILL.md`.
3. In Chrome on each Mac, open the data portal and confirm you are signed in.

## 6. Verify

```bash
python3 ~/ResearchHub/hub-lock.py status      # role, mode, lock
python3 ~/ResearchHub/hub-bot.py run          # prints: me: OK | peer: healthy
```

Open http://127.0.0.1:8787/ and http://127.0.0.1:8787/bots. After the first run, the bots page shows both Macs and `_hub/selftest.json` appears after 07:45.

## Optional parts

- `opendata/ingest.py` (used by the task template for a second dataset) is not included in this free version; remove step 10's ingest line in the template or add your own.
- Cloud mirror: install rclone, configure a remote named `gdrive`, schedule `src/mirror.sh`.
- Paperless-ngx: `src/sync-to-nas.sh` copies new files into a Paperless consume folder.
