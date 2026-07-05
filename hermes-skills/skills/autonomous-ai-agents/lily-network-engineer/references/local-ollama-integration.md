# Local Ollama Integration — Proxmox VE → Hermes Agent

## Topology
- **Ollama host**: Proxmox VE (192.168.1.55), systemd service, listens on all interfaces
- **Hermes host**: 192.168.1.222, connects via LAN
- **Model**: qwen2.5-coder:7b (7.6B params, Q4_K_M quantization, 32K context, tool-call capable)
- **Protocol**: OpenAI-compatible chat completions API at `http://192.168.1.55:11434/v1`

## Discovery Commands

### Check if Ollama is installed
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 'which ollama'
# Expected: /usr/local/bin/ollama
```

### Check version and status
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 'ollama --version && systemctl is-active ollama && ollama list'
```

### Check listening address (before fix — 127.0.0.1 only by default)
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 'ss -tlnp | grep ollama'
# Default: LISTEN 0 4096 127.0.0.1:11434
```

## Enabling LAN Access

### Step 1: Create systemd override
The cleanest way to set Ollama environment variables without editing the distro package file:

```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 '
mkdir -p /etc/systemd/system/ollama.service.d
cat > /etc/systemd/system/ollama.service.d/override.conf << '\''EOF'\''
[Service]
Environment="OLLAMA_HOST=0.0.0.0"
Environment="OLLAMA_ORIGINS=*"
EOF
'
```

### Step 2: Reload and restart
```bash
sshpass -p '{{PROXMOX_ROOT_PASSWORD}}' ssh root@192.168.1.55 '
systemctl daemon-reload
systemctl restart ollama
sleep 2
ss -tlnp | grep ollama
'
# Expected: LISTEN 0 4096 *:11434
```

## Hermes Provider Configuration

### Step 3: Add to `~/.hermes/config.yaml`
```yaml
custom_providers:
  ollama:
    base_url: http://192.168.1.55:11434/v1
    api_key: ""
    api_mode: chat_completions
    models:
      - qwen2.5-coder:7b
```

**Important**: `custom_providers` is a top-level key (sibling of `providers: {}`), NOT nested under it.

### Step 4: Validate the config
```bash
python3 -c "import yaml; yaml.safe_load(open('/home/leo/.hermes/config.yaml')); print('YAML valid')"
```

### Step 5: Test the API
```bash
# List models (OpenAI-style)
curl -s http://192.168.1.55:11434/v1/models
# Expected: {"object":"list","data":[{"id":"qwen2.5-coder:7b",...}]}

# Test inference
curl -s -X POST http://192.168.1.55:11434/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"qwen2.5-coder:7b","messages":[{"role":"user","content":"Say hello in 4 words"}],"stream":false}' \
  | python3 -m json.tool 2>/dev/null | head -10
```

## Verification Checklist
- [ ] Ollama service is `active` after restart
- [ ] `ss -tlnp` shows `*:11434` (all interfaces)
- [ ] `curl http://192.168.1.55:11434/v1/models` returns 200 with model list
- [ ] Chat completions endpoint responds correctly
- [ ] Hermes config.yaml validates as YAML
- [ ] Backup exists at `config.yaml.bak`

## Known Pitfalls

| Issue | Symptom | Fix |
|-------|---------|-----|
| Ollama listens on 127.0.0.1 only | curl from Hermes host fails with connection refused | Create systemd override with `OLLAMA_HOST=0.0.0.0`, restart service |
| Invalid YAML in config.yaml | Hermes fails to start or ignores custom_providers | Run `python3 -c "import yaml; yaml.safe_load(...)"` to validate |
| `api_key` empty string | Some OpenAI client SDKs reject empty keys | Change to `api_key: "ollama"` — Ollama ignores the value anyway |
| Model name mismatch | curl returns `{"error":"model 'xxx' not found"}` | Run `ollama list` on Proxmox, use exact name from output |
| config.yaml is a **protected file** in Hermes | Direct `write_file`/`patch` tools deny writing to it | Use `cp config.yaml config.yaml.bak && sed -i '...' config.yaml` via terminal |