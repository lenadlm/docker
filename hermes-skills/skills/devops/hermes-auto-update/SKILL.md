---
name: hermes-auto-update
description: "Hermes auto-update workflow: cron job setup, detached update, version tracking, and rollback."
version: 1.0.0
author: Leo
---

# Hermes Auto-Update Workflow

Two-cron approach for zero-downtime Hermes updates with changelog reporting.

## Jobs

### Job 1 — `update_gateway.sh` (00:00 EAT, daily)

Runs `hermes update --yes --no-backup` in detached mode so the gateway process isn't killed mid-update.

```bash
# ~/.hermes/scripts/update_gateway.sh
#!/bin/bash
hermes update --yes --no-backup > /dev/null 2>&1 &
```

### Job 2 — `hermes_update_check.py` (00:15 EAT, daily)

Tracks git SHA between runs and reports old SHA, new SHA, and changelog.

```bash
# ~/.hermes/scripts/hermes_update_check.py
```
Script reads/writes `~/.hermes/logs/hermes_version_track.json` to track the previous SHA, captures current SHA from `git rev-parse HEAD` in the Hermes install dir, and diffs the changelog between them.

Logs: `~/.hermes/logs/update_detached.log`

## Rollback

```bash
cp ~/.hermes/backup/* ~/.hermes/
hermes gateway restart
```

## Cron IDs (for reference)

- Job 1: `5b83ad2dfa9e` (update_gateway.sh)
- Job 2: `31efc67fd9a1` (hermes_update_check.py)