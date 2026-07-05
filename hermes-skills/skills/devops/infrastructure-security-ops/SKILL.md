---
name: infrastructure-security-ops
description: "Umbrella skill for host security monitoring, docker health, and maintenance reporting workflows."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [monitoring, security, host, docker, fail2ban, crowdsec, auditd, automation, network, recovery]
    related_skills: [lily-network-engineer, docker-management]
category: devops
---

# Infrastructure Security & Monitoring OPS (umbrella)

This umbrella skill consolidates class-level patterns for host security monitoring, Docker health, and automated Hermes-driven reporting. It is designed to be extended with session-specific references and templates, so future sessions can quickly reproduce or adapt successful workflows.

## Scope
- Fail2Ban monitoring (bans/unbans, trends) and report shaping
- CrowdSec decisions and sensor relevance
- Auditd events (login failures, suspicious activity)
- Docker daemon health, container statuses, open ports, and disk usage
- Hermes-driven daily reports to Telegram
- Safe cleanup and maintenance patterns (container/image cleanup, verification)

## Triggers / Capabilities
1) Fail2Ban: derive today’s bans/unbans; surface top offenders
2) CrowdSec: summarize active decisions and notable sensors
3) Auditd: count failed logins today; surface top IPs/accounts
4) Docker: health, containers, ports, disk usage; detect unhealthy containers; recover crashed containers
5) Network health: interface stats, gateway reachability, DNS resolution, listening socket audit
6) System health: cross-host audits across OPNsense, srv, Proxmox, Docker
7) Hermes: deliver digest to Telegram; maintain a clean, skimmable layout

## Pitfalls / Learnings
- **Reporting Preference:** Use grouping bullets/emoji for tabular data. **NEVER use pipe tables** (unsupported in Telegram).
- **Tailscale Configuration:** If running `tailscale up` to change settings (e.g., `--accept-routes`), you MUST explicitly include all current non-default flags (like `--advertise-exit-node`) or the command will fail with an error about missing flags.
- **Service Logic (Auditd):** Query via `ausearch -m USER_LOGIN -ts today --success no` to catch current-day failures.
- **Docker Cleanup:** Before removing images, check for running containers and hidden tags (e.g., `portainer/agent` vs `portainer-agent`).
- **CrowdSec Bouncer Mode:** If `iptables-restore` errors about missing ipsets (`crowdsec-blacklists-1 doesn't exist`), the bouncer config at `/etc/crowdsec/bouncers/crowdsec-firewall-bouncer.yaml` is using wrong mode. Check `mode:` field — should be `nftables` on modern Ubuntu (not iptables+ipset). The error is harmless if the bouncer is already running in nftables mode; just delete stale iptables entries and restart.
- **fail2ban sshd mode:** `mode = aggressive` picks up sudo PAM entries from auth.log that aren't SSH-related, causing "odd timestamp" warnings. Use `mode = extra` instead — it catches all real SSH brute force (bad auth, invalid users, timeouts) but skips sudo noise.
- **auto-ban pipeline:** fail2ban sync script (`fail2ban_sync_check.py`) now auto-bans gap IPs via `cscli decisions add --ip <IP> --duration 7d`. Gap IPs = in fail2ban's banned list but missing from CrowdSec decisions. Run the script to both report and fix gaps.
- **Git config for repo access:** After setting up SSH keys for GitHub, also set `git config --global user.name` and `user.email` — commits will fail silently otherwise.

## Verification Checklist
- [ ] All sub-tasks render as labeled bullets with emojis
- [ ] Delivery destination remains consistent
- [ ] No PII in daily summaries
- [ ] References exist for session replay

## Monitoring Reports & Scheduling (User Persistence)

### Report Formatting
- **Visuals:** Use emojis (🛡, 🐳, 🔍, 🆕) and bullet lists.
- **Tables:** **STRICTLY PROHIBITED.** Telegram does not render pipe tables. Use labeled key-value pairs or group bullets.
- **Content:** Provide summary first. No raw JSON; only human-readable reports.

### Security, Docker, & Tailscale Patterns
- **Tailscale:** Check backend state and MagicDNS connectivity via `tailscale status --json`. Monitor for "Some peers are advertising routes but --accept-routes is false" health warnings.
- **Docker Cooldowns:** When a specific container (e.g., `hlr-login`) needs a restart delay, use a one-time cron job (`repeat: once`) to handle the wait time.
- **Disk Usage:** Include `docker system df` details for image, volume, and build cache bloat.

### Daily Schedule
- **09:00:** Security (Fail2bit, CrowdSec, Auditd).
- **10:00:** Docker (Health, Usage, Disk).
- **11:00:** Hermes & Maintenance (Version, Changelog, Packages).

## Examples / Commands (non-exhaustive)
- Fail2Ban: sudo fail2ban-client status
- CrowdSec: sudo cscli decisions list -o json
- Auditd: sudo ausearch -m USER_LOGIN -ts today --success no
- Docker: docker info, docker ps -a, docker system df
- Hermes: hermes --version; hermes update
- Tailscale: tailscale status; systemctl status tailscaled

## Sub-skills Absorbed (Consolidation)
The following narrow skills have been consolidated into this umbrella as reference documents:

### 📋 Host Security Monitoring (`references/host-security-monitoring.md`)
Fail2Ban, CrowdSec, and Auditd monitoring procedures. Port accessibility diagnostics (port 8888 pattern), UFW rule shadowing, and AppArmor denial troubleshooting.

### 🖥️ Elevated Infrastructure Reporting (`references/elevated-infrastructure-reporting.md`)
Cross-host system health and security audits. Production-grade report template for system info, log analysis, security services, firewall, Docker, and system logs across OPNsense, srv, Proxmox, and Docker hosts.

### 🐳 Docker Health Check & Recovery (`references/docker-health-check.md`)
Container crash diagnosis and recovery on remote hosts. Portainer BoltDB lock resolution, DNS configuration for Proxmox/KVM guests, stale lock handling, and common failure matrix.

### 🌐 Network Health Check (`references/network-health-check.md`)
Automated local network monitoring: interface stats, gateway reachability, DNS resolution, and listening socket audit with intelligent false-positive filtering.

## References
- `references/host-security-monitoring.md`: Host security (Fail2Ban, CrowdSec, Auditd) detailed procedures
- `references/elevated-infrastructure-reporting.md`: Cross-host system health and security audit methodology
- `references/docker-health-check.md`: Docker container health check and recovery on remote hosts
- `references/network-health-check.md`: Local network health monitoring (interface, gateway, DNS, ports)
- `references/maintenance-reporting.md`: Host maintenance and reporting (Hermes version, system updates, Tailscale)
- `templates/daily_audit_report.py`: Python template for daily audit report generation
- `scripts/quick_health_check.py`: Quick health check script (Tailscale + Docker status)

