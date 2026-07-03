# Stack Reference

What runs where in the homelab.

## Docker Host (192.168.1.220)

| Stack | Path | Services |
|-------|------|----------|
| main | `/mnt/shared/tmp/docker/` | n8n, postgres, redis, dockge |
| prowlarr | `/home/leo/deployments/prowlarr/` | Prowlarr indexer |
| dockhand | `/home/leo/dockhand_update/` | Docker auto-updater |

### Docker Networks

| Network | Subnet | Gateway |
|---------|--------|---------|
| internal_network | 172.30.0.0/24 | 172.30.0.1 |
| external_network | Bridge (host) | — |

### Volumes

All persistent data is under `/docker/<stack>/` on the Docker host.

## Proxmox (192.168.1.55)

| VM ID | Name | Role |
|-------|------|------|
| 115 | homeassistant | Home Assistant OS |
| 174 | ubuntu | General purpose (GPU passthrough planned) |

## Hermes Agent (192.168.1.222)

Automation scripts in `~/.hermes/scripts/` handle:
- Proxmox health monitoring (hourly)
- Docker update checks (every 6h)
- Network recon (Lily hourly)
- Security reports
- Daily log summaries

## External Services

- **GitHub:** `github.com/lenadlm/docker` — Infrastructure repo
- **Cloudflare:** `haos.lenadlm.dev` — HA external access (Cloudflare Tunnel)
- **Tailscale:** `100.70.60.0/24` — Mesh VPN