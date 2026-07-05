#!/usr/bin/env bash
set -euo pipefail
# Docker Stack Auto-Updater (multi-service variant)
# Compares start times of ALL containers before/after pull
# Reports results via stdout (captured by cron delivery)
DOCKER_HOST="${DOCKER_HOST:-192.168.1.220}"
STACK_DIR="${STACK_DIR:-/mnt/shared/tmp/docker}"
LOG_FILE="${LOG_FILE:-/mnt/shared/tmp/docker_updates.log}"
timestamp() { date '+%Y-%m-%d %H:%M:%S'; }
echo "[$(timestamp)] 🔍 Starting Docker update check: $STACK_DIR"
result=$(ssh "$DOCKER_HOST" "STACK_DIR=$STACK_DIR" bash -s <<'REMOTE_SCRIPT'
  set -euo pipefail
  cd "$STACK_DIR"
  before_file=$(mktemp /tmp/before_XXXXXX.txt)
  after_file=$(mktemp /tmp/after_XXXXXX.txt)
  docker inspect --format '{{.Name}}|{{.State.StartedAt}}' $(docker compose ps -q 2>/dev/null) 2>/dev/null | sort > "$before_file"
  echo "=== PULL ==="
  docker compose pull 2>&1; pull_exit=$?
  echo "=== UP ==="
  docker compose up -d 2>&1; up_exit=$?
  docker inspect --format '{{.Name}}|{{.State.StartedAt}}' $(docker compose ps -q 2>/dev/null) 2>/dev/null | sort > "$after_file"
  echo "=== STATUS ==="
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Image}}'
  if diff -q "$before_file" "$after_file" >/dev/null 2>&1; then echo "UPDATED=false"; else echo "UPDATED=true"; fi
  rm -f "$before_file" "$after_file"
  exit $(( pull_exit | up_exit ))
REMOTE_SCRIPT
)
echo "$result"
if echo "$result" | grep -q "UPDATED=true"; then echo "🔄 Stack updated — containers recreated."
else echo "✅ No update needed — images already current."; fi
echo "[$(timestamp)] ✅ Docker update check complete."