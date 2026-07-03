# Leo's Homelab Infrastructure

**Source of truth for all infrastructure-as-code, automation, and documentation.**

## Structure

```
docker-stacks/       ← Docker compose files for all services
automation/          ← Scripts, cron jobs, network recon
infrastructure/      ← Proxmox, docker-host, network configs
notes/               ← Runbooks, ADRs, topology docs
gcp/                 ← Game server compose files
mpc/                 ← Media/management compose files
pve/                 ← Proxmox compose files
tmp/                 ← Legacy reference files
```

## Principles

- **Always push** — scripts, configs, .env.example, and compose files go here
- **Never commit secrets** — real .env files are gitignored; use .env.example templates
- **Signed commits** — all commits are GPG-signed
- **main branch** — stable, reviewed, deployed

## Access

| Service | Host | URL |
|---------|------|-----|
| Hermes | 192.168.1.222 | hermes.tail52be18.ts.net |
| Docker host | 192.168.1.220 | docker.home.arpa |
| Proxmox | 192.168.1.55 | pve.home.arpa |
| Home Assistant | 192.168.1.123 | haos.lenadlm.dev |