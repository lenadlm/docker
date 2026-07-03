#!/usr/bin/env bash
set -euo pipefail
script="$HOME/.hermes/scripts/lily_network_report.sh"
if [[ -x "$script" ]]; then
  bash -e "$script" 2>&1 | tee -a /var/log/lily_network_report_cron.log
else
  echo "Lily network report script not found or not executable" >&2
  exit 1
fi
