#!/usr/bin/env python3
"""
Daily Linux Deep Log Analysis Report
══════════════════════════════════════
Collects and analyzes system logs, Docker containers, security services,
and firewall activity — producing a structured Telegram-friendly summary.

Usage:
  sudo python3 /usr/local/bin/daily_log_report.py

When run via cron with delivery='origin', stdout is auto-delivered
to the current chat (Telegram). Requires sudo for /var/log access.
"""

import subprocess
import os
import re
import json
from datetime import datetime, timedelta
from collections import Counter

NOW = datetime.now()
SINCE = NOW - timedelta(hours=24)

LOG_PATHS = {
    "syslog": "/var/log/syslog",
    "auth": "/var/log/auth.log",
    "kern": "/var/log/kern.log",
    "audit": "/var/log/audit/audit.log",
    "fail2ban": "/var/log/fail2ban.log",
    "ufw": "/var/log/ufw.log",
}


def run(cmd, timeout=30):
    """Run a shell command, return stripped stdout. Returns '' on failure."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True,
                           text=True, timeout=timeout)
        return (r.stdout or "").strip()
    except Exception:
        return ""


def parse_syslog_timestamp(line):
    """Extract a datetime from a syslog-style line prefix."""
    m = re.match(r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})", line)
    if not m:
        return None
    try:
        return datetime.strptime(f"{NOW.year} {m.group(1)}",
                                 "%Y %b %d %H:%M:%S")
    except Exception:
        return None


def lines_since(filepath, max_lines=50000):
    """Read lines from a log file within the last 24 hours."""
    if not os.path.isfile(filepath):
        return []
    try:
        with open(filepath, "r", errors="replace") as f:
            all_lines = f.readlines()
    except PermissionError:
        return []
    all_lines = all_lines[-max_lines:]
    result = []
    for line in all_lines:
        ts = parse_syslog_timestamp(line)
        if ts and ts >= SINCE:
            result.append(line.strip())
        elif not ts:
            result.append(line.strip())
    return result


def safe_float(v):
    """Parse a number from a value like '3.5%' or 'N/A'."""
    try:
        return float(str(v).replace("%", "").strip())
    except (ValueError, TypeError, AttributeError):
        return 0.0


# ──────────────────────────────────────────────────────────────
# Analyzers
# ──────────────────────────────────────────────────────────────
def analyze_auditd():
    """Parse auditd logs for the last 24 hours."""
    filepath = LOG_PATHS["audit"]
    if not os.path.isfile(filepath):
        return {
            "key": ["Auditd log not found or not readable."],
            "suspicious": [],
            "violations": [],
            "recommendations": [
                "Install and enable auditd: sudo apt install auditd && "
                "sudo systemctl enable --now auditd"],
        }
    ausearch_out = run("sudo ausearch -ts today 2>/dev/null")
    lines = ausearch_out.splitlines() if ausearch_out else lines_since(filepath)

    type_counts = Counter()
    failed_logins = 0
    priv_esc = 0
    file_access = 0
    violations = []

    for line in lines:
        if "type=" not in line.lower() and "msg=" not in line:
            continue
        m = re.search(r"type=(\w+)", line)
        if m:
            type_counts[m.group(1)] += 1
        if (("USER_LOGIN" in line) or ("USER_AUTH" in line)) \
                and "res=failed" in line.lower():
            failed_logins += 1
        if "AVC" in line or "APPARMOR" in line:
            violations.append(line[:200])
        if "SYSCALL" in line and re.search(r"(chmod|chown|mount|umount)", line):
            file_access += 1
        if re.search(r'comm="(sudo|su|pkexec)"', line):
            priv_esc += 1

    key_events = [f"  {t}: {c} events"
                  for t, c in type_counts.most_common(8)]
    suspicious = []
    if failed_logins > 0:
        suspicious.append(
            f"{failed_logins} failed login/authentication attempts")
    if priv_esc > 0:
        suspicious.append(
            f"{priv_esc} privilege-escalation calls (sudo/su/pkexec)")
    if file_access > 0:
        suspicious.append(
            f"{file_access} sensitive file operations (chmod/chown/mount)")
    if violations:
        suspicious.append(f"{len(violations)} AppArmor/SELinux AVC denials")

    recommendations = []
    if failed_logins > 10:
        recommendations.append(
            f"\U0001f534 High failed-login count ({failed_logins}) "
            f"— tighten SSH key-only auth, review /etc/pam.d")
    if violations:
        recommendations.append(
            "\U0001f7e1 Review AVC denials: "
            "`ausearch -m avc -ts today`")
    if priv_esc > 5:
        recommendations.append(
            f"\U0001f7e1 Elevated priv-esc ({priv_esc} events) "
            f"— audit sudoers")
    if not recommendations:
        recommendations.append(
            "\u2705 No critical auditd anomalies in the last 24h")

    return {
        "key": key_events
             or ["No significant auditd events in the last 24h."],
        "suspicious": suspicious or ["None detected."],
        "violations": ([v[:200] for v in violations[:5]]
                       or ["None detected."]),
        "recommendations": recommendations,
    }


def analyze_syslog():
    """Parse syslog for errors, warnings, service restarts."""
    lines = lines_since(LOG_PATHS["syslog"])
    if not lines and os.path.isfile(LOG_PATHS["syslog"]):
        j_out = run(
            'journalctl --since "24 hours ago" '
            '--no-pager 2>/dev/null | head -5000')
        lines = j_out.splitlines() if j_out else []

    errors = []
    error_count = 0
    warnings = []
    warning_count = 0
    service_restarts = Counter()
    error_pat = re.compile(r"\b(error|crit|alert|emerg)\b", re.I)
    warn_pat = re.compile(r"\b(warn|warning)\b", re.I)
    svc_pat = re.compile(
        r"(systemd|supervisor|dockerd).*?"
        r"(started|stopped|restarted|failed|killing)", re.I)
    oom_pat = re.compile(
        r"oom[- ]?killer|out of memory|killed process", re.I)

    for line in lines:
        if error_pat.search(line):
            error_count += 1
            # Only keep the first few error entries
            if len(errors) < 3:
                # Extract just the hostname+service+short msg
                parts = line.split(": ", 2)
                short = parts[2][:150] if len(parts) > 2 else line[-150:]
                errors.append(short.strip())
        if warn_pat.search(line):
            warning_count += 1
            if len(warnings) < 3:
                parts = line.split(": ", 2)
                short = parts[2][:150] if len(parts) > 2 else line[-150:]
                warnings.append(short.strip())
        m = svc_pat.search(line)
        if m:
            svc_m = re.search(r"Starting (.+?)\.\.\.|Started (.+?)\.|Stopped (.+?)\.|failed (.+?)", line)
            if svc_m:
                svc = (svc_m.group(1) or svc_m.group(2)
                       or svc_m.group(3) or svc_m.group(4) or "").strip()
                # Extract just the service name (before " - ")
                if " - " in svc:
                    svc = svc.split(" - ")[0].strip()
                if svc:
                    service_restarts[svc] += 1
        if oom_pat.search(line):
            error_count += 1
            if len(errors) < 3:
                short = line.split(" OOM", 1)[-1].strip()[:150]
                errors.append(f"\U0001f534 OOM: {short}")

    # Service issue summary from restart counts
    service_summary = []
    for svc, cnt in service_restarts.most_common(5):
        if cnt > 3:
            service_summary.append(f"{svc}: {cnt} restarts")
    for svc, cnt in service_restarts.most_common(10):
        if cnt <= 3:
            service_summary.append(f"{svc}: {cnt} restarts")

    recommendations = []
    if error_count > 5:
        recommendations.append(
            f"\U0001f534 {error_count} errors logged — "
            f"`journalctl -p err --since '24h ago'`")
    if warning_count > 10:
        recommendations.append(
            f"\U0001f7e1 {warning_count} warnings — possible degrading services")
    for svc, cnt in service_restarts.most_common(5):
        if cnt > 3:
            recommendations.append(
                f"\U0001f7e1 {svc} restarted {cnt}x")
    if any("oom" in e.lower() for e in errors):
        recommendations.append(
            "\U0001f534 OOM events \u2014 review memory limits, "
            "consider RAM/swap")
    if not recommendations:
        recommendations.append(
            "\u2705 Syslog clean \u2014 no critical issues")

    return {
        "service_summary": service_summary or ["No service failures."],
        "errors": errors or ["No errors."],
        "error_count": error_count,
        "warning_count": warning_count,
        "warnings_list": warnings,
        "recommendations": recommendations,
    }


def analyze_auth():
    """Parse auth.log for login activity and suspicious access."""
    lines = lines_since(LOG_PATHS["auth"])
    if not lines and os.path.isfile(LOG_PATHS["auth"]):
        j_out = run(
            'journalctl --since "24 hours ago" -u ssh '
            '--no-pager 2>/dev/null | head -3000')
        lines = j_out.splitlines() if j_out else []

    failed_logins = Counter()
    successful_logins = []
    suspicious = []
    brute_force_ips = []

    for line in lines:
        m = re.search(
            r"Failed password for (?:invalid user )?"
            r"(\S+) from ([\d.]+)", line)
        if m:
            failed_logins[f"{m.group(1)}@{m.group(2)}"] += 1
        m = re.search(
            r"Accepted (\S+) for (\S+) from ([\d.]+)", line)
        if m:
            successful_logins.append(
                f"{m.group(2)} via {m.group(1)} from {m.group(3)}")
        m = re.search(r"Invalid user (\S+) from ([\d.]+)", line)
        if m:
            user, ip = m.group(1), m.group(2)
            if ip not in [x.split("@")[-1] for x in failed_logins]:
                failed_logins[f"{user}@{ip}"] += 1
        m = re.search(r"sudo:.*?COMMAND=(.+)", line)
        if m:
            suspicious.append(f"sudo: {m.group(1).strip()[:150]}")

    ip_fail_count = Counter()
    for key, count in failed_logins.items():
        ip_fail_count[key.split("@")[-1]] += count
    for ip, cnt in ip_fail_count.items():
        if cnt >= 5:
            brute_force_ips.append(f"{ip} ({cnt} attempts)")

    failed_list = [f"{cnt}x {entry}"
                   for entry, cnt in failed_logins.most_common(15)]
    recommendations = []
    if brute_force_ips:
        bf_str = ", ".join(brute_force_ips[:5])
        recommendations.append(
            f"\U0001f534 Brute-force sources: {bf_str} "
            f"\u2014 verify Fail2Ban/CrowdSec")
    if len(failed_list) > 20:
        recommendations.append(
            "\U0001f7e1 High failed login volume "
            "\u2014 consider SSH key-only auth")
    if successful_logins:
        recommendations.append(
            "\u2139\ufe0f Review successful logins to confirm access")
    if not recommendations:
        recommendations.append(
            "\u2705 No suspicious auth activity")

    suspicious_set = list(dict.fromkeys(suspicious))[:5]
    if len(suspicious) > 5:
        suspicious_set.append(f"...and {len(suspicious) - 5} more sudo commands")
    return {
        "failed": failed_list or ["No failed logins."],
        "successful": (list(dict.fromkeys(successful_logins))[:15]
                       or ["No interactive logins."]),
        "suspicious": suspicious_set,
        "recommendations": recommendations,
    }


def analyze_kernel():
    """Parse kernel logs for hardware issues, OOM, and crashes."""
    lines = lines_since(LOG_PATHS["kern"])
    if not lines and os.path.isfile(LOG_PATHS["kern"]):
        j_out = run(
            'journalctl -k --since "24 hours ago" '
            '--no-pager 2>/dev/null | head -5000')
        lines = j_out.splitlines() if j_out else []

    hardware, oom_events, crashes = [], [], []
    hw_pat = re.compile(
        r"(hardware error|mce|machine check|pci error|edac|"
        r"ata.*error|I/O error|disk.*error|temperature)", re.I)
    oom_pat = re.compile(
        r"(oom[- ]?killer|out of memory|"
        r"killed process \d+|Memory cgroup out of memory)", re.I)
    crash_pat = re.compile(
        r"(kernel panic|BUG:|Oops:|general protection fault|"
        r"segmentation fault|Call Trace)", re.I)

    for line in lines:
        if hw_pat.search(line):
            hardware.append(line[:250])
        if oom_pat.search(line):
            oom_events.append(line[:250])
        if crash_pat.search(line):
            crashes.append(line[:250])

    hardware = list(dict.fromkeys(hardware))[:15]
    oom_events = list(dict.fromkeys(oom_events))[:15]
    crashes = list(dict.fromkeys(crashes))[:10]

    recommendations = []
    if crashes:
        recommendations.append(
            f"\U0001f534 {len(crashes)} kernel crash(es) "
            f"\u2014 `journalctl -k --priority=crit`")
    if oom_events:
        recommendations.append(
            f"\U0001f534 {len(oom_events)} OOM activations "
            f"\u2014 check container mem limits")
    if hardware:
        recommendations.append(
            f"\U0001f7e1 {len(hardware)} hardware event(s) "
            f"\u2014 `dmesg -T | tail -50` or SMART")
    if not recommendations:
        recommendations.append("\u2705 Kernel clean \u2014 no issues")

    return {
        "hardware": hardware or ["No hardware issues."],
        "oom": oom_events or ["No OOM events."],
        "crashes": crashes,
        "recommendations": recommendations,
    }


def analyze_docker():
    """Analyze Docker containers, stats, logs, and health."""
    raw = run(
        "docker ps --format '{{.Names}}|{{.Status}}|{{.Ports}}' "
        "2>/dev/null")
    if not raw:
        return [{
            "name": "Docker",
            "errors": ["Docker not running or no containers."],
            "restarts": 0,
            "issues": ["Docker daemon may be down."],
            "recommendations": ["Check: `systemctl status docker`"],
        }]

    containers = []
    for p in raw.splitlines():
        parts = p.split("|")
        c = {"name": parts[0], "status": parts[1]}
        c["ports"] = parts[2] if len(parts) > 2 else ""
        containers.append(c)

    results = []
    for c in containers:
        errors, issues, recs, restarts = [], [], [], 0

        # Stats: use --no-stream --format for reliable parsing
        stats = run(
            f"docker stats --no-stream --format "
            f"'{{{{.Name}}}}|{{{{.CPUPerc}}}}|{{{{.MemUsage}}}}' "
            f"{c['name']} 2>/dev/null")
        cpu, mem = "N/A", "N/A"
        if stats:
            parts = stats.split("|")
            if len(parts) >= 3:
                cpu = parts[1].strip()
                mem = parts[2].strip()
            elif len(parts) == 2:
                cpu = parts[1].strip()

        # Restart count
        ins = run(
            f"docker inspect {c['name']} "
            f"--format '{{{{.RestartCount}}}}' 2>/dev/null")
        try:
            restarts = int(ins) if ins else 0
        except ValueError:
            restarts = 0

        # Logs - get recent errors with context
        logs = run(
            f"docker logs --tail 300 {c['name']} 2>&1 | head -3000")
        err_pat = re.compile(
            r"\b(error|fatal|exception|panic|failed|failure|"
            r"segfault|killed)\b", re.I)
        raw_errors = []
        for ll in logs.splitlines():
            if err_pat.search(ll):
                raw_errors.append(ll.strip())
        
        # Deduplicate and limit, but keep meaningful context
        seen = set()
        errors = []
        for err in raw_errors:
            # Normalize for deduplication (remove timestamp)
            normalized = re.sub(r'^\d{4}[-T]\d{2}[^\s]*\s*', '', err)[:200]
            if normalized not in seen:
                seen.add(normalized)
                errors.append(err[:250])
            if len(errors) >= 5:
                break

        # Health check
        health = run(
            f"docker inspect {c['name']} "
            f"--format '{{{{.State.Health.Status}}}}' 2>/dev/null")
        if health == "unhealthy":
            issues.append("Health check FAILING")
        if restarts > 3:
            issues.append(f"Restarted {restarts} times")
        if safe_float(cpu) > 90:
            issues.append(f"High CPU: {cpu}")

        if errors:
            recs.append(
                f"`docker logs --tail 500 {c['name']} | "
                f"grep -iE 'error|fatal|panic'`")
        if restarts > 3:
            recs.append(f"Inspect: `docker inspect {c['name']}`")
        if health == "unhealthy":
            recs.append(f"Check health endpoint for {c['name']}")
        if not recs:
            recs.append("\u2705 Container healthy")

        results.append({
            "name": c["name"],
            "status": c["status"],
            "cpu": cpu,
            "memory": mem,
            "restarts": restarts,
            "errors": errors or ["No errors in recent logs."],
            "issues": issues,
            "recommendations": recs,
        })
    return results


def analyze_ufw():
    """Parse UFW/firewall logs for blocked traffic and scanners."""
    lines = lines_since(LOG_PATHS["ufw"])
    if not lines:
        lines = [l for l in lines_since(LOG_PATHS["kern"]) if "UFW" in l]
    if not lines:
        j = run(
            'journalctl -k --since "24 hours ago" --no-pager '
            '2>/dev/null | grep UFW | head -3000')
        lines = j.splitlines() if j else []

    blocked = Counter()
    suspicious_ips = Counter()
    for line in lines:
        m = re.search(r"SRC=([\d.]+)", line)
        if m:
            ip = m.group(1)
            blocked[ip] += 1
            if blocked[ip] >= 10:
                suspicious_ips[ip] = blocked[ip]

    blocked_list = [f"{ip}: {cnt} blocks"
                    for ip, cnt in blocked.most_common(8)]
    blocked_summary = f"{len(blocked)} unique IPs blocked"
    suspicious_list = [
        f"{ip} ({cnt} blocks — possible scan)"
        for ip, cnt in suspicious_ips.most_common(5)]

    recommendations = []
    if suspicious_ips:
        top = ", ".join(f"{ip} ({c})"
                         for ip, c in suspicious_ips.most_common(3))
        recommendations.append(
            f"\U0001f534 Top scanners: {top} "
            f"\u2014 consider permanent ban or CrowdSec")
    if len(blocked) > 50:
        recommendations.append(
            f"\U0001f7e1 {len(blocked)} unique IPs blocked")
    if not recommendations:
        recommendations.append(
            "\u2705 UFW normal, no persistent threats")

    return {
        "blocked": blocked_list or ["No blocked traffic in 24h."],
        "blocked_summary": blocked_summary,
        "suspicious": suspicious_list,
        "recommendations": recommendations,
    }


def analyze_fail2ban():
    """Parse Fail2Ban logs for bans and repeat offenders."""
    log = LOG_PATHS["fail2ban"]
    if not os.path.isfile(log):
        return {
            "banned": ["Fail2Ban log not found."],
            "repeat": [],
            "recommendations": [
                "Install: sudo apt install fail2ban && "
                "sudo systemctl enable --now fail2ban"],
        }

    lines = lines_since(log)
    banned_ips, unbanned_ips = Counter(), Counter()
    for line in lines:
        m = re.search(r"Ban ([\d.]+)", line)
        if m:
            banned_ips[m.group(1)] += 1
        m = re.search(r"Unban ([\d.]+)", line)
        if m:
            unbanned_ips[m.group(1)] += 1

    banned_list = [f"{ip} ({c} ban(s))"
                   for ip, c in banned_ips.most_common(15)]
    repeat = [f"{ip} ({c} ban(s))"
              for ip, c in banned_ips.most_common() if c > 2]

    recommendations = []
    if len(banned_ips) > 10:
        recommendations.append(
            f"\U0001f7e1 {len(banned_ips)} IPs banned "
            f"\u2014 review jail.local")
    if repeat:
        recommendations.append(
            f"\U0001f534 Repeat offenders: "
            f"{', '.join(repeat[:5])} "
            f"\u2014 increase bantime or permanent block")
    if not banned_ips:
        recommendations.append("\u2705 No new bans in 24h")
    else:
        recommendations.append(
            f"\u2139\ufe0f {len(banned_ips)} unique IP(s) banned in 24h")

    return {
        "banned": banned_list or ["No new bans in 24h."],
        "repeat": repeat,
        "recommendations": recommendations,
    }


def analyze_crowdsec():
    """Query CrowdSec for active decisions and alert count."""
    if not run("which cscli 2>/dev/null"):
        return {
            "decisions": ["CrowdSec (cscli) not installed."],
            "alerts": [],
            "recommendations": [
                "Install: "
                "https://doc.crowdsec.net/"
                "docs/getting_started/install_crowdsec"],
        }

    decisions = run(
        "sudo cscli decisions list -o json 2>/dev/null")
    alerts_total = run(
        "sudo cscli alerts list -o json 2>/dev/null | "
        "python3 -c 'import json,sys; "
        "d=json.load(sys.stdin); print(len(d))' 2>/dev/null")
    if not alerts_total:
        alerts_total = "N/A"

    decision_list = []
    if decisions and decisions not in ("", "[]"):
        try:
            decs = json.loads(decisions)
            types, origins = Counter(), Counter()
            for d in decs:
                types[d.get("type", "unknown")] += 1
                origins[d.get("scenario", "unknown")] += 1
            for t, c in types.most_common(10):
                decision_list.append(f"{c}x {t}")
            for o, c in origins.most_common(5):
                decision_list.append(f"  -> {o}: {c}")
        except Exception:
            decision_list = ["Failed to parse CrowdSec JSON."]
    else:
        decision_list = ["No active CrowdSec decisions."]

    recommendations = []
    total = sum(1 for x in decision_list if "x" in x)
    if total > 20:
        recommendations.append(
            f"\U0001f7e1 {total} active decisions "
            f"\u2014 review hub scenarios")
    if alerts_total != "N/A":
        try:
            if int(alerts_total) > 50:
                recommendations.append(
                    f"\U0001f7e1 {alerts_total} total alerts")
        except ValueError:
            pass
    if not recommendations:
        recommendations.append("\u2705 CrowdSec operating normally")

    return {
        "decisions": decision_list or ["No active decisions."],
        "alerts": [f"Total alerts on record: {alerts_total}"],
        "recommendations": recommendations,
    }


# ──────────────────────────────────────────────────────────────
# Report Builder
# ──────────────────────────────────────────────────────────────
def build_report():
    """Build a Telegram-friendly report string."""
    S = []
    hostname = run("hostname") or "unknown"
    ts = NOW.strftime('%Y-%m-%d %H:%M:%S')

    S.append(f"\U0001f4cb *Daily Deep Log Analysis Report*")
    S.append(f"\U0001f550 *Generated:* {ts}")
    S.append(f"\U0001f3a5 *Host:* {hostname}")
    S.append(f"\U0001f4c5 *Period:* Last 24 hours")
    S.append("")

    # Auditd
    a = analyze_auditd()
    S.append("=== *Auditd Log Summary* ===")
    S.append("- *Key events:*")
    for e in a["key"]:
        S.append(f"  {e}")
    S.append("- *Suspicious activities:*")
    for e in a["suspicious"]:
        S.append(f"  {e}")
    S.append("- *Policy violations:*")
    for v in a["violations"]:
        S.append(f"  {v}")
    S.append("- *Recommendations:*")
    for r in a["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # Syslog
    s = analyze_syslog()
    S.append("=== *Syslog Summary* ===")
    S.append(f"- *Errors:* {s['error_count']} | *Warnings:* {s['warning_count']}")
    if s["service_summary"]:
        S.append("- *Service restarts:*")
        for i in s["service_summary"]:
            S.append(f"  {i}")
    if s["errors"] and s["errors"] != ["No errors."]:
        S.append("- *Sample errors:*")
        for e in s["errors"]:
            S.append(f"  {e}")
    if s["warnings_list"]:
        S.append("- *Sample warnings:*")
        for w in s["warnings_list"]:
            S.append(f"  {w}")
    S.append("- *Recommendations:*")
    for r in s["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # Auth
    au = analyze_auth()
    S.append("=== *Auth Log Summary* ===")
    S.append("- *Failed login attempts:*")
    for f in au["failed"][:10]:
        S.append(f"  {f}")
    S.append("- *Successful logins:*")
    for su in au["successful"]:
        S.append(f"  {su}")
    S.append("- *Suspicious access:*")
    for sx in au["suspicious"]:
        S.append(f"  {sx}")
    if not au["suspicious"]:
        S.append("  None detected.")
    S.append("- *Recommendations:*")
    for r in au["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # Kernel
    k = analyze_kernel()
    S.append("=== *Kernel Log Summary* ===")
    S.append("- *Hardware issues:*")
    for h in k["hardware"]:
        S.append(f"  {h}")
    S.append("- *OOM / crashes:*")
    for o in k["oom"]:
        S.append(f"  {o}")
    for c in k["crashes"]:
        S.append(f"  {c}")
    if not k["oom"] and not k["crashes"]:
        S.append("  None detected.")
    S.append("- *Recommendations:*")
    for r in k["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # Docker
    docker = analyze_docker()
    S.append("=== *Docker Logs Summary* ===")
    healthy_count = 0
    for c in docker:
        has_errors = c.get("errors") and c["errors"] != ["No errors in recent logs."]
        has_issues = bool(c.get("issues"))
        
        if not has_errors and not has_issues:
            healthy_count += 1
            S.append(f"  🐳 *{c['name']}* — ✅ healthy")
            S.append(f"    CPU: {c.get('cpu', 'N/A')} | "
                     f"Mem: {c.get('memory', 'N/A')}")
            continue
        
        # Container with issues — show details
        status_flags = []
        if has_issues:
            status_flags.extend(c["issues"])
        if has_errors:
            status_flags.append(f"{len(c['errors'])} error(s)")
        
        S.append(f"  🐳 *{c['name']}* ({c.get('status', 'N/A')})")
        S.append(f"    CPU: {c.get('cpu', 'N/A')} | "
                 f"Mem: {c.get('memory', 'N/A')}")
        S.append(f"    ⚠️ Issues: {', '.join(status_flags)}")
        
        # Show actual error messages with explanations
        if has_errors and c['errors'] != ["No errors in recent logs."]:
            S.append("    *Recent errors:*")
            for err_text in c["errors"][:3]:
                # Add context/explanation based on error type
                explanation = ""
                if "context canceled" in err_text:
                    explanation = " — connection dropped during reconnection"
                elif "failed to sufficiently increase receive buffer" in err_text:
                    explanation = " — increase UDP buffer: `sysctl -w net.core.rmem_max=7168000`"
                elif "error=\"" in err_text:
                    explanation = " — internal service error"
                
                # Extract just the error message part (after timestamp)
                err_short = re.sub(r'^\d{4}[-T]\d{2}[^\s]*\s*', '', err_text)
                if len(err_short) > 120:
                    err_short = err_short[:117] + "..."
                S.append(f"      🔴 {err_short}{explanation}")
    if healthy_count > 0:
        S.append(f"  ℹ️ {healthy_count} other container(s) healthy")
    S.append("")

    # UFW
    u = analyze_ufw()
    S.append("=== *Firewall (UFW) Summary* ===")
    S.append("- *Blocked traffic:*")
    for b in u["blocked"]:
        S.append(f"  {b}")
    S.append("- *Suspicious IPs:*")
    for s in u["suspicious"]:
        S.append(f"  {s}")
    if not u["suspicious"]:
        S.append("  None detected.")
    S.append("- *Recommendations:*")
    for r in u["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # Fail2Ban
    f2 = analyze_fail2ban()
    S.append("=== *Fail2Ban Summary* ===")
    S.append("- *Banned IPs:*")
    for b in f2["banned"]:
        S.append(f"  {b}")
    S.append("- *Repeat offenders:*")
    for r in f2["repeat"]:
        S.append(f"  {r}")
    if not f2["repeat"]:
        S.append("  None detected.")
    S.append("- *Recommendations:*")
    for r in f2["recommendations"]:
        S.append(f"  {r}")
    S.append("")

    # CrowdSec
    cs = analyze_crowdsec()
    S.append("=== *CrowdSec Summary* ===")
    S.append("- *Decisions:*")
    for d in cs["decisions"]:
        S.append(f"  {d}")
    S.append("- *Alerts:*")
    for al in cs["alerts"]:
        S.append(f"  {al}")
    S.append("- *Recommendations:*")
    for r in cs["recommendations"]:
        S.append(f"  {r}")

    S.append("")
    S.append("---")
    S.append(f"🏁 *End of Report* | {ts}")
    return "\n".join(S)


def main():
    """Generate report, handle Telegram 4096-char limit by splitting."""
    import math
    
    full_report = build_report()
    telegram_limit = 4000  # margin for safety
    
    if len(full_report) <= telegram_limit:
        print(full_report)
        return
    
    # Split into two messages at the Docker section boundary
    docker_marker = "=== *Docker Logs Summary* ==="
    docker_idx = full_report.find(docker_marker)
    
    if docker_idx > 0:
        part1 = full_report[:docker_idx].rstrip() + "\n\n⚠️ Docker details continued below..."
        part2 = full_report[docker_idx:]
        print(f"[PART 1/2]\n{part1}")
        print(f"\n---\n\n[PART 2/2]\n{part2}")
    else:
        # Fallback: split at UFW section
        ufw_marker = "=== *Firewall"
        ufw_idx = full_report.find(ufw_marker)
        if ufw_idx > 0:
            part1 = full_report[:ufw_idx].rstrip() + "\n\n⚠️ Continued below..."
            part2 = full_report[ufw_idx:]
            print(f"[PART 1/2]\n{part1}")
            print(f"\n---\n\n[PART 2/2]\n{part2}")
        else:
            # Last resort: split at midpoint
            mid = len(full_report) // 2
            # Find a good break point
            for i in range(mid, mid + 200):
                if i < len(full_report) and full_report[i] == '\n':
                    print(full_report[:i])
                    print(f"\n---\n\n{full_report[i:]}")
                    break


if __name__ == "__main__":
    main()
