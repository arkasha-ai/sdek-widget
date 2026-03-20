from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

doc = Document()

section = doc.sections[0]
section.page_width = Inches(8.5)
section.page_height = Inches(11)
section.left_margin = Cm(2.5)
section.right_margin = Cm(2.5)
section.top_margin = Cm(2.5)
section.bottom_margin = Cm(2.5)

# ─── helpers ──────────────────────────────────────────────

def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), hex_color)
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:val'), 'clear')
    tcPr.append(shd)

def add_hyperlink(para, url, text, font_size=10, color=(17, 85, 204), bold=False):
    """Insert a real clickable hyperlink into an existing paragraph."""
    part = para.part
    r_id = part.relate_to(
        url,
        'http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink',
        is_external=True
    )
    hl = OxmlElement('w:hyperlink')
    hl.set(qn('r:id'), r_id)
    hl.set(qn('w:history'), '1')

    run_el = OxmlElement('w:r')
    rPr = OxmlElement('w:rPr')

    col = OxmlElement('w:color')
    col.set(qn('w:val'), '%02x%02x%02x' % tuple(color))
    rPr.append(col)

    u = OxmlElement('w:u')
    u.set(qn('w:val'), 'single')
    rPr.append(u)

    sz = OxmlElement('w:sz')
    sz.set(qn('w:val'), str(font_size * 2))
    rPr.append(sz)

    if bold:
        b = OxmlElement('w:b')
        rPr.append(b)

    run_el.append(rPr)
    t = OxmlElement('w:t')
    t.text = text
    run_el.append(t)
    hl.append(run_el)
    para._p.append(hl)
    return hl

def add_heading(text, level=1, emoji=""):
    colors = {1: (30, 30, 30), 2: (40, 80, 160), 3: (60, 100, 180)}
    sizes  = {1: 20, 2: 16, 3: 13}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    p.paragraph_format.space_after  = Pt(6)
    run = p.add_run((emoji + " " + text).strip())
    run.font.size = Pt(sizes.get(level, 12))
    run.font.bold = True
    run.font.color.rgb = RGBColor(*colors.get(level, (0,0,0)))
    return p

def add_body(text, bold=False, italic=False, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(text)
    run.font.size  = Pt(11)
    run.font.bold  = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    return p

def add_bullet(text, level=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent   = Cm(0.8 + level * 0.5)
    p.paragraph_format.space_before  = Pt(2)
    p.paragraph_format.space_after   = Pt(2)
    run = p.add_run("•  " + text)
    run.font.size = Pt(11)
    return p

def add_tip(text, url=None):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    run = p.add_run("📹  ")
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = RGBColor(180, 60, 60)
    if url:
        add_hyperlink(p, url, text, font_size=10, color=(180, 60, 60), bold=True)
    else:
        r2 = p.add_run(text)
        r2.font.size  = Pt(10)
        r2.font.bold  = True
        r2.font.color.rgb = RGBColor(180, 60, 60)

def add_divider():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after  = Pt(8)
    run = p.add_run("─" * 80)
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(200, 200, 200)

def add_tool_table(tools):
    """tools = [(name, url, description, price), ...]"""
    table = doc.add_table(rows=1, cols=3)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    for i, h in enumerate(["Инструмент", "Для чего", "Цена"]):
        hdr[i].text = h
        run = hdr[i].paragraphs[0].runs[0]
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(255, 255, 255)
        shade_cell(hdr[i], '2E5090')
    for name, url, desc, price in tools:
        row = table.add_row().cells
        # col 0: clickable name
        p0 = row[0].paragraphs[0]
        add_hyperlink(p0, url, name, font_size=10, bold=True)
        # col 1
        row[1].text = desc
        row[1].paragraphs[0].runs[0].font.size = Pt(10)
        # col 2
        row[2].text = price
        row[2].paragraphs[0].runs[0].font.size = Pt(10)
    doc.add_paragraph()

def add_videos(items):
    """items = [(label, direct_youtube_url), ...]"""
    for label, url in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent  = Cm(0.5)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run("🎥  ")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(180, 50, 50)
        add_hyperlink(p, url, label, font_size=10, color=(180, 50, 50))

def add_articles(items):
    """items = [(label, url), ...]"""
    for label, url in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent  = Cm(0.5)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after  = Pt(2)
        run = p.add_run("📖  ")
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(50, 130, 50)
        add_hyperlink(p, url, label, font_size=10, color=(50, 130, 50))

def add_task(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.8)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after  = Pt(3)
    run = p.add_run(f"{num}.  {text}")
    run.font.size = Pt(11)
    if "(Продвинутое)" in text:
        run.font.color.rgb = RGBColor(150, 50, 200)

# ──────────────────────────────────────────────────────────
# ОБЛОЖКА
# ──────────────────────────────────────────────────────────
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(30)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("🤖  AI с нуля до агентов")
run.font.size = Pt(28); run.font.bold = True
run.font.color.rgb = RGBColor(30, 80, 180)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run("Практический курс: от первого промпта до собственного AI-агента")
run2.font.size = Pt(14); run2.font.italic = True
run2.font.color.rgb = RGBColor(100, 100, 100)

doc.add_paragraph()
for label, val in [
    ("Для кого:", "Менеджеры, предприниматели, специалисты без технического бэкграунда"),
    ("Результат:", "Уверенно применяете AI в работе, строите автоматизации и агентов"),
    ("Формат:", "Самостоятельное обучение с практическими заданиями"),
    ("Длительность:", "~3 месяца при 30-60 минутах в день"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    r1 = p.add_run(label + "  "); r1.bold = True; r1.font.size = Pt(11)
    r2 = p.add_run(val);          r2.font.size = Pt(11)

add_divider()

# ──────────────────────────────────────────────────────────
# ПЛАН
# ──────────────────────────────────────────────────────────
add_heading("ПЛАН НА 3 МЕСЯЦА", 1, "📅")
pt = doc.add_table(rows=1, cols=3)
pt.style = 'Table Grid'
hdr = pt.rows[0].cells
for i, h in enumerate(["Неделя", "Фокус", "Ежедневно"]):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True
    hdr[i].paragraphs[0].runs[0].font.size = Pt(10)
    hdr[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255,255,255)
    shade_cell(hdr[i], '2E5090')
for week, focus, daily in [
    ("1–2", "Промптинг: ChatGPT, Claude, техники, GPTs", "30 мин"),
    ("3",   "Изображения: Leonardo.ai, Midjourney, DALL-E", "45 мин"),
    ("4–5", "Видео: Kling AI, ElevenLabs, Runway, HeyGen, AI-кино", "45 мин"),
    ("6–8", "Автоматизация: Make, n8n, Telegram-бот с AI", "60 мин"),
    ("9–12","AI-агенты: Dify, Flowise, CrewAI, RAG", "60 мин"),
]:
    row = pt.add_row().cells
    for i, v in enumerate([week, focus, daily]):
        row[i].text = v; row[i].paragraphs[0].runs[0].font.size = Pt(10)
doc.add_paragraph()
add_divider()

# ──────────────────────────────────────────────────────────
# МОДУЛЬ 1 — ПРОМПТИНГ
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("МОДУЛЬ 1  —  Промптинг", 1, "📍")
p = doc.add_paragraph()
p.add_run("⏱ 1-2 недели  |  Сложность: ⭐☆☆☆☆").font.size = Pt(10)
p.runs[0].italic = True; p.runs[0].font.color.rgb = RGBColor(120,120,120)

add_heading("Что это и зачем", 3)
add_body("Промпт — инструкция для нейросети. От промпта зависит 80% качества ответа: одна и та же модель на плохой вопрос даст плохой ответ, а на хорошо сформулированный — отличный.")
add_body("Промптинг — навык, который прокачивается за 1-2 недели и остаётся с вами навсегда. Главное заблуждение: «ChatGPT тупой». На самом деле — просто нужно научиться с ним разговаривать.")

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("ChatGPT",    "https://chat.openai.com",      "Универсальный старт, самый популярный",        "Бесплатно / $20/мес"),
    ("Claude",     "https://claude.ai",             "Длинные тексты, анализ, рассуждения",          "Бесплатно / $20/мес"),
    ("Gemini",     "https://gemini.google.com",     "Работа с файлами, интеграция с Google",        "Бесплатно"),
    ("DeepSeek",   "https://chat.deepseek.com",     "Сильная модель, полностью бесплатно",          "Бесплатно"),
    ("Perplexity", "https://perplexity.ai",         "AI-поиск с источниками и ссылками",            "Бесплатно / $20/мес"),
])

add_heading("Ключевые техники промптинга", 3)
for title, body, example in [
    ("1. Role prompting — задать роль",
     "Дай AI роль перед заданием — кардинально меняет стиль и глубину ответа.",
     "Плохо: «Напиши резюме» | Хорошо: «Ты опытный HR-директор с 15 годами практики. Напиши резюме для PM, который хочет перейти в продуктовую компанию...»"),
    ("2. Chain-of-Thought — пошаговое мышление",
     "Попроси AI думать вслух — повышает качество на сложных задачах.",
     "«Прежде чем ответить, разбери задачу пошагово: определи контекст → выяви проблему → предложи решение»"),
    ("3. Few-shot — примеры",
     "Покажи 2-3 примера того, что хочешь получить. AI подхватит формат и стиль.", ""),
    ("4. Structured output — структурированный вывод",
     "Просишь вернуть результат в таблице, JSON, нумерованном списке.",
     "«Верни ответ в виде таблицы с колонками: Задача / Срок / Ответственный»"),
    ("5. Итерация через диалог",
     "Не пытайся с первого промпта получить идеальный результат. Дорабатывай через диалог.",
     "«Хорошо, теперь сделай это более формально» / «Убери третий пункт и расширь второй»"),
    ("6. Контекст и ограничения",
     "Всегда давай контекст: кто аудитория, формат, ограничения.",
     "Плохо: «Напиши статью про AI» | Хорошо: «Напиши статью 800 слов про AI для предпринимателей без технического образования»"),
]:
    add_body(title, bold=True)
    add_body(body)
    if example:
        add_body(example, italic=True, color=(80,80,80))

add_heading("Интересные нюансы ChatGPT", 3)
add_body("Custom Instructions — настрой ChatGPT под себя", bold=True)
add_body("Settings → Personalization → Custom Instructions. Пишешь один раз кто ты — каждый новый чат уже знает контекст.")
add_body("Память (Memory)", bold=True)
add_body("ChatGPT Plus запоминает между сессиями: «Запомни, что я PM в IT-компании» — и он учитывает это во всех будущих чатах.")
add_body("GPTs — персональные мини-агенты", bold=True)
add_body("В ChatGPT Plus: Explore GPTs — специализированные боты: Canva, Consensus, Code Interpreter. Можно создать своего GPT под любую задачу.")
add_body("Анализ файлов", bold=True)
add_body("ChatGPT Plus читает PDF, Excel, CSV: «Найди в договоре все пункты про штрафные санкции» или «Проанализируй отчёт и выдели ключевые метрики».")
add_body("Голосовой режим", bold=True)
add_body("ChatGPT работает голосом — удобно для брейншторминга во время прогулки. Advanced Voice в Plus-подписке поддерживает живой диалог.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("Как писать промты к ИИ за 14 минут (для начинающих)",        "https://www.youtube.com/watch?v=TabGj7fQCuQ"),
    ("Как писать ИДЕАЛЬНЫЕ промты для ChatGPT? 7 шаблонов",        "https://www.youtube.com/watch?v=uJeltPMBakw"),
    ("Единственный промт ChatGPT который тебе нужен в 2025",       "https://www.youtube.com/watch?v=lp3yjs1Fgy8"),
    ("Как создать СВОЙ ChatGPT — полный обзор GPT Builder",        "https://www.youtube.com/watch?v=TLVwpRrAJqU"),
    ("Полный апдейт 2025: какой ChatGPT выбрать, функции, фишки",  "https://www.youtube.com/watch?v=mcHUW4_bAaE"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Promptingguide.ai на русском — лучший бесплатный гайд",  "https://www.promptingguide.ai/ru"),
    ("Habr: Искусство промптинга",                              "https://habr.com/ru/search/?q=промптинг"),
    ("VC.ru: ChatGPT для бизнеса",                             "https://vc.ru/search?query=ChatGPT+промптинг"),
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в ChatGPT, настрой Custom Instructions (кто ты и как хочешь ответы)")
add_task(2, "Напиши промпт который генерирует резюме под конкретную вакансию")
add_task(3, "Создай промпт для анализа документа — выделять ключевые риски")
add_task(4, "Найди 3 полезных GPT в Explore GPTs для своей работы")
add_task(5, "(Продвинутое) Создай собственного GPT под конкретную задачу")

add_divider()

# ──────────────────────────────────────────────────────────
# МОДУЛЬ 2 — ИЗОБРАЖЕНИЯ
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("МОДУЛЬ 2  —  Генерация изображений", 1, "🎨")
p = doc.add_paragraph()
p.add_run("⏱ 1 неделя  |  Сложность: ⭐⭐☆☆☆").font.size = Pt(10)
p.runs[0].italic = True; p.runs[0].font.color.rgb = RGBColor(120,120,120)

add_heading("Что это и зачем", 3)
add_body("Ты описываешь картинку текстом — нейросеть генерирует её за секунды. То, что раньше стоило $200 у дизайнера, сейчас делается за 5 минут. Используется для: маркетинга, презентаций, аватаров, рекламных баннеров, иллюстраций.")

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("Midjourney",    "https://midjourney.com",         "Лучшее художественное качество",               "от $10/мес"),
    ("DALL-E 3",      "https://chat.openai.com",        "Встроен в ChatGPT Plus, удобно",               "Входит в $20/мес"),
    ("Leonardo.ai",   "https://leonardo.ai",            "Много бесплатных кредитов, FLUX.1",            "Бесплатно / $12/мес"),
    ("Adobe Firefly", "https://firefly.adobe.com",      "Безопасно для коммерческого использования",    "Бесплатно / от $5/мес"),
    ("Kandinsky",     "https://fusionbrain.ai",         "Российский сервис, полностью бесплатно",       "Бесплатно"),
    ("Шедеврум",      "https://shedevrum.ai",           "Яндекс, русскоязычный интерфейс",              "Бесплатно"),
])

add_heading("Ключевые техники", 3)
add_body("Структура промпта: [Объект/сцена] + [стиль] + [свет/атмосфера] + [детали] + [формат]", bold=True)
add_body("Пример: «Деловой мужчина 35 лет, кофе на фоне панорамного окна офиса, фотореализм, мягкий утренний свет, LinkedIn аватар, портретная ориентация»", italic=True, color=(80,80,80))

add_body("Ключевые слова стилей:", bold=True)
for s in ["Реализм: photorealistic, 8K, DSLR, sharp focus",
          "Минимализм: minimalist, flat design, clean lines, white background",
          "Кинематограф: cinematic, movie still, film grain, dramatic lighting",
          "Бизнес: professional, corporate, clean, modern"]:
    add_bullet(s)

add_body("Negative prompts, Reference image, Inpainting:", bold=True)
for s in ["Negative: убери лишнее — Midjourney: --no text, watermark, blurry",
          "Reference: загрузи фото как пример стиля",
          "Inpainting: выдели область и измени только её, остальное не трогает"]:
    add_bullet(s)

add_heading("Интересные нюансы", 3)
add_body("FLUX.1 — новый лидер реализма (2024)", bold=True)
add_body("FLUX.1 от Black Forest Labs обгоняет Midjourney в фотореализме. Доступен в Leonardo.ai бесплатно.")
add_body("Lora-модели в Leonardo.ai", bold=True)
add_body("Специализированные насадки на модель для конкретных стилей (аниме, архитектура, реализм). Выбираешь — качество резко растёт.")
add_body("Консистентность персонажа", bold=True)
add_body("Midjourney --cref или Leonardo Character Reference — закрепи внешность персонажа между генерациями.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("Midjourney — полный курс с 0 до профи за 30 минут",    "https://www.youtube.com/watch?v=_K6FbNdrLxw"),
    ("Как пользоваться Midjourney в 2025 году",              "https://www.youtube.com/watch?v=1h_PQndG-A0"),
    ("LEONARDO AI — структура промта, генерация изображений", "https://www.youtube.com/watch?v=VNeWIlI11H4"),
    ("Leonardo AI — основы, регистрация, первая генерация",  "https://www.youtube.com/watch?v=Li4ovXtiaUk"),
    ("Что такое Leonardo.Ai — генерация изображений",        "https://www.youtube.com/watch?v=3lnO35ZqHIs"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Habr: Сравнение AI-генераторов 2025",  "https://habr.com/ru/search/?q=генерация+изображений+AI+2025"),
    ("VC.ru: AI для дизайна",                "https://vc.ru/search?query=AI+дизайн+генерация"),
    ("Civitai.com — тысячи промптов и моделей", "https://civitai.com"),
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в Leonardo.ai (бесплатно), сгенерируй 10 вариантов")
add_task(2, "Создай деловой аватар для LinkedIn или Telegram")
add_task(3, "Сгенерируй 5 вариантов баннера для своего проекта")
add_task(4, "Один запрос в DALL-E, Leonardo и Kandinsky — сравни результат")
add_task(5, "(Продвинутое) Midjourney: character reference для консистентного персонажа")

add_divider()

# ──────────────────────────────────────────────────────────
# МОДУЛЬ 3 — ВИДЕО И ГОЛОС
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("МОДУЛЬ 3  —  Генерация видео и голоса", 1, "🎬")
p = doc.add_paragraph()
p.add_run("⏱ 2-3 недели  |  Сложность: ⭐⭐⭐☆☆").font.size = Pt(10)
p.runs[0].italic = True; p.runs[0].font.color.rgb = RGBColor(120,120,120)

add_heading("Что это и зачем", 3)
add_body("Самый быстро развивающийся сегмент AI. Год назад AI-видео было игрушкой — сейчас серьёзный рабочий инструмент. Можно создавать рекламу, обучающий контент, дубляж на 40+ языков, кино-ролики и длинные YouTube-видео — без оператора, студии и даже без своего лица в кадре.")

# --- 3.1 Базовые инструменты ---
add_heading("3.1  Базовые инструменты видео", 3)
add_tool_table([
    ("Runway Gen-3",      "https://runwayml.com",    "Text/Image-to-Video, топ кинематографическое качество",   "$15/мес"),
    ("Kling AI",          "https://klingai.com",     "Сильный конкурент Runway, есть бесплатный план",          "Бесплатно / $10/мес"),
    ("Sora",              "https://sora.com",        "Видео от OpenAI, длинные ролики до 20 сек",               "$20/мес (ChatGPT Plus)"),
    ("HeyGen",            "https://heygen.com",      "Видео-аватары, перевод видео с дубляжом",                 "$29/мес"),
    ("ElevenLabs",        "https://elevenlabs.io",   "Клонирование голоса, Text-to-Speech",                     "Бесплатно / $5/мес"),
    ("Luma Dream Machine","https://lumalabs.ai",     "Видео из фото, плавная анимация",                         "Бесплатно (лимиты)"),
    ("CapCut AI",         "https://capcut.com",      "Монтаж + AI субтитры, удаление фона, эффекты",            "Бесплатно"),
    ("Descript",          "https://descript.com",    "Монтаж видео через редактирование текста",                "Бесплатно / $12/мес"),
])

add_heading("Ключевые техники для коротких видео", 3)
add_body("Структура промпта: [Что происходит] + [обстановка] + [стиль] + [движение камеры] + [атмосфера]", bold=True)
add_body("Пример: «Деловая женщина идёт по ночному городу под дождём, неоновые огни, замедленная съёмка, кинематографический стиль, 4K»", italic=True, color=(80,80,80))
add_body("Движение камеры:", bold=True)
for s in ["slow zoom in — медленный наезд (напряжение)",
          "dolly shot — камера движется вдоль сцены",
          "panning left/right — панорамирование",
          "bird's eye view — вид сверху",
          "close-up — крупный план"]:
    add_bullet(s)

add_heading("Интересные нюансы", 3)
add_body("Аватары HeyGen — цифровой двойник", bold=True)
add_body("Записываешь 2-5 минут видео с нейтральным лицом → HeyGen обучает модель → вводишь текст → получаешь видео где «ты» говоришь его. Для корпоративных видео, курсов, персонализированных сообщений.")
add_tip("Как создать аватар HeyGen пошагово — смотри видео:", "https://www.youtube.com/watch?v=CqZ4i_7Auo4")
add_body("Voice Cloning в ElevenLabs:", bold=True)
add_body("1. Записываешь 1-2 минуты голоса → 2. ElevenLabs клонирует → 3. Вводишь текст → 4. Получаешь озвучку своим голосом. Используй для подкастов, обучающих видео, рекламы.")
add_body("Video Translation — дубляж без студии:", bold=True)
add_body("HeyGen и ElevenLabs переводят видео на 40+ языков с клонированным голосом и синхронизацией губ.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("Новый Runway GEN-4 — революционный генератор видео",     "https://www.youtube.com/watch?v=YyTdmWOEiZM"),
    ("Runway — создание видео с помощью AI (обзор)",           "https://www.youtube.com/watch?v=GUXWB0Mqigw"),
    ("Полный гайд по ElevenLabs 2025 — озвучка и клонирование","https://www.youtube.com/watch?v=NmFSkjSh23w"),
    ("Клонирую свой ГОЛОС через ИИ ElevenLabs — пошаговый гайд","https://www.youtube.com/watch?v=67Lw5jCc0Ck"),
    ("Генерация видео аватара в HeyGen (бесплатно в 2025)",    "https://www.youtube.com/watch?v=tHWSnrMXVQg"),
    ("Создаём цифрового аватара в HeyGen за 5 минут",          "https://www.youtube.com/watch?v=sp6N1pMczl8"),
    ("Kling 3.0 — полный обзор возможностей нейросети",        "https://www.youtube.com/watch?v=lBe0-UpArZk"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Habr: AI-видеогенерация 2025",            "https://habr.com/ru/search/?q=генерация+видео+AI"),
    ("VC.ru: Как бизнес использует AI-видео",   "https://vc.ru/search?query=AI+видео+бизнес"),
])

add_heading("Практические задания (базовый уровень)", 3)
add_task(1, "Создай 15-секундный ролик через Kling AI (бесплатно) — текст или фото в видео")
add_task(2, "Зарегистрируйся в ElevenLabs, озвучь любой текст синтезированным голосом")
add_task(3, "Запиши 1 минуту своего голоса → создай клон → озвучь им новый текст")
add_task(4, "(Продвинутое) Создай аватар в HeyGen — обращение без участия камеры")
add_task(5, "(Продвинутое) Попробуй Descript: загрузи видео и отредактируй через текст")

add_divider()

# --- 3.2 AI-кино ---
add_heading("3.2  AI-кино — создай настоящий фильм", 3)

add_body("Что это такое", bold=True)
add_body("AI-кино — это короткометражки (3-15 минут), снятые без актёров, камер и декораций. Ты пишешь сценарий, генерируешь изображения для раскадровки, создаёшь видеоклипы через Runway/Kling, озвучиваешь через ElevenLabs и склеиваешь в CapCut или Descript. Уже сейчас люди снимают полноценные короткометражки и выкладывают на YouTube и Vimeo.")

add_heading("Инструменты для AI-кино", 3)
add_tool_table([
    ("Runway Gen-3 Alpha", "https://runwayml.com",   "Кинематографические клипы 4-16 сек, лучшее качество",           "$15/мес"),
    ("Kling AI",           "https://klingai.com",    "Клипы до 10 сек, реалистичные движения",                        "Бесплатно / $10/мес"),
    ("MidJourney",         "https://midjourney.com", "Раскадровка (storyboard) и концепт-арт сцен",                   "$10/мес"),
    ("ElevenLabs",         "https://elevenlabs.io",  "Голоса всех персонажей, озвучка",                               "Бесплатно / $5/мес"),
    ("Suno / Udio",        "https://suno.com",       "Генерация саундтрека и музыки к сцене",                         "Бесплатно / $8/мес"),
    ("CapCut",             "https://capcut.com",     "Склейка клипов, субтитры, переходы, финальный монтаж",          "Бесплатно"),
    ("Descript",           "https://descript.com",   "Монтаж через текст, удаление пауз и слов-паразитов",            "Бесплатно / $12/мес"),
    ("Pika Labs",          "https://pika.art",       "Видео из изображений, стилизация, эффекты",                     "Бесплатно / $8/мес"),
])

add_heading("Процесс создания AI-фильма шаг за шагом", 3)

steps = [
    ("1. Сценарий (ChatGPT)", 
     "Пишешь сценарий через ChatGPT: «Напиши сценарий короткометражки на 5 минут в жанре sci-fi триллер, 8 сцен, с описанием визуала каждой». Получаешь готовый текст с диалогами и описаниями сцен."),
    ("2. Раскадровка (Midjourney)",
     "Для каждой сцены генерируешь концепт-картинку в Midjourney. Это «референс» для последующей генерации видео — чтобы все клипы были визуально единым миром."),
    ("3. Генерация клипов (Runway / Kling)",
     "Каждую картинку-референс загружаешь в Runway или Kling → указываешь движение и камеру → получаешь 4-10 секунд видео. На фильм 5 минут нужно ~30-40 клипов."),
    ("4. Озвучка персонажей (ElevenLabs)",
     "Создаёшь голоса для каждого персонажа (разные тембры, интонации). Вводишь диалоги → получаешь озвучку. Можно клонировать реальные голоса или создать уникальные."),
    ("5. Саундтрек (Suno)",
     "Генерируешь фоновую музыку через Suno: «Напряжённый оркестральный саундтрек, sci-fi триллер, 3 минуты». Несколько треков для разных сцен."),
    ("6. Монтаж (CapCut / Descript)",
     "Склеиваешь клипы, накладываешь озвучку и музыку, добавляешь субтитры, настраиваешь переходы. CapCut — проще, Descript — точнее (монтаж через текст)."),
]
for title, desc in steps:
    add_body(title, bold=True)
    add_body(desc)

add_heading("Реальные примеры AI-фильмов для вдохновения", 3)
add_videos([
    ("Лучшая нейросеть для видео: сравнение Runway, Kling, Pika, Hailuo", "https://www.youtube.com/watch?v=1NEZRZGzvWo"),
    ("Runway — создание видео с помощью AI",                              "https://www.youtube.com/watch?v=GUXWB0Mqigw"),
    ("Kling 3.0 — полный обзор, сравнение с другими ИИ",                  "https://www.youtube.com/watch?v=lBe0-UpArZk"),
    ("Новый Runway GEN-4 — революция видеогенерации",                     "https://www.youtube.com/watch?v=YyTdmWOEiZM"),
])

add_heading("Практические задания AI-кино", 3)
add_task(1, "Попроси ChatGPT написать сценарий короткометражки — 3 сцены, любой жанр")
add_task(2, "Сгенерируй раскадровку (3 картинки под каждую сцену) в Midjourney или Leonardo")
add_task(3, "Сделай 3 клипа по 5-8 сек через Kling AI или Runway — по одному на сцену")
add_task(4, "Создай голоса персонажей в ElevenLabs и озвучь диалоги")
add_task(5, "(Продвинутое) Склей всё в CapCut, добавь саундтрек из Suno — готовая короткометражка 1-2 минуты")

add_divider()

# --- 3.3 Длинные ролики ---
add_heading("3.3  Длинные ролики — 10-15 минут и больше", 3)

add_body("Зачем это нужно", bold=True)
add_body("Короткие клипы (4-16 сек из Runway/Kling) — строительные блоки. Длинные видео для YouTube, обучающих курсов, вебинаров, корпоративных презентаций создаются иначе: через специальные инструменты, которые берут текст/сценарий и сами собирают длинное видео.")

add_heading("Инструменты для длинных видео", 3)
add_tool_table([
    ("InVideo AI",      "https://invideo.io",         "Текст/идея → готовое видео 10-15 мин с озвучкой и монтажом", "Бесплатно / $20/мес"),
    ("Pictory AI",      "https://pictory.ai",         "Статья или сценарий → видео с AI-голосом и стоками",          "$19/мес"),
    ("Fliki",           "https://fliki.ai",           "Текст → видео с голосом, субтитрами, иллюстрациями",          "Бесплатно / $21/мес"),
    ("Steve.ai",        "https://steve.ai",           "Скрипт → видео с аватаром или анимацией",                     "$20/мес"),
    ("Synthesia",       "https://synthesia.io",       "Корпоративные видео с AI-аватаром-ведущим",                   "$22/мес"),
    ("HeyGen",          "https://heygen.com",         "Длинные видео с аватаром, до 30 мин",                         "$29/мес"),
    ("Adobe Premiere AI","https://adobe.com/premiere","Профессиональный монтаж + AI-функции",                        "$55/мес (Creative Cloud)"),
    ("CapCut",          "https://capcut.com",         "Финальный монтаж коротких и длинных роликов",                 "Бесплатно"),
])

add_heading("Два подхода к длинному видео", 3)

add_body("Подход 1: Автоматический (InVideo AI / Pictory)", bold=True)
add_body("Идеально для: YouTube-обзоров, обучающих видео, новостного контента.")
for s in [
    "Вводишь тему или вставляешь готовый текст/сценарий",
    "AI сам подбирает стоковые видео/изображения под каждый абзац",
    "AI озвучивает текст синтетическим голосом",
    "Добавляет субтитры, музыку, переходы",
    "Ты правишь если нужно — и видео готово",
    "Результат: 10-15 минут за 20-30 минут работы",
]:
    add_bullet(s)

add_body("Подход 2: Ручная сборка из AI-клипов (Runway + CapCut)", bold=True)
add_body("Идеально для: AI-кино, рекламы, авторского контента с уникальным визуалом.")
for s in [
    "Пишешь подробный сценарий с тайм-кодами: сцена 1 (0:00-1:30), сцена 2 (1:30-3:00)...",
    "Генерируешь клипы под каждый блок (Runway Gen-3 / Kling AI)",
    "Озвучиваешь через ElevenLabs (клонированный или синтетический голос)",
    "Генерируешь саундтрек под настроение каждой сцены (Suno)",
    "Склеиваешь в CapCut или Adobe Premiere",
    "Реальное время: 2-4 часа на 10-15 минут контента",
]:
    add_bullet(s)

add_body("Лайфхак: гибридный подход", bold=True)
add_body("Самое мощное — комбинировать: InVideo AI создаёт черновик видео (структура, стоки, текст) → ты заменяешь ключевые сцены своими AI-клипами из Runway → добавляешь клонированный голос из ElevenLabs. Получается уникальный контент при минимальных затратах времени.")

add_heading("Практический воркфлоу для YouTube-видео 10-15 мин", 3)
add_body("1. Сценарий (15-20 мин):", bold=True)
add_body("ChatGPT: «Напиши сценарий YouTube-видео 12 минут на тему [тема]. Структура: вступление (1 мин), 5 основных блоков (по 2 мин), заключение (1 мин). Для каждого блока — описание визуала»")

add_body("2. Нарезка на блоки (5 мин):", bold=True)
add_body("Разбиваешь сценарий на части. Для каждой части — что на экране (видеоряд или слайд), что говорится (закадровый текст).")

add_body("3. Визуальный ряд (30-60 мин):", bold=True)
add_body("Для информационного видео: InVideo AI или Pictory генерируют видеоряд автоматически.\nДля авторского: Runway/Kling под каждый блок (2-4 клипа на блок).")

add_body("4. Озвучка (10-20 мин):", bold=True)
add_body("ElevenLabs: вставляешь текст → получаешь закадровый голос. Совет: сначала создай черновик, потом подправь паузы и интонации.")

add_body("5. Финальный монтаж (20-30 мин):", bold=True)
add_body("CapCut: склеиваешь видео + аудио + добавляешь субтитры (автоматически) + музыку (из Suno или бесплатная лицензия с YouTube Audio Library).")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("InVideo AI — лучший генератор видео 2025 (учебник)",            "https://www.youtube.com/watch?v=UO_wKLKjFgU"),
    ("InVideo AI — профессиональное видео за 5 минут",                "https://www.youtube.com/watch?v=p-BJ9xmzKJo"),
    ("Лучшая нейросеть для видео: Runway, Kling, Pika, Hailuo",      "https://www.youtube.com/watch?v=1NEZRZGzvWo"),
    ("Новый Runway GEN-4 — обзор и возможности",                      "https://www.youtube.com/watch?v=YyTdmWOEiZM"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Habr: Создание видео с AI — обзор инструментов", "https://habr.com/ru/search/?q=создание+видео+AI+нейросеть"),
    ("VC.ru: AI-видео для бизнеса и контент-маркетинга", "https://vc.ru/search?query=AI+видео+контент+YouTube"),
])

add_heading("Практические задания (длинные ролики)", 3)
add_task(1, "Попробуй InVideo AI: введи любую тему → получи готовый 5-минутный ролик")
add_task(2, "Создай видео по своей статье или тексту через Pictory AI")
add_task(3, "Напиши сценарий 10-минутного видео через ChatGPT с тайм-кодами и описанием визуала")
add_task(4, "(Продвинутое) Гибридный подход: InVideo черновик + замени 3 ключевые сцены своими AI-клипами из Kling")
add_task(5, "(Продвинутое) Полный AI-YouTube-ролик 10+ минут: ChatGPT → Runway → ElevenLabs → CapCut")

add_divider()

# ──────────────────────────────────────────────────────────
# МОДУЛЬ 4 — АВТОМАТИЗАЦИЯ
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("МОДУЛЬ 4  —  Автоматизация без кода", 1, "⚙️")
p = doc.add_paragraph()
p.add_run("⏱ 2-3 недели  |  Сложность: ⭐⭐⭐☆☆").font.size = Pt(10)
p.runs[0].italic = True; p.runs[0].font.color.rgb = RGBColor(120,120,120)

add_heading("Что это и зачем", 3)
add_body("Автоматизация — разные сервисы работают друг с другом без тебя. Добавляешь AI — получаешь умную систему: письмо пришло → AI классифицировал → создал задачу → уведомил команду → записал в CRM. Не программирование — соединяешь блоки в визуальном конструкторе.")

add_body("Что можно автоматизировать:", bold=True)
for s in ["Обработка входящих писем с AI-ответами",
          "Публикация контента в соцсети по расписанию",
          "Мониторинг вакансий и упоминаний бренда",
          "CRM + AI = автоматические follow-up сообщения",
          "Сбор и анализ данных из разных источников",
          "Еженедельные отчёты без участия человека"]:
    add_bullet(s)

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("n8n",       "https://n8n.io",       "Open-source, лучший для AI, можно поднять self-hosted", "Бесплатно / $20/мес"),
    ("Make",      "https://make.com",     "Визуальные сценарии, проще n8n, идеален для старта",    "Бесплатно / $9/мес"),
    ("Zapier",    "https://zapier.com",   "Много готовых интеграций, самый популярный",             "$20/мес"),
    ("Voiceflow", "https://voiceflow.com","No-code AI чат-боты с памятью",                         "Бесплатно / $40/мес"),
    ("Botpress",  "https://botpress.com", "AI боты с аналитикой и кастомизацией",                  "Бесплатно / $49/мес"),
])

add_heading("Интересные нюансы", 3)
add_body("n8n vs Make — что выбрать?", bold=True)
add_body("Make — проще и нагляднее, идеален для начала. n8n — мощнее, self-hosted (бесплатно), лучше для AI. Рекомендация: начни с Make, потом переходи на n8n.")
add_body("AI Agent нода в n8n", bold=True)
add_body("Встроенная нода «AI Agent» — создаёшь агента с инструментами (поиск, файлы, API) и памятью прямо в визуальном редакторе. Без кода.")
add_body("Telegram-бот за 15 минут", bold=True)
add_body("Make/n8n + Telegram Bot API = полноценный бот. Получает сообщения → ChatGPT → отвечает. Буквально 15 минут на первый рабочий бот.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("n8n для начинающих — урок 1: установка и настройка",       "https://www.youtube.com/watch?v=6BpXH4nYHV4"),
    ("ИИ АГЕНТЫ в n8n — полный гайд для начинающих 2025",        "https://www.youtube.com/watch?v=Th_dLnPmbPw"),
    ("Автоматизация бизнес-процессов с AI: n8n + Dify",          "https://www.youtube.com/watch?v=uTtvtup7_oQ"),
    ("Как создать Telegram-бот с ChatGPT без программирования",   "https://www.youtube.com/watch?v=jyPN_61pR0I"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Habr: Автоматизация с n8n",                "https://habr.com/ru/search/?q=n8n+автоматизация"),
    ("VC.ru: AI автоматизация бизнеса",          "https://vc.ru/search?query=автоматизация+AI+бизнес"),
    ("Tproger: Инструменты автоматизации",       "https://tproger.ru/search?query=автоматизация"),
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в Make.com, пройди официальный tutorial (30 мин)")
add_task(2, "Создай первый сценарий: новое письмо на Gmail → уведомление в Telegram")
add_task(3, "Добавь AI: письмо → ChatGPT пишет краткое резюме → Telegram")
add_task(4, "Создай Telegram-бота который отвечает с помощью ChatGPT")
add_task(5, "(Продвинутое) n8n AI Agent: бот который ищет информацию в интернете")

add_divider()

# ──────────────────────────────────────────────────────────
# МОДУЛЬ 5 — АГЕНТЫ
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("МОДУЛЬ 5  —  AI-агенты", 1, "🤖")
p = doc.add_paragraph()
p.add_run("⏱ 1-2 месяца  |  Сложность: ⭐⭐⭐⭐☆").font.size = Pt(10)
p.runs[0].italic = True; p.runs[0].font.color.rgb = RGBColor(120,120,120)

add_heading("Что это и зачем", 3)
add_body("Агент — AI который не просто отвечает, а действует: получает задачу, планирует шаги, использует инструменты (браузер, файлы, API, код), проверяет результаты и итерирует до цели.")
add_body("Разница: ChatGPT — консультант, говорит что делать. Агент — исполнитель, который сам идёт и делает.")

add_body("Примеры задач:", bold=True)
for s in ["«Найди топ-10 конкурентов, проанализируй их сайты и составь отчёт»",
          "«Мониторь вакансии каждый день, отбирай подходящие и присылай подборку»",
          "«Просматривай мои письма, отвечай на типовые, важные — пересылай мне»"]:
    add_bullet(s)

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("Dify",              "https://dify.ai",                    "No-code AI агенты и пайплайны, лучший старт",   "Бесплатно / $59/мес"),
    ("Flowise",           "https://flowiseai.com",              "Визуальный конструктор, self-hosted",            "Бесплатно"),
    ("n8n AI Agent",      "https://n8n.io",                     "Агент в визуальном редакторе без кода",          "Бесплатно / $20/мес"),
    ("CrewAI",            "https://crewai.com",                 "Мульти-агентные системы (Python)",               "Бесплатно (open source)"),
    ("LangChain",         "https://python.langchain.com",       "Мощный фреймворк для агентов (Python)",          "Бесплатно (open source)"),
    ("OpenAI Assistants", "https://platform.openai.com/docs/assistants", "Встроенные агенты OpenAI через API", "Pay per use"),
])

add_heading("Интересные нюансы", 3)
add_body("RAG — агент со своей базой знаний", bold=True)
add_body("Загружаешь в Dify свои документы → агент отвечает, опираясь на них. Не выдумывает — достаёт конкретные данные из твоих файлов.")
add_body("Мульти-агентные системы в CrewAI", bold=True)
add_body("Пример команды: Researcher (ищет) + Analyst (анализирует) + Writer (пишет отчёт). Каждый делает своё, результат складывается автоматически.")
add_body("Встроенные агенты в ChatGPT Plus", bold=True)
for s in ["Advanced Data Analysis — пишет и выполняет код, анализирует Excel/CSV",
          "Browsing — читает актуальные страницы в интернете",
          "DALL-E — рисует изображения прямо в диалоге"]:
    add_bullet(s)
add_body("Ограничения — важно знать:", bold=True)
add_body("Агенты ошибаются на сложных задачах. Лучшая практика: агент предлагает → ты одобряешь. Начинай с тестовой «песочницы».")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    ("ИИ АГЕНТЫ в n8n — полный гайд для начинающих 2025",        "https://www.youtube.com/watch?v=Th_dLnPmbPw"),
    ("Автоматизация с AI: n8n + Dify на практике (вебинар)",      "https://www.youtube.com/watch?v=uTtvtup7_oQ"),
    ("Собрал команду AI-директоров на совещание — CrewAI",        "https://www.youtube.com/watch?v=6OaRO657k5o"),
    ("n8n — полный курс для начинающих (плейлист)",               "https://www.youtube.com/playlist?list=PL2lsRzl0d_kBnwtotsIotbmXnLTBUDeXs"),
])

add_heading("Статьи (русские)", 3)
add_articles([
    ("Habr: AI-агенты — введение",       "https://habr.com/ru/search/?q=AI+агенты"),
    ("Habr: LangChain на практике",      "https://habr.com/ru/search/?q=LangChain"),
    ("VC.ru: Агенты в бизнесе",          "https://vc.ru/search?query=AI+агенты+бизнес"),
])

add_heading("Практические задания", 3)
add_task(1, "Dify: создай простого агента с инструментом поиска в интернете")
add_task(2, "RAG в Dify: загрузи свои документы, создай чат-бота по ним")
add_task(3, "n8n AI Agent: получает запрос → ищет → структурированно отвечает")
add_task(4, "(Продвинутое) CrewAI: система из 3 агентов — Researcher + Analyst + Writer")
add_task(5, "(Продвинутое) Агент-мониторинг: каждый день следит за чем-то важным")

add_divider()

# ──────────────────────────────────────────────────────────
# TELEGRAM + ПРИНЦИПЫ
# ──────────────────────────────────────────────────────────
add_heading("Telegram-каналы — оставаться в курсе", 2, "📱")
tg_table = doc.add_table(rows=1, cols=2)
tg_table.style = 'Table Grid'
hdr = tg_table.rows[0].cells
for i, h in enumerate(["Канал", "О чём"]):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True
    hdr[i].paragraphs[0].runs[0].font.size = Pt(10)
    hdr[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255,255,255)
    shade_cell(hdr[i], '2E5090')
for ch, url, desc in [
    ("@ai_newz",           "https://t.me/ai_newz",           "Новости AI на русском"),
    ("@aitoolsclub",       "https://t.me/aitoolsclub",       "Обзоры новых AI-инструментов"),
    ("@vas3k_club",        "https://t.me/vas3k_club",        "Вастрик про технологии"),
    ("@machinelearning_ru","https://t.me/machinelearning_ru","ML и AI по-русски"),
    ("@neural_networks_ru","https://t.me/neural_networks_ru","Нейросети для практиков"),
]:
    row = tg_table.add_row().cells
    p0 = row[0].paragraphs[0]
    add_hyperlink(p0, url, ch, font_size=10, bold=True)
    row[1].text = desc
    row[1].paragraphs[0].runs[0].font.size = Pt(10)
doc.add_paragraph()
add_divider()

add_heading("Принципы быстрого обучения", 2, "💡")
for num, title, detail in [
    ("1", "Сразу на практике",              "Не читай всё подряд — пробуй руками после каждой темы"),
    ("2", "Один инструмент → один проект",  "Не распыляйся на 10 инструментов одновременно"),
    ("3", "Документируй что работает",      "Веди свою базу промптов хотя бы в Notion"),
    ("4", "Учись на кейсах",                "Ищи «как сделали X с помощью AI» на YouTube и Habr"),
    ("5", "Комьюнити",                      "Вопросы в Telegram-чатах закрывают пробелы за часы"),
    ("6", "Принцип минимального инструмента","Для каждой задачи — самый простой который справляется"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(f"{num}. {title}  — "); r1.bold = True; r1.font.size = Pt(11)
    r2 = p.add_run(detail); r2.font.size = Pt(11)

add_divider()

# ──────────────────────────────────────────────────────────
# ПРИЛОЖЕНИЕ — АНГЛИЙСКИЕ МАТЕРИАЛЫ
# ──────────────────────────────────────────────────────────
doc.add_page_break()
add_heading("ПРИЛОЖЕНИЕ", 1, "📚")
add_heading("Английские материалы для углублённого изучения", 2)
add_body("Английские источники опережают русскоязычные на 6-12 месяцев. Для тех, кто хочет быть на передовой.", italic=True)

add_heading("YouTube-каналы (English)", 3)
for channel, url, desc in [
    ("Matt Wolfe",      "https://www.youtube.com/@mreflow",       "AI новости, еженедельные обзоры инструментов"),
    ("AI Jason",        "https://www.youtube.com/@AIJasonZ",      "Агенты, автоматизация, n8n туториалы"),
    ("David Ondrej",    "https://www.youtube.com/@DavidOndrej",   "CrewAI, LangChain, мультиагентные системы"),
    ("Sam Witteveen",   "https://www.youtube.com/@samwitteveenai","LangChain, технические туториалы"),
    ("Two Minute Papers","https://www.youtube.com/@TwoMinutePapers","Доступные обзоры AI-исследований"),
    ("Andrej Karpathy", "https://www.youtube.com/@AndrejKarpathy","Глубокое понимание нейросетей (ex-Tesla AI)"),
    ("Lex Fridman",     "https://www.youtube.com/@lexfridman",    "Интервью с лидерами AI"),
    ("Corridor Crew",   "https://www.youtube.com/@CorridorCrew",  "VFX + AI-видео разборы, AI-кино"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    r1 = p.add_run("▶  "); r1.font.size = Pt(10); r1.font.color.rgb = RGBColor(200,50,50)
    add_hyperlink(p, url, channel, font_size=10, color=(200,50,50), bold=True)
    r2 = p.add_run("  —  " + desc); r2.font.size = Pt(10)

add_heading("Сайты и документация (English)", 3)
for url, desc in [
    ("https://www.promptingguide.ai",            "Лучший гайд по промптингу"),
    ("https://learnprompting.org",               "Интерактивные уроки промптинга"),
    ("https://python.langchain.com/docs",        "Документация LangChain"),
    ("https://docs.crewai.com",                  "Документация CrewAI"),
    ("https://docs.n8n.io",                      "Документация n8n"),
    ("https://theresanaiforthat.com",            "Каталог всех AI-инструментов"),
    ("https://openai.com/blog",                  "Официальный блог OpenAI"),
    ("https://anthropic.com/research",           "Исследования создателей Claude"),
    ("https://runwayml.com/research",            "Runway — исследования AI-видео"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    r1 = p.add_run("📖  "); r1.font.size = Pt(10); r1.font.color.rgb = RGBColor(50,130,50)
    add_hyperlink(p, url, url.replace("https://",""), font_size=10, color=(50,130,50), bold=True)
    r2 = p.add_run("  —  " + desc); r2.font.size = Pt(10)

add_heading("Видео по конкретным темам (English)", 3)
for title, url in [
    ("LangChain Crash Course for Beginners",  "https://www.youtube.com/watch?v=lG7Uxts9SXs"),
    ("Build AI Agents with n8n (AI Jason)",   "https://www.youtube.com/watch?v=bk3xAi430NQ"),
    ("CrewAI Tutorial — Build AI Agents",     "https://www.youtube.com/watch?v=kJvXT25LkwA"),
    ("Midjourney V7 Full Beginners Guide",    "https://www.youtube.com/watch?v=9DPpFQPJIig"),
    ("ElevenLabs Full Guide 2025",            "https://www.youtube.com/watch?v=NmFSkjSh23w"),
    ("HeyGen — How to Create AI Avatar",      "https://www.youtube.com/watch?v=tHWSnrMXVQg"),
    ("Runway Gen-3 Alpha — Full Tutorial",    "https://www.youtube.com/watch?v=GUXWB0Mqigw"),
    ("How to Make AI Short Film",             "https://www.youtube.com/watch?v=1NEZRZGzvWo"),
    ("InVideo AI Full Tutorial 2025",         "https://www.youtube.com/watch?v=UO_wKLKjFgU"),
    ("Dify AI Agent — Full Tutorial",         "https://www.youtube.com/watch?v=uTtvtup7_oQ"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent  = Cm(0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    r1 = p.add_run("🎥  "); r1.font.size = Pt(10); r1.font.color.rgb = RGBColor(180,50,50)
    add_hyperlink(p, url, title, font_size=10, color=(180,50,50))

add_divider()

# ФИНАЛ
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("🚀  Удачи в обучении!")
run.font.size = Pt(14); run.font.bold = True; run.font.color.rgb = RGBColor(30,80,180)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run("AI меняется каждые 2-3 месяца — главное не останавливаться.")
run2.font.size = Pt(10); run2.font.italic = True; run2.font.color.rgb = RGBColor(120,120,120)

p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
run3 = p3.add_run("Составлено: март 2026  |  Версия: 3.0")
run3.font.size = Pt(9); run3.font.color.rgb = RGBColor(160,160,160)

doc.save('/home/clawdbot/.openclaw/workspace/drafts/AI_Course_v3.docx')
print("Done!")
