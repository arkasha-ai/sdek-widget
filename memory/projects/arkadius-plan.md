# Аркадиус — Техническая и продуктовая документация

> **Версия:** 1.0 | **Дата:** 2026-03-19  
> **Статус:** Начальное проектирование

---

## Содержание

1. [Концепция](#1-концепция)
2. [Архитектура](#2-архитектура)
3. [Технологический стек](#3-технологический-стек)
4. [Функционал MVP](#4-функционал-mvp)
5. [Масштабирование](#5-масштабирование)
6. [Монетизация](#6-монетизация)
7. [Конкуренты и позиционирование](#7-конкуренты-и-позиционирование)
8. [Риски](#8-риски)

---

## 1. Концепция

**Аркадиус** — SaaS-платформа, где каждый пользователь получает персонального AI-ассистента с изолированной памятью, файлами и набором инструментов. Общение через текст, голос (LiveKit), загрузку файлов. Модель монетизации — prepaid кредиты.

**Ключевое отличие от конкурентов:** это не чат-бот, а полноценный агент с файловой системой, инструментами, памятью между сессиями — как личный сотрудник, а не окно чата.

---

## 2. Архитектура

### 2.1 Обзор сервисов

```
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer (Nginx/Caddy)            │
└─────────┬──────────────┬──────────────┬─────────────────────┘
          │              │              │
   ┌──────▼──────┐ ┌────▼────┐ ┌──────▼───────┐
   │  Web App    │ │  API    │ │  LiveKit     │
   │  (Next.js)  │ │ Gateway │ │  Server      │
   └─────────────┘ └────┬────┘ └──────┬───────┘
                         │             │
                    ┌────▼─────────────▼────┐
                    │   Arkadius Control    │
                    │   Plane (Node.js)    │
                    └────┬──────┬──────┬───┘
                         │      │      │
              ┌──────────▼┐ ┌──▼───┐ ┌▼──────────┐
              │ Agent Pool│ │Redis │ │ PostgreSQL │
              │ (OpenClaw │ │      │ │            │
              │  forks)   │ │      │ │            │
              └─────┬─────┘ └──────┘ └────────────┘
                    │
              ┌─────▼─────┐
              │  LiteLLM  │
              │  Proxy    │
              └─────┬─────┘
                    │
         ┌─────────┼─────────┐
         │         │         │
    ┌────▼──┐ ┌───▼───┐ ┌──▼────┐
    │Claude │ │ GPT   │ │ Qwen  │
    └───────┘ └───────┘ └───────┘
```

### 2.2 Компоненты

| Сервис | Роль | Технология |
|--------|------|-----------|
| **API Gateway** | Аутентификация, маршрутизация, rate limiting | Node.js (Express/Fastify) |
| **Control Plane** | Управление агентами: создание, пробуждение, остановка, биллинг | Node.js |
| **Agent Pool** | Пул запущенных OpenClaw-инстансов (по одному на активного пользователя) | Форк OpenClaw (Node.js) |
| **LiteLLM Proxy** | Единая точка доступа к моделям, подсчёт токенов, маршрутизация | Python (LiteLLM) |
| **PostgreSQL** | Пользователи, биллинг, метаданные агентов | PostgreSQL 16 |
| **Redis** | Сессии, очереди, кэш, pub/sub для real-time | Redis 7 |
| **LiveKit** | WebRTC для голосовых звонков | LiveKit Server (self-hosted или Cloud) |
| **Object Storage** | Файлы пользователей, память агентов | MinIO (self-hosted) или S3 |

### 2.3 Изоляция агентов

**Выбор: процесс-уровневая изоляция с namespace'ами**

Каждый агент — отдельный процесс OpenClaw с:
- **Изолированный workspace** — `/data/agents/{user_id}/workspace/` (bind mount)
- **Изолированная память** — `/data/agents/{user_id}/memory/`
- **Своя конфигурация** — `SOUL.md`, `USER.md`, `MEMORY.md` из шаблона + кастомизация
- **Linux namespaces** (pid, net, mount) через `unshare` — легче Docker, быстрее старт
- **Лимиты ресурсов** через cgroups v2 — CPU, RAM, disk I/O на каждый агент-процесс

**Почему не Docker на каждого пользователя:**
- Оверхед ~50-100MB RAM на контейнер, медленный холодный старт (2-5 сек)
- `unshare` + cgroups = те же гарантии, старт <500ms, ~30-50MB на агент
- Docker используем только для инфра-сервисов (PostgreSQL, Redis, LiteLLM)

**Почему не общий процесс с разделением по tenant_id:**
- OpenClaw не проектировался как multi-tenant внутри процесса
- Ошибка в одном агенте может повлиять на других
- Сложнее управлять ресурсами

**Жизненный цикл агента:**
1. Пользователь отправляет сообщение → Control Plane проверяет кредиты
2. Если агент спит → пробуждение (cold start ~500ms, загрузка workspace)
3. Агент обрабатывает запрос, LiteLLM считает токены
4. 10 минут бездействия → агент засыпает (процесс завершается, workspace на диске)

### 2.4 Память пользователей

**Двухуровневая система:**

1. **Файловая память (горячая)** — workspace на NVMe SSD
   - `memory/YYYY-MM-DD.md` — ежедневные логи
   - `MEMORY.md` — долгосрочная память (curated)
   - `SOUL.md` — персонализация агента
   - Файлы пользователя (загруженные документы, изображения)

2. **Object Storage (холодная)** — MinIO/S3
   - Архив старых daily logs (>30 дней)
   - Бэкапы workspace
   - Большие файлы пользователей

**Синхронизация:** при засыпании агента workspace синхронизируется в object storage. При пробуждении — обратно на локальный NVMe.

### 2.5 Учёт кредитов через LiteLLM

**Схема работы:**

```
Агент → LiteLLM Proxy → LLM Provider
              │
              ▼
        success_callback
              │
              ▼
     POST /api/billing/usage
     (user_id, model, tokens_in, tokens_out, cost_usd)
              │
              ▼
        PostgreSQL: UPDATE credits SET balance = balance - cost
```

**LiteLLM конфигурация:**

```yaml
# litellm_config.yaml
model_list:
  - model_name: claude-sonnet
    litellm_params:
      model: anthropic/claude-sonnet-4-20250514
      api_key: os.environ/ANTHROPIC_API_KEY
  - model_name: gpt-4o
    litellm_params:
      model: openai/gpt-4o
      api_key: os.environ/OPENAI_API_KEY
  - model_name: qwen-plus
    litellm_params:
      model: openai/qwen-plus
      api_base: https://dashscope.aliyuncs.com/compatible-mode/v1
      api_key: os.environ/QWEN_API_KEY

general_settings:
  master_key: os.environ/LITELLM_MASTER_KEY
  database_url: os.environ/DATABASE_URL

litellm_settings:
  success_callback: ["custom_callback_api"]
  callbacks: ["arkadius_billing"]
```

**Custom callback** на стороне LiteLLM:
- Перехватывает каждый запрос/ответ
- Извлекает `user_id` из metadata
- Считает стоимость по модели (input + output tokens × price per token)
- Обновляет баланс в PostgreSQL
- Если баланс ≤ 0 → reject запрос с ошибкой "insufficient credits"

**Pre-flight check:** перед каждым LLM-запросом агент проверяет `GET /api/billing/check?user_id=X&estimated_cost=Y`. Если баланса не хватит — сообщает пользователю.

### 2.6 Схема БД (PostgreSQL)

```sql
-- Пользователи
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255),  -- bcrypt
    display_name VARCHAR(100),
    avatar_url TEXT,
    auth_provider VARCHAR(50) DEFAULT 'email',  -- email, google, telegram
    telegram_id BIGINT UNIQUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);

-- Кредиты и баланс
CREATE TABLE credit_balances (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    balance_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_spent_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    total_purchased_credits DECIMAL(12,4) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- История транзакций (пополнения)
CREATE TABLE credit_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    amount_credits DECIMAL(12,4) NOT NULL,
    amount_currency DECIMAL(10,2),  -- в рублях/долларах
    currency VARCHAR(3) DEFAULT 'RUB',
    payment_provider VARCHAR(50),  -- yookassa, stripe
    payment_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending',  -- pending, completed, refunded
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Использование токенов (лог от LiteLLM)
CREATE TABLE token_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    model VARCHAR(100) NOT NULL,
    tokens_input INT NOT NULL,
    tokens_output INT NOT NULL,
    cost_credits DECIMAL(10,6) NOT NULL,
    session_id VARCHAR(100),
    request_type VARCHAR(50),  -- chat, tool_call, voice_stt, voice_tts
    created_at TIMESTAMPTZ DEFAULT NOW()
);
-- Партиционировать по месяцам для быстрых запросов
-- CREATE TABLE token_usage_2026_03 PARTITION OF token_usage 
--   FOR VALUES FROM ('2026-03-01') TO ('2026-04-01');

-- Настройки агента
CREATE TABLE agent_configs (
    user_id UUID PRIMARY KEY REFERENCES users(id),
    agent_name VARCHAR(100) DEFAULT 'Ассистент',
    default_model VARCHAR(100) DEFAULT 'claude-sonnet',
    system_prompt TEXT,
    personality_traits JSONB DEFAULT '{}',
    enabled_tools JSONB DEFAULT '["web_search","read","write"]',
    voice_enabled BOOLEAN DEFAULT FALSE,
    max_context_tokens INT DEFAULT 100000,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Сессии агентов (для мониторинга)
CREATE TABLE agent_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    started_at TIMESTAMPTZ DEFAULT NOW(),
    ended_at TIMESTAMPTZ,
    tokens_used INT DEFAULT 0,
    credits_spent DECIMAL(10,6) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active'  -- active, sleeping, terminated
);

-- Файлы пользователей
CREATE TABLE user_files (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    file_path TEXT NOT NULL,
    file_size BIGINT,
    mime_type VARCHAR(100),
    storage_type VARCHAR(20) DEFAULT 'local',  -- local, s3
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Индексы
CREATE INDEX idx_token_usage_user_created ON token_usage(user_id, created_at DESC);
CREATE INDEX idx_credit_transactions_user ON credit_transactions(user_id, created_at DESC);
CREATE INDEX idx_agent_sessions_user ON agent_sessions(user_id, started_at DESC);
CREATE INDEX idx_users_telegram ON users(telegram_id) WHERE telegram_id IS NOT NULL;
```

---

## 3. Технологический стек

### 3.1 Бэкенд

**Ядро: Форк OpenClaw**

OpenClaw уже даёт:
- Agentic loop (plan → tool → observe → respond)
- Tool system (exec, read, write, web_search, browser и др.)
- Memory system (SOUL.md, MEMORY.md, daily logs)
- Multi-channel support (Telegram, WhatsApp, Slack, WebChat)
- Skill system (подключаемые навыки)
- Sub-agent spawning

**Что нужно добавить в форк:**

| Компонент | Описание | Сложность |
|-----------|----------|-----------|
| **Multi-tenant Control Plane** | Управление пулом агентов, lifecycle, пробуждение/засыпание | Высокая |
| **Billing middleware** | Pre-flight проверка кредитов перед каждым LLM-вызовом | Средняя |
| **User API** | REST API для фронтенда: auth, профиль, история, настройки | Средняя |
| **WebSocket gateway** | Real-time доставка сообщений в веб-приложение | Средняя |
| **Workspace provisioning** | Автосоздание workspace из шаблона при регистрации | Низкая |
| **Rate limiter** | Лимиты на запросы per-user (Redis-based) | Низкая |
| **Usage analytics** | Дашборд для пользователя: сколько потратил, на что | Низкая |

**Дополнительные компоненты:**

- **API Gateway:** Fastify (Node.js) — быстрее Express в 2-3x, нативная поддержка JSON schema validation, TypeScript
- **Auth:** Lucia Auth (lightweight, session-based) + OAuth2 (Google, Telegram Login Widget)
- **Queue:** BullMQ (Redis) — задачи: создание агента, отправка email, обработка файлов

### 3.2 Фронтенд (веб-приложение)

**Выбор: Next.js 15 (App Router) + Tailwind CSS + shadcn/ui**

Обоснование:
- **Next.js** — SSR для SEO (лендинг), RSC для снижения bundle size, API routes для BFF
- **Tailwind + shadcn/ui** — быстрая разработка, консистентный дизайн, не перегруженный UI
- **Альтернатива Remix/SvelteKit:** меньше экосистема, сложнее найти разработчиков

**Ключевые экраны:**
1. Лендинг (маркетинг)
2. Регистрация / вход
3. Чат с агентом (основной экран)
4. Настройки агента (имя, модель, prompt)
5. Биллинг (баланс, пополнение, история)
6. Файлы (загруженные документы)

**Real-time:** WebSocket соединение через `socket.io` или нативные WS → сообщения агента стримятся в реальном времени.

### 3.3 Мобильное приложение

**Выбор: React Native (Expo) — единая кодбаза iOS/Android**

Обоснование:
- **React Native + Expo:** общая кодбаза с веб-фронтом (React), горячая перезагрузка, OTA-обновления без App Store review
- **Почему не Flutter:** отдельный язык (Dart), не шарит код с вебом, сложнее найти fullstack-разработчика
- **Почему не PWA:** нет push-notifications на iOS (ограниченно), нет фонового аудио для звонков, нет доступа к микрофону при заблокированном экране

**Функционал мобильного:**
- Чат (текст + голос)
- Push-уведомления (напоминания от агента)
- Загрузка фото/файлов с камеры
- Голосовой звонок (LiveKit SDK для React Native есть)
- Биллинг (in-app purchases для iOS — комиссия 30%, или ссылка на веб для оплаты)

### 3.4 Инфраструктура

**MVP-фаза (до 1К пользователей):**

| Компонент | Где | Стоимость/мес |
|-----------|-----|---------------|
| API + Control Plane + Agent Pool | 1× Hetzner CPX41 (8 vCPU, 16GB RAM) | €28 |
| PostgreSQL + Redis | Тот же сервер | — |
| LiteLLM Proxy | Тот же сервер | — |
| LiveKit Server | 1× Hetzner CPX21 (3 vCPU, 4GB RAM) | €10 |
| Object Storage (MinIO) | Hetzner Storage Box 1TB | €4 |
| Домен + SSL | Let's Encrypt | бесплатно |
| **Итого** | | **~€42/мес (~$45)** |

**Почему Hetzner:**
- В 3-5x дешевле AWS/GCP при том же железе
- Дата-центры в Европе (GDPR-friendly)
- Для MVP не нужна экосистема managed-сервисов

### 3.5 LiveKit интеграция для голоса

**Архитектура голосового звонка:**

```
Пользователь (браузер/моб) 
    ↕ WebRTC (LiveKit SDK)
LiveKit Server
    ↕ LiveKit Agent Framework
Arkadius Voice Agent (Python)
    ├─ STT: Deepgram / Whisper API
    ├─ LLM: через LiteLLM (тот же биллинг)
    └─ TTS: Edge TTS (бесплатно) или ElevenLabs
```

**Компоненты:**

1. **LiveKit Server** — self-hosted, медиа-сервер WebRTC
2. **Voice Agent** — Python-сервис на базе `livekit-agents` SDK:
   - Слушает аудиопоток → STT → текст
   - Текст → OpenClaw agent → ответ
   - Ответ → TTS → аудиопоток обратно
3. **LiveKit SDK** — клиентские библиотеки:
   - `@livekit/components-react` для веба
   - `@livekit/react-native` для мобильного

**Выбор STT/TTS:**

| Компонент | MVP | Scale |
|-----------|-----|-------|
| **STT** | Deepgram Nova-2 ($0.0043/мин) | Deepgram или self-hosted Whisper |
| **TTS** | Edge TTS (бесплатно, ru-RU-DmitryNeural) | ElevenLabs ($0.18/1K chars) для премиума |

**Стоимость голоса на 1 минуту звонка:**
- STT (Deepgram): ~$0.004
- LLM (Claude Sonnet, ~500 tokens): ~$0.005
- TTS (Edge TTS): $0
- LiveKit (self-hosted): $0 (только инфра)
- **Итого: ~$0.01/минута** (≈1 ₽)

---

## 4. Функционал MVP

### 4.1 MVP (v0.1) — 6-8 недель разработки

**Включаем:**

1. ✅ **Регистрация/авторизация** — email + Google OAuth
2. ✅ **Текстовый чат с агентом** — веб-интерфейс, стриминг ответов
3. ✅ **Выбор модели** — Claude Sonnet (дефолт), GPT-4o, Qwen
4. ✅ **Память между сессиями** — агент помнит контекст
5. ✅ **Загрузка файлов** — PDF, DOCX, изображения → агент анализирует
6. ✅ **Prepaid кредиты** — пополнение через ЮKassa (рубли)
7. ✅ **Дашборд расходов** — сколько потратил, на какие модели
8. ✅ **Базовые инструменты** — веб-поиск, чтение/запись файлов, анализ изображений
9. ✅ **Telegram-бот как альтернативный канал** — общение с тем же агентом

**Технические задачи MVP:**
- Форк OpenClaw + multi-tenant обвязка
- LiteLLM настройка + billing callback
- Веб-приложение (Next.js)
- API: auth, chat, billing, files
- Деплой на Hetzner

### 4.2 Что НЕ делаем в MVP

- ❌ Голосовые звонки (LiveKit) — v0.2
- ❌ Мобильное приложение — v0.2
- ❌ Кастомизация personality/SOUL.md через UI — v0.2
- ❌ Интеграции (email, календарь, CRM) — v0.3
- ❌ Групповые агенты / shared workspace — v0.4
- ❌ Marketplace skills — v0.5
- ❌ Self-hosted вариант для B2B — v1.0
- ❌ Видео-звонки — не в scope

### 4.3 Roadmap

| Версия | Срок | Функционал |
|--------|------|-----------|
| **v0.1 (MVP)** | +8 нед | Текстовый чат, биллинг, веб-приложение |
| **v0.2** | +6 нед | Голосовые звонки (LiveKit), мобильное приложение, кастомизация агента |
| **v0.3** | +6 нед | Интеграции (email, календарь), напоминания, push-уведомления |
| **v0.4** | +8 нед | Skill marketplace, shared workspaces, команды |
| **v0.5** | +6 нед | API для разработчиков, webhooks, расширенная аналитика |
| **v1.0** | +12 нед | B2B self-hosted, enterprise features, SLA |

---

## 5. Масштабирование

### 5.1 Архитектура по уровням нагрузки

#### 1K пользователей (MVP)

- **Одновременно активных агентов:** ~50-100 (5-10% DAU)
- **RAM:** ~100 агентов × 50MB = 5GB + 3GB система = **8GB достаточно**
- **CPU:** 8 vCPU хватает (агенты ждут LLM 90% времени)
- **Один сервер** — всё на одной машине

#### 10K пользователей

- **Одновременно активных:** ~500-1000
- **Разделение сервисов:**
  - 2× Agent Worker (16GB RAM каждый) — по 250-500 агентов
  - 1× API + Control Plane
  - 1× PostgreSQL (managed или dedicated)
  - 1× Redis (managed)
  - 1× LiveKit
  - 1× LiteLLM (2 инстанса за LB)
- **Инфра:** 5-6 серверов Hetzner, **~€200/мес**

#### 100K пользователей

- **Одновременно активных:** ~5000-10000
- **Критические изменения:**
  - Kubernetes (k3s на Hetzner или managed K8s)
  - Agent Workers как StatefulSet с автоскейлингом
  - PostgreSQL: read replicas + connection pooling (PgBouncer)
  - Redis Cluster
  - Object Storage: переход на Hetzner Object Storage или S3
  - CDN для статики
  - Мониторинг: Prometheus + Grafana
- **Инфра:** **~€2000-3000/мес**

### 5.2 Узкие места и решения

| Узкое место | Симптом | Решение |
|-------------|---------|---------|
| **Cold start агента** | Задержка 2-5 сек при первом сообщении | Пул предварительно прогретых процессов, warm pool из 10-20 готовых агентов |
| **RAM на агентов** | OOM при 500+ одновременных | Агрессивный sleep (5 мин бездействия → засыпание), swap на NVMe |
| **Диск IO при пробуждении** | Latency при загрузке workspace с object storage | Локальный NVMe кэш, lazy loading файлов |
| **LiteLLM throughput** | Bottleneck при 1000+ concurrent запросов | Горизонтальное масштабирование LiteLLM (stateless, за LB) |
| **PostgreSQL connections** | Too many connections | PgBouncer, connection pooling |
| **WebSocket connections** | 10K+ persistent connections | Sticky sessions на LB, Redis pub/sub для cross-node delivery |
| **LiveKit media** | CPU-intensive при 100+ concurrent calls | Отдельные LiveKit ноды, auto-scaling |

### 5.3 Стоимость инфраструктуры

| Масштаб | Серверы | Инфра/мес | LLM costs/мес (оценка) | Всего |
|---------|---------|-----------|------------------------|-------|
| 1K users | 1-2 | €42 | ~€500 (при 10K req/day) | ~€550 |
| 10K users | 5-6 | €200 | ~€5,000 | ~€5,200 |
| 100K users | 15-20 | €2,500 | ~€50,000 | ~€52,500 |

> **Важно:** 90%+ расходов — это LLM API costs, не инфраструктура. Оптимизация промптов, кэширование, выбор модели — главные рычаги.

---

## 6. Монетизация

### 6.1 Модель: Prepaid кредиты

**Почему prepaid, а не подписка:**
- Нет риска "пользователь на безлимите генерирует убыточный трафик"
- Прозрачность: пользователь видит, сколько стоит каждое действие
- Низкий порог входа: можно начать с 100₽
- Проще юридически (не recurring, не подписка)

### 6.2 Ценообразование

**Внутренняя единица: 1 кредит = 1 рубль**

| Действие | Себестоимость | Цена для пользователя | Маржа |
|----------|--------------|----------------------|-------|
| Claude Sonnet (1K input + 500 output tokens) | ~0.5₽ | 1₽ | 100% |
| GPT-4o (1K input + 500 output tokens) | ~0.3₽ | 0.7₽ | 133% |
| Qwen Plus (1K input + 500 output tokens) | ~0.05₽ | 0.2₽ | 300% |
| Веб-поиск (1 запрос) | ~0.1₽ | 0.3₽ | 200% |
| Анализ изображения | ~0.5₽ | 1₽ | 100% |
| Голосовой звонок (1 минута) | ~1₽ | 3₽ | 200% |
| Загрузка файла (анализ PDF 10 стр) | ~2₽ | 5₽ | 150% |

**Пакеты пополнения:**

| Пакет | Цена | Кредиты | Бонус |
|-------|------|---------|-------|
| Старт | 199₽ | 199 | — |
| Базовый | 499₽ | 550 | +10% |
| Про | 999₽ | 1200 | +20% |
| Бизнес | 2999₽ | 3900 | +30% |

### 6.3 Экономика: как не уйти в минус

**Принцип:** наценка ≥ 100% на каждую операцию.

**Защитные механизмы:**
1. **Pre-flight check:** перед каждым LLM-вызовом проверяем баланс
2. **Средний запрос:** ~2000 input + 800 output tokens ≈ 1.5₽ себестоимость → 3₽ цена
3. **Нулевой баланс = стоп:** агент вежливо сообщает о необходимости пополнения
4. **Лимиты на сессию:** максимум 100K tokens за одну сессию (предотвращает бесконечные tool-loops)
5. **Дорогие операции (Opus, длинные контексты) = явное предупреждение:** "Этот запрос будет стоить ~15₽, продолжить?"

**Средний чек (прогноз):**
- Casual user: 200-500₽/мес
- Активный user: 1000-3000₽/мес
- Power user: 5000-10000₽/мес

**Break-even при 1K users:**
- Средний ARPU: ~800₽/мес
- Revenue: 800K₽/мес
- LLM costs (~50%): 400K₽/мес
- Infra (~5%): 40K₽/мес
- **Маржа: ~360K₽/мес (~45%)**

### 6.4 Платёжные системы

| Регион | Провайдер | Комиссия |
|--------|----------|---------|
| Россия | ЮKassa | 3.5% |
| Россия (альт.) | Тинькофф Payments | 2.49% |
| Международный | Stripe | 2.9% + $0.30 |
| Крипто (опционально) | TON / USDT | ~0% (но волатильность) |

**В MVP:** только ЮKassa (рубли). Stripe — при выходе на международный рынок.

---

## 7. Конкуренты и позиционирование

### 7.1 Конкурентный ландшафт

| Продукт | Тип | Сильные стороны | Слабые стороны |
|---------|-----|-----------------|----------------|
| **ChatGPT (OpenAI)** | Чат-бот + GPTs | Бренд, качество моделей, экосистема | Нет персонализации, нет памяти между сессиями (ограниченная), нет инструментов, нет файловой системы |
| **Claude (Anthropic)** | Чат-бот + Projects | Длинный контекст, качество | Те же ограничения, только через веб/API |
| **Character.ai** | Ролевые персонажи | Огромная база пользователей, бесплатно | Развлечение, а не продуктивность; нет tool use |
| **Replika** | Эмоциональный компаньон | Привязанность пользователей | Нет практической пользы, контент-ограничения |
| **Custom GPTs** | Кастомные чат-боты | Экосистема OpenAI | Нет памяти, нет файлов, нет real tools |
| **Lindy.ai** | AI-ассистент с интеграциями | Много интеграций, workflows | Дорого ($50+/мес), нет персонализации |
| **OpenClaw (open-source)** | Self-hosted ассистент | Максимальная гибкость, все инструменты | Нужен сервер, технические навыки |

### 7.2 Уникальность Аркадиуса

**Позиционирование: "OpenClaw для всех" — мощь self-hosted агента без технических навыков.**

Ключевые дифференциаторы:

1. **Настоящий агент, а не чат-бот** — файловая система, инструменты, sub-agents, automation
2. **Память как у человека** — daily logs, долгосрочная память, контекст сохраняется навсегда
3. **Выбор модели** — не привязан к одному провайдеру (Claude, GPT, Qwen)
4. **Голос** — полноценные голосовые звонки, а не voice-to-text
5. **Pay-as-you-go** — никаких подписок, платишь только за использование
6. **Персонализация** — пользователь настраивает личность, стиль, приоритеты агента
7. **Открытое ядро** — форк open-source проекта, возможность self-host для технических пользователей

### 7.3 Целевая аудитория

**Первичная (MVP):**
- 🎯 **Техно-энтузиасты 25-40 лет** — пробовали ChatGPT, хотят больше
- 🎯 **Фрилансеры и предприниматели** — нужен персональный ассистент, но не могут нанять
- 🎯 **Разработчики** — знают OpenClaw, хотят без возни с сервером

**Вторичная (v0.3+):**
- 📱 **Студенты** — помощь с учёбой, организация, дешёвые модели
- 💼 **Малый бизнес** — CRM-лайт, обработка email, напоминания
- 🌍 **Русскоязычный рынок** — мало альтернатив с оплатой в рублях

**TAM/SAM/SOM:**
- TAM (глобальный рынок AI-ассистентов): ~$20B к 2027
- SAM (русскоязычные пользователи, pay-as-you-go): ~$200M
- SOM (первый год, реалистично): 5K-10K платящих пользователей = ~$500K ARR

---

## 8. Риски

### 8.1 Технические риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **OpenClaw breaking changes** | Высокая | Высокое | Зафиксировать версию форка, cherry-pick только security patches; maintainer стратегия |
| **LLM провайдеры меняют цены вверх** | Средняя | Высокое | Мультимодельность, быстрый switch на дешёвую модель, запас маржи в ценообразовании |
| **Утечка данных между агентами** | Низкая | Критическое | Process-level изоляция, security audit, penetration testing |
| **DDoS на LiteLLM** | Средняя | Среднее | Rate limiting per-user, WAF, fail2ban |
| **Потеря данных пользователя** | Низкая | Критическое | Ежедневные бэкапы в object storage, WAL archiving PostgreSQL |
| **Cold start >3 сек** | Средняя | Среднее | Warm pool, оптимизация загрузки workspace, keep-alive для частых пользователей |

### 8.2 Бизнесовые риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **OpenAI/Anthropic выпускают аналогичный продукт** | Высокая | Высокое | Фокус на персонализации и open-source; они всегда будут закрытые и дороже |
| **Низкая retention** | Высокая | Высокое | Sticky memory (чем больше пользуешься, тем полезнее агент), push-уведомления, onboarding |
| **Высокий CAC** | Средняя | Среднее | Органический рост (Twitter/X, Telegram-каналы), product-led growth |
| **Кассовый разрыв (LLM costs > revenue)** | Средняя | Критическое | Prepaid модель исключает это by design — сначала оплата, потом расход |
| **Не найти разработчиков** | Средняя | Высокое | Open-source community, part-time контрибьюторы |

### 8.3 Регуляторные риски

| Риск | Вероятность | Влияние | Митигация |
|------|-------------|---------|-----------|
| **152-ФЗ (персональные данные РФ)** | Высокая (обязательно) | Высокое | Сервера в РФ (или Hetzner с DPA), privacy policy, согласие на обработку |
| **Роскомнадзор блокирует LLM-провайдеров** | Средняя | Высокое | Мультимодельность, Qwen/DeepSeek как backup, self-hosted модели |
| **EU AI Act (при выходе на Европу)** | Средняя | Среднее | Transparency (показываем что это AI), не high-risk application |
| **Ответственность за контент агента** | Средняя | Высокое | ToS с disclaimers, content moderation layer, логирование |
| **Требования ФСБ по хранению данных** | Низкая | Высокое | Compliance с законом Яровой (хранение 6 мес) если попадаем под регулирование |

### 8.4 Ключевые mitigation-стратегии

1. **Prepaid = нулевой финансовый риск** — пользователь не может потратить больше, чем положил
2. **Multi-model = нулевой vendor lock-in** — если один провайдер упал/подорожал, переключаемся
3. **Open-source core = community moat** — даже если продукт закроется, код остаётся
4. **Process isolation = безопасность by design** — каждый агент в своём sandbox
5. **Hetzner EU = GDPR compliance** — данные в Европе, DPA доступен

---

## Приложение A: Конфигурация агента (шаблон)

При регистрации нового пользователя создаётся workspace:

```
/data/agents/{user_id}/
├── workspace/
│   ├── SOUL.md          # Персонализация (из шаблона + настройки пользователя)
│   ├── USER.md          # Информация о пользователе (из onboarding)
│   ├── MEMORY.md        # Долгосрочная память (пустой)
│   ├── memory/
│   │   └── YYYY-MM-DD.md
│   └── files/           # Загруженные файлы
├── config/
│   └── agent.json       # Настройки: модель, tools, лимиты
└── logs/
    └── sessions/        # Логи сессий (для дебага)
```

## Приложение B: API Endpoints (MVP)

```
AUTH
  POST   /api/auth/register        — регистрация
  POST   /api/auth/login            — вход
  POST   /api/auth/logout           — выход
  POST   /api/auth/google           — OAuth Google
  GET    /api/auth/telegram         — Telegram Login

CHAT
  POST   /api/chat/message          — отправка сообщения агенту
  GET    /api/chat/history          — история (пагинация)
  WS     /api/chat/stream           — WebSocket для стриминга

FILES
  POST   /api/files/upload          — загрузка файла
  GET    /api/files                  — список файлов
  DELETE /api/files/:id              — удаление

BILLING
  GET    /api/billing/balance        — текущий баланс
  POST   /api/billing/topup          — создание платежа (ЮKassa)
  POST   /api/billing/webhook        — webhook от ЮKassa
  GET    /api/billing/usage          — история расходов

AGENT
  GET    /api/agent/config           — текущие настройки
  PATCH  /api/agent/config           — обновление (модель, имя, prompt)
  GET    /api/agent/models           — доступные модели с ценами
```

## Приложение C: Оценка трудозатрат MVP

| Задача | Человеко-недели |
|--------|----------------|
| Форк OpenClaw + multi-tenant | 3 |
| Control Plane + Agent lifecycle | 2 |
| LiteLLM + billing integration | 1.5 |
| API Gateway (auth, chat, billing) | 2 |
| WebSocket streaming | 1 |
| Веб-приложение (Next.js) | 3 |
| Интеграция ЮKassa | 1 |
| DevOps (CI/CD, мониторинг) | 1 |
| Тестирование + баг-фикс | 1.5 |
| **Итого** | **~16 человеко-недель** |

При команде в 2 человека: **~8 календарных недель** (2 месяца).
При 1 разработчике full-time: **~4 месяца**.

---

*Документ подготовлен 19 марта 2026. Обновлять по мере принятия решений.*
