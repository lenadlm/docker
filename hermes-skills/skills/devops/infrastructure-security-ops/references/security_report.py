#!/usr/bin/env python3
import subprocess
import json
import re
from datetime import datetime, timedelta

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_fail2ban_report():
    since_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    log_content = run_command(f"sudo grep -E 'Ban |Unban ' /var/log/fail2ban.log | grep '{since_date}'")
    bans = re.findall(r"Ban (\d+\.\d+\.\d+\.\d+)", log_content)
    unbans = re.findall(r"Unban (\d+\.\d+\.\d+\.\d+)", log_content)
    report = "🛡 **Fail2Ban Activity (Last 24h)**\n"
    report += f"- Banned IPs: {len(bans)}\n"
    if bans: report += "  - " + ", ".join(set(bans[:10])) + "\n"
    report += f"- Unbanned IPs: {len(unbans)}\n"
    if unbans: report += "  - " + ", ".join(set(unbans[:10])) + "\n"
    return report

def main():
    print(get_fail2ban_report())

if __name__ == "__main__":
    main()
