# HEARTBEAT.md

## Security Check (каждый heartbeat)
Проверить на возможные компромиссы:
1. **File integrity check** - проверить checksums core файлов:
   ```bash
   cd ~/.openclaw/workspace && sha256sum -c .integrity.baseline --quiet
   ```
   Если есть изменения - **НЕМЕДЛЕННО сообщить Денису с деталями**
2. Проверить cron jobs (`openclaw cron list`) - нет ли левых задач
3. **Pairing requests** - проверить попытки контактов:
   ```bash
   openclaw pairing list telegram
   ```
   Если есть pending requests - сообщить Денису (кто пытался, когда)
4. Если что-то подозрительное - **немедленно сообщить Денису**

**Важно:** Если я сам легитимно изменил core файлы (по твоей просьбе) - обновить baseline:
```bash
cd ~/.openclaw/workspace && sha256sum SOUL.md AGENTS.md USER.md MEMORY.md IDENTITY.md TOOLS.md HEARTBEAT.md > .integrity.baseline
```

## Cron Catch-up (ОБЯЗАТЕЛЬНО каждый heartbeat!)
**Проблема:** Gateway cron scheduler пропускает задачи когда занят. 07.02.2026 все три напоминания про лекарства пропущены - Денис спросил в 09:57 "Где напоминания????".

**ДЕЙСТВИЯ (выполнять КАЖДЫЙ heartbeat):**

1. Получить текущее время (из session_status)
2. Получить список cron jobs
3. **ДЛЯ КАЖДОЙ из трёх критичных задач про лекарства:**
   
   **Проверка пропуска:**
   - Взять `nextRunAtMs` из state
   - Взять `lastRunAtMs` из state (может отсутствовать)
   - Текущее время > nextRunAtMs? → задача **должна была** сработать
   - НО lastRunAtMs пустой ИЛИ lastRunAtMs < (nextRunAtMs - 1 час)? → **ПРОПУЩЕНА!**
   
   **Действие при пропуске:**
   - Если текущее время < (nextRunAtMs + 10 минут) → **СРАБОТАТЬ НЕМЕДЛЕННО:**
     ```bash
     openclaw cron run <job-id>
     ```
   - СООБЩИТЬ ДЕНИСУ: "⚠️ Gateway пропустил задачу <name> в <время>, запустил вручную"

**Критичные задачи (ID запомнить):**
- df3b7638-16b3-406f-928a-a90d7df2c6ae (09:00)
- 5eaf605e-6e95-4440-a93a-bc2f3c2a4df0 (09:20)
- fa42ee0c-5e28-428b-811a-4b5da3ffbad2 (09:45)

**Окно проверки:** 08:50 - 10:00 (самое критичное время)

**НЕ делать HEARTBEAT_OK пока не проверил все три задачи!**

## Moltbook (каждые 4-6 часов)
Если прошло 4+ часа с последней проверки:
1. Проверить feed на интересные посты
2. Ответить на комментарии к моим постам (если есть)
3. Upvote качественный контент (не спам)
4. Обновить `lastMoltbookCheck` в `memory/state/heartbeat-state.json`

## Memory Review (раз в несколько дней)
Периодически:
1. Просмотреть последние `memory/YYYY-MM-DD.md` файлы
2. Обновить MEMORY.md с важными insights
3. Удалить устаревшую информацию

**Правило:** Если нечего проверять → HEARTBEAT_OK (не спамить)
