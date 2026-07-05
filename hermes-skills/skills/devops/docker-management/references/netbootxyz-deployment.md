# netbootxyz Deployment — Remote Docker Host Worked Example

## Canonical Location

The canonical compose file location is now **`/mnt/shared/tmp/docker/`** on the Docker host (192.168.1.220). Previously it was at `/docker/netbootxyz/` — that directory is now removed. All cron jobs and auto-update scripts reference the new path.

## Source
- Compose URL: `https://raw.githubusercontent.com/lenadlm/docker/refs/heads/main/mpc/netxyz/docker-compose.yml`
- Live file: `/mnt/shared/tmp/docker/docker-compose.yml`
- Target: `192.168.1.220` (Docker host, user `leo`)

## Compose File
```yaml
services:
  netbootxyz:
    image: ghcr.io/netbootxyz/netbootxyz
    container_name: netbootxyz
    environment:
      - MENU_VERSION=2.0.84
      - NGINX_PORT=80
      - WEB_APP_PORT=3000
      - TFTPD_OPTS=--dhcp-range=192.168.1.0,proxy --dhcp-match=set:bios,option:client-arch,0 --dhcp-match=set:uefi64,option:client-arch,7 --dhcp-boot=tag:bios,netboot.xyz.kpxe --dhcp-boot=tag:uefi64,netboot.xyz.efi
    volumes:
      - /docker/netbootxyz/config:/config
      - /mnt/shared/assets:/assets
    networks:
      - external_network
    ports:
      - "3300:3000"
      - "69:69/udp"
      - "8380:80"
    cap_add:
      - NET_ADMIN
    restart: unless-stopped

networks:
  external_network:
    external: true
```

**Note:** Even though the compose file lives at `/mnt/shared/tmp/docker/`, the config volume still mounts from `/docker/netbootxyz/config` (the original NFS mount path on the host). These host paths are independent of the compose file's own location.

## Environment / Port Mapping Mismatch (Resolved)
The original compose source URL has `WEB_APP_PORT=3300` but the port mapping is `3300:3000`. The discrepancy was fixed on the deployed copy:
- `WEB_APP_PORT` set to `3000` (matching the internal container port)

## Deployment Steps (executed on remote host)
```bash
# 1. Verify prerequisites
docker --version && docker compose version
docker network ls --filter name=external_network

# 2. Create directories
sudo mkdir -p /docker/netbootxyz /mnt/shared/assets /mnt/shared/tmp/docker
sudo chmod 755 /docker/netbootxyz /mnt/shared/assets /mnt/shared/tmp/docker
sudo chown leo:leo /docker/netbootxyz /mnt/shared/assets /mnt/shared/tmp/docker

# 3. Fetch compose file to canonical location
curl -sS -o /mnt/shared/tmp/docker/docker-compose.yml \
  https://raw.githubusercontent.com/lenadlm/docker/refs/heads/main/mpc/netxyz/docker-compose.yml

# 4. Fix port-mapping mismatch (if needed)
sed -i 's/WEB_APP_PORT=3300/WEB_APP_PORT=3000/' /mnt/shared/tmp/docker/docker-compose.yml

# 5. Add ProxyDHCP + cap_add to compose file
# (Add TFTPD_OPTS env var and cap_add: - NET_ADMIN as shown above)

# 6. Deploy
cd /mnt/shared/tmp/docker
docker compose pull
docker compose up -d

# 7. Verify
sleep 5
docker inspect netbootxyz --format '{{.State.Health.Status}}'
# Expected: healthy

docker ps --filter name=netbootxyz --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'

# Test ports
curl -sS -o /dev/null -w 'HTTP %{http_code}' http://localhost:8380   # → 200
curl -sS -o /dev/null -w 'HTTP %{http_code}' http://localhost:3300   # → 200

# Verify ProxyDHCP is active
docker logs netbootxyz 2>&1 | grep "proxy on subnet"
# → "DHCP, proxy on subnet 192.168.1.0"
```

## Verification Table
| Check | Expected | Result |
|-------|----------|--------|
| Container status | Up (healthy) | ✅ |
| Port 69/udp (TFTP) | Listening | ✅ |
| Port 8380→80 (HTTP boot) | HTTP 200 | ✅ |
| Port 3300→3000 (Web UI) | HTTP 200 | ✅ |
| ProxyDHCP active | log line | ✅ |

## Access URLs (post-deployment)
- Web UI: `http://192.168.1.220:3300`
- HTTP Boot: `http://192.168.1.220:8380`
- TFTP: `tftp://192.168.1.220:69`

## ProxyDHCP Configuration (LAN Only)

netboot.xyz runs dnsmasq as its DHCP/TFTP server. To expose the PXE boot menu automatically on the LAN, enable ProxyDHCP. This broadcasts boot offers alongside the existing DHCP server (no config changes needed on the router).

**Correct syntax** — just the network address with `,proxy`:
```
dhcp-range=192.168.1.0,proxy
```
Do NOT use a start-end range (e.g., `192.168.1.50,192.168.1.150,proxy`) — dnsmasq rejects that in proxy mode.

**Capability required**: ProxyDHCP needs `NET_ADMIN` to send raw broadcast packets. Add it to the compose file:
```yaml
services:
  netbootxyz:
    ...
    cap_add:
      - NET_ADMIN
```

**`docker update` does NOT support `--cap-add`**. You must:
1. Add `cap_add: - NET_ADMIN` to the compose file
2. Run `docker compose up -d` (recreates the container)

**Persistence**: Editing `/etc/dnsmasq.conf` inside the container is NOT persistent — the container recreates with the default config. Instead, use the `TFTPD_OPTS` env var:
```yaml
services:
  netbootxyz:
    environment:
      - TFTPD_OPTS=--dhcp-range=192.168.1.0,proxy
```
This passes extra args through the dnsmasq wrapper script (`/usr/local/bin/dnsmasq-wrapper.sh`) which forwards `$@` to dnsmasq. The env var survives `docker compose down/up`.

**Verification**: Check container logs for the confirmation line:
```
dnsmasq-dhcp[NN]: DHCP, proxy on subnet 192.168.1.0
```

**Full debug workflow** (if it fails):
```bash
# 1. Test syntax directly
docker exec netbootxyz dnsmasq --test -C /dev/null --dhcp-range='192.168.1.0,proxy'
# → "syntax check OK"

# 2. Check if capability is missing (look for this error)
docker logs netbootxyz 2>&1 | grep -i capability
# → "process is missing required capability NET_ADMIN"

# 3. Verify the env var is being used
docker exec netbootxyz ps aux | grep dnsmasq
# Should show --dhcp-range=192.168.1.0,proxy in the command line

# 4. Verify ProxyDHCP is active
docker logs netbootxyz 2>&1 | grep "proxy on subnet"
# → "DHCP, proxy on subnet 192.168.1.0"
```

**Note**: ProxyDHCP only works for one subnet per `dhcp-range` line. Add multiple lines if needed (e.g., VLAN):
```yaml
- TFTPD_OPTS=--dhcp-range=192.168.1.0,proxy --dhcp-range=192.168.2.0,proxy
```

## BIOS + UEFI Dual-Boot Support

ProxyDHCP alone (`--dhcp-range=192.168.1.0,proxy`) broadcasts that boot services are available, but **does not tell clients what file to fetch**. Without a `dhcp-boot` directive, PXE clients simply see "boot server available" and hang.

netboot.xyz provides separate boot files for BIOS (legacy) and UEFI:

### Available Boot Files

| File | Architecture | Use Case |
|------|-------------|----------|
| `netboot.xyz.kpxe` | BIOS x86_64 (Legacy PXE) | Standard BIOS PXE boot |
| `netboot.xyz-undionly.kpxe` | BIOS x86_64 | BIOS with undionly driver (smaller, 112 KB) |
| `netboot.xyz.efi` | UEFI x86_64 | Standard UEFI HTTP/PXE boot |
| `netboot.xyz-snp.efi` | UEFI x86_64 SNP | Simple Network Protocol |
| `netboot.xyz-snponly.efi` | UEFI x86_64 SNP only | Minimal UEFI |
| `netboot.xyz-arm64.efi` | UEFI ARM64 | ARM-based devices (RPi, etc.) |

All boot files live at `/config/menus/` (the TFTP root).

### Client Architecture Detection (dnsmasq)

Use `dhcp-match` tags to serve the right boot file per client:

```bash
# Match BIOS (client-arch 0) — tag as "bios"
--dhcp-match=set:bios,option:client-arch,0

# Match UEFI x86-64 (client-arch 7) — tag as "uefi64"
--dhcp-match=set:uefi64,option:client-arch,7
```

Then serve the appropriate boot file per tag:

```bash
--dhcp-boot=tag:bios,netboot.xyz.kpxe     # BIOS clients get .kpxe
--dhcp-boot=tag:uefi64,netboot.xyz.efi    # UEFI clients get .efi
```

### Full Working `TFTPD_OPTS` (Compose env var)

Combine all flags in one env var:

```yaml
services:
  netbootxyz:
    environment:
      - TFTPD_OPTS=--dhcp-range=192.168.1.0,proxy --dhcp-match=set:bios,option:client-arch,0 --dhcp-match=set:uefi64,option:client-arch,7 --dhcp-boot=tag:bios,netboot.xyz.kpxe --dhcp-boot=tag:uefi64,netboot.xyz.efi
```

Or split across multiple lines for readability (YAML folding):

```yaml
      - >-
        --dhcp-range=192.168.1.0,proxy
        --dhcp-match=set:bios,option:client-arch,0
        --dhcp-match=set:uefi64,option:client-arch,7
        --dhcp-boot=tag:bios,netboot.xyz.kpxe
        --dhcp-boot=tag:uefi64,netboot.xyz.efi
```

### How `TFTPD_OPTS` Works

netboot.xyz starts dnsmasq via a wrapper script at `/usr/local/bin/dnsmasq-wrapper.sh`:

```bash
#!/bin/bash
echo "[dnsmasq] Starting TFTP server..."
exec /usr/sbin/dnsmasq --port=0 --keep-in-foreground --enable-tftp \
  --user=nbxyz --tftp-secure --tftp-root=/config/menus \
  --log-facility=- --log-dhcp --log-queries "$@"
```

The `"$@"` passes any extra args from `TFTPD_OPTS` (injected via supervisord as `%(ENV_TFTPD_OPTS)s`). This is **the only persistent way** to configure dnsmasq — editing `/etc/dnsmasq.conf` or `/etc/supervisor.conf` inside the container is lost on recreate.

### Verification (Dual-Boot)

```bash
# Check the running dnsmasq command line shows all flags
docker exec netbootxyz ps aux | grep dnsmasq | grep -v grep

# Confirm ProxyDHCP is active
docker logs netbootxyz 2>&1 | grep "proxy on subnet"
# → "DHCP, proxy on subnet 192.168.1.0"

# TFTP test — verify boot files are fetchable
curl -sS -o /dev/null -w '%{http_code}' http://localhost:8380   # HTTP boot → 200
curl -sS -o /dev/null -w '%{http_code}' http://localhost:3300   # Web UI → 200
```

## Client Architecture Options (dnsmasq)

| `option:client-arch` value | Architecture | Tag convention |
|---------------------------|-------------|----------------|
| 0 | BIOS x86-32/PC | `bios`, `x86pc` |
| 2 | IA64 (Itanium) | `itanics` |
| 6 | EFI x86-64 (UEFI) | `uefi64`, `efi64` |
| 7 | EFI x86-64 (UEFI, alternative) | `uefi64`, `hammers` |
| 9 | EFI x86-32 | `efi32` |
| 1 | NEC/PC-98 | — |

For standard BIOS + UEFI home/lab setups, `0` (BIOS) and `7` (UEFI x86-64) cover the vast majority of devices.

## Pitfalls
- `WEB_APP_PORT` env var must match the internal container port in the `ports:` mapping — not the host port.
- Health check takes ~5s after `up -d`. Curl immediately will get `connection reset` even though the container is technically running.
- `docker compose pull` before `up -d` is optional but recommended — it separates download failures from startup failures.
- The `external_network` Docker network must exist before `up -d` or the stack will fail with "network not found".
- **ProxyDHCP syntax**: Use `dhcp-range=<network>,proxy` (just the network address). Start-end ranges are rejected with "bad dhcp-range".
- **NET_ADMIN required**: ProxyDHCP sends raw broadcast packets. Without it, dnsmasq exits with status 5 and "missing required capability NET_ADMIN".
- **Persistence**: Use `TFTPD_OPTS` env var or compose `cap_add:` — editing files inside the container is lost on recreate.
- **`docker update --cap-add` does NOT work**: It doesn't support `--cap-add`. Always modify the compose file and run `docker compose up -d`.
- **Compose file location**: The compose file location on the host `/mnt/shared/tmp/docker/` is independent from volume mounts like `/docker/netbootxyz/config`. Moving the compose file does NOT require moving volumes.
- **Container name conflicts**: If the container already exists from a different compose directory, `docker compose up -d` from the new location will fail with "container name already in use". Run `docker compose down` from the old location first, then deploy from the new one.