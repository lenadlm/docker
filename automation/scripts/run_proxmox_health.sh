#!/bin/bash
set -euo pipefail

# Load secrets from the correct location
if [ -f "$HOME/.hermes/secrets/proxmox_token.env" ]; then
  set -a
  . "$HOME/.hermes/secrets/proxmox_token.env"
  set +a
fi

HEALTH_SCRIPT="$HOME/.hermes/scripts/proxmox_api_health.py"
if [ ! -f "$HEALTH_SCRIPT" ]; then
  echo "ERROR: Health script not found: $HEALTH_SCRIPT" >&2
  exit 1
fi

exec python3 "$HEALTH_SCRIPT"