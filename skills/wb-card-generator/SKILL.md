---
name: wb-card-generator
description: Generate product listing cards for Wildberries (WB) and other marketplaces. Use when asked to create, generate, or design a product card/banner for WB, Ozon, or any marketplace. Takes a product photo, generates a styled scene via AI (bria/generate-background on Replicate), then overlays text/branding via HTML+Playwright. Triggers on "карточка товара", "сделай карточку", "wb card", "marketplace card", "product card".
---

# WB Card Generator

## Pipeline (строго в этом порядке)

1. **Анализ фото** — смотришь на исходник: форма товара, ориентация, где визуальный центр
2. **AI фон** — `bria/generate-background` на Replicate: промпт с указанием где товар и где чистое место под текст
3. **Анализ результата** — через `image()` tool смотришь куда встал товар, сколько чистого места
4. **HTML оверлей** — строишь текст/бренд поверх, не перекрывая товар
5. **Рендер** — Playwright chromium → JPEG 95

## Ключевые правила

- **Никакого PIL/rembg** — товар должен органично смотреться в сцене, только AI
- **Только Replicate** — других источников генерации нет
- **Смотреть на фото перед промптом** — понять форму и ориентацию товара
- **Анализировать AI результат** — перед вёрсткой HTML проверить через image() где товар
- Текст всегда LEFT, товар всегда RIGHT (если не оговорено иное)

## Шаг 2: bria/generate-background

```python
import replicate, base64, subprocess, os

token = subprocess.run(["bash","-c","source ~/.openclaw/secrets.env && echo $REPLICATE_API_TOKEN"],
    capture_output=True, text=True).stdout.strip()
os.environ["REPLICATE_API_TOKEN"] = token

with open("/path/to/product.jpg", "rb") as f:
    img_b64 = "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()

output = replicate.run(
    "bria/generate-background",
    input={
        "image": img_b64,
        "bg_prompt": "<тематическая сцена>. Toy/product is on the RIGHT side. LEFT half is clean bright open pastel space for text overlay. Professional product photography.",
        "refine_prompt": False,
        "original_quality": True,
    }
)
url = str(output[0]) if isinstance(output, list) else str(output)
```

**Примеры bg_prompt по категории:**
- Детские игрушки: `Soft spring nursery scene, warm bokeh flowers, cozy baby room. Product on RIGHT, left half clean cream space.`
- Одежда: `Modern minimal studio, soft shadows, neutral backdrop. Product on RIGHT, left half clean white space.`
- Косметика: `Elegant marble surface, soft light, botanical elements. Product on RIGHT, left half clean space.`

## Шаг 4: HTML шаблон

**Ключевые правила вёрстки (проверено):**
- Фон — `<img>` тег absolute 900×900, НЕ `background-image` на body/div (иначе body белый)
- `.content` — `position: absolute`, `background: transparent`, ширина строго до x игрушки минус 40px запас
- Текстовый блок — `.glass-card` с `backdrop-filter: blur(12px)` + `rgba(255,248,235,0.45)` — frosted glass
- Вертикальное центрирование — `margin-top: auto; margin-bottom: auto;` на `.text-block`
- НЕ использовать gradient overlay на всю левую половину — перекрывает фон

```html
<!-- Фон -->
<img class="bg-img" src="file:///tmp/result.jpg">

<!-- Контент -->
<div class="content"> <!-- position:absolute, transparent, width = x_toy - 40px -->
  <div class="brand">BRAND</div>
  <div class="age-badge">0+</div>
  <div class="text-block"> <!-- margin-top:auto; margin-bottom:auto -->
    <div class="glass-card"> <!-- backdrop-filter:blur(12px), rgba(255,248,235,0.45) -->
      ...текст...
    </div>
  </div>
</div>
```

Шрифт: Nunito через Google Fonts CDN.
Размер canvas: 900×900px.
Формат: JPEG quality=95.

## Шаг 5: Playwright рендер

```python
from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 900, "height": 900})
    page.goto("file:///tmp/card.html")
    page.wait_for_load_state("networkidle")
    time.sleep(1.5)
    page.screenshot(path="/path/to/output.jpg",
        clip={"x":0,"y":0,"width":900,"height":900},
        type="jpeg", quality=95)
    browser.close()
```

## Референсы

- Детальные примеры промптов: `references/prompts.md`
- HTML шаблоны по категориям: `references/templates.md`
