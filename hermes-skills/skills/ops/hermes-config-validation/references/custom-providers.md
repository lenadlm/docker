# Custom Providers: Self-Hosted LLM Backend to Hermes

## Overview

Hermes supports adding self-hosted or locally-running LLM backends as custom model providers. These use the OpenAI-compatible API format and are configured under `providers.custom.<name>` in `config.yaml`.

This is distinct from the hosted API providers (OpenRouter, Anthropic, etc.) which are managed via `providers.<provider-name>` — custom providers live under `providers.custom.*`.

## Canonical Format

**`providers` is a YAML dict, with a `custom` sub-dict whose keys are provider names:**

```yaml
providers:
  custom:
    <provider-name>:
      base_url: <openai-compatible-endpoint>/v1
      api_key: ""
```

### ❌ WRONG — `custom_providers:` as top-level key (outdated format)

```yaml
# DO NOT USE — this is an old format
custom_providers:
  - name: ollama
    base_url: http://host:11434/v1
    ...
```

The current Hermes format uses `providers.custom.<name>` with nested dicts, NOT a separate `custom_providers:` list.

### ✅ CORRECT — nested under `providers.custom`

```yaml
providers:
  custom:
    ollama:
      base_url: http://192.168.1.55:11434/v1
      api_key: ''
```

### Adding via `hermes config set` (preferred)

```bash
hermes config set providers.custom.ollama.base_url 'http://192.168.1.55:11434/v1'
hermes config set providers.custom.ollama.api_key ''
```

**Pitfall**: The `custom` provider name must not have spaces or special characters. Model tags (e.g. `llama3.1:8b`) are specified at usage time, not in the provider definition.

## Field Notes

| Field | Value | Notes |
|-------|-------|-------|
| `name` | `ollama`, `local-llama`, etc. | Dict key under `providers.custom.*` — used as `custom:<name>` in `provider:` fields |
| `base_url` | `http://<host>:<port>/v1` | Must end in `/v1` — Hermes appends `/chat/completions` etc. |
| `api_key` | `""` or actual key | Some backends require a placeholder string even if auth is disabled |

## Usage

Once configured, reference the provider as `custom:<name>` anywhere a `provider:` field appears:

```yaml
# As default model
hermes config set model.provider 'custom:ollama'
hermes config set model.default 'llama3.1:8b'

# As auxiliary service (compression)
hermes config set auxiliary.compression.provider 'custom:ollama'
hermes config set auxiliary.compression.model 'llama3.1:8b'
hermes config set auxiliary.compression.context_length 131072

# Usage from CLI
hermes --provider ollama --model qwen2.5-coder:7b
```

## Reverting to OpenRouter (or other hosted provider)

```bash
# Remove the custom provider reference by setting auxiliary services back to auto
hermes config set auxiliary.compression.provider auto
hermes config set auxiliary.compression.model ''

# The default model stays on its own provider — just set it back
hermes config set model.provider openrouter
hermes config set model.default deepseek/deepseek-v4-flash
```

## Worked Example: Ollama on Proxmox (192.168.1.55)

### Step 1: Enable LAN Listening

By default Ollama binds to `127.0.0.1:11434`. To make it accessible on the network:

```bash
# Create systemd override
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << 'EOF'
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF

# Apply
systemctl daemon-reload
systemctl restart ollama

# Verify — should show *:11434 not 127.0.0.1:11434
ss -tlnp | grep ollama
```

**Expected output:**
```
LISTEN 0  4096  *:11434  *:*  users:(("ollama",pid=NNNN,fd=4))
```

### Step 2: Verify the API is Accessible

```bash
# From the Hermes host (not the Ollama host):
curl -s http://192.168.1.55:11434/api/tags
curl -s http://192.168.1.55:11434/v1/models

# Test chat completion
curl -s -X POST http://192.168.1.55:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"Hello in 3 words"}],"stream":false}'
```

### Step 3: Configure in Hermes

```bash
hermes config set providers.custom.ollama.base_url 'http://192.168.1.55:11434/v1'
hermes config set providers.custom.ollama.api_key ''
```

### Step 4: Use the Provider

```bash
# One-shot with --provider flag
hermes --provider ollama --model qwen2.5-coder:7b

# Or as the default
hermes config set model.provider 'custom:ollama'
hermes config set model.default 'qwen2.5-coder:7b'
```

## Pitfalls

### API Key on LAN Backends
Ollama has **no native API key authentication**. On a trusted LAN, leaving `api_key: ""` is fine. If the endpoint is exposed externally, put a reverse proxy (nginx/Caddy) in front with an auth header check.

### Provider Name vs Model Tag
The `providers.custom.<name>` key is the **provider name** (e.g. `ollama`). The **model tag** (e.g. `llama3.1:8b`) is specified separately at usage time — in `model.default`, `auxiliary.X.model`, or the CLI `--model` flag. They are not the same thing.

### Reverting is Easy
```bash
# Just set everything back to auto/openrouter
hermes config set auxiliary.compression.provider auto
hermes config set model.provider openrouter
```
The custom provider definition under `providers.custom.ollama` can stay in the config harmlessly — it only activates when explicitly referenced.

### Endpoint Must Be Reachable
If Hermes is running as a VM on a different network namespace or inside a container, `localhost` won't work — use the actual LAN IP of the backend host. Test with `curl` before configuring.
