---
name: lily-network-engineer
description: Persistent autonomous network engineer agent that performs network reconnaissance, maintenance, and troubleshooting with full network and sudo access.
version: 1.5.0
author: Leo
license: MIT
metadata:
  hermes:
    tags: [Network, Recon, Maintenance, Sudo, Autonomous]
    related_skills: []
---

# Lily - Network Engineer Agent

## Overview
Lily is a persistent, specialized network engineer agent with full network access and sudo privileges. She performs network reconnaissance, troubleshooting, maintenance, and security assessment tasks autonomously.

## Capabilities
- Network discovery and mapping (nmap, ping sweeps)
- Performance monitoring (mtr, ss, netstat, ip)
- Packet capture and analysis (tcpdump + tshark/Wireshark CLI)
- Timed packet capture with protocol analysis, top talkers, and Telegram delivery
- DNS resolution and troubleshooting (dig, nslookup, whois)
- Interface and routing diagnostics (ip, ifconfig, route, ethtool)
- Advanced diagnostics (traceroute, latency tests)
- Firewall rule analysis and network configuration
- Connection tracking and security audits
- Automated monitoring and alerting
- **Managed server inventory via SSH** — live status of Docker hosts and Proxmox VE
- **Proxmox VE management via API token** — read-only inventory and status queries

## Access Levels
- Full sudo access (NOPASSWD configured for leo)
- Can capture packets on any interface
- Can read and modify network configurations
- Access to all network interfaces and sockets
- Can execute privileged diagnostic commands

## Prerequisites
- User `leo` with sudo privileges
- Network tools installed: nmap, tcpdump, iproute2, net-tools, dnsutils, mtr, whois
- tshark (optional, for protocol-aware packet capture; install via `printf 'y\n' | sudo apt-get install -y tshark`)
- Hermes agent framework
- sshpass (for initial password-based key deployment)
- Telegram credentials (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID) stored in `~/.hermes/secrets/proxmox_token.env` for report delivery

## Initial Remote Host Provisioning
When given access to new hosts (Docker, Proxmox, etc.), follow this workflow:

### Step 1: Discover and verify host is online
```bash
nmap -sn <IP>
```

### Step 2: Store host SSH keys
```bash
ssh-keyscan -H <IP> >> ~/.ssh/known_hosts 2>/dev/null
```

### Step 3: Generate SSH keys (if missing)
```bash
ls -la ~/.ssh/id_* 2>/dev/null || ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -q
```

### Step 4: Install sshpass (for password-based key deployment)
```bash
which sshpass 2>/dev/null || sudo apt-get install -y sshpass
```

### Step 5: Deploy SSH key using password
```bash
sshpass -p '<password>' ssh-copy-id -o StrictHostKeyChecking=no <user>@<IP>
```

### Step 6: Verify connectivity
```bash
ssh <user>@<IP> 'hostname; echo OK'
```

### Step 7: Record host details immediately
```bash
ssh <user>@<IP> 'hostname; uname -r; df -h /; free -h; <service-specific status>'
```
Save details to `/mnt/shared/tmp/.lily_known_hosts.json` under `managed_servers`.

### Known pitfalls
- Nmap with `-sV -O` and many ports can timeout on some hosts. Use simpler connectivity tests (`nmap -sn`, SSH test) first.
- SSH config file (`~/.ssh/config`) may be protected from writes by SELinux/AppArmor. Keys work directly without it.
- Proxmox VE uses `root` user by default, not `leo`.
- When starting a VM, if `qm start` fails with "you can't start a vm if it's a template", verify with `qm config <id> | grep template`. If `template: 1`, either clone the VM (`qm clone`) or remove the template flag (`qm set <id> --template 0`).
- Proxmox API: `https://<IP>:8006/api2/json/` (requires authentication)
- Docker host typically needs a user with sudo (e.g., `leo`) and membership in `docker` group.
- Always verify which SSH user to use (root vs non-root) before key deployment.
- **`lily_scan.py` SSH command syntax**: The script's `gather_managed_server_details()` function uses complex nested quoting for awk commands that can break. Simplify commands: use `'df -h / | tail -1'` instead of awk formatting, and `'free -h | grep Mem'` instead of awk. If managed server sections appear empty, check the script's SSH commands and simplify them.
- **Silent failures**: The script may fail silently if SSH commands return non-zero; add explicit error checking. Always verify SSH connectivity before running the scan: `ssh leo@192.168.1.220 'hostname'`.
- **Telegram 404 with valid token**: If Telegram returns `404 Not Found` even though the token appears valid, the most common cause is interpolating a redacted string literal (e.g., `[REDACTED]`) or `***` as the token value in a curl command. Always load the actual token from environment variables or a secrets file — never type/hardcode it.
- **Proxmox API returns empty VM list**: If `/api2/json/nodes/pve/qemu` returns `{"data":[]}`, the VMs may be stopped (not just paused). Check `/api2/json/cluster/resources` for all resources across the cluster, including stopped VMs.

## Invocation
Lily runs as a persistent agent. To activate or interact:

```
terminal(delegate_task(
    goal="Lily, run network diagnostics on the primary interface and report any issues",
    context="Interface: enp6s18. Network: 192.168.1.0/24",
    toolsets=['terminal', 'file', 'web']
))
```

Or create a cron job for continuous monitoring:
```
cronjob(action='create', schedule='*/5m', prompt="Lily, check network health: ping gateway, check interface stats, alert on high error rates")
```

## Known Host Directory
Lily maintains a map of stable host identities for reporting. IPs may change, so both IP and name are shown.

| IP | Hostname | OS | Role |
|----|----------|-----|------|
| 192.168.1.1 | opnsense.home.arpa | FreeBSD | OPNsense router (gateway, SSH, HTTP) |
| 192.168.1.5 | - | Linux 3.2-3.16 | D-Link micro_httpd device |
| 192.168.1.11 | mikrotik.home.arpa | - | MikroTik (SSH, HTTP) |
| 192.168.1.15 | nmba9008.home.arpa | Windows Server 2022 | Server (MSRPC 135, SMB 445) |
| 192.168.1.55 | pve.home.arpa | Linux 6.17.13-1-pve | Proxmox VE 9.1.6 (SSH root, NFS, REST API :8006) |
| 192.168.1.110 | lgwebostv.home.arpa | WebOS | LG TV (port 3000 open) |
| 192.168.1.123 | homeassistant.home.arpa | HAOS | Home Assistant (VM 109 on proxmox-ve, RPC 111) |
| 192.168.1.174 | ubuntu-desktop | Linux 5.3-5.4 | Ubuntu desktop |
| 192.168.1.220 | docker.home.arpa | Linux 6.8.0-106-generic | Docker host (VM 105 on proxmox-ve, user: leo, SSH, Docker 29.3.1, 15-19 containers) |
| 192.168.1.222 | hermes.home.arpa | Linux 6.17.x | Hermes agent (VM 220 on proxmox-ve) |

## Automated Hourly Parallel Recon Schedule
Currently deployed as cron job ID `00489f431363` ("Lily Hourly Network Recon"):
- Schedule: every 1h
- Delivery: telegram
- Skill: lily-network-engineer
- Reports to: /mnt/shared/tmp/lily_recon_YYYY-MM-DD_HH-MM.txt and lily_recon_latest.txt
- Baseline: /mnt/shared/tmp/.lily_baseline.json
- Host identity override file: /mnt/shared/tmp/.lily_known_hosts.json

## Network Recon Script with Managed Server Integration
The core script `/mnt/shared/tmp/lily_scan.py`:

1. Runs 3 parallel nmap chunks across 192.168.1.0/24
2. Loads known hosts from `.lily_known_hosts.json` for meaningful host names
3. Compares against baseline for new/removed host detection
4. Outputs formatted reports to `/mnt/shared/tmp/lily_recon_YYYY-MM-DD_HH-MM.txt`
5. Updates latest symlink: `/mnt/shared/tmp/lily_recon_latest.txt`
6. Saves updated baseline to `.lily_baseline.json`
7. **Pulls live managed server details via SSH**:
   - Docker host: OS, kernel, disk, memory, Docker version, container list with ports, Docker networks
   - Proxmox VE: PVE version, kernel, disk, memory, running/stopped VMs, storage pool status

### Report Format
```
[Header — generated, subnet, duration]
[SUMMARY — hosts up, new/removed, total open ports]
[DETAILED HOST INVENTORY — each host with role, OS, MAC, open ports]
[SEPARATOR]
[DOCKER HOST — 192.168.1.220]       ← live SSH-collected data
[Hostname, kernel]
[Disk, memory]
[Docker version and container summary table]
[All containers with port mappings]
[Docker networks list]
[SEPARATOR]
[PROXMOX VE — 192.168.1.55]        ← live SSH-collected data
[PVE version, kernel]
[Disk, memory]
[VM table (running and stopped)]
[Storage pool status table]
```

### Example Managed Servers Structure
Store at `/mnt/shared/tmp/.lily_known_hosts.json`:

```json
{
  "known_hosts": { /* host identity overrides */ },
  "managed_servers": {
    "docker-host": {
      "ip": "192.168.1.220",
      "ssh_user": "leo",
      "os": "Ubuntu 6.8.0-106-generic",
      "disk": "123G total, 24G used (21%)",
      "memory": "7.7Gi total, 3.4Gi used",
      "swap": "7.9Gi",
      "docker_version": "29.3.1",
      "containers_running": 19,
      "networks": ["bridge", "external_network", "host", "internal_network"],
      "key_services": { /* optional static info */ }
    },
    "proxmox-ve": {
      "ip": "192.168.1.55",
      "ssh_user": "root",
      "pve_version": "9.1.6",
      "kernel": "6.17.13-1-pve",
      "disk": "rpool/ROOT/pve-1 206G (3.5G used, 2%)",
      "memory": "31Gi total, 15Gi used",
      "running_vms": [ /* array of VM objects */ ],
      "stopped_vms": [ /* array */ ],
      "storage": { /* name->status map */ }
    }
  }
}
```

## Core Skills

### Naming Conventions (User Environment)
When referring to subnets in reports and diagnostics, use these exact labels:
- **LAN**: `192.168.1.0/24` — do NOT call this "VLAN" or any other name
- **VLAN20**: `192.168.2.0/24` — do NOT call this just "VLAN" without a number
These are the user's preferred subnet names. Using the wrong label will be corrected.

### Network Discovery & Mapping — Dual Subnet (Default)
Always scan **both** subnets on every report:
- **LAN**: 192.168.1.0/24 (primary)
- **VLAN**: 192.168.2.0/24 (OPNsense VLAN, through router)

- **Subnet sweeps**: `nmap -sn 192.168.1.0/24 && sudo nmap -sn 192.168.2.0/24`
- **Port scanning**: `sudo nmap -sS -p <ports> -T4 --open 192.168.1.0/24 192.168.2.0/24`
- **OS detection**: `nmap -O target`
- **Service enumeration**: `nmap -sV -sC target`
- **ARP discovery**: `ip neigh show`
- **Live host tracking**: `arp-scan -l`

### Multi-Subnet / VLAN Discovery

When a router or firewall (e.g., OPNsense) has multiple VLAN interfaces, scan additional subnets to build a complete network map.

**Detection** — check for signs of additional subnets:
```bash
# Show all interfaces and their addresses — look for non-primary subnets
ip addr show | grep "inet "

# Show routes — any RFC1918 route besides the primary subnet is suspect
ip route show | grep -E "192\.168\.|10\.|172\.(1[6-9]|2[0-9]|3[01])\."

# HTTP header of a known router may reveal it has VLAN interfaces
# e.g. OPNsense returns `Server: OPNsense` indicating a multi-interface gateway
curl -s -I http://192.168.1.1 2>&1 | grep -i server
```

**Scanning** — target the newly discovered subnet through the router:
```bash
# Ping sweep
sudo nmap -sn 192.168.2.0/24

# Port scan on key service ports
sudo nmap -sS -p 22,80,443,53,111,135,139,445,2049,3000,\
3389,8080,8443,9090,10000,32400 -T4 --open 192.168.2.0/24

# If a host responds to ping but shows no open ports, probe it deeper:
sudo nmap -p- --min-rate=500 -T4 --open --host-timeout=30s <ip>
```

**Identification** — HTTP response headers reveal software identity:
```bash
curl -s -I http://<ip> | grep -iE "server|powered-by"
# Server: OPNsense → OPNsense firewall/gateway
# Server: micro_httpd → embedded device (D-Link etc.)
```

**Pitfalls**:
- VLAN isolation may block cross-subnet scanning entirely. If the ping sweep returns zero hosts but you have strong reason to believe a VLAN exists, check firewall rules or attempt the scan from inside the VLAN (e.g., from the OPNsense shell).
- Scanning through a router is slower than the local subnet. Use `-T4 --host-timeout=30s` to avoid hanging on unresponsive ranges.
- A host that responds to ICMP but shows zero TCP ports is often a dedicated UDP service (DNS, NTP, syslog). Probe UDP ports or run a full TCP scan on just that host.
- When scanning VLANs through a firewall/router, the source MAC will be the router's, not the target's. nmap OS detection may be unreliable.

**Reference**: `references/vlan-discovery-example.md` contains a worked example
(OPNsense dual-subnet: 192.168.1.0/24 + 192.168.2.0/24) with exact commands
and results.

### Quick On-Demand Recon (Two-Phase)
For fast, on-demand reports (under 10s total), use a two-phase approach:

**Phase 1 — Ping sweep** (2-4s per subnet):
```bash
sudo nmap -sn 192.168.1.0/24 -oG /tmp/lily_ping.gnmap
sudo nmap -sn 192.168.2.0/24 -oG /tmp/lily_vlan2_ping.gnmap
```

**Phase 2 — Port scan on key ports** (3-5s per subnet):
```bash
sudo nmap -sS -p 22,80,443,111,135,139,445,3389,8080,8443,\
2049,5900,9090,10000,3000,32400,7878,8989,9091,\
3005,8324,1900,7359,8096 -T4 --open 192.168.1.0/24
sudo nmap -sS -p 22,80,443,53,111,135,139,445,2049,3000,\
3389,8080,8443,9090,10000 -T4 --open 192.168.2.0/24
```

**Phase 3 — Managed host live inventory** (via SSH/API):
```bash
# Docker host
ssh leo@192.168.1.220 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"'
ssh leo@192.168.1.220 'docker info --format "{{.ContainersRunning}} running, {{.Containers}} total, {{.OSType}} {{.KernelVersion}}"'

# Proxmox API token query
source ~/.hermes/secrets/proxmox_token.env
curl -k -s -H "Authorization: PVEAPIToken=${PROXMOX_TOKEN_ID}=${PROXMOX_TOKEN_SECRET}" \
  "https://${PROXMOX_HOST}:8006/api2/json/cluster/resources" | python3 -c \
  'import sys,json; [print(f"{x.get(\"type\",\"?\")} {x.get(\"vmid\",\"?\"): x.get(\"name\",\"?\")} - {x.get(\"status\",\"?\")}") for x in json.load(sys.stdin).get(\"data\",[])]'
```

Use this approach over the full parallel scan when speed matters and OS/service detection is optional.

### Parallel Scanning Methodology
For subnet-wide scans, split into 3 CIDR chunks and run simultaneously:

```bash
# Chunk definitions for 192.168.1.0/24:
Chunk 1: 192.168.1.0/26  (covers .1 - .63)
Chunk 2: 192.168.1.64/26 (covers .64 - .127)
Chunk 3: 192.168.1.128/25 (covers .128 - .255)
```

Command:
```bash
sudo nmap -sS -sV -O --osscan-guess <subnet> \
  -p 22,80,443,111,135,139,445,3389,8080,3128,2049,548,5900,8443,19999,10443,8888,9090,53,25,110,143,587,993,995,123,161,162,3306,5432,6379,27017 \
  --min-rate=100 -T4 --defeat-rst-ratelimit --host-timeout=30s -oX -
```

- Run all 3 in parallel, wait for completion, then parse XML.
- Total duration: ~60-90s vs 3+ minutes sequential.
- Use `-oX -` for XML output for programmatic parsing.

### Performance Monitoring
- **Path analysis**: `mtr --report-cycles 50 8.8.8.8`
- **Connection stats**: `ss -tuna`, `ss -i`
- **Interface counters**: `ip -s link show enp6s18`
- **Socket details**: `netstat -tunap`
- **Per-process I/O**: `nethogs`
- **Throughput**: `ifstat -t 1 10`

### Packet Analysis — tcpdump + tshark (Wireshark CLI)

Lily uses both tcpdump and tshark. tshark provides protocol-aware decoding and statistics output.

#### Install tshark (if missing)
```bash
sudo apt-get install -y tshark
```
**Pitfall**: The install prompts interactively about "Should non-superusers be able to capture packets?". Use auto-answer to avoid a hang:
```bash
printf 'y\n' | sudo apt-get install -y tshark
```
Or set DEBIAN_FRONTEND=noninteractive and pre-seed:
```bash
echo "wireshark-common wireshark-common/install-setuid boolean true" | sudo debconf-set-selections
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y tshark
```

#### Interface auto-detection (skip loopback)
```bash
iface=$(ip -o link show up | grep -v "lo" | head -n1 | awk -F': ' '{print $2}')
```

#### Timed capture + analysis + Telegram delivery + cleanup
This is the standard Lily workflow for one-shot packet analysis:

1. Capture N seconds: `sudo tshark -i "$iface" -a duration:60 -w /tmp/capture.pcap`
2. Analyze with protocol hierarchy: `tshark -r /tmp/capture.pcap -q -z io,phs`
3. Extract top talkers:
   - Sources: `tshark -r capture.pcap -Y ip -T fields -e ip.src | sort | uniq -c | sort -nr | head -5`
   - Destinations: `tshark -r capture.pcap -Y ip -T fields -e ip.dst | sort | uniq -c | sort -nr | head -5`
4. Extract top ports:
   - TCP: `tshark -r capture.pcap -Y tcp -T fields -e tcp.dstport | sort | uniq -c | sort -nr | head -5`
   - UDP: `tshark -r capture.pcap -Y udp -T fields -e udp.dstport | sort | uniq -c | sort -nr | head -5`
5. Send plain-text report to Telegram (see Telegram delivery pattern below)
6. **Delete the pcap file immediately** — captures may contain sensitive data
   ```bash
   rm -f /tmp/capture.pcap /tmp/report.txt
   ```

#### Telegram delivery pattern (reusable)
```bash
PAYLOAD=$(cat /path/to/report)
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID&text=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.stdin.read()))' <<< "$PAYLOAD")"
```

#### Example: full capture-and-report command (background-safe)
```bash
# 1. Install if needed
printf 'y\n' | sudo apt-get install -y tshark

# 2. Capture
iface=$(ip -o link show up | grep -v "lo" | head -n1 | awk -F': ' '{print $2}')
sudo tshark -i "$iface" -a duration:60 -w /mnt/shared/tmp/capture.pcap

# 3. Analyze
REPORT=/mnt/shared/tmp/report.txt
echo "=== Protocol ===" > "$REPORT"
tshark -r /mnt/shared/tmp/capture.pcap -q -z io,phs >> "$REPORT"
echo "=== Top Sources ===" >> "$REPORT"
tshark -r /mnt/shared/tmp/capture.pcap -Y ip -T fields -e ip.src | sort | uniq -c | sort -nr | head -5 >> "$REPORT"
# ... repeat for dst, ports ...

# 4. Deliver (load credentials first)
source ~/.hermes/secrets/proxmox_token.env 2>/dev/null || true
PAYLOAD=$(cat "$REPORT")
curl -s -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/sendMessage" \
  -d "chat_id=$TELEGRAM_CHAT_ID&text=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.stdin.read()))' <<< "$PAYLOAD")"

# 5. Cleanup
rm -f /mnt/shared/tmp/capture.pcap /mnt/shared/tmp/report.txt
```

#### Prerequisites for tshark workflow
- Package: tshark (install with auto-answer pitfall above)
- Sudo: leo has NOPASSWD sudo for capture
- Telegram: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be loaded (prefer secrets file: `source ~/.hermes/secrets/proxmox_token.env`)
- Capture dir: /mnt/shared/tmp/ (writable, cleanup after use)
- **Always delete pcap after use** — captures contain sensitive network traffic

A reusable capture script is bundled at `scripts/tshark_capture_report.sh`. Run it directly:
```bash
sudo bash scripts/tshark_capture_report.sh [duration_seconds]
```
It auto-detects the interface, captures, analyzes protocol hierarchy + top talkers, prints to stdout, and cleans up all temporary files on exit.

### DNS & Identity
- **A records**: `dig +short example.com`
- **All records**: `dig example.com any`
- **Trace resolution**: `dig +trace example.com`
- **Reverse lookup**: `dig -x 8.8.8.8`
- **WHOIS lookup**: `whois example.com`
- **NS records**: `dig NS example.com`

### Interface & Routing
- **IP addresses**: `ip addr show`
- **Interface stats**: `ethtool -i enp6s18 && ethtool -S enp6s18`
- **Routing table**: `ip route show`
- **ARP cache**: `ip neigh show`
- **Routing rules**: `ip rule show`
- **Policy routing**: `ip netns list` (if namespaces exist)

### Security & Firewall
- **Firewall rules**: `sudo iptables -L -n -v`, `sudo nft list ruleset`
- **Connection tracking**: `sudo conntrack -L`
- **Port listening**: `sudo lsof -i -P -n`
- **SELinux/AppArmor**: `sudo aa-status`, `getenforce`
- **Audit logs**: `sudo ausearch -m avc -ts recent`

### Troubleshooting Workflows
1. **Link down?**
   - `ip link show enp6s18`
   - `ethtool enp6s18`
   - `dmesg | grep enp6s18`
2. **No IP?**
   - `dhclient -v enp6s18` (or verify DHCP)
   - Check `cat /etc/netplan/*.yaml` or `/etc/network/interfaces`
3. **Can't reach gateway?**
   - `ping -c 4 192.168.1.1`
   - `arp -n | grep 192.168.1.1`
4. **High latency?**
   - `mtr --report 8.8.8.8`
   - `traceroute -n 8.8.8.8`
   - Check local: `ping -i 0.2 -c 100 gateway`
5. **DNS failure?**
   - `dig example.com`
   - `nslookup example.com`
   - Check `/etc/resolv.conf`, `systemd-resolve --status`

## Sudo Operations (Use with Caution)
- **Restart networking**: `sudo systemctl restart NetworkManager` or `sudo netplan apply`
- **Flush ARP**: `sudo ip neigh flush all`
- **Clear connection tracking**: `sudo conntrack -F`
- **Capture with elevated buffer**: `sudo tcpdump -i any -B 4096 -w capture.pcap`
- **Modify firewall**: `sudo iptables -A ...` or `sudo nft add rule ...`
- **Change interface**: `sudo ip link set dev enp6s18 up/down`, `sudo ip addr add/del ...`

## Safety Protocols
- **Destructive actions** require explicit confirmation
- **Packet captures** automatically rotate; sensitive data must be relocated or deleted
- **Firewall changes** must be logged with justification
- **Interface down** operations only after verifying no critical services
- **All sudo commands** are audited; maintain change tickets where applicable

## Alerting & Logging
- Log directory: `/var/log/lily/` (create: `sudo mkdir -p /var/log/lily && sudo chown leo:leo /var/log/lily`)
- Concurrent capture limit: 1 active capture per interface
- Retention: rotate logs daily, keep 7 days
- Health checks: run hourly and report to `lily-health.log`

- **Proxmox VM Management**: When managing VMs on Proxmox (`192.168.1.55`), use the `qm` CLI via SSH (root/{{PROXMOX_ROOT_PASSWORD}}) when direct SSH to the guest is refused (common in HAOS).
- **Tailscale Connection Handling**: If SSH connection to a host is refused on its public IP, attempt the Tailscale IP (`100.x.x.x`). Host key verification failures require checking `known_hosts` or ensuring `tailscale set --ssh` is enabled on the source.
- **SSH Key Management**: Save host-specific SSH keys to `~/.hermes/` (e.g., `srv_id_rsa`) to maintain isolation from standard user keys.

```bash
ssh root@192.168.1.55 qm list                    # List all VMs
ssh root@192.168.1.55 qm start <vmid>             # Start a VM
ssh root@192.168.1.55 qm stop <vmid>              # Stop a VM (graceful)
ssh root@192.168.1.55 qm status <vmid>            # Check VM status
ssh root@192.168.1.55 qm config <vmid>            # Show VM configuration
ssh root@192.168.1.55 qm clone <vmid> <new_id>    # Clone a VM (useful for templates)
```

**Template handling**: If a VM has `template: 1` in its config, it cannot be started directly. Either:
1. Clone it: `ssh root@192.168.1.55 qm clone <vmid> <new_id> --name <name> --full 1`, then start the clone
2. Remove template flag: `ssh root@192.168.1.55 qm set <vmid> --template 0`, then start (warning: breaks template functionality)

### Docker Host Inventory via SSH
Collect live Docker status on 192.168.1.220 (user `leo`):

```bash
ssh leo@192.168.1.220 'docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"'
ssh leo@192.168.1.220 'docker info --format "{{.ContainersRunning}} running, {{.Containers}} total, {{.OSType}} {{.KernelVersion}}"'
ssh leo@192.168.1.220 'df -h / | tail -1'
ssh leo@192.168.1.220 'free -h | grep Mem'
```

### Self-Hosted Hermes Maintenance

When managing a self-hosted Hermes Agent installation (cloned from git), the update procedure differs from the `hermes update` command used in pip/brew installations:

**Version check:**
```bash
cd ~/.hermes/hermes-agent && python -c "from hermes_cli import __version__; print(__version__)"
# Returns semantic version string, e.g. "0.17.0"
```

**Update procedure:**
```bash
cd ~/.hermes/hermes-agent
git pull origin main                          # fast-forward to latest
uv sync --frozen                              # sync dependencies (no lockfile changes)
git log --oneline v$(python -c "from hermes_cli import __version__; print(__version__)")..HEAD | wc -l   # count new commits
```

**Verification:**
```bash
cd ~/.hermes/hermes-agent
python -c "from hermes_cli import __version__; print(__version__)"  # new version string
git rev-parse --short HEAD                                            # new commit hash
git status --short                                                    # should be clean
```

**Pitfalls:**
- The git tag (e.g., `v2026.5.16`) may lag behind the actual code version — always check `hermes_cli.__version__` for the real version number.
- `uv sync --frozen` is preferred over `uv sync` because it preserves the lockfile — `uv sync` may upgrade transitive dependencies unnecessarily.
- Always backup `~/.hermes/config.yaml` before any update, especially if you've made local edits (custom providers, secrets). The git pull should not touch config.yaml, but a backup is cheap insurance.
- If `uv` is not in PATH, it's typically at `~/.local/bin/uv`.
- After update, check that custom_providers (e.g., Ollama) are still resolved correctly in `~/.hermes/config.yaml`.

### Local AI / Ollama Integration

Lily integrates local AI inference via Ollama running on the Proxmox VE host (192.168.1.55) for Hermes agent use.

**Check Ollama status:**
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 'which ollama && ollama --version && systemctl is-active ollama && ollama list'
```

**Enable LAN access** (Ollama listens on 127.0.0.1 by default):
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 '
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << '\''EOF'\''
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF
systemctl daemon-reload && systemctl restart ollama
'
```
Verify: `ss -tlnp | grep ollama` should show `*:11434` not `127.0.0.1:11434`.

**Add as Hermes custom provider** (in `~/.hermes/config.yaml`):
```yaml
custom_providers:
  ollama:
    base_url: http://192.168.1.55:11434/v1
    api_key: ""
    api_mode: chat_completions
    models:
      - qwen2.5-coder:7b
```

**Verify connectivity:**
```bash
# Native API
curl -s http://192.168.1.55:11434/api/tags

# OpenAI-compatible endpoint (used by Hermes)
curl -s http://192.168.1.55:11434/v1/models

# Test inference
curl -s -X POST http://192.168.1.55:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"Say hello in 3 words"}],"stream":false}'
```

**Usage with Hermes:**
```bash
hermes --provider ollama --model qwen2.5-coder:7b
```

**Pitfalls:**
- Ollama has no built-in API key authentication. On a trusted LAN this is fine; for external access, put a reverse proxy (nginx/Caddy) in front with an auth header check.
- The `api_key: ""` is intentional — Hermes accepts empty keys for local providers. If Hermes complains, set `api_key: "ollama"` (the actual string doesn't matter for Ollama).
- After modifying `config.yaml`, always validate: `python3 -c "import yaml; yaml.safe_load(open('/home/leo/.hermes/config.yaml'))"` and confirm YAML is valid.
- The `custom_providers` key goes at the top level of config.yaml (sibling of `providers`, not nested under it).
- Back up config.yaml before editing: `cp ~/.hermes/config.yaml ~/.hermes/config.yaml.bak`.

### Proxmox API Token Auth (Read-Only)
Prefer API token over SSH for read-only inventory. Store token in `~/.hermes/secrets/proxmox_token.env`:
```bash
export PROXMOX_HOST=192.168.1.55
export PROXMOX_TOKEN_ID=root@pam!hermes
export PROXMOX_TOKEN_SECRET=<actual-secret>
```

**Auth header format**: `PVEAPIToken=${TOKEN_ID}=${TOKEN_SECRET}`

**Useful endpoints**:
| Endpoint | Purpose |
|----------|---------|
| `/api2/json/version` | PVE version check |
| `/api2/json/nodes` | List cluster nodes |
| `/api2/json/nodes/pve/status` | Node uptime, load, memory |
| `/api2/json/nodes/pve/qemu` | All VMs on node |
| `/api2/json/nodes/pve/lxc` | All containers on node |
| `/api2/json/nodes/pve/qemu/<vmid>/status/current` | Single VM state |
| `/api2/json/cluster/resources` | All cluster resources (VMs, CTs, storage) |

**Pitfall**: If `/nodes/pve/qemu` returns empty data but the node is online, use `/cluster/resources` instead — stopped VMs may not appear under the node endpoint.

## Commissioning Checklist
- [x] Verify all network tools installed and functional
- [x] Confirm sudo NOPASSWD works for leo
- [x] Create log directory with proper permissions
- [x] Test basic nmap scan on localhost
- [x] Test tcpdump capture and rotation
- [x] Document network topology and base configuration
- [x] Set initial monitoring tasks in cron
- [x] Configure alert thresholds (error rates >1%, latency >100ms, packet loss >5%)
- [x] Hourly parallel recon cron job created (ID: 00489f431363)
- [x] Telegram delivery configured
- [x] Reports saved to /mnt/shared/tmp/
- [x] Baseline change tracking in .lily_baseline.json
- [x] Known host identities in `/mnt/shared/tmp/.lily_known_hosts.json`
- [x] Managed server SSH keys installed and verified
- [x] Managed server details integrated into hourly reports via `gather_managed_server_details()`

## Example Autonomous Task

**Goal**: "Lily, continuously monitor the WAN interface (enp6s18) for packet errors and notify if errors exceed 1% in the last 5 minutes"

**Implementation**:
```python
# Pseudocode for continuous monitoring
while True:
    stats = ip -s link show enp6s18
    rx_errors = parse_rx_errors(stats)
    total_rx = parse_rx_packets(stats)
    error_rate = rx_errors / total_rx
    if error_rate > 0.01:
        alert(f"High error rate on enp6s18: {error_rate:.2%}")
    sleep(300)  # 5 minutes
```

## Support
Lily operates under the supervision of Leo. All critical network changes require human approval. Refer to session logs for detailed operation history.
