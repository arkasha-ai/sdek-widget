#!/usr/bin/env python3
from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

def set_margins(doc, top=2, bottom=2, left=2, right=2):
    section = doc.sections[0]
    section.page_width = Cm(21)    # A4
    section.page_height = Cm(29.7)
    section.top_margin = Cm(top)
    section.bottom_margin = Cm(bottom)
    section.left_margin = Cm(left)
    section.right_margin = Cm(right)

def add_bold_run(para, text):
    run = para.add_run(text)
    run.bold = True
    return run

def add_normal_run(para, text):
    return para.add_run(text)

def add_category_header(doc, text):
    p = doc.add_paragraph()
    run = add_bold_run(p, text)
    run.font.size = Pt(12)
    return p

def add_item(doc, number, text, lxi=None, signal=None):
    p = doc.add_paragraph(style='List Bullet')
    run = add_bold_run(p, f"{number}. ")
    run.font.size = Pt(11)
    
    # Split text by **
    parts = text.split('**')
    for i, part in enumerate(parts):
        if i % 2 == 0:
            run = add_normal_run(p, part)
            run.font.size = Pt(11)
        else:
            run = add_bold_run(p, part)
            run.font.size = Pt(11)
    
    if lxi:
        run = add_normal_run(p, f"\n   L×I: ")
        run = add_bold_run(p, lxi)
        run.font.size = Pt(10)
    
    if signal:
        run = add_normal_run(p, f" | Ранний сигнал: ")
        run = add_normal_run(p, signal)
        run.font.size = Pt(10)
    
    return p

def add_top_priority(doc, number, title, description):
    p = doc.add_paragraph()
    run = add_bold_run(p, f"{number}. ")
    run.font.size = Pt(11)
    
    # Title with **
    parts = title.split('**')
    for i, part in enumerate(parts):
        if i % 2 == 0:
            run = add_normal_run(p, part)
            run.font.size = Pt(11)
        else:
            run = add_bold_run(p, part)
            run.font.size = Pt(11)
    
    run = add_normal_run(p, f" → {description}")
    run.font.size = Pt(11)
    return p

# Create document
doc = Document()

# Set margins
set_margins(doc)

# Set default font
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

# Title
title = doc.add_heading('Pre-Mortem анализ: AI-агент для продаж и агитации', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.font.size = Pt(18)
    run.font.color.rgb = RGBColor(0, 0, 0)

# Subtitle
subtitle = doc.add_paragraph()
subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = subtitle.add_run('Гравити Групп · 02.04.2026')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(100, 100, 100)

doc.add_paragraph()

# ============ PLAN 1 ============
h1 = doc.add_heading('ПЛАН 1: AI-агент для продаж индор-рекламы', level=1)
for run in h1.runs:
    run.font.size = Pt(14)

# Scenario
scenario = doc.add_paragraph()
run = add_bold_run(scenario, 'Сценарий провала: ')
run.font.size = Pt(11)
run = add_normal_run(scenario, '"Октябрь 2026. Прошло 6 месяцев. Агент провалился. Почему?"')
run.font.size = Pt(11)

# Section: Причины провала
h2 = doc.add_heading('Причины провала', level=2)
for run in h2.runs:
    run.font.size = Pt(13)

# People
add_category_header(doc, '👥 Люди')

add_item(doc, 1, 'Клиент ожидал **"волшебную кнопку"** — не вовлекается в настройку скриптов', 'H/H', 'Не даёт материалы на старте')
add_item(doc, 2, 'Менеджер не обрабатывает лиды вовремя — воронка рвётся', 'H/H', 'Лиды копятся без реакции 48ч+')
add_item(doc, 3, 'У Гравити Групп нет экспертизы в индор-рекламе — скрипты generic', 'M/H', 'Первые 50 рассылок — 0 ответов')

# Process
add_category_header(doc, '⚙️ Процесс')

add_item(doc, 4, 'Нет чёткой метрики успеха — **"больше лидов"** без цифр', 'H/H', 'Через месяц спор "что считать результатом"')
add_item(doc, 5, 'Scope creep — **"добавьте WhatsApp, звонки, ретаргетинг"**', 'H/M', 'Новые хотелки каждую неделю')
add_item(doc, 6, 'Скрипты не итерируются — нет A/B тестов, response rate падает', 'M/H', 'Response rate падает 3 недели подряд')

# Tech
add_category_header(doc, '💻 Технологии')

add_item(doc, 7, 'Аккаунты банят за массовые рассылки (LinkedIn/FB/TenChat)', 'H/H', 'Первый бан аккаунта')
add_item(doc, 8, 'Интеграция с Битрикс24 — кривое API, дубли, поломки', 'M/H', 'Потерянные лиды в CRM')
add_item(doc, 9, 'AI галлюцинирует — шлёт неадекватные сообщения ЛПР', 'M/H', 'Жалоба от ЛПР или скриншот бреда')
add_item(doc, 10, 'Парсеры ломаются при обновлениях соцсетей', 'H/M', 'Парсер молча перестал находить контакты')

# External
add_category_header(doc, '🌍 Внешние факторы')

add_item(doc, 11, 'Ужесточение 152-ФЗ / штрафы за парсинг', 'M/H', 'Новости о штрафах за парсинг соцсетей')
add_item(doc, 12, 'Сезонность рынка — летом ЛПР не отвечают', 'M/M', 'Резкое падение response rate')

# TOP-3
doc.add_heading('ТОП-3 приоритета', level=2)

add_top_priority(doc, 1, '**Баны за спам**', 'Стратегия прогрева аккаунтов (LinkedIn: max 20 запросов/день, TG: прогрев 2 нед), пул аккаунтов, мониторинг. Заложить 1-2 мес на разгон.')
add_top_priority(doc, 2, '**Нет KPI**', 'В договор: response rate >3%, X лидов/мес, дашборд. Первый месяц — калибровка.')
add_top_priority(doc, 3, '**AI галлюцинации**', 'Human review первые 2 недели на всё, потом выборочный аудит 10%. Whitelist фраз.')

# Early warnings
doc.add_heading('Ранние сигналы предупреждения', level=2)
for item in ['Response rate ниже 1% после 200 отправок', 'Бан аккаунта в первую неделю', 'Клиент не даёт материалы 5+ дней', 'Жалоба от ЛПР на "спам"/"бота"']:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(item)
    run.font.size = Pt(11)

# Legal risks
doc.add_heading('Юридические риски (РФ)', level=2)
for item in ['152-ФЗ: парсинг ФИО+контактов из соцсетей — серая зона. Штрафы до 18 млн руб.', 'ФЗ-38 о рекламе: email без согласия = штраф 100-500 тыс на юрлицо.', 'ЛС в соцсетях — прямого запрета нет, но платформы банят.']:
    p = doc.add_paragraph(style='List Bullet')
    parts = item.split('**')
    for i, part in enumerate(parts):
        if i % 2 == 0:
            run = p.add_run(part)
            run.font.size = Pt(11)
        else:
            run = p.add_run(part)
            run.bold = True
            run.font.size = Pt(11)

p = doc.add_paragraph()
run = add_bold_run(p, 'Риск: ')
run.font.size = Pt(11)
run = add_normal_run(p, 'средний — управляемый при грамотном оформлении.')
run.font.size = Pt(11)

# Reputation risks
doc.add_heading('Репутационные риски для Гравити Групп', level=2)
p = doc.add_paragraph()
run = add_normal_run(p, 'Низкий-средний. Аутрич — нормальная практика. НО: рынок индор-рекламы узкий, если агент шлёт мусор — все узнают кто за этим стоит.')
run.font.size = Pt(11)

# Recommendation
p = doc.add_paragraph()
run = add_bold_run(p, '✅ РЕКОМЕНДАЦИЯ: БРАТЬ С УСЛОВИЯМИ')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(0, 100, 0)

for item in ['Чёткий scope и KPI в договоре', 'Бюджет на прогрев (1-2 мес до полной мощности)', 'Human-in-the-loop на старте', 'Юрконсультация по 152-ФЗ до подписания', 'Ежемесячный review с правом выхода']:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(item)
    run.font.size = Pt(11)

doc.add_page_break()

# ============ PLAN 2 ============
h1 = doc.add_heading('ПЛАН 2: AI-агент для политической агитации', level=1)
for run in h1.runs:
    run.font.size = Pt(14)

# Scenario
scenario = doc.add_paragraph()
run = add_bold_run(scenario, 'Сценарий провала: ')
run.font.size = Pt(11)
run = add_normal_run(scenario, '"Октябрь 2026. Прошло 6 месяцев. Агент провалился. Почему?"')
run.font.size = Pt(11)

# Section: Причины провала
h2 = doc.add_heading('Причины провала', level=2)
for run in h2.runs:
    run.font.size = Pt(13)

# People
add_category_header(doc, '👥 Люди')

add_item(doc, 1, 'Политик/штаб не доверяет AI — боится утечки или скандала, саботирует внедрение', 'H/H', 'Штаб правит каждое сообщение вручную, агент бесполезен')
add_item(doc, 2, 'У Гравити Групп нет опыта в полит-коммуникациях — не понимают тонкостей, формулировки провоцируют скандал', 'H/H', 'Первый публичный конфликт из-за неудачной формулировки')
add_item(doc, 3, 'Нет ответственного от штаба за контент — никто не апрувит, всё зависает', 'M/H', 'Очередь на аппрув растёт, дедлайны срываются')

# Process
add_category_header(doc, '⚙️ Процесс')

add_item(doc, 4, 'Нет протокола эскалации — AI отвечает на острый вопрос сам, получается скандал', 'H/H', 'Скриншот ответа бота в негативном ключе в СМИ')
add_item(doc, 5, 'Контент устаревает мгновенно — политическая повестка меняется за часы, агент работает на вчерашних данных', 'H/H', 'Агент поздравляет с событием которое уже стало токсичным')
add_item(doc, 6, 'Scope размыт — **"мониторинг"** превращается в **"полноценную аналитическую систему"**', 'H/M', 'Через месяц штаб хочет предиктивную аналитику')

# Tech
add_category_header(doc, '💻 Технологии')

add_item(doc, 7, 'AI генерирует токсичные/провокационные высказывания от имени политика', 'M/H', 'Любой инцидент в первые 2 недели')
add_item(doc, 8, 'Массовые рассылки в соцсетях — баны аккаунтов, удаление ботов', 'H/H', 'Первый бан, жалобы "бот спамит"')
add_item(doc, 9, 'Мониторинг соцсетей даёт шум вместо сигнала — 90% нерелевантного', 'M/M', 'Штаб перестаёт читать отчёты мониторинга')
add_item(doc, 10, 'Утечка данных / переписки / стратегии через инфраструктуру агента', 'L/H', 'Любой несанкционированный доступ к системе')

# External
add_category_header(doc, '🌍 Внешние факторы')

add_item(doc, 11, 'Закон о **"фейках" / "дискредитации"** — AI-генерированный контент привлекает внимание регуляторов', 'M/H', 'Запрос от Роскомнадзора или прокуратуры')
add_item(doc, 12, 'Конкурент/оппозиция раскрывает использование ботов — публичный скандал', 'M/H', 'Расследование в СМИ о "ботофермах"')
add_item(doc, 13, 'Смена политической конъюнктуры — кандидат теряет поддержку, проект теряет смысл', 'M/M', 'Падение рейтингов кандидата')

# TOP-3
doc.add_heading('ТОП-3 приоритета', level=2)

add_top_priority(doc, 1, '**AI говорит от имени политика без контроля**', 'Строгий whitelist тем и формулировок. Все ответы на острые вопросы — ТОЛЬКО через человека. AI отвечает только на "безопасные" сценарии (поздравления, расписание, типовые вопросы).')
add_top_priority(doc, 2, '**Политическая повестка устаревает за часы**', 'Ежедневный апдейт "стоп-листа" тем от штаба. Механизм экстренного отключения рассылок за 5 минут. Без этого — агент опасен.')
add_top_priority(doc, 3, '**Публичное разоблачение "ботов"**', 'Прозрачность: бот должен представляться ботом ("Я цифровой помощник депутата X"). Не маскироваться под человека. Это и этичнее, и безопаснее юридически.')

# Early warnings
doc.add_heading('Ранние сигналы предупреждения', level=2)
for item in ['Скриншот неудачного ответа бота в публичном поле', 'Жалобы на "спам от политика" в соцсетях', 'Штаб перестаёт обновлять контент/стоп-листы', 'Расследование в СМИ о ботах в предвыборной кампании', 'Запрос от любого гос.органа']:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(item)
    run.font.size = Pt(11)

# Legal risks
h2 = doc.add_heading('Юридические риски (РФ) — КРИТИЧНО', level=2)
for run in h2.runs:
    run.font.color.rgb = RGBColor(180, 0, 0)

for item in ['ФЗ-67 "О выборах": использование ботов для агитации — может быть квалифицировано как нарушение порядка агитации. Штрафы + отмена результатов.', '152-ФЗ: обработка ПДн избирателей без согласия — прямое нарушение. Штрафы до 18 млн руб.', 'Статья 5.12 КоАП: нарушение порядка предвыборной агитации — штраф до 50 тыс на юрлицо.', 'Статья 141 УК РФ: воспрепятствование осуществлению избирательных прав — до 5 лет.', 'Закон о "фейках" (207.1-207.2 УК): AI может сгенерировать текст, квалифицируемый как недостоверная информация.']:
    p = doc.add_paragraph(style='List Bullet')
    parts = item.split('**')
    for i, part in enumerate(parts):
        if i % 2 == 0:
            run = p.add_run(part)
            run.font.size = Pt(11)
        else:
            run = p.add_run(part)
            run.bold = True
            run.font.size = Pt(11)

p = doc.add_paragraph()
run = add_bold_run(p, 'Риск: ')
run.font.size = Pt(11)
run = add_bold_run(p, 'ВЫСОКИЙ. ')
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(180, 0, 0)
run = add_normal_run(p, 'Юридическое поле минное.')
run.font.size = Pt(11)

# Reputation risks
h2 = doc.add_heading('Репутационные риски для Гравити Групп — КРИТИЧНО', level=2)
for run in h2.runs:
    run.font.color.rgb = RGBColor(180, 0, 0)

p = doc.add_paragraph()
run = add_bold_run(p, 'ВЫСОКИЙ риск. ')
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(180, 0, 0)
run = add_normal_run(p, '"Гравити Групп помогает политикам спамить ботами" — это заголовок который убивает бренд. Даже если проект успешен — ассоциация с политтехнологиями отпугнёт коммерческих клиентов. В случае скандала — Гравити Групп будет "та компания которая делала ботов для [политика]".')
run.font.size = Pt(11)

# Recommendation
p = doc.add_paragraph()
run = add_bold_run(p, '🚫 РЕКОМЕНДАЦИЯ: НЕ БРАТЬ')
run.font.size = Pt(12)
run.font.color.rgb = RGBColor(180, 0, 0)

p = doc.add_paragraph()
run = add_normal_run(p, 'Или брать ТОЛЬКО при выполнении ВСЕХ условий:')
run.font.size = Pt(11)

for item in ['Полная юридическая экспертиза ДО старта (бюджет: 50-100 тыс руб)', 'Бот ЯВНО представляется ботом (не маскируется под человека)', 'Никакой агитации "против" — только позитивный контент', 'Контракт через юрлицо клиента, Гравити Групп = техподрядчик', 'Право на немедленный выход без штрафов', 'Гравити Групп НЕ упоминается публично как исполнитель', 'Предоплата 100%']:
    p = doc.add_paragraph(style='List Bullet')
    run = p.add_run(item)
    run.font.size = Pt(11)

p = doc.add_paragraph()
run = add_bold_run(p, 'Соотношение риск/прибыль: плохое. ')
run.font.size = Pt(11)
run.font.color.rgb = RGBColor(180, 0, 0)
run = add_normal_run(p, 'Один скандал уничтожит больше, чем проект заработает.')
run.font.size = Pt(11)

# Save
doc.save('/home/clawdbot/.openclaw/workspace/drafts/premortem-ai-sales-agent-2026-04-02.docx')
print("Document saved successfully!")
