#!/usr/bin/env python3
"""Генерация DOCX с планом Product Card Generator / ZnaemAI"""

from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import datetime

doc = Document()

# Поля страницы
for section in doc.sections:
    section.top_margin = Cm(2)
    section.bottom_margin = Cm(2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# Стили
styles = doc.styles

def add_heading(text, level=1, color=None):
    p = doc.add_heading(text, level=level)
    p.alignment = WD_ALIGN_PARAGRAPH.LEFT
    for run in p.runs:
        if color:
            run.font.color.rgb = RGBColor(*color)
    return p

def add_paragraph(text, bold=False, indent=False):
    p = doc.add_paragraph()
    if indent:
        p.paragraph_format.left_indent = Inches(0.3)
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(11)
    return p

def add_bullet(text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    p.paragraph_format.left_indent = Inches(0.3)
    if bold_prefix:
        run = p.add_run(bold_prefix + " ")
        run.bold = True
        run.font.size = Pt(11)
    run2 = p.add_run(text)
    run2.font.size = Pt(11)
    return p

def add_table_simple(headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = 'Table Grid'
    # Заголовок
    hdr = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = h
        for para in hdr[i].paragraphs:
            for run in para.runs:
                run.bold = True
                run.font.size = Pt(10)
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    # Данные
    for ri, row_data in enumerate(rows):
        row = table.rows[ri + 1].cells
        for ci, val in enumerate(row_data):
            row[ci].text = val
            for para in row[ci].paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)
    return table

# ─────────────────────────────────────────────
# ШАПКА
# ─────────────────────────────────────────────
title = doc.add_heading('Стратегический план: Product Card Generator', 0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.font.color.rgb = RGBColor(0x1A, 0x56, 0xDB)

sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run(f'ZnaemAI • Версия 1.0 • {datetime.date.today().strftime("%d.%m.%Y")}')
r.font.size = Pt(10)
r.font.color.rgb = RGBColor(0x6B, 0x72, 0x80)

doc.add_paragraph()

# ─────────────────────────────────────────────
# 1. ЦЕЛЬ
# ─────────────────────────────────────────────
add_heading('1. Цель компании', level=1, color=(0x1A, 0x56, 0xDB))

add_bullet('₽1 200 000 MRR к сентябрю 2026 (~$14 000, 6 месяцев)', bold_prefix='Основная цель:')
add_bullet('₽130 000 MRR к июню 2026 (~$1 500, 3 месяца)', bold_prefix='Промежуточная:')

# ─────────────────────────────────────────────
# 2. ТЕКУЩИЙ СТАТУС
# ─────────────────────────────────────────────
add_heading('2. Текущий статус', level=1, color=(0x1A, 0x56, 0xDB))

add_table_simple(
    ['Параметр', 'Статус'],
    [
        ['MVP задеплоен', '✅ https://znaemai-card-generator.jakeberrimor.com/'],
        ['Выбор модели генерации', '✅ Реализован'],
        ['Авторизация', '❌ Нет'],
        ['Монетизация', '❌ Нет'],
        ['ИП', '✅ Подтверждено'],
        ['AI-лица в генерациях', '✅ Разрешено (с дисклеймером)'],
        ['Платящие пользователи', '0'],
        ['MRR', '0 ₽'],
    ]
)

doc.add_paragraph()

# ─────────────────────────────────────────────
# 3. ПРОДУКТ
# ─────────────────────────────────────────────
add_heading('3. Продукт', level=1, color=(0x1A, 0x56, 0xDB))

add_heading('Пайплайн генерации', level=2)
steps = [
    'Юзер загружает фото товара + описание',
    'claude-haiku анализирует фото, генерирует 4–6 сценариев сцен — ждёт одобрения',
    'nano-banana-pro генерирует lifestyle сцену для каждого одобренного сценария',
    'HTML/CSS шаблон + скриншот Playwright = финальная карточка',
    'Превью → одобрение → файлы отправляются через sendDocument',
    'Финальный запрос: «Оцените результат от 1 до 10»',
]
for i, s in enumerate(steps, 1):
    add_bullet(s, bold_prefix=f'{i}.')

add_heading('Технический стек', level=2)
add_bullet('Python / FastAPI — бэкенд')
add_bullet('LiteLLM — claude-haiku-4-5 (vision + генерация сценариев)')
add_bullet('Replicate API — nano-banana-pro (~$0.15/фото) / flux-kontext-pro (~$0.04/фото)')
add_bullet('Playwright — HTML/CSS шаблон + финальный скриншот')
add_bullet('S3 (FirstVDS) — хранилище результатов')
add_bullet('Vite + React + FSD + Shadcn/ui — фронтенд')

# ─────────────────────────────────────────────
# 4. ДОРОЖНАЯ КАРТА
# ─────────────────────────────────────────────
add_heading('4. Дорожная карта', level=1, color=(0x1A, 0x56, 0xDB))

add_heading('Фаза 0 — Юридика (Неделя 1, параллельно)', level=2)
add_table_simple(
    ['Действие', 'Кто', 'Срок', 'Статус'],
    [
        ['Публичная оферта + политика ПД', 'Денис + юрист', 'Неделя 1', '⏳'],
        ['Replicate: private predictions + скачивать output', 'Дмитрий', 'До Фазы 1', '⏳'],
        ['Чекбокс согласия на трансграничную передачу', 'Дмитрий', 'До монетизации', '⏳'],
        ['Уведомление Роскомнадзора', 'Денис', 'Неделя 2', '⏳'],
        ['AI-лица: правовой статус', 'Аркадий', 'Неделя 1', '✅ Готово'],
        ['Подтвердить наличие ИП', 'Денис', 'Немедленно', '✅ Готово'],
    ]
)

doc.add_paragraph()

add_heading('Фаза 1 — Монетизация (Недели 2–8)', level=2)
p = doc.add_paragraph()
r = p.add_run('⚠️  Реальный срок — 6–8 недель (ЮKassa занимает до 4 недель подключения)')
r.font.size = Pt(10)
r.font.color.rgb = RGBColor(0xC0, 0x55, 0x00)

add_bullet('Авторизация (email + пароль, OAuth VK/Яндекс опционально)', bold_prefix='Дмитрий:')
add_bullet('Кредитная система (1 кредит = 1 генерация, 5 бесплатных при регистрации)')
add_bullet('ЮKassa интеграция (пакеты: 20 / 100 / 500 кредитов) — карты + СБП + ЮMoney')
add_bullet('История генераций (30 дней)')
add_bullet('Кнопка «Регенерировать»')
add_bullet('Скачивать Replicate output на свой сервер (не replicate.delivery)')

add_heading('Фаза 2 — Первые пользователи (Недели 8–12)', level=2)
add_bullet('DM-аутрич к активным участникам Telegram-сообществ WB/Ozon')
add_bullet('Статья на Хабр (как устроена AI-команда, кейс Product Card Generator)')
add_bullet('ВКонтакте: группы по маркетплейсам')
add_bullet('Product Hunt лонч')
add_bullet('Демо-видео 30 сек: фото → карточка')
add_bullet('Реферальная программа (+5 кредитов за приглашённого)')

p2 = doc.add_paragraph()
r2 = p2.add_run('Цель: 50–100 регистраций, 5–10 платящих')
r2.bold = True
r2.font.size = Pt(11)

add_heading('Фаза 3 — Рост (Месяц 3–4)', level=2)
add_bullet('Batch-обработка (до 10 фото, скачать ZIP)')
add_bullet('Brand Kit v1 (логотип как overlay)')
add_bullet('Subscription тарифы: Старт ₽1 400/мес, Про ₽4 500/мес')

p3 = doc.add_paragraph()
r3 = p3.add_run('Цель: 50 платящих, ₽130 000 MRR')
r3.bold = True
r3.font.size = Pt(11)

add_heading('Фаза 4 — Масштаб (Месяц 5–6)', level=2)
add_bullet('SEO (лендинги «AI карточки WB/Ozon», «генерация фото товаров»)')
add_bullet('Партнёрства с консультантами по маркетплейсам')
add_bullet('White-label для агентств')

p4 = doc.add_paragraph()
r4 = p4.add_run('Цель: 250 платящих, ₽750 000 MRR')
r4.bold = True
r4.font.size = Pt(11)

# ─────────────────────────────────────────────
# 5. МОНЕТИЗАЦИЯ
# ─────────────────────────────────────────────
add_heading('5. Монетизация', level=1, color=(0x1A, 0x56, 0xDB))

add_heading('Тарифы (Freemium + Credits)', level=2)
add_table_simple(
    ['Тариф', 'Цена', 'Кредиты', 'Extras'],
    [
        ['Free', '0 ₽', '5/мес', '—'],
        ['Старт', '₽1 400/мес', '100/мес', 'Batch до 10'],
        ['Про', '₽4 500/мес', '500/мес', 'Batch до 50, API, Brand Kit'],
        ['Business', '₽13 000/мес', '2 000/мес', 'Batch ∞, White-label, Priority'],
        ['Разовые', '₽18/кредит', 'Покупка', 'От 20 штук'],
    ]
)

doc.add_paragraph()

add_heading('Экономика', level=2)
add_bullet('Себестоимость 1 генерации: ~₽4–8')
add_bullet('Цена: ₽18–20/кредит → маржа 55–75%')
add_bullet('Break-even: ~100 платящих (~₽270 000 MRR, ориентировочно M5)')
add_bullet('Платёжная система: ЮKassa (карты + СБП + ЮMoney)')

# ─────────────────────────────────────────────
# 6. ФИНАНСОВАЯ МОДЕЛЬ
# ─────────────────────────────────────────────
add_heading('6. Финансовая модель (консервативная)', level=1, color=(0x1A, 0x56, 0xDB))

add_table_simple(
    ['Период', 'Платящих', 'Ср. чек', 'MRR'],
    [
        ['M1 апр 2026', '0–3', '—', '₽0–6 000'],
        ['M2 май 2026', '10', '₽2 000', '₽20 000'],
        ['M3 июн 2026', '30', '₽2 500', '₽75 000'],
        ['M4 июл 2026', '60', '₽2 700', '₽162 000'],
        ['M5 авг 2026', '120', '₽2 800', '₽336 000'],
        ['M6 сен 2026', '250', '₽3 000', '₽750 000'],
    ]
)

doc.add_paragraph()
p5 = doc.add_paragraph()
r5 = p5.add_run('Оптимистичный M6: 400 платящих → ₽1 200 000 MRR')
r5.bold = True
r5.font.size = Pt(11)
r5.font.color.rgb = RGBColor(0x05, 0x7A, 0x55)

# ─────────────────────────────────────────────
# 7. БЛИЖАЙШИЕ ДЕЙСТВИЯ
# ─────────────────────────────────────────────
add_heading('7. Ближайшие 2 недели', level=1, color=(0x1A, 0x56, 0xDB))

add_table_simple(
    ['#', 'Действие', 'Кто', 'Срок'],
    [
        ['1', 'Заказать оферту + политику ПД у юриста', 'Денис', 'Неделя 1'],
        ['2', 'Авторизация (email + пароль) — стартовать сейчас', 'Дмитрий', 'Немедленно'],
        ['3', 'Подать заявку в ЮKassa', 'Денис + Дмитрий', 'Неделя 1'],
        ['4', 'Replicate: private predictions, скачивать output', 'Дмитрий', 'Неделя 1'],
        ['5', 'Кредитная система (1 кредит = 1 генерация)', 'Дмитрий', 'Неделя 2–3'],
    ]
)

# ─────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────
doc.add_paragraph()
footer_p = doc.add_paragraph()
footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r_f = footer_p.add_run('Документ подготовлен AI-командой ZnaemAI • Аркадий (посредник) • Максим (CEO) • Дмитрий (Engineer)')
r_f.font.size = Pt(9)
r_f.font.color.rgb = RGBColor(0x9C, 0xA3, 0xAF)

OUT = '/home/clawdbot/.openclaw/workspace/drafts/znaemai_plan_2026.docx'
doc.save(OUT)
print(f'Saved: {OUT}')
