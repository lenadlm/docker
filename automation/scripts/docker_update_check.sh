#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Docker Stack Auto-Updater
# Pulls latest images, redeploys if updates found
# Reports results via stdout (captured by cron delivery)
# ============================================================

DOCKER_HOST="${DOCKER_HOST:-192.168.1.220}"
STACK_DIR="/mnt/shared/tmp/docker"
LOG_FILE="/mnt/shared/tmp/docker_updates.log"

timestamp() {
  date '+%Y-%m-%d %H:%M:%S'
}

echo "[$(timestamp)] 🔍 Starting Docker update check: $STACK_DIR"

result=$(ssh leo@"$DOCKER_HOST" "STACK_DIR=$STACK_DIR" bash -s <<'REMOTE_SCRIPT'
  set -euo pipefail
  cd "$STACK_DIR"

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

# Check if update happened
if echo "$result" | grep -q "UPDATED=true"; then
  echo "🔄 Container was updated and recreated."
elif echo "$result" | grep -q "UPDATED=false"; then
  echo "✅ No update needed — images already current."
fi

# Log to file
{
  echo "[$(timestamp)] === Update Check ==="
  echo "$result"
  echo "----------------------------------------"
  echo ""
} >> "$LOG_FILE"

echo "[$(timestamp)] ✅ Docker update check complete."