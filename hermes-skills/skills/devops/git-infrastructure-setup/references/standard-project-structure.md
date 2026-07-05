# Standard Project Structure (~/projects/)

## Canonical Layout

```
~/projects/                              ← Git root
├── .gitignore                           ← Root gitignore (secrets, OS files, editor artifacts)
├── docker-stacks/
│   ├── main/                            ← Primary Docker Compose stack
│   │   ├── docker-compose.yml           ← Main service definitions
│   │   ├── n8n.yml                      ← Overlay/service-specific compose (if split)
│   │   ├── .env.example                 ← Template — copy to .env, fill secrets
│   │   ├── .gitignore                   ← Ignores: .env
│   │   └── README.md                    ← Stack overview, URLs, access info
│   ├── prowlarr/                        ← Secondary stack
│   │   └── docker-compose.yml
│   └── dockhand/                        ← Docker update handler
│       └── docker-compose.yml
├── automation/
│   └── scripts/                         ← All cron-able scripts
│       ├── *.sh                         ← Shell scripts
│       ├── *.py                         ← Python automation scripts
│       └── (no subdirectories — flat for cron compatibility)
├── infrastructure/
│   ├── proxmox/                         ← Proxmox host details
│   │   ├── host-info.txt               ← pveversion, hostname
│   │   ├── pve_dashboard.html          ← Captured dashboard
│   │   └── .gitignore                  ← Ignores: *.token.env, *.env
│   ├── docker-host/                     ← Docker host configs (captured)
│   │   ├── daemon.json                 ← Docker daemon config
│   │   ├── hostname.txt
│   │   └── hosts                       ← /etc/hosts from docker host
│   └── network/                         ← Network configs
│       └── iptables.rules              ← iptables-save output
└── notes/                               ← Documentation
    └── README.md                        ← Placeholder for runbooks and ADRs
```

## Design Principles

1. **Separation by concern**: docker-stacks, automation, infrastructure, notes
2. **Secrets out**: Real .env files live at their original location on the host; only .env.example templates reach the repo
3. **Flat scripts directory**: All cron scripts at one level (no subdirs) — cron references work consistently
4. **Self-documenting**: Each stack has a README with URLs, access info, and network topology
5. **Capture, don't relocate**: Files in ~/projects/ are copies/snapshots — originals stay on their host machines
6. **Infra is captured state**: Infrastructure configs (daemon.json, hosts, iptables) are read-only snapshots, not active config targets

## Verification

```bash
cd ~/projects
find . -name ".env" | grep -v .example | grep -v .gitignore
# Should return nothing — no real .env in the repo
```