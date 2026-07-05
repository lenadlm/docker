# Hermes Agent — Shared Skills

Skills shared between Hermes instances via git.

**How it works:**
- **Local Hermes** (hermes host): pushes skills every 6h via cron
- **VPS Hermes** (srv): pulls skills every 6h via cron
- Both use the `sync-skills.sh` script

**Sync excludes:**
- `.env`, `*secret*`, `*token*`, `*credential*` files
- Binary/generated files

**Add a new skill:**
```bash
# On local Hermes — create via skill_manage, then push
hermes skill sync --push

# On VPS — pull to get it
hermes skill sync --pull
```