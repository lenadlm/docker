# Proxmox VE API Response Data Structures

This reference documents the exact response shapes returned by common Proxmox VE API endpoints, including type quirks discovered through real usage.

## `GET /nodes/{node}/status`

```json
{
  "cpu": 0.025,                        // float (0.0–1.0) — multiply by 100 for %
  "cpuinfo": {
    "cores": 8,                         // int — physical cores
    "cpus": 8,                          // int — logical threads
    "model": "Intel(R) Core(TM) i7-9700T CPU @ 2.00GHz",
    "mhz": 800.0,                       // float — current frequency
    "hvm": 1,                           // int — hardware virtualization enabled
    "flags": [...]                      // array of strings — CPU feature flags
  },
  "memory": {
    "total": 33416736768,               // int — bytes (÷ 1024³ for GB)
    "used": 13058830336,                // int — bytes
    "free": 20357906432,                // int — bytes
    "available": 31948750848            // int — bytes (accounts for reclaimable)
  },
  "swap": {
    "total": 0,                         // int — bytes (0 = no swap configured)
    "used": 0,
    "free": 0
  },
  "rootfs": {
    "total": 214748364800,              // int — bytes
    "used": 13958643712,                // int — bytes
    "free": 199789625088,
    "avail": 199789625088
  },
  "loadavg": ["0.00", "0.00", "0.00"], // ARRAY OF STRINGS — cast to float!
  "uptime": 2396,                       // int — seconds
  "wait": 0.002,                        // float — I/O wait fraction
  "ksm": { "shared": 0 },              // dict — KSM shared memory in bytes
  "kversion": "Linux 7.0.2-3-pve #1 SMP PREEMPT_DYNAMIC PMX ...",
  "pveversion": "pve-manager/9.1.11/8eac2c86f015bdda",
  "status": "running"                   // string — "running" or "unknown"
}
```

### Key Gotchas

| Field | Expected Type | Actual Type | Notes |
|-------|--------------|-------------|-------|
| `memory` | flat `maxmem`/`mem` | **nested dict** | Access via `data["memory"]["total"]` NOT `data["maxmem"]` |
| `loadavg` | float array | **string array** | Must cast: `float(loadavg[0])` |
| `cpu` | percentage | **fraction** | Multiply by 100 for display |
| `swap` | flat fields | **nested dict** | Same pattern as `memory` |
| `rootfs` | flat fields | **nested dict** | Same pattern — has `total`, `used`, `free`, `avail` |
| `wait` | percentage | **fraction** | I/O wait as 0.0–1.0 |
| `cpuinfo.cpus` | missing | **present** | Number of threads (logical cores) |
| `cpuinfo.cores` | missing | **present** | Number of physical cores |

## `GET /cluster/resources`

Returns a flat array of resource objects. Each object has:

```json
{
  "type": "qemu",           // string — "qemu" | "lxc" | "storage" | "node"
  "vmid": 105,              // int — VM/CT ID (absent for node/storage entries)
  "name": "docker",         // string — display name
  "status": "running",      // string — "running" | "stopped"
  "cpus": 4,                // int — allocated CPU cores (may be absent)
  "maxmem": 8589934592,     // int — max memory in bytes
  "mem": 3724533760,        // int — current memory usage in bytes
  "maxdisk": 137438953472,  // int — max disk in bytes
  "disk": 0,                // int — current disk usage in bytes
  "node": "pve",            // string — hosting node
  "uptime": 123456          // int — seconds (only when running)
}
```

### Key Gotchas

| Field | Notes |
|-------|-------|
| `cpus` | May be absent for stopped VMs when queried via cluster/resources |
| `mem` | 0 for stopped VMs |
| `disk` | 0 for some API return formats; actual usage may come from storage status |
| `maxdisk` | May report full allocation, not thin-provisioned size |

## `GET /nodes/{node}/disks/list`

Returns array of physical disk objects:

```json
{
  "devpath": "/dev/nvme0n1",
  "dev": "/dev/nvme0n1",
  "size": 1024209543168,      // int — bytes
  "model": "Dahua C900 M.2 2280 NVMe 1TB SSD ",
  "serial": "NAYD02A36A05157",
  "osdid": "",
  "type": "nvme"              // string — "nvme", "sata", "ssd", "hdd"
}
```

## `GET /nodes/{node}/disks/zfs`

Returns ZFS pool detail including vdev and scan info. Use this instead of `/nodes/{node}/zfs` which may return empty.

## `GET /nodes/{node}/rrddata?timeframe=hour`

Returns time-series data array. Last element is most recent:

```json
{
  "time": 1687350000,    // int — unix timestamp
  "cpu": 0.024,          // float — CPU fraction
  "iowait": 0.0007,      // float — I/O wait fraction
  "load1": "0.00",       // STRING — cast to float
  "load5": "0.00",       // STRING
  "load15": "0.00",      // STRING
  "netin": 27448.0,      // float — bytes/s
  "netout": 36250.0,     // float — bytes/s
  "mem": 39.1,           // float — memory usage percentage
  "diskr": 0.0,          // float — disk read bytes/s
  "diskw": 0.0           // float — disk write bytes/s
}
```

### Key Gotchas

- `load1`, `load5`, `load15` are **strings** just like in node status — always cast to float
- `netin`/`netout` are in bytes/s — divide by 1024 for KB/s
- `mem` is a percentage already (0–100), not a fraction

## `GET /nodes/{node}/certificates/info`

Returns certificate info:

```json
{
  "filename": "pve-root-ca.pem",
  "issuer": "/CN=Proxmox Virtual Environment/OU=.../O=PVE Cluster Manager CA",
  "notbefore": 1700000000,
  "notafter": 2085000000       // int — unix timestamp
}
```

## `GET /nodes/{node}/subscription`

```json
{
  "status": "notfound",     // string — "active" | "notfound" | "expired"
  "level": null,            // string or null
  "productname": null,      // string or null
  "key": null               // string or null
}
```

## Common Patterns for Safe Parsing

### Memory (always a nested dict)
```python
mem = ns.get("memory", {})
total = mem.get("total", 0) or 0
used = mem.get("used", 0) or 0
pct = used / total * 100 if total else 0
```

### Load average (always strings)
```python
load = ns.get("loadavg", ["0", "0", "0"])
l1, l5, l15 = float(load[0]), float(load[1]), float(load[2])
```

### CPU (always fraction 0–1)
```python
cpu_pct = (ns.get("cpu", 0) or 0) * 100
```

### Swap and Rootfs (always nested dicts)
```python
swap = ns.get("swap", {})
rootfs = ns.get("rootfs", {})
```