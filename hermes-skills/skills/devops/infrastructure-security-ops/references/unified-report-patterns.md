# Timestamp Parsing Pattern

When filtering log files for a 24h window, ALWAYS handle both timestamp formats:

```python
def parse_timestamp(line):
    # ISO: 2026-05-10T00:00:27.997392+03:00
    m = re.match(r"^(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", line)
    if m:
        try:
            return datetime.strptime(f"{m.group(1)} {m.group(2)}", "%Y-%m-%d %H:%M:%S")
        except: pass
    # Syslog: May 11 09:00:07
    m = re.match(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", line)
    if m:
        try:
            return datetime.strptime(f"{NOW.year} {m.group(1)}", "%Y %b %d %H:%M:%S")
        except: pass
    return None
```

In `lines_since()`: **NEVER** use `elif not ts: result.append(line)`. That bypassed all date filtering for ISO-format ufw.log → returned everything instead of 24h.

```python
def lines_since(filepath, max_lines=50000):
    with open(filepath, "r", errors="replace") as f:
        all_lines = f.readlines()[-max_lines:]
    return [l.strip() for l in all_lines if parse_timestamp(l) and parse_timestamp(l) >= SINCE]
```

# UFW Log Sources (Priority)
1. `/var/log/ufw.log` — ISO timestamps
2. `/var/log/kern.log` — syslog timestamps, grep `[UFW BLOCK]`
3. `journalctl -k --since "24h"` — kernel buffer fallback

# Cross-Correlation Pattern
```python
ufw_ips = set(ufw_blocked)
f2b_ips = set(f2b_banned)
auth_ips = set(brute_force)
# F2B gap: ufw_ips - f2b_ips (400+ IPs blocked by firewall but not F2Ban)
# Confirmed: ufw_ips & f2b_ips (both caught them)
# Unguarded: auth_ips - ufw_ips - f2b_ips (SSH brute-force missed by all)
```

# Health Score (0-100)
```
100 - UFW>100:-10, >50:-5 | F2B repeat>5:-15, >0:-5 | SSH BF>3:-15, >0:-5
| errs>50:-15, >10:-8 | crashes*10 | OOM*3(max15) | unhealthy*10
```

# Syslog Noise Patterns (filter these out of error counts)
- `Tool terminal returned error`
- `delivery error.*Telegram send failed`
- `Security scan.*Variation selector`
- `Job '[a-f0-9]+': delivery error`
