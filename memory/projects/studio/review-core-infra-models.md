# Ревью модулей CORE, INFRA, MODELS — Аркадиус

> Автор: Аркаша (субагент-архитектор)  
> Дата: 2026-04-04  
> Источники: arkadius-modules.md (разделы 1-3) + nano-claude-code (SafeRL-Lab/nano-claude-code)

---

## Контекст ревью

**Важное ограничение MVP:** один Anthropic API ключ в `arkadius-admin`, прямой SDK — **без LiteLLM**.  
nano-claude-code сам использует прямой `ANTHROPIC_API_KEY` через Anthropic SDK.  
Всё что упоминает LiteLLM в INFRA — ошибка проектирования, нужно исправить.

---

## РАЗДЕЛ 1: CORE

### `core/config.py`

**Оценка ответственности:** Правильная. Единая точка конфигурации через Pydantic Settings — стандартный паттерн.

**Пропущено из nano-claude-code:**
- `CompactionSettings` — порог автокомпрессии (`COMPACTION_THRESHOLD = 0.7`, т.е. 70% контекстного окна). В nano-claude-code это жёстко задано в `compaction.py`, но для серверного решения лучше выносить в конфиг.
- `AdminAPISettings(base_url, internal_token)` — для межсервисного взаимодействия arkadius → arkadius-admin. Сейчас `ADMIN_API_URL` упоминается в инструментах, но в конфиге класса нет.

**Лишнее для MVP:**
- ❌ `LiteLLMSettings` — убрать полностью. MVP не использует LiteLLM прокси.

**Конкретные правки:**
```python
# УБРАТЬ:
class LiteLLMSettings(BaseSettings):
    ...

# ДОБАВИТЬ:
class AnthropicSettings(BaseSettings):
    api_key: str = Field(env="ANTHROPIC_API_KEY")
    default_model: str = "claude-sonnet-4-6"
    max_tokens: int = 8192
    compaction_threshold: float = 0.7  # % контекста до автокомпрессии

class AdminAPISettings(BaseSettings):
    url: str = Field(env="ADMIN_API_URL", default="http://arkadius-admin:8001")
    internal_token: str = Field(env="INTERNAL_API_TOKEN")

# В Settings убрать LiteLLMSettings, добавить AnthropicSettings и AdminAPISettings
class Settings(BaseSettings):
    db: DatabaseSettings = DatabaseSettings()
    s3: S3Settings = S3Settings()
    redis: RedisSettings = RedisSettings()
    anthropic: AnthropicSettings = AnthropicSettings()  # вместо litellm
    admin: AdminAPISettings = AdminAPISettings()
    vault_master_key: str = Field(env="VAULT_MASTER_KEY")
```

---

### `core/database.py`

**Оценка ответственности:** Правильная. Настройка async engine, фабрика сессий, pgvector.

**Пропущено из nano-claude-code:**
- nano-claude-code не использует БД (файловый storage), поэтому прямых аналогов нет. Это наше уникальное решение для серверного продукта — всё правильно.

**Что стоит добавить:**
- `check_pgvector_extension() -> bool` — проверка при старте приложения что pgvector установлен в PostgreSQL. Лучше упасть с понятной ошибкой сразу, чем получить непонятный SQL error при первом поиске по памяти.

**Лишнее:** Ничего. Модуль лаконичный и корректный.

**Конкретная правка:**
```python
async def check_pgvector_extension() -> None:
    """Проверить что pgvector установлен. Вызывать при startup."""
    async with AsyncSessionFactory() as session:
        result = await session.execute(
            text("SELECT extname FROM pg_extension WHERE extname = 'vector'")
        )
        if not result.scalar():
            raise RuntimeError(
                "pgvector extension не установлена в PostgreSQL. "
                "Выполните: CREATE EXTENSION vector;"
            )
```

---

### `core/exceptions.py`

**Оценка ответственности:** Правильная. Иерархия доменных исключений.

**Пропущено из nano-claude-code:**
- В nano-claude-code нет явной иерархии исключений (всё обрабатывается прямо в agent.py), но для нашего серверного решения иерархия нужна.
- Нет специализированных Anthropic-ошибок. `LLMError` — слишком общий.

**Конкретные правки:**
```python
# ДОБАВИТЬ специализацию:
class AnthropicRateLimitError(LLMError):
    """429 от Anthropic API — нужно ждать."""
    retry_after: int = 60  # секунды

class AnthropicOverloadedError(LLMError):
    """529 от Anthropic API — перегрузка серверов."""

class AnthropicAPIError(LLMError):
    """Прочие ошибки Anthropic API."""
    status_code: int

# ПЕРЕИМЕНОВАТЬ (опционально, не критично):
# LLMError → оставить, просто сделать его родителем Anthropic-специфичных
```

---

### `core/security.py`

**Оценка ответственности:** Правильная. JWT + пароли + tenant isolation.

**Пропущено:** Ничего существенного для MVP.

**Лишнее:** Ничего.

---

### `core/dependencies.py`

**Оценка ответственности:** Правильная. DI контейнер FastAPI.

**Пропущено:**
- `get_anthropic_client()` — dependency для получения AnthropicClient (если решим инжектировать через DI вместо singleton). Не критично для MVP.

**Лишнее:** Ничего.

---

## РАЗДЕЛ 2: INFRA

### `infra/llm/provider.py` ← КРИТИЧНАЯ ПРАВКА

**Оценка ответственности:** Неверная для MVP. Описан как "клиент к LiteLLM прокси" — это противоречит решению MVP об одном Anthropic ключе без LiteLLM.

**Пропущено из nano-claude-code:**
- nano-claude-code использует прямой `anthropic.Anthropic()` SDK в `providers.py`, никакого прокси.
- Extended Thinking поддержка (бета-фича Anthropic) — нужна для сложных задач
- Нативный подсчёт токенов через `client.messages.count_tokens()` — вместо эвристик

**Лишнее для MVP:**
- ❌ Весь концепт "клиент к LiteLLM прокси" — убрать
- ❌ Роутинг через ADMIN_API_URL для LLM — убрать

**Конкретные правки:**
```python
# БЫЛО (неверно для MVP):
class LiteLLMProvider:
    """Клиент к LiteLLM прокси (расположен в arkadius-admin)."""
    
# СТАЛО:
class AnthropicProvider:
    """
    Прямой клиент к Anthropic API через SDK.
    Единственная точка взаимодействия с Anthropic.
    Поддерживает streaming, подсчёт токенов для биллинга,
    retry при rate limits.
    """
    def __init__(self, client: "AnthropicClient"): ...  # инжектируется из infra/anthropic_client.py
    
    async def complete(
        self, 
        messages: list, 
        tools: list | None,
        model: str,
        stream: bool,
        thinking: bool = False  # Extended Thinking support
    ) -> AsyncGenerator[LLMChunk]: ...
    
    async def count_tokens(self, messages: list) -> int:
        """Нативный подсчёт через client.messages.count_tokens()."""
        ...
```

---

### НОВЫЙ МОДУЛЬ: `infra/anthropic_client.py` ← ДОБАВИТЬ

**Почему нужен:** Уже написан `provider.py`, но нужен отдельный низкоуровневый клиент-обёртка над SDK. Аналог того, что nano-claude-code делает в `providers.py` — инициализация, retry, rate limit handling.

**Ответственность:** Обёртка над `anthropic.AsyncAnthropic`. Настройка retry политики, логирование API вызовов, health check.

```python
# infra/anthropic_client.py
from anthropic import AsyncAnthropic, APIStatusError
from tenacity import retry, stop_after_attempt, wait_exponential

class AnthropicClient:
    """
    Синглтон-обёртка над Anthropic AsyncAnthropic SDK.
    Настраивает retry, таймауты, логирование.
    Не содержит бизнес-логики — только транспортный уровень.
    """
    
    def __init__(self, api_key: str, timeout: float = 60.0):
        self._client = AsyncAnthropic(
            api_key=api_key,
            timeout=timeout,
        )
    
    @property
    def messages(self):
        return self._client.messages
    
    async def health_check(self) -> bool:
        """Проверить доступность API."""
        ...
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60)
    )
    async def create_message(self, **kwargs):
        """Вызов с автоматическим retry при 429/529."""
        ...

def get_anthropic_client() -> AnthropicClient:
    """FastAPI dependency / singleton фабрика."""
    ...
```

**Зависимости:** `core/config.py` (AnthropicSettings)  
**Кто использует:** `infra/llm/provider.py`, `apps/memory/memory_search.py` (для embed через Claude)

---

### НОВЫЙ МОДУЛЬ: `infra/admin_client.py` ← ДОБАВИТЬ

**Почему нужен:** Модуль упоминается как зависимость в `apps/sandbox/router.py`, но не описан в INFRA. Это HTTP-клиент для синхронных вызовов arkadius → arkadius-admin.

**Ответственность:** Низкоуровневый HTTP клиент для internal API arkadius-admin. Авторизация через X-Internal-Token. Таймаут, retry.

```python
# infra/admin_client.py
import httpx

class AdminAPIClient:
    """
    HTTP-клиент для межсервисных вызовов arkadius → arkadius-admin.
    Авторизация: X-Internal-Token header.
    """
    def __init__(self, base_url: str, internal_token: str): ...
    
    async def exec_code(self, user_id: str, language: str, code: str, timeout: int) -> dict: ...
    async def create_sandbox(self, user_id: str) -> dict: ...
    async def destroy_sandbox(self, user_id: str) -> None: ...
    async def check_billing(self, user_id: str) -> dict: ...

def get_admin_client() -> AdminAPIClient:
    """FastAPI dependency."""
    ...
```

**Зависимости:** `core/config.py` (AdminAPISettings)

---

### `infra/llm/context_manager.py`

**Оценка ответственности:** Правильная. Управление контекстным окном.

**Пропущено из nano-claude-code:**
- nano-claude-code реализует двухуровневую компрессию в `compaction.py`:
  1. **Snip** — быстрое обрезание старых tool outputs без LLM вызова (бесплатно)
  2. **Auto-compact** — суммаризация через LLM когда snip недостаточен (платно)
- В нашем `context_manager.py` описан только один уровень (суммаризация через LLM). Нужно добавить snip.
- Явный порог компрессии (threshold) не упомянут.

**Конкретные правки:**
```python
class ContextManager:
    COMPACTION_THRESHOLD = 0.7  # 70% контекста → начинаем компрессию

    def snip_tool_outputs(
        self, 
        messages: list, 
        max_output_chars: int = 2000
    ) -> list:
        """
        ПЕРВЫЙ уровень: Быстро обрезать старые tool outputs без LLM вызова.
        Аналог nano-claude-code compaction.py:snip().
        Бесплатно, применяется первым.
        """
        ...

    async def compress_conversation(
        self, 
        messages: list, 
        keep_last_n: int = 10
    ) -> Summary:
        """
        ВТОРОЙ уровень: Суммаризация через LLM когда snip недостаточен.
        Применяется только если после snip всё ещё > threshold.
        """
        ...
    
    async def fit_messages(
        self, 
        messages: list, 
        max_tokens: int
    ) -> list:
        """
        Основной метод: сначала snip, потом compress если нужно.
        """
        # 1. Посчитать текущие токены
        # 2. Если < threshold → вернуть как есть
        # 3. snip_tool_outputs()
        # 4. Пересчитать. Если всё ещё > threshold → compress_conversation()
        ...
```

---

### `infra/s3/client.py`

**Оценка ответственности:** Правильная. Низкоуровневый S3 адаптер.

**Пропущено:** Ничего существенного.

**Лишнее:** Ничего. Для MVP это нужно.

---

### `infra/s3/storage.py`

**Оценка ответственности:** Правильная. Высокоуровневое API для работы с S3.

**Пропущено:** Ничего.

**Лишнее:** Ничего.

---

### `infra/cache/redis.py`

**Оценка ответственности:** Правильная. Кэш, pub/sub, rate limiting.

**Пропущено из nano-claude-code:**
- nano-claude-code не использует Redis (CLI инструмент), поэтому сравнение не релевантно.
- Стоит добавить `acquire_lock(key, timeout) / release_lock(key)` — distributed lock для критических операций (например, чтобы два воркера не дебетовали один кредитный аккаунт одновременно).

**Конкретная правка:**
```python
# ДОБАВИТЬ:
async def acquire_lock(self, key: str, timeout: int = 30) -> bool:
    """Распределённая блокировка через SET NX EX."""
    return await self._client.set(f"lock:{key}", "1", nx=True, ex=timeout)

async def release_lock(self, key: str) -> None:
    await self._client.delete(f"lock:{key}")
```

---

## РАЗДЕЛ 3: MODELS

### `models/user.py`

**Оценка ответственности:** Правильная.

**Лишнее для MVP:**
- ⚠️ `UserProfile(Base)` — для MVP можно объединить поля `display_name`, `timezone`, `language` прямо в `User`. Отдельная таблица — это оверинжиниринг на старте. Если нужна нормализация — добавить позже.

**Конкретная правка:**
```python
# MVP: объединить UserProfile в User
class User(Base):
    __tablename__ = "users"
    id: Mapped[UUID]
    email: Mapped[str]
    hashed_password: Mapped[str]
    display_name: Mapped[str | None]
    timezone: Mapped[str] = mapped_column(default="UTC")
    language: Mapped[str] = mapped_column(default="ru")
    created_at: Mapped[datetime]
    is_active: Mapped[bool] = mapped_column(default=True)

# UserProfile(Base) — убрать из MVP
```

---

### `models/agent.py`

**Оценка ответственности:** Правильная. Конфигурация и состояние агента.

**Лишнее для MVP:**
- ❌ `SubagentDefinition(Base)` — хранить конфиги типов субагентов в БД — оверинжиниринг. В nano-claude-code типы субагентов — это `AgentDefinition` объекты в коде (или markdown файлы `~/.nano_claude/agents/`), не строки в БД. Для MVP достаточно иметь типы как `Enum` в коде. Убрать из моделей.
- ❌ `current_mood` в `AgentState` — что это значит? Непонятный артефакт. Убрать.

**Пропущено:**
- `last_session_at` в `AgentState` — нужно для KAIROS (когда агент последний раз был активен)

**Конкретные правки:**
```python
class AgentState(Base):
    # УБРАТЬ:
    # current_mood: str  ← убрать, неопределённая семантика
    
    # ОСТАВИТЬ И ДОБАВИТЬ:
    last_active: Mapped[datetime | None]
    last_session_at: Mapped[datetime | None]  # для KAIROS триггеров
    context_summary: Mapped[str | None]
    s3_snapshot_key: Mapped[str | None]

# SubagentDefinition(Base) — убрать полностью из MVP
# Типы субагентов = Enum в коде apps/agent/subagent_router.py
```

---

### `models/session.py`

**Оценка ответственности:** Правильная. Сессии разговора + история сообщений.

**Пропущено из nano-claude-code:**
- В nano-claude-code сессии имеют названия (файлы `session_20260401_143022.json`). У нас нет `title` у `ConversationSession` — нужно добавить для отображения в UI.
- `summary` поле у `Message` — в nano-claude-code при компрессии старые сообщения заменяются на summary-сообщение. Нам нужно поддержать это на уровне модели.

**Лишнее:** Ничего.

**Конкретные правки:**
```python
class ConversationSession(Base):
    # ДОБАВИТЬ:
    title: Mapped[str | None]  # авто-генерируется из первого сообщения, null пока нет

class Message(Base):
    # ДОБАВИТЬ:
    is_summary: Mapped[bool] = mapped_column(default=False)
    # Флаг что это summary-сообщение, заменяющее N предыдущих.
    # При build_context — summary-сообщения получают особую обработку.
```

---

### `models/memory.py`

**Оценка ответственности:** Правильная. Трёхуровневая память с pgvector.

**Сравнение с nano-claude-code:**
- nano-claude-code типы памяти: `user`, `feedback`, `project`, `reference`
- Аркадиус типы: `fact`, `preference`, `event`, `skill`
- Наши типы лучше подходят для агентного продукта (не CLI инструмента). Оставить как есть.
- В nano-claude-code есть `staleness_score` — у нас тоже есть. ✅
- В nano-claude-code память хранится как markdown-файлы, у нас в PostgreSQL — правильно для серверного решения.

**Пропущено:**
- `last_accessed_at` — в nano-claude-code есть freshness tracking через возраст файла. У нас нет timestamp последнего доступа к записи. Нужен для алгоритма eviction (удалять записи которые давно не запрашивались, а не только старые).

**Конкретная правка:**
```python
class MemoryEntry(Base):
    # ДОБАВИТЬ:
    last_accessed_at: Mapped[datetime | None]
    # Обновляется при каждом MemorySearch hit. Используется в evict_stale().
```

---

### `models/tool.py`

**Оценка ответственности:** Правильная. Реестр инструментов + аудит.

**Пропущено из nano-claude-code:**
- nano-claude-code имеет `tool_registry.py` с `register_tool(ToolDef(...))`. У нас `ToolDefinition(Base)` — это хранение в БД. Важно: в nano-claude-code кастомные инструменты регистрируются через плагины (plugin/ package). У нас нет аналога хранения plugin-инструментов отдельно от builtin.
- Стоит добавить флаг `source` к `ToolDefinition`: `builtin | user_defined | plugin`.

**Конкретная правка:**
```python
class ToolDefinition(Base):
    # ИЗМЕНИТЬ:
    # is_builtin: bool  ← заменить на:
    source: Mapped[str]  # "builtin" | "user_defined" | "integration"
    # "integration" — инструменты созданные IntegrationBuilder'ом
```

---

### `models/subagent.py`

**Оценка ответственности:** Правильная. Задачи и результаты субагентов.

**Пропущено из nano-claude-code:**
- nano-claude-code субагенты типов: `general-purpose`, `coder`, `reviewer`, `researcher`, `tester`
- У нас `SubagentType(Enum)` — RESEARCHER, CODER, SCIENTIST.
- Пропущены: `REVIEWER` (ревью кода — важная задача), `TESTER` (запуск тестов).
- `SCIENTIST` — нестандартный тип, нужен нам специфически (анализ данных?). Оставить.

**Конкретная правка:**
```python
class SubagentType(Enum):
    RESEARCHER = "researcher"   # поиск информации
    CODER = "coder"             # написание кода
    REVIEWER = "reviewer"       # ревью кода — ДОБАВИТЬ
    TESTER = "tester"           # тестирование — ДОБАВИТЬ
    SCIENTIST = "scientist"     # анализ данных (наш специфичный тип)
    GENERAL = "general"         # ДОБАВИТЬ: общего назначения
```

---

### `models/billing.py`

**Оценка ответственности:** Правильная. Кредиты, транзакции, инвойсы.

**Пропущено:** Ничего существенного для MVP.

**Лишнее:** Ничего.

---

### `models/channel.py`

**Оценка ответственности:** ЧАСТИЧНО НЕВЕРНАЯ.

**Проблема:**
- `GroupParticipantRegistry(Base)` и `GroupParticipantProfile(Base)` находятся в `models/channel.py` — это неправильно. Это модели групп, не каналов. Нарушает Single Responsibility принцип.

**Конкретная правка:**
- Вынести `GroupParticipantRegistry` и `GroupParticipantProfile` в отдельный файл `models/group.py`.
- В `models/channel.py` оставить только `ChannelBinding`.

```
# БЫЛО:
models/channel.py:
  - ChannelBinding(Base)
  - GroupParticipantRegistry(Base)   ← не сюда
  - GroupParticipantProfile(Base)    ← не сюда

# СТАЛО:
models/channel.py:
  - ChannelBinding(Base)             ← только это

models/group.py (НОВЫЙ):            ← создать
  - GroupParticipantRegistry(Base)
  - GroupParticipantProfile(Base)
```

---

### `models/organization.py`

**Оценка ответственности:** Правильная.

**Пропущено:** Ничего для MVP.

**Вопрос приоритета:** Нужна ли Organization в самом первом MVP (один пользователь = один агент)? Если первый релиз — B2C без командного использования, можно отложить. Оставить на усмотрение Дениса.

---

### `models/agent_secret.py`

**Оценка ответственности:** Правильная. Vault для секретов.

**Пропущено:** Ничего.

**Лишнее:** Ничего.

---

## СВОДНАЯ ТАБЛИЦА ПРАВОК

| Модуль | Тип правки | Описание |
|--------|-----------|----------|
| `core/config.py` | **КРИТИЧНО** | Убрать `LiteLLMSettings`, добавить `AnthropicSettings` + `AdminAPISettings` |
| `infra/llm/provider.py` | **КРИТИЧНО** | Переименовать `LiteLLMProvider` → `AnthropicProvider`, убрать концепт LiteLLM прокси |
| `infra/anthropic_client.py` | **НОВЫЙ** | Создать обёртку над Anthropic SDK с retry, health check |
| `infra/admin_client.py` | **НОВЫЙ** | HTTP-клиент для inter-service вызовов arkadius → arkadius-admin |
| `infra/llm/context_manager.py` | Улучшение | Добавить двухуровневую компрессию: snip + compress (аналог nano-claude-code) |
| `infra/cache/redis.py` | Улучшение | Добавить `acquire_lock` / `release_lock` для distributed locking |
| `core/database.py` | Улучшение | Добавить `check_pgvector_extension()` для startup validation |
| `core/exceptions.py` | Улучшение | Добавить `AnthropicRateLimitError`, `AnthropicOverloadedError` |
| `models/user.py` | MVP-упрощение | Объединить `UserProfile` в `User`, убрать отдельную таблицу |
| `models/agent.py` | MVP-упрощение | Убрать `SubagentDefinition(Base)`, убрать `current_mood` из AgentState |
| `models/agent.py` | Добавление | Добавить `last_session_at` в AgentState |
| `models/session.py` | Добавление | Добавить `title` в ConversationSession, `is_summary` в Message |
| `models/memory.py` | Добавление | Добавить `last_accessed_at` для eviction алгоритма |
| `models/tool.py` | Улучшение | Заменить `is_builtin: bool` на `source: str` (builtin/user_defined/integration) |
| `models/subagent.py` | Добавление | Добавить типы REVIEWER, TESTER, GENERAL в SubagentType |
| `models/channel.py` | Рефакторинг | Вынести GroupParticipant* в отдельный `models/group.py` |

---

## КЛЮЧЕВЫЕ ВЫВОДЫ

### Что в nano-claude-code есть, а у нас нет (релевантное для CORE/INFRA/MODELS):
1. **Двухуровневая компрессия (snip + compact)** — у нас только compact. Snip дешевле, должен идти первым.
2. **Прямой Anthropic SDK** — у нас через LiteLLM прокси (противоречит MVP решению). Исправить.
3. **Health check для зависимостей** — pgvector, Anthropic API connectivity.

### Что у нас есть сверх nano-claude-code (и это правильно для серверного продукта):
- PostgreSQL вместо файлового storage — правильно
- Redis для кэша и pub/sub — правильно  
- pgvector для семантического поиска памяти — правильно
- Tenant isolation на уровне JWT — правильно
- Org-уровень — правильно (у nano-claude-code нет командных функций)

### Что лишнее для MVP (приоритетно убрать):
1. `LiteLLMSettings` и весь концепт LiteLLM прокси в INFRA
2. `SubagentDefinition(Base)` — хранить типы субагентов в коде, не в БД
3. `UserProfile` как отдельная таблица — объединить в User
4. `current_mood` в AgentState — непонятная семантика
