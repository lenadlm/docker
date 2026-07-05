#!/usr/bin/env python3
"""
Lily's Parallel Subnet Scanner — runs 3 nmap chunks simultaneously across 192.168.1.0/24.

Usage:
    python3 parallel_subnet_scan.py [--on-demand] [--ports PORTS]

Output:
    - /mnt/shared/tmp/lily_recon_latest.txt
    - /mnt/shared/tmp/lily_recon_on_demand_YYYY-MM-DD_HH-MM.txt  (if --on-demand)
    - /mnt/shared/tmp/lily_baseline.json  (updated)

Requires: sudo nmap, Python 3.8+
"""

import subprocess
import json
import xml.etree.ElementTree as ET
import os
import argparse
from datetime import datetime


def main():
    parser = argparse.ArgumentParser(description="Lily parallel subnet scanner")
    parser.add_argument("--on-demand", action="store_true", help="Save with on-demand timestamp")
    parser.add_argument("--ports", default="22,80,443,111,135,139,445,3389,8080,3128,2049,548,5900,8443,19999,10443,8888,9090",
                        help="Comma-separated ports to scan")
    args = parser.parse_args()

    outdir = "/mnt/shared/tmp"
    baseline_file = os.path.join(outdir, ".lily_baseline.json")
    os.makedirs(outdir, exist_ok=True)

    # Load baseline
    try:
        with open(baseline_file) as f:
            baseline = json.load(f)
        hosts_data = baseline.get("hosts", {})
        if isinstance(hosts_data, dict):
            old_host_set = set(hosts_data.keys())
        elif isinstance(hosts_data, list):
            old_host_set = set(hosts_data)
        else:
            old_host_set = set()
    except (FileNotFoundError, json.JSONDecodeError):
        old_host_set = set()

    # 3 chunks to cover /24 in parallel
    chunks = [
        ("192.168.1.0/26", "Chunk1"),
        ("192.168.1.64/26", "Chunk2"),
        ("192.168.1.128/25", "Chunk3"),
    ]
    results_xml = {}
    start_time = datetime.now()

    for subnet, label in chunks:
        cmd = [
            "sudo", "nmap", "-sS", "-sV", "-O", "--osscan-guess",
            subnet,
            "-p", args.ports,
            "--min-rate=100", "-T4", "--defeat-rst-ratelimit",
            "--host-timeout=30s", "-oX", "-"
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            results_xml[label] = result.stdout

    duration = (datetime.now() - start_time).total_seconds()

    # Parse all XML
    all_hosts = {}
    for xml in results_xml.values():
        all_hosts.update(parse_nmap_xml(xml))

    current_hosts_set = set(all_hosts.keys())
    new_hosts = current_hosts_set - old_host_set
    removed_hosts = old_host_set - current_hosts_set
    open_port_count = sum(len(h['ports']) for h in all_hosts.values())

    # Build report
    report_type = "ON-DEMAND SCAN" if args.on_demand else "HOURLY RECON"
    lines = [
        "=" * 50,
        f"🌐 LILY NETWORK REPORT — {report_type}",
        "=" * 50,
        f"Generated: {datetime.now().isoformat()}",
        "Subnet: 192.168.1.0/24",
        "Scan: SYN + sV + OS (parallel, -T4)",
        f"Duration: {duration:.1f}s",
        "-" * 50,
        "📊 SUMMARY",
        f"  Hosts up: {len(all_hosts)}",
        f"  New hosts: {len(new_hosts)}",
        f"  Removed hosts: {len(removed_hosts)}",
        f"  Total open ports: {open_port_count}",
        "-" * 50,
    ]

    if new_hosts:
        lines.append("🆕 NEW HOSTS:")
        for ip in sorted(new_hosts):
            h = all_hosts[ip]
            lines.append(f"  ✨ {ip} ({h['hostname'] or ip})")
            lines.append(f"    OS: {h['os']}")
            lines.append(f"    MAC: {h['mac']}")
            for p in h['ports']:
                lines.append(f"    {p}")
    else:
        lines.append("✅ No new hosts detected.")

    lines.append("-" * 50)
    lines.append("📋 DETAILED HOST INVENTORY")
    for ip in sorted(all_hosts.keys()):
        h = all_hosts[ip]
        status = "[NEW!]" if ip in new_hosts else ""
        lines.append(f"  📍 {ip} ({h['hostname'] or ip}) {status}".strip())
        lines.append(f"    OS: {h['os']}")
        lines.append(f"    MAC: {h['mac']}")
        if h['ports']:
            lines.append("    Open Ports:")
            for p in h['ports']:
                lines.append(f"      {p}")
        else:
            lines.append("    Open Ports: (none)")
        lines.append("")

    # Write files
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    if args.on_demand:
        report_path = os.path.join(outdir, f"lily_recon_manual_{timestamp}.txt")
    else:
        report_path = os.path.join(outdir, f"lily_recon_{timestamp}.txt")

    report_text = "\n".join(lines + ["=" * 50])

    with open(report_path, "w") as f:
        f.write(report_text)
    with open(os.path.join(outdir, "lily_recon_latest.txt"), "w") as f:
        f.write(report_text)

    # Update baseline (always dict format going forward)
    with open(baseline_file, "w") as f:
        json.dump({"hosts": all_hosts, "last_updated": datetime.now().isoformat()}, f, indent=2)

    print(report_text)


def parse_nmap_xml(xml_str):
    hosts = {}
    try:
        root = ET.fromstring(xml_str)
        for host in root.findall('.//host'):
            addr = host.find('address[@addrtype="ipv4"]')
            if addr is None:
                continue
            ip = addr.get('addr')
            host_entry = {"ip": ip, "ports": [], "os": "Unknown", "mac": "Unknown", "hostname": ""}
            hostname_el = host.find('.//hostname')
            if hostname_el is not None:
                host_entry["hostname"] = hostname_el.get('name')
            for a in host.findall('address'):
                if a.get('addrtype') == 'mac':
                    host_entry["mac"] = a.get('addr')
            os_el = host.find('.//osmatch')
            if os_el is not None:
                host_entry["os"] = os_el.get('name')
            for port in host.findall('.//port'):
                if port.find('state').get('state') == 'open':
                    portid = port.get('portid')
                    svc = port.find('service')
                    svc_name = svc.get('name') if svc is not None else ''
                    svc_prod = svc.get('product') if svc is not None else ''
                    svc_ver = svc.get('version') if svc is not None else ''
                    desc = f"{portid}/tcp open ({svc_name}"
                    if svc_prod:
                        desc += f" {svc_prod}"
                    if svc_ver:
                        desc += f" {svc_ver}"
                    desc += ")"
                    host_entry["ports"].append(desc)
            hosts[ip] = host_entry
    except ET.ParseError:
        pass
    return hosts


if __name__ == "__main__":
    main()
