---
name: network-health-check
description: Automated network health monitoring check - verifies interface stats, gateway reachability, DNS resolution, and listening sockets with intelligent filtering of expected services.
version: 1.0.0
author: Lily (Network Engineer Agent)
license: MIT
---

# Network Health Check Skill

## Purpose
Quick, repeatable health check for local network interfaces with intelligent service detection and false-positive reduction.

## Checks Performed

### 1. Interface Health
- **Command**: `ip -s link show <interface>`
- **Thresholds**: RX/TX errors > 100, drops > 100
- **What to look for**: CRC errors, overruns, dropped packets

### 2. Gateway Reachability
- **Command**: `ping -c 5 -W 2 <gateway>`
- **Thresholds**: Packet loss > 5%, latency > 200ms
- **What to look for**: Unreachable gateway, high latency spikes

### 3. DNS Resolution
- **Command**: `dig +short example.com @1.1.1.1`
- **Thresholds**: Any failure
- **What to look for**: DNS timeouts, NXDOMAIN, no answer

### 4. Listening Sockets
- **Command**: `ss -tuln`
- **Thresholds**: Unexpected high ports (> 10000, excluding known services)
- **What to look for**: Unauthorized services, rogue daemons
- **Known exceptions**: 
  - Tailscale ports (typically 41641, 44620, 33926, etc.)
  - Docker user-defined ports (10443, 19999, 8888, 9090, 8443 as per environment)
  - SSH high port variations

## Implementation

```python
# Pseudocode
def network_health_check(interface="enp6s18", gateway="192.168.1.1"):
    results = []
    
    # 1. Interface stats
    stats = terminal(f"ip -s link show {interface}")
    rx_errors, rx_drops = parse_interface_stats(stats)
    if rx_errors > 100 or rx_drops > 100:
        alert(f"High errors/drops on {interface}")
    
    # 2. Ping gateway
    ping = terminal(f"ping -c 5 -W 2 {gateway}")
    loss, latency = parse_ping(ping)
    if loss > 5 or latency > 200:
        alert(f"Gateway issues: {loss}% loss, {latency}ms latency")
    
    # 3. DNS test
    dns = terminal("dig +short example.com @1.1.1.1")
    if not dns['output'].strip():
        alert("DNS resolution failed")
    
    # 4. Listening sockets
    sockets = terminal("ss -tuln")
    unexpected = filter_known_services(sockets)
    if unexpected:
        alert(f"Unexpected ports: {unexpected}")
    
    # Write to log
    log_to_file("/var/log/lily/monitor.log", results)
    
    return "OK" if not alerts else f"ISSUES: {alerts}"
```

## Integration with Lily Agent

This skill is invoked automatically by Lily's hourly parallel recon cron job (ID: `00489f431363`) or manually:

```bash
terminal(delegate_task(
    goal="Lily, run network health check on enp6s18",
    toolsets=['terminal']
))
```

## Known False Positives & Mitigations

| Service | Expected Ports | Reason |
|---------|---------------|--------|
| Tailscale | 41641, ephemeral > 30000 | WireGuard P2P mesh uses dynamic ports |
| Docker containers | User-defined mappings | Per-container configuration |
| VPN clients | Dynamic high ports | Tunnel traffic |
| Kubernetes NodePort | 30000-32767 | Cluster services |

**To suppress false positives**: Maintain a whitelist of expected services and their port ranges in `/mnt/shared/tmp/.lily_known_hosts.json` under `monitoring.port_whitelist`.

## Logging
All checks log to `/var/log/lily/monitor.log` with timestamps. Historical logs kept for 7 days via logrotate configuration.

## Alert Thresholds
- **Critical**: Gateway unreachable, DNS failure, >1000 errors/drops
- **Warning**: >100 errors/drops, >5% loss, >200ms latency, unexpected high ports
- **Info**: All checks passing

## Related
- Part of lily-network-engineer agent
- Integrated with hourly recon (`lily_recon_latest.txt`)
- Reports to Telegram via cron job delivery