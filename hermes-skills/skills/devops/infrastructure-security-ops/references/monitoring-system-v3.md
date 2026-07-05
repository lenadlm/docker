# Monitoring System v3.0 — Architecture Reference

## Location
`/opt/reports/monitoring/main.py` — single-file monolith (~1750 lines)

## Components
- **Log Parser**: Multi-format timestamps (syslog `May 11 09:00:07`, ISO `2026-05-10T00:00:27`, journalctl fallback)
- **Auto-discovery**: Detects installed services, handles missing logs gracefully
- **Rotated logs**: Parses `.gz` and `.1` rotated files in addition to current log
- **Analyzers**: Auth/SSH, UFW, Fail2Ban, CrowdSec, auditd, syslog, Docker, network, performance
- **Cross-correlator**: Finds multi-source attack patterns and cascading failures
- **Scoring Engine**: 100-point security + system scores with weighted categories
- **SQLite Learning Engine**: Baseline trends, recurring incident tracking, severity escalation
- **Report Generators**: Markdown (Telegram), HTML dashboard (Jinja2), plain-text summary
- **Cleanup**: 3-day retention via script + logrotate config

## Running
```bash
sudo python3 /opt/reports/monitoring/main.py      # stdout = Markdown
cat /opt/reports/history/report_*.md              # saved reports
python3 -c "import sqlite3; sqlite3.connect('/opt/reports/db/reports.db')"  # trend DB
```

## Python Pitfalls Discovered
1. **dict.items() slicing**: `dict.items()[:n]` raises `TypeError` in Python 3. Must use `list(dict.items())[:n]`
2. **Variable shadowing**: `ts` was used for both timestamp string and Tailscale dict — Tailscale block overwrote the timestamp, causing `{}` dict to print in report footer
3. **Sudo permissions**: `/var/log/auth.log`, `/var/log/ufw.log`, etc. require root. Always run as root or via sudo

## Key Patterns Worth Remembering
- **Deduplication**: Normalize log lines by removing timestamps, IPs, PIDs → `re.sub(r"[\d]{4}[-T:. \d]{10,}|SRC=[\d.]+|DST=[\d.]+|pid=\d+|\[\d+\]", "...", line)`
- **Event correlation**: Cross-reference UFW blocked IPs with Fail2Ban banned IPs and SSH failed IPs → `ufw_ips - f2b_ips` finds coverage gaps
- **Scoring formula**: Security (40%) + System (60%) with per-category deductions (brute-force: -10 to -30, OOM: -15, crashes: -10 each, etc.)
- **Trend detection**: Compare current row vs previous row in SQLite → `p=0,c>0` is new, `c>p*1.5` is worsening, `c<p/2` is improvement
