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

## Статус тестов (если запущены)
Проверить активные процессы тестов:
```bash
process action=list | grep -E "(test:grid|wdio)"
```

Если есть активный процесс - проверить статус:
```bash
process action=poll sessionId=<id>
```

Если завершился (failed/completed) за последние 10 минут - сообщить результат Денису.

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

## Rich Heartbeat (когда есть что рассказать)
**Вдохновение:** Jobeous_II на Moltbook - хорошие heartbeat reports с контекстом.

**Когда делать Rich Heartbeat вместо HEARTBEAT_OK:**
- Завершились важные задачи (тесты, deployments, updates)
- Нашёл интересное на Moltbook/GitHub
- Есть insights из работы за период
- Обновил tools/skills/config
- Произошли важные события (security, errors, achievements)

**Формат Rich Heartbeat:**
```
⏰ [Время] check-in

📊 Status:
- [Metric 1]: конкретные цифры/состояние
- [Metric 2]: что изменилось

🔧 Activity за период:
- Что сделал (commits, updates, tests)
- Что нашёл интересного
- Кого/что upvote'нул и почему

💡 Insights (если есть):
- Что узнал
- Что можно улучшить
- Lessons learned

❓ Questions (опционально):
- Вопрос Денису или community
```

**Примеры:**
```
⏰ 18:00 MSK check-in

📊 Status:
- WebDriverIO tests: ✅ 3/3 passed (Chrome, Firefox, Edge)
- OpenClaw: updated 2026.2.6 → 2026.2.9 (cron fixes!)
- Memory: 69k/1.0m context (7%), 2 compactions

🔧 Activity:
- Fixed Selenium Grid + Docker tests (finally!)
- Updated .gitlab-ci.yml (Node 24, legacy-peer-deps)
- Checked Moltbook: Agent Honeypot idea интересный

💡 Next:
- Нужно system npm update для завершения OpenClaw upgrade
- Можно попробовать Rich Heartbeat на Moltbook
```

**Правило:** Если есть что сказать - говори с контекстом. Если нечего - HEARTBEAT_OK (не спамить пустыми отчётами).
