from docx import Document
from docx.shared import Pt, RGBColor
import sys

doc = Document()
style = doc.styles['Normal']
style.font.name = 'Arial'
style.font.size = Pt(11)

def heading(doc, text, level=1):
    return doc.add_heading(text, level=level)

def para(doc, text, bold=False, italic=False, color=None, size=None):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = RGBColor(*color)
    if size:
        run.font.size = Pt(size)
    return p

def bullet(doc, text, bold_prefix=None):
    p = doc.add_paragraph(style='List Bullet')
    if bold_prefix:
        r = p.add_run(bold_prefix)
        r.bold = True
        p.add_run(text)
    else:
        p.add_run(text)
    return p

def warn(doc, text):
    p = doc.add_paragraph()
    r = p.add_run('WARN: ' + text)
    r.bold = True
    r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
    return p

def update_note(doc, text):
    p = doc.add_paragraph()
    r = p.add_run('[ОБНОВЛЕНИЕ v1.2] ')
    r.bold = True
    r.font.color.rgb = RGBColor(0x16, 0x79, 0xA7)
    r2 = p.add_run(text)
    r2.font.color.rgb = RGBColor(0x16, 0x79, 0xA7)
    return p

def fixed(doc, text):
    p = doc.add_paragraph()
    r = p.add_run('[ИСПРАВЛЕНО] ')
    r.bold = True
    r.font.color.rgb = RGBColor(0x1E, 0x8B, 0x4C)
    r2 = p.add_run(text)
    r2.font.color.rgb = RGBColor(0x1E, 0x8B, 0x4C)
    return p

# ===== TITLE =====
doc.add_heading('SyncVoice™', 0)
para(doc, 'Система синхронного AI-перевода', bold=True, size=14)
para(doc, 'ВНУТРЕННЕЕ ТЕХНИЧЕСКОЕ РУКОВОДСТВО', bold=True)
para(doc, 'Версия 1.3 | Март 2026 (ревизия по результатам fact-check и web-исследования)', italic=True)
para(doc, 'КОНФИДЕНЦИАЛЬНО — Только для внутреннего использования Estetic Sound', bold=True, color=(0xC0, 0x39, 0x2B))
doc.add_page_break()

# ===== REVISION NOTE =====
heading(doc, 'ПРИМЕЧАНИЕ К ВЕРСИИ 1.2', level=1)
para(doc, 'Проведён полный fact-check всех технических тезисов по открытым источникам (HuggingFace, GitHub, arxiv, официальная документация). Найдены критические ошибки:', bold=True)
warn(doc, 'БЛОКЕР: Qwen3-TTS НЕ поддерживает Hindi — модель работает только с 10 языками (EN/ZH/RU/JA/KO/DE/FR/PT/ES/IT). Для Hindi нужен другой TTS.')
warn(doc, 'ЛИЦЕНЗИЯ NMT: NLLB-200 (CC-BY-NC 4.0) запрещает коммерческое использование. Заменить на MADLAD-400 (Apache 2.0).')
fixed(doc, 'Qwen-ASR -> правильное название: Qwen3-ASR (выпущен 2025). Поддерживает context biasing для глоссариев. Apache 2.0.')
fixed(doc, 'faster-whisper реабилитирован: с vad_filter=True (Silero VAD) значительно снижает галлюцинации. Поддерживает initial_prompt для hotwords.')
fixed(doc, 'NLLB-200 3.3B VRAM: ~8.2GB float16 (не 12-16GB как было написано). С CTranslate2 int8 — 2-4GB.')
fixed(doc, 'MADLAD-400 от Google — лучшая замена NLLB для EN<->RU. Apache 2.0, поддерживает 400+ языков.')
para(doc, 'Изменения затрагивают разделы 4.2, 4.3, 4.4, 5.1, 9.2. Остальные разделы без изменений.', bold=True)
doc.add_page_break()

# ===== SEC 1 =====
heading(doc, '1. РЕЗЮМЕ ПРОЕКТА', level=1)
para(doc, 'SyncVoice — on-premise система синхронного AI-перевода для фармацевтической компании. Два конференц-зала по 30 участников, перевод Hindi<->Russian<->English в реальном времени с задержкой менее 3 секунд.')
para(doc, 'Ключевые характеристики:', bold=True)
bullet(doc, '60 рабочих мест с персональными наушниками и микрофонами')
bullet(doc, '2-3 одновременных спикера максимум (не 30!)')
bullet(doc, 'Видеомост с партнёрами из Индии (удалённые участники)')
bullet(doc, 'Фармацевтическая терминология (требуется fine-tuning)')
bullet(doc, 'On-premise: все данные остаются внутри компании')
bullet(doc, 'Бюджет: ~$100,000 (10 млн руб.) включая разработку')
bullet(doc, 'Цепочка: Estetic Sound -> DDH (генподрядчик) -> Kristina (заказчик, фарма)')

# ===== SEC 2 =====
heading(doc, '2. ТЕХНИЧЕСКОЕ ЗАДАНИЕ', level=1)
heading(doc, '2.1 Физическая инфраструктура', level=2)
bullet(doc, '2 конференц-зала x 30 рабочих мест = 60 участников')
bullet(doc, 'Каждое место: микрофон + наушники + идентификация')
bullet(doc, 'Общие колонки в каждом зале (один выбранный поток)')
bullet(doc, 'PTZ-камеры с автотрекингом спикера')

heading(doc, '2.2 Аудиопотоки', level=2)
bullet(doc, 'Входящие: 2-3 спикера в зале + 1 поток из видеомоста')
bullet(doc, 'Исходящие: 1 поток в видеомост (выбранный язык)')
bullet(doc, 'Персональные: каждый участник выбирает свой язык в наушниках')
bullet(doc, 'Субтитры: текст на 2 языках поверх видеомоста (опция)')

heading(doc, '2.3 Языки', level=2)
bullet(doc, 'Приоритет 1: Hindi <-> Russian <-> English (все направления)')
bullet(doc, 'Приоритет 2: Chinese (Mandarin) — на перспективу')

heading(doc, '2.4 Требования к качеству', level=2)
bullet(doc, 'Латентность: < 3 секунд end-to-end')
bullet(doc, 'WER (Word Error Rate): < 15% для Hindi, < 10% для Russian/English')
bullet(doc, 'Фармацевтическая терминология: 95%+ корректных переводов')
bullet(doc, 'TTS: естественное произношение, без галлюцинаций')

# ===== SEC 3 =====
heading(doc, '3. ОБЗОР ПРОДЕЛАННОЙ АНАЛИТИКИ', level=1)
para(doc, 'За время работы над проектом проведён комплексный анализ по направлениям: STT-модели (ограничения окон, галлюцинации, VAD), архитектура глоссария, NMT для малоресурсных пар, TTS-системы (языковая поддержка, VRAM, RT-фактор), серверное оборудование и видеоплатформы.')

# ===== SEC 4 =====
heading(doc, '4. AI-PIPELINE: МОДЕЛИ И АРХИТЕКТУРА', level=1)

heading(doc, '4.1 Архитектура: каскадный pipeline', level=2)
para(doc, 'Речь -> STT (распознавание) -> NMT (перевод) -> TTS (синтез) -> Аудио', bold=True)
para(doc, 'Каскадный подход выбран вместо end-to-end моделей (SeamlessM4T): (1) fine-tuning каждого компонента отдельно под фарму, (2) глоссарий управляется на уровне STT, (3) лучше качество для редких языковых пар.')

# ===== 4.2 STT =====
heading(doc, '4.2 STT: распознавание речи', level=2)
update_note(doc, 'Пересмотрено по результатам fact-check. Faster-whisper частично реабилитирован.')

para(doc, 'Проблема Whisper — галлюцинации:', bold=True)
warn(doc, 'Whisper галлюцинирует не только на коротких окнах, но и на сегментах с тишиной/шумом (основная причина: condition_on_previous_text=True по умолчанию создаёт hallucination loops). Ограничение архитектурное.')
para(doc, 'Воркэраунды для Whisper:', bold=True)
bullet(doc, 'VAD-фильтрация (Silero VAD) перед подачей в Whisper — наиболее надёжное решение')
bullet(doc, 'condition_on_previous_text=False — снижает loop-галлюцинации')
bullet(doc, 'faster-whisper с vad_filter=True — встроенная Silero VAD прямо в pipeline + 2-4x speedup + initial_prompt для hotwords/глоссария')

para(doc, 'Рекомендуемые модели:', bold=True)

para(doc, 'Вариант A — Qwen3-ASR (приоритетный):', bold=True)
fixed(doc, 'Правильное название: Qwen3-ASR (не Qwen-ASR). Модели: Qwen3-ASR-1.7B и Qwen3-ASR-0.6B. Лицензия: Apache 2.0 (коммерческое разрешено).')
bullet(doc, '52 языка, включая Hindi, Russian, English')
bullet(doc, 'Context biasing: передаёшь текстовый глоссарий в запросе — модель смещает декодирование в сторону нужных терминов. Идеально для фармацевтики.')
bullet(doc, 'При раздельных аудиопотоках (по спикеру) — под каждый поток свой глоссарий')
bullet(doc, 'Поддерживает: language identification, timestamp prediction')

para(doc, 'Вариант B — faster-whisper large-v3 + VAD (резервный):', bold=True)
bullet(doc, 'vad_filter=True (Silero VAD) встроен — решает проблему галлюцинаций на тишине')
bullet(doc, 'initial_prompt — подаём фармацевтические термины как контекст')
bullet(doc, '2-4x быстрее оригинального Whisper на той же железе')
bullet(doc, 'Лицензия OpenAI Whisper: MIT. CTranslate2: MIT.')

para(doc, 'Ключевой принцип (сохраняется):', bold=True)
warn(doc, 'STT — источник истины. Глоссарий управляется на уровне STT. Постпроцессинг не работает.')
bullet(doc, 'Для TTS: LLM генерирует фонетику для нестандартных терминов -> подаётся в TTS')

para(doc, 'Двухмодельная стратегия:', bold=True)
bullet(doc, 'Qwen3-ASR-1.7B для Hindi (с Hindi глоссарием терминов)')
bullet(doc, 'Qwen3-ASR-1.7B для RU/EN (с RU/EN глоссарием терминов)')

# ===== 4.3 NMT =====
heading(doc, '4.3 NMT: машинный перевод', level=2)
update_note(doc, 'NLLB заменён. Добавлен MADLAD-400. Уточнены лицензии.')

para(doc, 'Почему постпроцессинг для глоссария не работает:', bold=True)
bullet(doc, 'STT может вернуть фонетически похожую строку вместо нужного термина — система не знает правильного варианта')
bullet(doc, 'Решение только через STT-уровень (context biasing в Qwen3-ASR)')

para(doc, 'Архитектура перевода (pivot через English):', bold=True)
bullet(doc, 'Hindi -> English: IndicTrans2 (MIT лицензия, коммерческое разрешено)')
bullet(doc, 'English -> Russian: Qwen3-8B int4 (глоссарий в system prompt)')
bullet(doc, 'English -> Hindi (обратно): IndicTrans2')
bullet(doc, 'English -> Chinese: MADLAD-400 или CosyVoice/ZH-специализированные')

para(doc, 'IndicTrans2 — статус:', bold=True)
fixed(doc, 'Подтверждено: IndicTrans2 от AI4Bharat. Лицензия: MIT (модели) + CC0 (данные). Коммерческое использование РАЗРЕШЕНО. Активно поддерживается. Лучшая открытая модель для Hindi<->English.')

para(doc, 'Замена NLLB-200 — MADLAD-400:', bold=True)
fixed(doc, 'NLLB-200: CC-BY-NC 4.0 — коммерческое использование ЗАПРЕЩЕНО. Блокер для продакшна. Замена: MADLAD-400 от Google.')
bullet(doc, 'Qwen3-8B: Apache 2.0 — коммерческое разрешено. int4 квантизация ~4-5GB VRAM')
bullet(doc, 'Поддерживает 400+ языков включая RU, HI, EN, ZH')
bullet(doc, 'Лучшее open-source качество EN<->RU на 2025 год')
bullet(doc, 'MADLAD-400-3B-MT — компактная версия, меньше VRAM')
warn(doc, 'Helsinki-NLP/opus-mt-en-ru: лицензия CC-BY 4.0 (коммерческое ОК), но модель 2020 года — устаревшая, низкое качество. Не рекомендуется для продакшна.')

# ===== 4.4 TTS =====
heading(doc, '4.4 TTS: синтез речи', level=2)
update_note(doc, 'Критическое исправление: Qwen3-TTS не поддерживает Hindi. Пересмотрена архитектура.')

warn(doc, 'КРИТИЧЕСКИЙ БЛОКЕР: Qwen3-TTS (правильное название, не Qwen TTS 1.7b) поддерживает только 10 языков: ZH, EN, JA, KO, DE, FR, RU, PT, ES, IT. HINDI НЕ ВХОДИТ! Для проекта с Hindi нужно другое решение.')
warn(doc, 'Piper TTS: Hindi официально не поддерживается в стандартных piper-voices без кастомного обучения. Не подходит для Hindi out-of-the-box.')

para(doc, 'Qwen3-TTS — характеристики:', bold=True)
fixed(doc, 'Правильное название: Qwen3-TTS (выпущен январь 2026, не Qwen TTS 1.7b). Лицензия: Apache 2.0.')
bullet(doc, 'Модели: Qwen3-TTS-12Hz-1.7B-Base, 1.7B-CustomVoice, 1.7B-VoiceDesign, 0.6B-CustomVoice')
bullet(doc, 'VRAM: 6-8GB (1.7B), 4-6GB (0.6B)')
bullet(doc, 'RT-фактор: ~1.3x (10 сек аудио = 13 сек генерации) — нужна оптимизация')
bullet(doc, 'ПЛЮСЫ: streaming, voice on-the-fly, загрузка аудио-произношений')
bullet(doc, 'Применимо для: RU, EN, ZH — но НЕ для Hindi!')

para(doc, 'XTTS v2 — рекомендуемый TTS для проекта:', bold=True)
fixed(doc, 'XTTS v2 поддерживает Hindi нативно (17 языков: EN, RU, HI, ZH и др.) — единственная опция среди рассмотренных, закрывающая все языки проекта.')
bullet(doc, 'VRAM: 4-6GB базово (может расти до 10GB при параллельных запросах) — рекомендуется 6GB+ per instance')
bullet(doc, 'RT-фактор: ~0.25-0.38 с deepspeed (быстрее реального времени!), first latency ~200ms')
bullet(doc, 'Поддерживает voice cloning — можно задать образец голоса')
bullet(doc, 'Лицензия: Coqui Public Model License — требует согласования для коммерческого использования')
warn(doc, 'Лицензия XTTS v2 требует проверки для коммерческого использования. Уточнить у текущих правообладателей.')

para(doc, 'Piper TTS — для RU/EN (без Hindi):', bold=True)
bullet(doc, 'VRAM: практически 0 (CPU-оптимизирован, работает на Raspberry Pi)')
bullet(doc, 'RT-фактор: < 0.1 на CPU — очень быстрый')
bullet(doc, 'Поддержка: EN (отлично), RU (есть голоса), Hindi — НЕ поддерживается стандартно')
bullet(doc, 'Если Hindi не нужен в Piper — использовать для RU/EN, XTTS v2 для Hindi')

para(doc, 'Рекомендуемая архитектура TTS:', bold=True)
bullet(doc, 'Вариант A (универсальный): XTTS v2 для всех языков (EN/RU/HI/ZH) — 6GB x3 инстанса = 18GB')
bullet(doc, 'Вариант B (гибридный): Piper для EN/RU (0 VRAM) + XTTS v2 только для HI/ZH (6GB x2 = 12GB) — экономия VRAM')
bullet(doc, 'Qwen3-TTS: добавить позже для EN/RU/ZH после оптимизации RT-фактора')

# ===== SEC 5 =====
heading(doc, '5. СЕРВЕРНОЕ ОБОРУДОВАНИЕ ДЛЯ AI', level=1)
heading(doc, '5.1 Расчёт VRAM — ПЕРЕСЧЁТ v1.2', level=2)
update_note(doc, 'Полный пересчёт с реальными данными по каждой модели.')

para(doc, 'Сценарий: 3 языка (RU, EN, Hindi) — приоритет 1. XTTS v2 для TTS.', bold=True)

table = doc.add_table(rows=7, cols=3)
table.style = 'Table Grid'
hdr = ['Компонент', 'VRAM (реальный)', 'Примечания']
rows_data = [
    ['STT: Qwen3-ASR-1.7B x2', '~3-4 GB каждая = ~6-8 GB', 'Hindi + RU/EN отдельно'],
    ['NMT: IndicTrans2 1B', '~2-3 GB', 'HI->EN'],
    ['NMT: MADLAD-400-3B', '~6-8 GB', 'EN<->RU (float16)'],
    ['TTS: XTTS v2 x3', '~6 GB каждая = ~18 GB', 'EN + RU + HI инстансы'],
    ['ИТОГО', '~32-37 GB', 'Без Chinese'],
    ['RTX 5090 (32 GB)', '32 GB', 'На грани — нужна оптимизация'],
]
for i, h in enumerate(hdr):
    cell = table.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
for r, rd in enumerate(rows_data):
    for c, v in enumerate(rd):
        table.rows[r+1].cells[c].text = v
doc.add_paragraph()

fixed(doc, 'NLLB-200 3.3B VRAM был завышен: реальный расчёт ~8.2GB float16 (с CTranslate2 int8 — 2-4GB). В таблице выше использован MADLAD-400-3B как замена.')

para(doc, 'Оптимизированный вариант (гибридный TTS):', bold=True)

table2 = doc.add_table(rows=6, cols=3)
table2.style = 'Table Grid'
hdr2 = ['Компонент', 'VRAM', 'Примечания']
rows2 = [
    ['STT: Qwen3-ASR-1.7B x2', '~6-8 GB', ''],
    ['NMT: IndicTrans2 + MADLAD-3B (int8)', '~2 + 3 = ~5 GB', 'CTranslate2 квантизация'],
    ['TTS: Piper x2 (EN/RU) + XTTS v2 x1 (HI)', '~0 + 6 GB = ~6 GB', 'Гибрид'],
    ['ИТОГО', '~17-19 GB', 'Много запаса'],
    ['RTX 5090 (32 GB)', '32 GB', 'ХВАТАЕТ + fine-tuning'],
]
for i, h in enumerate(hdr2):
    cell = table2.rows[0].cells[i]
    cell.text = h
    cell.paragraphs[0].runs[0].bold = True
for r, rd in enumerate(rows2):
    for c, v in enumerate(rd):
        table2.rows[r+1].cells[c].text = v
doc.add_paragraph()

para(doc, 'Сценарий с Chinese (4 языка):', bold=True)
bullet(doc, 'Добавляется: XTTS v2 x1 для ZH (+6GB) или Qwen3-TTS для ZH (+6-8GB)')
bullet(doc, 'Итого оптимизированный: ~23-27GB — RTX 5090 справляется')
bullet(doc, 'Итого базовый (XTTS v2 x4): ~30-36GB — на грани или не хватает')

para(doc, 'Варианты решения:', bold=True)
bullet(doc, 'A) Гибридный TTS (Piper+XTTS) + int8 NMT: 1x RTX 5090 хватает на 3-4 языка')
bullet(doc, 'B) Полный XTTS v2 x4: 2x RTX 5090 для надёжности')
bullet(doc, 'Обязателен: benchmark full pipeline до финального выбора железа')

heading(doc, '5.2 GPU — рекомендация', level=2)
warn(doc, 'DGX Spark — маркетинг. 128 GB unified memory, но bandwidth 273 GB/s = в 6.5x меньше RTX 5090. Latency вырастет в разы.')
bullet(doc, 'RTX 5090 (ASUS ROG ASTRAL, ~500K руб.) — 32GB GDDR7, bandwidth ~1.79 TB/s')
bullet(doc, 'При гибридном TTS + квантизации NMT: 1x RTX 5090 достаточно для 3-4 языков')
bullet(doc, '2x RTX 5090 — при полном XTTS v2 на все языки или для fine-tuning запаса')

# ===== SEC 6 =====
heading(doc, '6. КОНФЕРЕНЦ-ОБОРУДОВАНИЕ', level=1)
para(doc, 'Без изменений. Рекомендация: TAIDEN HCS-4800 (или Bosch CCS 1000D). Бюджет $5,000-7,000 на зал. Ключевое требование: изолированный аудиосигнал от каждого микрофона для STT.')

# ===== SEC 7 =====
heading(doc, '7. ПЛАТФОРМА ВИДЕОКОНФЕРЕНЦИЙ', level=1)
para(doc, 'Без изменений. LiveKit (self-hosted, Apache 2.0).')
bullet(doc, 'Per-participant audio PCM 48kHz из коробки')
bullet(doc, 'Agents Framework — готовый паттерн для STT->NMT->TTS')
bullet(doc, 'Latency 0.5-1.5 сек vs 1-3 сек у Zoom')
bullet(doc, '$0 лицензий — self-hosted')

# ===== SEC 8 =====
heading(doc, '8. UX И АВТОРИЗАЦИЯ', level=1)
para(doc, 'Без изменений. Три способа авторизации: СКУД-карта (основной), QR-код (гости), гостевая карта. Интерфейс участника — 7" экран. Админ-панели: председатель и IT/AI.')

# ===== SEC 9 =====
heading(doc, '9. ФИНАЛЬНЫЕ РЕКОМЕНДАЦИИ (v1.2)', level=1)
update_note(doc, 'AI-стек полностью пересмотрен после fact-check.')

heading(doc, '9.1 AI-сервер', level=2)
bullet(doc, 'При гибридном TTS (Piper RU/EN + XTTS v2 HI) + квантизации NMT: 1x RTX 5090 (32GB)')
bullet(doc, 'При полном XTTS v2 на все языки: 2x RTX 5090 (64GB)')
bullet(doc, 'Обязателен benchmark full pipeline перед финальным выбором')

heading(doc, '9.2 AI-модели — финальный стек v1.2', level=2)

t2 = doc.add_table(rows=7, cols=4)
t2.style = 'Table Grid'
h2 = ['Компонент', 'v1.0', 'v1.1', 'v1.3 (финальный стек)']
r2 = [
    ['STT', 'faster-whisper + IndicWhisper LoRA', 'Qwen-ASR', 'Qwen3-ASR-1.7B (context biasing, Apache 2.0)'],
    ['STT fallback', '—', '—', 'faster-whisper + vad_filter=True + initial_prompt'],
    ['NMT HI->EN', 'IndicTrans2', 'IndicTrans2', 'IndicTrans2 (MIT, подтверждено)'],
    ['NMT EN<->RU / HI', 'NLLB-200 3.3B', 'MADLAD-400-3B', 'Qwen3-8B int4 (Apache 2.0, glossary in prompt)'],
    ['TTS EN/RU', 'VITS/Piper', 'VITS/Piper', 'Piper TTS (CPU, ~0 VRAM)'],
    ['TTS Hindi', 'VITS/Piper', 'Qwen TTS', 'XTTS v2 (нативный Hindi, 4-6GB)'],
]
for i, h in enumerate(h2):
    c = t2.rows[0].cells[i]
    c.text = h
    c.paragraphs[0].runs[0].bold = True
for r, rd in enumerate(r2):
    for c, v in enumerate(rd):
        t2.rows[r+1].cells[c].text = v
doc.add_paragraph()

warn(doc, 'Qwen3-TTS: отложить для EN/RU/ZH после оптимизации RT-фактора (сейчас 1.3x — неприемлемо для live). Не использовать для Hindi.')

# ===== SEC 10 =====
heading(doc, '10. СЛЕДУЮЩИЕ ШАГИ', level=1)
bullet(doc, '[ ] Собрать MVP pipeline: Qwen3-ASR-1.7B -> IndicTrans2 -> MADLAD-400 -> XTTS v2, замерить latency')
bullet(doc, '[ ] Проверить: latency до первого звука < 2 сек')
bullet(doc, '[ ] Тест XTTS v2 Hindi voice quality — оценить естественность')
bullet(doc, '[ ] Проверить лицензию XTTS v2 для коммерческого использования')
bullet(doc, '[ ] Тест Qwen3-TTS INT8/INT4 для RU/EN — снизить RT-фактор до <= 1x')
bullet(doc, '[ ] Реальный замер VRAM полного pipeline vs теоретический расчёт')
bullet(doc, '[ ] Убедиться: MADLAD-400 качество EN<->RU приемлемо для фарм-терминологии')

# ===== SEC 11 =====
heading(doc, '11. БЮДЖЕТ', level=1)
para(doc, 'Общий бюджет: ~$100,000 (10 млн руб.). При гибридном TTS + квантизации NMT: 1x RTX 5090 (~500K руб.) — вписывается в бюджет. Финальный пересчёт после benchmark.')

doc.add_paragraph()
para(doc, '--- КОНЕЦ ДОКУМЕНТА ---', bold=True)
para(doc, 'SyncVoice™ | Версия 1.3 | Март 2026 | КОНФИДЕНЦИАЛЬНО', italic=True)

out = '/home/clawdbot/.openclaw/workspace/drafts/SyncVoice_Tech_Guide_v1.3.docx'
doc.save(out)
print('OK:', out)
