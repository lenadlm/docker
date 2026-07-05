#!/bin/bash
# Lily: tshark timed capture + analysis + Telegram report + cleanup
# Usage: sudo bash tshark_capture_report.sh [duration_seconds]
# Default: 60 seconds
set -euo pipefail

# Auto-install tshark if missing (non-interactive)
if ! command -v tshark &>/dev/null; then
  echo "tshark not found. Installing..." >&2
  printf 'y\n' | sudo apt-get install -y tshark 2>/dev/null || \
    echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections && \
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y tshark
fi

DURATION="${1:-60}"
PCAP="/mnt/shared/tmp/tshark_capture.pcap"
REPORT="/mnt/shared/tmp/tshark_report.txt"

# Auto-detect active interface (skip loopback)
IFACE=$(ip -o link show up | grep -v "lo" | head -n1 | awk -F': ' '{print $2}')
if [ -z "$IFACE" ]; then
  echo "ERROR: no active non-loopback interface found" >&2
  exit 1
fi

echo "=== TSHARK CAPTURE REPORT ===" > "$REPORT"
echo "Interface: $IFACE" >> "$REPORT"
echo "Duration: ${DURATION}s" >> "$REPORT"
echo "" >> "$REPORT"

# Capture
sudo tshark -i "$IFACE" -a duration:"$DURATION" -w "$PCAP" 2>/dev/null

echo "=== Protocol Hierarchy ===" >> "$REPORT"
tshark -r "$PCAP" -q -z io,phs 2>/dev/null >> "$REPORT"
echo "" >> "$REPORT"

echo "=== Top Source IPs ===" >> "$REPORT"
tshark -r "$PCAP" -Y ip -T fields -e ip.src 2>/dev/null | sort | uniq -c | sort -nr | head -5 >> "$REPORT"
echo "" >> "$REPORT"

echo "=== Top Destination IPs ===" >> "$REPORT"
tshark -r "$PCAP" -Y ip -T fields -e ip.dst 2>/dev/null | sort | uniq -c | sort -nr | head -5 >> "$REPORT"
echo "" >> "$REPORT"

echo "=== Top TCP Ports ===" >> "$REPORT"
tshark -r "$PCAP" -Y tcp -T fields -e tcp.dstport 2>/dev/null | sort | uniq -c | sort -nr | head -5 >> "$REPORT"
echo "" >> "$REPORT"

echo "=== Top UDP Ports ===" >> "$REPORT"
tshark -r "$PCAP" -Y udp -T fields -e udp.dstport 2>/dev/null | sort | uniq -c | sort -nr | head -5 >> "$REPORT"
echo "" >> "$REPORT"

echo "=== Capture Size ===" >> "$REPORT"
ls -lh "$PCAP" >> "$REPORT"

# Output to stdout for agent to capture
cat "$REPORT"

# Cleanup
rm -f "$PCAP" "$REPORT"