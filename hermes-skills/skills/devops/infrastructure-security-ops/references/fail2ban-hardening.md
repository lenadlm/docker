# Fail2Ban Hardening — SSHD Only (June 2026)

**Architecture change (June 2026):** Port scan detection moved from fail2ban to CrowdSec native. Recidive jail removed (CrowdSec handles repeat offenders). Fail2ban now runs **only the `sshd` jail** for SSH auth-layer blocking. Historical portscan/recidive config preserved below for reference.

## Current Architecture (1 jail)

| Jail | Filter | Log Source | Trigger | Ban | Notes |
|------|--------|-----------|---------|-----|-------|
| `sshd` | built-in (mode=extra) | `/var/log/auth.log` | 2 failures / 12h | 7d → 90d | Pushes bans to CrowdSec via `crowdsec` action (×2 duration) |

Port scan detection is handled by **CrowdSec natively** — see `references/crowdsec-native-portscan.md`.

## SSHD Filter Review

The built-in `/etc/fail2ban/filter.d/sshd.conf` with `mode = extra` is the active configuration (changed from `aggressive` June 2026):

| Pattern | Hits (24h) | What it catches |
|---------|-----------|-----------------|
| `Failed \S+ for ... from <HOST>` | ~2,600 | Failed password (root, valid, invalid users) |
| `Invalid user ... from <HOST>` | ~5,800 | Unknown username attempts |
| `Connection closed ... [preauth]` | ~6,800 | Connections dropped before auth |
| Various (banner, negotiate, etc.) | ~30 | Protocol-level anomalies |

**Key settings:**
- `mode = aggressive` — combines normal + ddos + extra patterns
- `publickey = any` — counts ALL failed publickey attempts as failures (most aggressive)
- `backend = polling` with `logpath = /var/log/auth.log`

**Verdict:** No gaps. Every SSH brute-force pattern is covered. The 7,500+ "missed" lines from `fail2ban-regex` are legitimate (CRON, sudo, successful logins).

## Verification (current: sshd only)

```bash
# Reload fail2ban after changes
sudo fail2ban-client reload

# Verify only sshd jail active
sudo fail2ban-client status

# Check individual jail stats
sudo fail2ban-client status sshd

# Cross-check: any IP in auth.log NOT in banned list?
BANNED=$(sudo fail2ban-client status sshd 2>/dev/null | grep "Banned IP list" | sed 's/.*Banned IP list:\\t//' | tr ' ' '\\n' | sort)
ALL_IPS=$(sudo grep "Failed password\\|Invalid user" /var/log/auth.log | awk '{for(i=1;i<=NF;i++) if($i ~ /^[0-9]+\\.[0-9]+\\.[0-9]+\\.[0-9]+$/) print $i}' | sort -u)
comm -13 <(echo "$BANNED" | sort) <(echo "$ALL_IPS" | sort)
```

## Pitfalls (current sshd jail)

- **CrowdSec ban expiry creates "already banned" gap (CRITICAL, NOT reinsertban):** When using `action = crowdsec`, fail2ban's `actionban` script only runs once per IP. The CrowdSec decision expires, but fail2ban keeps the IP in its internal banned list — saying "already banned" without re-pushing. **Fix:** Double CrowdSec duration in action script (`_DURATION=$(( _DURATION * 2 ))`) so bans overlap. `reinsertban` is NOT a real fail2ban setting (v1.0.2).
- **Reload resets all per-IP counters:** `sudo fail2ban-client reload` or restart resets every IP's failure counter to zero. After reload, it takes 5-10 minutes of uninterrupted monitoring for active scanners to accumulate enough hits. **Avoid reloading during active attacks.**
- **Config consolidation in jail.local:** All jail definitions belong in `/etc/fail2ban/jail.local`, NOT split across `jail.d/*.conf`. Filter files (regex patterns) still live in `/etc/fail2ban/filter.d/`. Keep `jail.d/defaults-debian.conf` as the only system file.
- **docker-auth is fully redundant:** Portscan covered it at network level, sshd covers auth level. No Docker API exposed over TCP on this host. Filter + jail already removed.
- **UFW log level:** Must be `medium` or higher for UFW BLOCK entries to hit kern.log (consumed by CrowdSec `iptables-logs` parser).

## Historical Config (pre-June 2026)

The following sections document the old fail2ban-centric architecture for reference. Do NOT re-enable these jails — CrowdSec native detection is superior.

### Port Scan Jail (DEPRECATED — replaced by CrowdSec `iptables-scan-multi_ports`)

**Prerequisite:** UFW logging must be `medium` or higher
```bash
sudo ufw logging medium
```

**Filter** (`/etc/fail2ban/filter.d/portscan.conf`):
```ini
[Definition]
failregex = ^.*UFW BLOCK.*SRC=<HOST>.*DPT=\\d+ .*$
ignoreregex =
```

**Jail** — in `/etc/fail2ban/jail.local` (removed June 2026):
```ini
[portscan]
enabled   = true
filter    = portscan
backend   = polling
maxretry  = 5
logpath   = /var/log/kern.log
```

**Tuning history (why maxretry=5):**
- Started at `maxretry=10 findtime=10min` — never banned because scanners hit 3-6 ports per burst and moved on before reaching 10
- Lowered to `maxretry=5 findtime=30min` — started catching some but tuning reloads kept resetting counters
- Removed `findtime`/`bantime` overrides → inherits DEFAULT `maxretry=2` — most aggressive, catches everything immediately

**Key insight:** Scanners hit 3-6 unique ports per burst, spread over hours. With maxretry too high (10) they never trigger.

### Recidive Jail (REMOVED June 2026 — CrowdSec handles repeat offenders natively)

Monitored fail2ban's own log for IPs that get banned multiple times across any jail.

**Jail** — in `/etc/fail2ban/jail.local` (removed June 2026):
```ini
[recidive]
enabled    = true
filter     = recidive
backend    = polling
findtime   = 30d
bantime    = 7d
bantime.maxtime = -1
logpath    = /var/log/fail2ban.log
```

**Escalation math (factor=6 inherited from DEFAULT):**
- 1st recidive ban: 7d
- 2nd: 42d
- 3rd: 252d
- No cap (`bantime.maxtime = -1` overrides DEFAULT 90d)

**Why `findtime=30d`:** Persistent attackers often pause days or weeks between campaigns.

**Critical recidive limitation:** Log rotation (`/var/log/fail2ban.log` rotated weekly) capped effective findtime to ~7d, not the configured 30d. journald had same gap — switching to `backend=systemd` didn't help. See SKILL.md pitfalls for full discussion.

## CrowdSec Action Integration

All jails inherit `action = crowdsec` from `[DEFAULT]` in `jail.local`. This pushes bans to CrowdSec's Local API instead of inserting iptables rules directly.

### ⚠️ IMPORTANT: `reinsertban` is NOT a real fail2ban setting

fail2ban v1.0.2 does NOT support `reinsertban`. Adding it to `jail.local` is **silently ignored**. Do NOT use it.

### How the gap actually works

The iptables chain order on this host is:

```
INPUT → CROWDSEC_CHAIN → ts-input → ufw-before-logging-input → ufw-before-input → ... → DROP
         (1st)                                         (2nd)
```

1. **When CrowdSec has active ban:** Traffic dropped at CROWDSEC_CHAIN → UFW never sees it → no UFW BLOCK logged
2. **When CrowdSec ban expires:** Bouncer removes rule → packet passes → UFW DROPs → UFW BLOCK logged
3. **fail2ban sees the log** → IP is in internal banned list → "already banned" — but CrowdSec has NO active decision

**"Already banned" is misleading.** The IP is only "banned" in fail2ban's database. UFW's default DROP policy is the actual enforcement.

### The real fix: Double the CrowdSec ban duration

Since `reinsertban` isn't real, make CrowdSec's ban outlast fail2ban's internal bantime.

**Modify `/etc/fail2ban/action.d/crowdsec.conf`** to add `_DURATION=$(( _DURATION * 2 ))`:

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

**Timeline with bantime=7d and ×2 duration:**
```
T+0d:   fail2ban ban 7d + CrowdSec ban 14d       ✅ Both blocking
T+7d:   f2b expires → re-detection → new 14d CS  ✅ Overlap (original 7d left)
T+14d:  Original CS expires, new one still active ✅ No gap
```

### Gap recovery

If IPs have fallen through (CrowdSec expired, fail2ban says "already banned"):

```bash
sudo cscli decisions add --ip <IP> --reason "fail2ban-<jail>" --type ban --duration 604800s
```

Verify sync:
```bash
sudo cscli decisions list -i <IP> -o human
sudo fail2ban-client status <jail> | grep "<IP>"
```

### CrowdSec native portscan detection (PRIMARY method since June 2026)

CrowdSec **replaces** the fail2ban portscan jail entirely. Installed:

```bash
# Already installed — verify with:
sudo cscli parsers list | grep iptables-logs
sudo cscli scenarios list | grep iptables-scan-multi_ports
```

**How it works:**
1. `kern.log` is acquired by CrowdSec via `/etc/crowdsec/acquis.d/setup.linux.yaml` with `type: syslog`
2. `syslog-logs` parser (s00-raw) extracts structured fields: `program=kernel`, `message=[UFW BLOCK] IN=...`
3. `iptables-logs` parser (s01-parse) matches on `evt.Parsed.program == 'kernel'` and `message contains 'IN='`, **excludes ACCEPT and AUDIT lines** → only DROP/BLOCK events pass through
4. Sets `log_type = iptables_drop`, extracts `source_ip`, `dst_port`, `proto`
5. `iptables-scan-multi_ports` scenario triggers on **15 distinct destination ports within 5 seconds**
6. Ban pushed to CrowdSec LAPI → bouncer inserts CROWDSEC_CHAIN rule immediately

**Metrics interpretation:**
- kern.log shows ~97 parsed out of 43k+ lines — **normal**. Parser explicitly skips ALLOW/AUDIT/ACCEPT
- "Lines poured to bucket" (~20) shows how many triggered the scenario threshold — that's the real signal
- ACCEPT/AUDIT lines are not a gap — they're correct exclusions

**Benefits over fail2ban portscan jail:**
- No "already banned" gap — single enforcement system
- No sync issues between fail2ban internal state and CrowdSec decisions
- No per-IP counter resets on reload
- Direct LAPI enforcement — faster reaction

**Migration path (June 2026):**
1. Ensure `crowdsecurity/iptables-logs` parser is installed and enabled
2. Ensure `crowdsecurity/iptables-scan-multi_ports` scenario is installed and enabled
3. Verify `kern.log` is in acquis config with `type: syslog`
4. Reload CrowdSec: `sudo systemctl reload crowdsec`
5. Verify metrics: `sudo cscli metrics 2>&1 | grep -E "(kern|iptables|poured)"` — confirm parsing is working
6. Remove fail2ban portscan jail from `jail.local`
7. Optionally remove recidive jail (CrowdSec handles repeat offenders natively)
8. Reload fail2ban: `sudo fail2ban-client reload`
9. Verify only sshd active: `sudo fail2ban-client status`

### Action script (`/etc/fail2ban/action.d/crowdsec.conf`)

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

