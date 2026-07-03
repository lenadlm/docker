#!/usr/bin/env python3
"""Combine all Proxmox data into final report."""
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

def api(path):
    url = f"https://{HOST}:8006/api2/json{path}"
    r = subprocess.run(["curl", "-s", "-k", "-H", f"Authorization: PVEAPIToken={tid}={ts}", url],
                       capture_output=True, text=True)
    try: return json.loads(r.stdout).get("data")
    except: return None

def fmt(n):
    return f"{n:,.1f}"

# Collect data
v = api("/version")
ns = api("/nodes/pve/status")
stor = api("/storage")
cr = api("/cluster/resources")
disks = api("/nodes/pve/disks/list")
zfs = api("/nodes/pve/zfs")
rrd = api("/nodes/pve/rrddata?timeframe=hour")
sub = api("/nodes/pve/subscription")

# Build report dict
report = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "host": "192.168.1.55",
    "version": f"Proxmox VE {v.get('release')} ({v.get('version')})" if v else "?",
}

if ns:
    ci = ns.get("cpuinfo", {})
    cpu_pct = (ns.get("cpu", 0) or 0) * 100
    uptime_s = ns.get("uptime", 0) or 0
    total_mem = ns.get("memory", {}).get("total", 0) or 0
    used_mem = ns.get("memory", {}).get("used", 0) or 0
    sw = ns.get("swap", {}) or {}
    rf = ns.get("rootfs", {}) or {}
    load_avg = ns.get("loadavg", []) or []
    kernel = ns.get("kversion", "?")

    report["uptime"] = f"{uptime_s//86400}d {(uptime_s%86400)//3600}h {(uptime_s%3600)//60}m"
    report["cpu"] = f"{ci.get('model','?')} | {ci.get('cores','?')}C/{ci.get('cpus','?')}T @ {ci.get('mhz','?')}MHz"
    report["cpu_usage"] = f"{cpu_pct:.1f}%"
    report["memory"] = f"{used_mem/1024**3:.1f}/{total_mem/1024**3:.1f}GB ({used_mem/total_mem*100:.1f}%)"
    report["swap"] = f"{sw.get('used',0)/1024**2:.0f}/{sw.get('total',0)/1024**2:.0f}MB" if sw.get('total',0) else "none"
    report["rootfs"] = f"{(rf.get('used',0) or 0)/1024**3:.0f}/{(rf.get('total',0) or 0)/1024**3:.0f}G ({(rf.get('used',0) or 0)/(rf.get('total',1) or 1)*100:.1f}%)"
    report["kernel"] = kernel
    if len(load_avg) >= 3:
        report["load"] = f"{float(load_avg[0]):.2f} / {float(load_avg[1]):.2f} / {float(load_avg[2]):.2f}"

if disks:
    report["disks"] = []
    for d in disks:
        report["disks"].append({
            "dev": d.get("devpath", d.get("dev", "?")),
            "size": f"{d.get('size',0)//1024**3}G",
            "model": d.get("model","?").strip(),
            "serial": d.get("serial","")
        })

if zfs:
    pools = zfs if isinstance(zfs, list) else [zfs]
    report["zfs_pools"] = []
    for p in pools:
        sz = p.get("size", 0) or 0
        al = p.get("alloc", 0) or 0
        report["zfs_pools"].append({
            "name": p.get("name","?"),
            "health": p.get("health","?"),
            "usage": f"{al//1024**3}/{sz//1024**3}G ({al/sz*100:.1f}%)" if sz else "?"
        })

if stor:
    report["storage_pools"] = []
    for s in sorted(stor, key=lambda x: x.get("storage","")):
        report["storage_pools"].append({
            "name": s.get("storage","?"),
            "type": s.get("type","?"),
            "content": s.get("content",""),
            "shared": "SHARED" if s.get("shared",0) else "local"
        })

if cr:
    vms = [r for r in cr if r.get("type") == "qemu"]
    cts = [r for r in cr if r.get("type") == "lxc"]
    report["vms"] = []
    for vm in sorted(vms, key=lambda x: x.get("vmid",0)):
        report["vms"].append({
            "vmid": vm.get("vmid","?"),
            "name": vm.get("name","?"),
            "status": vm.get("status","?"),
            "mem": f"{((vm.get('mem',0) or 0)//1024**2)}/{((vm.get('maxmem',0) or 0)//1024**2)}MB",
            "disk": f"{((vm.get('disk',0) or 0)//1024**3)}/{((vm.get('maxdisk',0) or 0)//1024**3)}G",
            "cpus": vm.get("cpus","?")
        })
    report["containers"] = len(cts)

if rrd and len(rrd) > 1:
    last = rrd[-1]
    report["load"] = f"{float(last.get('load1',0)):.2f} / {float(last.get('load5',0)):.2f} / {float(last.get('load15',0)):.2f}"
    report["netio"] = f"IN: {last.get('netin',0)/1024:.1f} KB/s  OUT: {last.get('netout',0)/1024:.1f} KB/s"

if sub:
    report["subscription"] = f"{sub.get('status','?')} / {sub.get('level','?')} / {sub.get('productname','?')}"

# Print final report
print()
print("╔══════════════════════════════════════════════════════════╗")
print("║     PROXMOX VE — SYSTEM REPORT                          ║")
print("║     " + report["timestamp"] + "                         ║")
print("╚══════════════════════════════════════════════════════════╝")
print()
print(f"  Host:      {report['host']}")
print(f"  Version:   {report['version']}")
print(f"  Uptime:    {report['uptime']}")
print(f"  Kernel:    {report.get('kernel','?')}")
print()
print("── Hardware ──────────────────────────────────────────────")
print(f"  CPU:       {report['cpu']}")
print(f"  CPU Util:  {report['cpu_usage']}")
print(f"  Memory:    {report['memory']}")
print(f"  Swap:      {report.get('swap','none')}")
print(f"  Root Disk: {report['rootfs']}")
if "load" in report:
    print(f"  Load Avg:  {report['load']}")
if "netio" in report:
    print(f"  Net I/O:   {report['netio']}")
print()
if "disks" in report:
    print("── Physical Disks ───────────────────────────────────────")
    for d in report["disks"]:
        print(f"  {d['dev']:12}  {d['size']:6}  {d['model'][:35]:35}  {d['serial']}")
    print()
if "zfs_pools" in report:
    print("── ZFS Pools ────────────────────────────────────────────")
    for p in report["zfs_pools"]:
        print(f"  {p['name']:12}  health={p['health']:7}  {p['usage']}")
    print()
if "storage_pools" in report:
    print("── Storage Pools ────────────────────────────────────────")
    for s in report["storage_pools"]:
        print(f"  {s['name']:12}  {s['type']:8}  {s['content']:30}  {s['shared']}")
    print()
if "vms" in report:
    print("── Virtual Machines ─────────────────────────────────────")
    print(f"  {'VM ID':>6}  {'Name':20}  {'Status':8}  {'CPU':4}  {'Memory':14}  {'Disk':12}")
    print(f"  {'─'*6}  {'─'*20}  {'─'*8}  {'─'*4}  {'─'*14}  {'─'*12}")
    for vm in report["vms"]:
        print(f"  {vm['vmid']:>6}  {vm['name']:20}  {vm['status']:8}  {str(vm['cpus']):>4}  {vm['mem']:14}  {vm['disk']:12}")
    print()
    print(f"  Containers: {report['containers']}")
print()
if "subscription" in report:
    print(f"  Subscription: {report['subscription']}")
else:
    print(f"  Subscription: not found")
print()