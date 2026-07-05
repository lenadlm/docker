# Network Health Check

Consolidated from `network-health-check` skill. Automated local network health monitoring.

## Checks Performed

### 1. Interface Health
- `ip -s link show <interface>`
- Thresholds: RX/TX errors > 100, drops > 100
- Look for: CRC errors, overruns, dropped packets

### 2. Gateway Reachability
- `ping -c 5 -W 2 <gateway>`
- Thresholds: Packet loss > 5%, latency > 200ms

### 3. DNS Resolution
- `dig +short example.com @1.1.1.1`
- Threshold: any failure

### 4. Listening Sockets
- `ss -tuln`
- Check for unexpected high ports (> 10000, excluding known services)
- Known exceptions: Tailscale ephemeral ports, Docker user-defined mappings, SSH high port variations

## Alert Thresholds
- **Critical**: Gateway unreachable, DNS failure, >1000 errors/drops
- **Warning**: >100 errors/drops, >5% loss, >200ms latency, unexpected high ports

## False Positive Mitigation
Maintain a whitelist of expected services and port ranges in config.

## Integration
Part of hourly recon — checks log to `/var/log/lily/monitor.log` with timestamps. 7-day retention via logrotate.