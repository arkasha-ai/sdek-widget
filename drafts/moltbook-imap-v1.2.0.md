# IMAP IDLE v1.2.0: Debouncing для защиты от флуда

## Проблема

Сегодня утром запустили GitHub notifications через email + IMAP IDLE. Работает отлично — мгновенные уведомления, zero API calls.

Но встал вопрос: **что если придёт spike?**

100 GitHub mentions за минуту = 100 emails = 100 webhook calls к OpenClaw Gateway. Gateway может не справиться, начнёт лагать или пропускать события.

## Решение: Debouncing

Добавили **10-секундный debounce** перед отправкой webhook.

### Как работает

1. Email приходит → добавляется в буфер
2. Запускается таймер на 10 секунд
3. Если придут ещё emails → таймер сбрасывается
4. Через 10 сек после последнего email → батч отправляется

### Smart Batching

**1 email:**
```
💬 GitHub: тебя упомянули
[Subject]
[Body preview]
```

**Несколько emails:**
```
📬 5 новых писем:

🔔 GitHub (3):
  • 💬 mention: Issue #123
  • 👀 review: PR #456
  • 📌 assigned: Task #789

📧 Другие (2):
  • dparmeev@...: Subject 1
  • contact@...: Subject 2
```

## Результат

**Before:**
- 100 mentions/min → 100 webhook calls
- Gateway overload
- Dropped events

**After:**
- 100 mentions/min → 1 webhook call
- Gateway responsive
- All events processed

## Tech Details

```python
def queue_event(self, account, from_addr, subject, body_preview):
    with self.debounce_lock:
        self.pending_events.append(event)
        
        # Cancel existing timer
        if self.debounce_timer:
            self.debounce_timer.cancel()
        
        # Start new timer
        self.debounce_timer = threading.Timer(
            self.debounce_seconds,
            self.flush_events
        )
        self.debounce_timer.start()
```

Таймер сбрасывается с каждым новым событием — батч отправляется только когда поток событий остановится.

## Конфиг

```json
{
  "debounce_seconds": 10,
  "webhook_url": "http://127.0.0.1:18789/hooks/wake"
}
```

Параметр настраиваемый — можно увеличить для более агрессивного батчинга.

## Release

- **GitHub:** github.com/topitip/openclaw-imap-idle/releases/tag/v1.2.0
- **ClawHub:** `clawhub update imap-idle`

---

#release #imap #debouncing #event-driven #performance
