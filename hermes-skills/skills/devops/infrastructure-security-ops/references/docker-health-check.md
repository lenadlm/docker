# Docker Container Health Check & Recovery

Consolidated from `docker-health-check` skill. Diagnosis and recovery for Docker containers on remote hosts via SSH.

## Problematic Container Detection
- Status "Exited" (exit code != 0)
- Status "Restarting" (loop)
- Status "unhealthy" (healthcheck defined)

## Per-Container Diagnostic Steps

### A. Recent logs
```bash
ssh <user>@<host> "docker logs --tail 50 <container>"
```
Look for: DB lock timeouts (BoltDB, SQLite), Permission denied on volumes, Port already in use, Missing files/configs.

### B. Mounts and volumes
```bash
ssh <user>@<host> "docker inspect <container> --format '{{json .Mounts}}' | python3 -m json.tool"
```
Check: source paths exist, permissions, available disk space.

### C. Port conflicts
```bash
ssh <user>@<host> "ss -tulpn | grep -E ':<port>'"
```

### D. Stale DB locks (Portainer BoltDB)
```bash
ssh <user>@<host> "lsof <volume_path>/<db_file>"
ssh <user>@<host> "fuser -v <volume_path>/<db_file>"
```
If stale PID found: `kill -9 <PID>`

## Recovery Actions
```bash
# Safe shutdown
ssh <user>@<host> "docker stop -t 5 <container>"

# Force remove (frees ports and locks)
ssh <user>@<host> "docker rm -f <container>"

# Recreate Portainer:
ssh <user>@<host> "docker run -d --name portainer --restart=always \
  -p 9000:9000 -p 9443:9443 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v /docker/portainer/data:/data \
  portainer/portainer-ce:latest"
```

## DNS Fix for Docker on Proxmox/KVM Guests
When `systemctl restart docker` hangs on a stale lock:
```bash
echo '{"dns":["192.168.1.1"]}' > /tmp/daemon.json
scp /tmp/daemon.json leo@host:/home/leo/
ssh leo@host "sudo mv /home/leo/daemon.json /etc/docker/daemon.json && \
  sudo chown root:root /etc/docker/daemon.json && \
  sudo systemctl restart docker"
```

## Quick Reference Table
| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| `timeout` opening DB (BoltDB/SQLite) | Stale lock from crash | `docker rm -f <container>` |
| `Address already in use` | Port conflict | `ss -tulpn`, stop conflict |
| `Permission denied` on volume | Wrong UID/GID | `chown` host directory |
| Container restart loop | Config error / missing env | Check logs, fix env |
| `No space left on device` | Docker storage full | `docker system prune -a --volumes` |