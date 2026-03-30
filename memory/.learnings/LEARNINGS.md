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

---

## [LRN-20260329-001] correction

**Logged**: 2026-03-29T20:31:00+03:00
**Priority**: critical
**Status**: active
**Area**: behavior

### Summary
Не пушить код без локальной проверки. Сначала тест — потом push.

### Details
Во время дебага бэкенда product-card-generator несколько раз пушил фиксы не проверив их локально. В результате деплоились нерабочие изменения, Денис был справедливо зол.

Правильный порядок:
1. Написал изменение
2. Запустил локально с реальными ENV (`DATABASE_URL`, `REDIS_URL` из .env)
3. Убедился что работает (curl /health, нет ошибок в логах)
4. Только тогда `git commit && git push`

### Suggested Action
Перед каждым пушем бэкенд-изменений — запускать `uvicorn` локально и проверять `/health`. Для bot.py — `python bot.py` и смотреть что нет ImportError.

### Metadata
- Source: user_feedback (Denis + Mikhail)
- Tags: testing, discipline, no-push-without-test

---

## [META-001] Принцип: Понимание > Угадывание

**Logged**: 2026-03-29
**Priority**: critical
**Area**: behavior

Если не понимаешь как система работает — СТОП.
10 минут документации < 5 часов слепых попыток.
"Try to figure it out" = пойми систему, не угадывай перебором.

---

## [META-002] Принцип: Observability перед работой

**Logged**: 2026-03-29
**Priority**: critical
**Area**: deploy, debugging

Перед началом работы: убедись что можешь видеть результат.
- Нет логов? Нет shell? Нет UI? → Сначала реши проблему видимости.
- Контейнер упал при старте через Dokploy UI → логов через `docker logs` нет. Смотреть через Logs вкладку в UI.
- Не просить то что физически недоступно.

---

## [META-003] Dokploy — как работает

**Logged**: 2026-03-29
**Area**: deploy, infrastructure

- Контейнеры в Dokploy изолированы в своей сети
- Managed сервисы (Postgres, Redis) в `dokploy-network`
- Чтобы app видел managed сервисы → `networks: dokploy-network: external: true` в compose
- Логи контейнера: только через Dokploy UI → вкладка Logs. `docker logs` CLI недоступен через веб.
- Skill: `skills/dokploy/SKILL.md` — читать ДО деплоя

