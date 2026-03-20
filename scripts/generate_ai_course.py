#!/usr/bin/env python3
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

doc = Document()

# ── Стили ──────────────────────────────────────────────────────────────────

def set_font(run, bold=False, size=11, color=None):
    run.bold = bold
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)

def add_heading(text, level=1, color=(30, 30, 30)):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        run.font.color.rgb = RGBColor(*color)
        if level == 1:
            run.font.size = Pt(20)
        elif level == 2:
            run.font.size = Pt(16)
        elif level == 3:
            run.font.size = Pt(13)
    return p

def add_para(text, bold=False, italic=False, size=11, color=None, align=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    run.font.size = Pt(size)
    if color:
        run.font.color.rgb = RGBColor(*color)
    if align:
        p.alignment = align
    return p

def add_bullet(text, level=0):
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(text)
    run.font.size = Pt(11)
    return p

def add_link_bullet(label, url, desc=""):
    p = doc.add_paragraph(style='List Bullet')
    r1 = p.add_run(f"• {label}")
    r1.bold = True
    r1.font.size = Pt(11)
    r1.font.color.rgb = RGBColor(0, 102, 204)
    if desc:
        r2 = p.add_run(f" — {desc}")
        r2.font.size = Pt(11)
    r3 = p.add_run(f"\n  {url}")
    r3.font.size = Pt(9)
    r3.font.color.rgb = RGBColor(120, 120, 120)
    return p

def add_table(headers, rows, col_widths=None):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    
    # Заголовок
    hrow = table.rows[0]
    for i, h in enumerate(headers):
        cell = hrow.cells[i]
        cell.text = h
        cell.paragraphs[0].runs[0].bold = True
        cell.paragraphs[0].runs[0].font.size = Pt(10)
        cell.paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
        # Фон заголовка
        tc = cell._tc
        tcPr = tc.get_or_add_tcPr()
        shd = OxmlElement('w:shd')
        shd.set(qn('w:fill'), '1a73e8')
        shd.set(qn('w:color'), 'auto')
        shd.set(qn('w:val'), 'clear')
        tcPr.append(shd)
    
    # Данные
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1]
        for ci, cell_text in enumerate(row_data):
            cell = row.cells[ci]
            cell.text = cell_text
            cell.paragraphs[0].runs[0].font.size = Pt(10)
            # Чередование строк
            if ri % 2 == 0:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                shd = OxmlElement('w:shd')
                shd.set(qn('w:fill'), 'f0f4ff')
                shd.set(qn('w:color'), 'auto')
                shd.set(qn('w:val'), 'clear')
                tcPr.append(shd)
    return table

def add_divider():
    p = doc.add_paragraph("─" * 80)
    for run in p.runs:
        run.font.size = Pt(8)
        run.font.color.rgb = RGBColor(200, 200, 200)
    return p

def add_module_header(num, title, duration, difficulty):
    p = doc.add_paragraph()
    r1 = p.add_run(f"Модуль {num}. ")
    r1.bold = True
    r1.font.size = Pt(17)
    r1.font.color.rgb = RGBColor(26, 115, 232)
    r2 = p.add_run(title)
    r2.bold = True
    r2.font.size = Pt(17)
    r2.font.color.rgb = RGBColor(30, 30, 30)
    
    p2 = doc.add_paragraph()
    r3 = p2.add_run(f"⏱ {duration}   |   Сложность: {difficulty}")
    r3.font.size = Pt(10)
    r3.font.color.rgb = RGBColor(100, 100, 100)
    r3.italic = True
    doc.add_paragraph()

# ══════════════════════════════════════════════════════════════════════════════
# ТИТУЛЬНАЯ СТРАНИЦА
# ══════════════════════════════════════════════════════════════════════════════

doc.add_paragraph()
doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("🤖  AI С НУЛЯ ДО АГЕНТОВ")
r.bold = True
r.font.size = Pt(28)
r.font.color.rgb = RGBColor(26, 115, 232)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Продвинутое практическое обучение")
r.font.size = Pt(16)
r.font.color.rgb = RGBColor(80, 80, 80)

doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("От промптинга до создания собственных AI-агентов")
r.font.size = Pt(12)
r.italic = True
r.font.color.rgb = RGBColor(120, 120, 120)

doc.add_paragraph()
doc.add_paragraph()

add_table(
    ["", ""],
    [
        ["Для кого", "Менеджеры, предприниматели, специалисты без технического бэкграунда"],
        ["Результат", "Применяете AI в работе, создаёте автоматизации, строите агентов"],
        ["Длительность", "3 месяца самостоятельного обучения"],
        ["Формат", "Теория + практические задания + ресурсы"],
        ["Версия", "1.0 — март 2026"],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# ВВЕДЕНИЕ
# ══════════════════════════════════════════════════════════════════════════════

add_heading("Введение", 1)

add_para(
    "Этот курс — не про то, чтобы 'познакомиться с нейросетями'. Это про то, чтобы "
    "перестать делать руками то, что за тебя может сделать AI. Мы идём от базового "
    "промптинга до создания агентов, которые работают самостоятельно.",
    size=12
)
doc.add_paragraph()

add_para("Как учиться эффективно:", bold=True, size=12)
add_bullet("Не читай всё подряд — сразу пробуй руками")
add_bullet("Один инструмент → один реальный проект. Не распыляйся")
add_bullet("Документируй что работает — веди базу своих промптов")
add_bullet("Учись на кейсах — ищи 'как сделали X с помощью AI'")
add_bullet("Задавай вопросы в комьюнити — это быстрее, чем читать доки")
doc.add_paragraph()

add_para("Дорожная карта на 3 месяца:", bold=True, size=12)
add_table(
    ["Неделя", "Модуль", "Ключевой результат"],
    [
        ["1–2", "Промптинг", "Умеешь получать от AI именно то, что нужно"],
        ["3", "Изображения", "Генерируешь визуал для задач без дизайнера"],
        ["4–5", "Видео и голос", "Создаёшь видеоконтент и озвучку с AI"],
        ["6–8", "Автоматизация", "Настроены рабочие сценарии без кода"],
        ["9–12", "AI-агенты", "Работает первый агент, который делает задачи за тебя"],
    ]
)

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 1. ПРОМПТИНГ
# ══════════════════════════════════════════════════════════════════════════════

add_module_header(1, "Промптинг — разговаривай с AI правильно", "1–2 недели", "⭐☆☆☆☆ Начальный")

add_para(
    "Промпт — это инструкция для нейросети. 80% результата зависит от того, как ты "
    "формулируешь задачу. Большинство людей использует AI как поисковик — это ошибка. "
    "Правильный промпт = конкретная роль + контекст + задача + формат ответа.",
    size=11
)
doc.add_paragraph()

add_heading("Инструменты", 3)
add_table(
    ["Инструмент", "Для чего лучше всего", "Цена"],
    [
        ["ChatGPT (GPT-4o)", "Универсальный старт, лучший для большинства задач", "Бесплатно / $20/мес"],
        ["Claude 3.5 Sonnet", "Длинные тексты, анализ документов, кодинг", "Бесплатно / $20/мес"],
        ["Gemini 2.0", "Интеграция с Google Docs/Sheets, работа с файлами", "Бесплатно"],
        ["Perplexity AI", "Поиск с источниками, актуальные данные", "Бесплатно / $20/мес"],
        ["Grok (xAI)", "Без цензуры, реальное время (Twitter)", "Бесплатно с X Premium"],
    ]
)
doc.add_paragraph()

add_heading("Ключевые техники", 3)

add_para("1. Role Prompting — дай AI роль", bold=True)
add_para(
    'Плохо: "Напиши продающий текст"\n'
    'Хорошо: "Ты опытный копирайтер с 10 годами опыта в B2B SaaS. '
    'Напиши продающий текст для...'
)
doc.add_paragraph()

add_para("2. Chain-of-Thought — пошаговое мышление", bold=True)
add_para(
    'Добавляй к сложным задачам: "Думай пошагово. Сначала проанализируй X, '
    'потом сделай Y, в конце дай итог в формате Z"'
)
doc.add_paragraph()

add_para("3. Few-shot — покажи примеры", bold=True)
add_para(
    '"Вот 2 примера того что мне нужно: [пример 1] [пример 2]. '
    'Теперь сделай то же самое для..."'
)
doc.add_paragraph()

add_para("4. Structured Output — формат ответа", bold=True)
add_para('"Верни ответ в виде таблицы / JSON / нумерованного списка / markdown"')
doc.add_paragraph()

add_para("5. Iterative Refinement — доработка через диалог", bold=True)
add_para(
    'Не переписывай промпт с нуля — уточняй: '
    '"Сделай это более кратко", "Добавь примеры", "Перепиши в более деловом стиле"'
)
doc.add_paragraph()

add_para("6. Meta-prompting — попроси AI написать промпт за тебя", bold=True)
add_para('"Напиши промпт для задачи X. Промпт должен давать конкретный результат Y"')
doc.add_paragraph()

add_heading("📺 Видео на YouTube", 3)
add_link_bullet(
    "Prompt Engineering Full Course",
    "https://youtube.com/watch?v=_ZvnD73m40o",
    "Andrew Ng — бесплатный курс от создателя DeepLearning.AI (2 часа)"
)
add_link_bullet(
    "ChatGPT Prompt Engineering Tips",
    "https://youtube.com/watch?v=jC4v5AS4RIM",
    "Канал Jeff Su — практичные техники за 20 минут"
)
add_link_bullet(
    "Advanced Prompting Techniques 2025",
    "https://youtube.com/watch?v=wVzuvf9D9BU",
    "Канал Matt Wolfe — продвинутые техники"
)
add_link_bullet(
    "Промптинг для бизнеса (русский)",
    "https://youtube.com/@ai_for_business_ru",
    "Практические кейсы на русском языке"
)
doc.add_paragraph()

add_heading("📖 Статьи и курсы", 3)
add_link_bullet(
    "Prompt Engineering Guide",
    "https://www.promptingguide.ai/ru",
    "Лучший бесплатный гайд, есть на русском. Все техники с примерами"
)
add_link_bullet(
    "Learn Prompting",
    "https://learnprompting.org",
    "Интерактивный курс с упражнениями"
)
add_link_bullet(
    "OpenAI Prompt Engineering Guide",
    "https://platform.openai.com/docs/guides/prompt-engineering",
    "Официальные рекомендации от OpenAI"
)
add_link_bullet(
    "Anthropic Prompt Library",
    "https://docs.anthropic.com/en/prompt-library",
    "100+ готовых промптов для разных задач"
)
add_link_bullet(
    "Курс ChatGPT Prompt Engineering (DeepLearning.AI)",
    "https://www.deeplearning.ai/short-courses/chatgpt-prompt-engineering-for-developers/",
    "Бесплатный мини-курс от Andrew Ng и OpenAI"
)
doc.add_paragraph()

add_heading("✏️ Практические задания", 3)
add_bullet("Напиши промпт для генерации резюме под конкретную вакансию — без доработки руками")
add_bullet("Создай промпт который анализирует договор и выделяет риски и невыгодные условия")
add_bullet("Сделай шаблон промпта для написания холодных писем (подставляй имя/компанию)")
add_bullet("Напиши мета-промпт: попроси AI создать промпт для твоей рабочей задачи")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 2. ИЗОБРАЖЕНИЯ
# ══════════════════════════════════════════════════════════════════════════════

add_module_header(2, "Генерация изображений", "1 неделя", "⭐⭐☆☆☆ Базовый")

add_para(
    "Ты описываешь картинку текстом — нейросеть её рисует. Используется для маркетинга, "
    "презентаций, концепт-артов, аватаров, рекламных баннеров. Дизайнер больше не нужен "
    "для базового визуала.",
    size=11
)
doc.add_paragraph()

add_heading("Инструменты", 3)
add_table(
    ["Инструмент", "Сильная сторона", "Цена"],
    [
        ["Midjourney v6", "Лучшее художественное качество, реализм", "$10–$30/мес"],
        ["DALL-E 3", "Встроен в ChatGPT, понимает текст, работает с инструкциями", "Входит в ChatGPT Plus"],
        ["Leonardo.ai", "Много бесплатных кредитов, хороший контроль стиля", "Бесплатно / $12/мес"],
        ["Adobe Firefly", "Безопасно для коммерции, интеграция с Adobe", "Бесплатно / от $5/мес"],
        ["Stable Diffusion (AUTOMATIC1111)", "Бесплатно локально, полный контроль", "Бесплатно (нужен GPU)"],
        ["Ideogram 2.0", "Лучший для текста на изображениях", "Бесплатно / $8/мес"],
        ["Flux.1", "Топовое качество, лучший open-source", "Через Replicate API"],
    ]
)
doc.add_paragraph()

add_heading("Ключевые техники", 3)
add_para("Описание стиля:", bold=True)
add_para('"cinematic lighting, 4K, photorealistic" — для реализма')
add_para('"flat design, minimalist, vector" — для иллюстраций')
add_para('"oil painting, impressionist style" — для арта')
doc.add_paragraph()

add_para("Negative prompts (что НЕ рисовать):", bold=True)
add_para('"--no text, watermark, blur, low quality, deformed hands"')
doc.add_paragraph()

add_para("Aspect ratio:", bold=True)
add_para('"--ar 16:9" для сторис, "--ar 1:1" для постов, "--ar 9:16" для вертикального видео"')
doc.add_paragraph()

add_heading("📺 Видео на YouTube", 3)
add_link_bullet(
    "Midjourney Full Beginner Course 2025",
    "https://youtube.com/watch?v=KJKKgQVMQ0Q",
    "Канал AI Andy — полный курс по Midjourney (1.5 часа)"
)
add_link_bullet(
    "Midjourney V6 Complete Guide",
    "https://youtube.com/watch?v=F5SLQO2V5LI",
    "Все новые функции v6, стили, параметры"
)
add_link_bullet(
    "Leonardo AI Tutorial for Beginners",
    "https://youtube.com/watch?v=yKBcEYA8aFg",
    "Практический гайд по Leonardo.ai"
)
add_link_bullet(
    "FLUX.1 — лучший генератор изображений 2025",
    "https://youtube.com/watch?v=rXFSGnpHvqs",
    "Обзор FLUX.1 vs Midjourney vs DALL-E"
)
doc.add_paragraph()

add_heading("📖 Статьи и ресурсы", 3)
add_link_bullet(
    "Civitai.com",
    "https://civitai.com",
    "Тысячи готовых промптов, моделей и стилей для Stable Diffusion"
)
add_link_bullet(
    "Midjourney Prompts Library",
    "https://www.midjourney.com/showcase",
    "Официальные примеры работ с промптами"
)
add_link_bullet(
    "PromptHero",
    "https://prompthero.com",
    "База лучших промптов для всех генераторов"
)
add_link_bullet(
    "Ideogram Prompts Guide",
    "https://ideogram.ai/blog",
    "Особенно полезен для промптов с текстом"
)
doc.add_paragraph()

add_heading("✏️ Практические задания", 3)
add_bullet("Сгенерируй 5 вариантов баннера для своего LinkedIn профиля")
add_bullet("Создай деловой аватар в разных стилях (реалистичный, иллюстрация, минимализм)")
add_bullet("Сделай серию иллюстраций для презентации (одинаковый стиль, разные сцены)")
add_bullet("Создай рекламный баннер для вымышленного продукта — только промптом")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 3. ВИДЕО И ГОЛОС
# ══════════════════════════════════════════════════════════════════════════════

add_module_header(3, "Генерация видео и голоса", "1–2 недели", "⭐⭐⭐☆☆ Средний")

add_para(
    "Видео из текста, оживление фото, клонирование голоса, аватары-ведущие, "
    "дубляж видео на другой язык — всё это доступно сейчас без видеографа и студии.",
    size=11
)
doc.add_paragraph()

add_heading("Инструменты", 3)
add_table(
    ["Инструмент", "Для чего", "Цена"],
    [
        ["Runway Gen-3 Alpha", "Видео из текста и фото, топ качество", "$15/мес"],
        ["Kling AI 1.6", "Видео из текста, сильный конкурент Runway", "Бесплатно / $10/мес"],
        ["Sora (OpenAI)", "Видео от OpenAI, реалистичные сцены", "$20/мес (ChatGPT Plus)"],
        ["HeyGen 2.0", "Видео-аватары ведущих, дубляж на 40+ языков", "$29/мес"],
        ["ElevenLabs", "Клонирование голоса, озвучка текста", "Бесплатно / $5/мес"],
        ["Luma Dream Machine", "Видео из текста и картинки, бесплатный тариф", "Бесплатно / $30/мес"],
        ["Synthesia", "Корпоративные видео с AI-аватарами", "$30/мес"],
        ["CapCut AI", "Монтаж с AI, субтитры, эффекты", "Бесплатно"],
    ]
)
doc.add_paragraph()

add_heading("📺 Видео на YouTube", 3)
add_link_bullet(
    "Runway Gen-3 Complete Tutorial",
    "https://youtube.com/watch?v=G_KGjOGatnY",
    "Полный гайд по Runway — текст в видео, стили, параметры"
)
add_link_bullet(
    "HeyGen Tutorial: AI Avatars for Business",
    "https://youtube.com/watch?v=NXMRInBD4gc",
    "Как создавать профессиональные видео с AI-ведущим"
)
add_link_bullet(
    "ElevenLabs Voice Cloning Guide",
    "https://youtube.com/watch?v=VB7MsepNZyc",
    "Клонируй свой голос за 5 минут"
)
add_link_bullet(
    "Kling AI vs Runway vs Sora — Сравнение 2025",
    "https://youtube.com/watch?v=jSMVdBnD1ac",
    "Честное сравнение топовых видео-генераторов"
)
add_link_bullet(
    "AI Video Creation Full Workflow",
    "https://youtube.com/watch?v=Y3K4KGSE1Ng",
    "Канал Matt Wolfe — полный воркфлоу от идеи до публикации"
)
doc.add_paragraph()

add_heading("📖 Статьи и ресурсы", 3)
add_link_bullet(
    "Runway Learning Center",
    "https://runwayml.com/blog",
    "Официальные туториалы и кейсы от команды Runway"
)
add_link_bullet(
    "ElevenLabs Docs",
    "https://elevenlabs.io/docs",
    "Документация по API и функциям клонирования голоса"
)
add_link_bullet(
    "AI Video Tools Comparison (Hugging Face)",
    "https://huggingface.co/spaces/multimodalart/video-models-comparison",
    "Интерактивное сравнение видео-моделей"
)
doc.add_paragraph()

add_heading("✏️ Практические задания", 3)
add_bullet("Создай 15-секундный ролик для своего проекта (текст → видео через Runway)")
add_bullet("Клонируй свой голос в ElevenLabs, озвучь короткий текст")
add_bullet("Сделай видео-аватар который рассказывает о твоих услугах (HeyGen)")
add_bullet("Переведи любое YouTube видео на другой язык с сохранением голоса (HeyGen Translate)")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 4. АВТОМАТИЗАЦИЯ
# ══════════════════════════════════════════════════════════════════════════════

add_module_header(4, "Автоматизация без кода", "2–3 недели", "⭐⭐⭐☆☆ Средний")

add_para(
    "Ты соединяешь сервисы между собой + добавляешь AI — и они работают без тебя. "
    "Пример: новое письмо → AI анализирует → создаёт задачу в Jira → уведомляет "
    "в Telegram. Без единой строки кода.",
    size=11
)
doc.add_paragraph()

add_heading("Инструменты", 3)
add_table(
    ["Инструмент", "Сильная сторона", "Цена"],
    [
        ["n8n", "Open-source, лучший для AI-автоматизаций, self-hosted", "Бесплатно / $20/мес"],
        ["Make (Integromat)", "Визуальные сценарии, проще чем n8n, 1500+ интеграций", "Бесплатно / $9/мес"],
        ["Zapier", "Самый большой каталог интеграций (6000+), простой", "$20/мес"],
        ["Voiceflow", "AI чат-боты и голосовые ассистенты", "Бесплатно / $40/мес"],
        ["Activepieces", "Open-source альтернатива Zapier", "Бесплатно"],
    ]
)
doc.add_paragraph()

add_heading("Что можно автоматизировать", 3)
add_bullet("Обработка входящих писем — AI читает, классифицирует, отвечает или создаёт задачу")
add_bullet("Публикация контента в соцсети по расписанию с AI-генерацией")
add_bullet("Мониторинг вакансий → анализ AI → уведомление в Telegram")
add_bullet("CRM: новый лид → AI пишет персональное письмо → отправляет")
add_bullet("Ежедневные отчёты из данных — автоматически каждое утро")
add_bullet("AI-ассистент в Telegram/WhatsApp который отвечает на вопросы о тебе")
doc.add_paragraph()

add_heading("📺 Видео на YouTube", 3)
add_link_bullet(
    "n8n AI Automation Course for Beginners",
    "https://youtube.com/watch?v=1MwSoB0gnM4",
    "Полный курс по n8n с AI — от нуля до рабочих сценариев"
)
add_link_bullet(
    "Build an AI Agent with n8n (no code)",
    "https://youtube.com/watch?v=RI-udxgqEbM",
    "Создаём AI-агента на n8n — пошагово"
)
add_link_bullet(
    "Make.com AI Automation Tutorial 2025",
    "https://youtube.com/watch?v=nj6nAiCpVBQ",
    "Make + ChatGPT — практические сценарии"
)
add_link_bullet(
    "Канал Cole Medin",
    "https://youtube.com/@ColeMedin",
    "Лучший канал по n8n и AI-автоматизации, практические кейсы"
)
add_link_bullet(
    "Канал Leon van Zyl",
    "https://youtube.com/@leonvanzyl",
    "n8n туториалы для бизнеса"
)
doc.add_paragraph()

add_heading("📖 Статьи и ресурсы", 3)
add_link_bullet(
    "n8n Docs",
    "https://docs.n8n.io",
    "Официальная документация + примеры сценариев"
)
add_link_bullet(
    "n8n Community Templates",
    "https://n8n.io/workflows",
    "1000+ готовых шаблонов автоматизаций"
)
add_link_bullet(
    "Make.com Academy",
    "https://academy.make.com",
    "Бесплатные курсы от Make"
)
doc.add_paragraph()

add_heading("✏️ Практические задания", 3)
add_bullet("Настрой уведомление в Telegram при новом письме на почте (Make или n8n)")
add_bullet("Создай AI-бота который отвечает на вопросы о твоих услугах (Voiceflow + GPT-4)")
add_bullet("Сделай сценарий: мониторинг вакансий hh.ru → AI анализирует подходит ли → уведомление")
add_bullet("Автоматическая публикация поста в Telegram каждый день (тема из RSS + GPT-4 переписывает)")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# МОДУЛЬ 5. AI-АГЕНТЫ
# ══════════════════════════════════════════════════════════════════════════════

add_module_header(5, "AI-агенты — AI который действует", "1–2 месяца", "⭐⭐⭐⭐☆ Продвинутый")

add_para(
    "Агент — это AI который не просто отвечает, а действует: ищет информацию в интернете, "
    "управляет файлами, заходит на сайты, выполняет задачи последовательно, помнит контекст. "
    "Думает и делает, а не только говорит.",
    size=11
)
doc.add_paragraph()

add_heading("Как устроен агент", 3)
add_para("Задача → Планирование → Инструменты → Действие → Оценка результата → (повтор если нужно) → Итог", italic=True)
doc.add_paragraph()

add_para("4 компонента любого агента:", bold=True)
add_bullet("LLM (мозг) — GPT-4o, Claude 3.5, Gemini 2.0 — принимает решения")
add_bullet("Tools (инструменты) — что умеет: браузер, файлы, API, запуск кода")
add_bullet("Memory (память) — краткосрочная (контекст) и долгосрочная (база знаний)")
add_bullet("Planning (планирование) — как разбивает сложную задачу на шаги")
doc.add_paragraph()

add_heading("Инструменты", 3)
add_table(
    ["Инструмент", "Для чего", "Сложность", "Цена"],
    [
        ["OpenClaw", "Готовый агент-ассистент с памятью и инструментами", "⭐", "От $20/мес"],
        ["Dify", "No-code агенты с UI, RAG, workflow", "⭐⭐", "Бесплатно / self-hosted"],
        ["CrewAI", "Мульти-агентные системы (Python)", "⭐⭐⭐", "Бесплатно (open-source)"],
        ["LangChain", "Фреймворк для агентов на Python, максимальный контроль", "⭐⭐⭐⭐", "Бесплатно"],
        ["AutoGen (Microsoft)", "Агенты которые общаются между собой", "⭐⭐⭐", "Бесплатно"],
        ["LangGraph", "Граф-агенты, сложные воркфлоу", "⭐⭐⭐⭐", "Бесплатно"],
        ["Flowise", "No-code LangChain, визуальный конструктор", "⭐⭐", "Бесплатно / self-hosted"],
    ]
)
doc.add_paragraph()

add_heading("📺 Видео на YouTube", 3)
add_link_bullet(
    "LangChain Full Course for Beginners 2025",
    "https://youtube.com/watch?v=lG7Uxts9SXs",
    "Freecodcamp — полный курс по LangChain (3 часа)"
)
add_link_bullet(
    "Build AI Agents with CrewAI",
    "https://youtube.com/watch?v=tnejrr-0a94",
    "Создаём мульти-агентную систему с CrewAI — пошагово"
)
add_link_bullet(
    "AutoGen Tutorial — Multi-Agent AI",
    "https://youtube.com/watch?v=V2qZ_lgxTzg",
    "Microsoft AutoGen — агенты которые работают в команде"
)
add_link_bullet(
    "Dify.AI Tutorial — No-Code AI Agents",
    "https://youtube.com/watch?v=rLAXVQ1SaFA",
    "Строим агента без кода на Dify"
)
add_link_bullet(
    "Канал David Ondrej",
    "https://youtube.com/@DavidOndrej",
    "Лучший канал про AI-агентов — практика, кейсы, архитектуры"
)
add_link_bullet(
    "Канал AI Jason",
    "https://youtube.com/@AIJasonZ",
    "Продвинутые туториалы по агентам и автоматизации"
)
doc.add_paragraph()

add_heading("📖 Статьи и курсы", 3)
add_link_bullet(
    "LangChain Docs",
    "https://python.langchain.com/docs",
    "Официальная документация — лучший старт для разработки агентов"
)
add_link_bullet(
    "CrewAI Docs",
    "https://docs.crewai.com",
    "Документация по CrewAI с примерами мульти-агентных систем"
)
add_link_bullet(
    "Курс AI Agents (DeepLearning.AI)",
    "https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/",
    "Бесплатный курс от Andrew Ng по агентам на LangGraph"
)
add_link_bullet(
    "Building LLM Applications (Hugging Face)",
    "https://huggingface.co/learn/cookbook/en/index",
    "Практические рецепты — RAG, агенты, fine-tuning"
)
add_link_bullet(
    "Anthropic Agent Patterns",
    "https://www.anthropic.com/research/building-effective-agents",
    "Официальное руководство Anthropic по паттернам агентов"
)
doc.add_paragraph()

add_heading("Продвинутые концепции", 3)
add_para("RAG (Retrieval-Augmented Generation):", bold=True)
add_para("Агент работает с твоей базой знаний — документами, сайтами, базами данных. Отвечает на вопросы используя твои данные.")
doc.add_paragraph()

add_para("Multi-agent systems:", bold=True)
add_para("Несколько агентов работают вместе: один ищет, другой анализирует, третий пишет отчёт. Каждый специализирован.")
doc.add_paragraph()

add_para("Tool use / Function calling:", bold=True)
add_para("Агент умеет вызывать функции: запустить поиск, отправить письмо, записать в базу данных, выполнить код.")
doc.add_paragraph()

add_heading("✏️ Практические задания", 3)
add_bullet("Настрой Dify — создай агента который отвечает на вопросы по загруженным документам (RAG)")
add_bullet("Сделай агента на CrewAI: 1й агент ищет вакансии, 2й анализирует, 3й пишет отклик")
add_bullet("Создай агента который мониторит конкурентов — раз в день проверяет их сайты и присылает дайджест")
add_bullet("Построй мульти-агентную систему для автоматического исследования рынка")

doc.add_page_break()

# ══════════════════════════════════════════════════════════════════════════════
# ДОПОЛНИТЕЛЬНО
# ══════════════════════════════════════════════════════════════════════════════

add_heading("Дополнительные ресурсы", 1)

add_heading("YouTube каналы обязательные к подписке", 2)
add_table(
    ["Канал", "Тематика", "Аудитория"],
    [
        ["Matt Wolfe (@mreflow)", "Обзоры всех новых AI инструментов", "Широкая"],
        ["David Ondrej (@DavidOndrej)", "AI-агенты, автоматизация, практика", "Продвинутая"],
        ["AI Jason (@AIJasonZ)", "Агенты, no-code, кейсы", "Средняя"],
        ["Cole Medin (@ColeMedin)", "n8n, LangChain, агенты", "Продвинутая"],
        ["Fireship (@Fireship)", "Технические объяснения за 100 секунд", "Техническая"],
        ["Two Minute Papers", "Обзоры научных статей по AI", "Академическая"],
    ]
)
doc.add_paragraph()

add_heading("Telegram каналы", 2)
add_table(
    ["Канал", "О чём"],
    [
        ["@ai_newz", "Новости AI на русском, ежедневно"],
        ["@aitoolsclub", "Новые AI инструменты — первым узнаёшь"],
        ["@openai_ru", "OpenAI новости на русском"],
        ["@langchain_ai", "LangChain обновления (eng)"],
        ["@midjourney_ru", "Midjourney советы и примеры"],
        ["@n8n_ru", "n8n автоматизация на русском"],
    ]
)
doc.add_paragraph()

add_heading("Полезные сайты", 2)
add_link_bullet("There's An AI For That", "https://theresanaiforthat.com", "База всех AI инструментов — найди нужный")
add_link_bullet("Futurepedia", "https://www.futurepedia.io", "Каталог AI инструментов с рейтингами")
add_link_bullet("Hugging Face", "https://huggingface.co", "Главная платформа для AI моделей и демо")
add_link_bullet("Papers With Code", "https://paperswithcode.com", "Научные статьи + код — следи за трендами")
add_link_bullet("AI Valley Discord", "https://discord.gg/aitools", "Комьюнити по AI инструментам")

doc.add_page_break()

add_heading("Финальный чеклист", 1)
add_para("После прохождения всех модулей ты должен уметь:", bold=True, size=12)
doc.add_paragraph()

checkpoints = [
    ("Модуль 1", [
        "Писать промпты которые дают нужный результат с первого раза",
        "Использовать Chain-of-Thought для сложных задач",
        "Применять Few-shot для точного формата вывода",
    ]),
    ("Модуль 2", [
        "Генерировать изображения для маркетинга и презентаций",
        "Управлять стилем, форматом и деталями изображения",
        "Использовать минимум 2 генератора изображений",
    ]),
    ("Модуль 3", [
        "Создавать видеоролики из текста или изображений",
        "Клонировать голос и озвучивать тексты",
        "Делать видео с AI-аватаром",
    ]),
    ("Модуль 4", [
        "Настроить базовый сценарий автоматизации в n8n или Make",
        "Создать AI-бота который отвечает на вопросы",
        "Автоматизировать хотя бы одну рабочую задачу",
    ]),
    ("Модуль 5", [
        "Понимать архитектуру AI-агентов",
        "Настроить агента на Dify (no-code)",
        "Создать мульти-агентную систему для реальной задачи",
    ]),
]

for module, items in checkpoints:
    add_para(module + ":", bold=True)
    for item in items:
        add_bullet("☐  " + item)
    doc.add_paragraph()

doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Удачи! Мир уже никогда не будет прежним 🚀")
r.bold = True
r.font.size = Pt(14)
r.font.color.rgb = RGBColor(26, 115, 232)

# Сохранить
out = "/home/clawdbot/.openclaw/workspace/drafts/AI_Course_v1.docx"
doc.save(out)
print(f"Saved: {out}")
