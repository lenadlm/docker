#!/usr/bin/env python3
import subprocess
import datetime
import os

# Configurable log paths
AUTH_LOG = "/var/log/auth.log"
SYSLOG = "/var/log/syslog"
AUDIT_LOG = "/var/log/audit/audit.log"

def get_output(cmd):
    try:
        return subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode('utf-8')
    except subprocess.CalledProcessError as e:
        return f"Error or No Events: {e.output.decode('utf-8') if e.output else str(e)}"

def main():
    report = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    report.append(f"🛡️ **LOGS & SECURITY AUDIT REPORT** - {now}")
    report.append("="*30)

    # 1. Auditd Summary
    report.append("\n📊 **AUDITD: Daily Summary**")
    report.append(get_output("sudo aureport -ts today --summary"))

    # 2. Auditd: Failed Login Attempts
    report.append("\n🚫 **AUDITD: Authentication Failures**")
    report.append(get_output("sudo aureport -au -ts today | grep -i 'no' | tail -n 10"))

    # 3. Auditd: AVC/AppArmor Denials
    report.append("\n⚠️ **AUDITD: Access Control Denials (AVC)**")
    report.append(get_output("sudo ausearch -m avc,apparmor -ts today | tail -n 15"))

    # 4. Fail2Ban Status
    report.append("\n⛓️ **FAIL2BAN: Active Bans**")
    report.append(get_output("sudo fail2ban-client status sshd"))

    # 5. UFW Recent Blocks
    report.append("\n🧱 **UFW: Recent Blocks (Top 5)**")
    report.append(get_output("sudo grep '[UFW BLOCK]' " + SYSLOG + " | tail -n 5"))

    # 6. Critical Syslog Errors
    report.append("\n🚨 **SYSTEM: Critical Logs**")
    report.append(get_output("sudo grep -E 'critical|error|failed|panic' " + SYSLOG + " | grep -v 'sshd' | tail -n 5"))

    final_report = "\n".join(report)
    print(final_report)

if __name__ == "__main__":
    main()
