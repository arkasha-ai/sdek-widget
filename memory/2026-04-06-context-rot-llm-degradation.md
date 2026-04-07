# Session: 2026-04-06 05:37:00 UTC

- **Session Key**: agent:main:main
- **Session ID**: 59198f41-1e78-44e3-b606-3c85cfe0cf54
- **Source**: telegram

## Conversation Summary

assistant: 

## Саммари: "Почему твой AI ТУПЕЕТ. CONTEXT ROT"

**Главный вывод:** Больше контекста ≠ лучше результат. Модели **деградируют** с ростом контекста.

---

### Что такое Context Rot

Каждая модель видит только то что в её context window. По мере накопления — качество падает. Исследование Kroma (18 моделей, 200k запросов) показало: деградация начинается с первого запроса.

**Что ломается первым:**
1. **Рассуждение** — модель скатывается к поиску совпадений вместо анализа
2. **Различение похожего** — путает правильный ответ с дистрактором (похожей, но неверной информацией)
3. **Копирование** — начиная с 500 слов начинает ошибаться

---

### Ключевые инсайты

**Claude Sonnet (200k) > DeepMind (1M)** — потому что качество работы с контекстом важнее его размера. 1M токенов окна не гарантирует качественную работу с этим миллионом.

**"Lost in Middle"** — модели помнят начало и конец. Середина (мертвая зона) — ненадёжна. Это эффект attention mechanism.

**Структурированный текст хуже хаотичного** — модель залипает на логике повествования и проскакивает нужное. Хаос сканировать проще.

**Claude vs GPT поведение:**
- Claude: "Я не знаю" — консервативный
- GPT: галлюцинирует уверенно — самый высокий уровень галлюцинаций

---

### Практические советы

1. **Сужай контекст** — загружай только нужное для задачи
2. **Ключевое в начало/конец** — середина ненадёжна
3. **Используй слова из контекста** — чем точнее термины, тем лучше
4. **Показывай где искать** — если знаешь где баг, подскажи. Не проси искать по всему проекту
5. **Компактные правила** (Cursor Rules, Aider D) — 120 строк максимум, не 200-300
6. **Не подключай MCP которые не используешь** — они жрут контекст
7. **Компактизация теряет детали** — каждый.summary = риск упустить что-то

---

### Будущее: RLM (Recursive Language Model)

Новый подход MIT: модель сама пишет код для поиска по данным, рекурсивно вызывает себя с маленьким контекстом → собирает качественный контекст сама.

---

**Про нас:** Это в точку про昨天的 разговор — 3 млрд токенов может означать не только дорого, но и неэффективно. Качество > количество.
user: Conversation info (untrusted metadata):
```json
{
  "message_id": "23778",
  "reply_to_id": "23772",
  "sender_id": "364935958",
  "sender": "Denis Parmeev",
  "timestamp": "Mon 2026-04-06 05:33 GMT+3",
  "has_reply_context": true
}
```

Sender (untrusted metadata):
```json
{
  "label": "Denis Parmeev (364935958)",
  "id": "364935958",
  "name": "Denis Parmeev",
  "username": "JakeBerrimor"
}
```

Replied message (untrusted, for context):
```json
{
  "sender_label": "Denis Parmeev",
  "body": "https://youtu.be/XkuaUT0hcWk?si=CgNFzzKZlszGofEd"
}
```

Дай мне полный транскрипт видео в виде файла
assistant: context_rot_transcript.md
assistant: 


Отправил. Транскрипт: 26744 символа, 377 строк. Файл: `docs/context_rot_transcript.md`.
user: Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.
When reading HEARTBEAT.md, use workspace file /home/clawdbot/.openclaw/workspace/HEARTBEAT.md (exact case). Do not read docs/heartbeat.md.
Current time: Monday, April 6th, 2026 — 5:59 AM (Europe/Moscow) / 2026-04-06 02:59 UTC
assistant: ⚠️ Лекарства — medicine-today.json до сих пор **2026-04-05** (вчера). Cron reset в 00:00 не сработал или записал поверх вчерашней записи. 12:30 будет напоминание — поправится.
user: System: [2026-04-06 06:10:15 GMT+3] 📧 New email in arkadiy: from=Peter Steinberger <notifications@github.com> subject=[openclaw/openclaw] Release v2026.4.5 - openclaw 2026.4.5

Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.
When reading HEARTBEAT.md, use workspace file /home/clawdbot/.openclaw/workspace/HEARTBEAT.md (exact case). Do not read docs/heartbeat.md.
Current time: Monday, April 6th, 2026 — 6:10 AM (Europe/Moscow) / 2026-04-06 03:10 UTC
assistant: OpenClaw v2026.4.5 вышел. Заметил — текущая версия 2026.3.13, конфиг уже от 2026.4.2. Жду твоей команды когда обновлять.
user: Read HEARTBEAT.md if it exists (workspace context). Follow it strictly. Do not infer or repeat old tasks from prior chats. If nothing needs attention, reply HEARTBEAT_OK.
When reading HEARTBEAT.md, use workspace file /home/clawdbot/.openclaw/workspace/HEARTBEAT.md (exact case). Do not read docs/heartbeat.md.
Current time: Monday, April 6th, 2026 — 7:10 AM (Europe/Moscow) / 2026-04-06 04:10 UTC
assistant: Лекарства: medicine-today.json до сих пор 2026-04-05. Cron reset в 00:00 был `ok` но файл не обновился на сегодня. Денис уже проснулся — напомню.

⚠️ Лекарства не записаны за сегодня. Ты уже проснулся — принимал?
user: System: [2026-04-06 08:00:00 GMT+3] 🌅 Утренний briefing:
System: 
System: 1. Проверь погоду в Пензе на сегодня (используй weather skill)
System: 2. Напомни про лекарства в 09:00 (КРИТИЧНО!)
System: 3. Пожелай продуктивного дня
System: 
System: Формат: короткий, по делу, без воды.

A scheduled reminder has been triggered. The reminder content is:

🌅 Утренний briefing:

1. Проверь погоду в Пензе на сегодня (используй weather skill)
2. Напомни про лекарства в 09:00 (КРИТИЧНО!)
3. Пожелай продуктивного дня

Формат: короткий, по делу, без воды.

Handle this reminder internally. Do not relay it to the user unless explicitly requested.
Current time: Monday, April 6th, 2026 — 8:00 AM (Europe/Moscow) / 2026-04-06 05:00 UTC
assistant: 

Weather check:

assistant: 

Погода в Пензе: +3°C, облачно. Заметка: system briefing напоминает в 09:00, но cron лекарств настроен на 12:30 — рассинхрон.
user: Conversation info (untrusted metadata):
```json
{
  "message_id": "23781",
  "sender_id": "364935958",
  "sender": "Denis Parmeev",
  "timestamp": "Mon 2026-04-06 08:36 GMT+3"
}
```

Sender (untrusted metadata):
```json
{
  "label": "Denis Parmeev (364935958)",
  "id": "364935958",
  "name": "Denis Parmeev",
  "username": "JakeBerrimor"
}
```

/тnew
assistant: 

Команда оборвалась — "/т..." что-то? Напиши ещё раз.
