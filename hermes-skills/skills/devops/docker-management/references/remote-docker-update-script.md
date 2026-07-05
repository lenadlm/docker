# Remote Docker Stack Update Checking

## Problem
You need to periodically check a remote Docker host for container image updates, apply them if available, and detect whether the container was actually recreated (not just "pulled the same image again").

## Canonical Deployment Path
All docker-compose stacks under management should store their compose files at **`/mnt/shared/tmp/docker/`** on the Docker host (192.168.1.220). Each stack gets its own subdirectory if there are multiple stacks, or the compose file lives directly in `/mnt/shared/tmp/docker/` for a single-stack setup. This location replaces the previous `/docker/<app>/` convention.

## Approach
Use SSH to run a pull+up cycle on the remote host, then compare the container's `StartedAt` timestamp before and after to determine if a real update occurred.

## Script: `docker_update_check.sh`

This script lives at `~/.hermes/scripts/docker_update_check.sh` on the Hermes management host. It is invoked as a no_agent cron job.

```bash
#!/usr/bin/env bash
set -euo pipefail

DOCKER_HOST="192.168.1.220"
STACK_DIR="/mnt/shared/tmp/docker"
LOG_FILE="/mnt/shared/tmp/docker_updates.log"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

echo "[$(timestamp)] Starting Docker update check: $STACK_DIR"

result=$(ssh leo@"$DOCKER_HOST" bash -s <<'REMOTE_SCRIPT'
  set -euo pipefail
  cd /mnt/shared/tmp/docker

  # Record container start time BEFORE pull
  before_since=$(docker inspect --format '{{.State.StartedAt}}' netbootxyz 2>/dev/null || echo "unknown")

  # Pull latest images
  echo "=== PULL ==="
  docker compose pull 2>&1
  pull_exit=$?

  # Redeploy (only recreates if image changed)
  echo "=== UP ==="
  docker compose up -d 2>&1
  up_exit=$?

  # Record container start time AFTER
  after_since=$(docker inspect --format '{{.State.StartedAt}}' netbootxyz 2>/dev/null || echo "unknown")

  echo "=== STATUS ==="
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Image}}'

  # Determine if container was recreated
  if [ "$before_since" != "$after_since" ] && [ "$before_since" != "unknown" ]; then
    echo "UPDATED=true"
  else
    echo "UPDATED=false"
  fi

  exit $(( pull_exit | up_exit ))
REMOTE_SCRIPT
)

echo "$result"

if echo "$result" | grep -q "UPDATED=true"; then
  echo "Container was updated and recreated."
elif echo "$result" | grep -q "UPDATED=false"; then
  echo "No update needed — images already current."
fi
```

## Key Insights

1. **SSH heredoc env var trap**: Single-quoted heredocs (`<<'REMOTE_SCRIPT'`) do NOT expand local variables — they are literal text. If your script defines `STACK_DIR=/path` locally and the remote heredoc references `"$STACK_DIR"`, it will be **empty** on the remote. Fix by passing the variable as an SSH environment variable:

   ```bash
   # ❌ Broken — STACK_DIR is empty on remote
   result=$(ssh user@host bash -s <<'REMOTE_SCRIPT'
     cd "$STACK_DIR"   # empty!
   REMOTE_SCRIPT
   )

   # ✅ Fixed — pass explicitly
   result=$(ssh user@host "STACK_DIR=$STACK_DIR" bash -s <<'REMOTE_SCRIPT'
     cd "$STACK_DIR"   # defined by SSH env
   REMOTE_SCRIPT
   )

   # Alternative: expand locally (no quotes on heredoc delimiter)
   # BUT then every $ inside must be escaped
   result=$(ssh user@host bash -s <<REMOTE_SCRIPT
     cd "$STACK_DIR"   # expanded locally before sending
   REMOTE_SCRIPT
   )
   ```

   Pitfall hits hardest when `DOCKER_HOST` or `STACK_DIR` use `${VAR:-default}` syntax — the default is never applied on the remote.

2. **`docker compose pull` always says "Pulled"** even when the image hasn't changed. You cannot use pull output to detect updates.
2. **`StartedAt` comparison is reliable**: Docker only restarts the container with a new `StartedAt` when `docker compose up -d` actually recreates it. If the image is the same, the container continues running with the old timestamp.
3. **For multi-service stacks**, compare ALL containers' start times, not just one. Use the multi-stack variant below.
4. **The heredoc approach** (`bash -s <<'REMOTE_SCRIPT'`) is safer than quoting complex commands inline — no escaping nightmares.
5. **Compose file location independence**: The volume mounts in the compose file use absolute host paths. Moving the compose file does not affect them — they still resolve correctly as long as the target directories exist on the host.

## Script: Multi-Service Variant

For stacks with multiple services (e.g., 14 services), compare start times across ALL containers:

```bash
#!/usr/bin/env bash
set -euo pipefail

DOCKER_HOST="192.168.1.220"
STACK_DIR="/mnt/shared/tmp/docker"
LOG_FILE="/mnt/shared/tmp/docker_updates.log"

timestamp() { date '+%Y-%m-%d %H:%M:%S'; }

echo "[$(timestamp)] 🔍 Starting Docker update check: $STACK_DIR"

result=$(ssh leo@"$DOCKER_HOST" bash -s <<'REMOTE_SCRIPT'
  set -euo pipefail
  cd /mnt/shared/tmp/docker

  # Record ALL containers start times BEFORE pull
  docker inspect --format '{{.Name}}|{{.State.StartedAt}}' $(docker compose ps -q 2>/dev/null) 2>/dev/null | sort > /tmp/before_times.txt

  # Pull latest images
  echo "=== PULL ==="
  docker compose pull 2>&1
  pull_exit=$?

  # Redeploy (only recreates if image changed)
  echo "=== UP ==="
  docker compose up -d 2>&1
  up_exit=$?

  # Record ALL containers start times AFTER
  docker inspect --format '{{.Name}}|{{.State.StartedAt}}' $(docker compose ps -q 2>/dev/null) 2>/dev/null | sort > /tmp/after_times.txt

  echo "=== STATUS ==="
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Image}}'

  # Compare — if any container changed, an update happened
  if diff -q /tmp/before_times.txt /tmp/after_times.txt >/dev/null 2>&1; then
    echo "UPDATED=false"
  else
    echo "UPDATED=true"
  fi

  exit $(( pull_exit | up_exit ))
REMOTE_SCRIPT
)

echo "$result"

if echo "$result" | grep -q "UPDATED=true"; then
  echo "🔄 Stack was updated — containers recreated."
elif echo "$result" | grep -q "UPDATED=false"; then
  echo "✅ No update needed — images already current."
fi
```

Key difference: uses `docker compose ps -q` to get all container IDs in the stack, then compares timestamps across ALL of them using `diff` on sorted files. If any single container was recreated, the stack was updated.

## Cron Schedule (every 6 hours)

```bash
cronjob action=create \
  name="Docker Stack Auto-Update" \
  schedule="0 */6 * * *" \
  script=docker_update_check.sh \
  no_agent=true \
  deliver=origin
```

This runs at 00:00, 06:00, 12:00, 18:00 and delivers results directly to Telegram.

## Container Name Conflicts on Relocation

If you move a compose file from one directory to another (e.g., `/docker/netbootxyz/` → `/mnt/shared/tmp/docker/`), `docker compose up -d` will fail with:

```
Error response from daemon: Conflict. The container name "/netbootxyz" is already in use...
```

**Fix**: Stop and remove the old stack first, then deploy from the new location:
```bash
# From the old location (if compose file still exists)
cd /docker/netbootxyz && docker compose down

# Or force remove the container directly
docker rm -f netbootxyz

# Then deploy from new location
cd /mnt/shared/tmp/docker && docker compose up -d
```

## Moving Between Locations Without Data Loss

The volume mounts (e.g., `/docker/netbootxyz/config:/config`) use **absolute host paths**, not paths relative to the compose file. This means:
- Data survives moving the compose file — the volumes keep mounting the same host directories
- No need to copy or move volume data
- The old compose directory (e.g., `/docker/netbootxyz/`) can be removed after the stack is deployed from the new location

## Extending to Multiple Stacks

To check multiple stacks on the same host, modify the script to iterate over an array:

```bash
STACKS=("/mnt/shared/tmp/docker" "/mnt/shared/tmp/app2" "/mnt/shared/tmp/app3")

for stack in "${STACKS[@]}"; do
  echo "Checking $stack..."
  ssh leo@"$DOCKER_HOST" "cd $stack && docker compose pull && docker compose up -d"
done
```