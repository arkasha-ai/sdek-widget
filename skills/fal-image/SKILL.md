---
name: fal-image
description: Generate images via fal.ai API. Supports Nano Banana Pro, Nano Banana 2, FLUX Kontext (img2img), and other fal.ai models. Use for product card generation, lifestyle scenes, image editing. No rate limits on RPM — only concurrency. Auth via FAL_API_KEY in secrets.env.
---

# fal.ai Image Generation Skill

Generate and edit images via fal.ai async queue.

## Setup

```bash
source ~/.openclaw/secrets.env
# FAL_API_KEY must be set
```

## Quick Usage

```bash
# Text-to-image (Nano Banana 2 — fastest, 4K)
python3 ~/.openclaw/workspace/skills/fal-image/generate.py \
  --model nano-banana-2 \
  --prompt "Product on marble surface, studio lighting" \
  --output /tmp/result.jpg

# Image-to-image (Nano Banana Pro — best quality, $0.15)
python3 ~/.openclaw/workspace/skills/fal-image/generate.py \
  --model nano-banana-pro \
  --image /path/to/product.jpg \
  --prompt "Place this product in a kitchen scene" \
  --output /tmp/result.jpg

# FLUX Kontext img2img — best for preserving product details
python3 ~/.openclaw/workspace/skills/fal-image/generate.py \
  --model flux-kontext \
  --image /path/to/product.jpg \
  --prompt "Change background to marble surface" \
  --output /tmp/result.jpg

# Inpainting — replace masked area
python3 ~/.openclaw/workspace/skills/fal-image/generate.py \
  --model flux-fill \
  --image /path/to/image.jpg \
  --mask /path/to/mask.png \
  --prompt "Wooden kitchen table with fresh herbs" \
  --output /tmp/result.jpg
```

## Models

| Alias | fal.ai endpoint | Price | Best for |
|-------|----------------|-------|----------|
| `nano-banana-2` | fal-ai/nano-banana-2 | ~$0.03 | Fast t2i, text rendering |
| `flux-kontext` | fal-ai/flux-kontext/dev | ~$0.04 | Preserve product details (img2img) |
| `flux-fill` | fal-ai/flux-pro/v1/fill | ~$0.05 | Inpainting (замена фона) |
| `flux-schnell` | fal-ai/flux/schnell | $0.003 | Fastest t2i |

## Nano Banana Pro на fal.ai — правильный endpoint

**❌ НЕ использовать:** `fal-ai/nano-banana-pro` (text-to-image, нет image_input, товар меняется)

**✅ ИСПОЛЬЗОВАТЬ:** `fal-ai/nano-banana-pro/edit` — режим редактирования с `image_urls`

```python
payload = {
    "prompt": "...",
    "image_urls": [img_b64_or_url],   # ← image_urls, не image_input!
    "aspect_ratio": "4:5",
    "resolution": "2K",
    "output_format": "jpeg",
    "safety_tolerance": "4",
}
# Sync вызов:
# POST https://fal.run/fal-ai/nano-banana-pro/edit
```

Этот endpoint сохраняет товар точно — аналог `image_input` на Replicate.

## Aspect Ratios
`1:1`, `4:5` (WB/Ozon standard), `16:9`, `9:16`, `3:4`

## Промпт для карточек товаров (ОБЯЗАТЕЛЬНО)

### Префикс промпта
Всегда начинать промпт с: `ultra realistic, photorealistic, 8k, professional product photography,`

Пример: `ultra realistic, photorealistic, professional product photography, Place this jacket in an urban scene...`

## Негативный промпт для карточек товаров (ОБЯЗАТЕЛЬНО)

Всегда добавлять при генерации карточек товаров чтобы модель не придумывала лишнее:

```
added logos, added text, added patches, added badges, added labels, added brand names, 
added inscriptions, added prints, added emblems, added flags, extra decorations, 
invented details, fake patches, fake text, fake logos, watermarks
```

Использование: `--negative "added logos, added text, added patches, added badges, added brand names, added inscriptions, added prints, invented details, fake patches, fake logos"`

## Auth
`FAL_API_KEY` in `~/.openclaw/secrets.env`

## Структура промпта для карточек товаров (проверено, работает)

Основана на официальном гайде Google для Nano Banana Pro.

### Формула

```
Place [точное описание товара с деталями] on/in [описание сцены/фона].
[Composition: medium shot, center-framed / etc].
[Style: professional fashion editorial photography, ultra realistic, photorealistic].
```

### Ключевые правила

1. **Начинать с глагола-действия:** `Place`, `Show`, `Create`, `Generate`
2. **Описывать товар конкретно:** цвет, материал, все детали (молния, нашивки, карманы, манжеты)
3. **Позитивное описание:** "gold zipper" вместо "keep the zipper"
4. **Структура:** Subject → Action → Location → Composition → Style
5. **НЕ писать** "keep exactly as shown" — модель игнорирует

### Пример (куртка на модели)

```
Place a beige MA-1 bomber jacket with black ribbed cuffs, black collar,
gold front zipper, left-sleeve utility pocket with zipper, and round embroidered patch on left arm
on a confident male model aged 25-30.
Urban street background with soft bokeh, natural daylight.
Medium shot, center-framed.
Professional fashion editorial photography, ultra realistic, photorealistic.
```

### Негативный промпт (всегда добавлять)

```
added logos, added text, added patches, added badges, added brand names, 
invented details, fake patches, fake logos, watermarks
```
