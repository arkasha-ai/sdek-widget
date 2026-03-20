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

def shade_cell(cell, hex_color):
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), hex_color)
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:val'), 'clear')
    tcPr.append(shd)

def add_heading(text, level=1, emoji=""):
    colors = {1: (30, 30, 30), 2: (40, 80, 160), 3: (60, 100, 180)}
    sizes = {1: 20, 2: 16, 3: 13}
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16 if level == 1 else 10)
    p.paragraph_format.space_after = Pt(6)
    run = p.add_run((emoji + " " + text).strip())
    run.font.size = Pt(sizes.get(level, 12))
    run.font.bold = True
    run.font.color.rgb = RGBColor(*colors.get(level, (0,0,0)))
    return p

def add_body(text, bold=False, italic=False, color=None):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(text)
    run.font.size = Pt(11)
    run.font.bold = bold
    run.font.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    return p

def add_bullet(text, level=0):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8 + level * 0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    run = p.add_run("•  " + text)
    run.font.size = Pt(11)
    return p

def add_tip(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run("📹  " + text)
    run.font.size = Pt(10)
    run.font.bold = True
    run.font.color.rgb = RGBColor(180, 60, 60)

def add_divider():
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    p.paragraph_format.space_after = Pt(8)
    run = p.add_run("─" * 80)
    run.font.size = Pt(8)
    run.font.color.rgb = RGBColor(200, 200, 200)

def add_tool_table(tools):
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
    for tool in tools:
        row = table.add_row().cells
        for i, val in enumerate(tool):
            row[i].text = val
            row[i].paragraphs[0].runs[0].font.size = Pt(10)
    doc.add_paragraph()

def add_videos(videos):
    for v in videos:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run("🎥  " + v)
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(180, 50, 50)

def add_articles(articles):
    for a in articles:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.5)
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        run = p.add_run("📖  " + a)
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(50, 130, 50)

def add_task(num, text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.8)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    run = p.add_run(f"{num}.  {text}")
    run.font.size = Pt(11)
    if "(Продвинутое)" in text:
        run.font.color.rgb = RGBColor(150, 50, 200)

# ===== ОБЛОЖКА =====
p = doc.add_paragraph()
p.paragraph_format.space_before = Pt(30)
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("🤖  AI с нуля до агентов")
run.font.size = Pt(28)
run.font.bold = True
run.font.color.rgb = RGBColor(30, 80, 180)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run("Практический курс: от первого промпта до собственного AI-агента")
run2.font.size = Pt(14)
run2.font.italic = True
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
    r1 = p.add_run(label + "  ")
    r1.bold = True
    r1.font.size = Pt(11)
    r2 = p.add_run(val)
    r2.font.size = Pt(11)

add_divider()

# ===== ПЛАН НА 3 МЕСЯЦА =====
add_heading("ПЛАН НА 3 МЕСЯЦА", 1, "📅")
plan_table = doc.add_table(rows=1, cols=3)
plan_table.style = 'Table Grid'
hdr = plan_table.rows[0].cells
for i, h in enumerate(["Неделя", "Фокус", "Ежедневно"]):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True
    hdr[i].paragraphs[0].runs[0].font.size = Pt(10)
    hdr[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    shade_cell(hdr[i], '2E5090')
for week, focus, daily in [
    ("1–2", "Промптинг: ChatGPT, Claude, техники, GPTs", "30 мин"),
    ("3", "Изображения: Leonardo.ai, Midjourney, DALL-E", "45 мин"),
    ("4–5", "Видео: Kling AI, ElevenLabs, Runway, HeyGen", "45 мин"),
    ("6–8", "Автоматизация: Make, n8n, Telegram-бот с AI", "60 мин"),
    ("9–12", "AI-агенты: Dify, Flowise, CrewAI, RAG", "60 мин"),
]:
    row = plan_table.add_row().cells
    for i, v in enumerate([week, focus, daily]):
        row[i].text = v
        row[i].paragraphs[0].runs[0].font.size = Pt(10)
doc.add_paragraph()
add_divider()

# ===== МОДУЛЬ 1 =====
doc.add_page_break()
add_heading("МОДУЛЬ 1  —  Промптинг", 1, "📍")
p = doc.add_paragraph()
p.add_run("⏱ 1-2 недели  |  Сложность: ⭐☆☆☆☆").font.size = Pt(10)
p.runs[0].italic = True
p.runs[0].font.color.rgb = RGBColor(120, 120, 120)

add_heading("Что это и зачем", 3)
add_body("Промпт — это инструкция для нейросети. От промпта зависит 80% качества ответа: одна и та же модель на плохой вопрос даст плохой ответ, а на хорошо сформулированный — отличный.")
add_body("Промптинг — навык, который прокачивается за 1-2 недели практики и остаётся с вами навсегда. Главное заблуждение новичков: «ChatGPT тупой». На самом деле — просто нужно научиться правильно с ним разговаривать. Это как Google: умеешь формулировать запрос — находишь что нужно.")

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("ChatGPT\nchat.openai.com", "Универсальный старт, самый популярный", "Бесплатно / $20/мес"),
    ("Claude\nclaude.ai", "Длинные тексты, анализ, рассуждения", "Бесплатно / $20/мес"),
    ("Gemini\ngemini.google.com", "Работа с файлами, интеграция с Google", "Бесплатно"),
    ("DeepSeek\nchat.deepseek.com", "Сильная модель, полностью бесплатно", "Бесплатно"),
    ("Perplexity\nperplexity.ai", "AI-поиск с источниками и ссылками", "Бесплатно / $20/мес"),
])

add_heading("Ключевые техники промптинга", 3)
for title, body, example in [
    ("1. Role prompting — задать роль",
     "Дай AI роль перед заданием — это кардинально меняет стиль и глубину ответа.",
     "Плохо: «Напиши резюме» | Хорошо: «Ты опытный HR-директор с 15 годами практики. Напиши резюме для Project Manager, который хочет перейти в продуктовую компанию...»"),
    ("2. Chain-of-Thought — пошаговое мышление",
     "Попроси AI думать вслух — повышает качество на сложных задачах.",
     "«Прежде чем ответить, разбери задачу пошагово: определи контекст → выяви проблему → предложи решение»"),
    ("3. Few-shot — примеры",
     "Покажи 2-3 примера того, что хочешь получить. AI подхватит формат и стиль.",
     ""),
    ("4. Structured output — структурированный вывод",
     "Просишь вернуть результат в таблице, JSON, нумерованном списке.",
     "«Верни ответ в виде таблицы с колонками: Задача / Срок / Ответственный»"),
    ("5. Итерация через диалог",
     "Не пытайся с первого промпта получить идеальный результат. Дорабатывай.",
     "«Хорошо, теперь сделай это более формально» / «Убери третий пункт и расширь второй»"),
    ("6. Контекст и ограничения",
     "Всегда давай контекст: кто аудитория, формат, ограничения.",
     "Плохо: «Напиши статью про AI» | Хорошо: «Напиши статью 800 слов про AI для предпринимателей без технического образования»"),
]:
    add_body(title, bold=True)
    add_body(body)
    if example:
        add_body(example, italic=True, color=(80, 80, 80))

add_heading("Интересные нюансы ChatGPT", 3)

add_body("Custom Instructions — настрой ChatGPT под себя", bold=True)
add_body("Settings → Personalization → Custom Instructions. Пишешь один раз кто ты и как хочешь получать ответы — каждый новый чат уже знает контекст без лишних объяснений.")

add_body("Память (Memory)", bold=True)
add_body("ChatGPT Plus запоминает информацию между сессиями. Скажи: «Запомни, что я Project Manager в IT-компании» — он будет учитывать это во всех будущих чатах.")

add_body("GPTs — персональные мини-агенты внутри ChatGPT", bold=True)
add_body("В ChatGPT Plus есть Explore GPTs — специализированные боты под конкретные задачи: Canva (дизайн), Consensus (научные статьи), Code Interpreter (анализ данных). Можно создать своего GPT под любую задачу.")

add_body("Анализ файлов в ChatGPT", bold=True)
add_body("ChatGPT Plus умеет читать PDF, Excel, CSV — закидывай документы и задавай вопросы: «Найди в этом договоре все пункты про штрафные санкции» или «Проанализируй этот отчёт и выдели ключевые метрики».")

add_body("Голосовой режим", bold=True)
add_body("ChatGPT работает голосом — удобно для брейншторминга во время прогулки или вождения. Режим Advanced Voice в Plus-подписке поддерживает живой диалог с прерываниями.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    "ChatGPT полный курс для начинающих — YouTube: «ChatGPT промптинг для начинающих 2025»",
    "Канал Вастрик про AI — youtube.com/@vas3k (технологии понятным языком)",
    "Техники промптинга — YouTube: «промптинг ChatGPT техники 2025»",
    "GPTs как создать своего бота — YouTube: «GPTs создать ChatGPT русский 2025»",
    "ChatGPT для бизнеса — YouTube: «ChatGPT для бизнеса применение русский»",
])

add_heading("Статьи (русские)", 3)
add_articles([
    "Promptingguide.ai на русском — www.promptingguide.ai/ru (лучший бесплатный гайд)",
    "Habr: Искусство промптинга — habr.com, поиск «промптинг»",
    "VC.ru: ChatGPT для бизнеса — vc.ru, поиск «ChatGPT промптинг»",
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в ChatGPT, настрой Custom Instructions (кто ты и как хочешь ответы)")
add_task(2, "Напиши промпт который генерирует резюме под конкретную вакансию")
add_task(3, "Создай промпт для анализа документа — выделять ключевые риски")
add_task(4, "Найди 3 полезных GPT в Explore GPTs для своей работы")
add_task(5, "(Продвинутое) Создай собственного GPT под конкретную задачу")

add_divider()

# ===== МОДУЛЬ 2 =====
doc.add_page_break()
add_heading("МОДУЛЬ 2  —  Генерация изображений", 1, "🎨")
p = doc.add_paragraph()
p.add_run("⏱ 1 неделя  |  Сложность: ⭐⭐☆☆☆").font.size = Pt(10)
p.runs[0].italic = True
p.runs[0].font.color.rgb = RGBColor(120, 120, 120)

add_heading("Что это и зачем", 3)
add_body("Ты описываешь картинку текстом — нейросеть генерирует её за секунды. Качество уже на уровне профессионального дизайнера для большинства задач. То, что раньше стоило $200 у фотографа, сейчас делается за 5 минут.")
add_body("Используется для: маркетинга, презентаций, концепт-артов, аватаров, рекламных баннеров, иллюстраций для статей и курсов.")

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("Midjourney\nmidjourney.com", "Лучшее художественное качество", "от $10/мес"),
    ("DALL-E 3 (в ChatGPT)", "Встроен в ChatGPT Plus, удобно", "Входит в $20/мес"),
    ("Leonardo.ai\nleonardo.ai", "Много бесплатных кредитов, вариативность", "Бесплатно / $12/мес"),
    ("Adobe Firefly\nfirefly.adobe.com", "Безопасно для коммерческого использования", "Бесплатно / от $5/мес"),
    ("Kandinsky\nfusionbrain.ai", "Российский сервис, полностью бесплатно", "Бесплатно"),
    ("Шедеврум\nshedevrum.ai", "Яндекс, русскоязычный интерфейс", "Бесплатно"),
])

add_heading("Ключевые техники", 3)
add_body("Структура хорошего промпта для изображений:", bold=True)
add_body("[Объект/сцена] + [стиль] + [свет/атмосфера] + [детали] + [формат]")
add_body("Пример: «Деловой мужчина 35 лет, кофе на фоне панорамного окна офиса, фотореализм, мягкий утренний свет, LinkedIn аватар, портретная ориентация»", italic=True, color=(80, 80, 80))

add_body("Ключевые слова для стилей:", bold=True)
add_bullet("Реализм: photorealistic, 8K, DSLR, sharp focus")
add_bullet("Минимализм: minimalist, flat design, clean lines, white background")
add_bullet("Кинематограф: cinematic, movie still, film grain, dramatic lighting")
add_bullet("Бизнес: professional, corporate, clean, modern")

add_body("Negative prompts — что убрать:", bold=True)
add_body("Добавь в конце запроса что НЕ должно быть. Midjourney: --no text, watermark, blurry, cartoon. Другие сервисы: поле «Negative prompt» в настройках.")

add_body("Reference image — пример за основу:", bold=True)
add_body("Загрузи фото как пример и скажи «Сгенерируй в этом же стиле» или «Создай похожий образ в деловой обстановке».")

add_body("Inpainting — редактирование части:", bold=True)
add_body("Выделяешь нужную область (фон, одежду, лицо) и говоришь что там должно быть. Остальное остаётся нетронутым. Есть в Midjourney и Leonardo.")

add_heading("Интересные нюансы", 3)

add_body("FLUX.1 — новый лидер качества реализма", bold=True)
add_body("В 2024 году вышел FLUX.1 от Black Forest Labs — по фотореализму обогнал Midjourney. Доступен в Leonardo.ai. Отлично работает для деловых портретов и продуктовых рендеров.")

add_body("Lora-модели в Leonardo.ai", bold=True)
add_body("Специализированные «насадки» на основную модель для конкретных стилей (аниме, реализм, архитектура). Выбираешь Lora → качество в нужном стиле резко растёт.")

add_body("Консистентность персонажа", bold=True)
add_body("Проблема: каждый раз новое лицо. Решения: Midjourney --cref (character reference) или Leonardo Character Reference — позволяют «закрепить» внешность персонажа между генерациями.")

add_body("ControlNet — точный контроль позы", bold=True)
add_body("В Stable Diffusion есть ControlNet — берёшь скелет позы из одного фото и «одеваешь» его в нужный стиль. Профессиональный инструмент для точного контроля позы и композиции.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    "Midjourney полный гайд — YouTube: «Midjourney гайд русский 2025»",
    "Leonardo.ai бесплатно — YouTube: «Leonardo ai туториал русский»",
    "DALL-E 3 в ChatGPT — YouTube: «DALL-E 3 ChatGPT русский туториал»",
    "Как создать AI аватар — YouTube: «AI аватар генерация 2025 русский»",
    "Шедеврум и Kandinsky — YouTube: «Шедеврум kandinsky туториал»",
    "FLUX.1 обзор — YouTube: «FLUX модель генерация изображений русский»",
])

add_heading("Статьи (русские)", 3)
add_articles([
    "Habr: Сравнение AI-генераторов — habr.com, поиск «генерация изображений AI 2025»",
    "VC.ru: AI для дизайна — vc.ru, поиск «AI дизайн генерация»",
    "Civitai.com — тысячи готовых промптов и моделей (английский, но с картинками всё понятно)",
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в Leonardo.ai (бесплатно), сгенерируй 10 вариантов — почувствуй промпты")
add_task(2, "Создай деловой аватар для LinkedIn или Telegram")
add_task(3, "Сгенерируй 5 вариантов баннера для своего проекта или услуги")
add_task(4, "Один запрос в DALL-E, Leonardo и Kandinsky — сравни результат")
add_task(5, "(Продвинутое) Midjourney: создай иллюстрацию с character reference для консистентного персонажа")

add_divider()

# ===== МОДУЛЬ 3 =====
doc.add_page_break()
add_heading("МОДУЛЬ 3  —  Генерация видео и голоса", 1, "🎬")
p = doc.add_paragraph()
p.add_run("⏱ 1-2 недели  |  Сложность: ⭐⭐⭐☆☆").font.size = Pt(10)
p.runs[0].italic = True
p.runs[0].font.color.rgb = RGBColor(120, 120, 120)

add_heading("Что это и зачем", 3)
add_body("Самый быстро развивающийся сегмент AI. Год назад AI-видео было игрушкой — сейчас серьёзный рабочий инструмент. Можно создавать видео для YouTube, рекламу, обучающий контент, дубляж на 40+ языков — без оператора, студии и даже без своего лица в кадре.")

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("Runway Gen-3\nrunwayml.com", "Text/Image-to-Video, топ качество", "$15/мес"),
    ("Kling AI\nklingai.com", "Сильный конкурент Runway, бесплатный план", "Бесплатно / $10/мес"),
    ("Sora\nsora.com", "Видео от OpenAI, длинные ролики", "$20/мес (ChatGPT Plus)"),
    ("HeyGen\nheygen.com", "Видео-аватары, перевод видео с дубляжом", "$29/мес"),
    ("ElevenLabs\nelevenlabs.io", "Клонирование голоса, Text-to-Speech", "Бесплатно / $5/мес"),
    ("Luma Dream Machine\nlumalabs.ai", "Видео из фото, плавная анимация", "Бесплатно (лимиты)"),
    ("Descript\ndescript.com", "Монтаж видео через редактирование текста", "Бесплатно / $12/мес"),
    ("CapCut AI\ncapcut.com", "Монтаж + AI субтитры и эффекты", "Бесплатно"),
])

add_heading("Ключевые техники", 3)

add_body("Text-to-Video — структура промпта:", bold=True)
add_body("[Что происходит] + [обстановка] + [стиль съёмки] + [движение камеры] + [атмосфера]")
add_body("Пример: «Деловая женщина идёт по ночному городу под дождём, неоновые огни отражаются в лужах, замедленная съёмка, кинематографический стиль, 4K»", italic=True, color=(80, 80, 80))

add_body("Движение камеры — ключевые термины:", bold=True)
add_bullet("slow zoom in — медленный наезд (создаёт напряжение)")
add_bullet("dolly shot — камера движется вдоль сцены")
add_bullet("panning left/right — панорамирование")
add_bullet("bird's eye view — вид сверху, аэросъёмка")
add_bullet("close-up — крупный план лица или объекта")

add_body("Voice Cloning в ElevenLabs:", bold=True)
add_body("1. Записываешь 1-2 минуты своего голоса  →  2. ElevenLabs клонирует  →  3. Вводишь любой текст  →  4. Получаешь озвучку своим голосом. Используй для подкастов, обучающих видео, рекламы.")

add_heading("Интересные нюансы", 3)

add_body("Аватары HeyGen — цифровой двойник без камеры", bold=True)
add_body("HeyGen позволяет создать видео-аватара: записываешь 2-5 минут видео с нейтральным выражением → HeyGen обучает модель → теперь вводишь текст и получаешь видео, где «ты» говоришь его. Используется для корпоративных видео, онлайн-курсов, персонализированных сообщений клиентам.")
add_tip("Смотри как создать аватар HeyGen: YouTube → «HeyGen аватар создать пошагово русский 2025»")

add_body("Video Translation — дубляж без студии", bold=True)
add_body("HeyGen и ElevenLabs умеют полностью дублировать видео: распознают речь → переводят → озвучивают клонированным голосом с синхронизацией губ. 40+ языков. Идеально для международного контента.")

add_body("Descript — монтаж через текст", bold=True)
add_body("Descript транскрибирует видео → ты редактируешь текст → видео автоматически монтируется. Удалил слово из текста — сцена исчезла. Революция в монтаже для нетехнарей.")

add_body("CapCut AI — бесплатный монтаж с AI-магией", bold=True)
add_body("CapCut встроил AI-функции: автоматические субтитры, удаление фона, умный монтаж под музыку, автоматические эффекты. Для коротких видео (Reels, TikTok, Shorts) — этого хватает без платных подписок.")

add_body("Image-to-Video — оживи фотографию", bold=True)
add_body("Загружаешь фото → указываешь что должно двигаться → получаешь 4-8 секунд видео. Работает в Runway, Kling AI, Luma. Отлично для рекламы и «оживления» статичного контента.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    "Runway Gen-3 AI-видео — YouTube: «Runway Gen 3 туториал русский 2025»",
    "ElevenLabs клонирование голоса — YouTube: «ElevenLabs клонирование голоса русский»",
    "HeyGen создание аватара — YouTube: «HeyGen аватар создать русский 2025»",
    "Kling AI бесплатная генерация видео — YouTube: «Kling AI туториал русский»",
    "CapCut AI монтаж для начинающих — YouTube: «CapCut AI монтаж туториал русский»",
    "Sora от OpenAI обзор — YouTube: «Sora OpenAI обзор русский»",
    "AI дубляж видео на русском — YouTube: «AI дубляж перевод видео HeyGen русский»",
])

add_heading("Статьи (русские)", 3)
add_articles([
    "Habr: AI-видеогенерация 2025 — habr.com, поиск «генерация видео AI»",
    "VC.ru: Как бизнес использует AI-видео — vc.ru, поиск «AI видео бизнес»",
    "DTF: Обзоры AI-инструментов — dtf.ru, поиск «AI видео»",
])

add_heading("Практические задания", 3)
add_task(1, "Создай 15-секундный ролик через Kling AI (бесплатно) — текст или фото в видео")
add_task(2, "Зарегистрируйся в ElevenLabs, озвучь любой текст синтезированным голосом")
add_task(3, "Запиши 1 минуту своего голоса → создай клон → озвучь им новый текст")
add_task(4, "(Продвинутое) Создай аватар в HeyGen — снимай обращение без камеры")
add_task(5, "(Продвинутое) Попробуй Descript: загрузи видео и отредактируй через текст")

add_divider()

# ===== МОДУЛЬ 4 =====
doc.add_page_break()
add_heading("МОДУЛЬ 4  —  Автоматизация без кода", 1, "⚙️")
p = doc.add_paragraph()
p.add_run("⏱ 2-3 недели  |  Сложность: ⭐⭐⭐☆☆").font.size = Pt(10)
p.runs[0].italic = True
p.runs[0].font.color.rgb = RGBColor(120, 120, 120)

add_heading("Что это и зачем", 3)
add_body("Автоматизация — это когда разные сервисы работают друг с другом без твоего участия. Добавляешь AI — получаешь умную систему: письмо пришло → AI классифицировал → создал задачу → уведомил команду → записал в CRM.")
add_body("Это не программирование. Ты соединяешь блоки в визуальном редакторе, как в конструкторе. Порог входа — несколько часов практики.")

add_body("Что можно автоматизировать уже сейчас:", bold=True)
for item in [
    "Обработка входящих писем с AI-ответами",
    "Публикация контента в соцсети по расписанию",
    "Мониторинг вакансий и упоминаний бренда",
    "CRM + AI = автоматические follow-up сообщения клиентам",
    "Сбор и анализ данных из разных источников",
    "Еженедельные отчёты без участия человека",
]:
    add_bullet(item)

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("n8n\nn8n.io", "Open-source, лучший для AI-автоматизаций, self-hosted", "Бесплатно / $20/мес"),
    ("Make\nmake.com", "Визуальные сценарии, проще n8n, идеален для старта", "Бесплатно / $9/мес"),
    ("Zapier\nzapier.com", "Много готовых интеграций, самый популярный", "$20/мес"),
    ("Voiceflow\nvoiceflow.com", "No-code AI чат-боты с памятью", "Бесплатно / $40/мес"),
    ("Botpress\nbotpress.com", "AI боты с аналитикой и кастомизацией", "Бесплатно / $49/мес"),
])

add_heading("Пример сценария в Make/n8n", 3)
add_body("Триггер → Обработка → AI → Действие → Результат", bold=True)
for step in [
    "Новое письмо на Gmail поступило (триггер)",
    "Отправить содержимое в ChatGPT: «Классифицируй письмо и напиши краткое резюме»",
    "Создать задачу в Notion с текстом резюме от AI",
    "Отправить уведомление в Telegram с результатом",
]:
    add_bullet(step)
add_body("В Make и n8n это выглядит как схема из блоков, соединённых стрелками. Каждый блок настраивается отдельно через понятный интерфейс.")

add_heading("Интересные нюансы", 3)

add_body("n8n vs Make — что выбрать для старта?", bold=True)
add_body("Make — проще и нагляднее, идеален для начала. n8n — мощнее и гибче, можно развернуть на своём сервере бесплатно, лучше для AI-агентов. Рекомендация: начни с Make, потом переходи на n8n.")

add_body("AI Agent нода в n8n", bold=True)
add_body("n8n имеет встроенную ноду «AI Agent» — создаёшь полноценного агента с инструментами (поиск, файлы, API) и памятью прямо в визуальном редакторе. Без единой строки кода.")

add_body("Telegram-бот за 15 минут", bold=True)
add_body("Make/n8n + Telegram Bot API = полноценный бот без программирования. Получает сообщения → передаёт в ChatGPT → отвечает. Реальный рабочий кейс буквально за 15 минут.")

add_body("Шаблоны — не изобретай велосипед", bold=True)
add_body("У n8n и Make есть библиотеки готовых шаблонов — поищи нужный сценарий, чаще всего он уже сделан. Остаётся только настроить под свои данные.")

add_body("Webhook — как события запускают сценарий", bold=True)
add_body("Webhook — URL-адрес который «ловит» события. Telegram отправил сообщение → webhook сработал → сценарий запустился. Самый распространённый тип триггера в автоматизации.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    "n8n для начинающих первый сценарий — YouTube: «n8n туториал русский начинающий 2025»",
    "Make.com автоматизация без кода — YouTube: «Make com автоматизация русский»",
    "Telegram-бот без программирования — YouTube: «Telegram бот n8n make без кода»",
    "AI автоматизация бизнеса кейсы — YouTube: «AI автоматизация бизнес n8n 2025 русский»",
    "Zapier vs Make сравнение — YouTube: «Zapier vs Make сравнение русский»",
])

add_heading("Статьи (русские)", 3)
add_articles([
    "Habr: Автоматизация с n8n — habr.com, поиск «n8n автоматизация»",
    "VC.ru: Как автоматизировать бизнес с AI — vc.ru, поиск «автоматизация AI бизнес»",
    "Tproger: Инструменты автоматизации — tproger.ru, поиск «автоматизация»",
])

add_heading("Практические задания", 3)
add_task(1, "Зарегистрируйся в Make.com, пройди официальный tutorial (30 мин)")
add_task(2, "Создай первый сценарий: новое письмо на Gmail → уведомление в Telegram")
add_task(3, "Добавь AI: письмо → ChatGPT пишет краткое резюме → Telegram с резюме")
add_task(4, "Создай Telegram-бота который отвечает на вопросы с помощью ChatGPT")
add_task(5, "(Продвинутое) n8n AI Agent: бот который ищет информацию в интернете по запросу")

add_divider()

# ===== МОДУЛЬ 5 =====
doc.add_page_break()
add_heading("МОДУЛЬ 5  —  AI-агенты", 1, "🤖")
p = doc.add_paragraph()
p.add_run("⏱ 1-2 месяца  |  Сложность: ⭐⭐⭐⭐☆").font.size = Pt(10)
p.runs[0].italic = True
p.runs[0].font.color.rgb = RGBColor(120, 120, 120)

add_heading("Что это и зачем", 3)
add_body("Агент — это AI который не просто отвечает на вопрос, а действует. Он получает задачу, сам планирует шаги, использует инструменты (браузер, файлы, API, код), проверяет результаты и итерирует пока не достигнет цели.")
add_body("Разница: обычный ChatGPT — консультант, говорит что делать. Агент — исполнитель, который сам идёт и делает.")

add_body("Примеры задач для агентов:", bold=True)
for item in [
    "«Найди топ-10 конкурентов в моей нише, проанализируй их сайты и составь отчёт»",
    "«Мониторь вакансии каждый день, отбирай подходящие и присылай подборку»",
    "«Просматривай мои письма, отвечай на типовые, важные — пересылай мне»",
    "«Собери данные из 20 источников, структурируй и сделай сводку»",
]:
    add_bullet(item)

add_heading("Инструменты модуля", 3)
add_tool_table([
    ("Dify\ndify.ai", "No-code AI агенты и пайплайны, лучший старт", "Бесплатно / $59/мес"),
    ("Flowise\nflowiseai.com", "Визуальный конструктор агентов, self-hosted", "Бесплатно"),
    ("n8n AI Agent\nn8n.io", "Агент в визуальном редакторе без кода", "Бесплатно / $20/мес"),
    ("CrewAI\ncrewai.com", "Мульти-агентные системы (Python)", "Бесплатно (open source)"),
    ("LangChain\npython.langchain.com", "Мощный фреймворк для агентов (Python)", "Бесплатно (open source)"),
    ("OpenAI Assistants\nplatform.openai.com", "Встроенные агенты OpenAI через API", "Pay per use"),
])

add_heading("Архитектура агента", 3)
add_body("Ключевые компоненты:", bold=True)
for comp in [
    "LLM (мозг) — GPT-4, Claude, Gemini — думает и принимает решения",
    "Tools (инструменты) — браузер, поиск, файлы, API, написание и выполнение кода",
    "Memory (память) — краткосрочная (в контексте) и долгосрочная (в базе данных)",
    "Planning (планирование) — разбивает большую задачу на шаги",
    "Reflection (рефлексия) — проверяет свои результаты и улучшает их",
]:
    add_bullet(comp)

add_body("Цикл работы:", bold=True)
add_body("Задача → Планирование → Выбор инструмента → Действие → Оценка результата → Следующий шаг → (Результат когда цель достигнута)")

add_heading("Интересные нюансы", 3)

add_body("RAG — агент со своей базой знаний", bold=True)
add_body("RAG (Retrieval-Augmented Generation) — агент, который ищет в своих документах перед ответом. Загружаешь в Dify свои договора, FAQ, регламенты → агент отвечает, опираясь на них. Не «выдумывает» — достаёт конкретные данные из твоих файлов.")

add_body("Мульти-агентные системы в CrewAI", bold=True)
add_body("Несколько специализированных агентов работают вместе. Пример команды: Researcher (ищет информацию) + Analyst (анализирует и структурирует) + Writer (пишет финальный отчёт). Каждый делает своё, результат складывается автоматически.")

add_body("Встроенные агенты в ChatGPT Plus", bold=True)
for item in [
    "Advanced Data Analysis — пишет и выполняет код, анализирует Excel/CSV файлы прямо в чате",
    "Browsing — заходит в интернет, читает актуальные страницы",
    "DALL-E — рисует изображения прямо в диалоге",
]:
    add_bullet(item)
add_body("ChatGPT сам решает какой агент использовать — они активируются автоматически.")

add_body("Computer Use — агент управляет компьютером", bold=True)
add_body("Anthropic выпустил Claude с функцией Computer Use: агент управляет мышью и клавиатурой, заходит на сайты, заполняет формы. Следующий уровень автоматизации.")

add_body("Ограничения агентов — важно знать", bold=True)
add_body("Агенты ошибаются, особенно на сложных многошаговых задачах. Нельзя давать агенту доступ к критическим системам без надзора. Лучшая практика: начинай с тестовой «песочницы», агент предлагает действие — ты одобряешь.")

add_heading("Видео для изучения (русские)", 3)
add_videos([
    "AI-агенты что это простое объяснение — YouTube: «AI агенты что это объяснение русский 2025»",
    "Dify создание агента без кода — YouTube: «Dify AI агент туториал русский»",
    "Flowise визуальный конструктор — YouTube: «Flowise туториал русский»",
    "RAG агент с базой знаний — YouTube: «RAG база знаний AI агент русский»",
    "n8n AI Agent нода — YouTube: «n8n AI agent туториал русский»",
    "CrewAI мультиагентная система — YouTube: «CrewAI туториал русский»",
])

add_heading("Статьи (русские)", 3)
add_articles([
    "Habr: AI-агенты введение — habr.com, поиск «AI агенты»",
    "Habr: LangChain на практике — habr.com, поиск «LangChain»",
    "VC.ru: Агенты в бизнесе — vc.ru, поиск «AI агенты бизнес»",
])

add_heading("Практические задания", 3)
add_task(1, "Разберись с Dify: создай простого агента с инструментом поиска в интернете")
add_task(2, "Настрой RAG: загрузи свои документы в Dify, создай чат-бота по ним")
add_task(3, "Создай агента в n8n AI Agent: получает запрос → ищет → структурированно отвечает")
add_task(4, "(Продвинутое) CrewAI: система из 3 агентов — Researcher + Analyst + Writer")
add_task(5, "(Продвинутое) Агент-мониторинг: каждый день следит за чем-то важным для тебя")

add_divider()

# ===== TELEGRAM-КАНАЛЫ =====
add_heading("Telegram-каналы — оставаться в курсе", 2, "📱")
tg_table = doc.add_table(rows=1, cols=2)
tg_table.style = 'Table Grid'
hdr = tg_table.rows[0].cells
for i, h in enumerate(["Канал", "О чём"]):
    hdr[i].text = h
    hdr[i].paragraphs[0].runs[0].bold = True
    hdr[i].paragraphs[0].runs[0].font.size = Pt(10)
    hdr[i].paragraphs[0].runs[0].font.color.rgb = RGBColor(255, 255, 255)
    shade_cell(hdr[i], '2E5090')
for ch, desc in [
    ("@ai_newz", "Новости AI на русском"),
    ("@aitoolsclub", "Обзоры новых AI-инструментов"),
    ("@vas3k_club", "Вастрик про технологии"),
    ("@machinelearning_ru", "ML и AI по-русски"),
    ("@neural_networks_ru", "Нейросети для практиков"),
]:
    row = tg_table.add_row().cells
    for i, v in enumerate([ch, desc]):
        row[i].text = v
        row[i].paragraphs[0].runs[0].font.size = Pt(10)
doc.add_paragraph()

add_divider()

# ===== ПРИНЦИПЫ ОБУЧЕНИЯ =====
add_heading("Принципы быстрого обучения", 2, "💡")
for num, principle, detail in [
    ("1", "Сразу на практике", "Не читай всё подряд — пробуй руками после каждой темы"),
    ("2", "Один инструмент → один реальный проект", "Не распыляйся на 10 инструментов одновременно"),
    ("3", "Документируй что работает", "Веди свою базу промптов хотя бы в Notion или заметках"),
    ("4", "Учись на кейсах", "Ищи «как сделали X с помощью AI» на YouTube и Habr"),
    ("5", "Комьюнити", "Вопросы в Telegram-чатах закрывают пробелы за часы, не дни"),
    ("6", "Принцип минимального инструмента", "Для каждой задачи — самый простой инструмент который справляется"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(4)
    r1 = p.add_run(f"{num}. {principle}  — ")
    r1.bold = True
    r1.font.size = Pt(11)
    r2 = p.add_run(detail)
    r2.font.size = Pt(11)

add_divider()

# ===== ПРИЛОЖЕНИЕ =====
doc.add_page_break()
add_heading("ПРИЛОЖЕНИЕ", 1, "📚")
add_heading("Английские материалы для углублённого изучения", 2)
add_body("Английские источники опережают русскоязычные на 6-12 месяцев. Эти материалы — для тех, кто хочет быть на передовой и смотреть первоисточники.", italic=True)

add_heading("YouTube-каналы (English)", 3)
for channel, url, desc in [
    ("Matt Wolfe", "youtube.com/@mreflow", "AI новости, еженедельные обзоры инструментов"),
    ("AI Jason", "youtube.com/@AIJasonZ", "Агенты, автоматизация, n8n туториалы"),
    ("David Ondrej", "youtube.com/@DavidOndrej", "CrewAI, LangChain, мультиагентные системы"),
    ("Sam Witteveen", "youtube.com/@samwitteveenai", "LangChain, технические туториалы по агентам"),
    ("Two Minute Papers", "youtube.com/@TwoMinutePapers", "Доступные обзоры AI-исследований"),
    ("Andrej Karpathy", "youtube.com/@AndrejKarpathy", "Глубокое понимание нейросетей (ex-Tesla AI)"),
    ("Lex Fridman", "youtube.com/@lexfridman", "Длинные интервью с лидерами AI"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(3)
    p.paragraph_format.space_after = Pt(3)
    r1 = p.add_run(f"▶  {channel}  ({url})  — ")
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(200, 50, 50)
    r2 = p.add_run(desc)
    r2.font.size = Pt(10)

add_heading("Сайты и документация (English)", 3)
for url, desc in [
    ("promptingguide.ai", "Лучший гайд по промптингу"),
    ("learnprompting.org", "Интерактивные уроки промптинга"),
    ("python.langchain.com/docs", "Документация LangChain"),
    ("docs.crewai.com", "Документация CrewAI"),
    ("docs.n8n.io", "Полная документация n8n"),
    ("theresanaiforthat.com", "Каталог всех AI-инструментов"),
    ("openai.com/blog", "Официальный блог OpenAI"),
    ("anthropic.com/research", "Исследования создателей Claude"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r1 = p.add_run(f"📖  {url}  — ")
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(50, 130, 50)
    r2 = p.add_run(desc)
    r2.font.size = Pt(10)

add_heading("Видео по конкретным темам (English)", 3)
for title, search in [
    ("LangChain Crash Course 2025", "YouTube: LangChain crash course 2025"),
    ("Build AI Agents with n8n", "YouTube: n8n AI agent 2025"),
    ("CrewAI Tutorial", "YouTube: CrewAI tutorial 2025"),
    ("Midjourney Full Course", "YouTube: Midjourney full course 2025"),
    ("ElevenLabs Full Guide", "YouTube: ElevenLabs full guide 2025"),
    ("HeyGen Avatar Creation", "YouTube: HeyGen avatar creation tutorial 2025"),
    ("Runway Gen-3 Full Tutorial", "YouTube: Runway Gen 3 tutorial 2025"),
    ("Dify AI Agent Tutorial", "YouTube: Dify AI agent tutorial 2025"),
    ("AutoGen Multi-Agent", "YouTube: AutoGen multi-agent tutorial 2025"),
]:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(2)
    r1 = p.add_run(f"🎥  {title}  — ")
    r1.font.size = Pt(10)
    r1.font.bold = True
    r1.font.color.rgb = RGBColor(180, 50, 50)
    r2 = p.add_run(search)
    r2.font.size = Pt(10)
    r2.font.italic = True
    r2.font.color.rgb = RGBColor(100, 100, 100)

add_divider()

# ===== ФИНАЛ =====
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run("🚀  Удачи в обучении!")
run.font.size = Pt(14)
run.font.bold = True
run.font.color.rgb = RGBColor(30, 80, 180)

p2 = doc.add_paragraph()
p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
run2 = p2.add_run("AI меняется каждые 2-3 месяца — главное не останавливаться.")
run2.font.size = Pt(10)
run2.font.italic = True
run2.font.color.rgb = RGBColor(120, 120, 120)

p3 = doc.add_paragraph()
p3.alignment = WD_ALIGN_PARAGRAPH.CENTER
run3 = p3.add_run("Составлено: март 2026  |  Версия: 2.0")
run3.font.size = Pt(9)
run3.font.color.rgb = RGBColor(160, 160, 160)

doc.save('/home/clawdbot/.openclaw/workspace/drafts/AI_Course_v2.docx')
print("Done!")
