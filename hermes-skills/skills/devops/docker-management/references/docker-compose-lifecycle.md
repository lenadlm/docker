# Docker Compose File Lifecycle

## Source of Truth
Docker compose files under management are tracked at two levels:

### 1. GitHub Repository (source of truth)
**Repo**: `https://github.com/lenadlm/docker`
- Contains the canonical compose files after deployment
- Organized by application name as subdirectories under the repo root

### 2. Remote Docker Host (deployed copy)
**Host**: `192.168.1.220` (leo@, key-based SSH)
**Path**: `/mnt/shared/tmp/docker/`
- Deployed compose files live here
- A `.env` file next to the compose file holds environment variables like `TUNNEL_TOKEN`, `PASSWORD`, `SUDO_PASSWORD`
- Env vars are sourced from existing configs on the host (e.g., `/docker/core/.env`)

### 3. Hermes Management Host (working copy)
**Host**: `192.168.1.222` (Hermes agent)
**Path**: `/mnt/shared/tmp/docker/`
- Synced from the remote Docker host after deployment
- Used by the auto-update cron job for reference

## Workflow

### New deployment:
1. Write or source the compose file (GitHub, user-provided, or from scratch)
2. Copy to Docker host: `scp compose.yml user@host:/mnt/shared/tmp/docker/`
3. Ensure `.env` with required variables exists alongside the compose file
4. Run `docker compose up -d` on the Docker host
5. Verify all containers are healthy
6. Clone the GitHub repo, save the compose file under the app name, push

### Updates:
1. Edit the compose file on the Docker host or Hermes host
2. Run `docker compose up -d` to apply changes
3. Sync the updated file back to the Hermes host: `scp user@host:/mnt/shared/tmp/docker/compose.yml /mnt/shared/tmp/docker/`
4. Push to GitHub repo

### Auto-updates:
- Handled by the cron job `Docker Stack Auto-Update (14 services)` every 6 hours
- Script at `scripts/docker_update_check.sh` (skill: docker-management)
- Only checks the deployed copy on the Docker host — does not push to GitHub