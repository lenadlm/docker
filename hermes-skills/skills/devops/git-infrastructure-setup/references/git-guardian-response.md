# GitGuardian Alert Response — Session Detail

## Incident: Telegram Bot Token Exposure

**Date**: 2026-07-03
**Repository**: `github.com:lenadlm/docker.git`
**Secret type**: Telegram Bot Token
**Pushed date**: 2026-07-03 18:10:01 UTC
**Bot username**: `@lulu_hermes_bot` (ID `8269470367`)

### Root Cause

The initial commit contained scripts with a partially-redacted Telegram Bot Token:

```
TELEGRAM_BOT_TOKEN="8269470367:***"
```

GitGuardian detected the `8269470367:` (numeric bot ID + colon) pattern as a Telegram Bot Token — even though the actual secret portion was `***`. The scanner matches the Telegram token format, not a full valid token.

### Resolution Steps

1. **Investigate** — identified the commit (`7671e83`) and file (`automation/scripts/check_homeassistant_update.py`) containing the pattern
2. **Assess** — partial match (bot ID `8269470367` exposed, secret portion `***`). Medium risk since the prefix identifies the bot but not the API key
3. **Revoke** — user revokes via BotFather (`/revoke`) and generates a new token
4. **Expand patterns** — added `literal:8269470367==>BOT_ID_REDACTED` to the replacement file
5. **Multi-pass filter-repo** — first pass missed the bot ID pattern; second pass added it:
   ```bash
   git filter-repo --force --replace-text /tmp/secret-patterns-expanded.txt
   ```
6. **Aggressive cleanup**:
   ```bash
   git reflog expire --expire=now --all
   git gc --prune=now --aggressive
   ```
7. **Delete stale remote branches** — `patch-1` through `patch-5` still carried old history
8. **Force-push** — `main` and `experiments/main`

### Pattern File Evolution

**First pass** (missed the bot ID):
```
literal:231665210==>CHAT_ID_REDACTED
literal:root@pam!hermes==>TOKEN_NAME_REDACTED
regex:PASS=1212\b==>PASS=REDACTED
```

**Second pass** (added the bot ID after GitGuardian alert):
```
literal:8269470367==>BOT_ID_REDACTED
[previous patterns repeated]
```

### Key Takeaway

Always include the **full identifiable prefix** of a secret in replacement patterns, not just the full secret value. GitGuardian and similar scanners match on format patterns, not just valid credentials. A bot token `8269470367:***` still looks like a bot token to the scanner.

### Post-Incident Actions

- [ ] Revoke Telegram bot token via BotFather → generate new
- [ ] Update `~/.hermes/.env` with new token
- [ ] Update `~/projects/.env` with new token
- [ ] Update `~/.hermes/secrets/proxmox_token.env` with new token
- [ ] GitGuardian auto-rescans; may take minutes to hours to clear alert