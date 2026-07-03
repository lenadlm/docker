#!/bin/bash
set -euo pipefail
OUTDIR="/home/leo/recon"
LIVE="$OUTDIR/live_hosts.txt"
INV="$OUTDIR/inventory.tsv"
KEYS="$OUTDIR/known_hosts_192.168.1.txt"
mkdir -p "$OUTDIR"
: > "$LIVE"; : > "$INV"; : > "$KEYS"

# Header for inventories
echo -e "ip\treachable\thostname (heuristic)\tssh_open (keyscan)" > "$INV"

# Step 1: Ping sweep
echo "Starting ping sweep 192.168.1.1-254..." >> "$OUTDIR/scan.log" 2>&1
LIVE_COUNT=0
for i in $(seq 1 254); do
  ip="192.168.1.$i"
  if ping -c 1 -W 1 "$ip" >/dev/null 2>&1; then
    echo "$ip" >> "$LIVE"
    LIVE_COUNT=$((LIVE_COUNT+1))
  fi
done
echo "Ping sweep complete. Live hosts: $LIVE_COUNT" >> "$OUTDIR/scan.log" 2>&1

# Step 2: SSH keyscan for live hosts
echo "Starting SSH keyscan for live hosts..." >> "$OUTDIR/scan.log" 2>&1
if [ -s "$LIVE" ]; then
  while IFS= read -r ip; do
    if [ -n "$ip" ]; then
      KEY=$(ssh-keyscan -T 5 "$ip" 2>/dev/null | head -n1 || true)
      if [ -n "$KEY" ]; then
        echo "$ip\tYES\t$KEY" >> "$INV"
        echo "$KEY" >> "$KEYS"
      else
        echo "$ip\tNO\t" >> "$INV"
      fi
    fi
  done < "$LIVE"
else
  echo "No live hosts detected; skipping SSH keyscan." >> "$OUTDIR/scan.log" 2>&1
fi

# Step 3: Summary
TOTAL=$(wc -l < "$LIVE" 2>/dev/null || echo 0)
echo "Summary: live_hosts=$TOTAL" >> "$OUTDIR/scan.log" 2>&1

echo "Recon complete." > "$OUTDIR/scan_complete.flag" 2>&1
