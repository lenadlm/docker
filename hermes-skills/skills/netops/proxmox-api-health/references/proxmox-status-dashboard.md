# Proxmox Status Dashboard

Consolidated from `proxmox-status-dashboard` skill. Generates a standalone HTML dashboard for Proxmox VE node/VM status.

## Trigger
User asks for a visual overview or dashboard of Proxmox VMs and node resources.

## Procedure

### 1. Extract Proxmox Data
```bash
pvesh get /nodes --output-format json
pvesh get /cluster/resources --type vm --output-format json
```

### 2. Generate HTML Dashboard
Python script to parse JSON, write styled HTML with:
- "Last Updated" timestamp
- Color-coded status (green=running, red=stopped)

### 3. Serve Locally
```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

### 4. SSH Tunnel for Remote Access
```bash
ssh -L 8000:127.0.0.1:8000 user@proxmox-ip
```

## Pitfalls
- Keep styling minimal if many VMs
- Check port 8000 isn't already in use
- Do NOT bind to `0.0.0.0` on public interfaces
- Static snapshot — wrap in cron loop for pseudo-live data