# Proxmox VE API Endpoints Quick Reference

## Authentication
All API calls use PVE API tokens. Format:
```
Authorization: PVEAPIToken=<TOKEN_ID>=<TOKEN_SECRET>
```
Token stored in `~/.hermes/secrets/proxmox_token.env`:
```
export PROXMOX_HOST=192.168.1.55
export PROXMOX_TOKEN_ID=root@pam!hermes
export PROXMOX_TOKEN_SECRET=<actual-secret>
```

## Base URL
```
https://<PROXMOX_HOST>:8006/api2/json
```

## Core Endpoints

### Cluster-Level (recommended for full inventory)
| Endpoint | Purpose |
|----------|---------|
| `GET /version` | PVE version check |
| `GET /nodes` | List all cluster nodes |
| `GET /cluster/resources` | All resources across the cluster (VMs, CTs, storage) — includes stopped VMs |
| `GET /cluster/resources?type=vm` | VM resources only |

### Node-Level (running VMs only)
| Endpoint | Purpose |
|----------|---------|
| `GET /nodes/{node}/status` | Node uptime, load, memory |
| `GET /nodes/{node}/qemu` | Running VMs on node |
| `GET /nodes/{node}/lxc` | Running containers on node |
| `GET /nodes/{node}/qemu/{vmid}/status/current` | Single VM state |
| `GET /nodes/{node}/qemu/{vmid}/config` | Single VM config |

### Storage
| Endpoint | Purpose |
|----------|---------|
| `GET /nodes/{node}/storage` | Configured storage on node |
| `GET /nodes/{node}/storage/{storage}/content` | Content listing on a storage |

## Common Patterns

### Full cluster inventory (includes stopped VMs)
```bash
curl -s -H "Authorization: PVEAPIToken=${PROXMOX_TOKEN_ID}=${PROXMOX_TOKEN_SECRET}" \
  "https://${PROXMOX_HOST}:8006/api2/json/cluster/resources" | python3 -m json.tool
```

### Quick summary of VMs
```bash
curl -s -H "Authorization: PVEAPIToken=${PROXMOX_TOKEN_ID}=${PROXMOX_TOKEN_SECRET}" \
  "https://${PROXMOX_HOST}:8006/api2/json/cluster/resources" | python3 -c \
  'import sys,json; data=json.load(sys.stdin).get("data",[]); [print(f"{x.get(\"type\",\"?\")} {x.get(\"vmid\",\"?\")}: {x.get(\"name\",\"?\")} - {x.get(\"status\",\"?\")}") for x in data]'
```

### Version check
```bash
curl -s -H "Authorization: PVEAPIToken=${PROXMOX_TOKEN_ID}=${PROXMOX_TOKEN_SECRET}" \
  "https://${PROXMOX_HOST}:8006/api2/json/version" | python3 -c 'import sys,json; print(json.load(sys.stdin).get("data",{}).get("version","unknown"))'
```

### Node resource usage
```bash
curl -s -H "Authorization: PVEAPIToken=${PROXMOX_TOKEN_ID}=${PROXMOX_TOKEN_SECRET}" \
  "https://${PROXMOX_HOST}:8006/api2/json/nodes/pve/status" | python3 -c \
  'import sys,json; d=json.load(sys.stdin).get("data",{}); print(f"CPU: {d.get(\"cpu\",\"?\")*100:.1f}%, Mem: {d.get(\"memory\",{}).get(\"used\",0)/1e9:.1f}/{d.get(\"memory\",{}).get(\"total\",0)/1e9:.1f}GB")'
```

## Pitfalls
- `/nodes/{node}/qemu` only returns **running** VMs — stopped VMs are invisible from this endpoint
- Always use `/cluster/resources` for the full VM/CT inventory including stopped resources
- The API token must have the `PVEAuditor` role for read-only access
- TLS verification: use `-k` only for testing; prefer verified certificates in production
