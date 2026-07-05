#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime

def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_docker_stats():
    info = run_command("docker info --format '{{json .}}'")
    try:
        data = json.loads(info)
        status = f"✅ Docker is running on {data.get('Name', 'unknown')} ({data.get('OperatingSystem', 'unknown')})\n"
        status += f"- Version: {data.get('ServerVersion')}\n"
        status += f"- Containers: {data.get('Containers')} (Running: {data.get('ContainersRunning')}, Stopped: {data.get('ContainersStopped')})\n"
        status += f"- Resource Metrics: {data.get('NCPU')} CPUs, {data.get('MemTotal') / (1024**3):.2f} GiB total\n"
        status += f"- Debug Mode: {data.get('Debug')}\n"
    except:
        status = "❌ Docker status check failed.\n"
    return status

def get_disk_usage():
    df = run_command("docker system df --format '{{json .}}'")
    try:
        lines = df.split('\n')
        report = "\n💾 **Disk Usage**\n"
        for line in lines:
            if not line: continue
            data = json.loads(line)
            dtype = data.get('Type', 'Unknown')
            total = data.get('TotalCount', 0)
            active = data.get('ActiveCount', 0)
            size = data.get('Size', '0B')
            reclaim = data.get('Reclaimable', '0%')
            report += f"- {dtype}: {total} total ({active} active), {size} size ({reclaim} reclaimable)\n"
    except:
        report = "\n💾 **Disk Usage (Fallback)**\n"
        report += run_command("docker system df") + "\n"
    return report

def get_container_report():
    ps = run_command("docker ps -a --format '{{.Names}}\t{{.Status}}\t{{.Ports}}'")
    lines = ps.split('\n')
    report = "\n📦 **Container Status & Ports**\n"
    if not lines or not lines[0]:
        report += "- No containers found.\n"
    else:
        for line in lines:
            if not line: continue
            parts = line.split('\t')
            name = parts[0]
            status = parts[1] if len(parts) > 1 else "unknown"
            ports = parts[2] if len(parts) > 2 else "none"
            report += f"- **{name}**: {status}\n"
            if ports and ports != "none":
                report += f"  - Ports: `{ports}`\n"
    return report

def get_resource_usage():
    stats = run_command("docker stats --no-stream --format '{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}'")
    lines = stats.split('\n')
    report = "\n📊 **Resource Usage**\n"
    for line in lines:
        if not line: continue
        parts = line.split('\t')
        report += f"- {parts[0]}: CPU {parts[1]}, Mem {parts[2]}\n"
    return report

def get_docker_issues():
    unhealthy = run_command("docker ps --filter \"health=unhealthy\" --format \"{{.Names}}\"")
    crashed = run_command("docker ps -a --filter \"status=exited\" --format \"{{.Names}} ({{.Status}})\"")
    report = "\n⚠️ **Detected Issues**\n"
    issues_found = False
    if unhealthy:
        report += f"- Unhealthy containers: {unhealthy}\n"
        issues_found = True
    if crashed:
        report += f"- Stopped/Crashed containers: {crashed}\n"
        issues_found = True
    if not issues_found:
        report += "- No immediate health or crash issues detected.\n"
    return report

def main():
    report = f"🐳 **Daily Docker Report - {datetime.now().strftime('%Y-%m-%d')}**\n\n"
    report += get_docker_stats()
    report += get_disk_usage()
    report += get_container_report()
    report += get_resource_usage()
    report += get_docker_issues()
    print(report)

if __name__ == "__main__":
    main()
