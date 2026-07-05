---
name: proxmox-api-health
description: Class-level umbrella skill for end-to-end Proxmox VE health reporting via API tokens; fetches version, node status, VM/CT inventories, and delivers plain-text digests to Telegram; logs to /mnt/shared/tmp/proxmox_api_health.log; supports optional audit data pull.
version: 1.1.0
author: Lily
license: MIT
metadata:
  hermes:
    tags: [netops, proxmox, api, telegram, health]
    related_skills: [lily-network-engineer]
---

# Proxmox API Health (Umbrella Skill)

## Purpose
Provide a class-level framework to reliably retrieve Proxmox VE health data via the REST API using API tokens, compose a plain-text digest suitable for Telegram delivery, and log results for auditing. Also includes HTML dashboard generation for visual VM/node status overview.

This umbrella coordinates endpoint calls, token management, dashboard generation, and delivery while allowing specialized sub-skills to plug in new data sources or delivery targets.

## Capabilities
- API token-based authentication against Proxmox VE (version, nodes)
- Inventory: list nodes, list VMs (qemu) and containers (lxc), and per-item status
- Optional: include VM/CT status detail (status_current) when available
- Digest composition: plain-text, Telegram-friendly with header === PROXMOX VE SUMMARY ===
- HTML dashboard: standalone page with color-coded VM/node status from `pvesh` data
- Telegram delivery of the digest via bot API
- Local logging to /mnt/shared/tmp/proxmox_api_health.log
- Secrets handling: host, token id, and token secret loaded from ~/.hermes/secrets/proxmox_token.env
- Optional: audit data pull via SSH to Proxmox host for aureport or host logs (if requested)

## Data Flow & Variables
- Environment:
  - PROXMOX_HOST, PROXMOX_TOKEN_ID, PROXMOX_TOKEN_SECRET stored in ~/.hermes/secrets/proxmox_token.env
  - TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID stored similarly for digest delivery
- Runs: a Python script proxmox_api_health.py (or equivalent) fetches data, assembles digest, and calls Telegram API
- Output log: /mnt/shared/tmp/proxmox_api_health.log

## Usage & Workflow
1) Load secret tokens from ~/.hermes/secrets/proxmox_token.env
2) Execute proxmox health fetch task (e.g., run proxmox_api_health.py).
3) The script will write a plain-text digest to the Telegram chat and log results.
4) Schedule three daily runs via cron: 0 0,8,16 * * *  ~/.hermes/scripts/run_proxmox_health.sh

## Pitfalls & Mitigation
- If `/nodes/<node>/qemu` returns `{"data":[]}` but the node is online and VMs exist, the VMs are likely stopped. Use `/api2/json/cluster/resources` instead — it returns all resources across the cluster including stopped VMs. The node-scoped endpoint only shows running VMs.
- Empty VM list from the node endpoint does not mean Proxmox has no VMs — always check `/cluster/resources` for the full picture.
- **API data structure quirks** — the `/nodes/{node}/status` endpoint returns `memory`, `swap`, and `rootfs` as **nested dicts**, not flat fields. Access via `data["memory"]["total"]`, not `data["maxmem"]`. The `loadavg` field is an **array of strings**, not floats — always cast with `float()`. See `references/api-data-structures.md` for the full breakdown of response shapes and safe parsing patterns.
- The `/nodes/{node}/zfs` endpoint may return `null`; use `/nodes/{node}/disks/zfs` instead for ZFS pool details including vdev and scan status.
- Telegram delivery can fail if bot token or chat_id is invalid or bot isn't added to the chat; verify via getMe/getChat endpoints before enabling delivery.
- TLS verification: prefer verified TLS in production; avoid `-k` in curl for production deployments.
- If you want to pull host-level audit data, ensure SSH keys are in place and Proxmox allows SSH key-based access.

## Examples
- Test endpoints manually (replace values):
  curl -k -s -H "Authorization: PVEAPIToken=root@pam!proxmox_token=TOKEN" "https://192.168.1.55:8006/api2/json/version"
- Fetch node inventory:
  curl -k -s -H "Authorization: PVEAPIToken=root@pam!proxmox_token=TOKEN" "https://192.168.1.55:8006/api2/json/nodes"
- Fetch qemu list for a node:
  curl -k -s -H "Authorization: PVEAPIToken=root@pam!proxmox_token=TOKEN" "https://192.168.1.55:8006/api2/json/nodes/pve/qemu"
- Fetch cluster resources (includes stopped VMs):
  curl -k -s -H "Authorization: PVEAPIToken=root@pam!proxmox_token=TOKEN" "https://192.168.1.55:8006/api2/json/cluster/resources"

## References
- `references/api-endpoints.md` — quick-endpoint guide and concrete curl examples.
- `references/proxmox-status-dashboard.md` — HTML dashboard generation from `pvesh` data for visual VM/node status overview.
- `references/api-data-structures.md` — exact response shapes, type quirks (nested memory dict, string loadavg, fraction CPU), and safe parsing patterns for every endpoint.
- `scripts/proxmox_system_report.py` — statically re-runnable comprehensive system report generator (version, node status, storage, VMs, disks, ZFS, RRD metrics, subscription). Outputs a formatted plain-text report to stdout. Usage: `python3 scripts/proxmox_system_report.py`