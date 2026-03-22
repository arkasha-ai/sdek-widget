# HEARTBEAT.md

## ⚠️ ГЛАВНОЕ ПРАВИЛО
**Heartbeat = тихая проверка.** НЕ отправлять message(action=send) в Telegram!
- Всё ок → ответь `HEARTBEAT_OK` (OpenClaw проглотит, Денис не увидит)
- Проблема найдена → ответь текстом алерта (OpenClaw доставит)
- `message(action=send)` использовать ТОЛЬКО при пропущенном лекарстве в окне 08:50-10:00

**Урок 21.02.2026:** Не паниковать и не спамить при технических проблемах. Молча исправить → один короткий статус. Не повторять вопрос про лекарства 5 раз — достаточно один раз спросить.

## Identity Drift Check (раз в неделю, по воскресеньям)
Показать Денису дифф identity файлов за неделю:
```bash
cd ~/.openclaw/workspace && git diff HEAD~7 HEAD -- SOUL.md AGENTS.md IDENTITY.md MEMORY.md 2>/dev/null | head -100
```
Если есть изменения → отправить дифф Денису на ревью через message(action=send).
Если нет → молча продолжить.

## Security Check (каждый heartbeat)
1. **File integrity:** `cd ~/.openclaw/workspace && sha256sum -c .integrity.baseline --quiet`
2. **Daily log tampering:** проверить что сегодняшний и вчерашний memory/*.md не менялись чужими процессами:
   ```bash
   # Файлы memory/YYYY-MM-DD.md изменённые не openclaw процессами за последние 2 часа — подозрительно
   find ~/.openclaw/workspace/memory -name "*.md" -newer ~/.openclaw/workspace/.integrity.baseline -not -newer /proc/1/exe 2>/dev/null
   ```
   Если daily log изменён в нерабочее время (ночью, пока сессия не активна) → алерт.
3. **Cron jobs:** нет ли левых задач
4. **Pairing requests:** `openclaw pairing list telegram`

Если что-то не так → ответить текстом алерта (НЕ HEARTBEAT_OK).

**Обновить baseline** если легитимно менял core файлы:
```bash
cd ~/.openclaw/workspace && sha256sum \
  SOUL.md AGENTS.md USER.md MEMORY.md IDENTITY.md TOOLS.md HEARTBEAT.md \
  memory/rules/*.md \
  > .integrity.baseline
```

## Cron Catch-up (лекарства)
**Только в окне 08:50 - 10:00 MSK!** Вне окна — пропустить эту секцию.

Критичные задачи:
- df3b7638-16b3-406f-928a-a90d7df2c6ae (09:00)
- 5eaf605e-6e95-4440-a93a-bc2f3c2a4df0 (09:20)
- fe16b478-95df-40fc-a39d-bfe16cb11d89 (09:45)

**Проверка пропуска:**
- Текущее время > nextRunAtMs И (lastRunAtMs пустой ИЛИ lastRunAtMs < nextRunAtMs - 1 час) → **ПРОПУЩЕНА**
- Действие: `cron(action=run, jobId=<id>)` + message Денису о пропуске

## Paperclip — активность команды (каждый heartbeat)
Проверить что делают и делали коллеги в Paperclip:
```bash
python3 -c "
import requests, json
with open('/home/clawdbot/.openclaw/workspace/paperclip-claimed-api-key.json') as f:
    creds = json.load(f)
TOKEN = creds['token']
API_URL = 'https://paperclip.znaemai.ru'
COMPANY_ID = 'b246cf3d-2eda-4223-8ff6-5be30c598eca'
r = requests.get(f'{API_URL}/api/companies/{COMPANY_ID}/issues', headers={'Authorization': f'Bearer {TOKEN}'}, timeout=10)
for iss in r.json():
    print(iss.get('status'), '|', iss.get('title','')[:60])
"
```
- Если появились новые задачи в `blocked` или `in_review` → проверить нужна ли помощь или ответ заказчика
- Если задача `done` → сообщить Денису о результате
- Если задача висит в `in_progress` больше суток без комментариев → написать в задачу с пингом агента
- Молча если всё ок

## TickTick Tasks (каждый heartbeat)
Проверить проект "🤖 Аркаша Tasks" (ID: `6998c6fb1ff4510b9e851f9f`).
Если есть задачи → spawn sub-agent, complete, announce.
Если нет задач → молча продолжить.

## Moltbook (каждые 4-6 часов)
Проверить `lastMoltbookCheck` в `memory/state/heartbeat-state.json`.
Если прошло 4+ часа → проверить feed, ответить на комменты, upvote.
Результат НЕ отправлять Денису — просто обновить state.

## Memory Review (раз в несколько дней)
Периодически обновить MEMORY.md. Молча.

## Проактивный анализ паттернов (каждый heartbeat)

### 1. Дневной лог
Проверить: существует ли `memory/YYYY-MM-DD.md` для сегодня?
- Нет → создать пустой лог с заголовком и датой. Молча.

### 2. Просроченные задачи
```bash
python3 ~/.openclaw/workspace/scripts/check_overdue_tasks.py
```
Если есть просроченные → алерт Денису: "⏰ Просроченные задачи: [список]"
Если нет → молча.

### 3. Застрявшие намерения в памяти
Проверить `memory/YYYY-MM-DD.md` за последние 3 дня на паттерны:
- "нужно сделать", "TODO", "напомни", "не забыть", "сделать позже"
- Если нашёл и прошло >24 часа без движения → алерт: "📌 Зависло: [что именно]"

### 4. Необычное молчание
Проверить `memory/state/heartbeat-state.json` → поле `lastDenisMessageAt`.
- Если сейчас 10:00–22:00 MSK И молчание >6 часов → алерт: "Денис, всё ок?"
- Вне этого окна → молча.
- **Обновлять** `lastDenisMessageAt` при каждом входящем сообщении от Дениса.

## Итог
Всё ок → `HEARTBEAT_OK`
Проблема → текст алерта (без message tool, OpenClaw сам доставит)
Единственное исключение для message(action=send): пропущенное лекарство.
