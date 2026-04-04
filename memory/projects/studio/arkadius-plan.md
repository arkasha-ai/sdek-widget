# Аркадиус — Техническая и продуктовая документация

> **Версия:** 2.0 | **Дата:** 2026-04-03  
> **Статус:** Активная разработка — старт 04.04.2026

---

## Содержание

1. [Концепция](#1-концепция)
2. [Команда и сроки](#2-команда-и-сроки)
3. [Архитектура](#3-архитектура)
4. [Агентная модель](#4-агентная-модель)
5. [Память](#5-память)
6. [Каналы и голос](#6-каналы-и-голос)
7. [Технологический стек](#7-технологический-стек)
8. [Репозитории](#8-репозитории)
9. [1-недельный roadmap](#9-1-недельный-roadmap)
10. [Монетизация](#10-монетизация)
11. [Масштабирование](#11-масштабирование)
12. [Конкуренты](#12-конкуренты)
13. [Риски](#13-риски)

---

## 1. Концепция

**Аркадиус** — SaaS-платформа где каждый пользователь получает персонального AI-агента с изолированной памятью, файлами и командой субагентов. Общение через текст, голос, файлы — через веб, Telegram, ВК, MAX.

**Ключевое отличие:** не чат-бот, а полноценный агент с файловой системой, командой субагентов, памятью между сессиями и проактивным поведением. Как личный сотрудник, а не окно чата.

**Не VTuber** — это отдельный продукт, не связанный с Аркадиусом.

---

## 2. Команда и сроки

- **Denis Parmeev** — product, архитектура, решения
- **Аркаша** — AI-разработка, реализация
- Максим/Дмитрий — подключаем позже по решению

**MVP срок: 1 неделя** (старт 04.04.2026)  
Обоснование: используем `nano-claude-code` как основу + паттерны из Claude Code утечки как blueprint. Большинство сложных проблем уже решено — адаптируем под наш стек.

---

## 3. Архитектура

### 3.1 Два репозитория

**`arkadius`** — продуктовый (пользовательский):
```
apps/
  web/          # Next.js — интерфейс пользователя
  agent/        # Agent Runner (Python FastAPI)
  api/          # Fastify/FastAPI — auth, chat, files
packages/
  shared/       # типы, утилиты
```

**`arkadius-admin`** — инфра (внутренний, только Денис видит):
```
apps/
  dashboard/    # Админка: пользователи, баланс, мониторинг
  billing/      # ЮKassa webhooks, транзакции
  inference/    # LiteLLM конфиг + роутинг моделей
infra/
  docker-compose.yml
  nginx/
  litellm/
```

LiteLLM — только в `arkadius-admin`. В продуктовом репо нет.

### 3.2 Обзор сервисов

```
┌─────────────────────────────────────────────────────┐
│              Load Balancer (Nginx)                  │
└──────┬──────────────┬──────────────┬────────────────┘
       │              │              │
 ┌─────▼─────┐  ┌────▼────┐  ┌─────▼──────┐
 │  Next.js  │  │   API   │  │  LiveKit   │
 │   (web)   │  │ Gateway │  │  Server    │
 └───────────┘  └────┬────┘  └─────┬──────┘
                      │             │
               ┌──────▼─────────────▼──────┐
               │      Control Plane        │
               │      (FastAPI Python)     │
               └───┬───────┬──────┬────────┘
                   │       │      │
          ┌────────▼┐ ┌───▼──┐ ┌─▼──────────┐
          │  Agent  │ │Redis │ │ PostgreSQL  │
          │  Pool   │ │      │ │             │
          │(Python) │ │      │ │             │
          └────┬────┘ └──────┘ └─────────────┘
               │
        ┌──────▼──────┐
        │  LiteLLM    │  (в arkadius-admin)
        │  Proxy      │
        └──────┬──────┘
               │
         ┌─────▼─────┐
         │  Claude   │
         │ Anthropic │
         └───────────┘
```

### 3.3 Sandbox и ноды

**Два типа выполнения кода агентом:**

**1. Нода пользователя (приоритет)**
- Пользователь подключает свой сервер/машину как ноду
- Агент выполняет код на ноде через WebSocket туннель
- Бесплатно для пользователя — его инфраструктура
- Два способа подключения:
  - SSH-нода: пользователь даёт SSH доступ → система сама заходит и разворачивает Rust daemon
  - Клиентская нода: пользователь ставит `arkadius-node-server` на своей машине

**2. Облачный sandbox (fallback)**
- Нет ноды → поднимается Docker контейнер в облаке Аркадиуса
- Pay-as-you-go: оплата кредитами за время использования
- Уровни:
  - **Micro:** 1 vCPU, 512MB RAM
  - **Small:** 2 vCPU, 2GB RAM
  - **Medium:** 4 vCPU, 8GB RAM

**Почему это важно:**
- Агент может писать и выполнять интеграции (IntegrationBuilder)
- Организации с нодой = данные не покидают их инфраструктуру (152-ФЗ)
- Мотивация подключить ноду: дешевле + быстрее + приватнее

---

### 3.4 Изоляция агентов

Каждый пользователь = отдельный процесс Agent Runner:
- Изолированный workspace `/data/agents/{user_id}/`
- Linux namespaces (pid, net, mount) через `unshare`
- cgroups v2 — лимиты CPU/RAM на процесс
- Cold start < 500ms
- Sleep через 10 мин бездействия

### 3.5 БД схема (PostgreSQL)

```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),
    display_name VARCHAR(100),
    telegram_id BIGINT UNIQUE,
    vk_id BIGINT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

CREATE TABLE credit_balances (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    balance_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_spent_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_purchased_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount_credits DECIMAL(12,4) NOT NULL,
    amount_rub DECIMAL(10,2),
    payment_provider VARCHAR(50) DEFAULT 'yookassa',
    payment_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE token_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    model VARCHAR(100) NOT NULL,
    tokens_input INT NOT NULL,
    tokens_output INT NOT NULL,
    cost_credits DECIMAL(10,6) NOT NULL,
    session_id VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE agent_configs (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    agent_name VARCHAR(100) DEFAULT 'Ассистент',
    default_model VARCHAR(100) DEFAULT 'claude-sonnet',
    system_prompt TEXT,
    enabled_tools JSONB DEFAULT '["web_search","read","write"]',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## 4. Агентная модель

### 4.1 Принцип: один главный + команда под капотом

Пользователь всегда говорит только с **Главным агентом**. Главный сам решает когда и кого из субагентов вызвать.

```
Пользователь → [Главный Агент]
                     │
         ┌───────────┼────────────┐
         ▼           ▼            ▼
    [Ресёрчер]  [Кодер]     [Учёный]
    (субагент)  (субагент)  (субагент)
```

**Философия:** модель решает, harness исполняет. Минимальная оркестрация, максимальная свобода модели.

### 4.2 Субагенты

| Субагент | Роль |
|----------|------|
| **Ресёрчер** | Поиск в интернете, сбор информации |
| **Кодер** | Написание и выполнение кода |
| **Аналитик** | Анализ данных, документов |
| **Учёный** | Особая роль — см. ниже |

### 4.3 Учёный — особый субагент

**Три функции Учёного:**

1. **Failure handler** — получает задачи с которыми не справился Главный. Анализирует почему, ищет подходы, пишет решение.

2. **Skill writer** — замечает повторяющиеся паттерны пользователя → пишет скилл → предлагает добавить. Например: "Ты 10 раз просил сводку новостей — создать автоматический скилл?"

3. **Prompt optimizer** — улучшает системные промпты субагентов на основе реального использования.

Пользователь может видеть статус: "Учёный работает над этим..."

### 4.4 KAIROS — проактивный режим

Заменяет простой heartbeat. Агент сам пишет пользователю когда:
- Нашёл что-то полезное
- Напоминание сработало
- Заметил паттерн поведения

Технически:
- Tick-промпты на регулярном интервале
- Лимит 15 сек на любое проактивное действие
- Режим Brief — краткие ответы, не флудить
- Append-only дневник наблюдений

---

## 5. Память

### 5.1 Четыре уровня (по паттерну Claude Code)

| Уровень | Описание | Реализация |
|---------|----------|------------|
| **SOUL.md / USER.md** | Явные инструкции, личность агента | Файл, загружается при старте |
| **Auto-notes** | Агент пишет заметки во время сессий | `.md` с YAML frontmatter |
| **Session memory** | Context window текущей сессии | В памяти процесса |
| **autoDream** | Фоновая консолидация между сессиями | Celery task |

### 5.2 autoDream — консолидация памяти

**Трёхгейтовый триггер** (все три должны пройти):
- ⏱ 24 часа с последнего "сна"
- 📊 Минимум 5 сессий накопилось
- 🔒 Lock свободен (нет параллельных снов)

**Четыре фазы:**
1. **Orient** — ls памяти, читает MEMORY.md, сканирует topic-файлы
2. **Gather** — grep по дневникам и транскриптам, ищет новое
3. **Consolidate** — пишет/обновляет файлы памяти, конвертирует "вчера" в даты
4. **Prune** — держит MEMORY.md ≤ 200 строк / 25KB

Субагент работает отдельно, read-only доступ к истории.

### 5.3 Открытая память

Пользователь видит MEMORY.md и может:
- Читать что агент о нём знает
- Редактировать записи
- Удалять

Это строит доверие — "стеклянная голова".

---

## 6. Каналы и голос

### 6.1 Каналы

| Канал | MVP | v0.2 |
|-------|-----|------|
| Веб | ✅ | ✅ |
| Telegram | ✅ | ✅ |
| ВКонтакте | ✅ | ✅ |
| MAX | ✅ | ✅ |

Единая память — агент один, точки входа разные.

### 6.2 Голосовые звонки (v0.2)

**Личный звонок:**
```
Нажал "Позвонить" → LiveKit room → STT → LLM → TTS → голос агента
```

**Конференция с командой:**
- Агент подключается к звонку как участник
- Слушает весь разговор
- Отвечает на вопросы ("Аркадиус, найди...")
- После — автоматически summary + action items

**TTS:** нейтральный, Edge TTS (Dmitry/Darya), бесплатно.

**v0.2 — Групповой режим:**
- Агент заходит в группы по ссылке (Telegram, VK, MAX)
- Без тега — сам решает когда отвечать (KAIROS в групповом чате)
- Двухуровневая модель участников:
  - Реестр (легкий, все участники): id, имя, роль, последняя активность, краткая заметка
  - Профили активных (в контекст только текущие собеседники)
- Новый участник → запись в реестре → при 3+ сообщениях формируется профиль
- В контекст: активные участники диалога + краткий реестр остальных

**v0.3 — Подключение к телеконференциям:**
- Телемост (Яндекс), Zoom, Google Meet
- Архитектура: LiveKit SIP trunk → конференция
- Агент получает ссылку → подключается как участник → слушает всех → отвечает голосом
- После встречи: автоматический summary + action items

---

## 7. Технологический стек

### 7.1 Backend

- **Язык:** Python 3.12
- **Framework:** FastAPI (async)
- **ORM:** SQLAlchemy async + Alembic
- **Queue:** Celery + Redis (или ARQ)
- **Agent Runner:** чистый Python async, на базе `nano-claude-code`

### 7.2 Agent Runner — ядро

```python
class AgentRunner:
    def __init__(self, user_id: str, config: AgentConfig):
        self.user_id = user_id
        self.memory = MemoryManager(user_id)
        self.tools = ToolRegistry()
        self.llm = LLMClient(config.model)
    
    async def run(self, message: str) -> AsyncGenerator[str, None]:
        context = await self.memory.load_context()
        
        while True:
            response = await self.llm.complete(
                system=context,
                messages=self.history,
                tools=self.tools.schemas()
            )
            
            if response.stop_reason == "end_turn":
                yield response.text
                break
                
            for tool_call in response.tool_calls:
                result = await self.tools.execute(
                    tool_call.name,
                    tool_call.args
                )
                self.history.append(tool_result(result))
        
        await self.memory.log(message, response.text)
```

### 7.3 Frontend

- **Framework:** Next.js 15 (App Router)
- **UI:** Tailwind CSS + shadcn/ui
- **Real-time:** WebSocket стриминг ответов

### 7.4 LLM

- **MVP:** только Anthropic Claude (Sonnet) — без Qwen, без GPT пока
- **Роутинг:** LiteLLM (в arkadius-admin)
- **Биллинг:** success_callback → PostgreSQL

### 7.5 Инфраструктура MVP (только РФ)

| Компонент | Где | Стоимость |
|-----------|-----|-----------|
| API + Agent Pool | FirstVDS (8 vCPU, 16GB) | ~2500₽/мес |
| PostgreSQL + Redis | Тот же сервер | — |
| LiveKit | FirstVDS | ~800₽/мес |
| S3 (persistent, файлы) | FirstVDS S3 ✅ уже есть | — |
| **Итого** | | **~3300₽/мес** |

### 7.6 Sandbox для агентов

Каждый пользователь получает изолированный Docker контейнер:
```
/agent/{user_id}/
  sandbox/          # эфемерный (рабочая директория задачи)
  persistent/       # постоянный, монтируется из S3
    packages/       # установленные pip/npm пакеты
    tools/          # утилиты (ffmpeg, pandoc и т.д.)
    bin/            # скрипты агента
    data/           # данные пользователя
```

**Монтирование S3 через rclone:**
```bash
rclone mount firstvds:arkadius/agents/{user_id} /agent \
  --allow-other \
  --vfs-cache-mode writes
```

**БД метаданные пакетов:**
```sql
CREATE TABLE agent_packages (
    user_id UUID REFERENCES users(id),
    package_name VARCHAR,
    package_type VARCHAR,  -- pip, npm, binary
    installed_at TIMESTAMPTZ
);
```

### 7.7 152-ФЗ и передача данных

**Хранение:** все данные пользователей на серверах FirstVDS (РФ) ✅

**Anthropic API:** запросы уходят на серверы Anthropic (США). По 152-ФЗ передача данных за рубеж разрешена при наличии согласия пользователя.

**Решение для MVP:** явное согласие в пользовательском соглашении:
> "Ваши запросы обрабатываются с использованием сервисов Anthropic PBC (США)"

**Для B2B enterprise (v1.0):** self-hosted модель на сервере в РФ — данные не покидают страну.

---

## 8. Репозитории

- **GitHub организация:** создаёт Денис 04.04.2026, добавляет `arkasha-ai`
- **`ZnaemAI/arkadius`** — бэкенд (Python FastAPI) + веб (Next.js) (private)
- **`ZnaemAI/arkadius-admin`** — инфра, LiteLLM, биллинг (private)
- **`ZnaemAI/arkadius-node-server`** — Rust daemon для серверных нод (SSH и клиентский режим) (private)
- **Основа Agent Runner:** https://github.com/SafeRL-Lab/nano-claude-code

### Другие полезные репозитории из Claude Code утечки:

| Репо | Что взять |
|------|-----------|
| https://github.com/SafeRL-Lab/nano-claude-code | Agent loop, tool registry, memory, SubAgentManager |
| https://github.com/shareAI-lab/learn-claude-code | Концепция harness = tools + knowledge + permissions |
| https://github.com/ultraworkers/claw-code | query_engine.py — референс agent loop |
| https://github.com/chauncygu/collection-claude-code-source-code | Оригинальный TS + анализ архитектуры |

---

## 9. 1-недельный roadmap

| День | Задача |
|------|--------|
| **День 1 (04.04)** | Org + репо, scaffolding монорепо, БД схема, Agent Runner скелет |
| **День 2 (05.04)** | Tool system (exec, read, write, web_search), Memory Manager |
| **День 3 (06.04)** | FastAPI: auth, chat endpoint, WebSocket стриминг |
| **День 4 (07.04)** | LiteLLM + billing (ЮKassa webhook), pre-flight check |
| **День 5 (08.04)** | Next.js: чат UI, биллинг, открытая память |
| **День 6 (09.04)** | autoDream + KAIROS, Telegram канал |
| **День 7 (10.04)** | Деплой Hetzner + smoke test + фикс багов |

---

## 10. Монетизация

**Модель:** Prepaid кредиты. 1 кредит = 1 рубль.

**Платёжная система:** только ЮKassa (Россия, рубли). Stripe — не в MVP.

**Пакеты:**

| Пакет | Цена | Кредиты | Бонус |
|-------|------|---------|-------|
| Старт | 199₽ | 199 | — |
| Базовый | 499₽ | 550 | +10% |
| Про | 999₽ | 1200 | +20% |
| Бизнес | 2999₽ | 3900 | +30% |

**ЦА:** только Россия в MVP.

**Sandbox тарификация:**
- Своя нода: exec бесплатно
- Облачный sandbox: X кредитов за минуту (по уровням Micro/Small/Medium)

**Защита:**
- Pre-flight check перед каждым LLM вызовом
- Нулевой баланс = стоп
- Лимит 100K tokens на сессию

---

## 11. Масштабирование

### До 1K пользователей (MVP)
- ~50-100 одновременных агентов
- RAM: 100 × 50MB = 5GB + система = 8GB достаточно
- Один сервер Hetzner CPX41

### До 10K пользователей
- 2× Agent Worker серверов (16GB RAM каждый)
- Отдельный PostgreSQL + Redis
- ~€200/мес инфра

### До 100K пользователей
- Kubernetes (k3s или managed)
- PostgreSQL read replicas + PgBouncer
- Redis Cluster
- ~€2500/мес инфра

> Важно: 90% расходов — LLM API, не инфра. Оптимизация промптов = главный рычаг.

---

## 12. Конкуренты

| Продукт | Слабое место |
|---------|-------------|
| ChatGPT | Нет памяти, нет настоящих инструментов |
| Claude | То же самое |
| Replika | Развлечение, нет практической пользы |
| Lindy.ai | $50+/мес, нет персонализации |
| OpenClaw | Нужен сервер, технические навыки |

**Наша ниша:** OpenClaw для всех — мощь self-hosted агента без технических навыков, с памятью и командой субагентов.

---

## 13. Риски

| Риск | Митигация |
|------|-----------|
| Anthropic меняет API | LiteLLM абстракция, можно переключить |
| Низкая retention | Sticky memory — чем больше используешь, тем полезнее |
| OOM при 500+ агентах | Агрессивный sleep, swap на NVMe |
| Утечка данных между агентами | Process-level изоляция обязательна |
| Prepaid убыток | By design невозможен — сначала оплата |

---

*Обновлено: 2026-04-03. Следующее обновление после первой недели разработки.*
