---
name: elevated-infrastructure-reporting
description: Reusable skill for autonomous, read-only, production-grade system health and security reporting across remote hosts (OPNsense, srv, Proxmox, Docker).
version: 1.0.0
author: Leo
license: MIT
metadata:
  hermes:
    tags: [network, monitoring, logging, auditing, auditd, telegram, ssh, sudo]
    related_skills: [lily-network-engineer]
---

# Elevated Infrastructure Reporting

This skill automates the collection and delivery of comprehensive system health and security audits from enterprise-grade hosts (OPNsense, srv, Proxmox, Docker) to Telegram. It focuses on read-only data collection, safe execution, and clear reporting.

## Purpose
- Read-only, authorized maintenance reports for infrastructure health and security.
- Generate human-readable reports delivered to Telegram.
- Serve as a reusable pattern for other hosts and services.

## When to Use
- Regular compliance/audit reporting.
- Security posture reviews.
- Production health dashboards via Telegram.

## Data Collection & Checks
1) SYSTEM INFO
- Hostname, OS, Kernel, Uptime, CPU, Memory, Disk usage, Top 5 processes by CPU and memory.

2) LOG ANALYSIS (High-Level Summary)
- Analyze /var/log/* (authentication health, service errors, critical events).
- Summarize counts and patterns, no intrusion detection.

3) SECURITY SERVICES STATUS
- fail2ban: status, active jails, banned count.
- crowdsec: status, basic metrics if available.

4) FIREWALL STATUS
- UFW: status and rules summary.
- iptables/nftables: basic overview if applicable.

5) DOCKER STATUS
- Docker service status, running containers, container health, and last 50 lines per container summarized.

6) SYSTEM LOGS
- syslog/journald summary, kernel logs (dmesg or journalctl -k). Highlight errors, warnings, hardware/driver issues.

## Output & Delivery
- Output format: plain text (no markdown), structured sections with clear headings.
- Delivery: Telegram chat (using existing bot credentials).

## Safety & Permissions
- Reads only: no destructive actions.
- Respect sudo boundaries; use safe, explicit commands.
- Ensure cron-based scheduling for 3-hour intervals.

## Scheduling & Reuse
- Intended as a reusable skill across hosts. Configure a cron job to run at 0, 8, and 16 hours as appropriate.

## Example Usage
- Trigger a health audit across managed hosts and deliver a Markdown-free plain text report to Telegram.

## Verification & Maintenance
- Validate delivery and adjust formatting if Telegram caps are reached.
- Update the knowledge base with new hosts, OS versions, and container sets as they change.
