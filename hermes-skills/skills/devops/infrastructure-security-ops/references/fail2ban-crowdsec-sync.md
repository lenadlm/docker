# Fail2Ban ↔ CrowdSec Sync Architecture

## The Real Gap Problem (NOT reinsertban)

**`reinsertban = true` is NOT a valid fail2ban setting.** fail2ban v1.0.2 does not support it. Adding it to jail.local is silently ignored. (User correction, June 2026.)

The actual gap works like this:

```
iptables chain order:  CROWDSEC_CHAIN → UFW → DROP
                        (1st)           (2nd)
```

1. IP gets banned → CrowdSec adds rule to CROWDSEC_CHAIN
2. Traffic is dropped at CROWDSEC_CHAIN → UFW never sees it → no UFW BLOCK logged
3. CrowdSec ban expires (after bantime) → bouncer removes rule
4. IP sends packet → passes CROWDSEC_CHAIN → hits UFW → DROPPED → UFW BLOCK logged
5. fail2ban reads UFW BLOCK → IP is in internal banned list → "already banned"
6. But CrowdSec has NO active decision → firewall has NO rule for this IP
7. UFW's default DROP policy is the only thing blocking the traffic

**"Already banned" is misleading — the IP is only "banned" in fail2ban's database, not at the firewall.**

## The Fix: Double CrowdSec Ban Duration

Since `reinsertban` doesn't exist, the fix is to make CrowdSec's ban duration **longer** than fail2ban's internal bantime. This way, when fail2ban's ban expires and the IP gets re-detected, a NEW CrowdSec ban is created — while the old one still has time remaining.

**Modify `/etc/fail2ban/action.d/crowdsec.conf`:**

```bash
actionban = \
    _DURATION="<bantime>"; \
    [ -z "$_DURATION" ] || [ "$_DURATION" -le 0 ] && _DURATION=14400; \
    _DURATION=$(( _DURATION * 2 )); \
    cscli decisions add \
        --ip "<ip>" \
        --reason "fail2ban-<name>" \
        --type ban \
        --duration "${_DURATION}s" 2>/dev/null
```

**Result with bantime=7d:**
- fail2ban internal ban: 7 days
- CrowdSec ban: 14 days (7 × 2)
- T+7d: fail2ban expires → IP re-detected → NEW 14d CrowdSec ban
- T+7d to T+14d: Original CrowdSec ban still active (7d remaining) → bouncer blocks → no gap
- T+14d: Original expires, but fresh 14d ban from T+7d is active → still no gap

**Overlapping bans = zero gap for actively attacking IPs.**

## bantime.increment Behavior Without reinsertban

- `reinsertban` doesn't exist, so `bantime.increment` only fires on NEW bans (when an IP's ban has fully expired and it gets re-detected)
- Actively attacking IPs: fail2ban's internal ban expires → re-detection → NEW ban → increment counts this as ban #2 → 42d → etc.
- This works correctly — each new detection cycle gets the escalated bantime

## CrowdSec Native Port Scan Detection

CrowdSec can **replace** the fail2ban portscan jail entirely:

```bash
# Install the parser and scenario
sudo cscli parsers install crowdsecurity/iptables-logs
sudo cscli scenarios install crowdsecurity/iptables-scan-multi_ports
```

**How it works:**
1. CrowdSec reads kern.log (via acquis.d/setup.linux.yaml)
2. `iptables-logs` parser extracts UFW BLOCK events → sets `log_type = iptables_drop`
3. `iptables-scan-multi_ports` scenario triggers on 15 distinct ports in 5s
4. Ban decision pushed to LAPI → bouncer enforces at CROWDSEC_CHAIN

**vs fail2ban portscan:**
- Single system (no sync issues)
- Direct LAPI enforcement (no action script middleman)
- No "already banned" gap problem
- Already reads kern.log via existing acquis config

**Native SSH detection:** CrowdSec already has `ssh-bf`, `ssh-slow-bf`, `ssh-time-based-bf` scenarios installed. Reads auth.log via acquis. fail2ban sshd jail is redundant but provides additional coverage.

## Gap Recovery (Manual Catch-Up)

When IPs are in fail2ban's banned list but missing from CrowdSec:

```bash
# For each jail, for each missing IP:
sudo cscli decisions add --ip <IP> --reason "fail2ban-<jail>" --type ban --duration 604800s
```

The bulk sync script automates this: `~/.hermes/scripts/fail2ban_sync_check.py`

## The Sync Check Script

`~/.hermes/scripts/fail2ban_sync_check.py` — daily at 12:00 via cron `16a2bd1e5a9b` (no_agent=True).

**Data sources:**
- `sudo fail2ban-client status` — jails, banned IPs
- `sudo cscli decisions list -o json` — CrowdSec decisions
- `sudo grep /var/log/auth.log` — SSH activity, leak detection
- `sudo grep /var/log/kern.log` — UFW block counts
- `sudo grep /var/log/fail2ban.log` — re-detection warnings, errors

## cscli JSON Parsing

The JSON decision `value` is the bare IP (e.g. "185.16.38.148"), NOT "Ip:185.16.38.148".
The `scope` field holds "Ip". Parse by checking `scope == "Ip"` then reading `value` directly.
The human output combines `scope:value` as "Ip:IP" — do NOT try to strip the "Ip:" prefix from JSON values.

## cscli Requires sudo (Non-Root Shells)

`/etc/crowdsec/config.yaml` is 600 root. Always use `sudo cscli` in scripts and manual operations.
The actionban script works without sudo because fail2ban-server runs as root.

## CrowdSec Supersedes Duplicate Decisions

When `cscli decisions add` is called multiple times for the same IP, each new decision replaces the previous one. Only 1 active decision per IP at any time.
`cscli decisions list -i <IP>` returns 1 result.
`cscli alerts list -i <IP> --all` shows the full history including superseded decisions.

## Current Config (Final, Jul 2026)

**jail.local — only sshd:**
```
[DEFAULT]
backend         = auto
banaction       = crowdsec
banaction_allports = crowdsec
action          = crowdsec
maxretry        = 2
findtime        = 12h
bantime         = 7d
bantime.increment = true
bantime.factor  = 6
bantime.rndtime = 12h
bantime.maxtime = 90d

[sshd]
enabled    = true
filter     = sshd
port       = ssh
mode       = extra         # NOT aggressive — aggressive catches sudo PAM entries
backend    = polling
logpath    = /var/log/auth.log
```

Portscan and recidive jails **removed** — CrowdSec handles port scanning natively via `iptables-scan-multi_ports` scenario (capacity=3, leakspeed=10s).

**Auto-ban pipeline:** The sync script (`fail2ban_sync_check.py`) now auto-bans gap IPs via:
```bash
cscli decisions add --ip <IP> --duration 7d --reason "fail2ban-sync-sshd"
```

**Action script** (`/etc/fail2ban/action.d/crowdsec.conf`):
Doubles the ban duration via `_DURATION=$(( _DURATION * 2 ))` so CrowdSec outlives fail2ban's internal bantime.

**Logrotate** (`/etc/logrotate.d/fail2ban`):
- Weekly rotation
- Keep 3 backups
- Compressed

## Key Timeline of Changes

| Date | Change | Why |
|------|--------|-----|
| Jun 20 | `reinsertban = true` added | Thought it was the fix — silently ignored |
| Jun 21 | Discovered `reinsertban` not supported | User correction |
| Jun 21 | Changed action script to double duration | Real fix — CrowdSec outlives f2b |
| Jun 21 | `bantime` 1d → 7d | Fewer expirations |
| Jun 21 | Logrotate monthly → weekly, rotate 4 → 3 | Standardize rotation |
| Jun 21 | Installed CrowdSec iptables-scan-multi_ports | Native portscan detection |
| Jun 21 | Recidive findtime 30d → 7d | Match logrotate window |