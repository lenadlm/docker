---
name: proxmox-status-dashboard
description: Status report for Proxmox VE nodes and VMs rendered as a portable HTML dashboard.
---

# Proxmox Status Dashboard

Generates a standalone HTML dashboard reporting the real-time status of Proxmox VE nodes and virtual machines. Use this when a visual overview is preferred over raw CLI output.

## Trigger Conditions
- User asks for a "report", "status overview", or "dashboard" of Proxmox VMs.
- Need to monitor multiple VMs and node resources (CPU/Mem) simultaneously.

## Step-by-Step Procedure

1. **Extract Proxmox Data**
   Use `pvesh` to gather JSON data for nodes and cluster resources:
   ```bash
   pvesh get /nodes --output-format json
   pvesh get /cluster/resources --type vm --output-format json
   ```

2. **Generate HTML Dashboard**
   Use a Python script (via `execute_code`) to parse the JSON and write a styled HTML file. 
   
   *Tip: Include a "Last Updated" timestamp and color-coded status (e.g., green for 'running', red for 'stopped').*

3. **Serve Dashboard (Optional/Local)**
   To view the dashboard, serve it using Python's built-in HTTP server:
   ```bash
   python3 -m http.server 8000 --bind 127.0.0.1
   ```
   *Note: Using --bind 127.0.0.1 limits access to the local machine for security.*

4. **Remote Access**
   If the agent is on a remote host, instruct the user to use an SSH tunnel to view the dashboard:
   ```bash
   ssh -L 8000:127.0.0.1:8000 user@proxmox-ip
   ```

## Pitfalls & Best Practices
- **Large Files**: If there are dozens of VMs, the HTML table can become large. Keep styling minimal.
- **Port Conflicts**: Always check if port 8000 is in use before starting the server.
- **Security**: Do not bind `http.server` to `0.0.0.0` on public-facing interfaces without authentication/firewalling.
- **Stale Data**: This approach creates a static snapshot. For "live" data, wrap the generation/serving in a loop or cron job.
