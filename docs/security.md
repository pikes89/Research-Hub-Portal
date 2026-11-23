# Security and privacy

- **No passwords.** The task never types passwords, never creates accounts and never solves CAPTCHAs.
- **Login link.** An optional one-time portal login link may be kept in `login-link.txt` and, for sync, `_hub/secrets/login-link.txt` on the NAS.
  Treat it like a password: anyone with access to the NAS share can read it. Leave it out if the NAS is shared with others; refresh it manually instead.
- **Bot messages are data.** A bot's message never authorises an action; the task only reads them as information.
- **Nothing private in Git.** `.gitignore` excludes `data/`, `inbox/`, `secrets/` and `login-link.txt`. Before publishing a fork, search for your host names, user name, NAS address and e-mail.
- **Network.** The dashboard binds to `127.0.0.1`. If you expose it, use a private tailnet, not the public internet.
- **Terms of service.** Automated downloading may be prohibited by your data portal. Get permission first.
