#!/usr/bin/env python3
import os, sys, json, datetime, requests, urllib3

# Proxmox API health report using API token authentication
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

HOST = os.environ.get('PROXMOX_HOST','192.168.1.55')
TOKEN_ID = os.environ.get('PROXMOX_TOKEN_ID', '')
TOKEN_SECRET = os.environ.get('PROXMOX_TOKEN_SECRET')

if not TOKEN_SECRET:
    print("ERROR: PROXMOX_TOKEN_SECRET not set", file=sys.stderr)
    sys.exit(2)

HEADERS = {'Authorization': f'PVEAPIToken={TOKEN_ID}={TOKEN_SECRET}'}
BASE = f'https://{HOST}:8006/api2/json'


def get(url):
    r = requests.get(url, headers=HEADERS, verify=False, timeout=15)
    r.raise_for_status()
    return r.json()


def build_report():
    lines = []
    t = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    lines.append(f"PROXMOX VE HEALTH REPORT - {t}")
    try:
        ver = get(BASE + '/version').get('data', {})
        lines.append(f"Proxmox VE version: {ver.get('version','unknown')}")
        nodes = get(BASE + '/nodes').get('data', [])
        if not nodes:
            lines.append("No nodes returned by API.")
        for node in nodes:
            node_name = node.get('node','unknown')
            lines.append(f"Node: {node_name}")
            node_status = get(BASE + f'/nodes/{node_name}/status').get('data', {})
            uptime = node_status.get('uptime', None)
            lines.append(f"  Uptime: {uptime if uptime is not None else 'unknown'} sec")
            # VMs
            qemu = get(BASE + f'/nodes/{node_name}/qemu').get('data', [])
            if qemu:
                lines.append("  VMs:")
                for vm in qemu:
                    vmid = vm.get('vmid')
                    vname = vm.get('name','')
                    try:
                        s = get(BASE + f'/nodes/{node_name}/qemu/{vmid}/status/current').get('data', {})
                        status = s.get('status','unknown')
                        uptime_vm = s.get('uptime','')
                    except Exception:
                        status = 'unknown'
                        uptime_vm = ''
                    lines.append(f"    {vmid} {vname} - {status} uptime={uptime_vm}")
            # Containers
            lxc = get(BASE + f'/nodes/{node_name}/lxc').get('data', [])
            if lxc:
                lines.append("  Containers:")
                for ct in lxc:
                    ct_id = ct.get('vmid')
                    ct_name = ct.get('name','')
                    try:
                        s = get(BASE + f'/nodes/{node_name}/lxc/{ct_id}/status/current').get('data', {})
                        status = s.get('status','unknown')
                        uptime_ct = s.get('uptime','')
                    except Exception:
                        status = 'unknown'
                        uptime_ct = ''
                    lines.append(f"    CT {ct_id} {ct_name} - {status} uptime={uptime_ct}")
    except Exception as e:
        lines.append(f"ERROR querying Proxmox API: {e}")
    return "\n".join(lines)


def main():
    report = build_report()
    # Append to local log file
    log = '/mnt/shared/tmp/proxmox_api_health.log'
    with open(log, 'a') as f:
        f.write(report + "\n\n")
    # Print to stdout — cron delivery mechanism sends this to Telegram
    print(report)

if __name__ == '__main__':
    main()
