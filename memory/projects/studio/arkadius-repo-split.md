# Аркадиус — Разделение репозиториев (v3)

> Обновлено: 2026-04-04

## Концепция

- `arkadius` ЗАВИСИТ от `arkadius-admin` — админка поставляет LLM и Sandbox
- `arkadius` имеет СВОЮ локальную БД для памяти
- Два режима: SaaS и On-prem

---

## Репозитории

### 1. arkadius (клиент + агент)

**Кто использует:** пользователь, может ставиться on-prem

```
apps/
  web/                    # Next.js UI
  agent/                  # Agent Core
    src/
      agent/              # orchestrator, loop, config
      llm/
        provider.py       # LLM client → ходит в arkadius-admin!
      tools/              # registry, web_search, memory_tools, browser, subagent
      memory/             # manager, snip, dream — СВОЯ ЛОКАЛЬНАЯ БД
      subagents/          # researcher, coder, scientist
      kairos/             # proactive watcher
      channels/           # telegram, vk, max, web
  api/                    # FastAPI — клиентский API
    src/
      core/
        config.py         # ADMIN_URL, ADMIN_API_KEY
        database.py       # ЛОКАЛЬНАЯ БД для памяти
      routes/
        auth.py           # локальная auth
        chat.py           # WebSocket чат
        files.py          # файлы
        memory.py         # API памяти для UI
        agents.py         # управление агентами
      services/
        admin_client.py   # HTTP клиент к arkadius-admin
docker-compose.yml        # postgres (память) + redis + api + web
```

**Что делает сам:**
- Память — своя локальная БД
- Agent loop, tools, subagents — локально
- Каналы — подключает сам
- UI, Auth — локально

**Что берёт от admin:**
- LLM ответы (через API)
- Sandbox (если нужен)
- Browser Pool (если нужен)

---

### 2. arkadius-admin (серверная инфра)

**Кто использует:** только команда/администратор

```
apps/
  admin-api/              # FastAPI — API для arkadius инстансов
    routes/
      llm.py              # LLM proxy → Anthropic API
      billing.py          # тарифы, лимиты, ЮKassa
      sandbox.py          # Docker sandbox per-client
      browser.py          # Browser Pool
      users.py            # управление клиентами/орг
      nodes.py            # мониторинг нод
      monitoring.py       # метрики, использование
      keys.py             # API ключи клиентов
    middleware/
      client_auth.py      # аутентификация arkadius инстансов
  admin-ui/               # Next.js — дашборд администратора
infra/
  docker-compose.yml      # PostgreSQL (биллинг), Redis, nginx
  nginx/
```

**Что поставляет клиентам:**
- LLM API (проксирует Anthropic)
- Sandbox (Docker)
- Browser Pool
- Биллинг (считает расход)
- Мониторинг

---

### 3. arkadius-node-server (Rust daemon)

Без изменений — daemon для подключения серверов как нод.

---

## Как arkadius подключается к admin

```python
# arkadius/apps/api/src/core/config.py
class Settings:
    ADMIN_URL: str  # ОБЯЗАТЕЛЬНЫЙ — без него не стартует
    ADMIN_API_KEY: str  # ОБЯЗАТЕЛЬНЫЙ

# arkadius/apps/agent/src/llm/provider.py
# НЕ ходит напрямую в Anthropic!
# Ходит в arkadius-admin
POST {ADMIN_URL}/api/llm/chat
  Headers: X-Client-Key: {ADMIN_API_KEY}
  Body: { messages, system, tools, model }
  → admin проксирует в Anthropic, считает токены
```

---

## API контракт arkadius-admin

```
# LLM
POST /api/llm/chat           — SSE стрим (проксирует Anthropic)
POST /api/llm/chat/sync      — синхронный запрос
GET  /api/llm/models          — доступные модели

# Billing  
GET  /api/billing/balance     — баланс клиента
GET  /api/billing/usage       — история расходов
POST /api/billing/check       — pre-flight check

# Sandbox
POST /api/sandbox/create      — создать контейнер
POST /api/sandbox/exec        — выполнить команду
DELETE /api/sandbox/{id}      — уничтожить

# Browser
POST /api/browser/acquire     — получить браузер
POST /api/browser/release     — вернуть
POST /api/browser/navigate    — навигация

# Auth
POST /api/auth/validate-key   — проверить ключ клиента
GET  /api/auth/client-info    — информация о клиенте
```

---

## Режимы деплоя

### SaaS
```
Наш сервер:
  arkadius (один инстанс, multi-tenant)
    → Agent loop × N юзеров (легковесные, async)
    → Память — PostgreSQL (multi-tenant по agent_id)
    → Sandbox НЕ постоянный — поднимается по требованию
    
  arkadius-admin
    → LLM proxy (Anthropic)
    → Billing per-user
    → Sandbox Pool (Docker по требованию — exec/код)
    → Browser Pool (по требованию)
  
Клиент:
  Браузер → наш web UI

Агент = легковесный async процесс. Sandbox = только когда нужен exec.
```

### On-prem
```
Наш сервер:
  arkadius-admin (Anthropic key, sandbox)
  
Сервер клиента:
  arkadius (своя PostgreSQL для памяти, свой Telegram бот)
    → подключается к нашему admin
```

### Enterprise (полностью автономный)
```
Сервер клиента:
  arkadius-admin (свой Anthropic key, свой sandbox)
  arkadius (своя память)
  Данные не покидают периметр
```

---

## План миграции

### Фаза 1: Перенести billing + infra в arkadius-admin
- `apps/api/src/routes/billing.py` → `arkadius-admin/apps/admin-api/routes/billing.py`
- `docker-compose.yml` (infra часть) → `arkadius-admin/infra/`
- `.env.example` (admin переменные) → `arkadius-admin/`

### Фаза 2: Переписать provider.py
- Сейчас: ходит напрямую в Anthropic API
- Нужно: ходит в `{ADMIN_URL}/api/llm/chat`
- Fallback: если ADMIN_URL не задан → прямой Anthropic (для dev)

### Фаза 3: Написать admin LLM proxy
- `arkadius-admin/apps/admin-api/routes/llm.py` — проксирует запросы в Anthropic
- Считает токены per-client
- SSE стрим passthrough

### Фаза 4: Admin UI
- Простой дашборд: клиенты, расход, метрики

### Фаза 5: Sandbox + Browser в admin
- Перенести sandbox управление
- Перенести browser pool
