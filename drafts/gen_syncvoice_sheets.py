#!/usr/bin/env python3
"""Генерация SyncVoice_Tasks_Front_Back.xlsx — 2 листа: Frontend и Backend."""

import openpyxl
from openpyxl.styles import (
    Font, PatternFill, Alignment, Border, Side, GradientFill
)
from openpyxl.utils import get_column_letter

wb = openpyxl.Workbook()

# ─────────────────────────────────────────────
# ДАННЫЕ
# ─────────────────────────────────────────────

# Что уже готово из MVP-прототипа (backend-side)
DONE_ITEMS = {
    "SeamlessM4T v2 Docker (FP16, batch inference)": ("✅ Готово", "Перенесено в Phase 1"),
    "WebSocket API + batch inference (main_batch.py)": ("✅ Готово", "База для Translation Agent"),
    "Batch pipeline (asyncio Queue, grouping)": ("✅ Готово", "Переносится в LiveKit Agent"),
    "Базовый UI (index.html)": ("✅ Готово", "Заменяется React-клиентом"),
    "Нагрузочные тесты + RTF замеры": ("✅ Готово", "Зафиксированы в benchmark.md"),
    "Выбор и валидация архитектуры": ("✅ Готово", "3 подхода протестированы"),
}

FRONTEND_TASKS = [
    # Phase, id, module, tasks, status, hours, cost, notes
    # ── Готово ──────────────────────────────────────────────
    ("MVP / Прототип", "0.1", "Базовый UI", "index.html — вход в комнату, выбор языка, минимальный интерфейс", "✅ Готово", 8, 20_000, "Будет заменён React-клиентом"),

    # ── Phase 1 ─────────────────────────────────────────────
    ("Phase 1", "1.4", "Web-клиент (React)", "React + LiveKit Client SDK: вход в комнату, выбор языка, видео-галерея, управление микро/камерой, индикаторы состояния (говорит / обрабатывается / готово)", "⏳ Нужно сделать", 56, 140_000, "Ключевой юзер-facing компонент"),

    # ── Phase 2 ─────────────────────────────────────────────
    ("Phase 2", "2.2", "Auth — Frontend", "Формы логина/регистрации, управление пользователями, защита роутов по ролям", "⏳ Нужно сделать", 24, 60_000, "Зависит от 2.1 Backend"),
    ("Phase 2", "2.5", "Glossary UI", "Таблица терминов, импорт CSV/Excel, версии, поиск, редактирование", "⏳ Нужно сделать", 24, 60_000, "Зависит от 2.4 Backend"),
    ("Phase 2", "2.8", "Screen Sharing", "Переключение layout при демонстрации экрана через LiveKit", "⏳ Нужно сделать", 16, 40_000, ""),
    ("Phase 2", "2.9", "Admin Portal — дашборд", "React: активные конференции, число участников, GPU нагрузка, latency в реальном времени (WebSocket)", "⏳ Нужно сделать", 40, 100_000, "Зависит от 2.11 Admin API"),
    ("Phase 2", "2.10", "Admin Portal — управление", "Управление юзерами/ролями, глоссариями, настройки системы, white-label, история сессий, архив записей", "⏳ Нужно сделать", 32, 80_000, ""),
]

BACKEND_TASKS = [
    # Phase, id, module, tasks, role, status, hours, cost, notes
    # ── Готово ──────────────────────────────────────────────
    ("MVP / Прототип", "0.2", "SeamlessM4T v2 Docker", "FP16, batch inference, Docker-образ, GPU runtime", "ML-инженер", "✅ Готово", 40, 120_000, "Переносится в LiveKit Agent"),
    ("MVP / Прототип", "0.3", "WebSocket API (main_batch.py)", "Batch inference API, asyncio, WebSocket клиент", "Backend", "✅ Готово", 24, 72_000, "База для Translation Agent"),
    ("MVP / Прототип", "0.4", "Batch pipeline", "asyncio Queue, группировка по (src_lang, tgt_lang), fanout", "Backend", "✅ Готово", 32, 96_000, ""),
    ("MVP / Прототип", "0.5", "Нагрузочные тесты", "RTF замеры, стресс-тест concurrent speakers", "QA", "✅ Готово", 16, 48_000, "benchmark.md"),
    ("MVP / Прототип", "0.6", "Выбор архитектуры", "3 подхода, валидация, финальный выбор LiveKit", "Backend", "✅ Готово", 24, 72_000, ""),

    # ── Phase 1 ─────────────────────────────────────────────
    ("Phase 1", "1.1", "LiveKit SFU", "Развёртывание LiveKit Server в Docker, конфигурация портов, TLS, интеграция с Redis", "DevOps", "⏳ Нужно сделать", 16, 40_000, ""),
    ("Phase 1", "1.2", "Translation Agent", "Перенос batch pipeline в LiveKit Agents SDK: VAD (Silero), chunking, fanout по языкам, публикация TTS-треков", "ML-инженер", "⏳ Нужно сделать", 60, 180_000, "Ключевой AI-компонент"),
    ("Phase 1", "1.3", "Маршрутизация потоков", "Подписки по языкам (track subscription rules), фильтрация своего перевода, динамическое обновление", "Backend", "⏳ Нужно сделать", 32, 96_000, ""),
    ("Phase 1", "1.5", "Backend API", "FastAPI: создание/управление комнатами, генерация LiveKit токенов, REST endpoints", "Backend", "⏳ Нужно сделать", 24, 72_000, ""),
    ("Phase 1", "1.6", "Coturn (TURN/STUN)", "Настройка Coturn в Docker, интеграция с LiveKit, NAT traversal тесты", "DevOps", "⏳ Нужно сделать", 12, 30_000, ""),
    ("Phase 1", "1.7", "Docker Compose (MVP)", "LiveKit + Translation Agent + Redis + Coturn, GPU runtime", "DevOps", "⏳ Нужно сделать", 16, 40_000, ""),
    ("Phase 1", "1.8", "Интеграционное тестирование", "E2E: подключение, перевод, latency замеры, стресс concurrent speakers", "QA", "⏳ Нужно сделать", 32, 64_000, ""),

    # ── Phase 2 ─────────────────────────────────────────────
    ("Phase 2", "2.1", "Auth + роли", "JWT auth, роли (Админ, Модератор, Участник, Гость), управление юзерами CRUD, гостевой доступ по ссылке", "Backend", "⏳ Нужно сделать", 40, 120_000, ""),
    ("Phase 2", "2.3", "GlossaryAI", "Post-processing: trie/hash-lookup, правила замены, 'не переводить', фонетика, интеграция в pipeline", "ML-инженер", "⏳ Нужно сделать", 48, 144_000, "Фарм-терминология критична"),
    ("Phase 2", "2.4", "Glossary CRUD + Import", "API: создание/редактирование/удаление терминов, импорт CSV/Excel, версионирование, PostgreSQL", "Backend", "⏳ Нужно сделать", 32, 96_000, ""),
    ("Phase 2", "2.6", "Recording Service", "LiveKit Egress API: composite layout, захват TTS-дорожек по языкам, FFmpeg mux в MP4", "Backend", "⏳ Нужно сделать", 48, 144_000, "Клиент: 'интересует, цена решит'"),
    ("Phase 2", "2.7", "Recording — хранение", "Файловое хранилище, retention политика, API для скачивания, метаданные в PostgreSQL", "Backend", "⏳ Нужно сделать", 16, 48_000, ""),
    ("Phase 2", "2.11", "Admin API", "Метрики (GPU, latency), алерты, аудит-лог, настройки системы", "Backend", "⏳ Нужно сделать", 32, 96_000, ""),
    ("Phase 2", "2.12", "PostgreSQL schema", "Миграции: пользователи, сессии, глоссарии, записи, аудит-лог, настройки", "Backend", "⏳ Нужно сделать", 12, 36_000, ""),
    ("Phase 2", "2.13", "Тестирование Phase 2", "Auth, глоссарий, запись, admin portal; регресс Phase 1", "QA", "⏳ Нужно сделать", 40, 80_000, ""),

    # ── Phase 3 ─────────────────────────────────────────────
    ("Phase 3", "3.1", "Docker Compose (production)", "Финальный compose: все сервисы, health checks, restart policies, logging", "DevOps", "⏳ Нужно сделать", 24, 60_000, ""),
    ("Phase 3", "3.2", "TLS / безопасность", "Сертификаты, шифрование at rest, HTTPS для всех endpoints", "DevOps", "⏳ Нужно сделать", 20, 50_000, ""),
    ("Phase 3", "3.3", "Mac Studio деплой", "Translation Agent нативно (launchd + venv + MPS), остальное Docker Desktop", "DevOps", "⏳ Нужно сделать", 24, 60_000, ""),
    ("Phase 3", "3.4", "DGX Spark деплой", "Адаптация для DGX OS, тестирование GB10 Blackwell", "DevOps", "⏳ Нужно сделать", 16, 40_000, ""),
    ("Phase 3", "3.5", "Мониторинг + алерты", "Prometheus, Grafana (или Admin Portal), алерты на latency/GPU/падение", "DevOps", "⏳ Нужно сделать", 20, 50_000, ""),
    ("Phase 3", "3.6", "Документация — установка", "Инструкции для 4 конфигураций: A100/A10, RTX 4090/5090, Mac Studio, DGX Spark", "DevOps", "⏳ Нужно сделать", 24, 60_000, ""),
    ("Phase 3", "3.7", "Документация — пользователь", "Руководство: модератор, участник, администратор", "Backend", "⏳ Нужно сделать", 16, 48_000, ""),
    ("Phase 3", "3.8", "Документация — API", "OpenAPI spec, примеры интеграции", "Backend", "⏳ Нужно сделать", 12, 36_000, ""),
    ("Phase 3", "3.9", "Нагрузочное тестирование", "10–20 участников, 3 языка, latency, запись, глоссарий на production-железе", "QA", "⏳ Нужно сделать", 24, 48_000, ""),
    ("Phase 3", "3.10", "Приёмочное тестирование", "Чеклист по всем FR/NFR, баг-фиксы, финальная стабилизация", "QA", "⏳ Нужно сделать", 32, 64_000, ""),
]

# ─────────────────────────────────────────────
# СТИЛИ
# ─────────────────────────────────────────────

def make_border(style="thin"):
    s = Side(style=style)
    return Border(left=s, right=s, top=s, bottom=s)

def hdr_fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

STATUS_FILL = {
    "✅ Готово":        PatternFill("solid", fgColor="D6F5D6"),
    "⏳ Нужно сделать": PatternFill("solid", fgColor="FFF9E6"),
    "🔄 В работе":      PatternFill("solid", fgColor="D6EEFF"),
}
STATUS_FONT = {
    "✅ Готово":        Font(color="1A7A1A", bold=True),
    "⏳ Нужно сделать": Font(color="9B6A00", bold=True),
    "🔄 В работе":      Font(color="0059A3", bold=True),
}
PHASE_COLOR = {
    "MVP / Прототип": "E8E0FF",
    "Phase 1":        "D6EAF8",
    "Phase 2":        "D5F5E3",
    "Phase 3":        "FDEBD0",
}

thin_border = make_border("thin")
thick_border = make_border("medium")

def style_header_row(ws, row, cols, bg_hex, text_hex="FFFFFF"):
    fill = hdr_fill(bg_hex)
    font = Font(bold=True, color=text_hex, size=11)
    for col in range(1, cols + 1):
        cell = ws.cell(row=row, column=col)
        cell.fill = fill
        cell.font = font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = thin_border

def style_data_cell(cell, wrap=True, center=False):
    cell.alignment = Alignment(
        horizontal="center" if center else "left",
        vertical="center",
        wrap_text=wrap
    )
    cell.border = thin_border

def write_phase_header(ws, row, phase, num_cols, color):
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=num_cols)
    c = ws.cell(row=row, column=1)
    c.value = f"  {phase}"
    c.fill = hdr_fill(color)
    c.font = Font(bold=True, size=11, color="333333")
    c.alignment = Alignment(horizontal="left", vertical="center")
    c.border = thin_border

# ─────────────────────────────────────────────
# ЛИСТ 1: FRONTEND
# ─────────────────────────────────────────────

ws_f = wb.active
ws_f.title = "🎨 Frontend"
ws_f.sheet_view.showGridLines = False
ws_f.row_dimensions[1].height = 40

FRONT_COLS = ["Фаза", "#", "Модуль", "Задачи", "Статус", "Часы", "Стоимость", "Примечание"]
FRONT_WIDTHS = [14, 5, 22, 52, 18, 7, 14, 28]

# ── Заголовок листа ──
ws_f.merge_cells("A1:H1")
title_cell = ws_f["A1"]
title_cell.value = "SyncVoice™ — Frontend задачи"
title_cell.fill = hdr_fill("2E4057")
title_cell.font = Font(bold=True, size=14, color="FFFFFF")
title_cell.alignment = Alignment(horizontal="center", vertical="center")
title_cell.border = thin_border

ws_f.row_dimensions[2].height = 32
style_header_row(ws_f, 2, len(FRONT_COLS), "4A90D9")
for col_idx, hdr in enumerate(FRONT_COLS, 1):
    ws_f.cell(row=2, column=col_idx, value=hdr)

# ── Данные ──
row = 3
current_phase = None
for task in FRONTEND_TASKS:
    phase, tid, module, tasks, status, hours, cost, notes = task

    if phase != current_phase:
        ws_f.row_dimensions[row].height = 22
        write_phase_header(ws_f, row, phase, len(FRONT_COLS), PHASE_COLOR.get(phase, "EEEEEE"))
        row += 1
        current_phase = phase

    ws_f.row_dimensions[row].height = 52
    vals = [phase, tid, module, tasks, status, hours, f"{cost:,} ₽".replace(",", " "), notes]
    for col_idx, val in enumerate(vals, 1):
        c = ws_f.cell(row=row, column=col_idx, value=val)
        style_data_cell(c, wrap=True, center=(col_idx in [1, 2, 5, 6, 7]))
        if col_idx == 5 and status in STATUS_FILL:
            c.fill = STATUS_FILL[status]
            c.font = STATUS_FONT[status]
        elif col_idx == 1:
            c.fill = hdr_fill(PHASE_COLOR.get(phase, "FFFFFF"))
            c.font = Font(bold=True, size=9, color="555555")
        elif col_idx == 3:
            c.font = Font(bold=True)
    row += 1

# ── Итого ──
ws_f.row_dimensions[row].height = 28
total_h = sum(t[5] for t in FRONTEND_TASKS)
total_c = sum(t[6] for t in FRONTEND_TASKS)
done_h  = sum(t[5] for t in FRONTEND_TASKS if t[4] == "✅ Готово")
done_c  = sum(t[6] for t in FRONTEND_TASKS if t[4] == "✅ Готово")
todo_h  = total_h - done_h
todo_c  = total_c - done_c

ws_f.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
c = ws_f.cell(row=row, column=1, value="ИТОГО (Frontend)")
c.fill = hdr_fill("2E4057"); c.font = Font(bold=True, color="FFFFFF"); c.alignment = Alignment(horizontal="center", vertical="center"); c.border = thin_border

for col, val in [(4, f"Всего: {total_h}ч / {total_c:,}₽  |  Готово: {done_h}ч / {done_c:,}₽  |  Осталось: {todo_h}ч / {todo_c:,}₽".replace(",", " ")),
                  (5, ""), (6, total_h), (7, f"{total_c:,} ₽".replace(",", " ")), (8, "")]:
    c2 = ws_f.cell(row=row, column=col, value=val)
    c2.fill = hdr_fill("2E4057"); c2.font = Font(bold=True, color="FFFFFF")
    c2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c2.border = thin_border

# ── Ширины колонок ──
for i, w in enumerate(FRONT_WIDTHS, 1):
    ws_f.column_dimensions[get_column_letter(i)].width = w

# ─────────────────────────────────────────────
# ЛИСТ 2: BACKEND
# ─────────────────────────────────────────────

ws_b = wb.create_sheet("⚙️ Backend")
ws_b.sheet_view.showGridLines = False
ws_b.row_dimensions[1].height = 40

BACK_COLS = ["Фаза", "#", "Модуль", "Задачи", "Роль", "Статус", "Часы", "Стоимость", "Примечание"]
BACK_WIDTHS = [14, 5, 22, 50, 13, 18, 7, 14, 28]

ws_b.merge_cells("A1:I1")
title_cell2 = ws_b["A1"]
title_cell2.value = "SyncVoice™ — Backend задачи"
title_cell2.fill = hdr_fill("1B3A4B")
title_cell2.font = Font(bold=True, size=14, color="FFFFFF")
title_cell2.alignment = Alignment(horizontal="center", vertical="center")
title_cell2.border = thin_border

ws_b.row_dimensions[2].height = 32
style_header_row(ws_b, 2, len(BACK_COLS), "27AE60")
for col_idx, hdr in enumerate(BACK_COLS, 1):
    ws_b.cell(row=2, column=col_idx, value=hdr)

ROLE_COLOR = {
    "Backend":    "E8F4FD",
    "ML-инженер": "F3E8FF",
    "DevOps":     "FEF9E7",
    "QA":         "FDEDEC",
}

row = 3
current_phase = None
for task in BACKEND_TASKS:
    phase, tid, module, tasks, role, status, hours, cost, notes = task

    if phase != current_phase:
        ws_b.row_dimensions[row].height = 22
        write_phase_header(ws_b, row, phase, len(BACK_COLS), PHASE_COLOR.get(phase, "EEEEEE"))
        row += 1
        current_phase = phase

    ws_b.row_dimensions[row].height = 52
    vals = [phase, tid, module, tasks, role, status, hours, f"{cost:,} ₽".replace(",", " "), notes]
    for col_idx, val in enumerate(vals, 1):
        c = ws_b.cell(row=row, column=col_idx, value=val)
        style_data_cell(c, wrap=True, center=(col_idx in [1, 2, 5, 6, 7, 8]))
        if col_idx == 6 and status in STATUS_FILL:
            c.fill = STATUS_FILL[status]
            c.font = STATUS_FONT[status]
        elif col_idx == 5 and role in ROLE_COLOR:
            c.fill = hdr_fill(ROLE_COLOR[role])
            c.font = Font(bold=True, size=9)
        elif col_idx == 1:
            c.fill = hdr_fill(PHASE_COLOR.get(phase, "FFFFFF"))
            c.font = Font(bold=True, size=9, color="555555")
        elif col_idx == 3:
            c.font = Font(bold=True)
    row += 1

# ── Итого Backend ──
ws_b.row_dimensions[row].height = 28
total_h = sum(t[6] for t in BACKEND_TASKS)
total_c = sum(t[7] for t in BACKEND_TASKS)
done_h  = sum(t[6] for t in BACKEND_TASKS if t[5] == "✅ Готово")
done_c  = sum(t[7] for t in BACKEND_TASKS if t[5] == "✅ Готово")
todo_h  = total_h - done_h
todo_c  = total_c - done_c

ws_b.merge_cells(start_row=row, start_column=1, end_row=row, end_column=4)
c = ws_b.cell(row=row, column=1, value="ИТОГО (Backend + DevOps + QA + ML)")
c.fill = hdr_fill("1B3A4B"); c.font = Font(bold=True, color="FFFFFF"); c.alignment = Alignment(horizontal="center", vertical="center"); c.border = thin_border

for col, val in [(5, ""), (6, f"Готово: {done_h}ч"), (7, total_h), (8, f"{total_c:,} ₽".replace(",", " ")),
                 (9, f"Осталось: {todo_h}ч / {todo_c:,}₽".replace(",", " "))]:
    c2 = ws_b.cell(row=row, column=col, value=val)
    c2.fill = hdr_fill("1B3A4B"); c2.font = Font(bold=True, color="FFFFFF")
    c2.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True); c2.border = thin_border

for i, w in enumerate(BACK_WIDTHS, 1):
    ws_b.column_dimensions[get_column_letter(i)].width = w

# ─────────────────────────────────────────────
# СОХРАНИТЬ
# ─────────────────────────────────────────────
out = "/home/clawdbot/.openclaw/workspace/drafts/SyncVoice_Tasks_Front_Back.xlsx"
wb.save(out)
print(f"Saved: {out}")
