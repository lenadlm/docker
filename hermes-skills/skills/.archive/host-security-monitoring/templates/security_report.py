#!/usr/bin/env python3
import subprocess
import json
import re
from datetime import datetime, timedelta

def run(cmd):
    return subprocess.run(cmd, shell=True, capture_output=True, text=True).stdout.strip()

def get_report():
    since = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    f2b = run(f"sudo grep -E 'Ban |Unban ' /var/log/fail2ban.log | grep '{since}'")
    crowdsec = run("sudo cscli decisions list -o json")
    audit = run("sudo ausearch -m USER_LOGIN,USER_AUTH -ts today --success no")
    
    # Process and format the report here...
    return f"Security Report for {since}\n..."

if __name__ == "__main__":
    print(get_report())
