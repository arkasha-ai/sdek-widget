# Исследование моделей генерации изображений на Replicate

**Дата:** 2026-03-21  
**Источники:** Replicate API, pricepertoken.com, teamday.ai, replicate.com/pricing

---

## Ключевые находки

### Ландшафт 2026 года

Рынок генерации изображений значительно изменился к марту 2026:

1. **FLUX 2.x семейство** (Black Forest Labs) — новое поколение доминирует в фотореализме
2. **Google** вышла с тремя линейками: Imagen 4, Nano Banana (Gemini), каждая с fast/ultra вариантами
3. **Ideogram v3** — лидер в типографике с тремя тирами (Turbo/Balanced/Quality)
4. **Recraft V4** — выделилась как дизайн-first модель + единственный нативный SVG генератор
5. **OpenAI GPT Image 1.5** — лучший prompt following, но нужен свой API key
6. **ByteDance Seedream 4.5/5** — сильный конкурент с кинематографической эстетикой

### Что рекомендует сам Replicate (из их коллекции)

- **Best overall:** GPT Image 1.5 + Nano Banana Pro
- **Photorealism:** FLUX 2 Max → FLUX 2 Pro → Seedream 4/4.5
- **Typography:** FLUX 2 Flex → Ideogram v3 → Recraft V4
- **Vector/SVG:** Recraft V4 SVG (единственная!)
- **Speed/Cost:** Imagen 4 Fast, FLUX Schnell, Ideogram v3 Turbo

---

## Топ-25 моделей по run_count на Replicate

| # | Модель | Run Count | ~Цена |
|---|--------|-----------|-------|
| 1 | SDXL Lightning 4-step | 1.03B | $0.002 |
| 2 | FLUX Schnell | 635M | $0.003 |
| 3 | SDXL | 84M | $0.005 |
| 4 | FLUX Kontext Pro | 47M | $0.04 |
| 5 | FLUX Dev | 43M | $0.025 |
| 6 | FLUX 1.1 Pro Ultra | 20M | $0.06 |
| 7 | Nano Banana Pro | 18M | $0.08 |
| 8 | FLUX Pro | 14M | $0.05 |
| 9 | Ideogram v3 Turbo | 8.3M | $0.03 |
| 10 | Recraft V3 | 8.1M | $0.04 |
| 11 | Imagen 4 | 7.9M | $0.04 |
| 12 | GPT Image 1.5 | 5.9M | $0.04-0.12 |
| 13 | Proteus v0.3 (anime) | 5.5M | $0.005 |
| 14 | Seedream 4.5 | 5.1M | $0.04 |
| 15 | Imagen 4 Fast | 4.8M | $0.02 |

---

## Ценовые категории

### Бюджетные (< $0.01)
- **SDXL Lightning:** $0.002 — массовая генерация, прототипы
- **FLUX Schnell:** $0.003 — быстрая, хорошее качество
- **SDXL:** $0.005 — LoRA, img2img, inpainting
- **Proteus v0.3:** $0.005 — аниме

### Средние ($0.01 - $0.04)
- **SD 3.5 Turbo:** $0.015
- **Qwen Image:** $0.02 — отличный текст, LoRA, img2img (ЛУЧШЕЕ VALUE!)
- **Imagen 4 Fast:** $0.02
- **FLUX Dev:** $0.025
- **Ideogram v3 Turbo:** $0.03
- **SD 3.5 Large:** $0.035
- **Recraft V3/V4:** $0.04
- **Imagen 4:** $0.04
- **Seedream 4.5:** $0.04
- **Luma Photon:** $0.04
- **Kontext Pro:** $0.04

### Премиум ($0.04+)
- **FLUX Pro:** $0.05
- **FLUX 2 Pro:** $0.055
- **FLUX 2 Flex:** $0.055
- **FLUX 1.1 Pro Ultra:** $0.06
- **FLUX 2 Max:** $0.08
- **Nano Banana Pro:** $0.08
- **GPT Image 1.5:** $0.04-0.12
- **Ideogram v3 Quality:** $0.09
- **Recraft V4 SVG:** $0.08

---

## Анализ по задачам

### Для универсального AgentSkill рекомендую включить:

1. **FLUX Schnell** — дефолт для быстрой генерации ($0.003)
2. **Qwen Image** — дефолт когда нужен текст в изображении ($0.02)
3. **FLUX Dev** — баланс качества и цены ($0.025)
4. **Ideogram v3 Turbo** — дизайн/типографика ($0.03)
5. **FLUX 2 Pro** — максимальное качество ($0.055)
6. **Recraft V4** — брендинг/дизайн ($0.04)
7. **SDXL** — бюджетная с LoRA/inpainting ($0.005)
8. **FLUX Kontext Pro** — редактирование ($0.04)

### Для автовыбора модели по задаче:

```
"быстро/прототип" → FLUX Schnell ($0.003)
"текст/надпись/постер" → Qwen Image ($0.02) или Ideogram v3 Turbo ($0.03)
"фото/реализм" → FLUX Dev ($0.025) или FLUX 2 Pro ($0.055)
"дизайн/бренд/лого" → Recraft V4 ($0.04) или Recraft V4 SVG ($0.08)
"редактирование" → FLUX Kontext Pro ($0.04)
"аниме" → Proteus v0.3 ($0.005) или Ideogram v3 Turbo (style=Anime)
"бюджет/массово" → SDXL Lightning ($0.002) или FLUX Schnell ($0.003)
"максимум качества" → FLUX 2 Max ($0.08)
```

---

## Технические заметки

### API формат на Replicate

Все модели вызываются через:
```bash
curl -s -X POST "https://api.replicate.com/v1/models/{owner}/{name}/predictions" \
  -H "Authorization: Bearer $REPLICATE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"input": {"prompt": "...", "aspect_ratio": "1:1"}}'
```

Или через predictions с version hash:
```bash
curl -s -X POST "https://api.replicate.com/v1/predictions" \
  -H "Authorization: Bearer $REPLICATE_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"version": "hash...", "input": {"prompt": "..."}}'
```

### Общие параметры для большинства моделей:
- `prompt` (обязательный)
- `aspect_ratio` — "1:1", "16:9", "9:16", "4:3", "3:4"
- `output_format` — "webp", "jpg", "png"
- `seed` — для воспроизводимости

### Модели с LoRA:
- SDXL (replicate_weights)
- Qwen Image (lora_weights, extra_lora_weights)
- FLUX Dev LoRA (специальная версия: black-forest-labs/flux-dev-lora)

### Модели с img2img:
- FLUX Dev (image + prompt_strength)
- Qwen Image (image + strength)
- SDXL (image + prompt_strength)
- SD 3.5 (image + prompt_strength)
- Ideogram v3 (image param)
- Seedream 4.5 (image_input)
- Proteus v0.3 (image + prompt_strength)

### Модели с inpainting:
- SDXL (mask param)
- Ideogram v3 (mask param)
- Proteus v0.3 (mask param)

---

## Новые тренды 2026

1. **Reference images** — FLUX 2 Pro/Max/Flex позволяют подавать до 8-10 reference images для consistency
2. **Reasoning-guided generation** — Nano Banana Pro использует Gemini для reasoning перед генерацией
3. **SVG output** — Recraft V4 SVG единственная модель с нативным вектором
4. **Multi-turn editing** — Nano Banana Pro поддерживает conversational editing
5. **Style presets** — Ideogram v3 имеет 4.3 миллиарда style presets
6. **Character consistency** — FLUX 2, Luma Photon, MiniMax поддерживают character reference
