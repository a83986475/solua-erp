# xPos repair baseline — 2026-09-18

This manifest records the source and rollback baseline without storing credentials or connection-config values.

## Source

- Upstream repository: `https://github.com/kodlyft/xpos.git`
- Branch: `develop`
- Source commit: `67457ca89e6d61077abad0df532cab473d61e356`
- Controlled build root: `xpos-client/frontend`
- Installed package version: `1.0.9`

## Rollback archive

Archive root: `C:\xpos\backups\xpos-20260918-baseline\`

| Artifact | Size | SHA256 |
|---|---:|---|
| `app.asar.v1.0.9` | 10,267,328 bytes | `4CB3A05B5BA8F1BCD2034EF93D880EF3BDD534DFF9131860489B5DBB8C7063F5` |
| `schema.sql` | 32,222 bytes | `FF036ED8F610BA3CD10BC80C0CB7A4F199F238035E4F7162896D3C2E7EE387DD` |
| `config/X POS-db-config.json` | 240 bytes | `90BB0B75CF9E2F14FD4880F5A92466A32FFF8C08B89F612DA6EA66A02A00F184` |
| `config/xpos-frontend-db-config.json` | 240 bytes | `90BB0B75CF9E2F14FD4880F5A92466A32FFF8C08B89F612DA6EA66A02A00F184` |

The extracted application baseline is archived at `app_extracted-v1.0.9/`. The database schema copy is the authoritative read-only structural backup for this repair; the local database itself was not modified or dumped.
