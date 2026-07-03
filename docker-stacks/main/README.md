Docker host: 192.168.1.220 (docker.home.arpa)
Networks:
  - internal_network: 172.30.0.0/24
  - external_network: host bridge

Stacks:
  - main: /mnt/shared/tmp/docker/docker-compose.yml (n8n, postgres, redis, dockge)
  - prowlarr: Prowlarr indexer
  - dockhand: Docker update handler

Access:
  - n8n: http://192.168.1.220:5678
  - n8n (internal): http://docker.home.arpa:5678
