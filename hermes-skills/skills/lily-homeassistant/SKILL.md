---
name: lily-homeassistant
description: Home Assistant API access for the Lily network engineer agent. Provides REST API client for monitoring, entity queries, and service calls.
version: 1.0.0
author: Leo
license: MIT
metadata:
  hermes:
    tags: [HomeAssistant, HA, IoT, API]
    related_skills: ["lily-network-engineer"]
---

# Lily Home Assistant Integration

## Overview
The Lily network agent can query and control Home Assistant via the REST API. This is on-demand only (not part of hourly recon reports).

## Setup

### Token
- Stored at: `/mnt/shared/tmp/ha_api_token` (chmod 600)
- Source: HA Profile → Long-Lived Access Tokens → Create Token
- Validity: long-lived (typically years)
- URL: `http://192.168.1.214:8123` (update if HA IP changes)

### Module
- Script: `/mnt/shared/tmp/lily_homeassistant.py`
- Import: `from lily_homeassistant import HomeAssistant`
- CLI: `python3 /mnt/shared/tmp/lily_homeassistant.py <command>`

## CLI Commands

```bash
# Health check with full config
python3 /mnt/shared/tmp/lily_homeassistant.py health

# Status summary (one-liner for recon reports)
python3 /mnt/shared/tmp/lily_homeassistant.py status

# List entities (optionally filter by domain)
python3 /mnt/shared/tmp/lily_homeassistant.py entities
python3 /mnt/shared/tmp/lily_homeassistant.py entities sensor

# Entity summary by domain with state counts
python3 /mnt/shared/tmp/lily_homeassistant.py summary

# Check specific entity state
python3 /mnt/shared/tmp/lily_homeassistant.py state sensor.front_door

# Call a service
python3 /mnt/shared/tmp/lily_homeassistant.py service media_player.turn_off media_player.lg_webos_tv

# Switch TV app/source (LG WebOS)
python3 /mnt/shared/tmp/lily_homeassistant.py service media_player.select_source media_player.lg_webos_tv '{"source":"YouTube"}'

# Call service without entity_id
python3 /mnt/shared/tmp/lily_homeassistant.py service notify.send_message '{"message": "Hello"}'
```

## Python API

```python
from lily_homeassistant import HomeAssistant

ha = HomeAssistant()

# Quick status for recon reports
ha.recon_status()        # dict: {status, version, location, component_count, ...}
ha.format_report()       # formatted string for log/report inclusion

# Health
ha.api_running()         # True/False
ha.health_check()        # (ok, config_dict)

# Entities
ha.list_entities()           # all entities
ha.list_entities("sensor")   # filtered by domain
ha.get_entity_state("switch.lights")
ha.entity_summary()      # dict of domains with counts and state breakdowns

# Control
ha.set_entity_state("input_boolean.guest_mode", "on")
ha.call_service("switch", "turn_off", "switch.adguard_home_protection")
ha.call_service_direct("notify.send_message", {"message": "Hello"})
ha.call_service("media_player", "turn_off", "media_player.lg_webos_tv")
```

## Known Limitations

### LG WebOS TV
- **media_player.turn_off works**, but **turn_on does not** — the TV's network interface sleeps when powered off.
- WoL magic packets are required for power-on. The MAC in ARP (when HA can see it) may be a virtual/container MAC, not the physical NIC.
- To enable reliable on/off: enable "Mobile TV On" in LG settings or configure Wake-on-LAN integration in HA with the physical MAC.
- When unavailable, HA reports state as `"unavailable"`.

### AdGuard Integration
- Switches for protection, filtering, parental control, safe search, safe browsing, query log are available.
- Useful for DNS troubleshooting: Lily can toggle protection during network diagnostics.

## Media Player Tips

### Switching Apps/Sources (LG WebOS TV)
- Use `media_player.select_source` service with `{\"source\": \"App Name\"}`.
- Source names must match exactly from `source_list` attribute.
- Example to open YouTube: `ha.call_service(\"media_player\", \"select_source\", \"media_player.lg_webos_tv\", {\"source\":\"YouTube\"})`
- To discover available sources: check `attributes.source_list` from `ha.get_entity_state()` or CLI: `python3 /mnt/shared/tmp/lily_homeassistant.py state media_player.lg_webos_tv` and parse the output.
- Note: `turn_on` does not work via network; TV must be manually powered or use WoL integration.

## Filesystem Access via Proxmox Console

When SSH is disabled on the Home Assistant VM (port 22 closed), you can still inspect its filesystem using Proxmox's `qm guest exec` command. This is useful for retrieving configuration files (e.g., `configuration.yaml`) or debugging.

### Prerequisites
- Proxmox host credentials: `root@192.168.1.55`, password `P!thag0ras`
- Home Assistant VM ID: `109`

### Step‑by‑Step Exploration

1. **Check SSH connectivity** (should fail):
   ```bash
   sshpass -p '47454745' ssh -o StrictHostKeyChecking=no leo@192.168.1.123 'echo test'
   ```

2. **Try API endpoint** (usually 404):
   ```bash
   curl -s -H "Authorization: Bearer $HA_TOKEN" "http://192.168.1.123:8123/api/config/configuration.yaml"
   ```

3. **Use Proxmox console to list root directory**:
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm guest exec 109 -- ls -la /"
   ```

4. **Examine mount points**:
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm guest exec 109 -- ls -la /mnt"
   ```
   Typical output:
   ```
   total 33
   drwxr-xr-x    6 root     root            96 Feb 12 17:10 .
   drwxr-xr-x   15 root     root           291 Feb 12 18:46 ..
   drwxr-xr-x    3 root     root         16384 Jan  1  1970 boot
   drwxr-xr-x    2 root     root            27 Feb 12 17:10 config
   drwxr-xr-x    6 root     root          4096 Mar  6 06:00 data
   drwxr-xr-x    6 root     root          1024 Mar  6 06:00 overlay
   ```

5. **Check config directory** (often empty in this mount):
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm guest exec 109 -- ls -la /mnt/config"
   ```

6. **Inspect overlay filesystem**:
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm guest exec 109 -- ls -la /mnt/overlay"
   ```

7. **Look for Home Assistant data** (may be on a separate data disk):
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm guest exec 109 -- find /mnt -name 'configuration.yaml' 2>/dev/null | head -5"
   ```

### If Configuration File Is Not Found
The Home Assistant configuration is often stored on a dedicated data disk that may not be mounted at `/mnt`. To locate it:

1. **List additional disks attached to VM 109** via Proxmox web UI or CLI:
   ```bash
   sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
     "qm config 109 | grep -E 'scsi|virtio|ide'"
   ```

2. **Mount the data disk** (if identified) using Proxmox's `qm mount` command, then repeat the `qm guest exec` steps on the new mount point.

### Quick Copy to Local Machine
Once the file path is known, copy it locally:
```bash
sshpass -p 'P!thag0ras' ssh -o StrictHostKeyChecking=no root@192.168.1.55 \
  "qm guest exec 109 -- cat /path/to/configuration.yaml" > ~/homeassistant_configuration.yaml
```

### Notes
- The `qm guest exec` command runs inside the VM’s guest agent; ensure the guest agent is installed and running in the Home Assistant OS.
- If the guest agent is missing, you may need to mount the VM’s disk directly on the Proxmox host.
- This method is read‑only; modifications should be done via the Home Assistant UI or API where possible.

## Entity Overview (as of first scan)
- 8 switches (AdGuard, Transmission)
- 3 media players (LG WebOS TV active, 2 Plex clients)
- 134 sensors (weather, Proxmox, Radarr, Plex, Tautulli, etc.)
- 13 binary sensors
- 58 buttons (mostly unavailable)
- 7 update entities

## Maintenance
- Token rotation: update `/mnt/shared/tmp/ha_api_token` if HA token is revoked.
- IP change: update `HOMEASSISTANT_URL` default in the script or set `HA_URL` env var.

## Monitoring and Diagnostics

### Network Reachability Checks
When Home Assistant appears unreachable, perform these checks before assuming service failure:

```bash
# Check if host is reachable
ping -c 2 192.168.1.214

# Check ARP entry (incomplete means host offline)
arp -a | grep 192.168.1.214

# Scan port 8123 with nmap (use -Pn if host blocks ping)
nmap -p 8123 192.168.1.214

# Test API directly with curl (timeout 2 seconds)
curl -s -f -m 2 http://192.168.1.214:8123/api/
```

### Fallback Version Checking
If the API is unavailable, fetch the latest Home Assistant Core release from GitHub:

```bash
curl -s https://api.github.com/repos/home-assistant/core/releases/latest | grep '"tag_name"' | head -1
```

### Scheduled Cron Job Reporting
For automated health checks, include:
- Service reachability status (UP/DOWN)
- Network connectivity diagnostics (ping, ARP, port scan)
- Latest available version (GitHub fallback)
- Recommendations for recovery

Example report structure:
```
**Home Assistant Core Update Status Check**
- 🔴 Service Status: Home Assistant is unreachable at http://192.168.1.214:8123
- 📊 Update Status: Cannot check for updates — API unavailable
- 🛠️ Recommended Actions: Verify server power, check network connectivity, update IP if changed
```
