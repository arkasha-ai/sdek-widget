# Ревью модулей AGENT, TOOLS, MEMORY — Аркадиус

> Автор: Аркаша (subagent, роль: архитектор)  
> Дата: 2026-04-04  
> Источник сравнения: nano-claude-code v3.03 (SafeRL-Lab/nano-claude-code)  
> Анализируемые модули: разделы 4–6 `arkadius-modules.md`

---

## Методология

1. Изучен полный README nano-claude-code (v3.03, ~9500 строк Python)
2. Прочитан исходник `agent.py` — реальный agent loop
3. Прочитан `tool_registry.py` — реальный паттерн регистрации
4. Прочитан `memory/store.py` — реальное хранилище памяти
5. Прочитан `multi_agent/subagent.py` — реальный SubAgentManager
6. Каждый модуль оценён по 4 критериям: правильность / пропущенное / лишнее / улучшения

---

## Модуль 4: APPS/AGENT — Runtime агентов

### 4.1 Оценка правильности

**agent_loop.py — ХОРОШАЯ ОСНОВА, но не полная**

nano-claude-code реализует loop так:
```python
def run(user_message, state, config, system_prompt, depth=0, cancel_check=None):
    state.messages.append({"role": "user", ...})
    config = {**config, "_depth": depth, "_system_prompt": system_prompt}
    while True:
        if cancel_check and cancel_check(): return
        maybe_compact(state, config)          # ← ПЕРЕД каждым вызовом LLM
        for event in stream(...):
            yield TextChunk | ThinkingChunk | AssistantTurn
        state.messages.append({"role": "assistant", ...})
        yield TurnDone(in_tokens, out_tokens)
        if not tool_calls: break             # ← выход без инструментов
        for tc in tool_calls:
            permitted = _check_permission(tc, config)  # ← permission ВНУТРИ loop
            result = execute_tool(tc, ...)
            state.messages.append({"role": "tool", ...})
    # → LOOP (до break)
```

Arkadius определяет `AgentLoop` с `run()`, `_process_tool_call()`, `_should_continue()`. Структура правильная. Но:
- `_should_continue()` — в nano это просто `if not assistant_turn.tool_calls: break`. Отдельный метод избыточен.
- `AgentEvent` union (TextDelta | ToolCall | ToolResult | Done | Error) — **хорошо**, полностью покрывает события.
- Нет параметра `depth` и `cancel_check` — это критическое упущение.

**context_builder.py — ПРАВИЛЬНО**  
Аналог `context.py` в nano-claude-code. Собирает CLAUDE.md + git status + memory + system prompt. В Аркадиусе: system_prompt + relevant_memories + session_history. Принципиально верно, хотя в nano каждый тип контекста загружается в фиксированном порядке.

**subagent_router.py + subagent_pool.py — ПРАВИЛЬНО ПО КОНЦЕПЦИИ, НО**

nano-claude-code использует `SubAgentManager` с `ThreadPoolExecutor(max_workers=5)`. Он держит `_by_name: Dict[str, str]` для адресации агентов по имени. Аркадиус вместо этого использует Celery tasks — это **архитектурное расхождение**. Celery правильный выбор для SaaS (персистентность, retry, мониторинг), но теряется `SendMessage`/`_inbox` паттерн.

**dream.py — УНИКАЛЬНО ДЛЯ АРКАДИУСА** (в nano нет autoDream)  
Концепция взята из OpenClaw. В nano-claude-code никакой фоновой рефлексии нет. Это ваша дифференциация — правильно держать, но нужны три чёткие фазы (см. улучшения).

**kairos.py — КРИТИЧЕСКАЯ ПРОБЛЕМА**  
В задаче указано "KAIROS — tick-промпты, 15 сек лимит". В текущем модуле этого лимита **нет**. Описан просто Celery beat без бюджета времени. Это важно: если tick занимает >15 секунд — система становится нереспонсивной.

**persona.py — ДУБЛИРОВАНИЕ**  
Функции `PersonaBuilder` полностью перекрываются `ContextBuilder`. В nano-claude-code нет отдельного персона-билдера — системный промпт строится в `context.py` одним методом.

### 4.2 Пропущенное из nano-claude-code

| Что пропущено | Где в nano | Критичность |
|--------------|-----------|-------------|
| `cancel_check: Callable[[], bool]` в agent loop | `agent.py:run()` | Высокая — без этого нельзя прервать зависший loop |
| `depth: int` параметр + `MAX_DEPTH = 3` | `SubAgentManager.max_depth` | Высокая — защита от бесконечной рекурсии субагентов |
| Worktree isolation для субагентов | `subagent.py:_create_worktree()` | Средняя — полезно для Coder-агента |
| `SendMessage` паттерн (inbox queue) | `SubAgentTask._inbox: Queue` | Средняя — общение с фоновым агентом без polling |
| Tick budget (15 сек) в KAIROS | Не в nano, но концепция важна | Высокая — из Claude Code leak |
| Tool output truncation (32000 chars) | `tool_registry.py:execute_tool()` | Средняя — без обрезки LLM захлёбывается |
| `maybe_compact` ПЕРЕД каждым LLM-вызовом | `agent.py:maybe_compact()` | Высокая — компрессия должна быть превентивной |

### 4.3 Лишнее для MVP

| Модуль | Почему лишний для MVP |
|--------|----------------------|
| `subagent_pool.py` | Дублирует `subagent_router.py`. Для MVP достаточно Celery status + revoke |
| `persona.py` | Полностью поглощается `context_builder.py` |
| `dream.py` + `kairos.py` | autoDream — мощная фича, но не нужна для запуска MVP |
| `src/org/manager.py` + `src/org/memory.py` | Орг-уровень — v2 фича |
| `src/vault/manager.py` + `src/vault/encryption.py` | Vault нужен, но для MVP достаточно encrypted field в `AgentSecret` без полного vault API |
| `src/nodes/` (все 3 файла) | Ноды — отдельная большая фича, не для MVP |
| Browser pool (`infra/browser_pool.py` и др.) | Явно v2+ |
| `IntegrationBuilder` | Явно v2+ |

### 4.4 Конкретные улучшения

**1. Добавить `cancel_check` и `depth` в AgentLoop:**
```python
async def run(
    self,
    session_id: str,
    user_message: str,
    depth: int = 0,
    cancel_check: Callable[[], bool] | None = None,
) -> AsyncGenerator[AgentEvent, None]:
    MAX_DEPTH = 3
    if depth >= MAX_DEPTH:
        yield Error(message=f"Max subagent depth ({MAX_DEPTH}) exceeded")
        return
    ...
    while True:
        if cancel_check and cancel_check():
            yield Error(message="Cancelled")
            return
        # compact BEFORE LLM call
        await self.context_manager.maybe_compact(session_id)
        ...
```

**2. KAIROS — добавить tick budget:**
```python
TICK_BUDGET_SECONDS = 15

class KairosService:
    async def run_tick_with_budget(self, action: AgentAction) -> bool:
        try:
            await asyncio.wait_for(
                self._execute_action(action),
                timeout=TICK_BUDGET_SECONDS
            )
            return True
        except asyncio.TimeoutError:
            logger.warning(f"KAIROS: action {action} exceeded {TICK_BUDGET_SECONDS}s budget")
            return False
```

**3. autoDream — три явные фазы:**
```python
class DreamService:
    async def reflect_on_sessions(self, agent_id, last_n_sessions):
        # Фаза 1: COLLECT — агрегировать сырые сессии
        raw = await self._collect_session_data(agent_id, last_n_sessions)
        # Фаза 2: REFLECT — LLM анализирует и извлекает факты
        insights = await self._llm_reflect(raw)  
        # Фаза 3: PLAN — что сделать proactive
        plan = await self._llm_plan(insights, agent_id)
        return DreamInsights(new_memories=insights.facts, planning_notes=plan)
```

**4. Убрать `persona.py`, перенести логику в `context_builder.py`:**
```python
class ContextBuilder:
    async def build(self, session_id, new_message) -> BuiltContext:
        agent = await self._get_agent(session_id)
        system = self._build_system_prompt(agent)  # было в persona.py
        memories = await self._fetch_relevant_memories(agent, new_message)
        messages = await self._get_session_history(session_id)
        return BuiltContext(system_prompt=system, messages=messages, tools_schema=...)
```

---

## Модуль 5: APPS/TOOLS — Инструменты

### 5.1 Оценка правильности

**tools/registry.py — КОНЦЕПТУАЛЬНО ВЕРНО, ПАТТЕРН НЕТОЧНЫЙ**

Реальный nano-claude-code НЕ использует декоратор `@register_tool`. Он использует **явную регистрацию через ToolDef**:

```python
# nano-claude-code (реальный код)
@dataclass
class ToolDef:
    name: str
    schema: Dict[str, Any]
    func: Callable[[Dict, Dict], str]
    read_only: bool = False          # ← ОТСУТСТВУЕТ в Аркадиусе
    concurrent_safe: bool = False    # ← ОТСУТСТВУЕТ в Аркадиусе

register_tool(ToolDef(name="Read", schema=READ_SCHEMA, func=read_file, read_only=True))
```

В Аркадиусе описан `@register_tool(name, description, schema)` — это валидный Python-паттерн, но **не из nano-claude-code**. Это важно потому что флаги `read_only` и `concurrent_safe` используются для автоматических решений о permission и параллельности.

**tools/base.py — ХОРОШО, НО БОГАЧЕ ЧЕМ НУЖНО**  
`ToolContext(user_id, agent_id, session_id, org_id, sandbox_info)` — правильно для SaaS. В nano просто `config: dict`. Аркадиус добавляет типизацию.

**tools/permission.py — ИЗЛИШНЯЯ АБСТРАКЦИЯ**  
В nano-claude-code permission check — это 10 строк ВНУТРИ agent loop (`_check_permission(tc, config)`). В Аркадиусе это отдельный сервис с `request_user_approval()`. Это правильно для web-продукта (нужен async approval через WebSocket), но `PermissionLevel.AUTO` должен опираться на `read_only` флаг из ToolDef.

**tools/builtin/ — ПОЧТИ ПОЛНЫЙ НАБОР**  
nano-claude-code имеет 21 инструмент (включая MCP + plugin). Аркадиус покрывает базовый набор. Что есть в nano но нет у Аркадиуса — см. 5.2.

### 5.2 Пропущенное из nano-claude-code

| Инструмент / концепция | nano-claude-code | Важность для MVP |
|-----------------------|-----------------|-----------------|
| `read_only` + `concurrent_safe` флаги в ToolDef | `tool_registry.py:ToolDef` | Высокая — нужны для auto-permission |
| Output truncation (32000 chars) при execute | `tool_registry.py:execute_tool(max_output=32000)` | Высокая — без этого LLM захлёбывается |
| `TaskCreate / TaskUpdate / TaskGet / TaskList` | `task/` package | Средняя — полезно для multi-step задач |
| MCP tool auto-discovery | `mcp/` package | Низкая — v2 |
| Plugin tools | `plugin/` package | Низкая — v2 |
| `Skill` / `SkillList` tools | `skill/tools.py` | Низкая — v2 |
| `SendMessage` / `CheckAgentResult` / `ListAgentTasks` | `multi_agent/tools.py` | Средняя — для субагентов |

**Критическое:** В текущей спецификации `execute_tool` в `registry.py` не упоминает обрезку вывода. Это ДОЛЖНО быть там.

### 5.3 Лишнее для MVP

| Компонент | Комментарий |
|-----------|-------------|
| `MemoryListTool` — отдельный инструмент | Можно заменить параметром `action=list` в `MemorySearchTool` |
| `FileGlobTool` + `FileGrepTool` как отдельные файлы | Можно объединить в `file_tools.py` |
| Сложная `PermissionService.request_user_approval()` | Для MVP достаточно AUTO/DENY. Manual — v2 |

### 5.4 Конкретные улучшения

**1. Добавить read_only и concurrent_safe в BaseTool:**
```python
class BaseTool(ABC):
    read_only: bool = False         # Не изменяет состояние → auto-approve
    concurrent_safe: bool = False   # Можно запускать параллельно
    
    @abstractmethod
    async def execute(self, input: dict, context: ToolContext) -> ToolResult: ...
```

**2. Output truncation в registry.execute_tool():**
```python
MAX_TOOL_OUTPUT = 32_000  # символов

async def execute_tool(self, name, input, context) -> ToolResult:
    tool = self._tools.get(name)
    result = await tool.execute(input, context)
    if result.output and len(result.output) > MAX_TOOL_OUTPUT:
        half = MAX_TOOL_OUTPUT // 2
        quarter = MAX_TOOL_OUTPUT // 4
        truncated = len(result.output) - half - quarter
        result.output = (
            result.output[:half]
            + f"\n[... {truncated} символов обрезано ...]\n"
            + result.output[-quarter:]
        )
    return result
```

**3. Permission на основе read_only флага:**
```python
# В permission.py
def check_permission(self, agent_id, tool_name, input) -> PermissionResult:
    tool = registry.get_tool(tool_name)
    if tool and tool.read_only:
        return PermissionResult(allowed=True, requires_approval=False)
    # иначе проверяем настройки агента
    ...
```

**4. Добавить `TaskCreate/TaskUpdate/TaskGet` для MVP (минимальная версия):**
Это сильно улучшает multi-step задачи — агент может отслеживать прогресс. Не нужна полная система с dependency edges, достаточно `pending → in_progress → done/failed` + хранение в Redis с TTL 24h.

---

## Модуль 6: APPS/MEMORY — Управление памятью

### 6.1 Оценка правильности

**Принципиальное расхождение в storage backend:**  
nano-claude-code хранит память в **markdown файлах** (user: `~/.nano_claude/memory/`, project: `.nano_claude/memory/`). Аркадиус хранит в **PostgreSQL + pgvector**. 

Для SaaS Аркадиуса PostgreSQL — **правильное решение**. Масштабируется, multi-tenant, можно делать SQL-фильтрацию. Но из nano нужно перенять ключевой паттерн: **MEMORY.md-индекс инжектится в каждый системный промпт**.

Это критично: в nano `context.py` всегда делает:
```python
memory_index = get_index_content("user") + get_index_content("project")
# → инжектируется в system_prompt как раздел "## Memory"
```

У Аркадиуса `context_builder.py` делает `_fetch_relevant_memories()` — это **семантический поиск**, а не индекс. Проблема: агент не знает ЧТО вообще есть в памяти, он видит только релевантное запросу. Нужны оба: краткий индекс (как в nano) + семантический поиск для деталей.

**memory_manager.py — ПРАВИЛЬНО**  
dual-scope (personal|org|project) — хорошо. Типы: fact, preference, event, skill — хорошо. Но пропущен **тип "feedback"** (как агент должен себя вести) — именно он обеспечивает долгосрочную персонализацию.

**memory_search.py — ЛУЧШЕ ЧЕМ В nano**  
pgvector cosine similarity > keyword search. Аркадиус правильно идёт дальше nano.

**compressor.py — НЕПОЛНАЯ РЕАЛИЗАЦИЯ**  
nano-claude-code имеет **два слоя компрессии**:
1. **Snip** — быстро обрезает старые tool outputs после N turns. Нет API-вызова.
2. **Auto-compact** — LLM summarization когда использование токенов >70% от лимита.

В Аркадиусе `compressor.py` реализует только второй слой (summarize). Первый (snip) отсутствует. Это неэффективно — тратим LLM токены на summarization когда можно просто обрезать старые tool results.

**s3_snapshot.py — ПРАВИЛЬНО, НО ДЛЯ MVP ЛИШНЕЕ**  
Снапшоты состояния агента в S3. В nano-claude-code нет ничего подобного (только session save/load в JSON). Для SaaS полезно, но для MVP — преждевременно.

### 6.2 Пропущенное из nano-claude-code

| Что пропущено | Где в nano | Критичность для MVP |
|--------------|-----------|---------------------|
| Тип памяти `feedback` (как агент должен себя вести) | `memory/types.py: MEMORY_TYPES["feedback"]` | Высокая — без этого персонализация невозможна |
| MEMORY.md-стиль краткого индекса для system prompt | `memory/context.py: get_memory_context()` | Высокая — агент должен видеть обзор памяти |
| Лимит индекса (200 строк / 25KB) | `memory/store.py: MAX_INDEX_LINES=200, MAX_INDEX_BYTES=25000` | Средняя — без лимита context переполняется |
| Slicing старых tool results (snip-слой) | `compaction.py: snip layer` | Высокая — критично для длинных сессий |
| Trigger auto-compact при >70% context | `compaction.py: maybe_compact()` | Высокая — сейчас непонятно когда запускается |
| Staleness warnings для пользователя (не только score) | `memory/scan.py: freshness helpers` | Низкая — UX улучшение |
| AI-ranked search (`use_ai=True`) | `memory/context.py` | Низкая — pgvector достаточно для MVP |

### 6.3 Лишнее для MVP

| Модуль | Комментарий |
|--------|-------------|
| `s3_snapshot.py` | Ценно, но PostgreSQL + S3 для снапшотов — v2. Для MVP достаточно DB |
| `scope=org` в memory_manager | Орг-память — v2 фича. Начать с personal + project |
| `scope=project` в memory_manager | Полезно, но для MVP достаточно personal |
| `evict_stale()` логика | Для MVP достаточно `staleness_score`. Полноценный eviction — v2 |

### 6.4 Конкретные улучшения

**1. Добавить тип памяти `feedback`:**
```python
# В models/memory.py — расширить ENUM
class MemoryType(str, Enum):
    FACT = "fact"           # факт о пользователе/контексте
    PREFERENCE = "preference"  # предпочтения
    EVENT = "event"         # произошедшее событие
    SKILL = "skill"         # навык агента
    FEEDBACK = "feedback"   # ← ДОБАВИТЬ: как агент должен себя вести
```

**2. Memory index summary в каждый system prompt:**
```python
# В context_builder.py
async def build(self, session_id, new_message) -> BuiltContext:
    # 1. Краткий индекс (аналог MEMORY.md)
    memory_index = await self._build_memory_index(agent_id)
    # 2. Релевантные детали через pgvector
    relevant = await memory_search.search(agent_id, new_message, limit=5)
    
    system = f"""
{base_system_prompt}

## Память (индекс)
{memory_index}  # краткий список: имя + тип + дата

## Релевантные воспоминания
{self._format_memories(relevant)}
"""
```

**3. Два слоя компрессии в compressor.py:**
```python
class ConversationCompressor:
    COMPACT_AT_RATIO = 0.70      # запускать LLM summarization при 70%
    SNIP_TOOL_RESULTS_AFTER = 5  # обрезать tool results старше 5 turns
    
    async def maybe_compact(self, session_id: str, current_tokens: int, max_tokens: int):
        ratio = current_tokens / max_tokens
        
        if ratio > self.COMPACT_AT_RATIO:
            # Слой 2: LLM summarization (дорого, но информативно)
            await self._auto_compact(session_id)
        elif ratio > 0.50:
            # Слой 1: Snip — просто обрезать старые tool results (бесплатно)
            await self._snip_old_tool_results(session_id)
    
    async def _snip_old_tool_results(self, session_id: str):
        """Обрезать content у tool messages старше N turns."""
        messages = await self._get_messages(session_id)
        cutoff = len(messages) - (self.SNIP_TOOL_RESULTS_AFTER * 2)
        for i, msg in enumerate(messages):
            if i < cutoff and msg.role == "tool" and len(msg.content) > 500:
                msg.content = msg.content[:200] + "\n[обрезано — старый результат инструмента]"
```

**4. Limit на инжектируемый memory index:**
```python
# В memory_search.py или context_builder.py
MAX_MEMORY_INDEX_LINES = 200
MAX_MEMORY_INDEX_BYTES = 25_000

async def _build_memory_index(self, agent_id: str) -> str:
    entries = await memory_manager.list(agent_id, scope="personal", limit=500)
    lines = [
        f"- [{e.type}] {e.content[:80]}... (создано {e.created_at.date()})"
        for e in entries
    ]
    index = "\n".join(lines)
    # Обрезать по лимиту
    if len(lines) > MAX_MEMORY_INDEX_LINES:
        lines = lines[:MAX_MEMORY_INDEX_LINES]
        index = "\n".join(lines) + f"\n... [и ещё {len(entries) - MAX_MEMORY_INDEX_LINES} записей]"
    if len(index.encode()) > MAX_MEMORY_INDEX_BYTES:
        index = index[:MAX_MEMORY_INDEX_BYTES] + "\n[обрезано]"
    return index
```

---

## Сводная матрица: Критичные проблемы vs MVP

### 🔴 Критичные (нужно исправить до MVP)

| Проблема | Модуль | Действие |
|---------|--------|---------|
| Нет `cancel_check` в agent loop | agent_loop.py | Добавить параметр + проверку в цикле |
| Нет `depth` + MAX_DEPTH | agent_loop.py + subagent_router.py | Добавить, передавать при spawn |
| `maybe_compact` не описан перед LLM-вызовом | context_builder.py / agent_loop.py | Вызывать compressor ПЕРЕД каждым stream() |
| Нет output truncation в registry | tools/registry.py | Добавить MAX_TOOL_OUTPUT = 32000 |
| Нет snip-слоя компрессии | memory/compressor.py | Добавить _snip_old_tool_results() |
| KAIROS без tick budget | agent/kairos.py | Добавить TICK_BUDGET_SECONDS = 15 |
| Нет `read_only` флага на инструментах | tools/base.py + permission.py | Добавить, использовать в permission check |
| Нет типа памяти `feedback` | models/memory.py | Добавить в ENUM |

### 🟡 Важные (желательно до MVP)

| Проблема | Модуль | Действие |
|---------|--------|---------|
| `persona.py` дублирует `context_builder.py` | agent/persona.py | Объединить |
| Memory index не инжектируется в system prompt | context_builder.py | Добавить краткий индекс + лимит 200 строк/25KB |
| Нет лимита на memory index в system prompt | context_builder.py | MAX_INDEX_LINES=200 |
| `subagent_pool.py` дублирует `subagent_router.py` | Оба файла | Объединить |

### 🟢 Можно отложить до v2

| Фича | Модуль |
|-----|--------|
| autoDream (dream.py + kairos.py) | agent/ |
| Org-уровень (src/org/) | agent/src/org/ |
| Vault (src/vault/) | agent/src/vault/ |
| Ноды (src/nodes/) | agent/src/nodes/ |
| Browser pool | infra/ (arkadius-admin) |
| IntegrationBuilder | agent/src/integrations/ |
| S3 snapshots | memory/s3_snapshot.py |
| Multi-scope memory (org/project) | memory_manager.py |
| Task management tools | tools/builtin/ |
| MCP integration | — |

---

## Что Аркадиус делает ЛУЧШЕ, чем nano-claude-code

(Это не критика — это преимущества для SaaS-продукта)

1. **PostgreSQL + pgvector** vs файлы — масштабируется, multi-tenant, semantic search
2. **ToolContext** (user_id, agent_id, session_id, org_id) vs `config: dict` — типизированный контекст
3. **Celery** для субагентов vs ThreadPoolExecutor — персистентность, retry, monitoring
4. **Billing** (CreditAccount, UsageTracker) — нет в nano
5. **Multi-channel** (Telegram, VK, MAX, Web) — нет в nano
6. **Docker sandbox** изоляция на пользователя — нет в nano (там просто Bash)
7. **Двухуровневые группы** (registry + profile) — нет в nano
8. **autoDream** как Celery task — концептуальная инновация над nano

---

## Итог по каждому модулю

| Модуль | Оценка | Главная проблема |
|--------|--------|-----------------|
| `agent_loop.py` | 7/10 | Нет cancel_check, depth, compaction trigger |
| `context_builder.py` | 7/10 | Нет memory index summary (только semantic search) |
| `dream.py` | 6/10 | Нет явных 3 фаз (collect/reflect/plan) |
| `kairos.py` | 5/10 | Нет tick budget (15 сек лимит) |
| `subagent_router.py` | 7/10 | Нет worktree isolation, SendMessage inbox |
| `subagent_pool.py` | 5/10 | Дублирование router.py — объединить |
| `persona.py` | 4/10 | Дублирование context_builder.py — удалить |
| `tools/registry.py` | 7/10 | Нет read_only/concurrent_safe, нет output truncation |
| `tools/base.py` | 8/10 | ToolContext хорош, но нужны флаги |
| `tools/permission.py` | 6/10 | Не использует read_only флаг |
| `tools/builtin/` (все) | 8/10 | Полный набор, но нет Task tools |
| `memory_manager.py` | 7/10 | Нет типа feedback |
| `memory_search.py` | 9/10 | pgvector > nano keyword search |
| `compressor.py` | 5/10 | Нет snip-слоя, нет 70% trigger |
| `s3_snapshot.py` | 7/10 | Правильно, но для MVP преждевременно |
