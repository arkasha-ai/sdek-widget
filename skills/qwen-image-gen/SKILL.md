---
name: qwen-image-gen
description: >
  Multi-model image generator via Replicate API. 13 models: FLUX, Qwen, Ideogram, Google Imagen/Gemini,
  SDXL, Recraft, Proteus. Auto-selects best model by task. Supports text-to-image, img2img, text rendering.
  Use when user asks to draw, generate, create, or edit an image.
  Triggers: "нарисуй", "сгенерируй", "generate image", "draw", "create image", "edit image".
---

# Image Generator (Multi-Model)

13 models via Replicate API with automatic model selection.

## Quick Start

```bash
source ~/.openclaw/secrets.env

# Auto-select model based on prompt
python3 {baseDir}/scripts/generate.py generate "a sunset over mountains"

# Specific model
python3 {baseDir}/scripts/generate.py generate "logo with text BRAND" --model qwen-image

# List all models
python3 {baseDir}/scripts/generate.py list

# Get recommendation
python3 {baseDir}/scripts/generate.py recommend "need a fast prototype sketch"
```

## Requirements

- `REPLICATE_API_TOKEN` in `~/.openclaw/secrets.env`
- `curl` (stdlib)
- Python 3 (stdlib only, no pip)

## Commands

### `generate "prompt" [options]`

| Flag | Default | Description |
|------|---------|-------------|
| `--model`, `-m` | `auto` | Model ID or `auto` for smart selection |
| `--negative` | — | Negative prompt (models that support it) |
| `--aspect-ratio`, `-r` | `1:1` | Aspect ratio |
| `--steps`, `-s` | model default | Inference steps |
| `--guidance`, `-g` | model default | Guidance scale |
| `--output`, `-o` | `drafts/<model>_<ts>.webp` | Output file path |
| `--format` | `webp` | `webp`/`png`/`jpg` |
| `--quality` | model default | Output quality 0-100 |
| `--image` | — | Input image for img2img (URL or local path) |
| `--strength` | model default | img2img strength 0-1 |
| `--seed` | random | Fixed seed |
| `--no-safety` | off | Disable safety checker |
| `--wait` | 180 | Max wait seconds |

### `list [--category CAT]`

Categories: `fast`, `photo`, `anime`, `text`, `edit`, `universal`

### `search "query"` — find models by keyword
### `info "model-id"` — detailed model info
### `recommend "task"` — get model recommendation with alternatives

## Models

| ID | Name | Cost | Speed | Best For |
|----|------|------|-------|----------|
| `flux-schnell` | FLUX.1 Schnell | $0.003 | ~2s | Fast prototypes, cheap batch |
| `flux-dev` | FLUX.1 Dev | $0.025 | ~10s | Quality photos, img2img |
| `flux-pro` | FLUX.1 Pro | $0.050 | ~12s | Premium quality |
| `flux-1.1-pro-ultra` | FLUX 1.1 Pro Ultra | $0.060 | ~15s | 4MP ultra-realism |
| `qwen-image` | Qwen Image | $0.020 | ~15s | **Best text rendering**, LoRA |
| `ideogram-v3-turbo` | Ideogram v3 Turbo | $0.030 | ~5s | Fast design + text |
| `imagen-4-fast` | Google Imagen 4 Fast | $0.020 | ~5s | Fast Google quality |
| `nano-banana-pro` | Gemini Image (Nano Banana) | $0.080 | ~8s | All-around best, editing, 4K, reasoning |
| `sdxl` | Stable Diffusion XL | $0.005 | ~8s | Budget, LoRA, inpainting |
| `sdxl-lightning` | SDXL Lightning | $0.002 | ~2s | **Cheapest**, mass generation |
| `flux-kontext-pro` | FLUX Kontext Pro | $0.040 | ~8s | **Image editing** |
| `proteus` | Proteus v0.3 | $0.005 | ~8s | **Anime/illustration** |
| `recraft-v4` | Recraft V4 | $0.040 | ~10s | Professional design, branding |

## Auto-Select Logic (`--model auto`)

| Keywords in prompt | Selected model |
|-------------------|----------------|
| текст, text, логотип, logo, надпись, sign | `qwen-image` |
| быстро, fast, quick, прото, draft | `flux-schnell` |
| фото, photo, реализм, portrait, пейзаж | `flux-dev` |
| аниме, anime, manga, мультик, illustration | `proteus` |
| редактир, edit, измени, замени | `flux-kontext-pro` |
| дизайн, design, бренд, brand, постер | `recraft-v4` |
| google, gemini, инфографика, reasoning | `nano-banana-pro` |
| _(default)_ | `flux-schnell` |

## Examples

```bash
# Logo with text
python3 {baseDir}/scripts/generate.py generate \
  "minimalist logo with text ZNAEM AI, blue palette" \
  --model qwen-image --aspect-ratio 1:1

# Fast prototype
python3 {baseDir}/scripts/generate.py generate \
  "cyberpunk cityscape at night" --model flux-schnell

# High quality photo
python3 {baseDir}/scripts/generate.py generate \
  "professional headshot, studio lighting" \
  --model flux-dev --steps 40 --guidance 4

# Anime character
python3 {baseDir}/scripts/generate.py generate \
  "anime girl with sword, cherry blossoms" \
  --model proteus --aspect-ratio 3:4

# Edit existing image
python3 {baseDir}/scripts/generate.py generate \
  "make the background a sunset" \
  --model flux-kontext-pro --image /path/to/photo.jpg

# Google Gemini quality (best all-around)
python3 {baseDir}/scripts/generate.py generate \
  "infographic about climate change with data charts" \
  --model nano-banana-pro --format png

# Cheapest option ($0.002)
python3 {baseDir}/scripts/generate.py generate \
  "abstract background pattern" --model sdxl-lightning
```

## Workflow for Agent

1. Source secrets: `source ~/.openclaw/secrets.env`
2. Run generate — script polls until done, prints file path to stdout
3. Send to user: `message(action=send, media=<path>)` or `message(action=send, filePath=<path>)`

## Notes

- Script uses `curl` subprocess (Python urllib blocked by proxy)
- Polling interval: 1.5s, default max wait: 180s
- Output defaults to `~/.openclaw/workspace/drafts/`
- stdout = file path only (for piping); all status goes to stderr
- nano-banana-pro only supports jpg/png (no webp) — auto-fallback to jpg
