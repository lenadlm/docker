---
name: docker-management
description: Manage Docker containers, images, volumes, networks, and Compose stacks — lifecycle ops, debugging, cleanup, and Dockerfile optimization.
version: 1.2.1
author: sprmn24
license: MIT
metadata:
  hermes:
    tags: [docker, containers, devops, infrastructure, compose, images, volumes, networks, debugging]
    category: devops
    requires_toolsets: [terminal]
---

# Docker Management

Manage Docker containers, images, volumes, networks, and Compose stacks using standard Docker CLI commands. No additional dependencies beyond Docker itself.

## When to Use

- Run, stop, restart, remove, or inspect containers
- Build, pull, push, tag, or clean up Docker images
- Work with Docker Compose (multi-service stacks)
- Manage volumes or networks
- Debug a crashing container or analyze logs
- Check Docker disk usage or free up space
- Review or optimize a Dockerfile

## Prerequisites

- Docker Engine installed and running
- User added to the `docker` group (or use `sudo`)
- Docker Compose v2 (included with modern Docker installations)
- **Backgrounding Remote Tasks**: When running `docker compose up` or `docker pull` on remote hosts via SSH, always use `background=true` with `notify_on_complete=true`. Foreground timeouts (600s) often trigger before images finish pulling or containers stabilize.
- **Permission Handling**: Ensure that volume paths on the host (e.g., `/docker/app/data`) are created and owned by the `PUID:PGID` specified in the compose file (usually 1000:1000) before starting the container to avoid "Permission Denied" startup loops.
- **External Networks**: If a compose file uses `external: true` for networks, run `docker network create <name> || true` before bringing the stack up.

Quick check:

```bash
docker --version && docker compose version
```

## Quick Reference

| Task | Command |
|------|---------|
| Run container (background) | `docker run -d --name NAME IMAGE` |
| Stop + remove | `docker stop NAME && docker rm NAME` |
| View logs (follow) | `docker logs --tail 50 -f NAME` |
| Shell into container | `docker exec -it NAME /bin/sh` |
| List all containers | `docker ps -a` |
| Build image | `docker build -t TAG .` |
| Compose up | `docker compose up -d` |
| Compose down | `docker compose down` |
| Disk usage | `docker system df` |
| Cleanup dangling | `docker image prune && docker container prune` |

### Remote Deployment (on hosts without Hermes)

When deploying to remote hosts (e.g., via SSH to 192.168.1.220):

- **Command Syntax**: Older systems may use `docker-compose`, newer ones use the Docker CLI plugin `docker compose`. Always check with `docker compose version` first.
- **GitHub Configs**: Check `https://github.com/lenadlm/docker` first for existing compose files before writing from scratch.
- **Backgrounding**: Always use `background=true` with `notify_on_complete=true` for `docker compose up` on remote hosts. Pulling images can take minutes and trigger 600s tool timeouts.
- **Verification**: Use `docker ps --format 'table {{.Names}}\t{{.Status}}\t{{.Image}}'` to list all containers and verify health.
- **.env files**: If the compose file uses `${VARIABLE}` syntax, ensure a `.env` file exists alongside it. Source secrets from existing configs on the host (e.g., `/docker/core/.env`) when available.
- **`*** placeholders vs `.env`**: If the template has literal `TUNNEL_TOKEN=***` instead of `${TUNNEL_TOKEN}`, Docker Compose does NOT interpolate `.env` values into `***`. Either replace `***` inline, or convert to `${VAR}` syntax. See `references/github-template-deployment.md` for details and worked example.

**References**:
- `references/docker-compose-lifecycle.md` — full lifecycle for compose files across GitHub → Docker host → Hermes host.
- `references/github-template-deployment.md` — deploying compose stacks from GitHub raw URLs, with `.env` secrets resolution, pre-deploy checks, and the full 14-service stack worked example.
- `references/guacamole-deployment.md` — deploying Apache Guacamole (web SSH/RDP/VNC gateway, 3 containers + PostgreSQL), init schema generation, `--postgresql` flag pitfall, dark mode caveats.
- `references/n8n-deployment.md` — n8n with Postgres + Redis, queue mode, scaling workers.
- `references/n8n-homelab-automations.md` — 35+ n8n workflow ideas for homelab automation, monitoring, security, AI, Proxmox, and network engineering.
##### Port Mapping & Env Var Mismatch Pitfall

When deploying compose stacks from external sources (GitHub, registries), the port mapping in the `ports:` section and the `WEB_APP_PORT` (or similar `*_PORT`) env var may disagree:

```yaml
# Example mismatch — WEB_APP_PORT=3300 but port mapping forwards 3000
services:
  webapp:
    image: some/image
    environment:
      - WEB_APP_PORT=3300    # app listens inside on 3300
    ports:
      - "3300:3000"          # Docker forwards host:3300 to container:3000 ✖
```

**Result**: Connecting to the host port succeeds (Docker opens the port) but the connection resets or times out — nothing is listening on port 3000 inside the container.

**Fix**: Align the env var with the mapping:
- Set `WEB_APP_PORT=3000` to match `"3300:3000"` (app listens on 3000, Docker forwards 3300→3000)
- Or change mapping to `"3300:3300"` (leaves WEB_APP_PORT=3300, Docker forwards 3300→3300)
- Either approach works, pick the one that requires fewer changes

Always check after `docker compose up -d`:
```bash
# Check if the service is listening on the expected internal port
ssh user@host "docker logs <container> --tail 10 | grep -i listening"
# Then test the mapped port
curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost:<host_port>
```

#### Health Check Retry Pattern

After `docker compose up -d`, containers may need 3-10 seconds to pass their health check before serving traffic. A single immediate curl is unreliable:

```bash
# Deploy
cd /path/to/stack && docker compose up -d

# Wait for health
sleep 5

# Verify health status
docker inspect <container> --format '{{.State.Health.Status}}'
# Expected: "healthy"

# THEN test HTTP — if it fails, retry once after another sleep
curl -sS -o /dev/null -w '%{http_code}' --connect-timeout 5 http://localhost:<port>
# If "connection reset" or "000", sleep 3 and retry
```

#### 🚩 Health Check Pipe Exit Code Pitfall

When writing a health check command, the exit code of a **pipeline** (`cmd1 | cmd2`) is the exit code of the **last** command in the pipeline, not the first:

```yaml
# ❌ WRONG — exit code is from grep, not curl
test: ["CMD-SHELL", "curl -f http://localhost/ | grep -q 'SomeString'"]
```

If the server responds 200 but the HTML doesn't contain `"SomeString"`, `grep` returns 1 and the health check fails — even though the service is working fine.

**Fixes** (in order of preference):

1. **Exec format** (JSON array) — avoids the pipe entirely. Use when the health check is a single command with no condition:
   ```yaml
   healthcheck:
     test: ["CMD", "curl", "-fs", "http://localhost:8080/"]
   ```

2. **Shell conditional** — if you need both a status check AND content check, use shell logic that preserves curl's exit code:
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "curl -f http://localhost/ | grep -q 'SomeString' || exit 1"]
   ```
   Note: This still has the same problem — grep's exit code is what Docker sees.

3. **Shell wrapper** — explicit check on curl's exit before grep:
   ```yaml
   healthcheck:
     test: ["CMD-SHELL", "curl -sf http://localhost/ > /dev/null && grep -q 'OK' <(curl -s http://localhost/)"]
   ```

**Best practice for web apps**: Just use exec-format curl with `-f` (fail on HTTP error ≥400) and `-s` (silent). Docker's health check only needs to know if the process is responding correctly, not whether a specific string is in the response.

#### Container Capabilities Pitfall — `docker update` Does NOT Support `--cap-add`

Some containers need special Linux capabilities (e.g., `NET_ADMIN` for raw socket operations, `SYS_PTRACE` for debuggers, `IPC_LOCK` for memory locking). Common symptoms of a missing capability:
```
process is missing required capability NET_ADMIN
dnsmasq: exited with status 5
```

**`docker update` does NOT support `--cap-add`**, `--cap-drop`, `--privileged`, or `--security-opt`:
```bash
# ❌ This does NOT work — "unknown flag: --cap-add"
docker update --cap-add NET_ADMIN mycontainer
```

**The fix is always in the compose file**, followed by a recreate:
```yaml
services:
  myapp:
    image: some/image
    cap_add:
      - NET_ADMIN        # or any other capability
```

Then recreate:
```bash
docker compose up -d    # detects compose change, recreates container
```

**For `docker run` containers** (no compose file), the only option is to stop, remove, and re-create with `--cap-add`.

**Quick debug flow for capability errors**:
```bash
# Check container logs for explicit capability errors
docker logs mycontainer 2>&1 | grep -i -E "capability|permission denied|operation not permitted"

# Verify which capabilities the container currently has
docker inspect mycontainer --format '{{json .HostConfig.CapAdd}}'
```

**Reference**: `references/remote-docker-update-script.md` — full worked example with auto-update checking, multi-service stack support, and container name conflict handling.
**Script**: `scripts/docker_update_check.sh` — runnable multi-service update checker. Deploy to `~/.hermes/scripts/` and create a cron job with `cronjob action=create schedule="0 */6 * * *" script=docker_update_check.sh no_agent=true deliver=origin`.

##### SSH Heredoc Variable Expansion Pitfall

When passing variables inside a `<<'REMOTE_SCRIPT'` heredoc (single-quoted delimiter), **bash does NOT expand variables** — the entire block is sent literally to the remote shell:

```bash
# ❌ $STACK_DIR is NOT expanded — remote shell tries to use its own (undefined) value
STACK_DIR="/mnt/shared/tmp/docker"
ssh user@host bash -s <<'REMOTE_SCRIPT'
  cd "$STACK_DIR"   # empty on remote — cd fails silently
  docker compose pull
REMOTE_SCRIPT
```

**The fix**: Pass variables as SSH environment variables before `bash -s`:

```bash
# ✅ Pass the variable to the remote session
STACK_DIR="/mnt/shared/tmp/docker"
ssh user@host "STACK_DIR=$STACK_DIR" bash -s <<'REMOTE_SCRIPT'
  cd "$STACK_DIR"   # now evaluates to /mnt/shared/tmp/docker on remote
  docker compose pull
REMOTE_SCRIPT
```

The SSH command syntax `ssh user@host "VAR=value" bash -s` sets env vars for the duration of the SSH session, making them available inside single-quoted heredocs.

**Alternative** (if the path is the same on both hosts): Just hardcode the path inside the heredoc if it's a static path that doesn't change between hosts:

```bash
ssh user@host bash -s <<'REMOTE_SCRIPT'
  cd /mnt/shared/tmp/docker   # fine — literal path
  docker compose pull
REMOTE_SCRIPT
```

Use the env-var pattern when the path is dynamic (e.g., defined at the top of the script, configurable via `.env`).

##### Cloudflared Token Management on Remote Hosts

When a Cloudflare tunnel token expires or needs replacement on a remote Docker host:

**Symptom**: Container constantly restarting — `docker inspect` shows `Restarts: 30+` and logs repeat `"Provided Tunnel token is not valid"`.

**Diagnosis**:
```bash
# Check restart count
docker inspect cloudflared --format '{{.State.Status}} | Restarts: {{.RestartCount}}'
# Check logs
docker logs --tail 10 cloudflared 2>&1
# Check token in .env
grep TUNNEL_TOKEN /path/to/stack/.env
```

**Fix** — update the token in the stack's `.env` file and restart:

1. Get the new token from [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) → Networks → Tunnels → select tunnel → copy connector token
2. Write a Python script (avoids sed quoting issues with base64 tokens):

```python
#!/usr/bin/env python3
"""Replace TUNNEL_TOKEN=*** line in .env with a new token."""
import sys
token_path = sys.argv[1]
env_path = sys.argv[2]
token = open(token_path).read().strip()
with open(env_path, 'r') as f:
    content = f.read()
lines = content.split('\n')
for i, line in enumerate(lines):
    if line.startswith('TUNNEL_TOKEN=***        lines[i] = 'TUNNEL_TOKEN=*** + token
        break
content = '\n'.join(lines)
with open(env_path, 'w') as f:
    f.write(content)
# Verify
if token in open(env_path).read():
    print(f'VERIFIED: token present ({len(token)} chars)')
else:
    print('ERROR: token NOT found')
    sys.exit(1)
```

3. Write the bare token to a file, SCP both to the remote host, then run:
```bash
scp update_token.py new_token_value leo@host:/tmp/
ssh leo@host "python3 /tmp/update_token.py /tmp/new_token_value /path/to/stack/.env"
```

> **Tip**: The `update_token.py` script lives in the docker-management skill at `scripts/update_token.py`. To retrieve it, run `skill_view(name='docker-management', file_path='scripts/update_token.py')`.

4. Restart the container to pick up the new token:
```bash
ssh leo@host "cd /path/to/stack && docker compose up -d cloudflared"
```

5. Verify it's running:
```bash
sleep 5 && docker inspect cloudflared --format '{{.State.Status}} | Restarts: {{.RestartCount}}'
docker logs --tail 5 cloudflared 2>&1  # Should show "Starting tunnel..." not "invalid token"
```

**Pitfalls**:
- **Base64 tokens break `sed`**: Tokens contain `/`, `+`, `=` — use Python or a dedicated script, not sed.
- **Token file format**: Write ONLY the token value to the file, not `TUNNEL_TOKEN=*** prefix — the Python script adds the prefix itself.
- **Quoting in SSH**: Nesting single quotes inside SSH commands breaks. Always use SCP for the token file and run the script locally on the remote host.
- **Token rotation**: Old tunnel token stops working immediately once revoked in Cloudflare. Update `.env` before restarting to minimize downtime.
- **Restart count resets**: `RestartCount` only resets when the container is recreated (`docker compose up -d` recreates it), not on a simple `docker restart`.
- **`docker exec` fails on crash-looping containers**: If the container is in `Status: restarting`, `docker exec` returns `"cannot exec into a container in a restarting state"`. Use `docker inspect` and `docker logs` for diagnostics instead.
- **Token file truncation during SCP**: The token file can get truncated during transfer (SSH quoting errors, pipe corruption). After SCP, verify with `wc -c token_file` on the remote host and compare the byte count to the original file. A 184-char base64 token should be exactly 184 bytes. If shorter, the token was corrupted and needs re-transfers.

---

#### YAML Tab Character Pitfall

Docker Compose v2 strictly rejects tab characters in YAML:
```
yaml: while scanning a plain scalar — found a tab character that violates indentation
```

**Fix with a single sed command:**
```bash
sed -i 's/\t/  /g; s/[[:space:]]*$//' docker-compose.yml
```

Converts all tabs to spaces and strips trailing whitespace. Validate after fixing:
```bash
docker compose config 2>&1 | head -5
```

Run this before the first `docker compose up -d` on compose files from external sources or user-edited files.

---

#### Container Name Conflict on Stack Relocation

When a compose file is moved to a new directory, `docker compose up -d` fails with:
```
Error: Conflict. The container name "/NAME" is already in use...
```

**Fix**: Remove the old container first, then deploy from the new location:
```bash
# From the old compose directory (if file still exists)
cd /docker/old && docker compose down

# Or force remove the single conflicting container
docker rm -f container_name

# Then deploy from new location
cd /mnt/shared/tmp/docker && docker compose up -d
```

Volume mounts use absolute host paths (e.g., `/docker/app/config:/config`), so they survive relocation — no data loss.

---

#### `enable-environment-properties` Pitfall — Some Properties Fail as Env Vars

The Guacamole Docker image adds `enable-environment-properties: true` to `guacamole.properties` automatically. This tells Guacamole's property system to also read from environment variables. **However**, typed properties (like `IntegerGuacamoleProperty`) can fail when their value comes from an env var string:

```
ERROR - authentication provider extension failed to start:
        Property "postgresql-port" must be an integer.
```

Even though `POSTGRESQL_PORT=5432` is set in the container, the `IntegerGuacamoleProperty.parseValue()` receives the string `"5432"` from `System.getenv()` and it may fail depending on how the env-to-property conversion works internally.

**Pattern**: When a Docker image auto-generates a config file from env vars and the application then re-reads properties via a typed property system, the env var path can bypass the type parser. The fix is always to **mount a config file directly** at the app's config path, bypassing the env-to-file generation.

For Guacamole specifically:
```yaml
volumes:
  - ./guacamole.properties:/etc/guacamole/guacamole.properties:ro
```

Contents:
```properties
postgresql-hostname: guacamole-postgres
postgresql-port: 5432
postgresql-database: guacamole_db
postgresql-username: guacamole
postgresql-password: ${GUAC_PASS}
```

This pattern applies to any container where env-var-to-property conversion is unreliable (e.g. Java apps with `IntegerProperty` classes, or YAML-based config generators that lose type information).

---

#### Pre-Deploy Prerequisite Checks

Before deploying a multi-service compose stack on a remote host:

1. Required Docker networks exist (`docker network ls | grep -E 'network_name'`)
2. All volume source directories exist
3. `.env` file exists for `${VARIABLE}` interpolation
4. No container name conflicts with currently running containers

Check with:
```bash
docker network ls | grep -E 'external|internal'
for d in /docker/app1/config /docker/app2/data; do [ -d "$d" ] || echo "MISSING: $d"; done
[ -f /stack/.env ] || echo "No .env file"
for name in service1 service2; do docker ps --format '{{.Names}}' | grep -q "^$name$" && echo "CONFLICT: $name"; done
```

Fix issues before running `docker compose up -d`.

---

### 1. Identify the domain

Figure out which area the request falls into:

- **Container lifecycle** → run, stop, start, restart, rm, pause/unpause
- **Container interaction** → exec, cp, logs, inspect, stats
- **Image management** → build, pull, push, tag, rmi, save/load
- **Docker Compose** → up, down, ps, logs, exec, build, config
- **Volumes & networks** → create, inspect, rm, prune, connect
- **Troubleshooting** → log analysis, exit codes, resource issues

### 2. Container operations

**Run a new container:**

```bash
# Detached service with port mapping
docker run -d --name web -p 8080:80 nginx

# With environment variables
docker run -d -e POSTGRES_PASSWORD=secret -e POSTGRES_DB=mydb --name db postgres:16

# With persistent data (named volume)
docker run -d -v pgdata:/var/lib/postgresql/data --name db postgres:16

# For development (bind mount source code)
docker run -d -v $(pwd)/src:/app/src -p 3000:3000 --name dev my-app

# Interactive debugging (auto-remove on exit)
docker run -it --rm ubuntu:22.04 /bin/bash

# With resource limits and restart policy
docker run -d --memory=512m --cpus=1.5 --restart=unless-stopped --name app my-app
```

Key flags: `-d` detached, `-it` interactive+tty, `--rm` auto-remove, `-p` port (host:container), `-e` env var, `-v` volume, `--name` name, `--restart` restart policy.

**Manage running containers:**

```bash
docker ps                        # running containers
docker ps -a                     # all (including stopped)
docker stop NAME                 # graceful stop
docker start NAME                # start stopped container
docker restart NAME              # stop + start
docker rm NAME                   # remove stopped container
docker rm -f NAME                # force remove running container
docker container prune           # remove ALL stopped containers
```

**Interact with containers:**

```bash
docker exec -it NAME /bin/sh          # shell access (use /bin/bash if available)
docker exec NAME env                   # view environment variables
docker exec -u root NAME apt update    # run as specific user
docker logs --tail 100 -f NAME         # follow last 100 lines
docker logs --since 2h NAME            # logs from last 2 hours
docker cp NAME:/path/file ./local      # copy file from container
docker cp ./file NAME:/path/           # copy file to container
docker inspect NAME                    # full container details (JSON)
docker stats --no-stream               # resource usage snapshot
docker top NAME                        # running processes
```

### 3. Image management

```bash
# Build
docker build -t my-app:latest .
docker build -t my-app:prod -f Dockerfile.prod .
docker build --no-cache -t my-app .              # clean rebuild
DOCKER_BUILDKIT=1 docker build -t my-app .       # faster with BuildKit

# Pull and push
docker pull node:20-alpine
docker login ghcr.io
docker tag my-app:latest registry/my-app:v1.0
docker push registry/my-app:v1.0

# Inspect
docker images                          # list local images
docker history IMAGE                   # see layers
docker inspect IMAGE                   # full details

# Cleanup
docker image prune                     # remove dangling (untagged) images
docker image prune -a                  # remove ALL unused images (careful!)
docker image prune -a --filter "until=168h"   # unused images older than 7 days
```

### 4. Docker Compose

```bash
# Start/stop
docker compose up -d                   # start all services detached
docker compose up -d --build           # rebuild images before starting
docker compose down                    # stop and remove containers
docker compose down -v                 # also remove volumes (DESTROYS DATA)

# Monitoring
docker compose ps                      # list services
docker compose logs -f api             # follow logs for specific service
docker compose logs --tail 50          # last 50 lines all services

# Interaction
docker compose exec api /bin/sh        # shell into running service
docker compose run --rm api npm test   # one-off command (new container)
docker compose restart api             # restart specific service

# Validation
docker compose config                  # validate and view resolved config
```

**Minimal compose.yml example:**

```yaml
services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - DATABASE_URL=postgres://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    volumes:
      - pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  pgdata:
```

### 5. Volumes and networks

```bash
# Volumes
docker volume ls                       # list volumes
docker volume create mydata            # create named volume
docker volume inspect mydata           # details (mount point, etc.)
docker volume rm mydata                # remove (fails if in use)
docker volume prune                    # remove unused volumes

# Networks
docker network ls                      # list networks
docker network create mynet            # create bridge network
docker network inspect mynet           # details (connected containers)
docker network connect mynet NAME      # attach container to network
docker network disconnect mynet NAME   # detach container
docker network rm mynet                # remove network
docker network prune                   # remove unused networks
```

### 6. Disk usage and cleanup

Always start with a diagnostic before cleaning:

```bash
# Check what's using space
docker system df                       # summary
docker system df -v                    # detailed breakdown

# Targeted cleanup (safe)
docker container prune                 # stopped containers
docker image prune                     # dangling images
docker volume prune                    # unused volumes
docker network prune                   # unused networks

# Aggressive cleanup (confirm with user first!)
docker system prune                    # containers + images + networks
docker system prune -a                 # also unused images
docker system prune -a --volumes       # EVERYTHING — named volumes too
```

**Warning:** Never run `docker system prune -a --volumes` without confirming with the user. This removes named volumes with potentially important data.

### 7. Maintenance and Updates

**Update all images and restart containers (remote via SSH):**
This pattern is useful for keeping a fleet of containers up-to-date on a remote Docker host from a management host.

```bash
# Remote update check — pull + redeploy + detect if container was recreated
ssh user@remote-host bash -s <<'REMOTE'
  set -euo pipefail
  STACK_DIR="/path/to/stack"

  cd "$STACK_DIR"
  before=$(docker inspect --format '{{.State.StartedAt}}' container_name 2>/dev/null || echo "unknown")

  docker compose pull 2>&1
  docker compose up -d 2>&1

  after=$(docker inspect --format '{{.State.StartedAt}}' container_name 2>/dev/null || echo "unknown")

  if [ "$before" != "$after" ] && [ "$before" != "unknown" ]; then
    echo "UPDATED=true — container was recreated"
  else
    echo "UPDATED=false — images already current"
  fi
REMOTE
```

This is more reliable than parsing pull output (which always says "Pulled" even for unchanged images). Uses container `StartedAt` timestamp comparison.

**Reference**: `references/remote-docker-update-script.md` contains a standalone script (`docker_update_check.sh`) that implements this pattern with Telegram-ready output, logging, and multi-stack support.

**Update all images and restart containers (local):**
```bash
# 1. Update Docker Engine (Ubuntu/Debian)
sudo apt update && sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 2. Update all Compose-managed stacks
# This finds the working directory for every running stack and pulls/ups it
stacks=$(docker ps --format '{{.Label "com.docker.compose.project.working_dir"}}' | sort -u | grep -v '^$')
for dir in $stacks; do
  if [ -d "$dir" ]; then
    echo "Updating stack in $dir..."
    cd "$dir" && docker compose pull && docker compose up -d
  fi
done

# 3. Cleanup to reclaim space
docker image prune -a -f
```

### 8. Troubleshooting Tip: Missing Compose Dirs
If `docker ps` shows a working directory label that no longer exists on the host, the container was likely deployed via a temporary tool (like Portainer or a deleted git repo). You must manually recreate these or use `docker-recycle` if the original run config is lost.


| Problem | Cause | Fix |
|---------|-------|-----|
| Container exits immediately | Main process finished or crashed | Check `docker logs NAME`, try `docker run -it --entrypoint /bin/sh IMAGE` |
| "port is already allocated" | Another process using that port | `docker ps` or `lsof -i :PORT` to find it |
| "no space left on device" | Docker disk full | `docker system df` then targeted prune |
| Can't connect to container | App binds to 127.0.0.1 inside container | App must bind to `0.0.0.0`, check `-p` mapping |
| Permission denied on volume | UID/GID mismatch host vs container | Use `--user $(id -u):$(id -g)` or fix permissions |
| Compose services can't reach each other | Wrong network or service name | Services use service name as hostname, check `docker compose config` |
| Build cache not working | Layer order wrong in Dockerfile | Put rarely-changing layers first (deps before source code) |
| Image too large | No multi-stage build, no .dockerignore | Use multi-stage builds, add `.dockerignore` |

#### Memory Limits — `mem_limit` vs `deploy.resources.limits`

**Standalone Docker Compose** ignores `deploy.resources.limits.memory` — that key is for **Docker Swarm** only.

```yaml
# ❌ Does NOT work in standalone compose (silently ignored)
services:
  app:
    deploy:
      resources:
        limits:
          memory: 512M

# ✅ Use mem_limit for standalone compose
services:
  app:
    mem_limit: 512m
```

After `docker compose up -d`, verify limits are applied:

```bash
docker inspect --format '{{divide .HostConfig.Memory 1048576}}' <container>
# Should show the number of MB, not 0
```

**Quick reference for common values:**
| Service type | Recommended limit | Notes |
|---|---|---|
| n8n / worker | 1 GB | Node heap also needs `NODE_OPTIONS=--max-old-space-size=X` |
| Postgres | 512 MB | Also tune `shared_buffers` (~25% of limit) |
| Redis | 256 MB | Also set `--maxmemory` (~50% of limit) |
| Generic service | 256-512 MB | Adjust based on logs/stats |
| Backup/cron | 128 MB | Usually low footprint |

---

#### Compose Stack Hardening

When deploying a multi-service compose stack, apply these hardening patterns to prevent OOMs, log flooding, startup races, and leaking secrets:

##### 1. Secrets Management via `.env`

Never hardcode passwords, tokens, or keys in compose files:

```yaml
# ❌ Bad — secrets in compose
environment:
  POSTGRES_PASSWORD: mypassword

# ✅ Good — secrets in .env, referenced with validation
environment:
  POSTGRES_PASSWORD: ${DB_PASSWORD:?Must set DB_PASSWORD in .env}
```

Create `.env` alongside the compose file:

```
DB_PASSWORD=$(openssl rand -base64 24)  # generate on each new stack
```

Generate secrets with:
```bash
# For Postgres/API passwords
openssl rand -base64 24

# For encryption keys (hex)
openssl rand -hex 32

# For simple passwords
openssl rand -base64 18
```

##### 2. Healthchecks on Every Stateful Service

Databases and main apps should have healthchecks so dependent services wait properly:

```yaml
postgres:
  image: postgres:16-alpine
  healthcheck:
    test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 30s

redis:
  image: redis:7-alpine
  healthcheck:
    test: ["CMD", "redis-cli", "ping"]
    interval: 10s
    timeout: 5s
    retries: 5
    start_period: 10s

n8n:
  image: n8nio/n8n:latest
  healthcheck:
    test: ["CMD", "node", "-e", "require('http').get('http://localhost:5678/healthz', (r) => {process.exit(r.statusCode >= 200 && r.statusCode < 400 ? 0 : 1)}).on('error', () => process.exit(1))"]
    interval: 30s
    timeout: 10s
    retries: 3
    start_period: 60s
```

##### 3. Proper Startup Ordering

Use `depends_on` with health conditions to ensure databases are ready before the app starts:

```yaml
services:
  app:
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
```

This prevents the app from crashing on startup because the DB isn't accepting connections yet.

##### 4. Memory Limits — Prevent OOM Domino Effect

Add `mem_limit` to **every** service. Without limits, one memory-leaking container can starve the entire host and OOM-kill critical services:

```yaml
services:
  app:
    mem_limit: 1g
  db:
    mem_limit: 512m
  cache:
    mem_limit: 256m
```

See "Memory Limits — `mem_limit` vs `deploy.resources.limits`" above for the standalone vs swarm distinction.

##### 5. Logging Limits — Prevent Disk Fill

Default Docker logging has **no cap** — a single crashing container can fill the disk with repeated error logs:

```yaml
services:
  app:
    logging:
      driver: json-file
      options:
        max-size: 10m
        max-file: 3
```

Add this to every service. 3 files × 10 MB = 30 MB max per service. Adjust upward for high-traffic services.

##### 6. Container Tuning

Tune databases and runtimes to stay within their memory limits:

**Postgres (via command args):**
```yaml
postgres:
  command: "postgres -c shared_buffers=128MB -c work_mem=16MB -c effective_cache_size=512MB"
```
Rule of thumb: `shared_buffers` ≈ 25% of mem_limit, `effective_cache_size` ≈ 50-75%.

**Redis (via command args):**
```yaml
redis:
  command: >
    redis-server --appendonly yes
    --appendfsync everysec
    --maxmemory 128mb
    --maxmemory-policy allkeys-lru
```
Rule of thumb: `--maxmemory` ≈ 50% of mem_limit. `allkeys-lru` prevents out-of-memory crashes under load.

**Node.js apps (via env var):**
```yaml
n8n:
  environment:
    NODE_OPTIONS: "--max-old-space-size=512"
```
Rule of thumb: 50-75% of the container's mem_limit. Avoid setting above 80% to leave room for the JS engine and native bindings.

##### 7. Application-Specific Hardening (n8n example)

For queue-mode n8n deployments, add these to contain runaway workflows:

```yaml
n8n:
  environment:
    N8N_PAYLOAD_SIZE_MAX: 16          # Max payload MB per workflow
    EXECUTIONS_DATA_MAX_SIZE: 32      # Max MB per execution
    EXECUTIONS_DATA_PRUNE: "true"     # Auto-clean old executions
    EXECUTIONS_DATA_MAX_AGE: 168      # Keep executions for 7 days (hours)
    NODE_OPTIONS: "--max-old-space-size=512"
```

For queue mode, add workers that can be scaled independently:

```yaml
worker1:
  image: n8nio/n8n:latest
  command: worker
  mem_limit: 1g
  environment:
    # Same DB + Redis connection vars as n8n
    NODE_OPTIONS: "--max-old-space-size=512"
    N8N_PAYLOAD_SIZE_MAX: 16
```

Scale workers later without redeploying the whole stack:
```bash
docker compose up -d --scale worker1=3
```

---

## Verification

After any Docker operation, verify the result:

- **Container started?** → `docker ps` (check status is "Up")
- **Logs clean?** → `docker logs --tail 20 NAME` (no errors)
- **Port accessible?** → `curl -s http://localhost:PORT` or `docker port NAME`
- **Image built?** → `docker images | grep TAG`
- **Compose stack healthy?** → `docker compose ps` (all services "running" or "healthy")
- **Disk freed?** → `docker system df` (compare before/after)

## Dockerfile Optimization Tips

When reviewing or creating a Dockerfile, suggest these improvements:

1. **Multi-stage builds** — separate build environment from runtime to reduce final image size
2. **Layer ordering** — put dependencies before source code so changes don't invalidate cached layers
3. **Combine RUN commands** — fewer layers, smaller image
4. **Use .dockerignore** — exclude `node_modules`, `.git`, `__pycache__`, etc.
5. **Pin base image versions** — `node:20-alpine` not `node:latest`
6. **Run as non-root** — add `USER` instruction for security
7. **Use slim/alpine bases** — `python:3.12-slim` not `python:3.12`
