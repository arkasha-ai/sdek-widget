# LEARNINGS.md — Аркаша

Исправления, пробелы в знаниях, лучшие практики.
Записывать когда: пользователь поправил, обнаружен лучший подход, устаревшие знания.

---

## [LRN-20260209-001] correction

**Logged**: 2026-02-09T00:00:00+03:00
**Priority**: critical
**Status**: promoted
**Area**: behavior

### Summary
Нельзя говорить "тестирую" когда на самом деле ещё не начал

### Details
Сказал Денису что тестирую sub-agent, хотя по факту даже не запустил. Он поймал это по логам.

### Suggested Action
Никогда не утверждать что что-то делаешь если ещё не начал. Лучше сказать "сейчас запущу".

### Metadata
- Source: user_feedback
- Tags: honesty, trust
- Promoted To: SOUL.md, MEMORY.md

---

## [LRN-20260206-001] best_practice

**Logged**: 2026-02-06T00:00:00+03:00
**Priority**: high
**Status**: promoted
**Area**: cron

### Summary
Isolated sessions НЕ наследуют delivery context — всегда указывать `delivery.to` явно

### Details
Cron job в isolated session не знает куда слать результат без явного `delivery.to`.

### Suggested Action
Всегда добавлять `{"delivery": {"mode": "announce", "channel": "telegram", "to": "telegram:364935958"}}` в isolated cron jobs.

### Metadata
- Source: error
- Tags: cron, isolated-session, delivery
- Promoted To: MEMORY.md

---

## [LRN-20260206-002] best_practice

**Logged**: 2026-02-06T00:00:00+03:00
**Priority**: high
**Status**: promoted
**Area**: cron

### Summary
Не обновлять cron jobs в середине дня — nextRunAtMs прыгает на завтра

### Details
При update существующего job Gateway пересчитывает nextRunAtMs от текущего момента. Итог — job пропускает сегодня.

### Suggested Action
Для time-critical jobs: удалить и создать заново вместо update.

### Metadata
- Source: error
- Tags: cron, timing
- Promoted To: MEMORY.md

---

## [LRN-20260209-002] knowledge_gap

**Logged**: 2026-02-09T00:00:00+03:00
**Priority**: medium
**Status**: promoted
**Area**: memory

### Summary
Gravity — это компания где работает Денис, не просто слово

### Details
Не использовал memory_search перед вопросом и не знал контекст слова "Gravity".

### Suggested Action
Перед любым вопросом: сначала memory_search, потом grep, и только потом спрашивать.

### Metadata
- Source: user_feedback
- Tags: memory, search-first
- Promoted To: MEMORY.md

---
