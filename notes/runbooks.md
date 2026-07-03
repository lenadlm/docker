# Runbooks

Common operational procedures for the homelab.

## Quick Reference

| Action | Command |
|--------|---------|
| Check Docker status | `ssh leo@192.168.1.220 "docker ps -a"` |
| View logs | `ssh leo@192.168.1.220 "docker logs -f <container>"` |
| Restart stack | `ssh leo@192.168.1.220 "docker compose -f /mnt/shared/tmp/docker/docker-compose.yml restart"` |
| Check HA health | `ssh leo@192.168.1.123 "ha core check"` |
| Proxmox VMs | `ssh root@192.168.1.55 "qm list"` |
| Proxmox health | `~/.hermes/scripts/run_proxmox_health.sh` |
| Git pull repo | `cd ~/projects && git pull` |
| Git push changes | `cd ~/projects && git add -A && git commit -m "msg" && git push` |

## Docker Stack Lifecycle

### Update all containers

```bash
ssh leo@192.168.1.220
cd /mnt/shared/tmp/docker
docker compose pull
docker compose up -d
docker image prune -f
```

### Rebuild a specific service

```bash
ssh leo@192.168.1.220
docker compose -f /mnt/shared/tmp/docker/docker-compose.yml up -d --force-recreate <service>
```

### Backup volumes

```bash
ssh leo@192.168.1.220
docker run --rm -v <volume_name>:/data -v /mnt/shared/backups:/backup alpine tar czf /backup/<volume_name>-$(date +%F).tar.gz -C /data .
```

## Troubleshooting

### Container won't start

1. `docker logs <container>` — check errors
2. `docker inspect <container>` — check mounts, networks
3. `docker compose config` — validate compose file
4. Check port conflicts: `ss -tlnp | grep <port>`

### Network issues

1. `ping <target>` — basic connectivity
2. `traceroute <target>` — find where it breaks
3. `docker network inspect internal_network` — container DNS
4. `iptables -L -n` — firewall rules

### Disk space

```bash
df -h
du -sh /mnt/shared/tmp/docker/*/
docker system df
```