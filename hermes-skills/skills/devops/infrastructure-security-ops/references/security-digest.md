# Host Security Digest (`security_digest.py`)

Runs daily at **08:00 EAT** via cron job `811f79972198` (`no_agent=True`).

## Script Location

`~/.hermes/scripts/security_digest.py`

## Data Sources

| Section | Command | Source |
|---------|---------|--------|
| Fail2Ban | `fail2ban-client status` | All jails auto-discovered (sshd, portscan, docker-auth) |
| CrowdSec | `cscli alerts list --since 24h` | Alert table parsing |
| Auditd | `ausearch -m USER_LOGIN -ts today` | Audit log |
| System health | `uptime`, `free`, `df`, `ps` | /proc |
| Docker security | `docker info`, `docker inspect` | Docker daemon |

## Risk Score Calculation

- 10 pts: Any Fail2Ban bans in 24h
- 15 pts: >20 CrowdSec alerts in 24h
- 20 pts: >50 failed logins today
- 5 pts: Zombie processes detected
- 10 pts: Privileged containers running
- 5 pts: Non-tailnet exposed ports

**Scale:** 0-9 = Green, 10-29 = Yellow, 30+ = Red

## Key Parsing Patterns

- CrowdSec alert table: `cells[1]` is the IP value column (after `Ip:` prefix). Index 0 is the alert ID, so always use column 1 for IP extraction.
- Auditd IP extraction: `grep -oP 'addr=\K[\d.]+'` extracts bare IPs from ausearch output (strips `addr=` prefix).
- Fail2Ban top attackers: `grep "Ban " /var/log/fail2ban.log* | grep -oP '\d+\.\d+\.\d+\.\d+' | sort | uniq -c | sort -rn` — searches rotated logs too via the glob.
- UFW BLOCK from kern.log: For the portscan jail, `sudo fail2ban-client status portscan` reports current failures. The digest auto-collects this via the generic jail iterator.

## Jail Auto-Discovery

The digest dynamically discovers all fail2ban jails:
```
sudo fail2ban-client status → parse "Jail list: sshd, portscan, docker-auth"
for each jail:
    sudo fail2ban-client status <jail> → parse "Currently banned", "Total banned", "Total failed"
```

No per-jail configuration is needed — adding new jails automatically extends the digest.

## Pitfalls

- `docker port` only shows the actual bound IP — use it to verify tailscale-only binding
- CrowdSec `cscli alerts list` table format varies — the value (IP) column is column 2 (index 1), not column 1
- Auditd `ausearch -ts today` uses local timezone — ensure EAT offset is correct
- `sudo` commands in reports need NOPASSWD in `/etc/sudoers` or they hang in non-interactive cron context