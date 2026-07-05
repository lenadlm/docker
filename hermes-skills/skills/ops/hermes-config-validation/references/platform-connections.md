# Platform Connection Testing: Telegram

## Bot Token Validation

### Direct API Test (no Hermes dependency)

```bash
source ~/.hermes/.env
curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe"
```

**Success response:**
```json
{
    "ok": true,
    "result": {
        "id": 8269470367,
        "is_bot": true,
        "first_name": "Hermes PVE",
        "username": "lulu_hermes_bot",
        "can_join_groups": true,
        "can_read_all_group_messages": false
    }
}
```

**Failure — invalid token:**
```json
{"ok": false, "error_code": 401, "description": "Unauthorized"}
```

## Gateway Startup Log Sequence (Success)

Read gateway logs with:
```bash
tail -30 ~/.hermes/logs/gateway.log
```

Successful Telegram connect produces this sequence:

```
Connecting to telegram...
[Telegram] Auto-discovered Telegram fallback IPs: 149.154.166.110
[Telegram] Telegram fallback IPs active: 149.154.166.110
[Telegram] set_my_commands OK for scope BotCommandScopeDefault (30 cmds)
[Telegram] set_my_commands OK for scope BotCommandScopeAllPrivateChats (30 cmds)
[Telegram] set_my_commands OK for scope BotCommandScopeAllGroupChats (30 cmds)
[Telegram] Telegram menu: 30 commands registered, 132 hidden (over 30 limit)
[Telegram] Connected to Telegram (polling mode)
✓ telegram connected
Gateway running with 1 platform(s)
Channel directory built: 2 target(s)
Sent home-channel startup notification to telegram:231665210
```

### Key success markers
- `✓ telegram connected` — the golden signal
- `Connected to Telegram (polling mode)` — confirms the mode (long polling vs webhook)
- `set_my_commands OK` — bot commands registered interactively
- `Sent home-channel startup notification` — delivery path confirmed

## Gateway Startup Log Sequence (Failure)

```
Connecting to telegram...
[Telegram] Primary api.telegram.org connection failed (); trying fallback IPs 149.154.167.220
[Telegram] Fallback IP 149.154.167.220 failed
[Telegram] Connect attempt 1/3 failed: Timed out — retrying in 1s
... (repeats 3 times)
✗ telegram failed to connect
Gateway failed to connect any configured messaging platform: telegram: Telegram startup failed: Timed out
```

### Failure causes and remedies

| Symptom | Likely Cause | Fix |
|---------|-------------|-----|
| All 3 attempts timeout | Network blocks Telegram's IPs (common in restricted geos or locked-down cloud VMs) | Use a proxy, VPN (Tailscale exit node), or check firewall rules |
| Primary fails but fallback works | DNS resolution issue for `api.telegram.org` | Check `/etc/resolv.conf` or switch DNS provider |
| 401 Unauthorized | Bot token wrong or revoked | Re-generate token via @BotFather, update `~/.hermes/.env` |

## Environment Variables

These go in `~/.hermes/.env`:

```
TELEGRAM_BOT_TOKEN=<from_BotFather>
TELEGRAM_HOME_CHANNEL=<numeric_chat_id>    # Startup notification & cron delivery target
TELEGRAM_ALLOWED_USERS=<comma_separated_ids>  # User IDs allowed to DM the bot
```

### Finding your chat/user ID
- Message `@userinfobot` on Telegram to get your numeric user ID
- For group chats: add @getidsbot to the group

### Critical .env ordering pitfall
The shipped `~/.hermes/.env` has a **commented-out template line**:
```
# TELEGRAM_BOT_TOKEN=***
```
Then somewhere below, the real uncommented line:
```
TELEGRAM_BOT_TOKEN=826947...
```

Since `.env` is sourced with `source ~/.hermes/.env`, **the last uncommented occurrence wins**. If there are two uncommented lines (both working and stale), the last one takes effect. If only the commented line exists, the variable is empty.

**Check with:**
```bash
grep -n "^TELEGRAM_BOT_TOKEN\|^# TELEGRAM_BOT_TOKEN" ~/.hermes/.env
```

## Plugin Management

```bash
# List all plugins and their status
hermes plugins list | grep platform

# Enable a platform
hermes plugins enable telegram-platform

# Disable a platform
hermes plugins disable telegram-platform

# Verify in config
hermes plugins list | grep telegram-platform
# Should show: enabled
```

**Critical**: `hermes plugins enable` prints "Takes effect on next session" — this means the gateway must be **restarted**. The plugin only loads at gateway startup.

## Gateway Restart

```bash
hermes gateway restart
```

**Warning**: This kills any active agent sessions. Warn the user first.

After restart, verify the plugin loaded:
```bash
sleep 3 && tail -10 ~/.hermes/logs/gateway.log | grep -E "telegram"
```

## Config Verification

```bash
hermes config show | grep -A1 "Messaging Platforms"
# Should show: Telegram:    configured
```

If it shows "not configured", the gateway knows about the platform but is waiting for the plugin and token.

## Network Connectivity

Telegram API servers are behind Cloudflare. Primary endpoint:
- `api.telegram.org` (resolves to Cloudflare IPs)

Fallback direct IPs (hard-coded in Hermes):
- `149.154.167.220` (older logs show `149.154.166.110` — varies by region)

If both DNS resolution and direct IPs fail on a host that has general internet access, check:
1. Host firewall (iptables/nftables/ufw) — allow outbound HTTPS to any destination
2. Corporate/ISP-level blocks on Telegram domains
3. DNS blocking (some resolvers NXDOMAIN telegram.org)