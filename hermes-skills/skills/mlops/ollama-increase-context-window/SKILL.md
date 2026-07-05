---
name: ollama-increase-context-window
description: Increase the context window of an existing Ollama model by creating a variant with a larger num_ctx value.
---

# Increase Ollama Model Context Window

Create a model variant with a larger context window (e.g., 32K → 65K) without re-downloading.

## Steps

1. Create a Modelfile:

```
FROM <base-model>:latest
PARAMETER num_ctx <desired-context>
```

2. Push it to the remote Ollama instance:

```bash
# Set remote Ollama host
export OLLAMA_HOST=http://<ip>:11434

# Create the variant (instant — reuses existing layers)
ollama create <base-model>-<ctx-label> -f /path/to/Modelfile
```

3. Verify:

```bash
ollama show <base-model>-<ctx-label>
# Look for: Parameters → num_ctx <desired-context>
```

## Hermes Integration

After creating the variant, wire it into Hermes:

```bash
# Override context length check
hermes config set model.context_length <desired-context>

# Point primary model at the new variant
hermes config set smart_model_routing.primary_model '{"provider": "custom:ollama", "model": "<base-model>-<ctx-label>"}'

# Add the variant to custom_providers model list
hermes config set custom_providers '[{"name": "ollama", "base_url": "http://<ip>:11434/v1", "api_key": "", "api_mode": "chat_completions", "models": ["<base-model>", "<base-model>-<ctx-label>"]}]'
```

## Notes

- The model's base metadata still reports the original context length — that's the architecture default and is ignored at runtime.
- Ollama's `num_ctx` parameter is what actually determines the context allocation during inference.
- Larger context = proportional VRAM increase (roughly 4x memory for 2x context on most architectures).
- The `ollama create` command is instant since it reuses existing model layers and only applies the parameter override.