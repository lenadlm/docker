# Guacamole Deployment

Deploy Apache Guacamole (clientless SSH/RDP/VNC gateway) on Docker for homelab VM access.

## Architecture

```
Browser → guacamole:8080 → guacd:4822 → VM (SSH)
                              ↓
                       PostgreSQL (auth/sessions)
```

## Quick Deploy (3 containers)

### 1. Generate DB Schema

```bash
# ⚠️ Flag is --postgresql, NOT --postgres
mkdir -p /docker/guacamole
docker run --rm guacamole/guacamole:latest /opt/guacamole/bin/initdb.sh --postgresql \
  > /docker/guacamole/initdb.sql
# Expected: ~793 lines, starts with Apache license header
```

### 2. Create docker-compose.yml

```yaml
services:
  guacamole-postgres:
    image: postgres:16-alpine
    container_name: guacamole-postgres
    restart: unless-stopped
    networks:
      - internal_network
    volumes:
      - /docker/guacamole/postgres:/var/lib/postgresql/data
      - /docker/guacamole/initdb.sql:/docker-entrypoint-initdb.d/initdb.sql:ro
    environment:
      - POSTGRES_USER=${GUACAMOLE_DB_USER:-guacamole}
      - POSTGRES_PASSWORD=${GUACAMOLE_DB_PASSWORD}
      - POSTGRES_DB=${GUACAMOLE_DB_NAME:-guacamole_db}
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${GUACAMOLE_DB_USER:-guacamole} -d ${GUACAMOLE_DB_NAME:-guacamole_db}"]
      interval: 10s
      timeout: 5s
      retries: 5

  guacd:
    image: guacamole/guacd:latest
    container_name: guacamole-guacd
    restart: unless-stopped
    networks:
      - internal_network
    command: ["/opt/guacamole/sbin/guacd", "-b", "0.0.0.0", "-L", "debug"]
    healthcheck:
      test: netstat -tln | grep 4822
      interval: 30s
      timeout: 5s
      retries: 3

  guacamole:
    image: guacamole/guacamole:latest
    container_name: guacamole
    restart: unless-stopped
    networks:
      - external_network
      - internal_network
    ports:
      - "8080:8080"
    depends_on:
      guacamole-postgres:
        condition: service_healthy
      guacd:
        condition: service_started
    volumes:
      # ⚠️ REQUIRED: guacamole.properties bypasses the env-var-to-property
      # mapping bug that causes "Property 'postgresql-port' must be an integer"
      - ./guacamole.properties:/etc/guacamole/guacamole.properties:ro
    environment:
      # NOTE: POSTGRESQL_PORT is NOT reliable via env vars — the
      # IntegerGuacamoleProperty parser fails on string env values.
      # Use guacamole.properties instead (see below).
      POSTGRES_HOSTNAME: guacamole-postgres
      POSTGRES_USER: ${GUACAMOLE_DB_USER:-guacamole}
      POSTGRES_PASSWORD: ${GUACAMOLE_DB_PASSWORD}
      POSTGRES_DATABASE: ${GUACAMOLE_DB_NAME:-guacamole_db}
      # Default web admin — change password on first login
      GUACAMOLE_USER: ${GUACAMOLE_USER:-guacadmin}
      GUACAMOLE_PASSWORD: ${GUACAMOLE_PASSWORD}

networks:
  external_network:
    external: true
  internal_network:
    external: true
```

### 2b. Create guacamole.properties (REQUIRED — fixes extension loading bug)

The PostgreSQL auth extension (`guacamole-auth-jdbc-postgresql`) defines `postgresql-port` as an `IntegerGuacamoleProperty`. When loaded via `enable-environment-properties: true`, the env var value `"5432"` fails parsing with:

```
ERROR - authentication provider extension failed to start:
        Property "postgresql-port" must be an integer.
```

**Root cause**: `SystemEnvironmentGuacamoleProperties` reads env vars as `String` via `System.getenv()`, and the `IntegerGuacamoleProperty` doesn't accept the string representation. The `POSTGRESQL_PORT` env var IS set in the container but the Guacamole property parser rejects it.

**Fix**: Mount a `guacamole.properties` file with the PostgreSQL connection properties as typed values:

```properties
# guacamole.properties — bypasses env-var-to-property mapping bug
# Mount at /etc/guacamole/guacamole.properties
postgresql-hostname: guacamole-postgres
postgresql-port: 5432
postgresql-database: guacamole_db
postgresql-username: guacamole
postgresql-password: <from .env>
```

Generate the file from .env at deploy time:

```bash
cat > /docker/guacamole/guacamole.properties << PROPEOF
postgresql-hostname: guacamole-postgres
postgresql-port: 5432
postgresql-database: ${GUACAMOLE_DB_NAME}
postgresql-username: ${GUACAMOLE_DB_USER}
postgresql-password: ${GUACAMOLE_DB_PASSWORD}
PROPEOF
```

### 3. Create .env

```bash
GUAC_DB_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(24))")
GUAC_ADMIN_PASS=$(python3 -c "import secrets; print(secrets.token_urlsafe(16))")

cat > /docker/guacamole/.env << EOF
GUACAMOLE_DB_USER=guacamole
GUACAMOLE_DB_NAME=guacamole_db
GUACAMOLE_DB_PASSWORD=${GUAC_DB_PASS}
GUACAMOLE_USER=guacadmin
GUACAMOLE_PASSWORD=${GUAC_ADMIN_PASS}
EOF
```

### 4. Deploy

```bash
cd /docker/guacamole && docker compose up -d

# Verify all containers healthy
docker compose ps
# Expected: 3 containers, guacamole-postgres "healthy", rest "Up"

# Test HTTP
curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/guacamole/
# Expected: 200

# Check logs for extension loading errors
docker logs guacamole 2>&1 | grep -i -E "ERROR|extension|postgresql"
# Should NOT show "must be an integer" error
```

## Adding Connections (Post-Deploy)

### Via Web UI

Access the web UI at `http://<host>:8080/guacamole/` and login with `guacadmin`.

| Connection Type | Host | Port | Use Case |
|----------------|------|------|----------|
| SSH | VM IP | 22 | Linux terminal access |
| RDP | VM IP | 3389 | Windows desktop |
| VNC | VM IP | 5900 | Console access (requires VNC server in VM) |

### Via REST API (Automated)

Create SSH, RDP, or VNC connections programmatically — useful for scripting, bootstrapping, or automation when the web UI is unavailable or you need repeatable deployment.

**1. Authenticate**

```bash
TOKEN=*** -s -X POST \
  -d 'username=guacadmin&password=<password>' \
  http://localhost:8080/guacamole/api/tokens \
  | python3 -c "import json,sys; print(json.load(sys.stdin)['authToken'])")
```

**2. Get the root connection group**

```bash
curl -s "http://localhost:8080/guacamole/api/session/data/postgresql/connectionGroups/ROOT/tree?token=$TOKEN"
# Returns: {\"identifier\":\"ROOT\", ...}
```

The root group identifier is always `\"ROOT\"` on a fresh installation.

**3. Create an SSH connection**

```bash
curl -s -X POST \
  "http://localhost:8080/guacamole/api/session/data/postgresql/connections?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "My Ubuntu VM",
    "parentIdentifier": "ROOT",
    "protocol": "ssh",
    "parameters": {
      "hostname": "192.168.1.100",
      "port": "22",
      "username": "leo",
      "password": "<vm_password>",
      "font-name": "monospace",
      "font-size": "10",
      "color-scheme": "white-black"
    },
    "attributes": {}
  }'
# Expected response includes the new connection identifier
```

**4. Verify the connection**

```bash
curl -s "http://localhost:8080/guacamole/api/session/data/postgresql/connections?token=$TOKEN" \
  | python3 -c "
import json,sys
d = json.load(sys.stdin)
for k,v in d.items():
    print(f'{k}: {v[\"name\"]} ({v[\"protocol\"]})')
"
```

**Protocol-specific parameters**

| Protocol | Required Parameters | Notes |
|----------|-------------------|-------|
| SSH | `hostname`, `port`, `username`, `password` | Or `private-key` + `passphrase` instead of password |
| RDP | `hostname`, `port` (3389), `username`, `password` | Add `security: \"nla\"` for Windows auth |
| VNC | `hostname`, `port` (5900), `password` | Also set `color-depth: \"16\"` for performance |

**Private key auth (SSH)** — embed the key content as a parameter:

```bash
# Read and JSON-escape the private key
PRIVATE_KEY_JSON=$(cat ~/.ssh/id_ed25519 | python3 -c "import json,sys; print(json.dumps(sys.stdin.read()))")

curl -s -X POST \
  "http://localhost:8080/guacamole/api/session/data/postgresql/connections?token=$TOKEN" \
  -H "Content-Type: application/json" \
  -d "{
    \"name\": \"Ubuntu VM (key)\",
    \"parentIdentifier\": \"ROOT\",
    \"protocol\": \"ssh\",
    \"parameters\": {
      \"hostname\": \"192.168.1.100\",
      \"port\": \"22\",
      \"username\": \"leo\",
      \"private-key\": $PRIVKEY,
      \"font-name\": \"monospace\",
      \"font-size\": \"10\"
    },
    \"attributes\": {}
  }"
```

**API token usage**: The Guacamole REST API accepts the auth token as:
- Query parameter: `?token=<TOKEN>` (used throughout this reference)
- Cookie: `GUAC_AUTH=<TOKEN>`
- Authorization header: `Bearer <TOKEN>`

## Password Management

### Default Credentials

- Username: `guacadmin`
- Password: `guacadmin` (from initdb.sql default hash)

### Password Hashing

Guacamole stores passwords in the `guacamole_user` table with:

| Column | Type | Description |
|--------|------|-------------|
| `password_hash` | `bytea` | SHA-256 digest |
| `password_salt` | `bytea` | 32-byte random salt |
| `password_date` | `timestamptz` | When password was set |

The hash algorithm (from `SHA256PasswordEncryptionService.java`):

```java
builder.append(password);
builder.append(BaseEncoding.base16().encode(salt));
// SHA-256 of (password + uppercase_hex(salt))
```

Equivalent Python:

```python
import hashlib
salt_bytes = bytes.fromhex('fe24adc5...')  # from DB password_salt
password = b'guacX-2024'
# Base16 = uppercase hex of the raw salt bytes
salt_hex = salt_bytes.hex().upper()
pw_hash = hashlib.sha256(password + salt_hex.encode()).hexdigest()
```

### Reset Password via SQL

When the web UI is inaccessible (e.g., forgotten password, or the JDBC auth extension failed to load), reset directly:

```bash
# Generate new salt and hash
python3 << 'PYEOF'
import hashlib, secrets
salt = secrets.token_hex(32)  # 32 bytes = 64 hex chars
salt_hex = salt.upper()
password = b'guacX-2024'  # ← change to desired password
pw_hash = hashlib.sha256(password + salt_hex.encode()).hexdigest()
print(f'SALT={salt}')
print(f'HASH={pw_hash}')
# Verify
verify = hashlib.sha256(password + bytes.fromhex(salt).hex().upper().encode()).hexdigest()
print(f'VERIFY={verify == pw_hash}')
PYEOF

# Update the database
docker exec guacamole-postgres psql -U guacamole -d guacamole_db -c "
UPDATE guacamole_user
SET password_hash = decode('HASH_FROM_ABOVE', 'hex'),
    password_salt = decode('SALT_FROM_ABOVE', 'hex'),
    password_date = CURRENT_TIMESTAMP
WHERE entity_id = (SELECT entity_id FROM guacamole_entity
                   WHERE name = 'guacadmin' AND type = 'USER');
"
```

### Verify Login via API

```bash
curl -s -X POST -d 'username=guacadmin&password=guacX-2024' \
  http://localhost:8080/guacamole/api/tokens
# Expected: {"authToken":"...","dataSource":"..."}
# On failure: {"type":"INVALID_CREDENTIALS","message":"Permission Denied."}
```

## Pitfalls

- **`--postgres` vs `--postgresql`**: initdb.sh accepts `--postgresql`, `--mysql`, or `--sqlserver`. `--postgres` fails with "Bad database type".
- **initdb.sql must be mounted before postgres starts**: The PostgreSQL `docker-entrypoint-initdb.d/` directory only runs SQL scripts on *first* initialization. If the data volume already exists, mount the init script and restarting won't re-run it — delete the data dir and re-deploy instead.
- **Extension loading failure**: Without `guacamole.properties`, the PostgreSQL auth extension fails with "Property 'postgresql-port' must be an integer." The env var `POSTGRESQL_PORT=5432` is set in the container but the `IntegerGuacamoleProperty` parser rejects it. Always mount a `guacamole.properties` file.
- **Healthcheck format**: PostgreSQL healthchecks need `CMD-SHELL` (not bare string) to handle env var interpolation: `test: ["CMD-SHELL", "pg_isready -U ${GUACAMOLE_DB_USER:-guacamole}"]`
- **External networks**: Both `external_network` (for browser traffic) and `internal_network` (for PostgreSQL/guacd communication) must exist before deploy: `docker network create external_network && docker network create internal_network`
- **Port 8080 conflict**: Check `ss -tlnp | grep :8080` before deploying. If taken, change the host port in `ports:`.
- **Rate limiting**: After 5 failed auth attempts in 300 seconds, the ban extension locks the IP. Check `docker logs guacamole | grep "Authentication has failed"` for ban messages. Wait 5 minutes or restart the container.
- **Password hash byte order**: The salt is stored as raw bytes (decode'd from hex). The hash is computed over `password + uppercase_hex_string(bytes)`, NOT over `password + raw_bytes`. Using lower-case hex or raw bytes produces a different hash.
- **Health check pipe exit code**: `test: curl -f http://localhost:8080/guacamole/ | grep -q "Guacamole"` uses a **pipe** — the health check exit code comes from the *last* command in the pipeline (grep), not curl. If the HTML doesn't contain the literal string "Guacamole", grep returns 1 even though the server responds 200. Always use **exec format** for health checks involving pipes or conditional logic:
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-fs", "http://localhost:8080/guacamole/"]
  ```
  This returns 0 on any successful HTTP response (<400) and non-zero on failure.
- **Dark theme via extension — WILL NOT WORK without Java classes**: Guacamole 24.04 (and likely all 1.x versions) does **not** serve CSS-only extensions. Creating a `.jar` with `guac-manifest.json` referencing CSS files and a `resources` section loads the extension (logged as loaded) but the CSS is never injected into the page. The JavaScript client fetches extension resources via the REST API (`api/session/ext/<token>`), which only returns metadata — not the actual CSS files. To inject custom CSS, you would need a **Java authentication provider** (or at minimum a Java class implementing `GuacamoleExtension` with proper resource serving). A pure CSS/JS manifest extension does not work. Workarounds that also didn't work:
  - Adding `"resources"` to the manifest
  - Using the `stylesheet` property in `guacamole.properties` (doesn't exist in standard Guacamole)
  - Mounting the CSS into the container at custom paths
  The only reliable approach for dark mode is to either:
  1. Write a tiny Java branding extension with proper `@Theme` annotation
  2. Inject CSS via a reverse proxy (nginx/sidecar container that modifies the HTML before delivery)
  3. Use a third-party forked image (e.g., `oznu/guacamole` which has built-in dark theme)