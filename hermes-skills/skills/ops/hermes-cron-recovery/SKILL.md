---
name: hermes-cron-recovery
description: Recover stuck cron jobs in Hermes Agent when scheduler state becomes stale
category: ops
---

# Recovering Stuck Cron Jobs in Hermes Agent

When Hermes Agent's cron scheduler misses runs (e.g., after a restart), jobs may show old `last_run_at` and an incorrect `next_run_at`, preventing them from firing on schedule.

## Symptoms
- `cronjob list` shows `last_run_at` far in the past (hours)
- `next_run_at` is unexpectedly far in the future (e.g., 18:18 instead of next hour)
- Expected hourly/daily jobs haven't run for multiple intervals
- Gateway has recently restarted

## Recovery Procedure

1. **Check cron job status**
   ```bash
   cronjob list
   ```

2. **Verify scheduler state**
   Look for:
   - `last_run_at` older than the expected interval
   - `next_run_at` not equal to current time + interval
   - `state: scheduled` (should still be scheduled)

3. **Manually trigger each affected job**
   ```bash
   cronjob run --job-id=<JOB_ID>
   ```

   This immediately executes the job and updates timestamps.

4. **Confirm recovery**
   Re-run `cronjob list` and verify:
   - `last_run_at` is recent (within the last minute)
   - `next_run_at` is correctly set to now + interval

5. **Optional: Restart gateway**
   If jobs remain stuck, restart the Hermes gateway to reset the scheduler:
   ```bash
   systemctl --user restart hermes-gateway
   ```

## Prevention
- Ensure gateway service is enabled: `systemctl --user enable hermes-gateway`
- Avoid frequent restarts during scheduled tasks
- Consider a monitoring cron job that alerts if cronjob list shows stale timestamps

## Notes
- The scheduler may not automatically catch up missed runs after a restart; manual triggering is required.
- This issue arises from the cron subsystem's state management; it's being tracked for a fix.
- The `cronjob run` command is idempotent and safe to execute on any scheduled job.