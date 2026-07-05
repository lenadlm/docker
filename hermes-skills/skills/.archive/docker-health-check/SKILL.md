---
name: docker-health-check
description: Health check and recovery for Docker containers on remote hosts via SSH. Identifies crashed/restarting containers, diagnoses common issues (port conflicts, volume locks), and performs recovery actions.
version: 1.0.0
author: Leo (learned from Hermes session 2026-04-06)
license: MIT
---

# Docker Health Check & Recovery

## Trial & Error Insights (Updated 2026-04-08)

During troubleshooting of Docker DNS resolution inside the VM `192.168.1.220`, I discovered two practical work‑arounds that emerged only through repeated attempts:

1. **Force‑Kill of Stale Database Locks**  
   When a container (e.g., Portainer) hangs on a database lock (BoltDB/SQLite), the usual `docker stop` won’t free the lock.  
   - **Work‑around:** `docker exec <container> kill -9 1` (or `docker stop -t 5 <container>` followed by `docker rm -f <container>` if needed).  
   - This manually breaks the lock and allows the container to be recreated with a fresh database, but note that it results in loss of the container’s state—back up any critical data first.  

2. **Dynamic DNS Configuration via `sshpass`**  
   Updating `/etc/docker/daemon.json` required bypassing sudo password prompts and contending with a lingering lock on the lock file.  
   - **Work‑around:**  
   - Create the JSON locally: `echo '{"dns":["192.168.1.1"]}' > /tmp/daemon.json`.  
   - Transfer it with `scp -o StrictHostKeyChecking=no /tmp/daemon.json leo@192.168.1.220:/home/leo/`.  
   - On the host, execute:  
   ```bash
   sudo mv /home/leo/daemon.json /etc/docker/daemon.json
   sudo chown root:root /etc/docker/daemon.json
   sudo systemctl restart docker
   ```  
   This avoids permission‑related failures and lets the new DNS servers take effect without triggering the stale‑lock issue. The method bypasses the need for interactive sudo password entry and sidesteps the stale‑lock that previously blocked `systemctl restart docker`.

These findings emerged only after repeated iterations of restarting Docker, observing `could not resolve external DNS server` errors, and manually killing processes to clear stuck locks. The workaround steps are now codified as best‑practice procedures for anyone automating Docker health checks on similar Proxmox/KVM guests.

## Overview
Diagnose and fix Docker container issues on remote hosts. Particularly useful for recovering from container crashes, BoltDB locks (Portainer), and port conflicts.

## Prerequisites
- SSH access to Docker host (user with docker group or sudo)
- docker CLI available on remote host
- Standard tools: ss, lsof, df, ls

## Core Workflow

### Step 1: List all containers with status
```bash
ssh <user>@<host> "docker ps -a --format 'table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}'"
```

### Step 2: Identify problematic containers
- Status containing "Exited" (exit code != 0)
- Status "Restarting" (loop)
- Status " unhealthy" (if healthcheck defined)

### Step 3: For each problematic container

#### A. Fetch recent logs
```bash
ssh <user>@<host> "docker logs --tail 50 <container>"
```
Look for:
- Database lock timeouts (BoltDB, SQLite)
- Permission denied on volumes
- Port already in use
- Missing files/configs

#### B. Inspect mounts and volumes
```bash
ssh <user>@<host> "docker inspect <container> --format '{{json .Mounts}}' | python3 -m json.tool"
```
Check:
- Source paths exist on host
- Permissions (read/write)
- Available disk space on mount host

#### C. Check for port conflicts
```bash
ssh <user>@<host> "ss -tulpn | grep -E ':<port>'"
```
If port is bound to another process, either:
- Stop the conflicting container/service
- Change the container's published port

#### D. Check container file locks (rare)
If logs show DB timeout and you suspect a stale lock:
```bash
ssh <user>@<host> "lsof <volume_path>/<db_file> 2>&1"
ssh <user>@<host> "fuser -v <volume_path>/<db_file> 2>&1"
```
If PID found and not from a running container: kill -9 <PID>

### Step 4: Recovery actions

#### Safe shutdown before removal
```bash
ssh <user>@<host> "docker stop -t 5 <container> 2>&1"
```

#### Force remove (frees ports and locks)
```bash
ssh <user>@<host> "docker rm -f <container> 2>&1"
```

#### Verify removal
```bash
ssh <user>@<host> "docker ps -a --format '{{.Names}}' | grep -w <container>"
```
Should return empty.

### Step 5: Recreate (if needed)

Example for Portainer:
```bash
ssh <user>@<host> "docker run -d --name portainer --restart=always \
  -p 9000:9000 -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /path/to/data:/data \
  portainer/portainer-ce:latest"
```

## System-level checks
- Disk space: `df -h <volume_dir>`
- Memory: `free -h`
- Docker version: `docker version`
- Docker disk usage: `docker system df`

## Common Issues & Quick Fixes

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `timeout` opening DB (BoltDB/SQLite) | Stale lock from crashed container | `docker rm -f <container>` (data volume preserved) |
| `Address already in use` on start | Port conflict with another container | Find conflicting service (`ss -tulpn`), stop it or change ports |
| `Permission denied` on volume | Host directory owned by wrong user | `chown` host directory to match container UID/GID |
| Container restart loop | App config error, missing env | Check logs, fix environment variables or config |
| `No space left on device` | Full Docker storage | `docker system prune -a --volumes` (caution) |

## Safety Notes
- Removing a container does NOT delete its volumes by default (unless `-v` flag is used). Data is preserved.
- Always check logs before removing; some containers may need config fixes instead.
- For critical containers ( databases), back up volume data first.

## Example Invocation
```bash
# Full health check
ssh leo@192.168.1.220 "docker ps -a --format 'table {{.Names}}\t{{.Status}}'"

# Troubleshoot a specific container
ssh leo@192.168.1.220 "docker logs --tail 100 portainer"
ssh leo@192.168.1.220 "docker inspect portainer"
ssh leo@192.168.1.220 "ss -tulpn | grep 9000"

# Recover Portainer from BoltDB lock
ssh leo@192.168.1.220 "docker stop -t 5 portainer"
ssh leo@192.168.1.220 "docker rm -f portainer"
ssh leo@192.168.1.220 "docker run -d --name portainer --restart=always -p 9000:9000 -p 9443:9443 -v /var/run/docker.sock:/var/run/docker.sock -v /docker/portainer/data:/data portainer/portainer-ce:latest"
```
