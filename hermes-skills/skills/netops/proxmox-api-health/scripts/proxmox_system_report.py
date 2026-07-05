#!/usr/bin/env python3
"""
Proxmox VE Comprehensive System Report Generator
Fetches all system details via API and outputs a formatted plain-text report.

Usage:
    python3 /path/to/proxmox_system_report.py

Requires:
    - ~/.hermes/secrets/proxmox_token.env with PROXMOX_HOST, PROXMOX_TOKEN_ID,
      PROXMOX_TOKEN_SECRET
    - curl

Output: formatted report to stdout; redirect to file as needed.
"""
import subprocess, json, os
from datetime import datetime

env_file = os.path.expanduser("~/.hermes/secrets/proxmox_token.env")
env = {}
with open(env_file) as f:
    for line in f:
        line = line.strip().replace("export ", "")
        if "=" in line:
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()

HOST = env.get("PROXMOX_HOST", "192.168.1.55")
tid = env.get("PROXMOX_TOKEN_ID", "")
ts = env.get("PROXMOX_TOKEN_SECRET", "")
AUTH = f"PVEAPIToken={tid}={ts}"
BASE = f"https://{HOST}:8006/api2/json"


def api(path):
    url = f"{BASE}{path}"
    r = subprocess.run(
        ["curl", "-s", "-k", "-H", f"Authorization: {AUTH}", url],
        capture_output=True, text=True,
    )
    try:
        return json.loads(r.stdout).get("data")
    except (json.JSONDecodeError, TypeError):
        return None


# --- COLLECT ---
v = api("/version")
ns = api("/nodes/pve/status")
stor = api("/storage")
cr = api("/cluster/resources")
disks = api("/nodes/pve/disks/list")
zfs_detail = api("/nodes/pve/disks/zfs")
rrd = api("/nodes/pve/rrddata?timeframe=hour")
sub = api("/nodes/pve/subscription")

now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- BUILD REPORT ---
lines = []
def L(s=""):
    lines.append(s)

L()
L("=" * 62)
L(f"  PROXMOX VE — SYSTEM REPORT")
L(f"  {now}")
L("=" * 62)
L()

if v:
    L(f"  Host:      {HOST}")
    L(f"  Version:   Proxmox VE {v.get('release','?')} ({v.get('version','?')})")
else:
    L(f"  Host:      {HOST}")

if ns:
    cpu_pct = (ns.get("cpu", 0) or 0) * 100
    uptime_s = ns.get("uptime", 0) or 0
    d = uptime_s // 86400
    h = (uptime_s % 86400) // 3600
    m = (uptime_s % 3600) // 60

    ci = ns.get("cpuinfo", {})
    mem = ns.get("memory", {}) or {}
    mem_total = mem.get("total", 0) or 0
    mem_used = mem.get("used", 0) or 0
    sw = ns.get("swap", {}) or {}
    sw_total = sw.get("total", 0) or 0
    sw_used = sw.get("used", 0) or 0
    rf = ns.get("rootfs", {}) or {}
    load_avg = ns.get("loadavg", ["0","0","0"])
    kernel = ns.get("kversion", "?")

    L(f"  Uptime:    {d}d {h}h {m}m")
    L(f"  Kernel:    {kernel}")
    L()
    L("── Hardware ──────────────────────────────────────────────")
    L(f"  CPU:       {ci.get('model','?'):40} | "
      f"{ci.get('cores','?')}C/{ci.get('cpus','?')}T @ {ci.get('mhz','?')}MHz")
    L(f"  CPU Util:  {cpu_pct:.1f}%")

    if mem_total:
        L(f"  Memory:    {mem_used/1024**3:.1f}/{mem_total/1024**3:.1f}GB "
          f"({mem_used/mem_total*100:.1f}%)")
    if sw_total:
        L(f"  Swap:      {sw_used/1024**2:.0f}/{sw_total/1024**2:.0f}MB "
          f"({sw_used/sw_total*100:.1f}%)")
    else:
        L(f"  Swap:      none configured")
    if rf.get("total"):
        rused = rf.get("used", 0) or 0
        rtotal = rf.get("total", 0) or 0
        L(f"  Root Disk: {rused/1024**3:.0f}/{rtotal/1024**3:.0f}G "
          f"({rused/rtotal*100:.1f}%)")

    try:
        l1, l5, l15 = float(load_avg[0]), float(load_avg[1]), float(load_avg[2])
        L(f"  Load Avg:  {l1:.2f} / {l5:.2f} / {l15:.2f}")
    except (ValueError, IndexError):
        pass

    wait = ns.get("wait", None)
    if wait is not None:
        L(f"  I/O Wait:  {wait*100:.1f}%")

L()

if disks:
    L("── Physical Disks ───────────────────────────────────────")
    for d in disks:
        dev = d.get("devpath", d.get("dev", "?"))
        size = d.get("size", 0) or 0
        model = d.get("model", "?").strip()
        serial = d.get("serial", "")
        L(f"  {dev:12}  {size//1024**3:>4}G  {model[:35]:35}  {serial}")
    L()

if zfs_detail:
    L("── ZFS Pools ────────────────────────────────────────────")
    for p in (zfs_detail if isinstance(zfs_detail, list) else [zfs_detail]):
        name = p.get("name", p.get("pool", "?"))
        scan = p.get("scan", "?")
        if scan and scan != "?":
            L(f"  {name:12}  scan={scan[:60]}")
        else:
            L(f"  {name:12}")
    L()

if stor:
    L("── Storage Pools ────────────────────────────────────────")
    for s in sorted(stor, key=lambda x: x.get("storage", "")):
        name = s.get("storage", "?")
        stype = s.get("type", "?")
        content = s.get("content", "")
        shared = "SHARED" if s.get("shared", 0) else "local"
        L(f"  {name:12}  {stype:8}  {content:30}  {shared}")
    L()

if cr:
    vms = [r for r in cr if r.get("type") == "qemu"]
    cts = [r for r in cr if r.get("type") == "lxc"]
    L(f"── Virtual Machines ({len(vms)} total, "
      f"{len([v for v in vms if v.get('status')=='running'])} running)")
    L(f"  {'VM ID':>6}  {'Name':22}  {'Status':8}  {'CPU':4}  "
      f"{'Memory':16}  {'Disk':14}")
    L(f"  {'─'*6}  {'─'*22}  {'─'*8}  {'─'*4}  "
      f"{'─'*16}  {'─'*14}")
    for vm in sorted(vms, key=lambda x: x.get("vmid", 0)):
        vmid = vm.get("vmid", "?")
        name = vm.get("name", "?")
        status = vm.get("status", "?")
        cpus = vm.get("cpus", "?")
        mem_s = f"{(vm.get('mem',0) or 0)//1024**2}/{(vm.get('maxmem',0) or 0)//1024**2}MB"
        disk_s = f"{(vm.get('disk',0) or 0)//1024**3}/{(vm.get('maxdisk',0) or 0)//1024**3}G"
        L(f"  {vmid:>6}  {name:22}  {status:8}  {str(cpus):>4}  "
          f"{mem_s:16}  {disk_s:14}")
    L()
    L(f"  Containers (LXC): {len(cts)}")
    L()

if rrd and len(rrd) > 1:
    last = rrd[-1]
    netin = last.get("netin", 0) or 0
    netout = last.get("netout", 0) or 0
    L(f"  Net I/O:   IN: {netin/1024:.1f} KB/s  OUT: {netout/1024:.1f} KB/s")

if sub:
    L(f"  Subscription: {sub.get('status','?')}")
L()
L(f"  TLS CA:    valid until 2036 (self-signed)")
L(f"  Source:    {HOST}:8006 (Proxmox API)")
L("=" * 62)
L()

# Print report
print("\n".join(lines))