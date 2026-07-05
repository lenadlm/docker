# Home Assistant OS — Update via Proxmox Guest Agent

## Overview

HA OS (VM 115, 192.168.1.123) is a Proxmox VM running Home Assistant Operating System. It has **no SSH** by default — the standard SSH addon is available but the guest agent is the primary remote access path.

## Quick Reference

```
Core:    /usr/bin/ha core info         →  ha core update
OS:      /usr/bin/ha os info           →  ha os update
Supervisor:  /usr/bin/ha supervisor info  →  ha supervisor update
Jobs:    /usr/bin/ha jobs info       (check running tasks)
Health:  /usr/bin/ha supervisor info | grep healthy
```

## Update Procedure

### 1. Check Current Versions

```bash
# From Proxmox host
qm guest exec 115 -- /usr/bin/ha core info
qm guest exec 115 -- /usr/bin/ha os info
qm guest exec 115 -- /usr/bin/ha supervisor info
```

Parse key fields from the JSON output:
- `version` / `version_latest` — current and available version
- `update_available: true/false`
- `healthy: true/false`

### 2. Update Core

```bash
qm guest exec 115 -- timeout 300 /usr/bin/ha core update
```

**Expected behavior**: The command will likely time out (the Docker image for the new version takes several minutes to download). This is normal — the job continues running inside the VM.

### 3. Track Download Progress

```bash
# Poll the job manager until the progress shows done
qm guest exec 115 -- /usr/bin/ha jobs info
```

Watch for:
- `name: home_assistant_core_update` — progress climbs from 0→100 over ~10-20 minutes
- `name: docker_interface_update` — sub-task that downloads layers
- When `done: true` and `jobs: []` appears, the update is complete

### 4. Verify Core Update

```bash
qm guest exec 115 -- /usr/bin/ha core info
# Confirm: version=2026.6.4, update_available=false
```

### 5. Update HA OS

```bash
qm guest exec 115 -- timeout 600 /usr/bin/ha os update
```

This also downloads an OS image and may time out. Poll `ha jobs info` to track the `os_manager_update` job.

The OS upgrade uses a dual-boot slot system:
- Slot A: previous version
- Slot B: new version (becomes `booted` after automatic reboot)

### 6. Verify Final State

```bash
# Core
qm guest exec 115 -- /usr/bin/ha core info | grep 'version:'
# OS
qm guest exec 115 -- /usr/bin/ha os info | grep -E 'version:|update_available' | head -2
# Supervisor health
qm guest exec 115 -- /usr/bin/ha supervisor info | grep -E 'healthy|update_available'
# Web UI
curl -s -o /dev/null -w '%{http_code}' http://192.168.1.123:8123/
```

### 7. Addon Updates (Optional)

Addons are updated individually or via the HA Web UI. The Terminal & SSH addon is often worth keeping updated for emergency access.

## Typical Timings

| Step | Time | Notes |
|------|------|-------|
| Core update trigger | Instant | Times out, runs in background |
| Core download | 10-20 min | Depends on image size and bandwidth |
| OS update trigger | Instant | Times out, runs in background |
| OS download + apply | 5-10 min | Includes automatic reboot |
| Total | 20-30 min | Mostly waiting for downloads |

## Pitfalls

- **Don't retry too fast**: If a previous `ha core update` timed out, retrying immediately gives "Another job is running for job group home_assistant_core". Wait for the job to complete; poll `ha jobs info`.
- **Absolute paths required**: `qm guest exec` runs without a full PATH. Always use `/usr/bin/ha` not just `ha`.
- **No graceful shutdown**: HA OS updates reboot automatically. Don't interrupt the OS update mid-flight.
- **Addons unaffected**: Core/OS updates don't affect installed addon versions. Update addons separately.
- **Web UI may be briefly unavailable** during the core container restart after download completes.