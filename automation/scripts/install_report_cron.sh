#!/usr/bin/env bash
set -e
CRON_LINE="0 * * * * /bin/bash -lc '/home/leo/.hermes/scripts/lily_network_report.sh' > /dev/null 2>&1"
(crontab -l 2>/dev/null; echo "$CRON_LINE") | crontab -
echo "JOB_ID:$(date +%s)"