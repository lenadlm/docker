---
name: host-security-monitoring
description: "Skills for monitoring host security including Fail2Ban, CrowdSec, Auditd, and Docker health."
version: 1.1.0
author: Hermes Agent
---

# Host Security Monitoring

This skill provides procedures for monitoring and reporting on host-level security services. It focuses on aggregating data from Fail2Ban, CrowdSec, and Auditd, as well as Docker daemon health and resource usage, into human-readable digests.

## Core Services

### Fail2Ban
- **Logs**: Usually at `/var/log/fail2ban.log`.
- **Logic**: Track `Ban` and `Unban` events.
- **Commands**: `fail2ban-client status <jail>` for real-time status.

### CrowdSec
- **Tool**: Use `cscli`.
- **Key Command**: `cscli decisions list -o json` to get active bans.
- **Architecture**: CrowdSec uses a local API (LAPI); ensure the service is running to query decisions.

### Auditd (Linux Auditing System)
- **Logs**: Usually at `/var/log/audit/audit.log`.
- **Search**: Use `ausearch` for structured querying (requires root).
- **Common queries**:
  - Failed logins: `ausearch -m USER_LOGIN,USER_AUTH -ts today --success no`
  - Modification of sensitive files: `ausearch -m SYS_CALL -k sensitive_files`

### Docker Monitor
- **Daemon Health**: `docker info --format '{{json .}}'` provides version, CPU, and resource info.
- **Disk Usage**: `docker system df` tracks space used by images, containers, and build cache.
- **Resources**: `docker stats --no-stream` for per-container CPU/Memory.
- **Issues**: Filter for `health=unhealthy` or `status=exited` to find failed containers.

## Procedures

### Generating a Daily Digest
1. **Extraction**: Use a Python script to parse logs from the last 24 hours. Python's `re` module is effective for the semi-structured nature of these logs.
2. **Aggregation**: Count bans/unbans and group Auditd events by targeted account or source IP.
3. **Docker Stats**: Include daemon health, `system df`, and container resource usage. 
4. **Hermes & Maintenance**: include current version, latest GitHub release (via API), release notes/new features, and a summary of system package updates from `dpkg.log`.
5. **Scheduling**: Use the `cronjob` tool to schedule daily execution (e.g., Security at 09:00, Docker at 10:00, Maintenance at 11:00).
6. **Delivery**: Set the cronjob delivery to `origin` to report directly back to the user's messaging platform (e.g., Telegram). Use Telegram-friendly formatting (bullets, bold headers, no tables).

## Diagnostic Workflow: Missing/Inaccessible Services (e.g. Port 8888)

When a specific port is inaccessible, follow this verified diagnostic sequence:
1. **Process Binding Check**: `ss -tulpn | grep <port>` or `netstat -tulpn`. Confirm if ANY process is listening and on which interface (127.0.0.1 vs 0.0.0.0 vs Tailscale IP).
2. **Local Loopback Test**: `curl -v http://127.0.0.1:<port>/health`. Rules out network/firewall issues.
3. **Interface IP Test**: `curl -v http://<Tailscale-IP>:<port>/health`. Verifies if the service is bound to the Tailscale interface.
4. **Interface Audit**: `ip addr show tailscale0`. Verify the interface is `UP` and has the expected IP.
5. **Firewall Order Audit**: `sudo ufw status verbose` and `sudo ufw status numbered`. Check for "deny" rules that might trump "allow" rules for the specific port.
6. **Tailscale Fabric Check**: `tailscale status` and `tailscale ping <peer-name>`. Verifies the P2P tunnel health.

## Pitfalls & Tips
- **Package Conflicts**: During `apt upgrade`, `openssh-server` (and others) may hang on config file prompts (PID lock). Check `ps aux | grep dpkg` if services fail to restart after updates.
- **AppArmor Denials**: Check for processes like `chrome` (headless) triggering AVC denials in `auditd` logs (`ausearch -m avc -ts today`), as these can prevent service initialization even if the script is "running".
- **UFW Rule Shadowing**: A `deny` rule added later may not override an earlier `allow` depending on position; always check `status numbered`.
- **Telegram Formatting**: Avoid pipe tables in reports; use bullet lists and labeled key-value pairs for better legibility on mobile.

## References
- `templates/monitoring_scripts.md`: A reference implementation of a monitoring script.
- `templates/docker_report.py`: A reference implementation of a monitoring script.
- `templates/security_report.py`: A reference implementation of a monitoring script.
- `templates/maintenance_report.py`: A reference implementation of a maintenance and version report script.
- `references/host-security-monitoring.md`: Additional session-specific notes and commands.

## Custom Reports & Maintenance
- **Purpose**: Daily maintenance, version tracking, and system health reporting.
- **Workflow**: 
  - Collect Hermes version with `hermes --version`.
  - Fetch latest GitHub release via API: `https://api.github.com/repos/NousResearch/hermes-agent/releases/latest`.
  - Extract release notes and features for the report.
  - Summarize today's system package updates from `/var/log/dpkg.log`.
- **References**:
  - `templates/maintenance_report.py`
