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

def get_report():
    since_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    
    # Fail2Ban
    f2b_log = run_command(f"sudo grep -E 'Ban |Unban ' /var/log/fail2ban.log | grep '{since_date}'")
    bans = len(re.findall(r"Ban ", f2b_log))
    
    # CrowdSec
    cs_json = run_command("sudo cscli decisions list -o json")
    try:
        cs_count = len(json.loads(cs_json))
    except:
        cs_count = 0
        
    # Auditd
    audit_events = run_command("sudo ausearch -m USER_LOGIN,USER_AUTH -ts today --success no")
    failed_logins = audit_events.count("type=USER_")

    report = f"🛡 Security Report {since_date}\n"
    report += f"- Fail2Ban Bans: {bans}\n"
    report += f"- CrowdSec Decisions: {cs_count}\n"
    report += f"- Auditd Failed Logins: {failed_logins}\n"
    return report

if __name__ == "__main__":
    print(get_report())
