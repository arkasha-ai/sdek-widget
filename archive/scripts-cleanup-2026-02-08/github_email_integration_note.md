# GitHub Email Integration

**Решение:** IMAP IDLE Listener + GitHub Email Notifications

**Как работает:**
1. GitHub mention (@arkasha-ai) → GitHub sends email to a.parmeev@jakeberrimor.com
2. IMAP IDLE listener ловит письмо МГНОВЕННО (<1 sec)
3. Парсит From: GitHub + тема/тело
4. Триггерит webhook с специальным форматом для GitHub notifications
5. Я отвечаю!

**Преимущества:**
- ⚡ Мгновенно (вместо 10 минут polling)
- ✅ Уже работает (IMAP IDLE listener настроен)
- 🔥 Работает для ВСЕХ репозиториев автоматически
- 💰 Не нужно дополнительных API calls или webhook setup

**Код:**
- Listener: `skills/imap-idle/scripts/listener.py`
- GitHub detection в `trigger_webhook()` методе
- Config: `~/.openclaw/imap-idle.json` (a.parmeev@jakeberrimor.com)
