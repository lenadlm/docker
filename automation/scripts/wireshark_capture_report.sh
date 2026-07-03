#!/bin/bash
set -euo pipefail
REPORT_DIR="/mnt/shared/tmp"
PCAP="$REPORT_DIR/wireshark_capture.pcap"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
REPORT_PATH="$REPORT_DIR/wireshark_report_${TIMESTAMP}.txt"

iface=$(ip -o link show up | awk -F': ' '/state UP/ && $2 != "lo" {print $2; exit}')
if [ -z "$iface" ]; then
  iface="eth0"
fi

echo "Interface: $iface" > "$REPORT_PATH"

# Capture 60 seconds (requires sudo)
sudo tshark -i "$iface" -a duration:60 -w "$PCAP" 2>> "$REPORT_PATH".log

# Analyze capture
PROTOS=$(tshark -r "$PCAP" -q -z io,phs)
SRC=$(tshark -r "$PCAP" -Y "ip" -T fields -e ip.src | sort | uniq -c | sort -nr | head -n 5)
DST=$(tshark -r "$PCAP" -Y "ip" -T fields -e ip.dst | sort | uniq -c | sort -nr | head -n 5)
TCP_P=$(tshark -r "$PCAP" -Y "tcp" -T fields -e tcp.dstport | sort | uniq -c | sort -nr | head -n 5)
UDP_P=$(tshark -r "$PCAP" -Y "udp" -T fields -e udp.dstport | sort | uniq -c | sort -nr | head -n 5)

cat > "$REPORT_PATH" <<EOF
=== WIRESHARK CAPTURE SUMMARY ===
Interface: $iface
Duration: 60s
Protocol distribution:
$PROTOS
Top sources:
$SRC
Top destinations:
$DST
Top TCP ports:
$TCP_P
Top UDP ports:
$UDP_P
EOF

# Send to Telegram if credentials provided
TELEGRAM_BOT_TOKEN="${TELEGRAM_BOT_TOKEN:-}"
TELEGRAM_CHAT_ID="${TELEGRAM_CHAT_ID:-}"
if [[ -n "$TELEGRAM_BOT_TOKEN" && -n "$TELEGRAM_CHAT_ID" ]]; then
  PAYLOAD=$(sed ':a;N;$!ba;s/\n/\\n/g' "$REPORT_PATH")
  curl -sS -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" -H "Content-Type: application/json" -d "{\"chat_id\":\"$TELEGRAM_CHAT_ID\",\"text\":\"$PAYLOAD\"}"
else
  echo "Telegram credentials not set; skipping Telegram delivery." >> "$REPORT_PATH"
fi

# Cleanup: delete capture and report per request
rm -f "$PCAP"
rm -f "$REPORT_PATH"
echo "Capture complete. Files removed as requested." 1>&2

exit 0
