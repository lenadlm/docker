# Telegram Gateway Setup Guide

## Symptom: Gateway Restart Loop or Setup Timeout
When running `hermes gateway setup` or looking at `hermes gateway status`, you may see:
- `Active: activating (auto-restart)`
- Errors like: `telegram: Telegram startup failed: The token REDACTED was rejected by the server.`

## Cause
This usually means the `TELEGRAM_BOT_TOKEN` in `~/.hermes/.env` is:
1. Revoked or expired.
2. Contains a typo.
3. Is a placeholder value from a previous failed installation.

## Solution

### 1. Update the Token
Set the actual token from [@BotFather](https://t.me/botfather) using `hermes config set`:
```bash
hermes config set telegram_bot_token "12345678:AaBbCcDd..."
```

### 2. Manual Fresh Start
If the setup wizard is stuck, you can force a clean state:
```bash
# 1. Stop and uninstall any failed service
hermes gateway stop
hermes gateway uninstall

# 2. Cleanup configuration if necessary
# Open config.yaml and remove telegram-related lines like:
# telegram_enabled: true
# telegram_home_id: 123456789

# 3. Re-run setup
hermes gateway setup
```

### 3. Verification
Once the service is started, verify it's green:
```bash
hermes gateway status
```
Look for `Active: active (running)`.
