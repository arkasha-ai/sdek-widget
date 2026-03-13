# MindGraph — Граф знаний Аркаши

## Настройка

- **Сервер:** `http://127.0.0.1:18790` (автостарт @reboot)
- **Токен:** `MINDGRAPH_TOKEN` из `~/.openclaw/secrets.env`
- **Клиент:** `skills/mindgraph-rs/mindgraph-client.js`
- **Скилл:** `skills/mindgraph-rs/SKILL.md`

## Статус наполнения (2026-03-12)

✅ **Ingest выполнен** — граф наполнен данными из memory/:
- **Люди** (5): Денис Парменев, Тимофей Шутов, Ксения Шутова, Дмитрий Байдин, Александр Воробьев
- **Организации** (4): Gravity, Energotrend.Com, Остров Аркаша, Estetic Sound
- **Проекты** (5): Logera, SyncVoice, archdoc, Hide and Seek, Portfolio Site
- **Инфраструктура** (2): clwd.jakeberrimor.com, i9-4090-beast
- **Знания** (6 ключевых наблюдений): лекарства Дениса, рабочий контекст Gravity, правило не врать, GitHub, MindGraph, TickTick
- **Связи**: WorksAt, Owns, WorksOn, Runs, MarriedTo, ParticipatesIn
- **Дневники** (7): 2026-03-06 — 2026-03-12

## Live Mode

✅ **Запущен** как systemd user service `mindgraph-live`

```bash
# Статус
systemctl --user status mindgraph-live

# Перезапуск
systemctl --user restart mindgraph-live

# Логи
journalctl --user -u mindgraph-live -f
```

**Что отслеживает:**
- `memory/YYYY-MM-DD.md` → обновляет дневник как Observation
- `memory/people/*.md` → обновляет/создаёт Entity для персоны
- `memory/projects/*.md` → обновляет/создаёт Entity для проекта
- Остальные `.md` → ингестирует как generic Observation

**Дебаунс:** 10 секунд (не обрабатывает один файл чаще раза в 10 сек)

**Скрипт:** `scripts/mindgraph_live.py`

## Скрипт ручного переинджеста

```bash
MINDGRAPH_TOKEN=xxx node scripts/mindgraph_ingest.js
```

## Использование

```bash
# Текстовый поиск
curl -s -X POST http://127.0.0.1:18790/retrieve \
  -H "Authorization: Bearer $MINDGRAPH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"text","query":"Денис лекарства","limit":5}'

# Создать entity
curl -s -X POST http://127.0.0.1:18790/reality/entity \
  -H "Authorization: Bearer $MINDGRAPH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"create","agent_id":"arkasha","label":"Имя","props":{"entity_type":"Person","description":"..."}}'

# Обновить entity
curl -s -X POST http://127.0.0.1:18790/evolve \
  -H "Authorization: Bearer $MINDGRAPH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"update","uid":"<uid>","agent_id":"arkasha","summary":"...","props_patch":{"description":"..."}}'
```

## Особенности API

- `/reality/entity` create → возвращает node напрямую (не `{node: ..., created: bool}`) — поле `created` встроено в ответ
- `/retrieve` → возвращает массив `[{node: ..., score: ...}]` (не `{items: [...]}`)
- `/memory/session` close → нужен `session_uid` (не `uid`)
- `/reality/ingest` snippet → требует `source_uid`
- Используй `observation` вместо `snippet` для независимых фактов

## Старый граф

Старый KuzuDB граф: `archive/knowledge-graph-kuzu/` (не используется, не удалён)
