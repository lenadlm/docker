# Elevated Infrastructure Reporting

Consolidated from `elevated-infrastructure-reporting` skill. System health and security audits across remote hosts (OPNsense, srv, Proxmox, Docker) delivered to Telegram.

## Data Collection Checklist

### 1) System Info
- Hostname, OS, Kernel, Uptime, CPU, Memory, Disk usage, Top 5 processes (CPU + memory)

### 2) Log Analysis
- Analyze `/var/log/*` for auth health, service errors, critical events
- Summarize counts and patterns (not intrusion detection)

### 3) Security Services
- `fail2ban`: status, active jails, banned count
- `crowdsec`: status, basic metrics

### 4) Firewall Status
- UFW: status + rules summary
- iptables/nftables: basic overview

### 5) Docker Status
- Docker service health, running containers, container health
- Last 50 lines per container (summarized)

### 6) System Logs
- syslog/journald summary, kernel logs (dmesg or `journalctl -k`)
- Highlight errors, warnings, hardware/driver issues

## Safety & Scheduling
- Read-only only — no destructive actions
- Respect sudo boundaries; use safe, explicit commands
- Schedule at 3-hour intervals via cron (e.g., 0 0,8,16 * * *)
- Deliver to Telegram in plain text (no markdown, structured sections with clear headings)