#!/usr/bin/env bash
set -euo pipefail

# Config / credentials
TELEGRAM_BOT_TOKEN="269470...Qd6g"
TELEGRAM_CHAT_ID="CHAT_ID_REDACTED"
LOG_DIR="${LOG_DIR:-/mnt/shared/tmp}"
INVENTORY_FILE="${HOME}/.hermes/network_inventory.txt"
SCRIPT_START_TS="$(date '+%Y-%m-%d %H:%M:%S')"
REPORT_FILE="${LOG_DIR}/lily_network_report_${SCRIPT_START_TS// /_}.log"
DOCKER_HOST="192.168.1.220"
DOCKER_USER="leo"

# Ensure log dir exists
mkdir -p "$LOG_DIR"

log() {
  echo -e "$1" | tee -a "$REPORT_FILE"
}

log_header() {
  log "=============================================="
  log "LILY NETWORK REPORT"
  log "Generated: ${SCRIPT_START_TS}"
  log "=============================================="
}

get_hostname() {
  local ip="$1"
  local host=""
  # Try local inventory first
  if [ -f "$INVENTORY_FILE" ]; then
    host=$(grep -w "$ip" "$INVENTORY_FILE" | awk '{print $2}' | head -n1)
  fi
  # Fallback to system resolver
  if [ -z "$host" ]; then
    host=$(getent hosts "$ip" | awk '{print $2}' | head -n1)
  fi
  echo "${host:-Unknown}"
}
vendor_from_mac() {
  local mac="$1"
  # Skipping OUI lookup for speed in this version
  echo "Unknown"
}
get_latency_ms() {
  local ip="$1"
  if ping -c 2 -W 1 "$ip" 2>/dev/null | head -n1 >/dev/null; then
    local latency
    latency=$(ping -c 2 -W 1 "$ip" | awk -F'/' '/min\/avg/ {print $5}')
    echo "$latency"
  else
    echo "-"
  fi
}

discover_hosts() {
  local discovery_lines=()
  if command -v arp-scan >/dev/null 2>&1; then
    local arp_out
    arp_out=$(sudo arp-scan -l 2>/dev/null | tail -n +3 | head -n -3)
    while IFS= read -r line; do
      [[ $line =~ ^([0-9]{1,3}\.){3}[0-9]{1,3} ]] || continue
      local ip
      local mac
      local host
      ip=$(echo "$line" | awk '{print $1}')
      mac=$(echo "$line" | awk '{print $2}')
      host=$(get_hostname "$ip")
      discovery_lines+=("$ip|$mac|$host")
    done <<< "$arp_out"
  fi
  echo "${discovery_lines[@]}" | tr ' ' '\n'
}
 docker_remote_report() {
  log ""
  log "Docker Status @ $DOCKER_HOST:"
  if ping -c 1 -W 1 "$DOCKER_HOST" >/dev/null 2>&1; then
    # Attempt to get docker status via SSH using existing keys
    local docker_out
    docker_out=$(ssh -o ConnectTimeout=5 -o StrictHostKeyChecking=no -o BatchMode=yes "${DOCKER_USER}@${DOCKER_HOST}" "docker ps --format '{{.Names}}\t{{.Status}}\t{{.Image}}'" 2>/dev/null || true)
    
    if [ -n "$docker_out" ]; then
      log "$docker_out"
    else
      log "  [?] Docker service not responding or no containers running."
    fi
  else
    log "  [!] Docker host unreachable via Ping."
  fi
}

build_report() {
  log_header
  log "Summary:"
  local lines
  lines=$(discover_hosts)
  local count=0
  if [ -n "$lines" ]; then
    IFS=$'\n' read -r -d '' -a arr <<< "$lines" || true
    count=${#arr[@]}
  fi
  log "Discovered devices: ${count}"
  log ""
  log "Device Table:"
  printf "%-15s %-18s %-15s %-10s\n" "IP Address" "MAC Address" "Hostname" "Latency" | tee -a "$REPORT_FILE"
  log "------------------------------------------------------------"
  if [ -n "$lines" ]; then
    IFS=$'\n' read -r -d '' -a arr <<< "$lines" || true
    for entry in "${arr[@]}"; do
      IFS='|' read -r ip mac host <<< "$entry"
      local latency
      latency=$(get_latency_ms "$ip")
      printf "%-15s %-18s %-15s %-10s\n" "$ip" "$mac" "$host" "${latency:--}" | tee -a "$REPORT_FILE"
    done
  fi
  log ""
  log "Health Checks:"
  local gw
  gw=$(ip route | awk '/default/ {print $3}')
  if [ -n "$gw" ]; then
    if ping -c 4 -W 1 "$gw" >/dev/null 2>&1; then
      log " Gateway ($gw): OK"
    else
      log " Gateway ($gw): Unreachable"
    fi
  fi
  if ping -c 2 -W 1 8.8.8.8 >/dev/null 2>&1; then
    log " Internet: OK"
  else
    log " Internet: FAIL"
  fi
  docker_remote_report
  log "=============================================="
}

build_report

# Send Telegram if configured
send_telegram_report() {
  if [[ -n "${TELEGRAM_BOT_TOKEN:-}" && -n "${TELEGRAM_CHAT_ID:-}" ]]; then
    if [[ -f "$REPORT_FILE" ]]; then
      local text
      text=$(sed 's/\x1b\[[0-9;]*m//g' "$REPORT_FILE" | tr '\n' '\n')
      # Truncate to Telegram limit (4096 chars)
      text="${text:0:4000}"
      curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
        --data-urlencode "chat_id=$TELEGRAM_CHAT_ID" \
        --data-urlencode "text=$text" >/dev/null 2>&1
    fi
  fi
}
send_telegram_report
