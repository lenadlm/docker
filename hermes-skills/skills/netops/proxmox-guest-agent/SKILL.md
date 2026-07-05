---
name: proxmox-guest-agent
description: Class-level umbrella for running commands and managing VMs on Proxmox VE via QEMU guest agent (qm guest exec), serial console, and monitor. Covers timeout handling, progress polling for long-running internal jobs, and OS-specific quirks (HA OS, generic Linux).
---

# Proxmox QEMU Guest Agent Operations

Trigger when you need to run commands inside a Proxmox VM that lacks SSH access (HA OS, minimal distros, boot troubleshooting), or when the guest agent offers faster/cleaner access than SSH.

## Prerequisites

- VM must have `agent: enabled=1` in its Proxmox config
- `qemu-guest-agent` must be installed and running inside the VM
- The VM must be in `running` state

Enable if missing:
```bash
qm set <VMID> --agent enabled=1
# Then install inside VM: apt install qemu-guest-agent && systemctl enable --now qemu-guest-agent
```

## Core Commands

### Run a command and get output

```bash
qm guest exec <VMID> -- <command>
qm guest exec <VMID> -- bash -c 'complex command | grep something'
```

Returns JSON: `{ exitcode, exited, out-data, err-data, out-truncated, err-truncated }`

### Check if agent is alive

```bash
qm guest ping <VMID>
```

### Get agent info

```bash
qm guest exec <VMID> -- hostnamectl
qm guest exec <VMID> -- cat /etc/os-release
```

## Handling Long-Running Commands

### Problem

`qm guest exec` has a default timeout (~30-60s). If the command takes longer, the Proxmox side returns with only a `pid` — but the command **keeps running** inside the VM.

### Symptoms

```
timeout reached, returning pid
{ "pid": 6290 }
```

If you retry the same operation, you may get:
```
Error: Another job is running for job group home_assistant_core
```

### Solution: Poll internal job state

For VMs that track long-running operations internally (HA OS, supervisor-based systems):

```bash
# 1. Start the job (it will time out on guest exec)
qm guest exec <VMID> -- timeout 300 /usr/bin/ha core update

# 2. Poll the internal job manager
qm guest exec <VMID> -- /usr/bin/ha jobs info
```

Parse the JSON to extract:
- `jobs[].name` — which job is running
- `jobs[].done` — true/false
- `jobs[].progress` — percentage (float)
- `jobs[].child_jobs` — sub-tasks

### Tracking progress in a loop (bash)

```bash
while true; do
  result=$(qm guest exec <VMID> -- /usr/bin/ha jobs info)
  progress=$(echo "$result" | python3 -c "
import sys, json
data = json.load(sys.stdin)
out = data.get('out-data', '')
jobs = json.loads(out).get('jobs', [])
progress = None
done = None
for j in jobs:
    if 'home_assistant' in j.get('name', '') or 'core_update' in j.get('name', ''):
        progress = j.get('progress')
        done = j.get('done')
        print(f'progress={progress}, done={done}')
")
  echo "$progress"
  [[ "$progress" == *"done=true"* || "$progress" == *"done: true"* ]] && break
  sleep 30
done
```

## Serial Console Fallback

When guest agent is unavailable but serial is configured:

```bash
# Configure serial (one-time)
qm set <VMID> --serial0 socket

# Connect interactively (press Ctrl+O to exit)
qm terminal <VMID> --iface serial0
```

For non-interactive commands, use `expect`-style piping or QEMU monitor.

## QEMU Monitor

```bash
qm monitor <VMID>
# Then type QEMU commands like: info block, system_reset, etc.
```

## VM Config Operations

### Read config
```bash
qm config <VMID>
```

### Modify config
```bash
qm set <VMID> --vga std
qm set <VMID> --delete hostpci0
qm set <VMID> --serial0 socket
```

## Pitfalls

- **Timeout != failure**: `qm guest exec` timing out means the Proxmox-side connection timed out, but the command still runs inside the VM. Never assume a timeout means the operation failed — verify via internal state or polling.
- **Guest exec timeout cap**: The Proxmox host enforces its own timeout on the guest exec RPC. Long downloads (Docker images for HA OS updates) will always time out. Always pair with a polling strategy.
- **No `which` in guest exec**: `qm guest exec` runs in a minimal environment. Use absolute paths (`/usr/bin/ha`) instead of bare commands when the VM has a non-standard PATH.
- **Parallel jobs**: If a previous guest exec timed out, retrying may get "Another job is running". Check `<ha> jobs info` or equivalent first, or wait for the job to complete naturally.
- **JSON newlines in output**: The `out-data` field contains literal `\n` strings within the JSON. Parse carefully with `json.loads()` or `python3 -c` as shown above.

## References

- `references/haos-update.md` — Full HA OS update recipe via guest agent