# Аркадиус — Разделение репозиториев (v3 FINAL)

> Обновлено: 2026-04-08

---

## Ключевое понимание

1. **`arkadius` ЗАВИСИТ от `arkadius-admin`** — админка поставляет LLM и Sandbox
2. **`arkadius` имеет СВОЮ локальную БД** для памяти (PostgreSQL или SQLite)
3. **Два режима деплоя:** SaaS и On-prem (+ Enterprise полностью автономный)

### Аналогия
- `arkadius-admin` = LiteLLM + Dokploy + Admin Panel (инфра-провайдер)
- `arkadius` = OpenClaw инстанс, который подключается к admin за LLM

---

## Репозитории

| Репо | Назначение | Кто деплоит |
|------|-----------|-------------|
| **ZnaemAI/arkadius** | Продукт: агент + UI + API + каналы + память | Мы (SaaS) или клиент (On-prem) |
| **ZnaemAI/arkadius-admin** | Инфра: LLM proxy, Sandbox, Browser Pool, Billing, Monitoring | Только мы |
| **ZnaemAI/arkadius-node-server** | Rust daemon для подключения серверов клиента как нод | Клиент (на своих серверах) |

---

## 1. arkadius (клиент + агент)

**Кто использует:** пользователь; может ставиться on-prem

### Что делает сам (автономно):
- **Память** — своя локальная БД (PostgreSQL/SQLite)
- **Agent loop, tools, subagents** — всё локально
- **Каналы** (Telegram, VK, MAX, Web) — подключает сам
- **UI** — Next.js
- **Auth** — локальная (или через admin SSO)

### Что берёт от admin:
- LLM ответы (через API) — клиент НЕ имеет свой ключ Anthropic
- Sandbox (если нужен code exec)
- Browser Pool (если нужен)

### Структура

```
arkadius/
├── apps/
│   ├── web/                          # Next.js UI
│   │   ├── app/
│   │   │   ├── (auth)/
│   │   │   │   ├── login/page.tsx
│   │   │   │   └── register/page.tsx
│   │   │   ├── (app)/
│   │   │   │   ├── chat/page.tsx          # @assistant-ui/react
│   │   │   │   ├── memory/page.tsx        # react-force-graph
│   │   │   │   ├── files/page.tsx
│   │   │   │   ├── billing/page.tsx       # recharts
│   │   │   │   └── settings/page.tsx
│   │   │   └── api/
│   │   │       ├── chat/route.ts          # WebSocket proxy
│   │   │       └── auth/[...all]/route.ts # better-auth
│   │   ├── components/
│   │   │   ├── chat/
│   │   │   │   ├── ChatThread.tsx
│   │   │   │   ├── ToolCallCard.tsx
│   │   │   │   └── StreamingMessage.tsx
│   │   │   ├── memory/
│   │   │   │   ├── MemoryGraph.tsx
│   │   │   │   └── MemoryEditor.tsx
│   │   │   └── ui/                        # shadcn
│   │   └── lib/
│   │       ├── api.ts                     # TanStack Query
│   │       ├── auth.ts                    # better-auth
│   │       └── store.ts                   # Zustand
│   │
│   ├── agent/                        # Agent Core (Python)
│   │   └── src/
│   │       ├── agent/
│   │       │   ├── agent_loop.py          # главный reasoning loop
│   │       │   ├── agent_manager.py       # CRUD агентов
│   │       │   ├── context_builder.py     # сборка LLM-контекста
│   │       │   ├── persona.py             # генерация system prompt
│   │       │   ├── dream.py               # autoDream — фоновая рефлексия
│   │       │   ├── kairos.py              # proactive tick-loop
│   │       │   ├── subagent_router.py     # маршрутизация к субагентам
│   │       │   └── subagent_pool.py       # lifecycle субагентов
│   │       │
│   │       ├── llm/
│   │       │   ├── provider.py            # ⚡ ходит в arkadius-admin за LLM!
│   │       │   └── context_manager.py     # подсчёт токенов, авто-компрессия
│   │       │
│   │       ├── tools/
│   │       │   ├── registry.py            # ToolRegistry + @register_tool
│   │       │   ├── base.py                # BaseTool ABC
│   │       │   ├── permission.py          # auto/manual/deny
│   │       │   └── builtin/
│   │       │       ├── web_search.py
│   │       │       ├── web_fetch.py
│   │       │       ├── code_exec.py       # → через admin sandbox
│   │       │       ├── memory_tools.py    # save/search/delete/list
│   │       │       ├── file_tools.py      # read/write/edit/glob/grep
│   │       │       ├── ask_user.py        # mid-task вопрос пользователю
│   │       │       └── browser.py         # → через admin browser pool
│   │       │
│   │       ├── memory/
│   │       │   ├── memory_manager.py      # CRUD + staleness + eviction
│   │       │   ├── memory_search.py       # pgvector семантический поиск
│   │       │   ├── compressor.py          # LLM-суммаризация
│   │       │   ├── snip.py                # бесплатная обрезка tool results
│   │       │   └── s3_snapshot.py         # бэкап состояния в S3
│   │       │
│   │       ├── subagents/
│   │       │   ├── researcher.py
│   │       │   ├── coder.py
│   │       │   └── scientist.py
│   │       │
│   │       ├── kairos/                    # proactive watcher
│   │       │   └── tick.py
│   │       │
│   │       ├── channels/
│   │       │   ├── base.py                # BaseChannel ABC
│   │       │   ├── router.py              # диспетчер → нужный агент
│   │       │   ├── media_pipeline.py      # image/audio/doc → S3
│   │       │   ├── web/handler.py         # REST + WebSocket
│   │       │   ├── telegram/handler.py    # aiogram 3.x webhook
│   │       │   ├── vk/handler.py          # VK Callback API
│   │       │   └── max/handler.py         # MAX Bot API
│   │       │
│   │       ├── groups/
│   │       │   ├── registry.py            # реестр участников
│   │       │   └── profile.py             # ephemeral state
│   │       │
│   │       ├── org/
│   │       │   ├── manager.py             # CRUD организаций
│   │       │   └── memory.py              # общая орг-память
│   │       │
│   │       ├── vault/
│   │       │   ├── manager.py             # CRUD секретов
│   │       │   └── encryption.py          # AES-256-GCM
│   │       │
│   │       ├── nodes/
│   │       │   ├── manager.py             # регистрация, пейринг
│   │       │   ├── executor.py            # exec через WebSocket
│   │       │   ├── protocol.py            # типы сообщений
│   │       │   ├── auth.py                # аутентификация нод
│   │       │   ├── reconnect.py           # exponential backoff
│   │       │   └── ssh_installer.py       # автоустановка по SSH
│   │       │
│   │       ├── tasks/
│   │       │   └── manager.py             # долгоживущие задачи
│   │       │
│   │       ├── mcp/
│   │       │   └── client.py              # MCP клиент (stdio/http)
│   │       │
│   │       └── integrations/
│   │           └── builder.py             # агент пишет свои интеграции
│   │
│   ├── api/                          # FastAPI — клиентский API
│   │   └── src/
│   │       ├── core/
│   │       │   ├── config.py              # ADMIN_URL, ADMIN_API_KEY
│   │       │   ├── database.py            # ЛОКАЛЬНАЯ БД (pg/sqlite)
│   │       │   ├── security.py            # JWT, пароли
│   │       │   ├── exceptions.py          # доменные ошибки
│   │       │   └── dependencies.py        # FastAPI DI
│   │       │
│   │       ├── routes/
│   │       │   ├── auth.py                # register/login/refresh
│   │       │   ├── chat.py                # POST /messages + SSE stream
│   │       │   ├── agents.py              # конфиг агента
│   │       │   ├── sessions.py            # CRUD сессий
│   │       │   ├── memory.py              # API памяти для UI
│   │       │   ├── files.py               # upload/download
│   │       │   ├── channels.py            # привязки каналов
│   │       │   ├── billing.py             # баланс, транзакции
│   │       │   ├── orgs.py                # организации
│   │       │   └── vault.py               # секреты (без значений)
│   │       │
│   │       ├── services/
│   │       │   └── admin_client.py        # HTTP клиент к arkadius-admin
│   │       │
│   │       └── websocket.py               # WS /ws/{token}
│   │
│   ├── worker/                       # Celery
│   │   ├── celery_app.py
│   │   └── tasks/
│   │       ├── dream_task.py
│   │       ├── kairos_task.py
│   │       └── subagent_task.py
│   │
│   └── billing/                      # Биллинг-логика
│       ├── credit_manager.py
│       ├── usage_tracker.py
│       ├── pricing.py
│       └── admin_key_mode.py          # MVP: один ключ, счётчик
│
├── infra/
│   ├── s3/
│   │   ├── client.py
│   │   └── storage.py
│   ├── cache/
│   │   └── redis.py
│   ├── anthropic_client.py            # low-level SDK wrapper
│   └── admin_client.py                # HTTP к arkadius-admin
│
├── models/
│   ├── user.py
│   ├── agent.py
│   ├── session.py
│   ├── memory.py                      # pgvector embeddings
│   ├── tool.py
│   ├── subagent.py
│   ├── billing.py
│   ├── channel.py
│   ├── organization.py
│   ├── agent_secret.py
│   ├── node.py
│   ├── task.py
│   ├── agent_integration.py
│   └── mcp_server.py
│
├── docker-compose.yml                 # postgres + redis + api + web + worker
├── .env.example
└── README.md
```

---

## 2. arkadius-admin (серверная инфра)

**Кто использует:** только мы (администраторы)

### Что поставляет клиентам:
- **LLM API** — проксирует Anthropic (клиент НЕ имеет свой ключ)
- **Sandbox** — Docker контейнеры по требованию
- **Browser Pool** — ~50 экземпляров, acquire/release
- **Биллинг** — считает расход, ЮKassa
- **Мониторинг** — метрики, алерты

### Структура

```
arkadius-admin/
├── apps/
│   ├── admin-api/                    # FastAPI — API для arkadius инстансов
│   │   ├── routes/
│   │   │   ├── llm.py                # LLM proxy → Anthropic API (SSE)
│   │   │   ├── billing.py            # тарифы, лимиты, ЮKassa webhook
│   │   │   ├── sandbox.py            # Docker sandbox per-client
│   │   │   ├── browser.py            # Browser Pool acquire/release
│   │   │   ├── users.py              # управление клиентами/орг
│   │   │   ├── nodes.py              # мониторинг нод
│   │   │   ├── monitoring.py         # метрики, использование
│   │   │   └── keys.py               # API ключи клиентов
│   │   ├── middleware/
│   │   │   └── client_auth.py        # X-Client-Key аутентификация
│   │   └── internal.py               # inter-service API (X-Internal-Token)
│   │
│   ├── admin-ui/                     # Next.js — дашборд администратора
│   │   ├── app/
│   │   │   ├── dashboard/page.tsx    # обзор системы
│   │   │   ├── clients/page.tsx      # список клиентов
│   │   │   ├── billing/page.tsx      # финансы
│   │   │   ├── monitoring/page.tsx   # метрики, логи
│   │   │   └── sandbox/page.tsx      # состояние контейнеров
│   │   └── components/
│   │
│   └── worker/
│       └── tasks/
│           └── sandbox_cleanup.py    # чистка idle контейнеров
│
├── sandbox/
│   ├── docker_manager.py             # lifecycle Docker контейнеров
│   └── exec_runner.py                # выполнение кода в sandbox
│
├── browser/
│   ├── pool.py                       # BrowserPool (acquire/release)
│   ├── state.py                      # save/restore cookies/localStorage
│   └── camoufox.py                   # anti-detect Firefox
│
├── billing/
│   └── yokassa.py                    # ЮKassa интеграция
│
├── litellm/
│   └── config_manager.py             # конфигурация LiteLLM proxy
│
├── monitoring/
│   └── dashboard.py                  # Prometheus + Grafana
│
├── infra/
│   ├── docker-compose.yml            # PostgreSQL, Redis, nginx, LiteLLM
│   └── nginx/
│
├── .env.example
└── README.md
```

---

## 3. arkadius-node-server (Rust daemon)

Устанавливается на серверы клиента. Подключается к arkadius по WebSocket.

```
arkadius-node-server/
├── src/
│   ├── main.rs
│   ├── ws_client.rs           # WebSocket клиент к arkadius
│   ├── exec.rs                # выполнение команд
│   ├── auth.rs                # аутентификация по node_token
│   └── protocol.rs            # типы сообщений (совпадают с Python)
├── install.sh                 # автоустановка + systemd
├── Cargo.toml
└── README.md
```

---

## Как arkadius подключается к admin

```python
# arkadius/apps/api/src/core/config.py
class Settings(BaseSettings):
    ADMIN_URL: str          # ОБЯЗАТЕЛЬНЫЙ — без него не стартует
    ADMIN_API_KEY: str      # ОБЯЗАТЕЛЬНЫЙ — ключ клиента

# arkadius/apps/agent/src/llm/provider.py
# НЕ ходит напрямую в Anthropic!
# Ходит в arkadius-admin:

async def complete(messages, tools, model, stream=True):
    response = await httpx.post(
        f"{ADMIN_URL}/api/llm/chat",
        headers={"X-Client-Key": ADMIN_API_KEY},
        json={"messages": messages, "tools": tools, "model": model},
        # SSE стрим
    )
    # admin проксирует в Anthropic, считает токены, проверяет лимиты

# Fallback для разработки:
# Если ADMIN_URL не задан → прямой Anthropic (для dev)
```

---

## API контракт: arkadius-admin

### LLM
```
POST /api/llm/chat              — SSE стрим (проксирует Anthropic)
POST /api/llm/chat/sync         — синхронный запрос
GET  /api/llm/models            — доступные модели для клиента
```

### Billing
```
GET  /api/billing/balance       — баланс клиента
GET  /api/billing/usage         — история расходов
POST /api/billing/check         — pre-flight check (хватит ли на запрос)
POST /api/billing/webhook/yokassa — webhook ЮKassa
```

### Sandbox
```
POST   /api/sandbox/create      — создать контейнер
POST   /api/sandbox/exec        — выполнить команду
DELETE /api/sandbox/{id}        — уничтожить
GET    /api/sandbox/status      — статус контейнера
```

### Browser Pool
```
POST /api/browser/acquire       — получить браузер из pool
POST /api/browser/release       — вернуть
POST /api/browser/action        — navigate/click/type/screenshot
```

### Auth
```
POST /api/auth/validate-key     — проверить ключ клиента
GET  /api/auth/client-info      — информация о клиенте
```

### Internal (inter-service, X-Internal-Token)
```
POST   /internal/sandbox/exec           — выполнить код
POST   /internal/sandbox/create         — создать sandbox
DELETE /internal/sandbox/{user_id}      — уничтожить
GET    /internal/billing/check/{user_id} — проверить баланс
POST   /internal/billing/webhook/yokassa — webhook ЮKassa
```

---

## Режимы деплоя

### SaaS (основной)
```
┌─── Наш сервер ──────────────────────────┐
│                                          │
│  arkadius (multi-tenant)                 │
│    → Agent loop × N юзеров (async)       │
│    → PostgreSQL (память per-agent)        │
│    → Next.js UI                          │
│                                          │
│  arkadius-admin                          │
│    → LLM proxy (Anthropic ключ)          │
│    → Sandbox Pool (Docker по требованию)  │
│    → Browser Pool (~50 экземпляров)       │
│    → ЮKassa биллинг                      │
│    → Admin Dashboard                     │
│                                          │
└──────────────────────────────────────────┘

Клиент: Браузер → наш web UI
```

### On-prem
```
┌─── Наш сервер ───────────┐     ┌─── Сервер клиента ─────────┐
│                           │     │                             │
│  arkadius-admin            │ ←── │  arkadius                   │
│    → LLM (Anthropic key)  │     │    → своя PostgreSQL        │
│    → Sandbox              │     │    → свой Telegram бот      │
│    → Browser Pool         │     │    → свой Next.js UI        │
│    → Биллинг              │     │    → ADMIN_URL=наш сервер   │
│                           │     │                             │
└───────────────────────────┘     └─────────────────────────────┘
```

### Enterprise (полностью автономный)
```
┌─── Сервер клиента ───────────────────────┐
│                                           │
│  arkadius-admin (свой Anthropic key)      │
│  arkadius (своя память, свои каналы)      │
│                                           │
│  Данные НЕ покидают периметр              │
│                                           │
└───────────────────────────────────────────┘
```

---

## Межсервисное взаимодействие

### 1. REST API (синхронное)

`arkadius` → `arkadius-admin` через HTTP.
Авторизация: `X-Client-Key` (публичный API) или `X-Internal-Token` (inter-service).

| arkadius вызывает | admin эндпоинт | Зачем |
|-------------------|---------------|-------|
| `llm/provider.py` | `POST /api/llm/chat` | LLM запросы |
| `tools/builtin/code_exec.py` | `POST /internal/sandbox/exec` | Выполнить код |
| `tools/builtin/browser.py` | `POST /api/browser/acquire` | Получить браузер |
| `billing/usage_tracker.py` | `GET /internal/billing/check/{user_id}` | Pre-flight баланс |

### 2. Redis Pub/Sub (асинхронное)

| Канал | Кто публикует | Кто слушает | Событие |
|-------|--------------|-------------|---------|
| `billing:topup:{user_id}` | admin (после ЮKassa) | arkadius | Пополнение → начислить |
| `sandbox:ready:{user_id}` | admin | arkadius | Sandbox готов |
| `sandbox:destroyed:{user_id}` | admin | arkadius | Sandbox уничтожен |
| `litellm:ratelimit` | admin | arkadius | Rate limit → backoff |

### 3. Общая PostgreSQL (опционально, SaaS only)

В SaaS-режиме оба сервиса могут работать с одной БД через разные схемы:
- `public` — arkadius (users, agents, memory, sessions)
- `admin` — arkadius-admin (litellm_config, sandbox_state, audit)

В On-prem — полностью раздельные БД.

---

## План миграции

### Фаза 1: Создать arkadius-admin репо (1 неделя)
- Инициализировать FastAPI проект
- Написать LLM proxy (`routes/llm.py`) — проксирует Anthropic с SSE
- Базовая аутентификация клиентов (`middleware/client_auth.py`)
- Docker compose: PostgreSQL + Redis + API
- Endpoint: `POST /api/llm/chat` → работает

### Фаза 2: Переписать provider.py в arkadius (2-3 дня)
- Сейчас: ходит напрямую в Anthropic
- Нужно: ходит в `{ADMIN_URL}/api/llm/chat`
- Fallback: если `ADMIN_URL` не задан → прямой Anthropic (dev режим)
- Тест: один E2E чат через admin proxy

### Фаза 3: Billing MVP (1 неделя)
- `admin_key_mode.py` в arkadius — простой счётчик токенов
- `routes/billing.py` в admin — баланс, usage
- Без ЮKassa пока — ручное пополнение

### Фаза 4: Sandbox в admin (1 неделя)
- Перенести Docker sandbox управление
- `sandbox/docker_manager.py` + `exec_runner.py`
- API: `POST /internal/sandbox/exec`
- arkadius → вызывает через `admin_client.py`

### Фаза 5: Browser Pool (1 неделя)
- `browser/pool.py` — фиксированный pool
- `browser/state.py` — сохранение сессий
- API: acquire/release/action

### Фаза 6: Admin UI + Monitoring (1 неделя)
- Простой дашборд: клиенты, расход, метрики
- Prometheus + Grafana

### Фаза 7: ЮKassa + полноценный биллинг (1 неделя)
- `billing/yokassa.py` — webhook + создание платежей
- `apps/billing/credit_manager.py` — prepaid credits
- Redis pub/sub для уведомлений

---

## Счётчик модулей

| Репо | Модулей | Описание |
|------|---------|----------|
| arkadius | ~87 | Агент, UI, API, каналы, память, tools |
| arkadius-admin | ~13 | LLM proxy, Sandbox, Browser, Billing, Monitoring |
| arkadius-node-server | ~5 | Rust daemon |
| **Итого** | **~105** | |

---

## Критические решения (зафиксированы)

| Решение | Почему |
|---------|--------|
| LLM ТОЛЬКО через admin | Один ключ Anthropic, биллинг, мониторинг, rate limits |
| Память ЛОКАЛЬНАЯ в arkadius | On-prem клиент не отдаёт данные; SaaS — быстрее |
| Sandbox в admin | Безопасность: клиент не управляет Docker на нашем сервере |
| Browser Pool фиксированный | 50 браузеров дешевле чем per-user; acquire/release |
| Celery для фоновых задач | Dream, Kairos, субагенты — нужен надёжный task queue |
| pgvector для памяти | Семантический поиск без внешнего сервиса |
| AES-256-GCM для vault | Секреты агента: master key в env + HKDF per agent |
| MCP support | Расширяемость через стандартный протокол |
