---
name: ai-music
description: "AI music and audio generation — HeartMuLa (open-source Suno-like) and AudioCraft/MusicGen (Meta) for text-to-music, text-to-sound, melody conditioning, and style transfer."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [music, audio, generation, ai, heartmula, audiocraft, musicgen, audiogen, text-to-music]
    related_skills: [songwriting-and-ai-music, songsee]
---

# AI Music & Audio Generation

Generate music and sound effects using open-source AI models. Coverage: **HeartMuLa** (Suno-like, lyrics+tags), **AudioCraft** (Meta's MusicGen/AudioGen).

For audio analysis/visualization, see `songsee`. For songwriting craft and Suno prompt engineering, see `songwriting-and-ai-music`.

---

## HeartMuLa — Open-Source Suno Alternative

[HeartMuLa](https://github.com/HeartMuLa/heartlib) generates music from lyrics + tags. Apache-2.0. Includes HeartCodec audio codec.

### Hardware Requirements
- **Minimum**: 8GB VRAM with `--lazy_load true`
- **Recommended**: 16GB+ VRAM
- **Multi-GPU**: `--mula_device cuda:0 --codec_device cuda:1`
- CPU mode works but is extremely slow (30-60+ min per song)

### Installation
```bash
git clone https://github.com/HeartMuLa/heartlib.git
cd heartlib
uv venv --python 3.10 .venv
. .venv/bin/activate
uv pip install -e .
uv pip install --upgrade datasets transformers
```

### Dependency Fixes
**Patch 1** in `src/heartlib/heartmula/modeling_heartmula.py`: Add RoPE reinit after `reset_caches`:
```python
from torchtune.models.llama3_1._position_embeddings import Llama3ScaledRoPE
for module in self.modules():
    if isinstance(module, Llama3ScaledRoPE) and not module.is_cache_built:
        module.rope_init()
        module.to(device)
```

**Patch 2** in `src/heartlib/pipelines/music_generation.py`: Add `ignore_mismatched_sizes=True` to all `HeartCodec.from_pretrained()` calls.

### Download models
```bash
cd heartlib
hf download --local-dir './ckpt' 'HeartMuLa/HeartMuLaGen'
hf download --local-dir './ckpt/HeartMuLa-oss-3B' 'HeartMuLa/HeartMuLa-oss-3B-happy-new-year'
hf download --local-dir './ckpt/HeartCodec-oss' 'HeartMuLa/HeartCodec-oss-20260123'
```

### Basic generation
```bash
cd heartlib && . .venv/bin/activate
python ./examples/run_music_generation.py \
  --model_path=./ckpt --version="3B" \
  --lyrics="./assets/lyrics.txt" --tags="./assets/tags.txt" \
  --save_path="./assets/output.mp3" --lazy_load true
```

### Key parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `--max_audio_length_ms` | 240000 | Max length in ms (240s) |
| `--topk` | 50 | Top-k sampling |
| `--temperature` | 1.0 | Sampling temperature |
| `--cfg_scale` | 1.5 | Classifier-free guidance scale |
| `--lazy_load` | false | Load/unload models on demand |

### Pitfalls
- **Do NOT use bf16 for HeartCodec** — degrades audio. Use fp32.
- Tags may be ignored (known issue). Lyrics dominate; experiment with tag ordering.
- Triton not available on macOS.
- RTX 5080 incompatibility reported.

---

## AudioCraft (Meta MusicGen/AudioGen)

Meta's [AudioCraft](https://github.com/facebookresearch/audiocraft) for text-to-music (MusicGen) and text-to-sound (AudioGen).

### Installation
```bash
pip install audiocraft
# Or via HuggingFace Transformers
pip install transformers torch torchaudio
```

### Quick start — MusicGen
```python
import torchaudio
from audiocraft.models import MusicGen

model = MusicGen.get_pretrained('facebook/musicgen-small')
model.set_generation_params(duration=8, top_k=250, temperature=1.0)
wav = model.generate(["happy upbeat electronic dance music with synths"])
torchaudio.save("output.wav", wav[0].cpu(), sample_rate=32000)
```

### Quick start — AudioGen (sound effects)
```python
from audiocraft.models import AudioGen
model = AudioGen.get_pretrained('facebook/audiogen-medium')
model.set_generation_params(duration=5)
wav = model.generate(["dog barking in a park with birds chirping"])
torchaudio.save("sound.wav", wav[0].cpu(), sample_rate=16000)
```

### Model variants
| Model | Size | Use Case |
|-------|------|----------|
| `musicgen-small` | 300M | Quick generation |
| `musicgen-medium` | 1.5B | Balanced |
| `musicgen-large` | 3.3B | Best quality |
| `musicgen-melody` | 1.5B | Melody conditioning |
| `musicgen-stereo-medium` | 1.5B | Stereo output |
| `musicgen-style` | 1.5B | Style transfer |
| `audiogen-medium` | 1.5B | Sound effects |

### Melody-conditioned generation
```python
model = MusicGen.get_pretrained('facebook/musicgen-melody')
melody, sr = torchaudio.load("melody.wav")
wav = model.generate_with_chroma(["acoustic guitar folk song"], melody, sr)
```

### Generation parameters
| Parameter | Default | Description |
|-----------|---------|-------------|
| `duration` | 8.0 | Length in seconds (1-120) |
| `top_k` | 250 | Top-k sampling |
| `top_p` | 0.0 | Nucleus sampling |
| `temperature` | 1.0 | Sampling temperature |
| `cfg_coef` | 3.0 | Classifier-free guidance |

### VRAM requirements
| Model | FP32 | FP16 |
|-------|------|------|
| musicgen-small | ~4GB | ~2GB |
| musicgen-medium | ~8GB | ~4GB |
| musicgen-large | ~16GB | ~8GB |

### Common issues
- **Poor quality**: Increase `cfg_coef`, improve prompts
- **CUDA OOM**: Use smaller model, reduce duration
- **Stereo not working**: Use `musicgen-stereo-*` variant

### References
- GitHub: https://github.com/facebookresearch/audiocraft
- Paper (MusicGen): https://arxiv.org/abs/2306.05284
- Paper (AudioGen): https://arxiv.org/abs/2209.15352
- HuggingFace: https://huggingface.co/facebook/musicgen-small