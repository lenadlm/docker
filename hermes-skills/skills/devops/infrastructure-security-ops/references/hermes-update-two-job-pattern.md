# Hermes Update Two-Job Pattern

## Problem

`hermes update --yes` auto-restarts ALL gateways after git pull + pip install succeeds. When run from within a cron job (`no_agent=True`), the scheduler process (inside the gateway) is killed by systemctl restart, and the delivery pipeline's asyncio event loop is destroyed before stdout can be captured and delivered.

This is a fundamental architecture constraint, not a bug.

## Solution: Two-Job Architecture

Job A (update, 00:00) and Job B (report, 00:15) are separate cron jobs. This eliminates the race condition entirely.

```
00:00 ─► Job A: update_gateway.sh ──► hermes update --yes --no-backup
                                          │
                                          ├── git pull (78 commits)
                                          ├── pip install
                                          ├── npm install + build
                                          └── gateway restart (script killed here)
                                              OK: output lost but update applied

00:15 ─► Job B: hermes_update_check.py ──► report-only script
                                               │
                                               ├── No gateway restart involved
                                               ├── Compares saved SHA vs current SHA
                                               ├── Shows old/new version + changelog
                                               └── Delivered safely via no_agent=True
                                                   (gateway already restarted and running)
```

## Implementation

### Job A: Update (`5b83ad2dfa9e`)

- **Script:** `~/.hermes/scripts/update_gateway.sh` — simple bash wrapper that runs `hermes update --yes --no-backup` and logs to `~/.hermes/logs/update_detached.log`
- **Config:** `no_agent=True`, script resolves relative to `~/.hermes/scripts/`
- **Delivery:** Output is usually lost due to gateway restart — acceptable, the update itself succeeded

### Job B: Report (`31efc67fd9a1`)

- **Script:** `~/.hermes/scripts/hermes_update_check.py` — Python script that:
  1. Loads previously saved git SHA from `~/.hermes/logs/hermes_version_track.json`
  2. Gets current git SHA from `git rev-parse HEAD` in the hermes-agent repo
  3. Compares SHAs → determines if update was applied
  4. Generates changelog between old and new SHA
  5. Saves current SHA to tracking file for next run
  6. Prints report to stdout (delivered by no_agent)
- **Config:** `no_agent=True`, scheduled 15 minutes after update job
- **Safety:** No gateway restart involved → no delivery pipeline risk

## SHA Tracking File

`~/.hermes/logs/hermes_version_track.json`:

```json
{
  "git_sha": "cffd6e3c8d0bf6a180ed19a919fab05f44def311",
  "version": "0.16.0",
  "timestamp": "2026-06-16T00:15:00"
}
```

## Report Format (post-update, successful)

```
🔄 **Hermes Update Report — 2026-06-16 00:15**

📦 **Version Update**
🔹 Old: v0.16.0 (cffd6e3c8d0b)
🆕 New: v0.16.0 (062c17d34f5)
📊 Commits: 78

📋 **Recent Changes**
🐛 ... (up to 8 commits)
🆕 ...

⏱ **Execution**
✅ Updated: cffd6e3c8d0b → 062c17d34f5 (78 commits)
⏰ Next check: 2026-06-17 00:15

🐳 **Agent Status**
✅ Gateway: running
📱 Telegram: connected
...
```

## Detection Logic

```python
old_sha = track.get("git_sha", "")
new_sha = get_current_sha()

sha_changed = old_sha and new_sha and old_sha != new_sha
if sha_changed:
    # Update was applied — show version comparison
elif old_sha == "":
    # First run — seed tracking, check commits behind
    if commits_behind >= 5:
        # Update failed
    else:
        # Up to date (small drift from new upstream pushes)
else:
    # SHA unchanged — check commits behind for failure detection
```

## Edge Cases

- **First run:** No previous tracked SHA → checks `hermes update --check` for commits behind. Small drift (<5) is normal (new upstream pushes during 15min gap between jobs). Large drift (≥5) = update failed.
- **Concurrent runs:** Jobs at 00:00 and 00:15 are spaced by 15 minutes — no overlap.
- **Gateway down at 00:15:** The report script uses `no_agent=True` which delivers via the scheduler directly — if the gateway is down at 00:15, delivery fails. But the gateway should be back up within seconds of the 00:00 restart, so this is unlikely.