# CrowdSec Native Port Scan Detection (June 2026)

Replaces fail2ban's portscan jail. No sync issues, no "already banned" gap, no per-IP counter resets on reload.

## Architecture

```
UFW DROP → kern.log
    ↓
CrowdSec acquis (type: syslog)
    ↓
syslog-logs parser (s00-raw)
  → Extracts: program=kernel, message=[UFW BLOCK] IN=...
    ↓
iptables-logs parser (s01-parse)
  → Filter: program == 'kernel' AND message contains 'IN='
  → Excludes: ACCEPT, AUDIT lines
  → Sets: log_type=iptables_drop, source_ip, dst_port, proto
    ↓
iptables-scan-multi_ports scenario
  → Current: 3 distinct ports in 10s (capacity=3, leakspeed=10s — aggressive, bans after 3-port scan)
  → Evolution: 15@5s → 10@30s → 5@40s → 5@40s → 3@10s
    ↓
CrowdSec LAPI → Bouncer → CROWDSEC_CHAIN 🚧
```

## Metrics Interpretation

From `sudo cscli metrics`:

| Metric | kern.log (~43k lines) | Meaning |
|--------|-----------------------|---------|
| Lines parsed | ~97 | DROP/BLOCK events (ACCEPT/AUDIT excluded by design) |
| Lines unparsed | ~43k | ALLOW, AUDIT, ACCEPT, and non-iptables kernel messages |
| Lines poured to bucket | ~20 | Events that matched the multi-ports threshold |
| Parser hits | 194 | Total iptables-logs matches (includes both poured and non-poured) |

**Low parsed count is normal.** Most kern.log is ALLOW/AUDIT traffic. The parser explicitly filters to only DROP events.

## Critical: Overflows vs Active Buckets

The scenario can show `Current Count: 6` and `Poured: 799` but **0 Overflows** — meaning it's tracking IPs but has never triggered a ban decision. An overflow IS a ban. If Overflows is `-`, the scenario has never produced a decision, regardless of Poured or Current Count. The Web Console shows active decisions, not active tracking.

Use `sudo cscli alerts list --scenario crowdsecurity/iptables-scan-multi_ports` to check for actual ban decisions.

## Log Injection for Testing

To verify the full pipeline:

```bash
TEST_IP="10.0.0.99"
NOW=$(date '+%Y-%m-%dT%H:%M:%S+03:00')
for port in 22 80 443 3306 8080; do
  sudo sh -c 'echo "$1 srv kernel: [UFW BLOCK] IN=eth0 OUT= MAC=... SRC=$2 DST=192.168.1.100 LEN=60 TOS=0x00 PREC=0x00 TTL=64 ID=54321 PROTO=TCP SPT=63345 DPT=$3 WINDOW=65535 RES=0x00 SYN URGP=0 " >> /var/log/kern.log' _ "$NOW" "$TEST_IP" "$port"
done
sleep 10
sudo cscli alerts list --scenario crowdsecurity/iptables-scan-multi_ports
```

**Caveats:**
- Use `sudo sh -c '...'` heredoc-style shell to avoid `DF` flag and trailing artifacts that ParseKV chokes on
- Match exact real UFW BLOCK format (no `DF` flag, trailing space)
- Also, entropy/resource consumption: 5 * 80 bytes per port (data injection).

## Verification

```bash
# Check parsers and scenarios are installed
sudo cscli parsers list | grep iptables-logs
sudo cscli scenarios list | grep iptables-scan-multi_ports

# Check live metrics
sudo cscli metrics 2>&1 | grep -E "(kern|iptables|poured)"

# Check active decisions from this scenario
sudo cscli alerts list --scenario crowdsecurity/iptables-scan-multi_ports
```

## Migration from fail2ban portscan

1. Ensure `crowdsecurity/iptables-logs` parser is installed and enabled
2. Ensure `crowdsecurity/iptables-scan-multi_ports` scenario is installed and enabled
3. Verify `kern.log` is in acquis config (`/etc/crowdsec/acquis.d/`) with `type: syslog`
4. (Optional) Tune the scenario: edit `/etc/crowdsec/scenarios/iptables-scan-multi_ports.yaml` — current aggressive config uses `capacity: 3, leakspeed: 10s` for near-instant bans on 3+ port scans
5. Reload CrowdSec: `sudo systemctl reload crowdsec`
6. Verify metrics parsing kern.log
7. Remove fail2ban portscan jail from `jail.local`
8. Remove fail2ban recidive jail (CrowdSec handles repeat offenders natively — ssh-bf, ssh-slow-bf scenarios)
9. Change sshd mode to `extra` in jail.local (NOT aggressive — aggressive catches sudo PAM entries)
10. Reload fail2ban: `sudo fail2ban-client reload`
11. Verify only sshd active: `sudo fail2ban-client status`