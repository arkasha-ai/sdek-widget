# Email (Himalaya) 📬

## ⚠️ КРИТИЧНО

```bash
# ✅ ПРАВИЛЬНО
himalaya envelope list --account contact --page 1 --page-size 10

# ❌ НЕПРАВИЛЬНО (env var не работает!)
HIMALAYA_ACCOUNT=contact himalaya envelope list
```

## Аккаунты

| Account | Email |
|---------|-------|
| `dparmeev` | dparmeev@luminesfox.com (default) |
| `spam` | spam@jakeberrimor.com |
| `contact` | contact@jakeberrimor.com |
| `contact-lumines` | contact@luminesfox.com |
| `arkady` | a.parmeev@jakeberrimor.com (мой!) |

## Команды

```bash
# Список писем
himalaya envelope list --account contact --page 1 --page-size 5

# Прочитать
himalaya message read <id> --account contact

# Папки
himalaya folder list --account spam

# Отправить (MML формат)
himalaya message send --account arkady
```

## Мой email

- `a.parmeev@jakeberrimor.com` → account `arkady`
- Password: `~/.openclaw/secrets.env` → ARKADY_PASSWORD
- IMAP/SMTP: mail.hosting.reg.ru (993/587)
- Для регистраций, уведомлений, GitHub

## IMAP IDLE Listener

**Script:** `scripts/imap_idle_listener_v2.py`

Мониторит 4 аккаунта (НЕ arkady): dparmeev, spam, contact, contact-lumines.  
Триггерит webhook мгновенно (<1 sec) при новом письме.

```bash
# Проверить статус
ps aux | grep imap_idle_listener_v2

# Запустить вручную
python3 -u scripts/imap_idle_listener_v2.py
```

**Dependencies:** `pip3 install imapclient --user --break-system-packages`

**Webhook config** (`~/.openclaw/openclaw.json`):
```json
{"hooks": {"enabled": true, "token": "f016901f219067c9d30dea113c41576057c71e4d068d6363", "path": "/hooks"}}
```

**Keep-alive:** IDLE refresh каждые 15 мин, reconnect с backoff (5s → 300s).
