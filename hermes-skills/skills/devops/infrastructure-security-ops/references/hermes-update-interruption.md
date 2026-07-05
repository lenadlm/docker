# Hermes Update Gateway-Restart Interruption

## Pattern
Running `hermes update` (manual or cron) while the Telegram gateway is also active can produce a partial interruption. The update process stages work in order:
1. git pull + stash/restore — completes first
2. pip install (wheel build + dep resolution) — completes second
3. npm install (browser tools postinstall) — runs last
4. gateway restart (if applicable)

If the gateway restarts **during** the update (step 3 or 4), the running `hermes update` process receives a **SIGINT** and exits with code **130** ("Command interrupted"). The gateway's own restart kills the shell session.

## Symptoms
- `hermes update` output shows `[Command interrupted]` at the end
- Exit code `130` (128 + SIGINT)
- npm install may be incomplete (postinstall scripts didn't finish)
- A subsequent `hermes update` run reports: `✓ Already up to date!`

## Why "Already up to date" after interruption
Steps 1 (git pull) and 2 (pip install) completed *before* the interrupt arrived. Only the npm postinstall and the explicit gateway restart step were killed. Re-running detects no new upstream changes, applies the stash, and returns "up to date."

## Verifying completeness
If the npm postinstall was interrupted, the browser tools may not work:
```bash
ls ~/.hermes/hermes-agent/node_modules/.package-lock.json  # check npm state
```
If missing or corrupted, reinstall the browser tools:
```bash
cd ~/.hermes/hermes-agent && npm install
```

## Deliver-Before-Restart Pattern (2026-06-09)

The auto-update script (`~/.hermes/scripts/hermes_update_check.py`) runs
nightly at **00:00 EAT** via cron job `5b83ad2dfa9e` with `no_agent=True`.

**The problem**: `hermes update --yes` auto-restarts ALL gateways (built into
the CLI at `hermes_cli/main.py` line ~8710) after git pull + pip install.
With `no_agent=True`, the cron scheduler captures stdout and delivers it AT
SCRIPT EXIT — but the gateway was already killed and replaced, so the delivery
pipeline's asyncio event loop is dead → `RuntimeError: cannot schedule new
futures after interpreter shutdown` → **report never arrives on Telegram.**

**The fix**: Send the report via `hermes send` BEFORE running the update:

```
Check updates → Build report → Backup config
→ hermes send --to telegram:231665210 --file /tmp/report.md  ← gateway still alive
→ sleep 2s
→ hermes update --yes  ← auto-restarts gateway (safe — report already sent)
→ print brief confirmation (may be lost — doesn't matter)
```

**Key insight**: `hermes send` works independently of the running gateway
for bot-token platforms (Telegram, Discord, Slack, Signal). It reads
credentials from `~/.hermes/.env` directly.

### Script location

`~/.hermes/scripts/hermes_update_check.py` — cron job `5b83ad2dfa9e`,
`no_agent=True`, schedule `0 0 * * *`.

### Edge cases

- **No updates**: No gateway restart → normal `no_agent=True` stdout delivery works fine.
- **`hermes send` fails**: Script logs failure, still proceeds with update.
- **Update fails before pip install**: No restart occurs → brief confirmation print arrives.
- **Manual `hermes update`**: Terminal-attached, restart prints to terminal. No cron pipeline involved.