#!/usr/bin/env python3
import subprocess
import json
import os
import re
from datetime import datetime, timedelta

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return result.stdout.strip()
    except Exception as e:
        return f"Error running command: {e}"

def system_overview():
    uptime = run_command("uptime -p")
    load = run_command("cat /proc/loadavg").split()[:3]
    load_str = ", ".join(load)
    cpu = os.cpu_count()
    mem = run_command("free -m | grep Mem").split()
    mem_used = int(mem[2])
    mem_total = int(mem[1])
    mem_pct = round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0
    swap = run_command("free -m | grep Swap").split()
    swap_used = int(swap[2]) if len(swap) >= 3 else 0
    swap_total = int(swap[1]) if len(swap) >= 2 else 0
    swap_line = f" | 💿 Swap: {swap_used}MB/{swap_total}MB" if swap_total > 0 else ""
    disk = run_command("df -h / | tail -1").split()
    disk_pct = disk[4] if len(disk) > 4 else "unknown"
    zombies = run_command("ps aux | awk '$8 ~ /Z/ {count++} END {print count+0}'")
    zombie_alert = f" | 💀 {zombies} zombie(s)" if int(zombies) > 0 else ""
    updates = run_command("apt list --upgradable 2>/dev/null | wc -l")
    update_count = int(updates) - 1 if updates.isdigit() else 0
    update_line = f" | 📦 {update_count} pending updates" if update_count > 0 else " | ✅ System up to date"
    report = "💻 **System Overview**\n"
    report += f"⏱ Uptime: {uptime}\n"
    report += f"📊 Load: {load_str} ({cpu} CPU) | 💻 Memory: {mem_pct}%\n"
    report += f"📁 Root: {disk_pct}{update_line}{swap_line}{zombie_alert}"
    return report

def critical_services():
    system_units = [
        ('tailscaled', 'tailscaled'),
        ('docker', 'docker'),
        ('cron', 'cron'),
        ('sshd', 'SSH'),
        ('fail2ban', 'Fail2Ban'),
        ('crowdsec', 'CrowdSec'),
        ('ufw', 'UFW Firewall'),
    ]
    docker_containers = [
        ('cloudflared', 'Cloudflare Tunnel'),
    ]
    user_services = [
        ('hermes-gateway', 'Hermes Gateway'),
    ]
    report = "\n\n🛡 **Critical Services**\n"
    failed_list = []
    for unit, label in system_units:
        status = run_command(f"systemctl is-active {unit} 2>/dev/null").strip()
        if status == "active":
            report += f"✅ {label}\n"
        elif status == "inactive":
            report += f"🔴 {label}: inactive\n"
            failed_list.append(label)
        elif status == "":
            report += f"⚪ {label}: not installed\n"
        else:
            report += f"🔴 {label}: {status}\n"
            failed_list.append(label)
    for container, label in docker_containers:
        running = run_command(f"docker ps --format '{{{{.Names}}}}' 2>/dev/null | grep -x {container}")
        if running:
            report += f"✅ {label}\n"
        else:
            report += f"🔴 {label}: not running\n"
            failed_list.append(label)
    for service, label in user_services:
        status = run_command(f"systemctl --user is-active {service}.service 2>/dev/null").strip()
        if status == "active":
            report += f"✅ {label}\n"
        elif status == "" or status == "inactive":
            # Fallback: check if gateway process is running
            proc = run_command("ps aux | grep 'hermes.*gateway' | grep -v grep")
            if proc:
                report += f"✅ {label}\n"
            else:
                report += f"🔴 {label}: inactive\n"
                failed_list.append(label)
        else:
            report += f"🔴 {label}: {status}\n"
            failed_list.append(label)
    if failed_list:
        report += f"\n⚠️ Services down: {', '.join(failed_list)}"
    return report

def tailscale_network():
    try:
        ts_json = run_command("tailscale status --json 2>/dev/null")
        if not ts_json:
            return "\n\n🌐 **Tailscale Network**\n❌ Tailscale not available"
        data = json.loads(ts_json)
        backend = data.get("BackendState", "Unknown")
        peers = data.get("Peer", {})
        self_node = data.get("Self", {})
        health = data.get("Health", [])
        online = []
        offline = []
        for k, p in peers.items():
            name = p.get("HostName", "?")
            ip = p.get("TailscaleIPs", ["?"])[0] if p.get("TailscaleIPs") else "?"
            if p.get("Online", False):
                online.append(f"{name} ({ip})")
            else:
                last = p.get("LastSeen", "")
                if last:
                    last = last[:19].replace("T", " ")
                offline.append(f"{name} ({ip}) - last {last}")
        report = "\n\n🌐 **Tailscale Network**\n"
        report += f"🔗 State: {backend}"
        if self_node.get("Relay"):
            report += f" | Relay: {self_node['Relay']}"
        report += f"\n🟢 Online ({len(online)}): " + ", ".join(online[:5])
        if len(online) > 5:
            report += f" +{len(online)-5} more"
        report += f"\n🔴 Offline ({len(offline)}):\n" + "\n".join(offline[:5])
        if len(offline) > 5:
            report += f"\n...+{len(offline)-5} more offline"
        if health:
            report += "\n\n⚠️ Health Warnings:\n"
            for h in health:
                report += f"🔴 {h}\n"
        else:
            report += "\n✅ No health warnings"
        report += "\n\n📡 **Reachability Check:**\n"
        ts_docker = os.environ.get("TAILSCALE_DOCKER", "100.70.60.220")
        ts_hermes = os.environ.get("TAILSCALE_HERMES", "100.70.60.222")
        ts_ha = os.environ.get("TAILSCALE_HA", "100.70.60.123")
        for name, ip in [("docker", ts_docker), ("hermes", ts_hermes), ("homeassistant", ts_ha)]:
            result = run_command(f"tailscale ping --c=1 --timeout=5s {ip} 2>&1 | head -1")
            if "reply" in result.lower() or "ms" in result.lower():
                report += f"✅ {name} ({ip}): reachable\n"
            else:
                report += f"🔴 {name} ({ip}): UNREACHABLE\n"
        return report
    except Exception as e:
        return f"\n\n🌐 **Tailscale Network**\n⚠️ Check failed: {e}"

def get_fail2ban_report():
    print("Collecting Fail2Ban report...")
    since_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log_content = run_command(f"sudo grep -E 'Ban |Unban ' /var/log/fail2ban.log | grep '{since_date}'")
    bans = re.findall(r"Ban (\d+\.\d+\.\d+\.\d+)", log_content)
    unbans = re.findall(r"Unban (\d+\.\d+\.\d+\.\d+)", log_content)
    ban_counts = {}
    for ip in bans:
        ban_counts[ip] = ban_counts.get(ip, 0) + 1
    repeat_offenders = {ip: c for ip, c in ban_counts.items() if c > 1}
    report = "\n\n🛡 **Fail2Ban Activity (Last 24h)**\n"
    report += f"- Banned IPs: {len(bans)}"
    if bans:
        report += f"\n  - {', '.join(set(bans[:10]))}"
        if len(set(bans)) > 10:
            report += "..."
    report += f"\n- Unbanned IPs: {len(unbans)}"
    if unbans:
        report += f"\n  - {', '.join(set(unbans[:10]))}"
        if len(set(unbans)) > 10:
            report += "..."
    if repeat_offenders:
        report += f"\n🔁 Repeat offenders: {', '.join(f'{ip}({c}x)' for ip, c in repeat_offenders.items())}"
    return report

def get_crowdsec_report():
    print("Collecting CrowdSec report...")
    decisions_json = run_command("sudo cscli decisions list -o json")
    try:
        decisions = json.loads(decisions_json)
    except:
        decisions = []
    alerts = run_command("sudo cscli alerts list -o json 2>/dev/null | python3 -c 'import json,sys; print(len(json.load(sys.stdin)))' 2>/dev/null || echo 0").strip()
    report = "\n\n👥 **CrowdSec Active Decisions**\n"
    if not decisions:
        report += "✅ No active bans/decisions."
    else:
        report += f"🚫 Active decisions: {len(decisions)}\n"
        scenarios = {}
        for d in decisions:
            s = d.get('scenario', 'unknown')
            scenarios[s] = scenarios.get(s, 0) + 1
        for s, count in scenarios.items():
            report += f"  - {s}: {count}\n"
    report += f"\n📊 Total alerts on record: {alerts}"
    return report

def get_ssh_analysis():
    auth_log = run_command("sudo grep 'Failed password' /var/log/auth.log 2>/dev/null | tail -20")
    if not auth_log:
        return "\n\n🔐 **SSH Authentication**\n✅ No failed SSH attempts in recent logs"
    lines = auth_log.strip().split('\n')
    ips = re.findall(r"from (\d+\.\d+\.\d+\.\d+)", auth_log)
    users = re.findall(r"for (?:invalid user )?(\S+) from", auth_log)
    ip_counts = {}
    for ip in ips:
        ip_counts[ip] = ip_counts.get(ip, 0) + 1
    top_ips = sorted(ip_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    user_counts = {}
    for u in users:
        user_counts[u] = user_counts.get(u, 0) + 1
    top_users = sorted(user_counts.items(), key=lambda x: x[1], reverse=True)[:5]
    report = "\n\n🔐 **SSH Authentication (Recent)**\n"
    report += f"❌ Failed attempts: {len(lines)}\n"
    report += "\n🎯 Top source IPs:\n"
    for ip, count in top_ips:
        report += f"  - {ip}: {count} attempts\n"
    report += "\n👤 Targeted accounts:\n"
    for user, count in top_users:
        report += f"  - {user}: {count} attempts\n"
    success = run_command("sudo grep 'Accepted' /var/log/auth.log 2>/dev/null | tail -5")
    if success:
        report += "\n✅ Recent successful logins:\n"
        for line in success.strip().split('\n'):
            match = re.search(r"Accepted \S+ for (\S+) from (\S+)", line)
            if match:
                report += f"  - {match.group(1)} from {match.group(2)}\n"
    return report

def get_auditd_report():
    print("Collecting Auditd report...")
    failed_logins = run_command("sudo ausearch -m USER_LOGIN,USER_AUTH -ts today --success no")
    event_count = failed_logins.count("type=USER_")
    report = "\n\n🔍 **Auditd Security Events (Today)**\n"
    if event_count == 0:
        report += "✅ No suspicious login failures detected via auditd today."
    else:
        report += f"❌ Failed login attempts: {event_count}\n"
        ips = re.findall(r"addr=(\d+\.\d+\.\d+\.\d+)", failed_logins)
        accts = re.findall(r"acct=\"([^\"]+)\"", failed_logins)
        if ips:
            report += f"  - Top targeted IPs: {', '.join(set(ips[:5]))}\n"
        if accts:
            report += f"  - Targeted accounts: {', '.join(set(accts[:5]))}\n"
    return report

def get_ufw_summary():
    blocked = run_command("sudo grep 'UFW BLOCK' /var/log/ufw.log 2>/dev/null | grep -oP 'SRC=\K[\d.]+' | sort | uniq -c | sort -rn | head -10")
    total = run_command("sudo grep -c 'UFW BLOCK' /var/log/ufw.log 2>/dev/null || echo 0").strip()
    unique_ips = run_command("sudo grep 'UFW BLOCK' /var/log/ufw.log 2>/dev/null | grep -oP 'SRC=\K[\d.]+' | sort -u | wc -l").strip()
    report = "\n\n🧱 **UFW Firewall Summary**\n"
    report += f"📊 Total blocks: {total} | Unique IPs: {unique_ips}\n"
    if blocked:
        report += "🎯 Top blocked sources:\n"
        for line in blocked.strip().split('\n'):
            parts = line.strip().split()
            if len(parts) == 2:
                count, ip = parts
                label = "(possible scanner)" if int(count) > 50 else ""
                report += f"  - {ip}: {count} blocks {label}\n"
    return report

def get_log_alerts():
    errors = run_command("journalctl -p err --since '24h ago' --no-pager -q | head -5")
    err_count = run_command("journalctl -p err --since '24h ago' --no-pager -q 2>/dev/null | wc -l")
    report = "\n\n📋 **System Log Alerts**\n"
    if errors:
        report += f"🔴 Errors (24h): {err_count}\n"
        report += f"  Sample: {errors[:200]}\n"
    else:
        report += "✅ No system errors in last 24h\n"
    return report

def get_docker_container_health():
    ps = run_command("docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Image}}'")
    if not ps:
        return ""
    report = "\n\n🐳 **Container Health**\n"
    issues = []
    for line in ps.split('\n'):
        if not line:
            continue
        parts = line.split('\t')
        name = parts[0]
        status = parts[1] if len(parts) > 1 else "unknown"
        if "unhealthy" in status.lower():
            issues.append(f"🔴 {name}: UNHEALTHY")
        elif "exited" in status.lower():
            code = run_command(f"docker inspect {name} --format '{{{{.State.ExitCode}}}}' 2>/dev/null")
            emoji = "💀" if code != "0" else "🟡"
            issues.append(f"{emoji} {name}: exited (code {code})")
        else:
            report += f"✅ {name}: {status}\n"
    if issues:
        report += "".join(f"{i}\n" for i in issues)
    return report

def main():
    date_str = datetime.now().strftime('%Y-%m-%d %H:%M')
    report = f"🚀 **Enhanced Security Report - {date_str}**"
    report += f"\n\n{system_overview()}"
    report += critical_services()
    report += tailscale_network()
    report += get_fail2ban_report()
    report += get_crowdsec_report()
    report += get_ssh_analysis()
    report += get_auditd_report()
    report += get_ufw_summary()
    report += get_docker_container_health()
    report += get_log_alerts()
    print(report)

if __name__ == "__main__":
    main()
