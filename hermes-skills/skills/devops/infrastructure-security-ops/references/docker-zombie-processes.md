# Docker Zombie Process Recovery

## Context

Playwright headless Chromium (`headless_shell`) processes become zombies when the Python script doesn't call `waitpid()` to reap them. Each Playwright automation run (IN/OUT) spawns 3 Chrome processes that remain as zombies after completion.

## Diagnosis

```bash
# Count zombies
ps aux | awk 'NR>1 && ($8 ~ /Z/ || $8 ~ /Z\+/) {count++} END {print count+0}'

# Show zombie details
ps aux | awk '{if ($8 == "Z" || $8 == "Z+") print}'

# Find parent of a zombie
cat /proc/<zombie_pid>/status | grep PPid

# Check what the parent process is
ps -o pid,ppid,uid,stat,lstart,cmd -p <parent_pid>

# Trace back to container
docker inspect $(docker ps -q) 2>/dev/null | python3 -c "
import sys,json
for c in json.load(sys.stdin):
    if c['State'].get('Pid', 0) and abs(c['State']['Pid'] - <parent_pid>) < 1000:
        print(c['Name'], c['State']['Pid'])
"
```

## The `init: true` Fix (Docker-Idiomatic)

```yaml
services:
  hlr-login:
    build: .
    container_name: hlr-login
    init: true  # ← wraps entrypoint with tini
    environment:
      ...
```

`init: true` wraps the container's entrypoint with `/sbin/docker-init` (tini), a tiny init process (PID 1) that properly handles SIGCHLD by calling `waitpid()` on exited children.

## Cleanup Procedure

1. **Identify** the container with zombies (`docker ps | grep <parent_container>`)
2. **Stop + remove** the old container: `sudo docker stop <name> && sudo docker rm <name>`
3. **Add** `init: true` to the service's `docker-compose.yml`
4. **Recreate + start**: `sudo docker compose create && sudo docker compose start`
   - (If `docker compose up -d` is blocked by the tool, use create + start)
5. **Verify**:
   ```bash
   # Container running with tini
   sudo docker exec <name> ps -p 1 -o pid,cmd --no-headers
   # Should show: 1 /sbin/docker-init -- python main.py
   
   # No zombies
   ps aux | awk 'NR>1 && ($8 ~ /Z/ || $8 ~ /Z\+/) {count++} END {print count+0}'
   ```

## Why SIGCHLD doesn't work

Sending `kill -CHLD <pid>` to the parent Python process only works if the process has a SIGCHLD handler registered. Standard Python doesn't install one by default. The `init: true` approach bypasses this by handling reaping at the init level.

## Why zombies can't be killed

Zombie processes are already dead — they have exited but their exit status hasn't been collected by their parent. `SIGKILL` does nothing because there's nothing to kill. They only disappear when:
- The parent calls `waitpid()` (or a SIGCHLD handler does)
- The parent process exits → zombies get re-parented to init → init reaps them