#!/usr/bin/env python3
import subprocess
import json
import re
import os
from datetime import datetime

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_latest_release():
    raw = run_command("curl -s https://api.github.com/repos/NousResearch/hermes-agent/releases/latest")
    try:
        data = json.loads(raw)
        tag = data.get('tag_name') or data.get('name') or ''
        body = data.get('body') or ''
        return tag, body
    except Exception:
        return None, None

def extract_notes(body, max_lines=6):
    if not body: return []
    lines = body.splitlines()
    bullets = []
    for line in lines:
        s = line.strip()
        if not s: continue
        bullets.append(s.lstrip('-').lstrip('*').strip())
        if len(bullets) >= max_lines: break
    return bullets

def get_hermes_version():
    current = run_command("hermes --version")
    latest_tag, changelog = get_latest_release()
    report = "🤖 **Hermes Agent Version Report**\n"
    report += f"- Current Version: `{current}`\n"
    if latest_tag:
        report += f"- Latest Available: `{latest_tag}`\n"
        if latest_tag.lower() not in (current or '').lower():
            report += "✨ A new version may be available! Run `hermes update`.\n"
        else:
            report += "✅ Up to date.\n"
        notes = extract_notes(changelog, max_lines=6)
        if notes:
            report += "\n✨ Release Notes\n"
            for n in notes: report += f"- {n}\n"
    return report

def get_system_package_updates():
    updates_raw = run_command("grep -E ' status installed ' /var/log/dpkg.log | tail -n 200")
    updated = sorted(set(re.findall(r"install\s+([^\s:]+)", updates_raw)))
    report = "\n💾 **System Package Updates (Today)**\n"
    if not updated:
        report += "- No packages updated today.\n"
    else:
        report += f"- Updated {len(updated)} packages: " + ", ".join(updated[:15]) + ("..." if len(updated) > 15 else "") + "\n"
    return report

def main():
    report = f"📊 **Daily Maintenance Report - {datetime.now().strftime('%Y-%m-%d')}**\n\n"
    report += get_hermes_version()
    report += get_system_package_updates()
    print(report)

if __name__ == "__main__":
    main()
