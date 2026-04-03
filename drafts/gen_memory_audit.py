#!/usr/bin/env python3
"""Generate memory audit DOCX for Denis review."""

from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn

doc = Document()

# Page setup - A4 landscape
section = doc.sections[0]
section.page_width = Cm(29.7)
section.page_height = Cm(21)
section.left_margin = Cm(1.5)
section.right_margin = Cm(1.5)
section.top_margin = Cm(1.5)
section.bottom_margin = Cm(1.5)

# Styles
style = doc.styles['Normal']
style.font.name = 'Arial'
style.font.size = Pt(9)

# Title
title = doc.add_heading('Revision pamyati Arkashi - 2026-04-02', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
for run in title.runs:
    run.text = 'Ревизия памяти Аркаши — 2026-04-02'

p = doc.add_paragraph()
p.add_run('Документ для ревью Дениса. По каждому факту — проставить статус и комментарий.').bold = False
p2 = doc.add_paragraph()
p2.add_run('Статусы: верно | устарело | неверно | нужно уточнить')

facts = []
n = [0]

def add(cat, fact, value):
    n[0] += 1
    facts.append((n[0], cat, fact, '', value, ''))

# === О ДЕНИСЕ ===
add('О Денисе', 'Имя', 'Денис')
add('О Денисе', 'Локация', 'Пенза')
add('О Денисе', 'Часовой пояс', 'Europe/Moscow (GMT+3)')
add('О Денисе', 'Роль на работе', 'Проектный руководитель / Разработчик / Тимлид / Архитектор')
add('О Денисе', 'Интересы', 'LLM, агенты, AI')
add('О Денисе', 'Стандарт качества', 'Дотошный, ищет оптимальное, не быстрое')
add('О Денисе', 'Pet-проект', 'Корпоративная база знаний (Logera)')
add('О Денисе', 'Telegram ID', '364935958')
add('О Денисе', 'GitHub personal', 'topitip')
add('О Денисе', 'Email рабочий', 'a.parmeev@jakeberrimor.com')

# === ЗДОРОВЬЕ ===
add('Здоровье', 'Операция', '2024 - удаление щитовидной железы после рака')
add('Здоровье', 'Радиойодотерапия', 'После операции, месяц без лекарств - критическое состояние')
add('Здоровье', 'Адаптация организма', '~3 года (с 2024)')
add('Здоровье', 'Лекарства: время приема', '09:00 ежедневно, на голодный желудок')
add('Здоровье', 'Напоминания', '09:00 (основное), 09:20 (повторное), 09:45 (критичное)')
add('Здоровье', 'Последствия пропуска', 'Сонливость, вплоть до комы; риск рецидива рака')
add('Здоровье', 'Финансовые сложности', 'Нет денег на регулярные проверки (анализы, УЗИ)')
add('Здоровье', 'Самочувствие на лекарствах', 'Прекрасно, набрал вес, работает полноценно')
add('Здоровье', 'Побочки: мало лекарств', 'Тянет в сон, усталость')
add('Здоровье', 'Побочки: много лекарств', 'Гиперактивность, бессонница')
add('Здоровье', 'Напоминания через', 'System crontab (Gateway cron ненадежен)')

# === О СЕБЕ (АРКАША) ===
add('Аркаша', 'Имя агента', 'Аркаша')
add('Аркаша', 'Email', 'a.parmeev@jakeberrimor.com (account: arkady)')
add('Аркаша', 'GitHub: arkasha-ai', 'Разблокирован 25.02.2026, тикет #4087174')
add('Аркаша', 'GitHub: arkasha-bot', 'Машинный аккаунт, email: arkadiy@jakeberrimor.com')
add('Аркаша', 'SSH ключ arkasha-bot', '~/.ssh/github_arkasha_bot')
add('Аркаша', 'Браузер', 'profile="openclaw"')
add('Аркаша', 'Moltbook', 'https://moltbook.com/u/Arkasha')

# === РАБОТА / GRAVITY ===
add('Работа/Gravity', 'Компания', 'Gravity Group (ООО Гравити Групп)')
add('Работа/Gravity', 'ИНН Gravity', '5908999996')
add('Работа/Gravity', 'Директор Gravity', 'Яборов Андрей Владимирович')
add('Работа/Gravity', 'Telegram Gravity LLM', '-4958457563')
add('Работа/Gravity', 'Тимофей Шутов', 'Финансовый директор Gravity, группа -5112704488')
add('Работа/Gravity', 'Ставка ПЭК РИЗ', '3000 руб./час')
add('Работа/Gravity', 'Проект ПЭК РИЗ', 'Экзаменационная система, Python/FastAPI + Vue.js 3')
add('Работа/Gravity', 'Проект Возврат ТМЦ', 'Ждем ответов на 9 вопросов, 856-1604 часов')
add('Работа/Gravity', 'Проект Аудитор', 'Ждем ставку от Дениса')
add('Работа/Gravity', 'НДС считается', 'СВЕРХУ от оценки (не включен внутрь)')
add('Работа/Gravity', 'Гарантийный срок', '3 месяца после подписания акта')
add('Работа/Gravity', 'Стандарт оплаты', '30% предоплата / 40% по готовности / 30% после акта')
add('Работа/Gravity', 'Скрипт заявок', 'scripts/gravity_zavka_generator_v2.py')
add('Работа/Gravity', 'Шаблон заявки', 'ТОЛЬКО шаблонная замена, НИКОГДА Document() с нуля')

# === ZNAEM AI / СТУДИЯ ===
add('ZnaemAI', 'Название студии', 'Znaem AI')
add('ZnaemAI', 'Сайт', 'https://znaemai.ru')
add('ZnaemAI', 'Домен sellershot', 'sellershot.ru (зарегистрирован 22.03.2026)')
add('ZnaemAI', 'Telegram группа', '-1003831241406 (бывший -5268967728)')
add('ZnaemAI', 'Команда: Денис', 'Архитектор / Разработчик')
add('ZnaemAI', 'Команда: Миша Коржов', 'Продажи, @mskorzhov, ms.korzhov@gmail.com')
add('ZnaemAI', 'Команда: Аркаша', 'AI-агент / Сооснователь')
add('ZnaemAI', 'Миша: зарплата ожид.', 'От 180 000 руб., готов в офис Москвы')
add('ZnaemAI', 'Миша: hh.ru', 'https://hh.ru/resume/85bac3b7ff09d1a6fa0039ed1f656e665a6f44')
add('ZnaemAI', 'Кейсы', '4 шт: Агент для юриста, SyncVoice, Logera, Sales Coach')
add('ZnaemAI', 'AI-аудит', 'Бесплатно')
add('ZnaemAI', 'Агент под ключ', '150-300К руб./проект')
add('ZnaemAI', 'White-label агент', '30К руб./мес + токены')
add('ZnaemAI', 'Потенциальный клиент', 'Тот же что SyncVoice: 4 продукта (SyncVoice+Logera+Sales Coach+клон Аркаши)')

# === PAPERCLIP / SELLERSHOT ===
add('Paperclip/SellerShot', 'Paperclip URL', 'https://paperclip.znaemai.ru')
add('Paperclip/SellerShot', 'Agent ID (Аркадий)', '7fba4a1f-dbb5-49a9-ad74-4840f5556a52')
add('Paperclip/SellerShot', 'Company ID', 'b246cf3d-2eda-4223-8ff6-5be30c598eca')
add('Paperclip/SellerShot', 'Максим (CEO)', 'Agent a5893697-cd59-40e4-b7f7-51ccd26b77b5')
add('Paperclip/SellerShot', 'Дмитрий (Engineer)', 'Agent 5a630270-602f-434a-bedf-8c244f04cc61')
add('Paperclip/SellerShot', 'Gitea org', 'git.jakeberrimor.com/znaem-ai')
add('Paperclip/SellerShot', 'Gitea ceo-agent creds', 'CeoAgent2026! / token c0ef1b36...')
add('Paperclip/SellerShot', 'Gitea engineer creds', 'EngAgent2026! / token aba5e5aa...')
add('Paperclip/SellerShot', 'Repo', 'znaem-ai/product-card-generator')
add('Paperclip/SellerShot', 'MVP URL', 'https://znaemai-card-generator.jakeberrimor.com')
add('Paperclip/SellerShot', 'TG бот', '@sellershot_bot')
add('Paperclip/SellerShot', 'Cron мониторинг', 'Каждые 30 мин')
add('Paperclip/SellerShot', 'Стек бэкенда', 'FastAPI + SQLAlchemy async + asyncpg + Alembic + Redis')
add('Paperclip/SellerShot', 'Стек бота', 'aiogram 3.x + RedisStorage (FSM)')
add('Paperclip/SellerShot', 'Генерация', 'Gemini/FLUX через LiteLLM + Replicate + fal.ai')
add('Paperclip/SellerShot', 'Dokploy webhook', 'https://dokploy.jakeberrimor.com/api/deploy/compose/ZZvBrnbheUne2tpkXIb9F')
add('Paperclip/SellerShot', 'Формат карточки', '4:5')
add('Paperclip/SellerShot', 'Пайплайн карточек', 'FLUX Kontext -> HTML/CSS -> Playwright -> карточка')
add('Paperclip/SellerShot', 'FLUX Kontext Pro цена', '~$0.04/фото')
add('Paperclip/SellerShot', 'Nano Banana Pro цена', '~$0.15/фото (1K/2K)')

# === ПРОЕКТ LOGERA ===
add('Проект Logera', 'Репозиторий', 'topitip/logera.space (приватный GitHub)')
add('Проект Logera', 'Ветка', 'feature/design-improvements')
add('Проект Logera', 'Стек frontend', 'SvelteKit 2.38 + Svelte 5.38 + shadcn-svelte + Tailwind 4')
add('Проект Logera', 'Стек backend', 'FastAPI 0.115 + Peewee + LangGraph + LiteLLM')
add('Проект Logera', 'Docker сервисы', '21 шт')
add('Проект Logera', 'Таблицы в БД', '24')
add('Проект Logera', 'Воркеры', '7: media_prep, diarization, asr, speaker_linking, indexer, nlp_adapter, cleanup')
add('Проект Logera', 'Документация', '17 md файлов, 7500+ строк')

# === ПРОЕКТ SYNCVOICE ===
add('Проект SyncVoice', 'Суть', 'Система синхронного перевода, on-premise')
add('Проект SyncVoice', 'Языки', 'Русский - Английский - Хинди - Китайский')
add('Проект SyncVoice', 'Бюджет КП', '~6 млн руб')
add('Проект SyncVoice', 'Telegram чат', '-5178956577')
add('Проект SyncVoice', 'Дмитрий Байдин', 'Куратор, @bdd1974, +7 905 787 8773, ДР 6 марта 1974')
add('Проект SyncVoice', 'Константин (Estetic Sound)', 'Интегратор/продажник')
add('Проект SyncVoice', 'Оборудование клиента', 'Gistron (не Crestron!) беспроводная конгресс-система')
add('Проект SyncVoice', 'Статус', 'Дедлайн 07.03 - описание функционала + демо MVP')

# === ПРОЕКТ PORTFOLIO ===
add('Проект Portfolio', 'Концепция', 'Чат-интерфейс вместо страниц, LLM генерирует текст + UI')
add('Проект Portfolio', 'Стек', 'Next.js + FastAPI + Aden Hive + LiteLLM + PostgreSQL + Redis')
add('Проект Portfolio', 'Домен frontend', 'jakeberrimor.com')
add('Проект Portfolio', 'Домен backend', 'api.jakeberrimor.com')
add('Проект Portfolio', 'Хостинг frontend', 'Vercel (Next.js SSG)')
add('Проект Portfolio', 'Хостинг backend', 'clwd.jakeberrimor.com')

# === ПРОЕКТ ARCHDOC ===
add('Проект Archdoc', 'Fork', 'arkasha-ai/archdoc, ветка feature/improvements-v2')
add('Проект Archdoc', 'PR', 'https://github.com/topitip/archdoc/pull/1')
add('Проект Archdoc', 'Язык', 'Rust, edition 2024')

# === ПРОЕКТ DIY СТОЛ ===
add('Проект DIY Стол', 'Тип', 'Угловой Г-образный 150x150 см, электрорегулировка')
add('Проект DIY Стол', 'Бюджет', '~25 000 руб (железо)')
add('Проект DIY Стол', 'Статус', 'Планирование')
add('Проект DIY Стол', 'Электроника', 'ESP32 + SimpleFOC + AS5048A')

# === ПРОЕКТ BRAIN-INSPIRED AI ===
add('Проект Brain-AI', 'Суть', 'Мозгоподобная архитектура AI: модули-специалисты + протокол')
add('Проект Brain-AI', 'Целевое железо', 'NVIDIA DGX Spark (~$3-5K, 128GB unified memory)')
add('Проект Brain-AI', 'Начат', '10 марта 2026')

# === ПРОЕКТ HIDE AND SEEK ===
add('Проект Hide&Seek', 'Суть', 'Программа-прятка для Windows (Rust)')
add('Проект Hide&Seek', 'Killswitch', 'C:\\Users\\Public\\.nomorerunning')
add('Проект Hide&Seek', 'Статус', 'ТЗ, не начато')

# === ЛЮДИ ===
add('Люди', 'Михаил Коржов: TG', '@mskorzhov')
add('Люди', 'Михаил Коржов: телефон', '89934884250')
add('Люди', 'Михаил Коржов: email', 'ms.korzhov@gmail.com')
add('Люди', 'Михаил Коржов: роль', 'PM, 4+ лет опыта, ищет работу')
add('Люди', 'Тимофей Шутов: роль', 'Финансовый директор Gravity')
add('Люди', 'Ксения Шутова: роль', 'Руководитель детского центра "Остров Аркаша"')
add('Люди', 'Ксения Шутова: TG', '@shutovakv (ID: 458267070)')
add('Люди', 'Ксения Шутова: группа', '"Остров Аркаша" (-5056580782)')
add('Люди', 'Александр Воробьев: TG ID', '942014320')
add('Люди', 'Александр Воробьев: роль', 'Юрист, знакомый Дениса')
add('Люди', 'Дмитрий Байдин: компания', 'Energotrend.Com - CEO')
add('Люди', 'Дмитрий Байдин: ДР', '6 марта 1974')
add('Люди', 'Дмитрий Байдин: роль в SyncVoice', 'Куратор/посредник')
add('Люди', 'Группа "Афигеваем"', '-5226768769 (Денис, Света, Котик @Rotibor_bot, Аркаша)')

# === ИНСТРУМЕНТЫ ===
add('Инструменты', 'MindGraph сервер', 'http://127.0.0.1:18790 (автостарт @reboot)')
add('Инструменты', 'MindGraph live mode', 'systemd user service mindgraph-live')
add('Инструменты', 'MindGraph содержимое', '5 людей, 4 орг, 5 проектов, 2 инфры, 6 знаний')
add('Инструменты', 'Старый граф KuzuDB', 'archive/knowledge-graph-kuzu/ (не используется)')
add('Инструменты', 'Email accounts', 'dparmeev, spam, contact, contact-lumines, arkady')
add('Инструменты', 'IMAP IDLE', 'scripts/imap_idle_listener_v2.py (4 accounts, НЕ arkady)')
add('Инструменты', 'TickTick: Аркаша Tasks', '6998c6fb1ff4510b9e851f9f')
add('Инструменты', 'TickTick: Личный', '695bc6dd7d799105bb21e874')
add('Инструменты', 'TickTick: Работа', '695bc7447dd51105bb21e8ee')
add('Инструменты', 'TickTick: Фитнес', '695bfa4ba268d125f73668e9')
add('Инструменты', 'TTS голос', 'ru-RU-DmitryNeural (Edge TTS)')
add('Инструменты', 'Whisper endpoint', 'https://litellm.jakeberrimor.com, model: openai/whisper-large-v3')
add('Инструменты', 'Qdrant embedding', 'Qwen3-Embedding-0.6B via LiteLLM')
add('Инструменты', 'Qdrant collection', 'arkasha')
add('Инструменты', 'Podcast TTS', 'Yandex SpeechKit v3 gRPC (ermil + alena)')
add('Инструменты', 'Replicate модель', 'FLUX.1-dev (black-forest-labs/flux-dev)')
add('Инструменты', 'VK сервисный ключ', 'VK_SERVICE_TOKEN в secrets.env')
add('Инструменты', 'Penpot URL', 'https://penpot.jakeberrimor.com')
add('Инструменты', 'Penpot аккаунт', 'spam@jakeberrimor.com / q25RiI#L')
add('Инструменты', 'Penpot MCP', 'https://penpot-mcp.jakeberrimor.com/sse')
add('Инструменты', 'shadcn-studio API Key', 'F3A391ED-2051-489F-94BE-CE8C9D5ED92B')
add('Инструменты', 'Qwen3-TTS сервер', 'http://109.194.141.123:7860 (только когда beast вкл)')
add('Инструменты', 'Qwen3-TTS голоса', 'denis (neutral/happy/serious/angry), yulia (neutral)')
add('Инструменты', 'КонсультантПлюс', 'логин: 1046617 / пароль: pjdDQEAd')

# === ПРАВИЛА/УРОКИ ===
add('Правила/Уроки', 'НИКОГДА не врать', 'Уроки: 09.02, 21.02.2026')
add('Правила/Уроки', 'Cron для лекарств', 'System crontab, не Gateway cron')
add('Правила/Уроки', 'QMD Hybrid Search', 'НЕ РАБОТАЕТ, PR #65 сырой, Qdrant')
add('Правила/Уроки', 'Agent-to-Agent', 'Paperclip API (Redis relay убран 22.03.2026)')
add('Правила/Уроки', 'Nested Sub-agents', 'Работает, проверено экспериментально')
add('Правила/Уроки', 'Email security', 'Не отвечать незнакомцам без одобрения Дениса')
add('Правила/Уроки', 'Подпись в email', 'Аркадий (не Аркаша)')
add('Правила/Уроки', 'browser.act', 'Сломан, использовать openclaw browser click')
add('Правила/Уроки', 'Правило 2 неудач', '2 провала деплоя -> СТОП -> Денису')
add('Правила/Уроки', 'Git safety', 'develop -> ТОЛЬКО develop, master НИКОГДА')
add('Правила/Уроки', 'Внешние чаты', 'Не называть Дениса, не раскрывать инфру')
add('Правила/Уроки', 'Отправка файлов', 'ТОЛЬКО message(filePath=...), НЕ путь в тексте')
add('Правила/Уроки', 'Голосовые', 'Whisper -> текст -> tts -> asVoice=true')
add('Правила/Уроки', 'Heartbeat', 'Следовать HEARTBEAT.md, checklist перед OK')
add('Правила/Уроки', 'SingularityApp token', '8deced88-6018-44ad-9c1e-c87d7e895189')
add('Правила/Уроки', 'AI рендеры основные', 'Nano Banana (bananalab.pw) + fal.ai (резерв)')
add('Правила/Уроки', 'Триггер "выпил"', 'Обновить medicine-today.json, ответить коротко')

# Create table
table = doc.add_table(rows=1, cols=6, style='Table Grid')
table.alignment = WD_TABLE_ALIGNMENT.CENTER

widths = [Cm(1.0), Cm(3.5), Cm(7.0), Cm(2.5), Cm(7.5), Cm(5.0)]

# Header
header_cells = table.rows[0].cells
headers = ['#', 'Категория', 'Факт', 'Статус', 'Текущее значение в памяти', 'Комментарий Дениса']
for i, (cell, text) in enumerate(zip(header_cells, headers)):
    cell.text = text
    cell.width = widths[i]
    for paragraph in cell.paragraphs:
        paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for run in paragraph.runs:
            run.bold = True
            run.font.size = Pt(8)
    shading = cell._element.get_or_add_tcPr()
    shading_elm = shading.makeelement(qn('w:shd'), {
        qn('w:val'): 'clear',
        qn('w:color'): 'auto',
        qn('w:fill'): 'D9E2F3'
    })
    shading.append(shading_elm)

# Data rows
for num, cat, fact, status, value, comment in facts:
    row = table.add_row()
    cells = row.cells
    cells[0].text = str(num)
    cells[1].text = cat
    cells[2].text = fact
    cells[3].text = status
    cells[4].text = value
    cells[5].text = comment
    for i, cell in enumerate(cells):
        cell.width = widths[i]
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.size = Pt(8)
            if i == 0:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER

output = '/home/clawdbot/.openclaw/workspace/drafts/memory-audit-2026-04-02.docx'
doc.save(output)
print(f'OK: {len(facts)} facts saved to {output}')
