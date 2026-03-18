# Replicate — AI Image Generation

## Доступ
- Token: `REPLICATE_API_TOKEN` в `~/.openclaw/secrets.env`
- Библиотека: `python3 -c "import replicate"` (установлена system-wide)

## Модели

### FLUX.1-dev (`black-forest-labs/flux-dev`)
Лучшая для продуктовых рендеров, техвизуализаций, концепт-арта.
```python
import replicate, os, urllib.request

output = replicate.run(
    "black-forest-labs/flux-dev",
    input={
        "prompt": "...",
        "num_outputs": 1,
        "aspect_ratio": "3:4",   # "1:1", "16:9", "3:4", "4:3" и т.д.
        "output_format": "jpg",
        "output_quality": 90,
        "num_inference_steps": 28,
        "guidance": 3.5,
    }
)

for item in output:
    urllib.request.urlretrieve(str(item), "/path/to/output.jpg")
    break
```

### Другие модели (не тестировались)
- `black-forest-labs/flux-schnell` — быстрее, чуть хуже качество
- `black-forest-labs/flux-pro` — платнее, лучше качество
- `stability-ai/sdxl` — SD XL
- `lucataco/sdxl-controlnet` — SD XL + ControlNet (img2img с контролем)

## Шаблон скрипта
`scripts/render_table_column.py` — рабочий пример для рендера механической детали

## Промпт-паттерны
- Продуктовый рендер: `"Professional product photography, white studio background, soft diffused lighting, 8k, photorealistic"`
- Технический: `"cross-section cutaway view, technical illustration, industrial aesthetic"`
- Интерьер: `"interior design render, Unreal Engine 5, photorealistic, natural lighting"`

## Первый тест (2026-03-18)
Рендер телескопической колонки DIY стола (80/60/40мм квадратные трубы, шпиндель, BLDC мотор) — результат отличный с первой попытки.
