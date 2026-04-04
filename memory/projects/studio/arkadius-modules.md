# Аркадиус — Модули бэкенда (Python FastAPI)

> Составлено на основе: OpenClaw (каналы, агенты, сессии, маршрутизация) + nano-claude-code (agent loop, tool registry, memory, multi-agent, context compression)
>
> Обновлено: 2026-04-04 — добавлены org-уровень, vault, разбивка по репозиториям, межсервисное взаимодействие

---

## Репозитории

| Репо | Назначение |
|------|-----------|
| **ZnaemAI/arkadius** | Продуктовый код: agent loop, tools, memory, channels, API для пользователей, billing логика |
| **ZnaemAI/arkadius-admin** | Инфра и админка: LiteLLM конфиг, ЮKassa интеграция, Docker sandbox управление, мониторинг, дашборд |
| **ZnaemAI/arkadius-node-server** | Rust daemon для серверных нод (клиентский режим) + автоустановка через SSH |

---

## Структура проекта

```
arkadius/                        [репо: arkadius]
├── core/                    — общие утилиты и настройки
├── infra/                   — внешние сервисы (S3, Redis, LiteLLM, Docker)
├── models/                  — SQLAlchemy ORM модели
├── apps/
│   ├── api/                 — FastAPI роуты (v1)
│   ├── agent/               — runtime агентов
│   │   └── src/
│   │       ├── org/         — управление организациями
│   │       └── vault/       — зашифрованное хранилище секретов
│   ├── tools/               — ToolRegistry + встроенные инструменты
│   ├── memory/              — управление памятью
│   ├── channels/            — каналы (Web, Telegram, VK, MAX)
│   ├── groups/              — групповые чаты (двухуровневая модель)
│   ├── billing/             — биллинг и кредиты
│   └── worker/              — Celery задачи
└── tests/

arkadius-admin/                  [репо: arkadius-admin]
├── litellm/                 — конфигурация LiteLLM прокси
├── sandbox/                 — Docker sandbox управление
├── billing_provider/        — ЮKassa интеграция
├── monitoring/              — метрики, алерты, дашборды
└── admin_api/               — внутренний API для inter-service вызовов
```

---

## 1. CORE — Ядро и конфигурация

---

### config.py

- **Репо:** arkadius
- **Путь:** `core/config.py`
- **Ответственность:** Единая точка конфигурации приложения через Pydantic Settings. Читает переменные окружения, формирует DSN для БД, S3, Redis, LiteLLM прокси. Разделяет конфиги по окружениям (dev/staging/prod).
- **Классы:**
  - `Settings(BaseSettings)` — все env vars
  - `DatabaseSettings`, `S3Settings`, `LiteLLMSettings`, `RedisSettings`
  - `get_settings() -> Settings` — cached singleton (lru_cache)
- **Зависимости:** нет
- **Источник:** OpenClaw (модель конфига с провайдерами/каналами) + nano-claude-code (паттерн env-конфигурации)

---

### database.py

- **Репо:** arkadius
- **Путь:** `core/database.py`
- **Ответственность:** Настройка asyncpg + SQLAlchemy async engine. Фабрика сессий, базовый класс моделей, декоратор транзакций. Поддерживает pgvector для семантического поиска памяти.
- **Классы:**
  - `engine` — AsyncEngine (asyncpg)
  - `AsyncSessionFactory` — sessionmaker
  - `Base` — декларативная база
  - `get_db()` — FastAPI dependency
  - `transactional(func)` — декоратор для атомарных операций
- **Зависимости:** `core/config.py`
- **Источник:** OpenClaw (паттерн хранения агентов в БД, не в файлах)

---

### exceptions.py

- **Репо:** arkadius
- **Путь:** `core/exceptions.py`
- **Ответственность:** Иерархия доменных исключений Аркадиуса. Все бизнес-ошибки наследуются отсюда. Маппинг на HTTP статусы через ExceptionHandlers.
- **Классы:**
  - `ArkException(Exception)` — базовое
  - `AgentNotFoundError`, `InsufficientCreditsError`, `SandboxError`
  - `ToolExecutionError`, `LLMError`, `ChannelError`
  - `OrgNotFoundError`, `VaultDecryptionError` — новые
  - `register_exception_handlers(app: FastAPI)`
- **Зависимости:** нет
- **Источник:** новый

---

### security.py

- **Репо:** arkadius
- **Путь:** `core/security.py`
- **Ответственность:** JWT генерация/валидация, хеширование паролей, tenant-изоляция на уровне токенов. Каждый JWT несёт `user_id`, `org_id` (optional) и `tenant_id` для multi-tenant проверок.
- **Классы:**
  - `create_access_token(user_id, tenant_id, org_id=None) -> str`
  - `verify_token(token) -> TokenPayload`
  - `hash_password(plain) -> str`
  - `verify_password(plain, hashed) -> bool`
  - `get_current_user(token) -> User` — FastAPI dependency
- **Зависимости:** `core/config.py`, `models/user.py`
- **Источник:** новый

---

### dependencies.py

- **Репо:** arkadius
- **Путь:** `core/dependencies.py`
- **Ответственность:** Центральный реестр FastAPI dependencies. Инъекция DB-сессии, текущего пользователя, агента, организации, биллинг-аккаунта. Обеспечивает tenant-изоляцию на уровне DI.
- **Классы:**
  - `get_db()` — async DB session
  - `get_current_user()` — текущий User из JWT
  - `get_user_agent()` — Agent текущего пользователя
  - `get_current_org()` — Organization из JWT (опционально)
  - `get_billing_account()` — CreditAccount пользователя
  - `require_credits(min_credits: int)` — guard на минимальный баланс
- **Зависимости:** `core/security.py`, `core/database.py`, `models/`
- **Источник:** новый

---

## 2. INFRA — Инфраструктурные адаптеры

---

### s3/client.py

- **Репо:** arkadius
- **Путь:** `infra/s3/client.py`
- **Ответственность:** Низкоуровневый async S3 клиент для FirstVDS (S3-compatible). Поддерживает presigned URLs, multipart upload, versioning. Абстрагирует boto3/aiobotocore от бизнес-логики.
- **Классы:**
  - `S3Client` — singleton wrapper
  - `upload_bytes(bucket, key, data) -> str`
  - `download_bytes(bucket, key) -> bytes`
  - `generate_presigned_url(bucket, key, expires) -> str`
  - `delete_object(bucket, key)`
  - `list_objects(bucket, prefix) -> List[str]`
- **Зависимости:** `core/config.py`
- **Источник:** OpenClaw (S3 как persistent storage для агентов)

---

### s3/storage.py

- **Репо:** arkadius
- **Путь:** `infra/s3/storage.py`
- **Ответственность:** Высокоуровневое API для работы с S3 в контексте агентов. Управляет структурой бакетов: `agents/{agent_id}/snapshots/`, `agents/{agent_id}/files/`, `orgs/{org_id}/`, `users/{user_id}/uploads/`. Сериализует/десериализует объекты.
- **Классы:**
  - `AgentStorageService`
  - `save_agent_snapshot(agent_id, state: dict) -> str`
  - `load_agent_snapshot(agent_id) -> dict`
  - `save_file(agent_id, filename, data) -> str`
  - `list_agent_files(agent_id) -> List[FileInfo]`
- **Зависимости:** `infra/s3/client.py`
- **Источник:** OpenClaw

---

### cache/redis.py

- **Репо:** arkadius
- **Путь:** `infra/cache/redis.py`
- **Ответственность:** Redis клиент (aioredis) для кэширования сессий, rate limiting, pub/sub между воркерами и API. Хранит ephemeral state агентов между запросами. Также используется для межсервисного pub/sub.
- **Классы:**
  - `RedisClient` — singleton
  - `get_session_cache(session_id) -> dict | None`
  - `set_session_cache(session_id, data, ttl)`
  - `publish(channel, message)`
  - `subscribe(channel) -> AsyncGenerator`
  - `rate_limit(key, limit, window) -> bool`
- **Зависимости:** `core/config.py`
- **Источник:** OpenClaw

---

### llm/provider.py

- **Репо:** arkadius
- **Путь:** `infra/llm/provider.py`
- **Ответственность:** Клиент к LiteLLM прокси (расположен в arkadius-admin). Единственная точка взаимодействия с LLM. Поддерживает streaming, считает токены для биллинга, обрабатывает rate limits и retry.
- **Классы:**
  - `LiteLLMProvider`
  - `complete(messages, tools, model, stream) -> AsyncGenerator[LLMChunk]`
  - `count_tokens(messages) -> int`
  - `LLMChunk` — streaming chunk (text | tool_call | usage)
  - `UsageStats(input_tokens, output_tokens, cost_usd)`
- **Зависимости:** `core/config.py`, `core/exceptions.py`
- **Источник:** nano-claude-code (streaming API + automatic tool-use loop)

---

### llm/context_manager.py

- **Репо:** arkadius
- **Путь:** `infra/llm/context_manager.py`
- **Ответственность:** Управление контекстным окном Claude: подсчёт токенов, авто-компрессия длинных диалогов до лимита модели, сохранение "сжатого" контекста в БД. Аналог Context Compression из nano-claude-code.
- **Классы:**
  - `ContextManager`
  - `fit_messages(messages, max_tokens) -> List[Message]`
  - `compress_conversation(messages, keep_last_n) -> Summary`
  - `build_context(session_id, system_prompt) -> List[dict]`
  - `estimate_tokens(messages) -> int`
- **Зависимости:** `infra/llm/provider.py`, `models/session.py`
- **Источник:** nano-claude-code (Context Compression / auto-compact)

---

### sandbox/docker_manager.py

- **Репо:** arkadius-admin
- **Путь:** `sandbox/docker_manager.py`
- **Ответственность:** Lifecycle management Docker-контейнеров на пользователя. Создаёт, запускает, приостанавливает, удаляет изолированные sandbox-контейнеры. Маппит S3-volume через FUSE или bind mount. Ограничивает CPU/RAM/network. Предоставляет REST API для обращений из arkadius.
- **Классы:**
  - `DockerSandboxManager`
  - `create_sandbox(user_id, image) -> SandboxInfo`
  - `get_or_create(user_id) -> SandboxInfo`
  - `destroy_sandbox(user_id)`
  - `pause_idle_sandboxes(idle_minutes)` — Celery периодика
  - `SandboxInfo(container_id, status, user_id)`
- **Зависимости:** `core/config.py`, `infra/s3/storage.py`
- **Источник:** OpenClaw (изоляция на пользователя, multi-tenant)

---

### sandbox/exec_runner.py

- **Репо:** arkadius-admin
- **Путь:** `sandbox/exec_runner.py`
- **Ответственность:** Выполнение кода/команд внутри Docker sandbox пользователя через Docker exec API. Стриминг stdout/stderr, таймаут, перехват ошибок. Используется инструментом code_exec через внутренний API arkadius-admin.
- **Классы:**
  - `SandboxExecRunner`
  - `run_command(user_id, cmd, timeout) -> ExecResult`
  - `run_code(user_id, language, code) -> ExecResult`
  - `ExecResult(stdout, stderr, exit_code, timed_out)`
- **Зависимости:** `sandbox/docker_manager.py`
- **Источник:** OpenClaw

---

## 3. MODELS — ORM модели (SQLAlchemy)

---

### user.py

- **Репо:** arkadius
- **Путь:** `models/user.py`
- **Ответственность:** Пользователь системы (tenant). Хранит учётные данные, привязки к каналам, метаданные.
- **Классы:**
  - `User(Base)` — id, email, hashed_password, created_at, is_active
  - `AuthToken(Base)` — refresh tokens, device info
  - `UserProfile(Base)` — display_name, timezone, language
- **Зависимости:** `core/database.py`
- **Источник:** новый

---

### agent.py

- **Репо:** arkadius
- **Путь:** `models/agent.py`
- **Ответственность:** Конфигурация и состояние персонального AI-агента. Агент может принадлежать пользователю (user_id) или организации (org_id). Хранит системный промпт, модель, параметры, включённые инструменты.
- **Классы:**
  - `Agent(Base)` — id, user_id (nullable для орг-агента), org_id (nullable), name, system_prompt, model, config_json
  - `AgentState(Base)` — current_mood, last_active, context_summary, s3_snapshot_key
  - `AgentConfig` — pydantic schema для config_json
  - `SubagentDefinition(Base)` — Researcher/Coder/Учёный конфиги
- **Зависимости:** `core/database.py`, `models/user.py`, `models/organization.py`
- **Источник:** OpenClaw (агенты в БД), обновлён: добавлены org_id и nullable user_id

---

### session.py

- **Репо:** arkadius
- **Путь:** `models/session.py`
- **Ответственность:** Сессия разговора (аналог thread в OpenAI). Хранит историю сообщений, метаданные, привязку к каналу. Поддерживает групповые, личные и орг-сессии.
- **Классы:**
  - `ConversationSession(Base)` — id, agent_id, channel_type, channel_id, is_group, created_at
  - `Message(Base)` — id, session_id, role, content_json, tool_calls_json, tokens_used, created_at
  - `SessionState(Base)` — compressed_context, last_message_at, status
- **Зависимости:** `core/database.py`, `models/agent.py`
- **Источник:** nano-claude-code

---

### memory.py

- **Репо:** arkadius
- **Путь:** `models/memory.py`
- **Ответственность:** Постоянная память агента. Трёхуровневая: personal (между сессиями пользователя), org (общая для организации), project (привязана к контексту). Поддерживает pgvector для семантического поиска.
- **Классы:**
  - `MemoryEntry(Base)` — id, agent_id, org_id (nullable), scope (personal|org|project), type (fact|preference|event|skill), content, embedding (Vector), staleness_score, created_at
  - `MemoryTag(Base)` — теги для быстрой фильтрации
- **Зависимости:** `core/database.py`, `models/agent.py`, `models/organization.py`
- **Источник:** nano-claude-code (dual-scope memory, 4 types, staleness); обновлён: добавлен scope=org

---

### tool.py

- **Репо:** arkadius
- **Путь:** `models/tool.py`
- **Ответственность:** Реестр инструментов и лог их выполнения. Хранит определения кастомных инструментов пользователя, историю вызовов для отладки и аудита.
- **Классы:**
  - `ToolDefinition(Base)` — id, name, description, schema_json, is_builtin, owner_id
  - `ToolExecution(Base)` — id, session_id, tool_name, input_json, output_json, duration_ms, error, created_at
- **Зависимости:** `core/database.py`
- **Источник:** новый

---

### subagent.py

- **Репо:** arkadius
- **Путь:** `models/subagent.py`
- **Ответственность:** Задачи и результаты субагентов (Researcher, Coder, Учёный). Позволяет главному агенту делегировать и асинхронно получать результаты.
- **Классы:**
  - `SubagentTask(Base)` — id, parent_session_id, agent_type, prompt, status (pending|running|done|failed), created_at
  - `SubagentResult(Base)` — task_id, result_json, tokens_used, duration_ms
- **Зависимости:** `core/database.py`, `models/session.py`
- **Источник:** nano-claude-code (typed sub-agents, background mode)

---

### billing.py

- **Репо:** arkadius
- **Путь:** `models/billing.py`
- **Ответственность:** Биллинговые модели: аккаунт кредитов, транзакции пополнения/списания, инвойсы ЮKassa.
- **Классы:**
  - `CreditAccount(Base)` — user_id, balance (Decimal), currency
  - `CreditTransaction(Base)` — id, account_id, amount, type (topup|debit|refund), description, ref_id
  - `YoKassaInvoice(Base)` — id, user_id, amount, status, yokassa_payment_id, created_at
- **Зависимости:** `core/database.py`, `models/user.py`
- **Источник:** новый

---

### channel.py

- **Репо:** arkadius
- **Путь:** `models/channel.py`
- **Ответственность:** Привязки пользователей и организаций к мессенджерам. Хранит channel_type, channel_specific_id, статус верификации. Орг-агент может быть привязан к каналу организации.
- **Классы:**
  - `ChannelBinding(Base)` — id, user_id (nullable), org_id (nullable), channel_type (telegram|vk|max|web), external_id, metadata_json, verified_at
  - `GroupParticipantRegistry(Base)` — двухуровневая модель групп
  - `GroupParticipantProfile(Base)` — профиль активного участника группы
- **Зависимости:** `core/database.py`, `models/user.py`, `models/organization.py`
- **Источник:** OpenClaw (multi-channel, group routing); обновлён: добавлен org_id

---

### organization.py *(новый)*

- **Репо:** arkadius
- **Путь:** `models/organization.py`
- **Ответственность:** Организации и их участники. Organization — юридическое лицо или команда, использующая Аркадиуса. OrgMember описывает роль конкретного пользователя в организации.
- **Классы:**
  - `Organization(Base)` — id, name, slug, owner_id, plan, config_json, created_at
  - `OrgMember(Base)` — id, org_id, user_id, role (admin|member|guest), joined_at, is_active
- **Зависимости:** `core/database.py`, `models/user.py`
- **Источник:** новый (org-уровень)

---

### agent_secret.py *(новый)*

- **Репо:** arkadius
- **Путь:** `models/agent_secret.py`
- **Ответственность:** Зашифрованное хранилище секретов агента. Каждая запись — один секрет с типом и зашифрованным значением. Ключ шифрования хранится в env, не в БД.
- **Классы:**
  - `AgentSecret(Base)` — id, agent_id, key_name, encrypted_value (bytes), secret_type (api_key|ssh_key|credential|oauth), created_at, updated_at
- **Зависимости:** `core/database.py`, `models/agent.py`
- **Источник:** новый (vault)

---

## 4. APPS/AGENT — Runtime агентов

---

### agent_loop.py

- **Репо:** arkadius
- **Путь:** `apps/agent/agent_loop.py`
- **Ответственность:** Главный reasoning loop агента. Принимает сообщение → строит контекст → вызывает LLM → обрабатывает tool calls → итерирует до финального ответа. Стримит ответ обратно в канал. Центральный модуль всей системы.
- **Классы:**
  - `AgentLoop`
  - `async run(session_id, user_message) -> AsyncGenerator[AgentEvent]`
  - `_process_tool_call(tool_name, tool_input) -> ToolResult`
  - `_should_continue(response) -> bool`
  - `AgentEvent` — union type: TextDelta | ToolCall | ToolResult | Done | Error
- **Зависимости:** `infra/llm/provider.py`, `infra/llm/context_manager.py`, `apps/tools/registry.py`, `apps/memory/memory_manager.py`, `apps/agent/context_builder.py`, `models/session.py`
- **Источник:** nano-claude-code (Streaming API + automatic tool-use loop), OpenClaw (agent runtime)

---

### agent_manager.py

- **Репо:** arkadius
- **Путь:** `apps/agent/agent_manager.py`
- **Ответственность:** CRUD операции над агентами в PostgreSQL. Создание агента при регистрации пользователя или организации, обновление конфига, получение состояния, деактивация.
- **Классы:**
  - `AgentManager`
  - `create_agent(user_id, config: AgentConfig) -> Agent`
  - `create_org_agent(org_id, config: AgentConfig) -> Agent`
  - `get_agent(user_id) -> Agent`
  - `get_org_agent(org_id) -> Agent`
  - `update_agent_config(agent_id, config: AgentConfig)`
  - `update_agent_state(agent_id, state: AgentState)`
- **Зависимости:** `core/database.py`, `models/agent.py`, `infra/s3/storage.py`, `models/organization.py`
- **Источник:** OpenClaw; обновлён: поддержка орг-агентов

---

### context_builder.py

- **Репо:** arkadius
- **Путь:** `apps/agent/context_builder.py`
- **Ответственность:** Собирает полный LLM-контекст для запроса: системный промпт + релевантные воспоминания (personal + org) + история сессии + injected context. Аналог Context Injection из nano-claude-code.
- **Классы:**
  - `ContextBuilder`
  - `build(session_id, new_message: str) -> BuiltContext`
  - `_inject_system_context(agent: Agent) -> str`
  - `_fetch_relevant_memories(agent_id, query, org_id=None) -> List[MemoryEntry]`
  - `BuiltContext(system_prompt, messages, tools_schema)`
- **Зависимости:** `apps/memory/memory_manager.py`, `apps/tools/registry.py`, `infra/llm/context_manager.py`, `models/agent.py`, `models/session.py`
- **Источник:** nano-claude-code (Context injection), OpenClaw (agent-specific system prompt)

---

### dream.py

- **Репо:** arkadius
- **Путь:** `apps/agent/dream.py`
- **Ответственность:** autoDream — фоновая рефлексия агента. Celery task, запускаемый по расписанию или триггеру. Анализирует прошедшие сессии, обновляет долгосрочную память, планирует proactive действия.
- **Классы:**
  - `@celery_app.task auto_dream(agent_id: str)`
  - `DreamService`
  - `reflect_on_sessions(agent_id, last_n_sessions) -> DreamInsights`
  - `extract_memories(sessions) -> List[MemoryEntry]`
  - `update_agent_summary(agent_id, insights)`
  - `DreamInsights(new_memories, updated_facts, planning_notes)`
- **Зависимости:** `apps/worker/celery_app.py`, `apps/memory/memory_manager.py`, `infra/llm/provider.py`, `models/session.py`, `models/agent.py`
- **Источник:** OpenClaw (autoDream как Celery task)

---

### kairos.py

- **Репо:** arkadius
- **Путь:** `apps/agent/kairos.py`
- **Ответственность:** KAIROS — фоновый tick-loop агента. Периодически проверяет: пора ли написать пользователю, нужен ли autoDream, истёк ли sandbox контейнер. Реализован как Celery beat задача.
- **Классы:**
  - `@celery_app.task kairos_tick()` — запускается каждые N минут
  - `KairosService`
  - `check_pending_reminders() -> List[AgentAction]`
  - `check_dream_schedule(agent_id) -> bool`
  - `dispatch_proactive_messages(actions: List[AgentAction])`
  - `AgentAction` — union: SendMessage | TriggerDream | CleanupSandbox
- **Зависимости:** `apps/worker/celery_app.py`, `apps/channels/router.py`, `apps/agent/dream.py`, `models/agent.py`
- **Источник:** OpenClaw (KAIROS background tick loop)

---

### subagent_router.py

- **Репо:** arkadius
- **Путь:** `apps/agent/subagent_router.py`
- **Ответственность:** Маршрутизирует задачи главного агента к специализированным субагентам. Определяет тип субагента, создаёт SubagentTask, запускает через Celery, возвращает handle для получения результата.
- **Классы:**
  - `SubagentRouter`
  - `spawn(parent_session_id, task_type, prompt) -> SubagentTask`
  - `get_result(task_id) -> SubagentResult | None`
  - `wait_for_result(task_id, timeout) -> SubagentResult`
  - `SubagentType(Enum)` — RESEARCHER, CODER, SCIENTIST
- **Зависимости:** `apps/worker/celery_app.py`, `models/subagent.py`, `infra/llm/provider.py`
- **Источник:** nano-claude-code (multi-agent spawn, typed agents, background mode)

---

### subagent_pool.py

- **Репо:** arkadius
- **Путь:** `apps/agent/subagent_pool.py`
- **Ответственность:** Управляет жизненным циклом субагентов: пул активных задач, отслеживание статусов, отмена зависших задач, лимиты параллельности на пользователя.
- **Классы:**
  - `SubagentPool`
  - `get_active_tasks(user_id) -> List[SubagentTask]`
  - `cancel_task(task_id)`
  - `cleanup_stale_tasks(max_age_minutes)`
  - `can_spawn(user_id) -> bool`
- **Зависимости:** `infra/cache/redis.py`, `models/subagent.py`
- **Источник:** nano-claude-code

---

### persona.py

- **Репо:** arkadius
- **Путь:** `apps/agent/persona.py`
- **Ответственность:** Генерация и кэширование системного промпта агента. Собирает: базовый характер + специфика пользователя/организации + текущий контекст + инструкции по инструментам.
- **Классы:**
  - `PersonaBuilder`
  - `build_system_prompt(agent: Agent, context: dict) -> str`
  - `get_tool_instructions(tools: List[str]) -> str`
  - `personalize(agent_id, base_prompt) -> str`
- **Зависимости:** `models/agent.py`, `apps/memory/memory_manager.py`
- **Источник:** новый

---

### src/org/manager.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/agent/src/org/manager.py`
- **Ответственность:** Управление организациями: создание, управление участниками, назначение и изменение ролей. Единая точка входа для всех операций с org-сущностями.
- **Классы:**
  - `OrgManager`
  - `create_org(owner_id, name, slug) -> Organization`
  - `get_org(org_id) -> Organization`
  - `add_member(org_id, user_id, role: OrgRole) -> OrgMember`
  - `remove_member(org_id, user_id)`
  - `change_role(org_id, user_id, new_role: OrgRole)`
  - `get_members(org_id) -> List[OrgMember]`
  - `is_member(org_id, user_id, min_role: OrgRole = OrgRole.GUEST) -> bool`
  - `OrgRole(Enum)` — ADMIN, MEMBER, GUEST
- **Зависимости:** `core/database.py`, `models/organization.py`, `models/agent.py`, `apps/agent/agent_manager.py`
- **Источник:** новый (org-уровень)

---

### src/org/memory.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/agent/src/org/memory.py`
- **Ответственность:** Управление общей орг-памятью. Орг-память доступна всем агентам в рамках организации. Разграничивает scope='org' от scope='personal'. Контролирует права чтения/записи по роли.
- **Классы:**
  - `OrgMemoryService`
  - `save_org_memory(org_id, agent_id, content, type, tags) -> MemoryEntry`
  - `search_org_memory(org_id, query, limit) -> List[MemoryEntry]`
  - `list_org_memory(org_id, type=None, limit=50) -> List[MemoryEntry]`
  - `delete_org_memory(org_id, entry_id, requestor_role: OrgRole)`
  - `merge_personal_and_org(agent_id, org_id, query) -> List[MemoryEntry]`
- **Зависимости:** `core/database.py`, `models/memory.py`, `models/organization.py`, `apps/memory/memory_search.py`
- **Источник:** новый (org-уровень)

---

### src/vault/manager.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/agent/src/vault/manager.py`
- **Ответственность:** VaultManager — интерфейс для работы с зашифрованными секретами агента. CRUD операции над секретами. Расшифровка происходит только при явном get_secret() вызове.
- **Классы:**
  - `VaultManager`
  - `set_secret(agent_id, key_name, value, secret_type: SecretType) -> None`
  - `get_secret(agent_id, key_name) -> str` — расшифровывает при возврате
  - `delete_secret(agent_id, key_name) -> None`
  - `list_keys(agent_id) -> List[SecretKeyInfo]`
  - `SecretType(Enum)` — API_KEY, SSH_KEY, CREDENTIAL, OAUTH
  - `SecretKeyInfo(key_name, secret_type, updated_at)` — без value
- **Зависимости:** `core/database.py`, `models/agent_secret.py`, `apps/agent/src/vault/encryption.py`
- **Источник:** новый (vault)

---

### src/vault/encryption.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/agent/src/vault/encryption.py`
- **Ответственность:** AES-256-GCM шифрование секретов. Каждый агент имеет уникальный encryption key, который деривируется из мастер-ключа сервера (env) + agent_id через HKDF. Ключ никогда не хранится в БД.
- **Классы:**
  - `VaultEncryption`
  - `encrypt(agent_id, plaintext: str) -> bytes`
  - `decrypt(agent_id, ciphertext: bytes) -> str`
  - `_derive_key(agent_id: str) -> bytes` — HKDF(master_key, agent_id)
  - `generate_nonce() -> bytes` — random 12 bytes для GCM
- **Зависимости:** `core/config.py` (VAULT_MASTER_KEY из env)
- **Источник:** новый (vault)

---

## 5. APPS/TOOLS — Инструменты

---

### tools/registry.py

- **Репо:** arkadius
- **Путь:** `apps/tools/registry.py`
- **Ответственность:** ToolRegistry с авторегистрацией через декоратор `@register_tool`. Хранит все доступные инструменты, генерирует JSON-схемы для LLM, применяет фильтрацию по permissions пользователя.
- **Классы:**
  - `ToolRegistry` — singleton
  - `@register_tool(name, description, schema)` — декоратор
  - `get_tools_for_agent(agent_id) -> List[ToolSchema]`
  - `execute_tool(name, input, context) -> ToolResult`
  - `get_tool_schema(name) -> dict`
- **Зависимости:** `apps/tools/base.py`, `apps/tools/permission.py`, `models/tool.py`
- **Источник:** nano-claude-code (tool_registry, auto-registration), OpenClaw (ToolRegistry паттерн)

---

### tools/base.py

- **Репо:** arkadius
- **Путь:** `apps/tools/base.py`
- **Ответственность:** Базовые типы и абстрактный класс инструмента. Все инструменты реализуют `BaseTool`. Стандартизирует контракт input/output.
- **Классы:**
  - `BaseTool(ABC)`
  - `async execute(input: dict, context: ToolContext) -> ToolResult`
  - `ToolResult(success, output, error, metadata)`
  - `ToolContext(user_id, agent_id, session_id, org_id, sandbox_info)`
  - `ToolSchema(name, description, input_schema)`
- **Зависимости:** нет
- **Источник:** nano-claude-code

---

### tools/builtin/web_search.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/web_search.py`
- **Ответственность:** Поиск в интернете через внешний поисковый API. Возвращает структурированные результаты. Ограничение: N запросов в день на пользователя.
- **Классы:**
  - `WebSearchTool(BaseTool)` — execute(query, num_results) -> ToolResult
- **Зависимости:** `apps/tools/base.py`, `infra/cache/redis.py`
- **Источник:** nano-claude-code (WebSearch built-in tool)

---

### tools/builtin/web_fetch.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/web_fetch.py`
- **Ответственность:** Загрузка и извлечение читаемого контента URL. Конвертирует HTML в Markdown. Поддерживает PDF через внешний парсер.
- **Классы:**
  - `WebFetchTool(BaseTool)` — execute(url, extract_mode) -> ToolResult
- **Зависимости:** `apps/tools/base.py`
- **Источник:** nano-claude-code (WebFetch built-in tool)

---

### tools/builtin/code_exec.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/code_exec.py`
- **Ответственность:** Выполнение кода в Docker sandbox пользователя. Отправляет запрос в arkadius-admin API, получает результат выполнения. Поддерживает Python, Bash.
- **Классы:**
  - `CodeExecTool(BaseTool)` — execute(language, code, timeout) -> ToolResult
- **Зависимости:** `apps/tools/base.py`, `core/config.py` (ADMIN_API_URL)
- **Источник:** nano-claude-code (Bash tool + sandbox isolation), OpenClaw (Docker sandbox)

---

### tools/builtin/memory_tools.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/memory_tools.py`
- **Ответственность:** Инструменты для управления памятью агента: сохранение новых фактов, поиск по памяти, удаление устаревших записей. Агент вызывает их явно.
- **Классы:**
  - `MemorySaveTool(BaseTool)` — scope=personal|org
  - `MemorySearchTool(BaseTool)` — семантический поиск
  - `MemoryDeleteTool(BaseTool)`
  - `MemoryListTool(BaseTool)`
- **Зависимости:** `apps/tools/base.py`, `apps/memory/memory_manager.py`
- **Источник:** nano-claude-code (MemorySave/Delete/Search/List tools)

---

### tools/builtin/file_tools.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/file_tools.py`
- **Ответственность:** Работа с файлами в S3-хранилище агента. Read/Write/Edit/Glob/Grep.
- **Классы:**
  - `FileReadTool(BaseTool)`, `FileWriteTool(BaseTool)`, `FileEditTool(BaseTool)`, `FileGlobTool(BaseTool)`, `FileGrepTool(BaseTool)`
- **Зависимости:** `apps/tools/base.py`, `infra/s3/storage.py`
- **Источник:** nano-claude-code (Read/Write/Edit/Glob/Grep tools)

---

### tools/builtin/ask_user.py

- **Репо:** arkadius
- **Путь:** `apps/tools/builtin/ask_user.py`
- **Ответственность:** Инструмент паузы агента для уточняющего вопроса к пользователю mid-task. Публикует вопрос в канал, ждёт ответа через Redis pub/sub, продолжает выполнение.
- **Классы:**
  - `AskUserTool(BaseTool)` — execute(question, choices: List[str] | None)
- **Зависимости:** `apps/tools/base.py`, `infra/cache/redis.py`, `apps/channels/router.py`
- **Источник:** nano-claude-code (AskUserQuestion tool)

---

### tools/permission.py

- **Репо:** arkadius
- **Путь:** `apps/tools/permission.py`
- **Ответственность:** Система разрешений на выполнение инструментов. Уровни: auto, manual, deny. Конфигурируется на уровне агента.
- **Классы:**
  - `ToolPermissionService`
  - `check_permission(agent_id, tool_name, input) -> PermissionResult`
  - `request_user_approval(session_id, tool_name, input) -> bool`
  - `PermissionLevel(Enum)` — AUTO, MANUAL, DENY
  - `PermissionResult(allowed, requires_approval, reason)`
- **Зависимости:** `infra/cache/redis.py`, `models/agent.py`
- **Источник:** nano-claude-code (Permission system)

---

## 6. APPS/MEMORY — Управление памятью

---

### memory_manager.py

- **Репо:** arkadius
- **Путь:** `apps/memory/memory_manager.py`
- **Ответственность:** Основной сервис для работы с памятью агента. Двухуровневая логика: personal (только для конкретного пользователя) и org (общая для организации). CRUD записей, скоринг свежести, eviction.
- **Классы:**
  - `MemoryManager`
  - `save(agent_id, content, scope: Literal['personal','org','project'], type, tags, org_id=None) -> MemoryEntry`
  - `get(agent_id, entry_id) -> MemoryEntry`
  - `delete(agent_id, entry_id)`
  - `list(agent_id, scope, type, limit, org_id=None) -> List[MemoryEntry]`
  - `update_staleness_scores(agent_id)`
  - `evict_stale(agent_id, keep_top_n)`
- **Зависимости:** `core/database.py`, `models/memory.py`, `apps/agent/src/org/memory.py`
- **Источник:** nano-claude-code (Persistent memory, dual-scope); обновлён: двухуровневая память personal+org

---

### memory_search.py

- **Репо:** arkadius
- **Путь:** `apps/memory/memory_search.py`
- **Ответственность:** Семантический поиск по памяти. Использует pgvector для cosine similarity. Fallback на text search. Поддерживает поиск по обоим scope (personal + org одновременно).
- **Классы:**
  - `MemorySearchService`
  - `search(agent_id, query, limit, scope=None, org_id=None) -> List[MemoryEntry]`
  - `embed(text) -> List[float]`
  - `text_search(agent_id, query) -> List[MemoryEntry]`
- **Зависимости:** `core/database.py`, `models/memory.py`, `infra/llm/provider.py`
- **Источник:** nano-claude-code (AI memory search)

---

### compressor.py

- **Репо:** arkadius
- **Путь:** `apps/memory/compressor.py`
- **Ответственность:** Сжатие истории разговора до summary для экономии контекста. Генерирует связный summary через LLM, сохраняет в SessionState.
- **Классы:**
  - `ConversationCompressor`
  - `compress(session_id, messages, keep_last_n) -> CompressedContext`
  - `summarize(messages) -> str`
  - `CompressedContext(summary, kept_messages, tokens_saved)`
- **Зависимости:** `infra/llm/provider.py`, `models/session.py`
- **Источник:** nano-claude-code (Context compression, auto-compact)

---

### s3_snapshot.py

- **Репо:** arkadius
- **Путь:** `apps/memory/s3_snapshot.py`
- **Ответственность:** Снапшоты полного состояния агента в S3. Периодически сохраняет: память, активные сессии, конфиг.
- **Классы:**
  - `AgentSnapshotService`
  - `create_snapshot(agent_id) -> SnapshotRef`
  - `restore_snapshot(agent_id, snapshot_ref)`
  - `list_snapshots(agent_id) -> List[SnapshotRef]`
  - `SnapshotRef(s3_key, created_at, agent_version)`
- **Зависимости:** `infra/s3/storage.py`, `apps/memory/memory_manager.py`, `models/agent.py`
- **Источник:** OpenClaw

---

## 7. APPS/CHANNELS — Каналы

---

### channels/base.py

- **Репо:** arkadius
- **Путь:** `apps/channels/base.py`
- **Ответственность:** Абстрактный базовый класс канала. Определяет контракт приёма/отправки сообщений, нормализации входящих событий. Поддерживает привязку к личному пользователю или организации.
- **Классы:**
  - `BaseChannel(ABC)`
  - `async send_message(channel_id, text, media) -> bool`
  - `async send_stream(channel_id, stream: AsyncGenerator)`
  - `normalize(raw_event) -> ChannelMessage`
  - `ChannelMessage(user_id, org_id, channel_type, text, media, raw)`
  - `ChannelType(Enum)` — WEB, TELEGRAM, VK, MAX
- **Зависимости:** нет
- **Источник:** OpenClaw (multi-channel inbox)

---

### channels/web/handler.py

- **Репо:** arkadius
- **Путь:** `apps/channels/web/handler.py`
- **Ответственность:** Канал Web: HTTP REST + WebSocket. Принимает сообщения через REST POST, стримит ответы через WebSocket/SSE. Аутентификация через JWT.
- **Классы:**
  - `WebChannel(BaseChannel)`
  - `POST /api/v1/chat`, `GET /api/v1/chat/stream`, `WebSocketHandler`
- **Зависимости:** `apps/channels/base.py`, `apps/channels/router.py`
- **Источник:** OpenClaw

---

### channels/telegram/handler.py

- **Репо:** arkадius
- **Путь:** `apps/channels/telegram/handler.py`
- **Ответственность:** Telegram канал через aiogram 3.x. Webhook-режим. Обработка текста, фото, документов, inline-кнопок. Поддерживает как личные чаты (user_id), так и каналы организаций (org_id).
- **Классы:**
  - `TelegramChannel(BaseChannel)`
  - `setup_webhook(token, webhook_url)`
  - `on_message(message: aiogram.Message)`
  - `on_callback_query(query: aiogram.CallbackQuery)`
  - `send_with_markdown(chat_id, text)`
- **Зависимости:** `apps/channels/base.py`, `apps/channels/router.py`, `models/channel.py`
- **Источник:** OpenClaw (Telegram channel, webhook mode, group routing); обновлён: поддержка орг-каналов

---

### channels/vk/handler.py

- **Репо:** arkadius
- **Путь:** `apps/channels/vk/handler.py`
- **Ответственность:** VK Messenger канал через VK API Callback. Обработка личных сообщений и сообщений из групп ВКонтакте.
- **Классы:**
  - `VKChannel(BaseChannel)`
  - `verify_secret(request) -> bool`
  - `on_new_message(event: dict)`
  - `send_message(peer_id, text, keyboard=None)`
- **Зависимости:** `apps/channels/base.py`, `apps/channels/router.py`
- **Источник:** OpenClaw

---

### channels/max/handler.py

- **Репо:** arkadius
- **Путь:** `apps/channels/max/handler.py`
- **Ответственность:** MAX мессенджер (ex-ICQ) через MAX Bot API. Обработка текстовых сообщений, медиа, стикеров.
- **Классы:**
  - `MAXChannel(BaseChannel)`
  - `on_webhook(payload: dict)`
  - `send_message(chat_id, text)`
  - `send_media(chat_id, url, media_type)`
- **Зависимости:** `apps/channels/base.py`, `apps/channels/router.py`
- **Источник:** OpenClaw

---

### channels/router.py

- **Репо:** arkadius
- **Путь:** `apps/channels/router.py`
- **Ответственность:** Диспетчер входящих сообщений из всех каналов. Маршрутизирует сообщение к нужному агенту (пользователя или организации), создаёт/возобновляет сессию, передаёт в agent_loop.
- **Классы:**
  - `ChannelRouter`
  - `dispatch(message: ChannelMessage) -> None`
  - `resolve_user(channel_type, external_id) -> User | None`
  - `resolve_org(channel_type, external_id) -> Organization | None`
  - `get_or_create_session(user_id, org_id, channel_type, channel_id) -> ConversationSession`
  - `route_to_agent(session_id, message)`
- **Зависимости:** `apps/channels/base.py`, `apps/agent/agent_loop.py`, `models/channel.py`, `models/session.py`, `models/organization.py`
- **Источник:** OpenClaw (multi-agent routing, session model); обновлён: поддержка орг-агентов

---

### channels/media_pipeline.py

- **Репо:** arkadius
- **Путь:** `apps/channels/media_pipeline.py`
- **Ответственность:** Обработка медиафайлов: изображения, аудио (транскрипция через Whisper), документы. Загружает в S3, возвращает нормализованный ChannelMedia объект.
- **Классы:**
  - `MediaPipeline`
  - `process_image(file_bytes, filename) -> ChannelMedia`
  - `transcribe_audio(audio_bytes) -> str`
  - `process_document(file_bytes, filename) -> ChannelMedia`
  - `ChannelMedia(s3_key, type, transcription, metadata)`
- **Зависимости:** `infra/s3/storage.py`, `infra/llm/provider.py`
- **Источник:** OpenClaw (media pipeline, transcription hooks)

---

## 8. APPS/GROUPS — Групповые чаты

---

### groups/registry.py

- **Репо:** arkadius
- **Путь:** `apps/groups/registry.py`
- **Ответственность:** Реестр участников групповых чатов (первый уровень двухуровневой модели). Хранит полный список всех пользователей группы, их роли, время вступления.
- **Классы:**
  - `GroupRegistryService`
  - `register_participant(group_id, user_id, role)`
  - `unregister_participant(group_id, user_id)`
  - `get_participants(group_id) -> List[GroupParticipant]`
  - `is_member(group_id, user_id) -> bool`
- **Зависимости:** `core/database.py`, `models/channel.py`
- **Источник:** OpenClaw (двухуровневая модель групп)

---

### groups/profile.py

- **Репо:** arkadius
- **Путь:** `apps/groups/profile.py`
- **Ответственность:** Профили активных участников группы (второй уровень). Хранит ephemeral state: последняя активность, предпочтения в рамках группы.
- **Классы:**
  - `GroupProfileService`
  - `get_or_create_profile(group_id, user_id) -> GroupParticipantProfile`
  - `update_last_active(group_id, user_id)`
  - `set_awaiting_reply(group_id, user_id, awaiting: bool)`
  - `get_active_participants(group_id, since_minutes) -> List[GroupParticipantProfile]`
- **Зависимости:** `infra/cache/redis.py`, `models/channel.py`
- **Источник:** OpenClaw (group routing, activation modes)

---

## 9. APPS/BILLING — Биллинг

---

### billing/credit_manager.py

- **Репо:** arkadius
- **Путь:** `apps/billing/credit_manager.py`
- **Ответственность:** Управление кредитным балансом пользователей. Атомарное пополнение и списание. Защита от отрицательного баланса.
- **Классы:**
  - `CreditManager`
  - `get_balance(user_id) -> Decimal`
  - `debit(user_id, amount, description, ref_id) -> CreditTransaction`
  - `credit(user_id, amount, description, ref_id) -> CreditTransaction`
  - `get_transactions(user_id, limit, offset) -> List[CreditTransaction]`
- **Зависимости:** `core/database.py`, `models/billing.py`
- **Источник:** новый

---

### billing/usage_tracker.py

- **Репо:** arkadius
- **Путь:** `apps/billing/usage_tracker.py`
- **Ответственность:** Отслеживание и списание кредитов за использование LLM и инструментов. Конвертирует токены в кредиты по прайс-листу.
- **Классы:**
  - `UsageTracker`
  - `track_llm_usage(user_id, session_id, usage: UsageStats)`
  - `track_tool_usage(user_id, tool_name, duration_ms)`
  - `calculate_cost(usage: UsageStats) -> Decimal`
  - `get_usage_stats(user_id, period) -> UsageSummary`
- **Зависимости:** `apps/billing/credit_manager.py`, `apps/billing/pricing.py`, `models/tool.py`
- **Источник:** новый

---

### billing/yokassa.py

- **Репо:** arkadius-admin
- **Путь:** `billing_provider/yokassa.py`
- **Ответственность:** Интеграция с ЮKassa (ЮMoney). Создание платёжных ссылок, обработка webhook-уведомлений об оплате. После успешного платежа публикует событие в Redis → arkadius подхватывает и начисляет кредиты.
- **Классы:**
  - `YoKassaService`
  - `create_payment(user_id, amount_rub, description) -> PaymentLink`
  - `handle_webhook(payload: dict)` — verifies signature, publishes to Redis
  - `get_payment_status(payment_id) -> PaymentStatus`
  - `PaymentLink(url, payment_id, expires_at)`
- **Зависимости:** `core/config.py`, `infra/cache/redis.py`
- **Источник:** новый (arkadius-admin)

---

### billing/pricing.py

- **Репо:** arkadius
- **Путь:** `apps/billing/pricing.py`
- **Ответственность:** Прайс-лист: стоимость LLM токенов в кредитах, стоимость инструментов, тарифные планы.
- **Классы:**
  - `PricingService`
  - `get_token_price(model, token_type) -> Decimal`
  - `get_tool_price(tool_name) -> Decimal`
  - `get_plan(plan_id) -> PricingPlan`
  - `PricingPlan(name, monthly_credits, features)`
- **Зависимости:** `core/config.py`
- **Источник:** новый

---

## 10. APPS/API — FastAPI роуты

---

### api/v1/auth.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/auth.py`
- **Ответственность:** Эндпоинты аутентификации: регистрация, логин, refresh token, логаут, привязка Telegram.
- **Классы:**
  - `POST /auth/register`, `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `POST /auth/telegram`
- **Зависимости:** `core/security.py`, `apps/agent/agent_manager.py`, `models/user.py`
- **Источник:** новый

---

### api/v1/agents.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/agents.py`
- **Ответственность:** Управление агентом пользователя: конфиг, системный промпт, модель, состояние.
- **Классы:**
  - `GET /agents/me`, `PATCH /agents/me`, `GET /agents/me/state`, `POST /agents/me/reset`
- **Зависимости:** `core/dependencies.py`, `apps/agent/agent_manager.py`
- **Источник:** новый

---

### api/v1/orgs.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/api/v1/orgs.py`
- **Ответственность:** API для управления организациями: создание, управление участниками, орг-агент.
- **Классы:**
  - `POST /orgs` — создать организацию
  - `GET /orgs/{org_id}` — информация
  - `GET /orgs/{org_id}/members` — список участников
  - `POST /orgs/{org_id}/members` — добавить участника
  - `DELETE /orgs/{org_id}/members/{user_id}` — удалить
  - `PATCH /orgs/{org_id}/members/{user_id}` — изменить роль
  - `GET /orgs/{org_id}/agent` — орг-агент
- **Зависимости:** `core/dependencies.py`, `apps/agent/src/org/manager.py`, `apps/agent/agent_manager.py`
- **Источник:** новый (org-уровень)

---

### api/v1/vault.py *(новый)*

- **Репо:** arkadius
- **Путь:** `apps/api/v1/vault.py`
- **Ответственность:** API для управления секретами агента: список ключей, добавление, удаление. Получить расшифрованное значение нельзя через API — только изнутри sandbox.
- **Классы:**
  - `GET /vault/keys` — список ключей (без значений)
  - `PUT /vault/keys/{key_name}` — добавить/обновить секрет
  - `DELETE /vault/keys/{key_name}` — удалить
  - `GET /vault/keys/{key_name}/type` — тип секрета
- **Зависимости:** `core/dependencies.py`, `apps/agent/src/vault/manager.py`
- **Источник:** новый (vault)

---

### api/v1/sessions.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/sessions.py`
- **Ответственность:** CRUD сессий разговора: список, история сообщений, удаление.
- **Классы:**
  - `GET /sessions`, `GET /sessions/{id}/messages`, `DELETE /sessions/{id}`
- **Зависимости:** `core/dependencies.py`, `models/session.py`
- **Источник:** новый

---

### api/v1/messages.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/messages.py`
- **Ответственность:** Основной эндпоинт чата: отправка сообщений агенту, получение ответа через SSE streaming.
- **Классы:**
  - `POST /messages`, `GET /messages/stream`, `POST /messages/{id}/feedback`
- **Зависимости:** `core/dependencies.py`, `apps/agent/agent_loop.py`, `apps/billing/usage_tracker.py`
- **Источник:** новый

---

### api/v1/memory.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/memory.py`
- **Ответственность:** API для управления памятью агента: просмотр, поиск, ручное добавление/удаление.
- **Классы:**
  - `GET /memory`, `POST /memory`, `DELETE /memory/{id}`, `GET /memory/search?q=`
- **Зависимости:** `core/dependencies.py`, `apps/memory/memory_manager.py`, `apps/memory/memory_search.py`
- **Источник:** новый

---

### api/v1/channels.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/channels.py`
- **Ответственность:** Управление привязками каналов: добавление Telegram/VK/MAX аккаунтов, привязка к организации.
- **Классы:**
  - `GET /channels`, `POST /channels/telegram/link`, `DELETE /channels/{id}`
- **Зависимости:** `core/dependencies.py`, `models/channel.py`
- **Источник:** новый

---

### api/v1/billing.py

- **Репо:** arkadius
- **Путь:** `apps/api/v1/billing.py`
- **Ответственность:** Биллинг API: текущий баланс, история транзакций, создание платежа. Webhook от ЮKassa принимается в arkadius-admin, не здесь.
- **Классы:**
  - `GET /billing/balance`, `GET /billing/transactions`, `POST /billing/topup`
- **Зависимости:** `core/dependencies.py`, `apps/billing/credit_manager.py`
- **Источник:** новый

---

### api/websocket.py

- **Репо:** arkadius
- **Путь:** `apps/api/websocket.py`
- **Ответственность:** WebSocket эндпоинт для real-time взаимодействия через Web-канал. Bidirectional: сообщения пользователя → агент, стрим ответа агента ← система.
- **Классы:**
  - `WebSocket /ws/{session_token}`
  - `WebSocketManager` — реестр активных соединений
  - `broadcast_to_session(session_id, event)`
  - `WSEvent` — union: UserMessage | AgentDelta | AgentDone | Error | AskUser
- **Зависимости:** `core/security.py`, `apps/agent/agent_loop.py`, `infra/cache/redis.py`
- **Источник:** OpenClaw

---

## 11. APPS/WORKER — Celery

---

### worker/celery_app.py

- **Репо:** arkadius
- **Путь:** `apps/worker/celery_app.py`
- **Ответственность:** Конфигурация Celery: broker (Redis), backend (Redis), routing задач, настройки Celery Beat (KAIROS, autoDream, cleanup).
- **Классы:**
  - `celery_app = Celery(...)` — singleton
  - `beat_schedule` — расписание периодических задач
  - `task_routes` — routing по очередям
- **Зависимости:** `core/config.py`
- **Источник:** OpenClaw

---

### worker/tasks/dream_task.py

- **Репо:** arkadius
- **Путь:** `apps/worker/tasks/dream_task.py`
- **Ответственность:** Celery task для autoDream. Запускается по расписанию для каждого активного агента или триггером после длинной сессии.
- **Классы:**
  - `@celery_app.task auto_dream(agent_id: str)`
  - `@celery_app.task trigger_dream(agent_id: str, trigger: str)`
- **Зависимости:** `apps/worker/celery_app.py`, `apps/agent/dream.py`
- **Источник:** OpenClaw

---

### worker/tasks/kairos_task.py

- **Репо:** arkadius
- **Путь:** `apps/worker/tasks/kairos_task.py`
- **Ответственность:** Celery Beat периодическая задача KAIROS. Запускается каждые N минут.
- **Классы:**
  - `@celery_app.task kairos_tick()`
- **Зависимости:** `apps/worker/celery_app.py`, `apps/agent/kairos.py`
- **Источник:** OpenClaw

---

### worker/tasks/sandbox_cleanup.py

- **Репо:** arkadius-admin
- **Путь:** `sandbox/tasks/sandbox_cleanup.py`
- **Ответственность:** Уборка заброшенных Docker sandbox-контейнеров. Запускается каждые 30 минут, уничтожает контейнеры простаивающие более N часов.
- **Классы:**
  - `@celery_app.task cleanup_idle_sandboxes()`
- **Зависимости:** `sandbox/docker_manager.py`
- **Источник:** OpenClaw

---

### worker/tasks/subagent_task.py

- **Репо:** arkadius
- **Путь:** `apps/worker/tasks/subagent_task.py`
- **Ответственность:** Celery task для выполнения субагентов (Researcher/Coder/Учёный) в фоне. Изолированный agent loop с ограниченным набором инструментов.
- **Классы:**
  - `@celery_app.task run_subagent(task_id: str)`
- **Зависимости:** `apps/worker/celery_app.py`, `apps/agent/subagent_router.py`, `infra/llm/provider.py`
- **Источник:** nano-claude-code (background mode subagents)

---

## 12. ARKADIUS-ADMIN — Специфичные модули

---

### litellm/config_manager.py

- **Репо:** arkadius-admin
- **Путь:** `litellm/config_manager.py`
- **Ответственность:** Управление конфигурацией LiteLLM прокси: список моделей, API ключи провайдеров, rate limits, cost tracking. Предоставляет API для обновления конфига без рестарта.
- **Классы:**
  - `LiteLLMConfigManager`
  - `get_active_models() -> List[ModelConfig]`
  - `update_model_config(model_id, config)`
  - `set_provider_key(provider, api_key)`
  - `get_usage_stats(period) -> UsageReport`
- **Зависимости:** `core/config.py`
- **Источник:** новый (arkadius-admin)

---

### monitoring/dashboard.py

- **Репо:** arkadius-admin
- **Путь:** `monitoring/dashboard.py`
- **Ответственность:** Сбор и отображение метрик системы: активные агенты, использование LLM, биллинг, health sandbox-контейнеров. Prometheus metrics + Grafana дашборды.
- **Классы:**
  - `MetricsCollector`
  - `get_system_health() -> HealthReport`
  - `get_billing_summary(period) -> BillingSummary`
  - `get_agent_activity_stats() -> AgentStats`
- **Зависимости:** `infra/cache/redis.py`, общая PostgreSQL БД
- **Источник:** новый (arkadius-admin)

---

### admin_api/internal.py

- **Репо:** arkadius-admin
- **Путь:** `admin_api/internal.py`
- **Ответственность:** Внутренний REST API для межсервисного взаимодействия. Принимает запросы от arkadius: проверка billing, exec кода в sandbox, вебхук ЮKassa. Защищён shared secret (не публичный JWT).
- **Классы:**
  - `POST /internal/sandbox/exec` — выполнить код в sandbox
  - `GET /internal/billing/check/{user_id}` — проверить баланс
  - `POST /internal/billing/webhook/yokassa` — webhook ЮKassa
  - `POST /internal/sandbox/create` — создать sandbox
  - `DELETE /internal/sandbox/{user_id}` — уничтожить sandbox
- **Зависимости:** `sandbox/docker_manager.py`, `sandbox/exec_runner.py`, `billing_provider/yokassa.py`
- **Источник:** новый (arkadius-admin)

---

## 13. NODES — Управление нодами пользователя

---

### apps/agent/src/nodes/manager.py

- **Репо:** arkadius
- **Путь:** `apps/agent/src/nodes/manager.py`
- **Ответственность:** Управление подключёнными нодами. Регистрация, пейринг, мониторинг статуса, маршрутизация exec запросов на нужную ноду.
- **Классы:**
  - `NodeManager`
  - `NodeRegistry`
- **Зависимости:** `models/node.py`, `infra/cache/redis.py`, `apps/agent/src/vault/manager.py`
- **Источник:** новый (по образцу OpenClaw node-host)

---

### apps/agent/src/nodes/executor.py

- **Репо:** arkadius
- **Путь:** `apps/agent/src/nodes/executor.py`
- **Ответственность:** Выполнение команд на ноде через WebSocket туннель. Получает результат и возвращает агенту.
- **Классы:**
  - `NodeExecutor`
  - `ExecResult`
- **Зависимости:** `apps/agent/src/nodes/manager.py`
- **Источник:** новый

---

### apps/agent/src/nodes/ssh_installer.py

- **Репо:** arkadius
- **Путь:** `apps/agent/src/nodes/ssh_installer.py`
- **Ответственность:** Автоматическая установка `arkadius-node-server` на сервер пользователя по SSH. Скачивает бинарник, настраивает systemd сервис.
- **Классы:**
  - `SSHInstaller`
- **Зависимости:** `apps/agent/src/vault/manager.py` (для SSH ключей)
- **Источник:** новый

---

### models/node.py

- **Репо:** arkadius
- **Путь:** `models/node.py`
- **Ответственность:** SQLAlchemy модель ноды.
- **Классы:**
  - `Node(Base)` — id, org_id, name, node_type: ssh|client, status, capabilities JSONB, ssh_host, ssh_user, ssh_key_id
- **Зависимости:** `core/database.py`
- **Источник:** новый

---

## 14. SANDBOX — Облачные контейнеры (arkadius-admin)

---

### apps/sandbox/manager.py

- **Репо:** arkadius-admin
- **Путь:** `apps/sandbox/manager.py`
- **Ответственность:** Управление облачными Docker sandbox контейнерами. Создание по требованию, мониторинг, уничтожение после таймаута. Три уровня: Micro/Small/Medium.
- **Классы:**
  - `SandboxManager`
  - `SandboxInstance`
- **Зависимости:** `infra/docker.py`, `models/sandbox.py`
- **Источник:** новый

---

### apps/sandbox/router.py

- **Репо:** arkadius
- **Путь:** `apps/sandbox/router.py`
- **Ответственность:** Роутер выполнения кода. Если есть активная нода → отправляет туда. Нет ноды → запрашивает облачный sandbox через arkadius-admin API.
- **Классы:**
  - `ExecRouter`
- **Зависимости:** `apps/agent/src/nodes/manager.py`, `infra/admin_client.py`
- **Источник:** новый

---

## 15. INTEGRATIONBUILDER — Самописные интеграции агента

---

### apps/agent/src/integrations/builder.py

- **Репо:** arkadius
- **Путь:** `apps/agent/src/integrations/builder.py`
- **Ответственность:** Позволяет агенту самостоятельно писать интеграции с внешними сервисами. Исследует API → пишет Python код → тестирует через sandbox/ноду → регистрирует как инструмент.
- **Классы:**
  - `IntegrationBuilder`
  - `IntegrationSpec`
- **Методы:** `research_api()`, `write_integration()`, `test_integration()`, `register_tool()`, `save_credentials()`
- **Зависимости:** `apps/tools/registry.py`, `apps/sandbox/router.py`, `apps/agent/src/vault/manager.py`
- **Источник:** новый

---

### models/agent_integration.py

- **Репо:** arkadius
- **Путь:** `models/agent_integration.py`
- **Ответственность:** Хранение написанных агентом интеграций.
- **Классы:**
  - `AgentIntegration(Base)` — id, agent_id, service_name, integration_code, tool_schema JSONB, status: active|testing|failed, created_by: user|scientist
- **Зависимости:** `core/database.py`, `models/agent.py`
- **Источник:** новый

---

## 16. МЕЖСЕРВИСНОЕ ВЗАИМОДЕЙСТВИЕ

Два репозитория — `arkadius` и `arkadius-admin` — общаются через три механизма.

---

### 13.1 REST API (синхронные вызовы)

`arkadius` → `arkadius-admin` через внутренний HTTP API.  
Адрес задаётся через `ADMIN_API_URL` в env (например, `http://arkadius-admin:8001`).  
Авторизация: shared secret в заголовке `X-Internal-Token`.

| Вызов из arkadius | Эндпоинт в arkadius-admin | Назначение |
|-------------------|--------------------------|-----------|
| `CodeExecTool.execute()` | `POST /internal/sandbox/exec` | Выполнить код в Docker sandbox |
| `DockerSandboxManager.get_or_create()` | `POST /internal/sandbox/create` | Создать sandbox для нового пользователя |
| `DockerSandboxManager.destroy_sandbox()` | `DELETE /internal/sandbox/{user_id}` | Удалить sandbox |
| `billing/credit_manager.py` (topup) | `GET /internal/billing/check/{user_id}` | Проверка баланса перед дорогой операцией |

---

### 13.2 Общая PostgreSQL БД

Оба сервиса пишут/читают из одной БД через разные схемы:

| Схема | Владелец | Читатель |
|-------|----------|---------|
| `public` (users, agents, sessions, memory, ...) | arkadius | arkadius-admin (только чтение для мониторинга) |
| `admin` (litellm_config, sandbox_state, audit_log) | arkadius-admin | arkadius (только чтение) |

Прямые JOIN между схемами допустимы только для monitoring/reporting. Бизнес-логика не должна зависеть от cross-schema запросов.

---

### 13.3 Redis Pub/Sub (асинхронные события)

Используется для событий, где не нужен синхронный ответ.

| Канал | Публикует | Подписан | Событие |
|-------|-----------|---------|---------|
| `billing:topup:{user_id}` | arkadius-admin (после webhook ЮKassa) | arkadius (credit_manager) | Пополнение баланса → начислить кредиты |
| `sandbox:ready:{user_id}` | arkadius-admin (после создания контейнера) | arkadius (agent_loop) | Sandbox готов → можно запускать код |
| `sandbox:destroyed:{user_id}` | arkadius-admin (после cleanup) | arkadius (agent_manager) | Sandbox уничтожен → обновить статус агента |
| `litellm:ratelimit` | arkadius-admin (LiteLLM прокси) | arkadius (infra/llm/provider.py) | Rate limit достигнут → бэкофф |

---

## 17. BROWSER POOL (репо: arkadius-admin)

**Концепция:** Браузеры не постоянные — pool фиксированного размера (~50 экземпляров). Каждый агент берёт браузер из pool, восстанавливает сессию из vault, выполняет задачу, сохраняет сессию обратно, возвращает браузер в pool.

---

### `infra/browser_pool.py`

- **Репо:** arkadius-admin
- **Путь:** `infra/browser_pool.py`
- **Ответственность:** Connection pool браузеров фиксированного размера. Управляет жизненным циклом Playwright/Camoufox экземпляров. Если все заняты — очередь ожидания.
- **Классы:** `BrowserPool`, `BrowserSession`
- **Методы:** `acquire(user_id) → BrowserSession`, `release(session)`, `get_stats()`
- **Зависимости:** `infra/browser_state.py`, `infra/camoufox.py`
- **Источник:** новый

---

### `infra/browser_state.py`

- **Репо:** arkadius-admin
- **Путь:** `infra/browser_state.py`
- **Ответственность:** Сохранение и восстановление состояния браузера (cookies, localStorage, sessionStorage) через vault агента. Шифрует состояние перед сохранением.
- **Классы:** `BrowserStateManager`
- **Методы:** `save_state(user_id, page) → encrypted_state`, `restore_state(user_id, page)`, `clear_state(user_id)`
- **Зависимости:** `apps/agent/src/vault/manager.py`
- **Источник:** новый

---

### `infra/camoufox.py`

- **Репо:** arkadius-admin
- **Путь:** `infra/camoufox.py`
- **Ответственность:** Интеграция с Camoufox (anti-detect Firefox) для сайтов с защитой от ботов. Используется вместо обычного Playwright когда обычный браузер блокируется.
- **Классы:** `CamoufoxDriver`
- **Методы:** `launch(headless, fingerprint)`, `connect_playwright()`
- **Зависимости:** нет
- **Источник:** camoufox skill

---

### `apps/agent/src/tools/browser.py`

- **Репо:** arkadius
- **Путь:** `apps/agent/src/tools/browser.py`
- **Ответственность:** Инструмент браузера для агента. Запрашивает сессию из BrowserPool (через arkadius-admin API), выполняет действия (navigate, click, type, screenshot, extract), возвращает результат агенту.
- **Классы:** `BrowserTool`
- **Методы:** `navigate(url)`, `click(selector)`, `type(selector, text)`, `screenshot()`, `extract_text()`, `get_page_data()`
- **Зависимости:** `infra/admin_client.py`, `apps/tools/registry.py`
- **Источник:** новый + OpenClaw browser tool паттерн

---

## Сводная таблица модулей

| Модуль | Репо | Слой | Источник |
|--------|------|------|---------|
| `core/config.py` | arkadius | Core | OpenClaw + nano |
| `core/database.py` | arkadius | Core | OpenClaw |
| `core/exceptions.py` | arkadius | Core | новый |
| `core/security.py` | arkadius | Core | новый |
| `core/dependencies.py` | arkadius | Core | новый |
| `infra/s3/client.py` | arkadius | Infra | OpenClaw |
| `infra/s3/storage.py` | arkadius | Infra | OpenClaw |
| `infra/cache/redis.py` | arkadius | Infra | OpenClaw |
| `infra/llm/provider.py` | arkadius | Infra | nano-claude-code |
| `infra/llm/context_manager.py` | arkadius | Infra | nano-claude-code |
| `sandbox/docker_manager.py` | **arkadius-admin** | Infra | OpenClaw |
| `sandbox/exec_runner.py` | **arkadius-admin** | Infra | OpenClaw |
| `models/user.py` | arkadius | DB | новый |
| `models/agent.py` | arkadius | DB | OpenClaw (обновлён) |
| `models/session.py` | arkadius | DB | nano |
| `models/memory.py` | arkadius | DB | nano (обновлён) |
| `models/tool.py` | arkadius | DB | новый |
| `models/subagent.py` | arkadius | DB | nano |
| `models/billing.py` | arkadius | DB | новый |
| `models/channel.py` | arkadius | DB | OpenClaw (обновлён) |
| `models/organization.py` | arkadius | DB | **новый (org)** |
| `models/agent_secret.py` | arkadius | DB | **новый (vault)** |
| `apps/agent/agent_loop.py` | arkadius | Agent | nano + OpenClaw |
| `apps/agent/agent_manager.py` | arkadius | Agent | OpenClaw (обновлён) |
| `apps/agent/context_builder.py` | arkadius | Agent | nano + OpenClaw |
| `apps/agent/dream.py` | arkadius | Agent | OpenClaw |
| `apps/agent/kairos.py` | arkadius | Agent | OpenClaw |
| `apps/agent/subagent_router.py` | arkadius | Agent | nano |
| `apps/agent/subagent_pool.py` | arkadius | Agent | nano |
| `apps/agent/persona.py` | arkadius | Agent | новый |
| `apps/agent/src/org/manager.py` | arkadius | Org | **новый (org)** |
| `apps/agent/src/org/memory.py` | arkadius | Org | **новый (org)** |
| `apps/agent/src/vault/manager.py` | arkadius | Vault | **новый (vault)** |
| `apps/agent/src/vault/encryption.py` | arkadius | Vault | **новый (vault)** |
| `apps/tools/registry.py` | arkadius | Tools | nano + OpenClaw |
| `apps/tools/base.py` | arkadius | Tools | nano |
| `apps/tools/builtin/*` (7 файлов) | arkadius | Tools | nano |
| `apps/tools/permission.py` | arkadius | Tools | nano |
| `apps/memory/memory_manager.py` | arkadius | Memory | nano (обновлён) |
| `apps/memory/memory_search.py` | arkadius | Memory | nano |
| `apps/memory/compressor.py` | arkadius | Memory | nano |
| `apps/memory/s3_snapshot.py` | arkadius | Memory | OpenClaw |
| `apps/channels/base.py` | arkadius | Channels | OpenClaw |
| `apps/channels/web/handler.py` | arkadius | Channels | OpenClaw |
| `apps/channels/telegram/handler.py` | arkadius | Channels | OpenClaw (обновлён) |
| `apps/channels/vk/handler.py` | arkadius | Channels | OpenClaw |
| `apps/channels/max/handler.py` | arkadius | Channels | OpenClaw |
| `apps/channels/router.py` | arkadius | Channels | OpenClaw (обновлён) |
| `apps/channels/media_pipeline.py` | arkadius | Channels | OpenClaw |
| `apps/groups/registry.py` | arkadius | Groups | OpenClaw |
| `apps/groups/profile.py` | arkadius | Groups | OpenClaw |
| `apps/billing/credit_manager.py` | arkadius | Billing | новый |
| `apps/billing/usage_tracker.py` | arkadius | Billing | новый |
| `billing_provider/yokassa.py` | **arkadius-admin** | Billing | новый |
| `apps/billing/pricing.py` | arkadius | Billing | новый |
| `apps/api/v1/auth.py` | arkadius | API | новый |
| `apps/api/v1/agents.py` | arkadius | API | новый |
| `apps/api/v1/orgs.py` | arkadius | API | **новый (org)** |
| `apps/api/v1/vault.py` | arkadius | API | **новый (vault)** |
| `apps/api/v1/sessions.py` | arkadius | API | новый |
| `apps/api/v1/messages.py` | arkadius | API | новый |
| `apps/api/v1/memory.py` | arkadius | API | новый |
| `apps/api/v1/channels.py` | arkadius | API | новый |
| `apps/api/v1/billing.py` | arkadius | API | новый |
| `apps/api/websocket.py` | arkadius | API | OpenClaw |
| `apps/worker/celery_app.py` | arkadius | Worker | OpenClaw |
| `apps/worker/tasks/dream_task.py` | arkadius | Worker | OpenClaw |
| `apps/worker/tasks/kairos_task.py` | arkadius | Worker | OpenClaw |
| `sandbox/tasks/sandbox_cleanup.py` | **arkadius-admin** | Worker | OpenClaw |
| `apps/worker/tasks/subagent_task.py` | arkadius | Worker | nano |
| `litellm/config_manager.py` | **arkadius-admin** | Admin | новый |
| `monitoring/dashboard.py` | **arkadius-admin** | Admin | новый |
| `admin_api/internal.py` | **arkadius-admin** | Admin | новый |

| `apps/agent/src/nodes/manager.py` | arkadius | Nodes | **новый (nodes)** |
| `apps/agent/src/nodes/executor.py` | arkadius | Nodes | **новый (nodes)** |
| `apps/agent/src/nodes/ssh_installer.py` | arkadius | Nodes | **новый (nodes)** |
| `models/node.py` | arkadius | DB | **новый (nodes)** |
| `apps/sandbox/manager.py` | **arkadius-admin** | Sandbox | **новый (sandbox)** |
| `apps/sandbox/router.py` | arkadius | Sandbox | **новый (sandbox)** |
| `apps/agent/src/integrations/builder.py` | arkadius | Integration | **новый (integration)** |
| `models/agent_integration.py` | arkadius | DB | **новый (integration)** |
| `infra/browser_pool.py` | **arkadius-admin** | Infra | **новый (browser-pool)** |
| `infra/browser_state.py` | **arkadius-admin** | Infra | **новый (browser-pool)** |
| `infra/camoufox.py` | **arkadius-admin** | Infra | **новый (browser-pool)** |
| `apps/agent/src/tools/browser.py` | arkadius | Tools | **новый (browser-pool)** |

**Итого: 88 модулей** (было 84, добавлено 4 новых)  
**arkadius:** 75 модулей | **arkadius-admin:** 13 модулей

---

## Ключевые архитектурные решения (закреплённые)

| Решение | Реализация |
|---------|-----------|
| Агенты в БД | `models/agent.py` + `apps/agent/agent_manager.py` |
| S3 для persistent storage | `infra/s3/storage.py` + `apps/memory/s3_snapshot.py` |
| ToolRegistry с @decorator | `apps/tools/registry.py` |
| autoDream как Celery task | `apps/worker/tasks/dream_task.py` + `apps/agent/dream.py` |
| KAIROS как background tick | `apps/worker/tasks/kairos_task.py` + `apps/agent/kairos.py` |
| Двухуровневая модель групп | `apps/groups/registry.py` + `apps/groups/profile.py` |
| Только Anthropic через LiteLLM | `infra/llm/provider.py` → LiteLLM прокси в arkadius-admin |
| ЮKassa prepaid кредиты | `billing_provider/yokassa.py` (admin) + `apps/billing/credit_manager.py` |
| Docker sandbox в admin-репо | `sandbox/docker_manager.py` (arkadius-admin) |
| **Org-уровень** | `models/organization.py` + `apps/agent/src/org/manager.py` + `apps/agent/src/org/memory.py` |
| **Vault секретов агента** | `models/agent_secret.py` + `apps/agent/src/vault/manager.py` + `apps/agent/src/vault/encryption.py` |
| **Двухуровневая память personal+org** | `apps/memory/memory_manager.py` (scope=personal\|org\|project) |
| **Inter-service через REST + Redis** | `admin_api/internal.py` + Redis pub/sub (топики billing/sandbox) |
| **Ноды пользователя** | `models/node.py` + `apps/agent/src/nodes/manager.py` + `apps/agent/src/nodes/executor.py` + `apps/agent/src/nodes/ssh_installer.py` |
| **Роутинг exec (node/sandbox)** | `apps/sandbox/router.py` — нода → приоритет, фоллбэк на облачный sandbox |
| **SandboxManager (3 уровня)** | `apps/sandbox/manager.py` (arkadius-admin): Micro/Small/Medium |
| **IntegrationBuilder** | `apps/agent/src/integrations/builder.py` — агент пишет и регистрирует интеграции как инструменты |
| **Хранение интеграций** | `models/agent_integration.py` — код + schema + статус |
| **Browser Pool** | `infra/browser_pool.py` (arkadius-admin) — pool ~50 браузеров; агент acquire → restore session → task → save session → release |
