#!/usr/bin/env python3
# Lily - Hourly Parallel Network Recon with Telegram Alerts
# Run from cron every hour
from hermes_tools import terminal, write_file
import json
import subprocess
import concurrent.futures
import re
import time
from datetime import datetime, timedelta

WORK_DIR = '/mnt/shared/tmp'
BASELINE_FILE = f'{WORK_DIR}/.lily_baseline.json'
REPORT_PREFIX = 'lily_recon'

def run_parallel_nmap():
    """Run parallel nmap scans with SYN + service version + OS detection"""
    chunks = [
        ("192.168.1.0/26", "1-64"),
        ("192.168.1.64/26", "65-128"),
        ("192.168.1.128/25", "129-256"),
    ]
    
    def scan_chunk(cidr, label):
        txt_out = f"/tmp/lily_chunk_{label}.txt"
        cmd = (
            f"sudo nmap -sS -sV -O --osscan-guess "
            f"-p 22,23,25,53,80,110,111,135,139,143,161,"
            f"443,445,587,993,995,1433,1521,1723,2049,"
            f"3128,3306,3389,5432,5900,6379,8080,8443,9090,"
            f"22222,27017 --min-rate=100 -T4 --defeat-rst-ratelimit "
            f"--host-timeout=30s "
            f"--append-output -oN {txt_out} "
            f"{cidr} 2>&1"
        )
        terminal(cmd, timeout=60)
        return f"/tmp/lily_chunk_{label}.txt"
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        future_to_chunk = {executor.submit(scan_chunk, cidr, label): label
                          for cidr, label in chunks}
        results = []
        for future in concurrent.futures.as_completed(future_to_chunk):
            results.append(future.result())
    
    # Combine
    combined = f"{WORK_DIR}/lily_combined.txt"
    with open(combined, 'w') as out:
        for tmpfile in results:
            try:
                with open(tmpfile) as f:
                    out.write(f.read())
            except:
                pass
    return combined

def parse_nmap_results(combined_file):
    """Parse nmap output into structured list"""
    out = terminal(f"cat {combined_file}")['output']
    hosts = []
    current = None
    
    for line in out.split('\n'):
        if 'Nmap scan report for' in line:
            m = re.search(r'([\d.]+)\s*(?:\(([\d.]+)\)|$)', line)
            if m:
                current = {
                    'hostname': m.group(1).strip(),
                    'ip': m.group(2) if m.group(2) else m.group(1),
                    'mac': None,
                    'os': None,
                    'ports': [],
                    'timeout': False
                }
        elif 'MAC Address:' in line and current:
            m = re.search(r'MAC Address:\s+([0-9A-Fa-f:]+)', line)
            if m:
                current['mac'] = m.group(1)
        elif 'OS details:' in line and current:
            current['os'] = line.split('OS details:')[1].strip()
        elif 'Device type:' in line and current:
            current['os'] = line.split('Device type:')[1].strip()
        elif ('tcp' in line.lower() or 'udp' in line.lower()) and 'open' in line.lower():
            if current:
                parts = line.strip().split()
                if len(parts) >= 3:
                    port = parts[0].rstrip('/tcp').rstrip('/udp')
                    service = parts[2] if len(parts) > 2 else ''
                    version = ' '.join(parts[3:]) if len(parts) > 3 else ''
                    current['ports'].append({
                        'port': port,
                        'service': service,
                        'version': version
                    })
        elif 'Host seems down' in line or 'timed out' in line:
            if current:
                current['timeout'] = True
        
        if current and (line.strip() == '' or line.startswith('\n')):
            if current['ip'] or current['hostname']:
                hosts.append(current)
            current = None
    
    # Deduplicate
    uniq = {}
    for h in hosts:
        key = h['ip'] or h['hostname']
        if key:
            if key in uniq:
                if len(h['ports']) > len(uniq[key]['ports']):
                    uniq[key] = h
            else:
                uniq[key] = h
    
    return list(uniq.values())

def load_baseline():
    try:
        with open(BASELINE_FILE, 'r') as f:
            return json.load(f)
    except:
        return {}

def save_baseline(hosts):
    data = {}
    for h in hosts:
        key = h['ip'] or h['hostname']
        data[key] = h
    with open(BASELINE_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def detect_changes(hosts, baseline):
    current_dict = {h['ip'] or h['hostname']: h for h in hosts}
    new = [h for key, h in current_dict.items() if key not in baseline]
    removed = [h for key, h in baseline.items() if key not in current_dict]
    return new, removed

def format_report(hosts, new, removed, duration):
    lines = []
    lines.append("=" * 60)
    lines.append("🌐 LILY NETWORK REPORT — HOURLY RECON")
    lines.append("=" * 60)
    lines.append(f"Generated: {datetime.now().isoformat()}")
    lines.append(f"Subnet: 192.168.1.0/24")
    lines.append(f"Duration: {duration}s")
    lines.append(f"Scan: SYN + sV + OS (parallel, -T4)")
    lines.append("-" * 60)
    lines.append(f"📊 SUMMARY")
    lines.append(f"  Hosts up: {len(hosts)}")
    lines.append(f"  New hosts: {len(new)}")
    lines.append(f"  Removed hosts: {len(removed)}")
    lines.append(f"  Total open ports: {sum(len(h['ports']) for h in hosts)}")
    lines.append("-" * 60)
    
    if new:
        lines.append("🆕 NEW HOSTS:")
        for h in new:
            ip = h.get('ip') or h.get('hostname')
            lines.append(f"  ✨ {h.get('hostname', '?')} ({ip})")
            if h.get('os'):
                lines.append(f"    OS: {h['os']}")
            if h.get('mac'):
                lines.append(f"    MAC: {h['mac']}")
            for p in h.get('ports', []):
                lines.append(f"    {p['port']} open ({p.get('service', '?')} {p.get('version', '')})")
        lines.append("-" * 60)
    
    if removed:
        lines.append("❌ HOSTS OFFLINE:")
        for h in removed:
            ip = h.get('ip') or h.get('hostname')
            lines.append(f"  ⚠️  {h.get('hostname', '?')} ({ip})")
        lines.append("-" * 60)
    
    lines.append("📋 DETAILED HOST INVENTORY")
    for h in sorted(hosts, key=lambda x: x.get('ip') or '0'):
        ip = h.get('ip') or h.get('hostname')
        hostname = h.get('hostname') if h.get('hostname') != ip else '-'
        tag = " [NEW!]" if ip in [n.get('ip') or n.get('hostname') for n in new] else ""
        lines.append(f"  📍 {ip} ({hostname}){tag}")
        
        if h.get('timeout'):
            lines.append("    ⚠️  Host timed out — partial data")
        else:
            if h.get('os'):
                lines.append(f"    OS: {h['os']}")
            if h.get('mac'):
                lines.append(f"    MAC: {h['mac']}")
            if h.get('ports'):
                lines.append(f"    Open Ports ({len(h['ports'])}):")
                for p in h['ports']:
                    svc = f"{p.get('service', '?')} {p.get('version', '')}".strip()
                    lines.append(f"      {p['port']} → {svc}")
            else:
                lines.append("    No open ports")
        lines.append("")
    
    lines.append("=" * 60)
    return '\n'.join(lines)

def send_to_telegram(report):
    """Send report to Telegram (via hermes)"""
    try:
        # First send a shorter alert summary if there are new/removed hosts
        # We'll rely on hermes cron delivery for full report
        return True
    except:
        return False

def main():
    start = time.time()
    print("[Lily] Hourly network recon starting...")
    
    # 1. Scan
    combined_file = run_parallel_nmap()
    print("[Lily] Scan complete. Parsing...")
    
    # 2. Parse
    hosts = parse_nmap_results(combined_file)
    print(f"[Lily] Found {len(hosts)} hosts")
    
    # 3. Load baseline and detect changes
    baseline = load_baseline()
    new_hosts, removed_hosts = detect_changes(hosts, baseline)
    print(f"[Lily] Changes: +{len(new_hosts)} new, -{len(removed_hosts)} gone")
    
    # 4. Save new baseline
    save_baseline(hosts)
    
    # 5. Format report
    duration = round(time.time() - start, 1)
    report = format_report(hosts, new_hosts, removed_hosts, duration)
    
    # 6. Save to files
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M')
    report_file = f"{WORK_DIR}/{REPORT_PREFIX}_{timestamp}.txt"
    latest_file = f"{WORK_DIR}/lily_recon_latest.txt"
    
    write_file(report_file, report)
    write_file(latest_file, report)
    
    print(f"\n[Report] {report_file}")
    print(f"[Size] {len(report)} bytes")
    
    # 7. Telegram alert if changes
    if new_hosts or removed_hosts:
        alert_lines = []
        if new_hosts:
            alert_lines.append(f"🆕 {len(new_hosts)} new hosts detected")
            for h in new_hosts:
                ip = h.get('ip') or h.get('hostname')
                alert_lines.append(f"  - {ip}")
        if removed_hosts:
            alert_lines.append(f"❌ {len(removed_hosts)} hosts went offline")
        alert = "Lily Network Recon:\n" + "\n".join(alert_lines)
        # Use hermes messaging for Telegram
        print(f"[Alert]\n{alert}")
    
    # For the cron job, the report will be delivered via the cron 'deliver' mechanism
    
    print("[Lily] Done.")

if __name__ == '__main__':
    main()
