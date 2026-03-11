# Техническое Задание: BrainNet v0.1 (Прототип)

> **Версия документа:** 1.1 (локальные модели + векторный протокол)  
> **Дата:** 2026-03-10  
> **Статус:** Черновик  

---

## Содержание

1. [Цель и область применения](#1-цель-и-область-применения)
2. [Архитектура системы](#2-архитектура-системы)
3. [Спецификация компонентов](#3-спецификация-компонентов)
4. [Протоколы взаимодействия](#4-протоколы-взаимодействия)
5. [Стек технологий](#5-стек-технологий)
6. [Структура проекта](#6-структура-проекта)
7. [Этапы реализации](#7-этапы-реализации)
8. [Метрики и тестирование](#8-метрики-и-тестирование)
9. [Открытые вопросы и риски](#9-открытые-вопросы-и-риски)

---

## 1. Цель и область применения

### 1.1. Проблема

Современные AI-агенты строятся как монолиты: одна модель принимает решения, формулирует ответ и выполняет действия. У этого подхода три фундаментальных дефекта:

1. **Отсутствие разделения "что"/"как".** Модель, которая решает ЧТО делать, одновременно знает КАК это делать на уровне tool calls. Результат: агент ROME (Alibaba) во время RL-обучения самостоятельно начал майнить криптовалюту и открыл SSH-туннель — потому что ничто архитектурно не мешало исполнительному слою порождать собственные цели.

2. **Единый reward signal.** Одна функция вознаграждения для всех аспектов поведения приводит к reward hacking — агент оптимизирует прокси-метрику, а не реальную цель.

3. **Отсутствие иерархии скоростей.** Каждый запрос проходит полный цикл inference, даже если ответ уже известен из предыдущего опыта. Нет аналога рефлексов, нет градации по сложности.

### 1.2. Решение

BrainNet — мультиагентная архитектура, вдохновлённая принципами работы человеческого мозга:

- **Иерархия скоростей** (рефлексы → детектор → коллегия → ответ) — как кортикальные уровни обработки
- **Gossip-координация** вместо центрального маршрутизатора — как нейронные ансамбли
- **Архитектурное разделение "что"/"как"** — моторный слой не может порождать цели
- **ConflictMonitor** — аналог передней поясной коры, разрешающей конфликт быстрых и медленных путей
- **Emergent specialization** — модели коллегии сами находят специализацию через reward за уникальность

### 1.3. Область применения прототипа

Прототип BrainNet v0.1 — **AI-ассистент общего назначения** с текстовым интерфейсом:

- Принимает текстовые запросы пользователя
- Обрабатывает через иерархию уровней (L0–L3)
- Выполняет действия через набор tools (файловая система, web-поиск, калькулятор)
- Возвращает текстовый ответ

**Не входит в прототип:** мультимодальность, обучение в реальном времени (кроме Importance Scorer), распределённая работа на нескольких серверах.

### 1.4. Целевые характеристики прототипа

| Метрика | Значение |
|---------|----------|
| Латентность L0 (cache hit) | < 50 мс |
| Латентность L1 (fast detector) | < 200 мс |
| Латентность L2 (reasoning) | < 5 с |
| Латентность end-to-end (L3) | < 8 с |
| Параллельных запросов | до 10 |
| Размер рабочей памяти | до 100 элементов на задачу |
| Узлов в gossip-сети | 6–10 |

---

## 2. Архитектура системы

### 2.1. Схема компонентов

```
                         ┌─────────────────────────────────────────────┐
                         │              USER INPUT                     │
                         └────────────────────┬────────────────────────┘
                                              │
                                              ▼
                         ┌────────────────────────────────────────────┐
                         │            DISPATCHER (asyncio)            │
                         │  - принимает запрос                        │
                         │  - запускает pipeline L0 → L1 → L2 → L3   │
                         │  - управляет early exit                    │
                         └──────┬─────────┬──────────┬────────────────┘
                                │         │          │
                    ┌───────────▼──┐  ┌───▼────┐  ┌──▼──────────────────┐
                    │  CacheLayer  │  │  Fast   │  │  ReasoningCollegium │
                    │    (L0)      │  │Detector │  │       (L2)          │
                    │              │  │  (L1)   │  │                     │
                    │ ┌──────────┐ │  │ Qwen    │  │ ┌───┐ ┌───┐ ┌───┐ │
                    │ │L1: exact │ │  │ 2.5-0.5B│  │ │M_a│ │M_b│ │M_c│ │
                    │ │L2: semant│ │  │ (local) │  │ └─┬─┘ └─┬─┘ └─┬─┘ │
                    │ │L3: patter│ │  └────┬────┘  │   └──┬──┘──┬──┘   │
                    │ └──────────┘ │       │       │      ▼     ▼      │
                    └──────┬───────┘       │       │  ┌────────────┐   │
                           │               │       │  │ Aggregator │   │
                           │               │       │  └─────┬──────┘   │
                           ▼               ▼       └────────┼──────────┘
                    ┌──────────────────────────────────────┐ │
                    │         ConflictMonitor               │ │
                    │  - fast vs slow conflict detection    │ │
                    │  - stop-signal (SSRT: 150–250мс)     │ │
                    └──────────────┬───────────────────────┘ │
                                   │                         │
                                   ▼                         ▼
                         ┌────────────────────────────────────────────┐
                         │              FinalNode (L3)                │
                         │   Qwen2.5-0.5B (локально)                 │
                         │   формулирует ответ из агрегации L2       │
                         └────────────────────┬───────────────────────┘
                                              │
                    ┌─────────────────────────┼──────────────────────┐
                    │                         ▼                      │
                    │    ┌──────────────────────────────────┐        │
                    │    │         MotorNode                │        │
                    │    │  - Action Codebook (10d)         │        │
                    │    │  - nearest neighbor lookup       │        │
                    │    │  - temporal summation            │        │
                    │    │  - обратимое/необратимое         │        │
                    │    └──────────────┬───────────────────┘        │
                    │                   │                             │
                    │                   ▼                             │
                    │    ┌──────────────────────────────────┐        │
                    │    │         TOOL EXECUTION           │        │
                    │    │  file_read, web_search, calc...  │        │
                    │    └──────────────────────────────────┘        │
                    └────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                    GOSSIP LAYER (фоновый)                       │
    │                                                                 │
    │  Все узлы (L1, M_a, M_b, M_c, FinalNode, MotorNode)           │
    │  соединены gossip-протоколом:                                   │
    │  - broadcast входного сигнала                                   │
    │  - Importance Scorer на каждом узле                             │
    │  - синхронизация при совпадении оценок                          │
    └─────────────────────────────────────────────────────────────────┘

    ┌─────────────────────────────────────────────────────────────────┐
    │                    WORKING MEMORY (Redis)                       │
    │                                                                 │
    │  - Общий буфер задачи (task context)                           │
    │  - Промежуточные результаты узлов                               │
    │  - Стирается после завершения задачи                            │
    └─────────────────────────────────────────────────────────────────┘
```

### 2.2. Потоки данных

**Основной поток (happy path — cache miss):**

```
User input
  → Dispatcher: создаёт TaskContext в WorkingMemory
  → L0 CacheLayer: проверяет 3 уровня кеша
     [MISS] → L1 FastDetector
  → L1 FastDetector: классифицирует запрос (локальная модель)
     → определяет: нужен L2 или достаточно простого ответа
     [COMPLEX] → L2 ReasoningCollegium
  → L2: 3 модели параллельно
     → каждая пишет свой ответ в WorkingMemory
     → Aggregator: кластеризация embeddings, выявление консенсуса
  → ConflictMonitor: проверяет конфликт fast/slow
     [NO CONFLICT] → FinalNode
  → L3 FinalNode: формулирует финальный ответ
     → если нужно действие → MotorNode
  → MotorNode: nearest neighbor в Action Codebook
     → если dist < θ и обратимое → выполнить
     → если необратимое → задержка D, ожидание подтверждения
  → User output
```

**Быстрый поток (cache hit):**

```
User input → Dispatcher → L0 CacheLayer
  [L1 HIT — exact] → подставить параметры из WorkingMemory → User output (~1мс)
  [L2 HIT — semantic] → подставить параметры → User output (~10мс)
  [L3 HIT — pattern] → подставить параметры → User output (~50мс)
```

**Gossip-поток (параллельный):**

```
User input → broadcast всем узлам
  → каждый узел: ImportanceScorer(embedding) → score ∈ [0, 1]
  → передать соседям: (embedding, score)
  → если |score_i - score_j| < δ → синхронизация
  → синхронизированные узлы обрабатывают совместно
```

### 2.3. Описание компонентов (обзор)

| Компонент | Уровень | Роль | Латентность |
|-----------|---------|------|-------------|
| CacheLayer | L0 | Рефлексы: мгновенный ответ из кеша | 1–50 мс |
| FastDetector | L1 | Быстрая классификация и маршрутизация | 50–200 мс |
| ReasoningCollegium | L2 | Глубокое рассуждение (3 модели) | 500 мс – 5 с |
| Aggregator | L2 (часть) | Кластеризация ответов коллегии | 50–100 мс |
| FinalNode | L3 | Формулировка ответа из агрегации | 200–500 мс |
| MotorNode | — | Трансляция абстрактной команды в tool call | 10–50 мс |
| GossipProtocol | Фон | Координация между узлами | постоянно |
| WorkingMemory | Инфра | Общий буфер данных задачи | <1 мс |
| ConflictMonitor | Фон | Детекция и разрешение конфликтов fast/slow | ~200 мс |
| ImportanceScorer | На узле | Оценка важности входного сигнала для узла | 5–20 мс |

---

## 3. Спецификация компонентов

### 3.1. CacheLayer (L0)

**Назначение:** Три уровня кеша для мгновенного ответа без обращения к моделям.

**Входные данные:**

```python
@dataclass
class CacheQuery:
    text: str                    # Текст запроса пользователя
    embedding: list[float]       # Embedding запроса (768d, Qwen3-Embedding-0.6B)
    task_context_id: str         # ID текущей задачи в WorkingMemory
```

**Выходные данные:**

```python
@dataclass
class CacheResult:
    hit: bool                    # Попадание в кеш
    level: int | None            # 1, 2 или 3 — уровень попадания (None если miss)
    response_template: str | None # Шаблон ответа (если hit)
    action_pattern: ActionPattern | None  # Паттерн действия (если L3 hit)
    confidence: float            # Уверенность (1.0 для exact, similarity для semantic)
```

**Алгоритм работы:**

1. **L1 — Exact Cache (Redis, ~1 мс):**
   - Ключ: SHA-256 от нормализованного текста (lowercase, strip, убрать пунктуацию)
   - Значение: JSON с шаблоном ответа и TTL
   - TTL: 3600 с (1 час) для фактических ответов, 86400 с (24 часа) для tool-паттернов
   - Hit → вернуть немедленно

2. **L2 — Semantic Cache (~10 мс):**
   - Хранилище: Redis с модулем RedisSearch (HNSW индекс по embeddings)
   - Embedding запроса сравнивается с сохранёнными через cosine similarity
   - Порог: `similarity > 0.92` — hit
   - Зона неуверенности: `0.85 < similarity < 0.92` — передать L1 для верификации
   - `similarity < 0.85` — miss
   - Максимум записей: 10 000 (LRU eviction по score)

3. **L3 — Pattern Cache (~50 мс):**
   - Кешируем **паттерн действия**, не конкретные параметры
   - Паттерн: `(tool_name, param_type_signature)` — например `("file_read", "path:string")`
   - Конкретные значения (путь к файлу, URL) берутся из WorkingMemory
   - Хранилище: Redis hash, ключ — embedding кластера паттерна
   - Порог similarity для паттернов: `> 0.88`

```python
@dataclass
class ActionPattern:
    tool: str                     # Имя инструмента
    param_types: dict[str, str]   # {param_name: type} — без конкретных значений
    param_sources: dict[str, str] # {param_name: "working_memory.key"} — откуда брать
```

**Запись в кеш:** Происходит после успешного выполнения полного pipeline (L0 miss → L1 → L2 → L3 → ответ). Записываются все три уровня одновременно.

**Граничные случаи:**

- Redis недоступен → пропустить L0 полностью, перейти к L1 (graceful degradation)
- Embedding сервис недоступен → L2 и L3 недоступны, работает только L1 exact
- Конфликт записи (параллельные запросы) → last-write-wins (для кеша приемлемо)
- Кеш-отравление (некорректный кешированный ответ) → TTL + возможность ручной инвалидации по префиксу

---

### 3.2. FastDetector (L1)

**Назначение:** Быстрая классификация запроса локальной моделью. Определяет: можно ли ответить простой генерацией или нужен L2 (reasoning коллегия).

**Модель:** Qwen2.5-0.5B, запущена локально на RTX 4090 через vLLM. ~0.5 GB VRAM. Минимальная латентность благодаря малому размеру модели.

**Входные данные:**

```python
@dataclass
class DetectorInput:
    text: str                     # Текст запроса
    embedding: list[float]        # Embedding запроса
    task_context_id: str          # ID контекста
    working_memory_slice: dict    # Релевантный срез рабочей памяти
```

**Выходные данные:**

```python
@dataclass
class DetectorOutput:
    route: Literal["simple", "complex", "clarify", "refuse"]
    confidence: float             # 0.0–1.0
    simple_response: str | None   # Если route == "simple" — сгенерированный ответ
    action_hint: str | None       # Подсказка для L2: "needs_tool", "factual", "creative"
    estimated_complexity: int     # 1–5 (для логирования и метрик)
```

**Алгоритм работы:**

1. Сформировать промпт для классификации (без system prompt):
   ```
   Classify this user request. Output JSON only.
   Request: {text}
   Context: {working_memory_slice summary, max 200 tokens}
   ```
2. Запустить inference локальной модели (max_tokens=256, temperature=0.1)
3. Парсить JSON-ответ
4. Решение по маршрутизации:
   - `confidence > 0.8` и route == "simple" → сгенерировать ответ на L1, перейти к L3 (пропуск L2)
   - `confidence > 0.6` и route == "complex" → передать L2
   - `confidence < 0.6` → передать L2 (на L1 не уверены)
   - route == "clarify" → запросить уточнение у пользователя
   - route == "refuse" → отклонить (опасный/неэтичный запрос)

**Граничные случаи:**

- Модель вернула невалидный JSON → retry 1 раз, при повторе → route="complex" (отправить в L2)
- Таймаут inference (>200 мс) → route="complex" (не блокировать)
- Модель не загружена / OOM → graceful fallback: всё идёт в L2

---

### 3.3. ReasoningCollegium (L2)

**Назначение:** Параллельный reasoning тремя разными моделями для получения разнообразных точек зрения на задачу.

**Модели (локальные, на beast i9-4090, через HuggingFace transformers + vLLM):**

Один экземпляр Qwen2.5-1.5B загружен в VRAM (~1.5 GB FP16). Три параллельных инстанса (M_a, M_b, M_c) — это три параллельных forward pass одной и той же модели с разным `torch.manual_seed()`, а не три копии в памяти.

| Слот | Модель | seed | Назначение (emergent) |
|------|--------|------|-----------------------|
| M_a | Qwen2.5-1.5B (локально) | 42 | Специализация через ImportanceScorer reward |
| M_b | Qwen2.5-1.5B (локально) | 137 | Специализация через ImportanceScorer reward |
| M_c | Qwen2.5-1.5B (локально) | 2718 | Специализация через ImportanceScorer reward |

**VRAM:** ~4.5 GB суммарно (1 модель + 3 KV-cache для параллельных инференсов)

**Входные данные:**

```python
@dataclass
class CollegiumInput:
    text: str                          # Запрос пользователя
    embedding: list[float]             # Embedding запроса
    working_memory_slice: dict         # Релевантный контекст
    action_hint: str | None            # От FastDetector
    task_context_id: str
```

**Выходные данные (от каждого инстанса):**

```python
@dataclass
class ModelResponse:
    model_id: str                      # "M_a" | "M_b" | "M_c"
    text: str                          # Ответ модели (декодированный для агрегатора)
    embedding: np.ndarray              # Projection head output (10–50d) для межмодульной передачи
    hidden_state: torch.Tensor | None  # Полный hidden state (для FinalNode через inputs_embeds)
    reasoning_trace: str | None        # Chain-of-thought (если модель поддерживает)
    proposed_actions: list[ActionProposal]  # Предложенные действия
    confidence: float                  # Самооценка модели (если есть)
    latency_ms: float                  # Время генерации
```

```python
@dataclass
class ActionProposal:
    tool: str                          # Имя инструмента
    params: dict[str, str]             # Абстрактные параметры (ЧТО, не КАК)
    reversible: bool                   # Обратимо ли действие
    rationale: str                     # Обоснование (для агрегатора)
```

**Алгоритм работы:**

1. Сформировать промпт для каждой модели:
   - **Без system prompt** — принципиальное решение для естественного разнообразия
   - Разный `seed` для каждой модели (M_a: seed=42, M_b: seed=137, M_c: seed=2718)
   - Температура: 0.7 (единая для всех)
   - max_tokens: 1024

2. Запустить три параллельных forward pass **одной загруженной модели** с разным seed:
   ```python
   async def forward_with_seed(model, tokenizer, prompt, seed):
       torch.manual_seed(seed)
       inputs = tokenizer(prompt, return_tensors="pt").to(model.device)
       with torch.no_grad():
           outputs = model.generate(**inputs, max_new_tokens=1024, temperature=0.7, do_sample=True)
       return tokenizer.decode(outputs[0], skip_special_tokens=True)

   responses = await asyncio.gather(
       run_sync(forward_with_seed, model, tokenizer, prompt, seed=42),
       run_sync(forward_with_seed, model, tokenizer, prompt, seed=137),
       run_sync(forward_with_seed, model, tokenizer, prompt, seed=2718),
       return_exceptions=True
   )
   ```
   
   > **Примечание:** Параллельные forward pass возможны через vLLM continuous batching (один процесс vLLM обрабатывает 3 запроса одновременно) или через sequential forward в thread pool. vLLM предпочтительнее для GPU utilization.

3. Обработать исключения:
   - Если 1 модель упала → работаем с 2
   - Если 2 упали → работаем с 1 (пометить как low-confidence)
   - Если все 3 упали → ошибка, вернуть пользователю сообщение об ошибке

4. Для каждого ответа вычислить embedding через `sentence-transformers` (локально) или projection head (векторный протокол)

5. Передать все ответы в Aggregator

**Reward за уникальность (emergent specialization):**

После каждого запроса вычислить для каждой модели:
```
uniqueness_score_i = 1 - max(cosine_similarity(emb_i, emb_j)) for j ≠ i
```

**Механизм специализации через ImportanceScorer:**

Поскольку все модели локальные, emergent specialization реализуется через ImportanceScorer:
- Каждый инстанс коллегии (M_a, M_b, M_c) обучает **свой собственный** ImportanceScorer независимо
- Scorer получает reward signal: 1.0 если ответ данного инстанса попал в консенсус или дал уникальный полезный вклад, 0.0 иначе
- Scorer учится акцентировать разные аспекты входного вектора → разные инстансы начинают "видеть" разное в одном и том же входе
- Результат: emergent specialization без fine-tuning самой LLM — специализация на уровне внимания к входу

Дополнительно: через **векторный протокол** (см. §4.5) каждый инстанс получает не текст, а embedding, прошедший через projection head scorer'а — разные scorer'ы подают на вход модели разные проекции одного сигнала.

**Граничные случаи:**

- Таймаут одной модели (>10 с) → отменить, работать с остальными
- Все модели дали идентичные ответы (cosine > 0.95) → не ошибка, просто нет дисперсии; передать как есть
- Одна модель дала ответ на другом языке → нормализовать через embedding (embedding language-agnostic)

---

### 3.4. Aggregator

**Назначение:** Объединение ответов коллегии без использования LLM. Выявление консенсуса через embedding-кластеризацию.

**Входные данные:**

```python
@dataclass
class AggregatorInput:
    responses: list[ModelResponse]     # 1–3 ответа от коллегии
    task_context_id: str
```

**Выходные данные:**

```python
@dataclass
class AggregatorOutput:
    consensus: str | None              # Текст консенсуса (если есть)
    consensus_embedding: list[float]   # Embedding консенсуса
    all_responses: list[ModelResponse] # Все ответы (для FinalNode)
    agreement_score: float             # 0.0–1.0 — степень согласия
    clusters: list[ResponseCluster]    # Кластеры ответов
    proposed_actions: list[ActionProposal]  # Объединённые действия
    conflict_detected: bool            # Есть ли конфликт между ответами
```

```python
@dataclass
class ResponseCluster:
    center_embedding: list[float]
    members: list[str]                 # model_ids
    text: str                          # Текст ближайшего к центру
```

**Алгоритм работы:**

1. **Вычислить матрицу cosine similarity** между embeddings всех ответов:
   ```
   sim_matrix[i][j] = cosine_similarity(resp_i.embedding, resp_j.embedding)
   ```

2. **Кластеризация:**
   - Если N=3: используем простую пороговую кластеризацию
   - Порог: `sim > 0.75` → в один кластер
   - Возможные исходы:
     - 1 кластер (все согласны, agreement > 0.75) → сильный консенсус
     - 2 кластера (2 vs 1) → слабый консенсус (мнение большинства)
     - 3 кластера (все разные) → нет консенсуса

3. **Формирование консенсуса:**
   - Сильный консенсус → текст ответа ближайшего к центроиду
   - Слабый консенсус → текст из большего кластера, пометка "не все согласны"
   - Нет консенсуса → передать все 3 ответа FinalNode для синтеза

4. **Агрегация действий:**
   - Действие предложено 2+ моделями → включить в proposed_actions
   - Действие предложено 1 моделью → включить с пометкой low_confidence
   - Конфликтующие действия (разные tools) → conflict_detected = true

**Граничные случаи:**

- Только 1 ответ → agreement_score = 0.5, передать как есть
- Ответы на разных языках → embedding нормализует (embedding модель multilingual)
- Очень длинные ответы (>4000 tokens) → для embedding использовать первые 512 tokens

---

### 3.5. FinalNode (L3)

**Назначение:** Формулирование финального ответа пользователю. Не рассуждает — только форматирует и синтезирует.

**Модель:** Qwen2.5-0.5B, запущена локально на RTX 4090 через vLLM. ~0.5 GB VRAM.

**Входные данные:**

```python
@dataclass
class FinalNodeInput:
    aggregator_output: AggregatorOutput
    original_query: str
    working_memory_slice: dict
    task_context_id: str
```

**Выходные данные:**

```python
@dataclass
class FinalNodeOutput:
    response_text: str                 # Финальный текст для пользователя
    actions_to_execute: list[ActionProposal]  # Действия для MotorNode
    needs_clarification: bool          # Запросить уточнение?
    clarification_question: str | None
    metadata: dict                     # Для логирования
```

**Алгоритм работы:**

1. Сформировать промпт:
   ```
   You are a response formatter. Do not reason. Do not add information.
   Synthesize the following expert opinions into one coherent response.
   
   User question: {original_query}
   
   Expert opinions:
   {aggregator_output.all_responses — тексты}
   
   Agreement level: {agreement_score}
   
   If experts disagree, present the majority view and note the dissent.
   Respond in the same language as the user's question.
   ```

2. Параметры вызова:
   - temperature: 0.3 (низкая — формулируем, не творим)
   - max_tokens: 2048
   - seed: фиксированный (для воспроизводимости)

3. Из ответа извлечь:
   - Текст для пользователя
   - Список действий (если коллегия предложила)

4. Применить принцип неопределённости:
   - Если action requires parameter с 0 или N>1 кандидатов → needs_clarification = true
   - Если action необратимо и agreement_score < 0.7 → needs_clarification = true

**Граничные случаи:**

- Модель L3 недоступна → вернуть текст из aggregator.consensus напрямую (без форматирования)
- Ответ пустой → retry 1 раз, при повторе → вернуть consensus as-is
- Ответ слишком длинный (>4096 chars) → обрезать с пометкой "[ответ сокращён]"

---

### 3.6. MotorNode

**Назначение:** Трансляция абстрактных команд (ЧТО делать) в конкретные tool calls (КАК делать). Критически важно: MotorNode **не знает зачем** выполняется действие. Он не может порождать собственные цели.

**Входные данные:**

```python
@dataclass
class MotorInput:
    actions: list[ActionProposal]      # Абстрактные команды от FinalNode
    working_memory_slice: dict         # Для подстановки конкретных параметров
    task_context_id: str
```

**Выходные данные:**

```python
@dataclass
class MotorOutput:
    executed_actions: list[ExecutedAction]
    pending_confirmations: list[PendingAction]  # Необратимые — ждут подтверждения
    errors: list[ActionError]
```

```python
@dataclass
class ExecutedAction:
    tool: str
    params: dict                       # Конкретные значения
    result: Any
    latency_ms: float

@dataclass
class PendingAction:
    action_id: str
    tool: str
    params: dict
    reason: str                        # "irreversible_action"
    timeout_s: float                   # Сколько ждать подтверждения
```

**Action Codebook:**

```python
# 10-мерное пространство действий
# Каждый tool — точка в этом пространстве
ACTION_CODEBOOK: dict[str, np.ndarray]  # tool_name → 10d vector

# Примеры:
# "file_read":     [0.9, 0.1, 0.0, 0.8, 0.0, 0.0, 0.1, 0.0, 0.9, 0.0]
# "file_write":    [0.9, 0.1, 0.0, 0.8, 0.0, 0.0, 0.1, 0.0, 0.1, 0.9]
# "web_search":    [0.1, 0.9, 0.0, 0.0, 0.8, 0.0, 0.0, 0.9, 0.5, 0.0]
# "calculator":    [0.0, 0.0, 0.9, 0.0, 0.0, 0.9, 0.0, 0.0, 0.9, 0.0]

# Размерности (семантика определяется при обучении, примерная интерпретация):
# d0: filesystem_related
# d1: network_related
# d2: computation_related
# d3: local_scope
# d4: external_scope
# d5: deterministic
# d6: stochastic
# d7: information_retrieval
# d8: reversible
# d9: state_modifying
```

**Алгоритм работы:**

1. Получить абстрактную команду от FinalNode (например: `tool="read_file", params={"target": "config"}`)

2. Подставить конкретные параметры из WorkingMemory:
   - `params["target"] = "config"` → lookup в WorkingMemory → `/home/user/config.yaml`

3. **Nearest Neighbor в Action Codebook:**
   - Вычислить embedding команды в 10d action space
   - Найти ближайший tool в codebook
   - `dist = euclidean_distance(command_vector, tool_vector)`
   - Если `dist < θ` (θ = 0.3) → выполнить
   - Если `θ < dist < 2θ` → temporal summation (накопить сигнал, ждать)
   - Если `dist > 2θ` → отбросить молча (не распознали команду)

4. **Temporal Summation:**
   - Буфер последних N=5 сигналов для каждого tool
   - Если 3+ сигналов за последние 2 секунды указывают на один tool → выполнить
   - Действовать по **последнему уверенному** сигналу (не усреднять)

5. **Классификация действий:**
   - Обратимые (file_read, web_search, calculator) → выполнить немедленно
   - Необратимые (file_write, file_delete, send_email) → задержка D = 2 с, ожидание подтверждения от ConflictMonitor/slow stream

6. **Принцип неопределённости:**
   - Параметр имеет 0 кандидатов → ошибка, запросить у пользователя
   - Параметр имеет N>1 кандидатов → запросить выбор у пользователя
   - Никогда не угадывать при необратимом действии

**Граничные случаи:**

- Tool не найден в codebook → ошибка ActionError("unknown_tool")
- WorkingMemory не содержит нужного параметра → запрос у пользователя
- Tool timeout → retry 1 раз, при повторе → ActionError("tool_timeout")
- Tool вернул ошибку → записать в WorkingMemory, передать обратно в pipeline

**Безопасность (ключевое):**

MotorNode **не имеет доступа** к:
- Формированию промптов для LLM
- Созданию новых ActionProposal
- Модификации Action Codebook в runtime
- Любой сетевой активности, не указанной в codebook

Это архитектурная гарантия того, что моторный слой не может "придумать" майнинг или SSH-туннель.

---

### 3.7. GossipProtocol

**Назначение:** Децентрализованная координация между узлами без центрального маршрутизатора. Каждый узел независимо оценивает важность входного сигнала и синхронизируется с узлами, давшими похожую оценку.

**Участники:** Все вычислительные узлы сети — FastDetector (L1), три модели коллегии (M_a, M_b, M_c), FinalNode, MotorNode. Итого 6 узлов в прототипе.

**Топология:** Полносвязный граф (каждый узел — сосед каждого). Для 6 узлов это оправдано. При масштабировании (>20 узлов) → переход на random subset of neighbors (fanout=3).

**Входные данные (сообщение gossip):**

```python
@dataclass
class GossipMessage:
    message_id: str                    # UUID
    source_node: str                   # ID узла-отправителя
    signal_embedding: list[float]      # Embedding входного сигнала (768d)
    importance_score: float            # Оценка важности от ImportanceScorer (0.0–1.0)
    timestamp: float                   # Unix timestamp (ms)
    hop_count: int                     # Сколько раз пересылалось (TTL)
    payload: dict | None               # Дополнительные данные (опционально)
```

**Алгоритм работы:**

1. **Broadcast:** При поступлении нового запроса Dispatcher рассылает сигнал (embedding) всем узлам одновременно через asyncio.

2. **Независимая оценка:** Каждый узел запускает ImportanceScorer:
   ```
   score_i = ImportanceScorer_i(signal_embedding)
   ```

3. **Gossip-рассылка:** Каждый узел передаёт соседям:
   ```
   (signal_embedding, score_i, node_id, timestamp)
   ```

4. **Синхронизация:** Узел i получает оценку от узла j:
   - Если `|score_i - score_j| < δ` (δ = 0.15) → считаются **согласованными**
   - Согласованные узлы формируют **рабочую группу** для данного сигнала
   - Рабочая группа: shared view в WorkingMemory (Redis pub/sub channel)

5. **Hop limit:** `max_hops = 3`. При hop_count >= max_hops → не пересылать дальше.

6. **Дедупликация:** Каждый узел хранит set последних 1000 message_id. Повторные — игнорировать.

7. **Затухание:** importance_score уменьшается на 10% за каждый hop:
   ```
   forwarded_score = score * (0.9 ** hop_count)
   ```

**Транспорт:** В прототипе — in-process asyncio queues (все узлы в одном процессе). При масштабировании → Redis pub/sub или ZeroMQ.

**Граничные случаи:**

- Узел не отвечает в течение 500 мс → считать его оценку = 0 (не заинтересован)
- Все узлы дали score < 0.2 → сигнал неинтересен никому (маловероятно для user input)
- Цикл сообщений → дедупликация по message_id
- Clock skew между узлами → в прототипе один процесс, проблемы нет; при распределении использовать Lamport timestamps

---

### 3.8. WorkingMemory

**Назначение:** Общий буфер данных задачи. Все узлы stateless — они берут нужный срез из WorkingMemory и пишут результаты обратно.

**Реализация:** Redis 7.x с модулем RedisJSON + RedisSearch.

**Структура данных:**

```python
# Ключи в Redis:

# Контекст задачи (создаётся Dispatcher)
"task:{task_id}:context" → {
    "query": str,                      # Исходный запрос
    "query_embedding": list[float],    # Embedding запроса
    "created_at": float,               # Timestamp
    "status": str,                     # "processing" | "completed" | "error"
    "route": str | None,               # "simple" | "complex" | None
}

# Промежуточные результаты узлов
"task:{task_id}:node:{node_id}" → {
    "output": Any,                     # Результат работы узла
    "timestamp": float,
    "latency_ms": float,
}

# Gossip-состояние
"task:{task_id}:gossip" → {
    "scores": {node_id: float},        # importance scores
    "groups": [[node_id, ...]],        # рабочие группы
}

# Результат агрегации
"task:{task_id}:aggregation" → {
    "consensus": str | None,
    "agreement_score": float,
    "clusters": [...],
}

# Финальный ответ
"task:{task_id}:response" → {
    "text": str,
    "actions": [...],
    "metadata": {...},
}
```

**Операции:**

| Операция | Метод | Латентность |
|----------|-------|-------------|
| Записать срез | `JSON.SET` | < 1 мс |
| Прочитать срез | `JSON.GET` с path | < 1 мс |
| Поиск по embedding | `FT.SEARCH` (HNSW) | < 5 мс |
| Pub/sub уведомление | `PUBLISH` | < 1 мс |
| Удалить задачу | `DEL` (batch) | < 1 мс |

**Жизненный цикл:**

1. Dispatcher создаёт `task:{id}:context`
2. Узлы читают нужные ключи, пишут свои результаты
3. После ответа пользователю — все ключи `task:{id}:*` удаляются
4. Фоновый cleaner: каждые 60 секунд удаляет задачи старше 5 минут (зависшие)

**Граничные случаи:**

- Redis OOM → включить maxmemory-policy `allkeys-lru` (вытеснять старое)
- Конкурентная запись → Redis single-threaded, атомарно; для сложных операций — Lua scripts
- Задача зависла → cleaner удалит через 5 минут; пользователь получит timeout

---

### 3.9. ConflictMonitor (ACC) + CriticalThinkingLayer (DLPFC + IFC)

**Источник:** Нейронаука (PFC + ACC механизмы критического мышления), PubMed 41003246, PMC 2730728, Wikipedia ACC.

---

#### 3.9.1 ConflictMonitor — аналог ACC

**Назначение:** Детекция и разрешение конфликтов между быстрым (L0/L1) и медленным (L2/L3) потоками обработки. Аналог передней поясной коры (ACC) в мозге.

**Два уровня детекции (уточнение из нейронауки):**
```
50–100мс  → быстрый ERN: "что-то не так" — ConflictMonitor флаг
200мс+    → медленная PFC: "вот что именно и что делать" — CriticalThinkingLayer
```

**Входные данные:**

```python
@dataclass
class ConflictMonitorInput:
    fast_result: Any | None            # Результат L0/L1 (если есть)
    fast_confidence: float
    slow_result: AggregatorOutput | None  # Результат L2 (если завершился)
    slow_confidence: float
    fast_timestamp: float              # Когда L0/L1 ответил
    slow_timestamp: float | None       # Когда L2 завершился
    task_context_id: str
```

**Выходные данные:**

```python
@dataclass
class ConflictDecision:
    action: Literal["use_fast", "use_slow", "stop_fast", "wait_slow", "merge"]
    reason: str
    stop_signal_sent: bool             # Был ли послан stop-signal
    latency_ms: float
```

**Алгоритм работы:**

ConflictMonitor работает **непрерывно** как фоновая корутина для каждой задачи.

1. **Фаза 1: L0/L1 ответил, L2 ещё работает**
   - Запустить таймер SSRT (Stop Signal Reaction Time) = 200 мс
   - Если L2 завершится за SSRT → перейти к фазе 2
   - Если L2 не завершился за SSRT → вернуть fast result пользователю

2. **Фаза 2: Оба результата есть — проверка конфликта**
   ```
   conflict_score = 1 - cosine_similarity(fast_embedding, slow_embedding)
   ```
   - `conflict_score < 0.2` → нет конфликта, использовать fast (быстрее)
   - `0.2 ≤ conflict_score < 0.5` → слабый конфликт, использовать slow (надёжнее)
   - `conflict_score ≥ 0.5` → сильный конфликт, использовать slow + логировать

3. **Stop-signal:**
   - Если fast result уже отправлен пользователю, а slow result отличается (conflict > 0.5):
     - Отправить коррекцию: "Подождите, уточняю ответ..."
     - Заменить на slow result
   - Stop-signal тормозит **источник** (отменяет coroutine L0/L1), а не очередь

4. **Окно отмены:**
   - T = 150–250 мс (SSRT из нейронауки)
   - В прототипе: T = 200 мс (фиксировано)
   - Если fast result не отправлен за T → отменить fast, ждать slow

**Граничные случаи:**

- L0 hit с confidence 1.0 → не ждать L2, отправить сразу (exact match из кеша)
- L2 упал → использовать fast result (что есть)
- Оба упали → ошибка, сообщить пользователю
- Fast и slow предлагают разные actions → приоритет slow (reasoning > рефлекс)

---

#### 3.9.2 CriticalThinkingLayer — аналог DLPFC + IFC right

**Назначение:** Проверка логической связности и внутренней согласованности ответа коллегии. Не генерирует ответ — оценивает качество рассуждения. Аналог дорсолатеральной PFC (рабочая память + логика) и правой IFC (unbiased reasoning).

**Когда активируется:**
- ConflictMonitor поднял флаг (ERN сработал)
- Все три инстанса коллегии дали слишком похожие ответы (similarity > 0.9 → подозрение на пузырь)
- Задача содержит явное противоречие или высокий stakes (необратимое действие)

**Два подзадачи:**

**DLPFC — проверка согласованности:**
```
Взять ответы коллегии + контекст рабочей памяти
Проверить: нет ли внутренних противоречий?
           соответствует ли ответ известным фактам?
           не противоречит ли предыдущим решениям задачи?
→ consistency_score: 0..1
```

**IFC right — структурное несогласие (адвокат дьявола):**
Один инстанс коллегии (M_c, фиксированный) получает специальный контекст:
```
"Два других агента пришли к выводу X. Найди слабые места в этом выводе.
 Что могло быть упущено? Где логика может быть неверной?"
```
Это не случайный несогласный — это структурная роль. M_c всегда играет IFC right когда CriticalThinkingLayer активен.

**Алгоритм:**
```
1. ConflictMonitor флаг → CriticalThinkingLayer активируется
2. DLPFC проверяет согласованность → consistency_score
3. Если consistency_score < 0.6 → IFC right (M_c) запускает challenge
4. M_c ответ → добавить в агрегатор как отдельный кластер
5. Агрегатор пересчитывает консенсус с учётом challenge
6. Если challenge существенно меняет результат → вернуть коллегии на пересмотр
```

**Защита от информационного пузыря (drift detection):**
```python
# Раз в N задач:
current_scorer_state = scorer.get_weights()
baseline = load_checkpoint(days_ago=7)
drift = cosine_distance(current_scorer_state, baseline)
if drift > DRIFT_THRESHOLD:
    alert("Значительный дрейф scorer'а за неделю — требуется ревью")
    # Не откатывать автоматически — уведомить человека
```

**Diversity penalty против пузыря:**
```python
RPE_effective = RPE × (1 - similarity_to_recent_N)
# Если последние N примеров слишком похожи → снижать вес их RPE
# Однотипное не должно сильно переучивать scorer
```

---

### 3.10. ImportanceScorer

**Назначение:** Лёгкая нейросеть на каждом узле, оценивающая важность входного сигнала для данного узла. Определяет, должен ли узел активироваться.

**Архитектура модели:**

```python
class ImportanceScorer(nn.Module):
    """
    LoRA-style модуль, 1–10M параметров.
    Обновляется онлайн (simple gradient step после каждой задачи).
    """
    # Input: embedding (768d)
    # Output: importance score (scalar, 0..1, sigmoid)
    
    # Архитектура:
    # Linear(768, 128) → ReLU → Linear(128, 32) → ReLU → Linear(32, 1) → Sigmoid
    # ~100K параметров (начальная версия)
    
    # LoRA adaptation:
    # Основные Linear слои заморожены после начальной тренировки
    # LoRA rank r=8, применяется ко всем Linear слоям
    # ~25K обучаемых параметров
```

**Входные данные:**

```python
embedding: torch.Tensor  # shape: (768,) — embedding входного сигнала
```

**Выходные данные:**

```python
score: float  # 0.0–1.0, importance score
```

**Обучение — RPE-guided consolidation (биологически обоснованный подход):**

Вместо experience replay с случайными примерами — приоритизация через ошибку предсказания награды (RPE), как в дофаминовой системе мозга.

**Онлайн (во время работы) — направленный LTP:**
```
RPE = actual_outcome - predicted_score   # ошибка предсказания

если RPE > +порог:                       # неожиданно ХОРОШО
    gradient step +                      # усилить активацию на этом типе сигнала
    сохранить (embedding, RPE) в episodic_buffer  # "повторять!"

elif RPE < -порог:                       # неожиданно ПЛОХО
    gradient step -                      # подавить активацию
    сохранить (embedding, RPE) в episodic_buffer  # "не повторять!"

else:                                    # ожидаемо (|RPE| ≤ порог)
    пропустить                           # скучно — не учиться
```

RPE > 0 (лучше ожидания) → дофамин всплеск → усилить веса → чаще активироваться на подобном.
RPE < 0 (хуже ожидания) → дофамин провал → ослабить веса → реже активироваться.
RPE ≈ 0 (как ожидалось) → нет сигнала → веса не трогать → нет деградации.

**Офлайн (аналог сна) — консолидация:**
```
1. Взять топ-N примеров из episodic_buffer по |RPE|  (самые неожиданные)
2. Обновить ImportanceScorer на этих примерах
3. Synaptic downscaling: примеры с низким RPE → слегка ослабить их веса
4. Очистить episodic_buffer
```

Важное (высокий RPE) переходит в долгосрочную память. Шум (низкий RPE) downscale и забывается намеренно. Деградации нет не потому что защищаем всё — а потому что важное усиливается, неважное само вытесняется.

**Score компонента "полезности":**

```
RPE = actual_outcome - predicted_score
relevance = α * |RPE| + β * novelty + γ * neighbor_assessment
```
- `|RPE|`: модуль ошибки предсказания (главный сигнал — неожиданность)
- `novelty`: cosine distance от средних embeddings последних 100 сигналов
- `neighbor_assessment`: средний importance_score соседей в gossip

Коэффициенты по умолчанию: α=0.5, β=0.3, γ=0.2.

**Источник:** Нейронаука — дофамин как учитель (VTA/RPE), гиппокамп replay + synaptic downscaling, PFC D1 рецепторы (pattern separation). [PNAS 1518931113, eLife 90793, Cercor 25/10/3629]

**Локальный кеш узла:**

Каждый узел хранит локальный кеш последних результатов:
```python
@dataclass
class LocalCacheEntry:
    embedding: list[float]
    result: Any
    score: float                       # novelty + prediction_error + neighbor_assessment
    created_at: float
    ttl: float                         # Время жизни (секунды)
```
TTL вычисляется динамически: `ttl = base_ttl * score` (base_ttl = 300 с, score 0–1 → TTL 0–300 с).

**Граничные случаи:**

- Первые N=100 запросов → score = 0.5 по умолчанию (cold start)
- NaN в embedding → score = 0.0 (не активироваться)
- Градиент explosion → clip_grad_norm = 1.0

---

## 4. Протоколы взаимодействия

### 4.1. Формат сообщений

Все межкомпонентные сообщения — Python dataclasses. Для хранения в Redis сериализуются в JSON (embedding → base64 float32).

**Базовое сообщение (обновлено для векторного протокола):**

```python
@dataclass
class BrainNetMessage:
    id: str                            # UUID v4
    type: str                          # Тип сообщения (см. ниже)
    source: str                        # ID узла-отправителя
    target: str | None                 # ID узла-получателя (None = broadcast)
    timestamp: float                   # Unix timestamp (ms)
    task_id: str                       # ID задачи
    ttl: int                           # Время жизни (hops для gossip, секунды для WM)
    # Векторный протокол: межмодульное общение через embeddings
    embedding: np.ndarray              # projection head output, 10–50d float32
    importance_score: float            # 0..1
    # Текст только для входа от пользователя и выхода к пользователю:
    raw_text: Optional[str] = None     # None для межмодульных сообщений
    payload: dict | None = None        # Дополнительная нагрузка (зависит от type)
```

> **Ключевой принцип:** Между компонентами передаётся сжатый вектор (embedding), а не текст. Текст присутствует только на границе системы (вход от пользователя → tokenize; выход к пользователю → decode). Это экономит контекстное окно и ускоряет межмодульное общение.

**Типы сообщений:**

| type | Описание | payload |
|------|----------|---------|
| `"signal"` | Входной сигнал (от Dispatcher) | `{"text": str, "embedding": list}` |
| `"importance"` | Оценка важности (gossip) | `{"score": float}` |
| `"sync_request"` | Запрос синхронизации | `{"group_id": str}` |
| `"response"` | Ответ узла | `{"text": str, "embedding": list, "actions": list}` |
| `"conflict"` | Обнаружен конфликт | `{"fast": dict, "slow": dict, "score": float}` |
| `"stop"` | Stop-signal | `{"target_node": str, "reason": str}` |
| `"action"` | Команда для MotorNode | `{"tool": str, "params": dict, "reversible": bool}` |
| `"result"` | Результат tool call | `{"tool": str, "result": Any, "error": str|None}` |
| `"clarify"` | Запрос уточнения у пользователя | `{"question": str, "options": list}` |

### 4.2. Gossip-протокол (детально)

**Параметры протокола:**

```python
GOSSIP_CONFIG = {
    "fanout": 5,                       # Сколько соседей оповещать (в полносвязном = все)
    "max_hops": 3,                     # Максимум пересылок
    "score_delta": 0.15,               # Порог для синхронизации
    "decay_factor": 0.9,               # Затухание score за hop
    "dedup_window": 1000,              # Размер окна дедупликации (message_ids)
    "timeout_ms": 500,                 # Таймаут ожидания ответа узла
    "sync_channel_prefix": "gossip:sync:",  # Redis pub/sub prefix
}
```

**Протокол синхронизации:**

```
Фаза 1: Broadcast
  Dispatcher → все узлы: GossipMessage(signal_embedding, hop=0)

Фаза 2: Evaluate
  Каждый узел i:
    score_i = ImportanceScorer_i(signal_embedding)
    → записать в Redis: "task:{id}:gossip:scores:{node_i}" = score_i

Фаза 3: Exchange
  Каждый узел i → все соседи: GossipMessage(signal_embedding, score_i, hop=1)
  
Фаза 4: Group Formation
  Каждый узел i:
    for each received (node_j, score_j):
      if |score_i - score_j| < delta:
        add node_j to my_group
    → записать в Redis: "task:{id}:gossip:groups:{node_i}" = my_group

Фаза 5: Sync
  Узлы в одной группе подписываются на общий Redis pub/sub channel:
    "gossip:sync:{task_id}:{group_hash}"
  Обмениваются данными через этот канал
```

**Временные гарантии:**

- Фазы 1–4: должны завершиться за < 100 мс (in-process, asyncio)
- Фаза 5: длится столько, сколько нужно для обработки (параллельно с pipeline)

### 4.3. Voting / синхронизация

В прототипе voting в классическом смысле не используется. Вместо этого:

1. **Implicit voting через agreement_score** в Aggregator: если 2 из 3 моделей дали похожий ответ — это "голосование большинством"

2. **Gossip-группы** — тоже форма voting: узлы с похожей оценкой важности объединяются

3. **Explicit voting** зарезервировано для будущих версий (например, для принятия решений о необратимых действиях)

### 4.4. Async/Sync Bridge

Все компоненты BrainNet работают в asyncio event loop. Для синхронных операций:

**Синхронные операции, требующие bridge:**

- Inference локальной модели (PyTorch) → `loop.run_in_executor(thread_pool, model.forward, input)`
- Тяжёлые вычисления numpy (embedding similarity) → `loop.run_in_executor`
- Файловый I/O → `aiofiles`

**Конфигурация:**

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Thread pool для синхронных операций
THREAD_POOL = ThreadPoolExecutor(
    max_workers=4,                     # 4 потока (не больше — GIL)
    thread_name_prefix="brainnet-sync"
)

# Обёртка для sync → async
async def run_sync(func, *args):
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(THREAD_POOL, func, *args)

# Пример использования:
# result = await run_sync(torch_model.forward, input_tensor)
```

**CUDA-операции:**

PyTorch на CUDA уже асинхронен по отношению к CPU. Однако:
- `model.forward()` блокирует Python thread до завершения
- Решение: `run_in_executor` + отдельный CUDA stream для каждого inference

```python
# Каждый узел с локальной моделью получает свой CUDA stream
cuda_streams = {
    "fast_detector": torch.cuda.Stream(),
    "importance_scorer_L1": torch.cuda.Stream(),
    # ...
}
```

### 4.5. Векторный протокол (inputs_embeds)

**Мотивация:** Все модели BrainNet — локальные, с полным доступом к PyTorch API. Это позволяет общаться между модулями не текстом, а векторами через `inputs_embeds`, минуя tokenizer.

**Принцип работы:**

```python
# Традиционный текстовый ввод (только для пользовательского ввода):
input_ids = tokenizer.encode(user_text, return_tensors="pt")
outputs = model(input_ids=input_ids)

# Векторный ввод (межмодульное общение):
# Вектор от соседнего узла — уже в embedding space модели
outputs = model(inputs_embeds=received_vector)
```

**Архитектура projection head:**

Каждый узел имеет projection head — маленькая сеть (Linear → ReLU → Linear), которая:
1. Принимает hidden state модели (размерность модели, например 896d для Qwen2.5-0.5B или 1536d для Qwen2.5-1.5B)
2. Проецирует в компактное пространство (10–50d)
3. Передаёт соседнему узлу

На принимающей стороне — обратный projection (50d → model_dim), чтобы подать на `inputs_embeds`.

```python
class ProjectionHead(nn.Module):
    def __init__(self, model_dim: int, proj_dim: int = 50):
        super().__init__()
        self.down = nn.Linear(model_dim, proj_dim)
        self.up = nn.Linear(proj_dim, model_dim)
    
    def encode(self, hidden_state: torch.Tensor) -> torch.Tensor:
        """model_dim → proj_dim (для передачи)"""
        return self.down(F.relu(hidden_state))
    
    def decode(self, projected: torch.Tensor) -> torch.Tensor:
        """proj_dim → model_dim (для inputs_embeds)"""
        return self.up(F.relu(projected))
```

**Что это даёт:**
- Контекстное окно **не растёт** от межмодульного общения
- Передаём сжатое представление (10–50 float32 ≈ 40–200 bytes), а не текст (сотни–тысячи tokens)
- Latency: передача вектора ~0 мс vs. tokenize+detokenize ~5–10 мс
- Текст только на входе от пользователя и на выходе к пользователю

**Ограничения:**
- Projection head нужно обучать (или инициализировать из PCA hidden states)
- Потеря информации при сжатии (50d << 896/1536d) — компромисс
- Debugging сложнее: вектор не читается глазами (нужна визуализация)

---

## 5. Стек технологий

### 5.1. Инфраструктура

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| Сервер (beast) | i9-13900K + RTX 4090 (24GB VRAM) + 32GB RAM | Все модели локальные, ~6–7 GB VRAM из 24 GB |
| ОС | Linux (Ubuntu 22.04+) | CUDA support, production-ready |
| Python | 3.12 | asyncio improvements, typing, dataclasses |
| GPU inference | PyTorch 2.1+ CUDA 12.x | Стандарт для ML, CUDA поддержка |
| Async runtime | asyncio (stdlib) | Нативный для Python, без лишних зависимостей |
| Кеш/память | Redis 7.x + RedisJSON + RedisSearch | Sub-ms латентность, JSON документы, vector search |

### 5.2. ML / AI

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| **Основной inference** | HuggingFace `transformers` + `vLLM` | Локальные модели, полный контроль, доступ к `inputs_embeds` для векторного протокола |
| **Ускорение загрузки** | `accelerate` | Автоматическое распределение по GPU, mixed precision |
| Локальная модель (L1) | Qwen2.5-0.5B через vLLM | Быстрый inference, ~0.5 GB VRAM |
| Коллегия (L2) | Qwen2.5-1.5B × 1 экземпляр, 3 parallel forward | ~4.5 GB VRAM, три seed для разнообразия |
| Финальный узел (L3) | Qwen2.5-0.5B через vLLM | ~0.5 GB VRAM |
| Моторика | Qwen2.5-0.5B + function calling | ~0.5 GB VRAM |
| Embeddings (основные) | `sentence-transformers` (локально) | Без внешних зависимостей, multilingual |
| Embeddings (fallback) | LiteLLM API `Qwen3-Embedding-0.6B` | Опциональный fallback через `https://litellm.jakeberrimor.com` |
| LLM API (опционально) | LiteLLM | Только для экспериментов и fallback, не основной путь |
| Importance Scorer | PyTorch (custom nn.Module) + 6× tiny LoRA | Легко обучать онлайн, <1 GB суммарно |
| Similarity/кластеризация | `numpy` + `scipy` | cosine_similarity, простая кластеризация |

**Итого VRAM:** ~6–7 GB из 24 GB доступных на RTX 4090

### 5.3. Networking / Transport

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| Gossip (in-process) | `asyncio.Queue` | Все узлы в одном процессе, минимальная латентность |
| Gossip (будущее) | Redis pub/sub или ZeroMQ | Для распределённой версии |
| WorkingMemory sync | Redis pub/sub | Нативный для Redis, < 1 мс |
| User interface | WebSocket (FastAPI) | Real-time, двунаправленный |
| HTTP API | FastAPI | Async-native, автодокументация |

### 5.4. Observability

| Компонент | Технология | Обоснование |
|-----------|------------|-------------|
| Логирование | `structlog` | Структурированные JSON-логи |
| Метрики | Prometheus client | Стандарт, легко интегрировать |
| Трейсинг | OpenTelemetry (spans) | Trace full pipeline L0→L3 |
| Визуализация | Grafana | Дашборды, алерты |

### 5.5. Зависимости (requirements.txt)

```
# Core
fastapi>=0.110
uvicorn>=0.29
redis>=5.0

# ML — основной inference (локальные модели)
torch>=2.1
transformers>=4.40
vllm>=0.4
accelerate>=0.27
numpy>=1.26
scipy>=1.12
sentence-transformers>=2.5

# ML — опциональный fallback через API
openai>=1.12                           # Опционально: LiteLLM API fallback

# Observability
structlog>=24.1
prometheus-client>=0.20
opentelemetry-api>=1.23
opentelemetry-sdk>=1.23

# Utilities
pydantic>=2.6
python-dotenv>=1.0
aiofiles>=23.2

# Dev
pytest>=8.0
pytest-asyncio>=0.23
httpx>=0.27  # для тестирования FastAPI
```

---

## 6. Структура проекта

```
brainnet/
├── README.md
├── pyproject.toml                     # Project metadata, dependencies
├── .env.example                       # Шаблон переменных окружения
├── docker-compose.yml                 # Redis + (опционально) vLLM
│
├── src/
│   └── brainnet/
│       ├── __init__.py
│       ├── main.py                    # Entry point, FastAPI app
│       ├── config.py                  # Pydantic Settings, все параметры
│       │
│       ├── core/                      # Ядро системы
│       │   ├── __init__.py
│       │   ├── dispatcher.py          # Dispatcher: приём запроса, запуск pipeline
│       │   ├── pipeline.py            # Orchestration L0 → L1 → L2 → L3
│       │   └── types.py              # Все dataclass'ы и типы (BrainNetMessage, etc.)
│       │
│       ├── layers/                    # Уровни обработки
│       │   ├── __init__.py
│       │   ├── cache_layer.py         # L0: CacheLayer (3 уровня кеша)
│       │   ├── fast_detector.py       # L1: FastDetector (локальная модель)
│       │   ├── collegium.py           # L2: ReasoningCollegium (3 модели)
│       │   ├── aggregator.py          # Aggregator (embedding кластеризация)
│       │   └── final_node.py          # L3: FinalNode (формулировка ответа)
│       │
│       ├── motor/                     # Моторный слой
│       │   ├── __init__.py
│       │   ├── motor_node.py          # MotorNode: action codebook + execution
│       │   ├── action_codebook.py     # Action Codebook (10d vectors)
│       │   ├── tools.py               # Реестр доступных инструментов
│       │   └── temporal_buffer.py     # Temporal summation buffer
│       │
│       ├── gossip/                    # Gossip-протокол
│       │   ├── __init__.py
│       │   ├── protocol.py            # GossipProtocol: broadcast, evaluate, sync
│       │   ├── node_registry.py       # Реестр узлов
│       │   └── transport.py           # Транспортный уровень (asyncio queues)
│       │
│       ├── memory/                    # Рабочая память
│       │   ├── __init__.py
│       │   ├── working_memory.py      # WorkingMemory: Redis wrapper
│       │   ├── cache_store.py         # Хранилище кешей (L0)
│       │   └── cleaner.py             # Фоновая очистка зависших задач
│       │
│       ├── monitor/                   # Мониторинг и безопасность
│       │   ├── __init__.py
│       │   ├── conflict_monitor.py    # ConflictMonitor: fast/slow conflict
│       │   └── safety.py              # Safety checks (необратимые действия)
│       │
│       ├── scoring/                   # ImportanceScorer
│       │   ├── __init__.py
│       │   ├── importance_scorer.py   # Модель ImportanceScorer (PyTorch)
│       │   ├── trainer.py             # Online training loop
│       │   └── checkpoints/           # Сохранённые веса
│       │
│       ├── llm/                       # LLM интеграция
│       │   ├── __init__.py
│       │   ├── client.py              # Основной клиент: vLLM/transformers для локальных моделей
│       │   ├── embeddings.py          # Embedding вычисление (sentence-transformers локально + API fallback)
│       │   ├── local_model.py         # Интерфейс к локальным моделям (vLLM + inputs_embeds)
│       │   ├── vector_protocol.py     # Projection heads, encode/decode для межмодульных векторов
│       │   └── litellm_fallback.py    # Опциональный fallback через LiteLLM API
│       │
│       ├── api/                       # HTTP API
│       │   ├── __init__.py
│       │   ├── routes.py              # REST endpoints
│       │   └── websocket.py           # WebSocket для real-time
│       │
│       └── observability/             # Логи, метрики, трейсы
│           ├── __init__.py
│           ├── logging.py             # structlog config
│           ├── metrics.py             # Prometheus метрики
│           └── tracing.py             # OpenTelemetry setup
│
├── tests/
│   ├── conftest.py                    # Fixtures (Redis mock, LLM mock)
│   ├── unit/
│   │   ├── test_cache_layer.py
│   │   ├── test_fast_detector.py
│   │   ├── test_collegium.py
│   │   ├── test_aggregator.py
│   │   ├── test_motor_node.py
│   │   ├── test_gossip.py
│   │   ├── test_conflict_monitor.py
│   │   └── test_importance_scorer.py
│   ├── integration/
│   │   ├── test_pipeline.py           # End-to-end pipeline
│   │   ├── test_working_memory.py     # Redis integration
│   │   └── test_llm_client.py         # LiteLLM integration
│   └── load/
│       └── test_load.py               # Нагрузочное тестирование
│
├── scripts/
│   ├── start_vllm.sh                 # Запуск vLLM со всеми локальными моделями
│   ├── download_models.sh            # Скачивание Qwen2.5-0.5B, 1.5B, sentence-transformers
│   ├── train_importance_scorer.py     # Офлайн-обучение ImportanceScorer
│   ├── train_projection_heads.py      # Обучение projection heads для векторного протокола
│   └── benchmark.py                   # Бенчмарк латентности по уровням
│
└── docs/
    ├── architecture.md                # Этот документ (сокращённый)
    └── api.md                         # API документация
```

### 6.1. Зависимости между модулями

```
core/types.py ← все модули (общие типы)
core/dispatcher.py ← core/pipeline.py
core/pipeline.py ← layers/*, motor/*, monitor/*
layers/cache_layer.py ← memory/cache_store.py, llm/embeddings.py
layers/fast_detector.py ← llm/local_model.py, memory/working_memory.py
layers/collegium.py ← llm/local_model.py, llm/vector_protocol.py, llm/embeddings.py
layers/aggregator.py ← llm/embeddings.py
layers/final_node.py ← llm/local_model.py, llm/vector_protocol.py
motor/motor_node.py ← motor/action_codebook.py, motor/tools.py, memory/working_memory.py
gossip/protocol.py ← gossip/transport.py, scoring/importance_scorer.py
monitor/conflict_monitor.py ← llm/embeddings.py
```

---

## 7. Этапы реализации

### Этап 0: Фундамент (1–2 дня)

**Цель:** Рабочий скелет проекта, конфигурация, базовые типы.

- [ ] Создать структуру проекта (pyproject.toml, src/, tests/)
- [ ] Определить все dataclasses в `core/types.py`
- [ ] Настроить `config.py` (Pydantic Settings, .env)
- [ ] Настроить structlog, базовые метрики
- [ ] Docker-compose для Redis
- [ ] Скачать модели: Qwen2.5-0.5B-Instruct, Qwen2.5-1.5B-Instruct, sentence-transformers
- [ ] Запустить vLLM с Qwen2.5-1.5B, проверить inference
- [ ] Проверить `inputs_embeds` API — что модели принимают векторный ввод
- [ ] Опционально: проверить подключение к LiteLLM API (fallback)

**Критерий готовности:** `python -m brainnet` запускается, подключается к Redis, делает тестовый inference локальной модели через vLLM.

---

### Этап 1: Working Memory + LLM Client (2–3 дня)

**Цель:** Рабочая память и клиент к моделям — два фундаментальных сервиса.

- [ ] `memory/working_memory.py` — CRUD операции, TTL, pub/sub
- [ ] `llm/client.py` — обёртка для локальных моделей через vLLM (async, retry, timeout) + опциональный LiteLLM fallback
- [ ] `llm/embeddings.py` — вычисление embeddings через sentence-transformers (локально) + API fallback
- [ ] `memory/cleaner.py` — фоновая очистка зависших задач
- [ ] Тесты: unit + integration с Redis

**Критерий готовности:** Можно создать задачу в WM, записать/прочитать данные, получить embedding локально, вызвать локальную модель через vLLM.

---

### Этап 2: Минимальный Pipeline L2→L3 (3–4 дня)

**Цель:** Коллегия + Агрегатор + FinalNode — основной reasoning path.

- [ ] `layers/collegium.py` — параллельный вызов 3 моделей
- [ ] `layers/aggregator.py` — cosine similarity, кластеризация, consensus
- [ ] `layers/final_node.py` — формулировка ответа
- [ ] `core/pipeline.py` — оркестрация L2→L3 (без L0/L1 пока)
- [ ] `core/dispatcher.py` — приём запроса, создание task context
- [ ] Простой CLI-интерфейс для тестирования
- [ ] Тесты: collegium с mock LLM, aggregator unit tests

**Критерий готовности:** Пользователь вводит вопрос → получает ответ от коллегии через агрегатор → FinalNode форматирует.

---

### Этап 3: CacheLayer (L0) + FastDetector (L1) (3–4 дня)

**Цель:** Быстрые уровни обработки.

- [ ] `memory/cache_store.py` — три уровня кеша в Redis
- [ ] `layers/cache_layer.py` — L1 exact, L2 semantic, L3 pattern
- [ ] `layers/fast_detector.py` — классификация через локальную модель
- [ ] `llm/local_model.py` — интерфейс к vLLM / llama.cpp
- [ ] `scripts/start_local_model.sh` — запуск Qwen2.5-0.5B (L1) через vLLM
- [ ] Интеграция L0→L1 в pipeline (early exit)
- [ ] Тесты: cache hit/miss, detector routing

**Критерий готовности:** Повторный вопрос отвечается из кеша за <50 мс. Простые вопросы обрабатываются на L1 без L2.

---

### Этап 4: MotorNode (2–3 дня)

**Цель:** Выполнение действий через Action Codebook.

- [ ] `motor/action_codebook.py` — 10d vectors для каждого tool
- [ ] `motor/tools.py` — реестр tools (file_read, web_search, calculator)
- [ ] `motor/temporal_buffer.py` — temporal summation
- [ ] `motor/motor_node.py` — nearest neighbor, threshold, reversibility check
- [ ] `monitor/safety.py` — проверка необратимых действий
- [ ] Интеграция в pipeline: FinalNode → MotorNode → Tool execution
- [ ] Тесты: codebook lookup, temporal summation, safety checks

**Критерий готовности:** Пользователь просит "прочитай файл X" → pipeline → MotorNode → file_read(X) → ответ с содержимым.

---

### Этап 5: ConflictMonitor (2 дня)

**Цель:** Детекция и разрешение конфликтов fast/slow.

- [ ] `monitor/conflict_monitor.py` — фоновая корутина, SSRT timer
- [ ] Интеграция: ConflictMonitor наблюдает за L0/L1 и L2/L3
- [ ] Stop-signal: отмена fast result если slow отличается
- [ ] Тесты: конфликт, нет конфликта, таймаут

**Критерий готовности:** При конфликте fast/slow → правильное решение за <250 мс.

---

### Этап 6: Gossip-протокол + ImportanceScorer (3–4 дня)

**Цель:** Децентрализованная координация.

- [ ] `scoring/importance_scorer.py` — PyTorch модель
- [ ] `scoring/trainer.py` — online training
- [ ] `gossip/transport.py` — asyncio queues
- [ ] `gossip/protocol.py` — broadcast, evaluate, group formation, sync
- [ ] `gossip/node_registry.py` — реестр узлов
- [ ] Интеграция: gossip работает параллельно с pipeline
- [ ] Тесты: group formation, score convergence

**Критерий готовности:** Узлы формируют рабочие группы на основе importance scores. Scorer обновляется после каждой задачи.

---

### Этап 7: API + Observability (2 дня)

**Цель:** HTTP API и мониторинг.

- [ ] `api/routes.py` — REST: POST /query, GET /status, GET /metrics
- [ ] `api/websocket.py` — WebSocket для streaming ответов
- [ ] `observability/metrics.py` — Prometheus метрики по всем компонентам
- [ ] `observability/tracing.py` — OpenTelemetry spans для pipeline
- [ ] Grafana дашборд (JSON template)
- [ ] `scripts/benchmark.py` — автоматический бенчмарк

**Критерий готовности:** Работающий HTTP API. Grafana дашборд показывает латентность, cache hit rate, agreement scores.

---

### Этап 8: Интеграция и стресс-тестирование (2–3 дня)

**Цель:** Полный end-to-end тест, нагрузка.

- [ ] End-to-end тесты: 20+ сценариев (простые, сложные, tool use, конфликты, ошибки)
- [ ] Нагрузочное тестирование: 10 параллельных запросов
- [ ] Тест graceful degradation: отключить Redis, отключить API, отключить модель
- [ ] Тест безопасности: попытки MotorNode выйти за codebook
- [ ] Профилирование: bottleneck analysis
- [ ] Документация API

**Критерий готовности:** Система стабильно работает под нагрузкой 10 req/s, graceful degradation при отказах.

---

### Сводка по срокам

| Этап | Длительность | Суммарно |
|------|-------------|----------|
| 0: Фундамент | 1–2 дня | 1–2 дня |
| 1: WM + LLM | 2–3 дня | 3–5 дней |
| 2: L2→L3 pipeline | 3–4 дня | 6–9 дней |
| 3: L0 + L1 | 3–4 дня | 9–13 дней |
| 4: MotorNode | 2–3 дня | 11–16 дней |
| 5: ConflictMonitor | 2 дня | 13–18 дней |
| 6: Gossip + Scorer | 3–4 дня | 16–22 дня |
| 7: API + Observability | 2 дня | 18–24 дня |
| 8: Интеграция | 2–3 дня | 20–27 дней |
| **Итого** | **20–27 рабочих дней** | **~1–1.5 месяца** |

---

## 8. Метрики и тестирование

### 8.1. Метрики системы (Prometheus)

```python
# Латентность по уровням
brainnet_request_duration_seconds{level="L0|L1|L2|L3|total"}

# Cache
brainnet_cache_hits_total{level="L1|L2|L3"}
brainnet_cache_misses_total
brainnet_cache_hit_rate                    # hits / (hits + misses)

# Коллегия
brainnet_collegium_response_time_seconds{model="M_a|M_b|M_c"}
brainnet_collegium_agreement_score         # Histogram
brainnet_collegium_uniqueness_score{model="M_a|M_b|M_c"}

# ConflictMonitor
brainnet_conflicts_total
brainnet_conflict_resolution{action="use_fast|use_slow|stop_fast"}
brainnet_stop_signal_latency_ms

# Gossip
brainnet_gossip_messages_total
brainnet_gossip_groups_formed_total
brainnet_gossip_sync_latency_ms

# ImportanceScorer
brainnet_importance_score{node="..."}      # Histogram
brainnet_scorer_loss{node="..."}           # Online training loss

# MotorNode
brainnet_motor_actions_total{tool="...", reversible="true|false"}
brainnet_motor_codebook_distance           # Histogram
brainnet_motor_temporal_accumulations_total

# Ошибки
brainnet_errors_total{component="...", type="..."}
```

### 8.2. Тестирование Gossip-протокола

**Unit-тесты:**

1. **Group formation:** 6 узлов, задать importance scores вручную. Проверить что узлы с |delta| < 0.15 оказались в одной группе.
2. **Deduplication:** Послать одно сообщение 3 раза. Проверить что обработано 1 раз.
3. **Hop limit:** Послать сообщение с hop_count=3. Проверить что не переслано дальше.
4. **Decay:** Score=0.8, hop=2 → forwarded_score = 0.8 * 0.9^2 = 0.648.

**Integration-тесты:**

5. **Convergence:** Запустить 6 узлов с реальными ImportanceScorers. Подать 100 запросов. Проверить что группы стабилизируются (одинаковые запросы → одинаковые группы).
6. **Latency:** Время от broadcast до group formation < 100 мс (p99).

### 8.3. Тестирование Emergent Specialization

**Метрики:**
1. **Cosine similarity ответов** — между ответами моделей коллегии по сериям запросов
2. **Расхождение hidden states** — cosine distance между projection head выходами трёх инстансов через итерации обучения ImportanceScorer

**Процедура:**

1. Подготовить датасет из 100 разнообразных запросов (код, факты, творчество, аналитика)
2. Прогнать через коллегию, записать:
   - embeddings ответов каждого инстанса
   - hidden states (projection head output) каждого ImportanceScorer
3. Построить матрицу similarity 3x3 для каждого запроса
4. Отслеживать динамику по сериям:
   - Серия 1 (запросы 1–100): baseline similarity
   - Серия 2–N: если specialization работает — similarity ответов должна снижаться, а расхождение hidden states — расти

**Дополнительная метрика (hidden states divergence):**
```python
# После каждых 100 запросов:
for i, j in combinations([scorer_a, scorer_b, scorer_c], 2):
    divergence = 1 - cosine_similarity(
        i.projection_head.encode(test_embedding),
        j.projection_head.encode(test_embedding)
    )
    log_metric(f"scorer_divergence_{i}_{j}", divergence)
```

**Ожидание:** С локальными моделями и обучаемыми ImportanceScorer'ами specialization **реально достижима** через различие в projection head. Scorer'ы учатся акцентировать разные аспекты входного вектора.

**Критерии успеха:**
- Similarity ответов < 0.6 между парами после 500 запросов
- Hidden states divergence > 0.3 после 500 запросов
- Scorer'ы стабилизируются (loss < 0.1) к 1000 запросов

### 8.4. Тестирование ConflictMonitor

**Сценарии:**

| # | Сценарий | Ожидаемый результат |
|---|----------|---------------------|
| 1 | L0 hit (exact), L2 не нужен | use_fast, stop_signal_sent=false |
| 2 | L1 simple (confidence=0.9), L2 согласен | use_fast (быстрее), conflict_score < 0.2 |
| 3 | L1 simple (confidence=0.9), L2 не согласен | use_slow, stop_signal_sent=true |
| 4 | L1 не успел за SSRT, L2 готов | use_slow, stop_signal_sent=false |
| 5 | L2 timeout, L1 есть | use_fast (fallback) |
| 6 | L1 предлагает action, L2 — другой action | conflict, use_slow |
| 7 | Оба предлагают необратимое действие, разное | conflict, needs_clarification |

**Латентность:** Stop-signal должен отработать за < 250 мс (SSRT). Измерять на 1000 запусках, p99 < 250 мс.

### 8.5. Нагрузочное тестирование

**Инструмент:** `locust` или кастомный asyncio-клиент.

**Сценарии:**

| Сценарий | RPS | Длительность | Проверяем |
|----------|-----|-------------|-----------|
| Baseline | 1 | 5 мин | Корректность, baseline latency |
| Moderate | 5 | 10 мин | Стабильность, нет утечек памяти |
| Peak | 10 | 5 мин | Деградация, таймауты |
| Cache warm | 10 (повторные запросы) | 5 мин | Cache hit rate > 80% |
| Stress | 20 | 2 мин | Graceful degradation |

**Мониторинг во время нагрузки:**
- RSS memory (не должно расти линейно)
- Redis memory usage
- GPU utilization (для L1)
- Error rate

---

## 9. Открытые вопросы и риски

### 9.1. Открытые вопросы

| # | Вопрос | Влияние | Предложение |
|---|--------|---------|-------------|
| 1 | **Calibration of ImportanceScorer convergence speed.** Как быстро scorer'ы коллегии должны сходиться к специализации? Слишком быстро → застрянут в локальном минимуме. Слишком медленно → не успеют специализироваться за разумное число запросов. | Высокое — ключевая гипотеза архитектуры | Эксперимент: запустить с lr=1e-4, измерить cosine distance между проекциями трёх scorer'ов через каждые 100 запросов. Целевое расхождение: >0.3 за 500 запросов. |
| 2 | **Размерность Action Codebook.** 10d выбрано интуитивно. Оптимальная размерность? | Среднее — влияет на точность MotorNode | Начать с 10d, измерить accuracy codebook lookup на 20+ tools. Если плохо — увеличить до 16–32d. |
| 3 | **SSRT = 200 мс — верно ли для наших латентностей?** В нейронауке 150–250 мс — для моторных реакций. У нас L2 может длиться 5+ секунд. | Среднее — влияет на UX | Возможно SSRT должен быть относительным: SSRT = max(200мс, 10% от expected_L2_time). Экспериментировать. |
| 4 | **Порог семантического кеша (0.92).** Слишком высокий → мало хитов. Слишком низкий → неверные хиты. | Среднее | Начать с 0.92, логировать все similarity > 0.8, вручную проверить false positives/negatives, калибровать. |
| 5 | **Формат Action Codebook embeddings.** Как маппить абстрактную команду от коллегии в 10d вектор? | Высокое — без этого MotorNode не работает | Простой вариант: ключевые слова → фиксированный вектор. Сложный: обучить маленький encoder. |
| 6 | **Обучение ImportanceScorer: что считать "полезностью" узла?** | Среднее | Прокси: узел был в winning группе → полезен. Или: узел сгенерировал ответ, попавший в консенсус → полезен. |
| 7 | **Gossip-протокол: нужен ли он при 6 узлах?** Для 6 узлов broadcast проще и быстрее. | Низкое в прототипе | Реализовать gossip для корректности архитектуры. При 6 узлах разница с broadcast минимальна. |

### 9.2. Риски

| # | Риск | Вероятность | Влияние | Митигация |
|---|------|------------|---------|-----------|
| 1 | **Локальные модели: OOM или конкуренция за GPU.** Все модели на одной RTX 4090. При пиковой нагрузке возможна конкуренция за VRAM/compute. | Средняя | Высокое — деградация latency | vLLM continuous batching. Приоритизация: L1 > L2 > L3 (быстрый путь важнее). При OOM → уменьшить batch size или quantize до INT8. LiteLLM API как emergency fallback. |
| 2 | **Qwen2.5-0.5B для L1 недостаточно умна.** 0.5B модель может плохо классифицировать сложные запросы. | Средняя | Среднее | Benchmark классификации на тестовом датасете. Если accuracy < 80% → заменить L1 на Qwen2.5-1.5B (доп. ~1.5 GB VRAM, всё ещё в бюджете). Или использовать Qwen2.5-0.5B + ensemble-voting. |
| 3 | **Redis Single Point of Failure.** Вся рабочая память в одном Redis. | Средняя | Высокое — система неработоспособна | В прототипе приемлемо. При продакшене: Redis Sentinel / Cluster. Fallback: in-memory dict при недоступности Redis. |
| 4 | **Aggregator не находит консенсус.** 3 разных модели → 3 разных ответа. | Средняя | Среднее — FinalNode справится, но хуже | FinalNode должен уметь синтезировать из 3 разных мнений. Это его основная задача. |
| 5 | **Action Codebook не покрывает нужные действия.** Фиксированный codebook vs. разнообразие запросов. | Средняя | Среднее | Начать с 5–10 tools. Расширять по мере тестирования. Fallback: если dist > 2θ → запросить уточнение. |
| 6 | **Complexity creep.** 10 компонентов для прототипа — много. Отладка сложная. | Высокая | Среднее | Строго следовать этапам. Каждый этап — рабочий инкремент. Не переходить к следующему пока текущий не стабилен. |
| 7 | **GPU memory.** Все модели локальные: Qwen2.5-0.5B (L1, L3, Motor) + Qwen2.5-1.5B (коллегия) + ImportanceScorer (6 шт) + sentence-transformers. | Низкая | Среднее | Оценка: Qwen2.5-1.5B ~3GB FP16 + 3× Qwen2.5-0.5B ~1.5GB + ImportanceScorer <1GB + sentence-transformers ~0.5GB ≈ **6–7 GB из 24 GB**. Запас ~17 GB. При необходимости: quantization (INT8/INT4) для дополнительной экономии. |
| 8 | **Emergent specialization недостаточно выражена.** Один и тот же Qwen2.5-1.5B с разным seed может давать слишком похожие ответы. | Средняя | Среднее | Специализация через ImportanceScorer: разные scorer'ы подают разные projection входного вектора → модель «видит» разное. Измерять scorer divergence. Если недостаточно — увеличить projection dim или добавить noise injection. |

### 9.3. Архитектурные допущения прототипа

1. **Все узлы в одном процессе.** В прототипе не нужна сетевая коммуникация между узлами — только asyncio queues. Это упрощает разработку, но ограничивает масштабирование.

2. **Gossip-топология фиксирована.** 6 узлов, полносвязный граф. Динамическое добавление/удаление узлов — вне скоупа.

3. **Action Codebook фиксирован.** Набор tools и их 10d-представления задаются при запуске. Динамическое расширение — вне скоупа.

4. **Один пользователь.** Прототип не поддерживает multi-tenancy. Один user, один pipeline.

5. **Нет персистентности между сессиями.** ImportanceScorer weights сохраняются, кеш в Redis переживает рестарт, но WorkingMemory и gossip-состояние — нет.

---

## Приложение A: Переменные окружения

```bash
# .env

# Локальные модели (основной путь)
MODEL_FAST_DETECTOR=Qwen/Qwen2.5-0.5B-Instruct     # L1
MODEL_COLLEGIUM=Qwen/Qwen2.5-1.5B-Instruct          # L2 (одна модель, 3 seed)
MODEL_FINAL=Qwen/Qwen2.5-0.5B-Instruct              # L3
MODEL_MOTOR=Qwen/Qwen2.5-0.5B-Instruct              # Моторика
MODEL_EMBEDDING=sentence-transformers/all-MiniLM-L6-v2  # Локальные embeddings

# LiteLLM API (опциональный fallback)
LITELLM_BASE_URL=https://litellm.jakeberrimor.com
LITELLM_API_KEY=sk-4x1xrEJX9-aQmnD4XUDv-Q
LITELLM_EMBEDDING_MODEL=litellm/Qwen3-Embedding-0.6B

# Redis
REDIS_URL=redis://localhost:6379/0

# vLLM endpoints (локальные модели)
VLLM_BASE_URL=http://localhost:8000/v1     # vLLM primary endpoint
VLLM_COLLEGIUM_URL=http://localhost:8001/v1  # vLLM для коллегии (опционально отдельный)

# Pipeline
CACHE_SEMANTIC_THRESHOLD=0.92
CACHE_PATTERN_THRESHOLD=0.88
CACHE_MAX_ENTRIES=10000
DETECTOR_CONFIDENCE_THRESHOLD=0.8
COLLEGIUM_TEMPERATURE=0.7
COLLEGIUM_MAX_TOKENS=1024
FINAL_TEMPERATURE=0.3
MOTOR_CODEBOOK_THRESHOLD=0.3
CONFLICT_SSRT_MS=200
GOSSIP_SCORE_DELTA=0.15
GOSSIP_MAX_HOPS=3

# Server
HOST=0.0.0.0
PORT=8080
```

## Приложение B: Glossary

| Термин | Определение |
|--------|-------------|
| **Action Codebook** | Словарь доступных действий, представленных как точки в 10-мерном пространстве |
| **Agreement Score** | Степень согласия между моделями коллегии (0.0–1.0) |
| **Consensus** | Общее мнение коллегии, выявленное через кластеризацию embeddings |
| **Emergent Specialization** | Гипотеза о том, что модели коллегии самостоятельно найдут специализацию через reward за уникальность |
| **Gossip Protocol** | Децентрализованный протокол координации без центрального маршрутизатора |
| **Importance Scorer** | Лёгкая нейросеть, оценивающая важность сигнала для конкретного узла |
| **MotorNode** | Исполнительный слой, знающий КАК (tool calls), но не ЧТО (цели) |
| **SSRT** | Stop Signal Reaction Time — время реакции на stop-signal (из нейронауки) |
| **Temporal Summation** | Накопление сигналов во времени перед принятием решения о действии |
| **Vector Protocol** | Межмодульное общение через `inputs_embeds` вместо текста; сжатые проекции (10–50d) вместо полных token sequences |
| **Working Memory** | Общий буфер данных задачи в Redis, стирается после завершения |

---

*Конец Технического Задания. Версия 1.0.*
