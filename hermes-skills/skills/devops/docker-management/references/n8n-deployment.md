# n8n Deployment Reference

Deploying n8n with Postgres + Redis backend on a standalone Docker Compose host.

## Minimal Environment Variables (`.env`)

```
N8N_DB_PASSWORD=openssl rand -base64 24)
N8N_ENCRYPTION_KEY=*** rand -hex 32)
N8N_BASIC_AUTH_USER=admin
N8N_BASIC_AUTH_PASSWORD=openssl rand -base64 18)
```

## Compose Structure (5 Services)

| Service | Image | Purpose |
|---|---|---|
| `postgres` | postgres:16-alpine | Workflow DB |
| `redis` | redis:7-alpine | Queue broker |
| `n8n` | n8nio/n8n:latest | Main web UI (port 5678) |
| `worker1` | n8nio/n8n:latest | Queue worker (no port) |
| `postgres-backup` | prodrigestivill/postgres-backup-local:16-alpine | Daily DB backup |

## Key Environment Vars for n8n

```yaml
# Queue mode (required for workers)
EXECUTIONS_MODE: queue
QUEUE_BULL_REDIS_HOST: redis
QUEUE_BULL_REDIS_PORT: 6379

# Web UI access
N8N_HOST: 192.168.1.220
N8N_PORT: 5678
WEBHOOK_URL: http://192.168.1.220:5678/

# Security
N8N_SECURE_COOKIE: "false"           # HTTP access; "true" if behind HTTPS proxy
N8N_BASIC_AUTH_ACTIVE: "true"
N8N_BASIC_AUTH_USER: ${N8N_BASIC_AUTH_USER:-admin}
N8N_BASIC_AUTH_PASSWORD: ${N8N_BASIC_AUTH_PASSWORD:?required}

# Workflow limits
N8N_PAYLOAD_SIZE_MAX: 16             # Max MB per workflow payload
EXECUTIONS_DATA_MAX_SIZE: 32         # Max MB per execution
EXECUTIONS_DATA_PRUNE: "true"
EXECUTIONS_DATA_MAX_AGE: 168         # 7 days

# Node.js heap
NODE_OPTIONS: "--max-old-space-size=512"
```

## Secure Cookie Handling

The `N8N_SECURE_COOKIE` error appears when accessing n8n over HTTP with the cookie set to `true`:

```
Your n8n server is configured to use a secure cookie,
however you are either visiting this via an insecure URL, or using Safari.
```

**Fix for HTTP access**: Set `N8N_SECURE_COOKIE: "false"`
**Fix for HTTPS access**: Set `N8N_SECURE_COOKIE: "true"` → requires TLS/proxy termination

## Postgres Tuning

```yaml
command: "postgres -c shared_buffers=128MB -c work_mem=16MB -c effective_cache_size=512MB"
```

## Redis Tuning

```yaml
command: >
  redis-server --appendonly yes
  --appendfsync everysec
  --maxmemory 128mb
  --maxmemory-policy allkeys-lru
```

## Scaling Workers

```bash
# Scale to 3 workers
docker compose up -d --scale worker1=3
```

All workers pull from the same Redis queue. Each gets its own memory limit.

## First-Run Setup

1. Deploy: `docker compose up -d`
2. Access: `http://<host>:5678`
3. Login: `admin` + password from `.env`
4. (Optional) Create Cloudflare tunnel → switch `N8N_SECURE_COOKIE` to `"true"`