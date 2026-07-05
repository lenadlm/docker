---
name: opnsense-network-audit-automation
category: network-engineering
description: Class-level umbrella for OPNsense network operations — system audits, network discovery, SSH connectivity, cross-node MCP coordination, and inventory gathering.
version: 2.0.0
author: Leo (Lily) — consolidated from narrow siblings
license: MIT
tags: [opnsense, audit, network, discovery, nmap, ssh, mcp, inventory, telegram, security]
---

# OPNsense Network Operations (Umbrella Skill)

Consolidated umbrella for OPNsense/FreeBSD network operations. Absorbs narrow sibling skills into labeled sections with reference documents.

## Scope

- **System audit**: Automated, read-only health and security reports from srv/OPNsense, delivered to Telegram on a 3-hour schedule
- **Network inventory**: When DHCP/ARP APIs are inaccessible, falling back to ARP table + Nmap scanning
- **Nmap deployment**: Install and run nmap directly on OPNsense/FreeBSD for Layer 2 network discovery
- **SSH connectivity**: Multi-path (Public IP, Tailscale, Local) SSH access verification and automated key management
- **Cross-node MCP**: Manager-Worker coordination between remote Hermes instances via MCP bridge or delegation fallback

---

## References (Absorbed Sub-skills)

### 🔍 Cross-Node MCP Coordination (`references/cross-node-mcp-coordination.md`)
Two approaches for Manager-Worker Hermes coordination: direct MCP bridge (`hermes mcp serve --port <PORT>`) or delegation fallback via SSH-delegated subagents. Port conflict detection, Tailscale binding, SSH key standardization.

### 🌐 Deploying Nmap on OPNsense (`references/gateway-native-nmap-deployment.md`)
Install nmap on OPNsense/FreeBSD via `pkg install -y nmap`, run subnet discovery scans for Layer 2 MAC addresses, correlate with ARP table. Backgrounding strategies for large subnets.

### 📋 Network Inventory with Access Restrictions (`references/network-inventory-with-restrictions.md`)
Fallback chain when OPNsense DHCP/ARP APIs are blocked: ARP table → Nmap scan → Terminal tools. Per-OPNsense specific paths and DNS correlation.

### 🔑 SSH Infrastructure Access Verification (`references/ssh-infrastructure-access-verification.md`)
Systematic multi-path probing (Public IP / Tailscale / Local), automated host key trust (`StrictHostKeyChecking=accept-new`), failure type differentiation ("Connection Refused" vs "Tailnet policy"), and key generation/maintenance.

### Core Audit Script (Original Skill Body Below)

**Prerequisites:**
- Access to srv with SSH key at `~/.hermes/srv_id_rsa`
- Telegram bot token and chat ID
- Tools: nmap, aureport, docker, journalctl, dmesg, auth log
- Root via sudo for audit/log commands

**Workflow:**
- Run every 3 hours via cron
- Read-only (no destructive actions)
- Create `/tmp/srv_system_report.sh` on srv
- Gather: system info, aureport (today), docker ps, auth.log tail, dmesg
- Build Markdown report, deliver to Telegram

**Commands:**
```bash
# System info
hostnamectl && uptime && df -h

# Audit
sudo aureport -au --summary -ts today
sudo aureport -x --summary -ts today

# Docker
docker ps --format "Names\tStatus\tImage"

# Logs
sudo tail -n 50 /var/log/auth.log
sudo dmesg -T --level=err,crit,alert,emerg

# Telegram delivery
curl -s -X POST "https://api.telegram.org/bot$TOKEN/sendMessage" \
  -d "chat_id=$CHAT_ID" -d "text=$report" -d "parse_mode=Markdown"
```

**Verification:**
- Manual run to verify content formatting
- Validate Telegram delivery
- Cron schedule: `0 */3 * * *`
