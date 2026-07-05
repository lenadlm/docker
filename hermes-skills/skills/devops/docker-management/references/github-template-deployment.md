# GitHub Template Deployment — Docker Compose from Raw URL

Deploy a multi-service compose stack to a remote Docker host using a template from a GitHub raw URL. Covers the full workflow: fetch, pre-deploy checks, `.env` secrets resolution, deploy, and verify.

## Source

- **Template repo**: `https://github.com/lenadlm/docker`
- **Raw URL pattern**: `https://raw.githubusercontent.com/lenadlm/docker/refs/heads/main/<path>/docker-compose.yml`
- **Canonical deploy path**: `/mnt/shared/tmp/docker/` on the Docker host (`192.168.1.220`)
- **`.env` file**: Placed alongside the compose file at `/mnt/shared/tmp/docker/.env`

## Workflow

### 1. Fetch the template

```bash
# Fetch the raw compose file
curl -sS -o compose.yml \
  https://raw.githubusercontent.com/lenadlm/docker/refs/heads/main/<path>/docker-compose.yml

# Write to canonical location on the Docker host
scp compose.yml leo@192.168.1.220:/mnt/shared/tmp/docker/docker-compose.yml
```

### 2. Check for `.env` file

The template's compose file may use `***` placeholder values for secrets instead of `${VAR}` syntax. If so, the `.env` file must exist with the actual values:

```bash
# Check if .env exists
ssh leo@192.168.1.220 "[ -f /mnt/shared/tmp/docker/.env ] && echo 'exists' || echo 'missing'"

# If missing, check the Docker host for existing configs to source from:
#   - /docker/core/.env
#   - /docker/<app>/config/ (for specific app config files)
```

**`.env` file format** (example):
```
TUNNEL_TOKEN=eyJh...secret...
PASSWORD=changeme
SUDO_PASSWORD=changeme
PLEX_CLAIM=claim-xxxxx
```

### 3. Resolve `***` placeholders

If the compose file has `TUNNEL_TOKEN=***` (literal `***`) instead of `${TUNNEL_TOKEN}`, **Docker Compose does NOT interpolate `.env` variables into `***`** — it treats `***` as a literal string. You must either:

**Option A — Replace `***` with the actual value in the compose file** (for one-off deployments):
```bash
# Read the token from .env
TOKEN=$(grep '^TUNNEL_TOKEN=' /mnt/shared/tmp/docker/.env | cut -d= -f2-)

# Replace in compose file
sed -i "s/TUNNEL_TOKEN=\*\*\*/TUNNEL_TOKEN=$TOKEN/" /mnt/shared/tmp/docker/docker-compose.yml
```

**Option B — Change the compose file to use `${VAR}` syntax** (better for maintainability):
```yaml
# In compose file:
#   Before: TUNNEL_TOKEN=***
#   After:  TUNNEL_TOKEN=${TUNNEL_TOKEN}
# Then .env has: TUNNEL_TOKEN=actual_value
# Compose will interpolate automatically on `docker compose up -d`
```

**Recommendation**: Prefer Option B for new deployments (the `.env` file is the single source of truth). Use Option A when the template must stay close to the upstream source.

### 4. Pre-deploy checks

Before running `docker compose up -d`:

```bash
# Required networks exist
ssh leo@192.168.1.220 "docker network ls --format '{{.Name}}' | grep -E 'external_network|internal_network'"

# Volume source directories exist
ssh leo@192.168.1.220 'for d in /docker/app1/config /docker/app2/data; do [ -d "$d" ] && echo "OK: $d" || echo "MISSING: $d"; done'

# .env file exists
ssh leo@192.168.1.220 '[ -f /mnt/shared/tmp/docker/.env ] && echo ".env OK" || echo ".env MISSING"'

# No container name conflicts
ssh leo@192.168.1.220 'for name in service1 service2 service3; do docker ps --format "{{.Names}}" | grep -q "^$name$" && echo "CONFLICT: $name"; done'

# Validate YAML
ssh leo@192.168.1.220 'cd /mnt/shared/tmp/docker && docker compose config > /dev/null 2>&1 && echo "YAML OK" || echo "YAML INVALID"'
```

**Common pre-deploy issues and fixes:**

| Issue | Check | Fix |
|-------|-------|-----|
| Missing network | `docker network ls` | `docker network create <name>` |
| Tab characters in YAML | `docker compose config` fails | `sed -i 's/\\t/  /g; s/[[:space:]]*$//' docker-compose.yml` |
| Container name conflict | `docker ps -a --format '{{.Names}}'` | `docker compose -f /old/path/compose.yml down` or `docker rm -f <name>` |
| Missing `.env` | `[ -f .env ]` | Create from existing configs or ask user |
| Volume dir doesn't exist | `[ -d /docker/app/config ]` | `mkdir -p /docker/app/config && chown 1000:1000 /docker/app/config` |

### 5. Deploy

```bash
ssh leo@192.168.1.220 bash -s <<'REMOTE'
  set -euo pipefail
  cd /mnt/shared/tmp/docker

  echo "=== Pulling images ==="
  docker compose pull 2>&1

  echo "=== Starting stack ==="
  docker compose up -d 2>&1

  echo "=== Container status ==="
  sleep 5
  docker compose ps --format 'table {{.Name}}\t{{.Status}}\t{{.Health}}'
REMOTE
```

### 6. Verify

```bash
ssh leo@192.168.1.220 bash -s <<'REMOTE'
  cd /mnt/shared/tmp/docker

  # Check all containers are running
  RUNNING=$(docker compose ps --status running -q | wc -l)
  TOTAL=$(docker compose ps -q | wc -l)
  echo "Containers: $RUNNING/$TOTAL running"

  # Check healthy status
  docker inspect $(docker compose ps -q) --format '{{.Name}} {{.State.Health.Status}}' 2>/dev/null

  # Spot-check critical ports
  for port in 7878 8096 9091 9696 5055 8181 32400; do
    curl -sS -o /dev/null -w "PORT $port: HTTP %{http_code}\n" --connect-timeout 3 http://localhost:$port 2>/dev/null || echo "PORT $port: unreachable"
  done
REMOTE
```

### 7. Auto-update integration

After deployment, update the auto-update cron job to reference the compose file location:

```bash
# Update the docker_update_check.sh script's STACK_DIR variable
sed -i 's|STACK_DIR=.*|STACK_DIR="/mnt/shared/tmp/docker"|' ~/.hermes/scripts/docker_update_check.sh
```

The cron job will then automatically pull and redeploy the stack every 6 hours.

## Pitfalls

- **`***` in compose is NOT interpolated from `.env`**: Docker Compose only substitutes `${VAR}` syntax. Literal `***` stays as-is. You must either replace it or change to `${VAR}` syntax.
- **Port mapping vs env var mismatch**: The compose may have `WEB_APP_PORT=3300` but port mapping `3300:3000`. The app listens on the internal port (3000), not the host port. Fix by aligning the env var with the mapping.
- **Container name conflict on relocation**: If the same container name exists from a previous deploy at a different compose path, use `docker compose down` from the old location or `docker rm -f <name>`.
- **Health check timing**: Containers may need 3-10 seconds after `up -d` before serving traffic. Curl immediately will get `connection reset`.
- **`docker update` doesn't support `--cap-add`**: Capabilities must be set in the compose file and applied via `docker compose up -d`.

## Worked Example: Full 14-Service Stack Deployment

The full Docker stack (cloudflared, dockhand, dozzle, code-server, copyparty, plex, tautulli, jellyfin, netbootxyz, flaresolverr, seerr, prowlarr, radarr, transmission) was deployed from:

```
https://raw.githubusercontent.com/lenadlm/docker/refs/heads/main/tmp/docker-compose.yml
```

To: `/mnt/shared/tmp/docker/docker-compose.yml` on `192.168.1.220`

Secrets in `.env`: `TUNNEL_TOKEN`, `PASSWORD`, `SUDO_PASSWORD`

The `TUNNEL_TOKEN=***` placeholders in the template were resolved by reading from the existing `.env` file and replacing inline (Option A), because the compose file was kept close to the upstream template for diff-ability.