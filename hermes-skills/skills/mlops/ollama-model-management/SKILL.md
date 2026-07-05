---
name: ollama-model-management
description: "Manage Ollama-served models — create Modelfiles, extend context windows, build named model variants, verify health. Covers remote-host orchestration (SSH), RAM headroom estimation, and the full create → verify → test cycle."
version: 1.0.0
author: Hermes Agent
metadata:
  ollama:
    tags: [ollama, modelfile, context-window, inference, model-management]
    related_skills: [hermes-config-updates, serving-llms-vllm, llama-cpp]
---

# Ollama Model Management

Create new named model variants from existing Ollama models by modifying parameters through Modelfiles. The canonical use case is extending context windows (`num_ctx`), but any Ollama PARAMETER can be overridden this way.

## Workflow

### 1. Verify Ollama is accessible

```bash
# If Ollama is local:
ollama list

# If Ollama is on a remote host (use OLLAMA_HOST — no SSH needed):
OLLAMA_HOST=http://<host>:11434 ollama list

# Or via API health check:
curl -s http://<host>:11434/api/tags | python3 -m json.tool
```

The `OLLAMA_HOST` env var is the **preferred approach** for remote hosts — it avoids SSH key setup and works from any machine with the ollama CLI installed.

### 2. Check available models

```bash
ollama list
```

Confirm the base model is already pulled before attempting to create a variant.

### 3. Estimate RAM headroom

A 64K context KV cache adds roughly this much overhead over 32K:

| Model size | Extra RAM (32K→64K) | Notes |
|------------|---------------------|-------|
| 3B  | ~60-80 MB | Trivial |
| 7B  | ~120-160 MB | Usually fine with 4+ GB free |
| 13B | ~240-320 MB | Needs ~8 GB free |
| 70B | ~1.2-1.6 GB | Needs ~20+ GB free |

Quick check:

```bash
free -h
```

**Warning threshold:** If available RAM is less than **2× the model size** + 1 GB, warn the user. The model's peak memory (from `systemctl status ollama`) plus the KV cache overhead must fit comfortably.

### 4. Create Modelfile

```bash
cat > Modelfile << 'EOF'
FROM <base-model>:<tag>
PARAMETER num_ctx 65536
EOF
```

Other common PARAMETER overrides:

- `num_ctx` — context window size (tokens)
- `temperature` — generation temperature (0.0-2.0)
- `top_p` — nucleus sampling threshold
- `num_predict` — max tokens to generate
- `stop` — stop sequences

### 5. Build the new named model

```bash
ollama create <new-model-name> -f Modelfile
```

The name should be descriptive, e.g. `qwen2.5-coder-64k` (base + override). This is a **new separate model entry** — the original remains untouched.

### 6. Verify

```bash
ollama list                                  # Confirm it appears
ollama run <new-model-name> "respond with OK if you are working"  # Functional test
```

### 7. Point Hermes at the new model (if applicable)

```bash
# Option A: Set as the default model directly
hermes config set model.default <model-name>
hermes config set model.provider custom:ollama

# Option B (recommended): Use smart_model_routing for automatic model selection
hermes config set smart_model_routing.primary_model '{"provider": "custom:ollama", "model": "<model-name>"}'

# Always update custom_providers to add the new model to the model list:
hermes config set custom_providers '<json-array-including-new-model>'

# CRITICAL: If the model's base metadata reports a smaller context length than
# what you set via num_ctx, override Hermes' minimum context check:
hermes config set model.context_length <num_ctx-value>
```

Note: `hermes config set` for array values stores them as JSON strings inside YAML. This is normal — Hermes' config parser handles both formats.

---

## Pitfalls

- **Do NOT modify the original model** — always create a named variant. The original serves as a fallback.
- **RAM underestimation** — The `ollama create` command itself is lightweight (just metadata), but `ollama run` loads the model into memory. Peak RAM usage occurs during inference, not during creation.
- **SSH key issues** — If accessing a remote Ollama host, verify SSH key auth first. Test with `ssh -o PreferredAuthentications=publickey user@host 'hostname'`.
- **Model unload** — Ollama unloads idle models after ~5 min. RAM usage drops back down. This is normal.
- **num_ctx limits** — Each model has an architectural max context length. Setting `num_ctx` above the model's trained maximum may produce degraded output or memory errors. Check the model's config for `max_position_embeddings`.
- **Model metadata mismatch** — `ollama show <model>` shows `num_ctx <value>` in the Parameters section, but the **context length** metadata field often still reports the original architecture default (e.g. 32768). This is cosmetic — Ollama allocates `num_ctx` at runtime. **However**: Hermes reads the metadata field for its 64K minimum check, so you MUST also set `model.context_length` in Hermes config to match your `num_ctx` value, or the model will be rejected at startup.

## Remote Model Operations (Pull, Abort, Cleanup)

### Remote Pull with Background Tracking

When pulling a large model on a remote host via SSH, use Hermes' background process tracking:

```bash
# Start the pull with notify_on_complete
terminal(
  command="ssh user@host 'ollama pull <model-tag>'",
  background=True,
  notify_on_complete=True
)
```

This returns a `session_id` immediately. The system notifies you when the download finishes.

### Aborting a Remote Pull

If the user changes their mind mid-download, the pull must be killed **at both ends**:

```bash
# 1. Kill the local Hermes background process
process(action='kill', session_id='<session-id>')

# 2. Kill the remote SSH command (process.kill sends SIGTERM which may not propagate)
ssh user@host "pkill -f 'ollama pull <model-tag>'"

# 3. Clean up partial download from Ollama's cache
ssh user@host "ollama rm <model-tag> 2>/dev/null"
```

**Why both steps?** `process(kill)` sends SIGTERM to the local `ssh` process, but the remote `ollama pull` may keep running on the host if it doesn't get the signal. The `pkill -f` on the remote host ensures it's truly dead.

### Cleanup After Partial Download

Ollama stores partial downloads in its blob store. Even after killing the pull, partial blobs linger:

```bash
# Clean up any partial model
ollama rm <model-tag>
# If the pull didn't start writing manifests yet, this is a no-op

# Verify the model is truly gone
ollama list
```

**Expected output** after successful abort: the model tag should not appear in `ollama list`.

### Pull Progress Monitoring

Ollama's pull output includes:
```
pulling <sha-prefix>:  XX% |██████               |  XXX MB/8.9 GB  2.0 MB/s    1h0m
```

The percentage and speed give a reasonable ETA. For very large models (16B+ = ~8-16 GB), expect download times of **30 min to 2 hours** depending on bandwidth (2-4 MB/s typical at consumer speeds).

### Storage Considerations

Check available disk space before starting a pull:

```bash
# On the target host
df -h /usr/share/ollama/.ollama/models  # or wherever Ollama stores models
ollama list  # check current disk usage by existing models
```

| Model Size | Approx Download | Typical Time at 3 MB/s |
|------------|----------------|----------------------|
| 7B (Q4)    | 4.7 GB         | ~25 min              |
| 8B (Q4)    | 4.9 GB         | ~27 min              |
| 16B (Q4)   | ~8-9 GB        | ~45-60 min           |
| 70B (Q4)   | ~40 GB         | ~3.5-4 h             |

### Background Process Lifecycle Summary

```
terminal(background=True, notify_on_complete=True)
    → session_id returned immediately
    → Process runs in background
    → system notifies on completion OR
    → process(action='wait', session_id=...) for synchronous blocking
    → process(action='poll', session_id=...) for non-blocking status
    → process(action='log', session_id=...) for full output
    → process(action='kill', session_id=...) to abort
```

## References

For the exact commands and output from an end-to-end 7B model 32K→64K extension session, see `references/context-extension-example.md`.

## Verification Steps

```bash
# Confirm new model exists
ollama list | grep -E "<new-model>"

# CRITICAL: Verify num_ctx parameter is set correctly
ollama show <new-model> | grep -E "(num_ctx|context length|Parameters)"

# Functional test
ollama run <new-model> -- "respond with OK if you are working"
# The `-- ` separates CLI flags from the prompt

# Check RAM headroom
free -h

# Or check via API (no CLI needed):
curl -s http://<host>:11434/api/show -d '{"model":"<new-model>"}' | python3 -c "
import sys, json
d = json.load(sys.stdin)
print('Modelfile:', d.get('modelfile', 'N/A'))
print('Parameters:', d.get('parameters', 'N/A'))
"
```