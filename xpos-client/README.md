# xPos client source baseline

This directory is the controlled build source for the desktop xPos client.

- Base source: `kodlyft/xpos` `develop` at commit `67457ca89e6d61077abad0df532cab473d61e356`.
- Package version is kept at the installed client line (`1.0.9`).
- The source is intentionally scoped to `frontend/`; ERPNext/server code remains in the existing server app and is not copied into this client baseline.
- The current installed ASAR, extracted application, schema, and local connection-config copies are archived outside Git under `C:\xpos\backups\xpos-20260918-baseline\`.
- Generated output, dependency folders, installers, archives, databases, credentials, cookies, and connection configuration are excluded from version control.

Build from `frontend/` with the checked-in `yarn.lock`. Do not patch `app.asar` directly; update this source and rebuild the package.
