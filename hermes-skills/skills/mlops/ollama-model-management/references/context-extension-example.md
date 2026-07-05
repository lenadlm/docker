# Context Extension Example: Qwen2.5-Coder 32K → 64K on Proxmox

## Environment
- **Host:** Proxmox VE at 192.168.1.55 (hostname: `pve`)
- **SSH user:** root
- **Ollama version:** via official systemd service
- **Base model:** qwen2.5-coder:7b (4.7 GB)
- **Target model:** qwen2.5-coder-64k

## Complete Command Sequence

```bash
# 1. Verify Ollama is running
ssh root@192.168.1.55 'systemctl status ollama --no-pager'
# Output: Active: active (running), PID 1307, Memory 39.5M (peak 4.7G)

# 2. Check existing models
ssh root@192.168.1.55 'ollama list'

# 3. Check RAM headroom
ssh root@192.168.1.55 'free -h'
# Result: 31 GB total, 19 GB available — plenty of headroom

# 4. Create Modelfile locally, send to host
cat > /tmp/Modelfile << 'EOF'
FROM qwen2.5-coder:7b
PARAMETER num_ctx 65536
EOF

scp /tmp/Modelfile root@192.168.1.55:/root/Modelfile

# 5. Build new model
ssh root@192.168.1.55 'ollama create qwen2.5-coder-64k -f /root/Modelfile'
# Output: gathering model components → using existing layers → success

# 6. Verify
ssh root@192.168.1.55 'ollama list'
# Shows: qwen2.5-coder-64k:latest  4.7 GB  (new, separate entry)
#        qwen2.5-coder:7b          4.7 GB  (original, untouched)

ssh root@192.168.1.55 'ollama run qwen2.5-coder-64k "respond with OK if you are working"'
# Output: OK

# 7. Point Hermes config at the new model
hermes config set model.default qwen2.5-coder-64k
hermes config set model.provider custom:ollama
hermes config set custom_providers '[{"name":"ollama","base_url":"http://192.168.1.55:11434/v1","api_key":"","api_mode":"chat_completions","models":["qwen2.5-coder:7b","qwen2.5-coder-64k"]}]'
```

## RAM Profile

| Metric | Before | After (model loaded) |
|--------|--------|---------------------|
| Used   | 11 GB  | 18 GB               |
| Available | 19 GB | 12 GB               |
| Ollama RSS | 39.5 MB | 47 MB (peak 4.7 GB during inference) |

The 7 GB bump is Ollama caching the model in memory. It unloads after ~5 min idle.

## Key Observations

- `ollama create` is instant — it only writes metadata pointing at existing model layers
- The model doesn't actually load into RAM until the first `ollama run`
- Peak memory (4.7 GB) matches the model file size on disk
- Original `qwen2.5-coder:7b` is completely untouched