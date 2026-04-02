# Arkadia Memory Engine — Architecture Document

> **Version:** 1.0.0  
> **Date:** 2026-04-01  
> **Status:** Draft  
> **Author:** Architecture Team  

---

## Table of Contents

1. [Онтология](#1-онтология)
2. [Схема Neo4j](#2-схема-neo4j)
3. [Memory Engine API](#3-memory-engine-api)
4. [Entity Resolution](#4-entity-resolution)
5. [Retrieval](#5-retrieval)
6. [Decay и архивация](#6-decay-и-архивация)
7. [Multi-tenancy](#7-multi-tenancy)
8. [Интеграция с агентом](#8-интеграция-с-агентом)
9. [Инфраструктура](#9-инфраструктура)
10. [Риски и mitigation](#10-риски-и-mitigation)

---

## 1. Онтология

### 1.1 Типы сущностей (Entity Types)

Фиксированный enum. Расширение — только через миграцию схемы + ревью.

| Enum | Описание | Примеры |
|------|----------|---------|
| `Person` | Человек, известный пользователю | "мама", "Олег из офиса", сам пользователь |
| `Organization` | Компания, команда, сообщество | "Яндекс", "наша команда", "книжный клуб" |
| `Place` | Физическая локация | "дом", "офис на Тверской", "Стамбул" |
| `Project` | Проект, инициатива, задача с границами | "ремонт кухни", "запуск MVP", "диссертация" |
| `Topic` | Тема, область интересов | "machine learning", "вегетарианство", "стоицизм" |
| `Event` | Разовое событие с датой | "собеседование 15 марта", "свадьба Олега" |
| `Preference` | Предпочтение пользователя | "не люблю звонки", "предпочитаю dark mode" |
| `Habit` | Регулярное действие / паттерн | "бегаю по утрам", "читаю перед сном" |
| `Goal` | Цель, намерение | "выучить Go до лета", "похудеть на 5 кг" |
| `Fact` | Атомарный факт, не привязанный к другим типам | "аллергия на арахис", "группа крови II+" |
| `Emotion` | Эмоциональное состояние, зафиксированное в контексте | "тревога перед дедлайном", "радость от оффера" |
| `Artifact` | Цифровой артефакт, упомянутый пользователем | "статья про RAG", "книга Thinking Fast and Slow" |

> **Подводный камень:** Соблазн добавить `Tag`, `Category`, `Note` — не делать. Это размывает онтологию. Если факт не ложится ни в один тип — это `Fact`.

### 1.2 Типы связей (Relation Types)

Связи направленные. Формат: `(source_type) -[RELATION]-> (target_type)`.

| Enum | Source → Target | Описание |
|------|----------------|----------|
| `KNOWS` | Person → Person | Знакомство |
| `WORKS_AT` | Person → Organization | Работает в |
| `MEMBER_OF` | Person → Organization | Участник |
| `LOCATED_IN` | Place → Place, Person → Place, Organization → Place | Находится в |
| `WORKS_ON` | Person → Project | Работает над |
| `INTERESTED_IN` | Person → Topic | Интересуется |
| `ATTENDED` | Person → Event | Посетил |
| `RELATES_TO` | Any → Any | Общая связь (когда специализированной нет) |
| `PART_OF` | Any → Any | Часть чего-то (проект → организация, место → место) |
| `CAUSED_BY` | Emotion → Event, Emotion → Fact | Вызвано чем-то |
| `BLOCKS` | Fact → Goal, Project → Goal | Блокирует достижение |
| `SUPPORTS` | Fact → Goal, Habit → Goal | Способствует достижению |
| `PRECEDES` | Event → Event | Хронологический порядок |
| `CONTRADICTS` | Fact → Fact, Preference → Preference | Противоречит (важно для consistency) |
| `MENTIONED_IN` | Any → Artifact | Упомянуто в артефакте |
| `POSSIBLE_DUPLICATE` | Any → Any (same type) | Возможный дубликат (для ручного мержа) |

> **Подводный камень:** `RELATES_TO` — это escape hatch, не основная связь. Если >20% связей `RELATES_TO` — онтология недостаточна, нужно расширять.

### 1.3 Уровни важности (Importance)

Каждый факт/сущность получает importance при создании. Это **не** оценка LLM — это детерминированные правила.

| Level | Enum | TTL (default) | Правила назначения |
|-------|------|---------------|-------------------|
| 5 | `critical` | ∞ (never decay) | Здоровье, аллергии, хронические болезни, имена детей, day-of-birth |
| 4 | `high` | 365 дней | Работа, ключевые люди, активные цели, текущее место жительства |
| 3 | `medium` | 180 дней | Предпочтения, интересы, активные проекты |
| 2 | `low` | 90 дней | Разовые события, упоминания людей без контекста |
| 1 | `ephemeral` | 30 дней | Настроение, мелкие факты ("сегодня дождь") |

**Правила автоматического повышения importance:**
- Факт упомянут повторно (>= 3 раза) → importance += 1 (max 4)
- Факт связан с `critical` сущностью → min importance = 3
- Пользователь явно сказал "запомни" / "это важно" → importance = 4

**Правила автоматического понижения:**
- Нет упоминаний > TTL → `status = archived` (не удаление!)
- `Goal` с `status = completed` → importance -= 1 через 30 дней

### 1.4 Примеры Cypher запросов по типам

```cypher
// Найти все Person, связанные с пользователем
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity {entity_type: 'Person'})
WHERE e.status = 'active'
RETURN e ORDER BY e.importance DESC, e.updated_at DESC

// Найти все Goal и что их блокирует
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(g:Entity {entity_type: 'Goal', status: 'active'})
OPTIONAL MATCH (blocker)-[:BLOCKS]->(g)
RETURN g.label, g.importance, collect(blocker.label) AS blockers

// Найти Emotion с причиной за последнюю неделю
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(em:Entity {entity_type: 'Emotion'})
WHERE em.observed_at > datetime() - duration('P7D')
OPTIONAL MATCH (em)-[:CAUSED_BY]->(cause)
RETURN em.label, em.observed_at, cause.label AS caused_by
ORDER BY em.observed_at DESC

// Все Preference (никогда не устаревают если importance >= 3)
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(p:Entity {entity_type: 'Preference'})
WHERE p.status = 'active'
RETURN p.label, p.importance, p.observed_at
```

---

## 2. Схема Neo4j

### 2.1 Ноды

#### `UserRoot`
Корневой узел каждого тенанта. Все данные пользователя доступны только через него.

```
(:UserRoot {
  tenant_id: String!,        // UUID, PK — совпадает с user_id в PostgreSQL
  created_at: DateTime!,
  status: String!            // 'active' | 'suspended' | 'deleted'
})
```

#### `Entity`
Основной узел для всех сущностей.

```
(:Entity {
  id: String!,               // UUID
  tenant_id: String!,        // Денормализация для быстрых запросов + безопасности
  entity_type: String!,      // Enum: Person, Organization, Place, ...
  label: String!,            // Каноническое имя ("Мама", "Яндекс")
  aliases: String[],         // Альтернативные имена ["мамуля", "Ирина Петровна"]
  importance: Integer!,      // 1-5
  status: String!,           // 'active' | 'archived' | 'deleted'
  
  // Temporal
  observed_at: DateTime!,    // Когда факт впервые зафиксирован
  updated_at: DateTime!,     // Последнее обновление
  last_mentioned_at: DateTime, // Последнее упоминание пользователем
  mention_count: Integer!,   // Счётчик упоминаний (для importance boost)
  valid_from: DateTime,      // Начало актуальности (null = всегда)
  valid_until: DateTime,     // Конец актуальности (null = до сих пор)
  
  // Content
  summary: String,           // Краткое описание (1-2 предложения)
  source_type: String!,      // 'user_stated' | 'agent_inferred' | 'system'
  source_session_id: String, // ID сессии, в которой создано
  confidence: Float,         // 0.0-1.0, только для agent_inferred
  
  // Soft delete
  deleted_at: DateTime,
  deleted_reason: String
})
```

#### `Observation`
Атомарная единица информации, привязанная к Entity. Один Entity может иметь множество Observations (append-only лог).

```
(:Observation {
  id: String!,               // UUID
  tenant_id: String!,
  content: String!,          // Текст наблюдения ("Сказал что устал от проекта")
  observed_at: DateTime!,    // Когда зафиксировано
  source_type: String!,      // 'user_stated' | 'agent_inferred'
  source_session_id: String,
  importance: Integer!,      // 1-5
  status: String!,           // 'active' | 'archived'
  embedding_id: String       // ID вектора в embedding store (если есть)
})
```

#### `Session`
Метаданные сессии разговора (для трассировки).

```
(:Session {
  id: String!,               // UUID
  tenant_id: String!,
  started_at: DateTime!,
  ended_at: DateTime,
  summary: String,           // Автосаммари сессии (генерируется при закрытии)
  message_count: Integer
})
```

### 2.2 Рёбра (Relationships)

#### UserRoot → Entity: `OWNS`
```
[:OWNS {
  created_at: DateTime!
}]
```

#### Entity → Entity: Онтологические связи
```
[:KNOWS | :WORKS_AT | :MEMBER_OF | ... {
  id: String!,               // UUID
  tenant_id: String!,
  created_at: DateTime!,
  observed_at: DateTime!,    // Когда связь зафиксирована
  valid_from: DateTime,
  valid_until: DateTime,
  source_type: String!,      // 'user_stated' | 'agent_inferred'
  confidence: Float,
  status: String!,           // 'active' | 'archived' | 'deleted'
  context: String            // Контекст ("работает с 2024 года")
}]
```

#### Entity → Observation: `HAS_OBSERVATION`
```
[:HAS_OBSERVATION {
  created_at: DateTime!
}]
```

#### Entity → Session: `MENTIONED_IN_SESSION`
```
[:MENTIONED_IN_SESSION {
  created_at: DateTime!,
  role: String               // 'subject' | 'context' | 'reference'
}]
```

#### Entity → Entity: `POSSIBLE_DUPLICATE`
```
[:POSSIBLE_DUPLICATE {
  id: String!,
  created_at: DateTime!,
  similarity_score: Float!,  // 0.0-1.0
  match_reason: String!,     // 'alias_overlap' | 'name_similarity' | 'context_match'
  resolved: Boolean!,        // false = pending, true = resolved
  resolution: String         // 'merged' | 'distinct' | null
}]
```

### 2.3 Индексы

```cypher
// Основные lookup индексы
CREATE INDEX idx_entity_tenant FOR (e:Entity) ON (e.tenant_id);
CREATE INDEX idx_entity_type FOR (e:Entity) ON (e.entity_type);
CREATE INDEX idx_entity_status FOR (e:Entity) ON (e.status);
CREATE INDEX idx_entity_label FOR (e:Entity) ON (e.label);
CREATE INDEX idx_entity_importance FOR (e:Entity) ON (e.importance);

// Temporal индексы (критичны для retrieval)
CREATE INDEX idx_entity_observed FOR (e:Entity) ON (e.observed_at);
CREATE INDEX idx_entity_updated FOR (e:Entity) ON (e.updated_at);
CREATE INDEX idx_entity_last_mentioned FOR (e:Entity) ON (e.last_mentioned_at);

// Observation индексы
CREATE INDEX idx_obs_tenant FOR (o:Observation) ON (o.tenant_id);
CREATE INDEX idx_obs_observed FOR (o:Observation) ON (o.observed_at);

// Composite индексы (самые частые паттерны запросов)
CREATE INDEX idx_entity_tenant_type FOR (e:Entity) ON (e.tenant_id, e.entity_type);
CREATE INDEX idx_entity_tenant_status FOR (e:Entity) ON (e.tenant_id, e.status);
CREATE INDEX idx_entity_tenant_importance FOR (e:Entity) ON (e.tenant_id, e.importance);

// UserRoot
CREATE INDEX idx_userroot_tenant FOR (u:UserRoot) ON (u.tenant_id);

// Session
CREATE INDEX idx_session_tenant FOR (s:Session) ON (s.tenant_id);

// Full-text search index (для alias matching)
CREATE FULLTEXT INDEX ft_entity_label FOR (e:Entity) ON EACH [e.label];
```

### 2.4 Constraints

```cypher
// Уникальность
CREATE CONSTRAINT uq_userroot_tenant FOR (u:UserRoot) REQUIRE u.tenant_id IS UNIQUE;
CREATE CONSTRAINT uq_entity_id FOR (e:Entity) REQUIRE e.id IS UNIQUE;
CREATE CONSTRAINT uq_observation_id FOR (o:Observation) REQUIRE o.id IS UNIQUE;
CREATE CONSTRAINT uq_session_id FOR (s:Session) REQUIRE s.id IS UNIQUE;

// NOT NULL (Neo4j 5.x+)
CREATE CONSTRAINT nn_entity_tenant FOR (e:Entity) REQUIRE e.tenant_id IS NOT NULL;
CREATE CONSTRAINT nn_entity_type FOR (e:Entity) REQUIRE e.entity_type IS NOT NULL;
CREATE CONSTRAINT nn_entity_label FOR (e:Entity) REQUIRE e.label IS NOT NULL;
CREATE CONSTRAINT nn_entity_status FOR (e:Entity) REQUIRE e.status IS NOT NULL;
CREATE CONSTRAINT nn_entity_importance FOR (e:Entity) REQUIRE e.importance IS NOT NULL;
```

### 2.5 Примеры CREATE/MERGE запросов

```cypher
// Создание UserRoot при регистрации
CREATE (u:UserRoot {
  tenant_id: $tenantId,
  created_at: datetime(),
  status: 'active'
})

// Создание Entity (Person)
MATCH (u:UserRoot {tenant_id: $tenantId})
CREATE (u)-[:OWNS {created_at: datetime()}]->(e:Entity {
  id: $entityId,
  tenant_id: $tenantId,
  entity_type: 'Person',
  label: 'Олег',
  aliases: ['Олежка', 'Олег Петров'],
  importance: 3,
  status: 'active',
  observed_at: datetime(),
  updated_at: datetime(),
  last_mentioned_at: datetime(),
  mention_count: 1,
  summary: 'Коллега по работе, backend разработчик',
  source_type: 'user_stated',
  source_session_id: $sessionId,
  confidence: null
})

// Добавление Observation к Entity
MATCH (e:Entity {id: $entityId, tenant_id: $tenantId})
CREATE (e)-[:HAS_OBSERVATION {created_at: datetime()}]->(o:Observation {
  id: $obsId,
  tenant_id: $tenantId,
  content: 'Олег сказал что переходит в другую компанию',
  observed_at: datetime(),
  source_type: 'user_stated',
  source_session_id: $sessionId,
  importance: 3,
  status: 'active'
})
// Обновить updated_at и last_mentioned_at на Entity
SET e.updated_at = datetime(), e.last_mentioned_at = datetime(),
    e.mention_count = e.mention_count + 1

// Создание связи между Entity
MATCH (e1:Entity {id: $entityId1, tenant_id: $tenantId})
MATCH (e2:Entity {id: $entityId2, tenant_id: $tenantId})
CREATE (e1)-[:WORKS_AT {
  id: $relId,
  tenant_id: $tenantId,
  created_at: datetime(),
  observed_at: datetime(),
  source_type: 'user_stated',
  confidence: null,
  status: 'active',
  context: 'работает с 2024 года, senior developer'
}]->(e2)

// Мягкое удаление
MATCH (e:Entity {id: $entityId, tenant_id: $tenantId})
SET e.status = 'deleted', e.deleted_at = datetime(), e.deleted_reason = 'user_request'
```

---

## 3. Memory Engine API

### 3.1 Интерфейс

Memory Engine — это TypeScript сервис, предоставляющий API как для agentic loop, так и для tool calls.

```typescript
// types.ts

type EntityType = 
  | 'Person' | 'Organization' | 'Place' | 'Project' | 'Topic'
  | 'Event' | 'Preference' | 'Habit' | 'Goal' | 'Fact'
  | 'Emotion' | 'Artifact';

type RelationType = 
  | 'KNOWS' | 'WORKS_AT' | 'MEMBER_OF' | 'LOCATED_IN'
  | 'WORKS_ON' | 'INTERESTED_IN' | 'ATTENDED' | 'RELATES_TO'
  | 'PART_OF' | 'CAUSED_BY' | 'BLOCKS' | 'SUPPORTS'
  | 'PRECEDES' | 'CONTRADICTS' | 'MENTIONED_IN'
  | 'POSSIBLE_DUPLICATE';

type ImportanceLevel = 1 | 2 | 3 | 4 | 5;

type SourceType = 'user_stated' | 'agent_inferred' | 'system';

type EntityStatus = 'active' | 'archived' | 'deleted';

interface Entity {
  id: string;
  tenantId: string;
  entityType: EntityType;
  label: string;
  aliases: string[];
  importance: ImportanceLevel;
  status: EntityStatus;
  observedAt: Date;
  updatedAt: Date;
  lastMentionedAt: Date | null;
  mentionCount: number;
  validFrom: Date | null;
  validUntil: Date | null;
  summary: string | null;
  sourceType: SourceType;
  sourceSessionId: string | null;
  confidence: number | null;
}

interface Observation {
  id: string;
  tenantId: string;
  content: string;
  observedAt: Date;
  sourceType: SourceType;
  sourceSessionId: string | null;
  importance: ImportanceLevel;
  status: EntityStatus;
  embeddingId: string | null;
}

interface Relation {
  id: string;
  tenantId: string;
  type: RelationType;
  sourceEntityId: string;
  targetEntityId: string;
  observedAt: Date;
  validFrom: Date | null;
  validUntil: Date | null;
  sourceType: SourceType;
  confidence: number | null;
  status: EntityStatus;
  context: string | null;
}

// Ошибки
class MemoryEngineError extends Error {
  constructor(
    message: string,
    public code: MemoryErrorCode,
    public details?: Record<string, unknown>
  ) { super(message); }
}

type MemoryErrorCode = 
  | 'TENANT_NOT_FOUND'
  | 'ENTITY_NOT_FOUND' 
  | 'DUPLICATE_ENTITY'
  | 'INVALID_ENTITY_TYPE'
  | 'INVALID_RELATION'
  | 'TENANT_ISOLATION_VIOLATION'
  | 'QUOTA_EXCEEDED'
  | 'NEO4J_UNAVAILABLE';
```

### 3.2 Полный API

```typescript
interface MemoryEngine {
  // === Entity Operations ===
  
  /**
   * Создать новую сущность.
   * 
   * Внутри:
   * 1. Валидация entityType по enum
   * 2. Entity Resolution: поиск дубликатов (см. раздел 4)
   * 3. Если дубликат найден → создание + POSSIBLE_DUPLICATE ребро
   * 4. Если нет → создание Entity + OWNS ребро от UserRoot
   * 5. Автоматическое назначение importance по правилам
   * 
   * Ошибки: TENANT_NOT_FOUND, INVALID_ENTITY_TYPE, QUOTA_EXCEEDED
   */
  createEntity(params: {
    tenantId: string;
    entityType: EntityType;
    label: string;
    aliases?: string[];
    importance?: ImportanceLevel;  // Если не указан — авто
    summary?: string;
    sourceType: SourceType;
    sessionId?: string;
    confidence?: number;
    validFrom?: Date;
    validUntil?: Date;
  }): Promise<{ entity: Entity; possibleDuplicates: Entity[] }>;

  /**
   * Обновить существующую сущность.
   * 
   * Внутри:
   * 1. Проверка tenant_id — ОБЯЗАТЕЛЬНО совпадение
   * 2. Обновление полей (merge, не replace)
   * 3. updated_at = now()
   * 4. Aliases — append, не replace (старые не удаляем)
   * 
   * Ошибки: ENTITY_NOT_FOUND, TENANT_ISOLATION_VIOLATION
   */
  updateEntity(params: {
    tenantId: string;
    entityId: string;
    label?: string;
    aliases?: string[];          // Добавляются к существующим
    importance?: ImportanceLevel;
    summary?: string;
    validFrom?: Date;
    validUntil?: Date;
  }): Promise<Entity>;

  /**
   * Мягкое удаление сущности.
   * 
   * Внутри:
   * 1. status = 'deleted', deleted_at = now()
   * 2. Все связи этой сущности: status = 'archived'
   * 3. Observations остаются (append-only)
   * 
   * Ошибки: ENTITY_NOT_FOUND
   */
  deleteEntity(params: {
    tenantId: string;
    entityId: string;
    reason: string;
  }): Promise<void>;

  /**
   * Получить сущность по ID.
   */
  getEntity(params: {
    tenantId: string;
    entityId: string;
    includeObservations?: boolean;  // default: false
    includeRelations?: boolean;     // default: false
  }): Promise<Entity & {
    observations?: Observation[];
    relations?: Relation[];
  }>;

  /**
   * Поиск сущностей по критериям.
   */
  searchEntities(params: {
    tenantId: string;
    query?: string;              // Full-text search по label + aliases
    entityType?: EntityType;
    importanceMin?: ImportanceLevel;
    status?: EntityStatus;
    limit?: number;              // default: 20, max: 100
    offset?: number;
  }): Promise<{ entities: Entity[]; total: number }>;

  // === Observation Operations ===

  /**
   * Добавить наблюдение к сущности.
   * 
   * Внутри:
   * 1. Создание Observation node
   * 2. HAS_OBSERVATION ребро к Entity
   * 3. Обновление Entity: updated_at, last_mentioned_at, mention_count++
   * 4. Проверка importance boost (mention_count >= 3)
   * 5. Генерация embedding (async, не блокирует)
   * 
   * Ошибки: ENTITY_NOT_FOUND
   */
  addObservation(params: {
    tenantId: string;
    entityId: string;
    content: string;
    importance?: ImportanceLevel;
    sourceType: SourceType;
    sessionId?: string;
  }): Promise<Observation>;

  /**
   * Получить observations для сущности.
   */
  getObservations(params: {
    tenantId: string;
    entityId: string;
    limit?: number;             // default: 50
    since?: Date;
    importanceMin?: ImportanceLevel;
  }): Promise<Observation[]>;

  // === Relation Operations ===

  /**
   * Создать связь между сущностями.
   * 
   * Внутри:
   * 1. Валидация relation type по enum
   * 2. Проверка что обе сущности принадлежат тому же tenant
   * 3. Проверка что связь не дублируется (same type, same direction)
   * 4. Если дубликат → обновление existing (observed_at = now)
   * 5. Если нет → создание нового ребра
   * 
   * Ошибки: ENTITY_NOT_FOUND, INVALID_RELATION, TENANT_ISOLATION_VIOLATION
   */
  createRelation(params: {
    tenantId: string;
    sourceEntityId: string;
    targetEntityId: string;
    relationType: RelationType;
    sourceType: SourceType;
    context?: string;
    confidence?: number;
    validFrom?: Date;
    validUntil?: Date;
  }): Promise<Relation>;

  /**
   * Удалить связь (мягкое удаление).
   */
  deleteRelation(params: {
    tenantId: string;
    relationId: string;
  }): Promise<void>;

  // === Retrieval (read path — LLM-assisted) ===

  /**
   * Основной метод retrieval. Трёхуровневый поиск.
   * 
   * Подробности алгоритма — раздел 5.
   * 
   * Возвращает структурированный контекст для system prompt.
   */
  retrieve(params: {
    tenantId: string;
    query: string;             // Текст запроса пользователя
    sessionId?: string;        // Текущая сессия (для temporal boost)
    maxTokens?: number;        // Бюджет токенов для контекста (default: 2000)
    includeArchived?: boolean; // default: false
  }): Promise<RetrievalResult>;

  /**
   * Получить "профиль" пользователя — top-level snapshot памяти.
   * Используется для формирования начального system prompt.
   */
  getUserProfile(params: {
    tenantId: string;
    maxTokens?: number;        // default: 1500
  }): Promise<UserProfile>;

  // === Session Management ===

  /**
   * Открыть сессию.
   */
  openSession(params: {
    tenantId: string;
  }): Promise<{ sessionId: string }>;

  /**
   * Закрыть сессию с автосаммари.
   * 
   * Внутри: НЕ делает LLM-саммари автоматически.
   * Саммари передаётся агентом (он уже его сгенерировал).
   */
  closeSession(params: {
    tenantId: string;
    sessionId: string;
    summary?: string;
    messageCount?: number;
  }): Promise<void>;

  // === Duplicate Resolution ===

  /**
   * Получить pending дубликаты для ручного разрешения.
   */
  getPendingDuplicates(params: {
    tenantId: string;
    limit?: number;
  }): Promise<DuplicatePair[]>;

  /**
   * Разрешить дубликат: merge или mark as distinct.
   * 
   * При merge:
   * 1. Все observations перемещаются к target entity
   * 2. Все связи перемещаются к target entity
   * 3. Aliases объединяются
   * 4. Source entity: status = 'deleted', reason = 'merged_into:<targetId>'
   * 5. mention_count суммируется
   * 6. importance = max(source, target)
   */
  resolveDuplicate(params: {
    tenantId: string;
    duplicateRelationId: string;
    resolution: 'merge' | 'distinct';
    keepEntityId?: string;      // При merge — какой entity оставить
  }): Promise<void>;

  // === Admin / Maintenance ===

  /**
   * Получить статистику памяти для тенанта.
   */
  getStats(params: {
    tenantId: string;
  }): Promise<MemoryStats>;

  /**
   * Запустить decay процесс для тенанта (обычно вызывается cron-ом).
   */
  runDecay(params: {
    tenantId: string;
    dryRun?: boolean;
  }): Promise<DecayResult>;
}

// Return types

interface RetrievalResult {
  entities: RetrievedEntity[];
  observations: RetrievedObservation[];
  relations: RetrievedRelation[];
  contextText: string;          // Готовый текст для system prompt
  tokenCount: number;           // Примерная оценка токенов
  retrievalMeta: {
    temporalHits: number;
    semanticHits: number;
    graphTraversalHits: number;
    totalCandidates: number;
    prunedCount: number;
  };
}

interface UserProfile {
  coreEntities: Entity[];       // Top importance entities
  recentTopics: Entity[];       // Последние темы разговоров
  activeGoals: Entity[];        // Незавершённые цели
  preferences: Entity[];        // Предпочтения
  contextText: string;          // Готовый текст
  tokenCount: number;
}

interface MemoryStats {
  entityCount: number;
  observationCount: number;
  relationCount: number;
  byType: Record<EntityType, number>;
  byImportance: Record<ImportanceLevel, number>;
  oldestEntity: Date;
  newestEntity: Date;
  pendingDuplicates: number;
}

interface DecayResult {
  archived: number;
  importanceDecreased: number;
  skipped: number;
}

interface DuplicatePair {
  relationId: string;
  entity1: Entity;
  entity2: Entity;
  similarityScore: number;
  matchReason: string;
  createdAt: Date;
}
```

### 3.3 Обработка ошибок

```typescript
// Все методы ОБЯЗАНЫ:
// 1. Проверять tenant_id в КАЖДОМ запросе к Neo4j (WHERE clause)
// 2. Возвращать MemoryEngineError с конкретным кодом
// 3. Логировать ошибки с tenant_id (но БЕЗ содержимого памяти)

// Пример middleware
async function withTenantGuard<T>(
  tenantId: string,
  fn: () => Promise<T>
): Promise<T> {
  // Проверка формата UUID
  if (!isValidUUID(tenantId)) {
    throw new MemoryEngineError(
      'Invalid tenant ID format',
      'TENANT_NOT_FOUND'
    );
  }
  
  // Проверка существования tenant (кэшируется на 5 мин)
  const exists = await tenantCache.getOrFetch(tenantId, async () => {
    const result = await neo4j.run(
      'MATCH (u:UserRoot {tenant_id: $tid}) RETURN u',
      { tid: tenantId }
    );
    return result.records.length > 0;
  });
  
  if (!exists) {
    throw new MemoryEngineError(
      `Tenant ${tenantId} not found`,
      'TENANT_NOT_FOUND'
    );
  }
  
  return fn();
}
```

### 3.4 Примеры использования

```typescript
const engine = new MemoryEngine(neo4jDriver);

// Создание сущности
const { entity, possibleDuplicates } = await engine.createEntity({
  tenantId: 'user-123',
  entityType: 'Person',
  label: 'Олег Петров',
  aliases: ['Олег', 'Олежка'],
  summary: 'Коллега, backend разработчик в Яндексе',
  sourceType: 'user_stated',
  sessionId: 'session-456',
});

if (possibleDuplicates.length > 0) {
  // Не мержим автоматически! Просто информируем.
  console.log(`Found ${possibleDuplicates.length} possible duplicates`);
}

// Добавление наблюдения
await engine.addObservation({
  tenantId: 'user-123',
  entityId: entity.id,
  content: 'Олег перешёл в Сбер на позицию тимлида',
  importance: 3,
  sourceType: 'user_stated',
  sessionId: 'session-789',
});

// Retrieval
const context = await engine.retrieve({
  tenantId: 'user-123',
  query: 'Что там с Олегом на работе?',
  sessionId: 'session-789',
  maxTokens: 2000,
});
// context.contextText → вставляется в system prompt
```

---

## 4. Entity Resolution

### 4.1 Принципы

- **Никакого LLM на критическом пути записи.** Entity resolution — чисто алгоритмический.
- **Never auto-merge.** Если есть подозрение — создаём `POSSIBLE_DUPLICATE` ребро.
- **False negative лучше false positive.** Лучше два узла для одного человека, чем один узел для двух разных.

### 4.2 Пошаговый алгоритм

```
INPUT: CreateEntityParams { tenantId, entityType, label, aliases, ... }

STEP 1: Нормализация
  - normalized_label = lowercase(trim(label))
  - normalized_aliases = aliases.map(a => lowercase(trim(a)))
  - all_names = [normalized_label, ...normalized_aliases]

STEP 2: Exact Match (O(1) с индексом)
  MATCH (e:Entity {tenant_id: $tenantId, entity_type: $entityType})
  WHERE toLower(e.label) = $normalizedLabel AND e.status <> 'deleted'
  RETURN e
  
  → Если найден: НЕ создаём новый. Добавляем observation к существующему.
     Возвращаем { entity: existing, possibleDuplicates: [] }

STEP 3: Alias Match (O(n) по aliases, n обычно < 5)
  MATCH (e:Entity {tenant_id: $tenantId, entity_type: $entityType})
  WHERE e.status <> 'deleted'
    AND any(alias IN e.aliases WHERE toLower(alias) IN $allNames)
  RETURN e
  
  → Если найден: НЕ мержим. Создаём новый + POSSIBLE_DUPLICATE.

STEP 4: Fuzzy Match (Levenshtein distance ≤ 2 для коротких имён, ≤ 3 для длинных)
  MATCH (e:Entity {tenant_id: $tenantId, entity_type: $entityType})
  WHERE e.status <> 'deleted'
  WITH e, apoc.text.levenshteinDistance(toLower(e.label), $normalizedLabel) AS dist
  WHERE dist <= CASE WHEN size($normalizedLabel) <= 6 THEN 2 ELSE 3 END
  RETURN e, dist
  ORDER BY dist ASC
  LIMIT 3
  
  → Если найден (dist > 0): Создаём новый + POSSIBLE_DUPLICATE с similarity_score.

STEP 5: Нет совпадений
  → Создаём новый Entity. Нет POSSIBLE_DUPLICATE.
```

> **Подводный камень:** Levenshtein distance — это не серебряная пуля. "Олег" и "Олеся" — distance 2, но это разные люди. Поэтому fuzzy match ВСЕГДА создаёт `POSSIBLE_DUPLICATE`, никогда не мержит.

### 4.3 Когда создаём новый узел

1. **Exact match не найден** (Step 2 пуст)
2. **Alias match найден** → создаём новый + `POSSIBLE_DUPLICATE` (пусть пользователь решит)
3. **Fuzzy match найден** → создаём новый + `POSSIBLE_DUPLICATE`
4. **Ничего не найдено** → создаём новый

### 4.4 Когда помечаем possible_duplicate

1. Alias overlap (Step 3): `match_reason = 'alias_overlap'`, `similarity_score = 1.0`
2. Fuzzy match (Step 4): `match_reason = 'name_similarity'`, `similarity_score = 1.0 - (dist / max_label_len)`
3. **Никогда** при exact match — это тот же entity, не дубликат

### 4.5 Система aliases

```typescript
// Aliases — append-only. Никогда не удаляем alias.
// Причина: пользователь мог сослаться на "маму" как "Ирина Петровна" 
// один раз, и мы должны помнить это навсегда.

// При updateEntity с новыми aliases:
const currentAliases = entity.aliases;
const newAliases = params.aliases;
const mergedAliases = [...new Set([...currentAliases, ...newAliases])];

// При resolveDuplicate(merge):
const mergedAliases = [...new Set([
  entity1.label,        // label проигравшего entity становится alias
  ...entity1.aliases,
  ...entity2.aliases,
])];
```

### 4.6 Cypher для Entity Resolution

```cypher
// Полный resolution pipeline в одном запросе (для производительности)
MATCH (u:UserRoot {tenant_id: $tenantId})

// Exact match
OPTIONAL MATCH (u)-[:OWNS]->(exact:Entity {entity_type: $entityType})
WHERE toLower(exact.label) = $normalizedLabel AND exact.status <> 'deleted'

// Alias match (если exact не найден)
OPTIONAL MATCH (u)-[:OWNS]->(alias_match:Entity {entity_type: $entityType})
WHERE exact IS NULL
  AND alias_match.status <> 'deleted'
  AND any(a IN alias_match.aliases WHERE toLower(a) IN $allNames)

// Fuzzy match (если ни exact ни alias)
OPTIONAL MATCH (u)-[:OWNS]->(fuzzy:Entity {entity_type: $entityType})
WHERE exact IS NULL AND alias_match IS NULL
  AND fuzzy.status <> 'deleted'
  AND apoc.text.levenshteinDistance(toLower(fuzzy.label), $normalizedLabel) <= 3

RETURN exact, collect(DISTINCT alias_match) AS alias_matches, 
       collect(DISTINCT fuzzy) AS fuzzy_matches
```

---

## 5. Retrieval

### 5.1 Трёхуровневый retrieval

Retrieval вызывается на каждое сообщение пользователя. Задача — собрать релевантный контекст из графа в рамках токен-бюджета.

```
Level 1: Temporal (быстрый, детерминированный)
  → Последние N сущностей по last_mentioned_at
  → Сущности из текущей сессии
  
Level 2: Semantic (средний, keyword + fulltext)
  → Full-text search по query
  → Keyword extraction из query → match по labels/aliases
  
Level 3: Graph Traversal (глубокий, по связям)
  → Для каждого entity из Level 1+2 → traverse 1-2 hop
  → Приоритет: importance DESC, freshness DESC
```

### 5.2 Level 1: Temporal Retrieval

```cypher
// Последние упомянутые сущности (за последние 7 дней)
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
WHERE e.status = 'active'
  AND e.last_mentioned_at > datetime() - duration('P7D')
RETURN e
ORDER BY e.last_mentioned_at DESC
LIMIT 10

// Сущности из текущей сессии
MATCH (e:Entity {tenant_id: $tenantId})-[:MENTIONED_IN_SESSION]->(s:Session {id: $sessionId})
WHERE e.status = 'active'
RETURN e
ORDER BY e.importance DESC
```

### 5.3 Level 2: Semantic Retrieval

```cypher
// Full-text search
CALL db.index.fulltext.queryNodes('ft_entity_label', $query) 
YIELD node, score
WHERE node.tenant_id = $tenantId AND node.status = 'active'
RETURN node AS e, score
ORDER BY score DESC
LIMIT 10

// Keyword match по aliases
UNWIND $keywords AS keyword
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
WHERE e.status = 'active'
  AND (toLower(e.label) CONTAINS keyword 
       OR any(a IN e.aliases WHERE toLower(a) CONTAINS keyword))
RETURN DISTINCT e, e.importance AS imp
ORDER BY imp DESC
LIMIT 10
```

> **Подводный камень:** Full-text index в Neo4j не фильтрует по свойствам ноды. `WHERE node.tenant_id = $tenantId` — ОБЯЗАТЕЛЕН после fulltext query. Без этого — утечка данных между тенантами.

### 5.4 Level 3: Graph Traversal

```cypher
// 1-hop traversal от найденных entity (Level 1 + Level 2)
UNWIND $foundEntityIds AS eid
MATCH (e:Entity {id: eid, tenant_id: $tenantId})-[r]-(neighbor:Entity)
WHERE neighbor.status = 'active'
  AND neighbor.tenant_id = $tenantId  // КРИТИЧНО: tenant guard
  AND type(r) <> 'POSSIBLE_DUPLICATE'
RETURN DISTINCT neighbor, r, 
       neighbor.importance AS imp,
       neighbor.last_mentioned_at AS freshness
ORDER BY imp DESC, freshness DESC
LIMIT 20

// 2-hop traversal (только для high-importance сущностей)
UNWIND $highImportanceEntityIds AS eid
MATCH (e:Entity {id: eid, tenant_id: $tenantId})
      -[r1]-(mid:Entity {tenant_id: $tenantId})
      -[r2]-(far:Entity {tenant_id: $tenantId})
WHERE mid.status = 'active' AND far.status = 'active'
  AND far.importance >= 3
  AND type(r1) <> 'POSSIBLE_DUPLICATE'
  AND type(r2) <> 'POSSIBLE_DUPLICATE'
RETURN DISTINCT far, type(r1) AS via_rel1, mid.label AS via_entity, type(r2) AS via_rel2
ORDER BY far.importance DESC
LIMIT 10
```

### 5.5 Построение System Prompt

```typescript
async function buildContextPrompt(
  tenantId: string,
  retrievalResult: RetrievalResult,
  maxTokens: number = 2000
): Promise<string> {
  const sections: string[] = [];
  let currentTokens = 0;
  
  // 1. Core profile (всегда включается, ~300 tokens)
  const profile = await engine.getUserProfile({ tenantId, maxTokens: 300 });
  sections.push(`## About the user\n${profile.contextText}`);
  currentTokens += profile.tokenCount;
  
  // 2. Active goals (если есть, ~100 tokens)
  if (profile.activeGoals.length > 0) {
    const goalsText = profile.activeGoals
      .map(g => `- ${g.label} (importance: ${g.importance})`)
      .join('\n');
    sections.push(`## Active goals\n${goalsText}`);
    currentTokens += estimateTokens(goalsText);
  }
  
  // 3. Retrieved context (основной блок, remaining budget)
  const remainingBudget = maxTokens - currentTokens;
  const contextParts: string[] = [];
  
  // Сортируем по relevance: importance * freshness_score
  const ranked = rankByRelevance(retrievalResult.entities);
  
  for (const entity of ranked) {
    const entityText = formatEntity(entity);
    const entityTokens = estimateTokens(entityText);
    
    if (currentTokens + entityTokens > maxTokens) break;
    
    contextParts.push(entityText);
    currentTokens += entityTokens;
  }
  
  if (contextParts.length > 0) {
    sections.push(`## Relevant memories\n${contextParts.join('\n\n')}`);
  }
  
  // 4. Preferences (всегда, если вмещаются, ~100 tokens)
  if (currentTokens + 100 < maxTokens) {
    const prefs = retrievalResult.entities
      .filter(e => e.entityType === 'Preference')
      .slice(0, 5);
    if (prefs.length > 0) {
      const prefsText = prefs.map(p => `- ${p.label}`).join('\n');
      sections.push(`## User preferences\n${prefsText}`);
    }
  }
  
  return sections.join('\n\n');
}

function formatEntity(entity: RetrievedEntity): string {
  let text = `**${entity.label}** (${entity.entityType})`;
  if (entity.summary) text += `: ${entity.summary}`;
  
  // Добавляем последние observations (max 3)
  if (entity.observations?.length > 0) {
    const obs = entity.observations.slice(0, 3);
    text += '\n' + obs.map(o => 
      `  - [${formatDate(o.observedAt)}] ${o.content}`
    ).join('\n');
  }
  
  return text;
}
```

### 5.6 Контроль размера контекста

| Компонент | Бюджет (tokens) | Стратегия обрезки |
|-----------|-----------------|-------------------|
| User profile | 300 (fixed) | Top-5 entities by importance |
| Active goals | 100 (flex) | Top-3 goals |
| Retrieved entities | 1200 (flex) | Ranked by relevance score, cut at budget |
| Preferences | 100 (flex) | Top-5 preferences |
| Relations context | 300 (flex) | Only for entities in retrieved set |
| **Total** | **2000** | Hard cap, drop lowest-ranked |

> **Подводный камень:** `estimateTokens` — это приближение (chars / 4 для английского, chars / 2 для кириллицы). Реальный подсчёт через tiktoken слишком медленный для hot path. Делаем с запасом 10%.

---

## 6. Decay и архивация

### 6.1 Двумерная классификация

```
                          source_type
                 user_stated    agent_inferred    system
importance  ┌──────────────┬────────────────┬────────────┐
  5 critical│  NEVER DECAY │  NEVER DECAY   │ NEVER DECAY│
  4 high    │  365 дней    │  180 дней      │ 365 дней   │
  3 medium  │  180 дней    │  90 дней       │ 180 дней   │
  2 low     │  90 дней     │  45 дней       │ 90 дней    │
  1 ephemer │  30 дней     │  14 дней       │ 30 дней    │
            └──────────────┴────────────────┴────────────┘

TTL отсчитывается от max(last_mentioned_at, updated_at).
```

**Ключевое различие:** `agent_inferred` факты decay быстрее, потому что они менее надёжны. Если пользователь ни разу не подтвердил inferred факт — он скорее всего неточный.

### 6.2 Правила

```typescript
interface DecayRule {
  importance: ImportanceLevel;
  sourceType: SourceType;
  ttlDays: number;           // -1 = never
  action: 'archive' | 'importance_decrease';
}

const DECAY_RULES: DecayRule[] = [
  // Critical — никогда
  { importance: 5, sourceType: 'user_stated',    ttlDays: -1,  action: 'archive' },
  { importance: 5, sourceType: 'agent_inferred', ttlDays: -1,  action: 'archive' },
  { importance: 5, sourceType: 'system',         ttlDays: -1,  action: 'archive' },
  
  // High
  { importance: 4, sourceType: 'user_stated',    ttlDays: 365, action: 'importance_decrease' },
  { importance: 4, sourceType: 'agent_inferred', ttlDays: 180, action: 'importance_decrease' },
  { importance: 4, sourceType: 'system',         ttlDays: 365, action: 'importance_decrease' },
  
  // Medium
  { importance: 3, sourceType: 'user_stated',    ttlDays: 180, action: 'importance_decrease' },
  { importance: 3, sourceType: 'agent_inferred', ttlDays: 90,  action: 'importance_decrease' },
  { importance: 3, sourceType: 'system',         ttlDays: 180, action: 'importance_decrease' },
  
  // Low
  { importance: 2, sourceType: 'user_stated',    ttlDays: 90,  action: 'archive' },
  { importance: 2, sourceType: 'agent_inferred', ttlDays: 45,  action: 'archive' },
  { importance: 2, sourceType: 'system',         ttlDays: 90,  action: 'archive' },
  
  // Ephemeral
  { importance: 1, sourceType: 'user_stated',    ttlDays: 30,  action: 'archive' },
  { importance: 1, sourceType: 'agent_inferred', ttlDays: 14,  action: 'archive' },
  { importance: 1, sourceType: 'system',         ttlDays: 30,  action: 'archive' },
];
```

### 6.3 Алгоритм фонового процесса

```typescript
/**
 * Запускается раз в сутки через cron.
 * Обрабатывает по одному tenant за раз (chunked).
 * Batch size: 100 entities за транзакцию.
 */
async function runDecayJob(): Promise<void> {
  const tenants = await getAllActiveTenants();
  
  for (const tenantId of tenants) {
    try {
      await runDecayForTenant(tenantId);
    } catch (err) {
      logger.error('Decay failed for tenant', { tenantId, error: err });
      // Продолжаем с остальными — один tenant не блокирует всех
    }
    
    // Rate limiting: пауза между тенантами
    await sleep(100);
  }
}

async function runDecayForTenant(tenantId: string): Promise<DecayResult> {
  const result: DecayResult = { archived: 0, importanceDecreased: 0, skipped: 0 };
  const now = new Date();
  
  for (const rule of DECAY_RULES) {
    if (rule.ttlDays === -1) continue; // Skip "never decay"
    
    const cutoff = new Date(now.getTime() - rule.ttlDays * 24 * 60 * 60 * 1000);
    
    if (rule.action === 'archive') {
      // Архивация: status → 'archived'
      const cypher = `
        MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
        WHERE e.importance = $importance
          AND e.source_type = $sourceType
          AND e.status = 'active'
          AND coalesce(e.last_mentioned_at, e.updated_at) < $cutoff
        SET e.status = 'archived', e.updated_at = datetime()
        RETURN count(e) AS cnt
      `;
      const res = await neo4j.run(cypher, {
        tenantId, importance: rule.importance,
        sourceType: rule.sourceType, cutoff: cutoff.toISOString()
      });
      result.archived += res.records[0].get('cnt').toNumber();
      
    } else if (rule.action === 'importance_decrease') {
      // Понижение importance на 1
      const cypher = `
        MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
        WHERE e.importance = $importance
          AND e.source_type = $sourceType
          AND e.status = 'active'
          AND coalesce(e.last_mentioned_at, e.updated_at) < $cutoff
        SET e.importance = e.importance - 1, e.updated_at = datetime()
        RETURN count(e) AS cnt
      `;
      const res = await neo4j.run(cypher, {
        tenantId, importance: rule.importance,
        sourceType: rule.sourceType, cutoff: cutoff.toISOString()
      });
      result.importanceDecreased += res.records[0].get('cnt').toNumber();
    }
  }
  
  return result;
}
```

### 6.4 Что никогда не удаляем (даже при архивации)

| Категория | Причина |
|-----------|---------|
| `importance = 5` (critical) | Здоровье, безопасность — жизненно важно |
| `entity_type = 'Fact'` с health-тегом | Медицинская информация бессрочна |
| `UserRoot` node | Структурный якорь |
| `Session` nodes | Аудит, трассируемость |
| Любой node с `status = 'deleted'` | Уже "удалён", keep для аудита |
| `POSSIBLE_DUPLICATE` relations (unresolved) | Нужны для consistency |

> **Подводный камень:** Soft delete + никогда не удаляем физически = граф растёт бесконечно. Решение: отдельный cold storage (export archived nodes раз в квартал в object storage, удалить из Neo4j). Реализовать когда граф > 100K nodes на tenant.

---

## 7. Multi-tenancy

### 7.1 Стратегия изоляции

**Выбрана:** Shared graph с `tenant_id` на каждом node и relationship.

**Почему не отдельная database/instance per tenant:**
- Neo4j Community Edition: 1 database. Enterprise нужна для multi-db.
- Отдельные instances: overhead ~200MB RAM каждый, не масштабируется.
- Shared graph с tenant_id: простая, проверенная, достаточно безопасная при правильной реализации.

**Когда переходить на database-per-tenant:**
- Enterprise лицензия + >1000 платящих пользователей
- Compliance требования (GDPR data residency)
- Отдельные SLA per customer

### 7.2 Реализация tenant isolation

```typescript
// КАЖДЫЙ запрос к Neo4j ОБЯЗАН содержать tenant_id в WHERE clause.
// Это не "хорошая практика" — это архитектурное требование.

// Middleware для Driver (обёртка)
class TenantScopedNeo4j {
  constructor(
    private driver: neo4j.Driver,
    private tenantId: string
  ) {}

  async run(cypher: string, params: Record<string, unknown> = {}): Promise<neo4j.Result> {
    // Валидация: cypher ДОЛЖЕН содержать tenant_id reference
    if (!cypher.includes('tenant_id') && !cypher.includes('$tenantId')) {
      throw new Error(
        'SECURITY: Cypher query must reference tenant_id. ' +
        'This is a mandatory isolation requirement.'
      );
    }
    
    const session = this.driver.session();
    try {
      return await session.run(cypher, { 
        ...params, 
        tenantId: this.tenantId  // Всегда inject
      });
    } finally {
      await session.close();
    }
  }
}
```

### 7.3 Row-level security на уровне графа

```
Architectural Rule:  UserRoot → [:OWNS] → Entity
                     Все Entity ОБЯЗАНЫ иметь [:OWNS] путь к UserRoot

Запрос:              ВСЕГДА начинай с MATCH (u:UserRoot {tenant_id: $tenantId})
                     
Денормализация:      tenant_id дублируется на КАЖДОМ node (Entity, Observation, Session)
                     и на КАЖДОМ relationship для быстрой фильтрации.
                     
Defence in depth:    Даже если забыл MATCH от UserRoot,
                     WHERE e.tenant_id = $tenantId ловит утечку.
```

```cypher
// ПРАВИЛЬНО (двойная защита):
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
WHERE e.tenant_id = $tenantId  // Redundant но защищает от ошибок в traversal
  AND e.status = 'active'
RETURN e

// НЕПРАВИЛЬНО (утечка данных):
MATCH (e:Entity {entity_type: 'Person'})
RETURN e
// ^^^ Это НИКОГДА не должно пройти code review
```

### 7.4 Тесты на isolation

```typescript
describe('Tenant Isolation', () => {
  it('should never return entities from another tenant', async () => {
    // Setup: создаём entity в tenant-A
    await engine.createEntity({
      tenantId: 'tenant-A',
      entityType: 'Person',
      label: 'Secret Person',
      sourceType: 'user_stated',
    });

    // Act: ищем из tenant-B
    const result = await engine.searchEntities({
      tenantId: 'tenant-B',
      query: 'Secret Person',
    });

    // Assert: пусто
    expect(result.entities).toHaveLength(0);
  });

  it('should reject queries without tenant_id', async () => {
    await expect(
      neo4j.run('MATCH (e:Entity) RETURN e LIMIT 1')
    ).rejects.toThrow('SECURITY: Cypher query must reference tenant_id');
  });
});
```

---

## 8. Интеграция с агентом

### 8.1 Agentic Loop

```
┌─────────────────────────────────────────────────────┐
│                    Agent Loop                       │
│                                                     │
│  1. User message arrives                            │
│  2. ──► Memory.retrieve(query=message)              │
│  3. ◄── Retrieved context                           │
│  4. Build system prompt + context                   │
│  5. ──► LLM call (with memory tools available)      │
│  6. ◄── LLM response (possibly with tool calls)     │
│  7. Execute tool calls (memory writes)              │
│  8. Return response to user                         │
│  9. ──► Memory.trackMention(entities mentioned)     │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 8.2 Когда агент ПИШЕТ в память (триггеры)

Memory Engine предоставляет tools, которые LLM вызывает по своему усмотрению. Но триггеры описаны в system prompt.

```typescript
const MEMORY_WRITE_TRIGGERS = `
You have access to memory tools. Use them when:

1. **User shares a fact about themselves or others**
   → memory_create_entity or memory_add_observation
   Examples: "My mom's name is Irina", "I started a new job"

2. **User expresses a preference**
   → memory_create_entity(type='Preference')
   Examples: "I don't like phone calls", "I prefer dark mode"

3. **User mentions a goal**
   → memory_create_entity(type='Goal')
   Examples: "I want to learn Go by summer"

4. **User corrects previously known information**
   → memory_add_observation (new observation, not update)
   Examples: "Actually, Oleg moved to Sber" 

5. **User shares emotional state with context**
   → memory_create_entity(type='Emotion') + CAUSED_BY relation
   Examples: "I'm stressed because of the deadline"

DO NOT write to memory when:
- User is asking a question (read-only)
- User is making small talk without factual content
- Information is purely temporal ("it's raining now")
  unless user explicitly says "remember this"
`;
```

### 8.3 Когда агент ЧИТАЕТ из памяти

```
Автоматически (каждое сообщение):
  - retrieve() → контекст в system prompt
  - getUserProfile() → базовый профиль (кэшируется на 5 мин)

По запросу (tool calls):
  - memory_search → searchEntities()
  - memory_get_entity → getEntity(includeObservations=true)
  - memory_get_related → graph traversal от конкретного entity
```

### 8.4 Tool Definitions для LLM

```typescript
const MEMORY_TOOLS = [
  {
    name: 'memory_create_entity',
    description: 'Create a new entity in user memory (person, place, project, etc.)',
    parameters: {
      type: 'object',
      properties: {
        entity_type: {
          type: 'string',
          enum: ['Person', 'Organization', 'Place', 'Project', 'Topic',
                 'Event', 'Preference', 'Habit', 'Goal', 'Fact', 'Emotion', 'Artifact'],
          description: 'Type of entity to create',
        },
        label: {
          type: 'string',
          description: 'Primary name/label for this entity',
        },
        aliases: {
          type: 'array',
          items: { type: 'string' },
          description: 'Alternative names the user uses for this entity',
        },
        summary: {
          type: 'string',
          description: 'Brief description (1-2 sentences)',
        },
        importance: {
          type: 'integer',
          minimum: 1,
          maximum: 5,
          description: '1=ephemeral, 2=low, 3=medium, 4=high, 5=critical (health/safety)',
        },
        related_to: {
          type: 'object',
          properties: {
            entity_id: { type: 'string' },
            relation_type: {
              type: 'string',
              enum: ['KNOWS', 'WORKS_AT', 'MEMBER_OF', 'LOCATED_IN',
                     'WORKS_ON', 'INTERESTED_IN', 'ATTENDED', 'RELATES_TO',
                     'PART_OF', 'CAUSED_BY', 'BLOCKS', 'SUPPORTS',
                     'PRECEDES', 'CONTRADICTS', 'MENTIONED_IN'],
            },
          },
          description: 'Optional: create a relation to an existing entity',
        },
      },
      required: ['entity_type', 'label'],
    },
  },
  {
    name: 'memory_add_observation',
    description: 'Add a new observation/fact to an existing entity',
    parameters: {
      type: 'object',
      properties: {
        entity_id: {
          type: 'string',
          description: 'ID of the entity to add observation to',
        },
        content: {
          type: 'string',
          description: 'The observation text',
        },
        importance: {
          type: 'integer',
          minimum: 1,
          maximum: 5,
        },
      },
      required: ['entity_id', 'content'],
    },
  },
  {
    name: 'memory_search',
    description: 'Search user memory for entities matching a query',
    parameters: {
      type: 'object',
      properties: {
        query: {
          type: 'string',
          description: 'Search query (name, topic, or keyword)',
        },
        entity_type: {
          type: 'string',
          enum: ['Person', 'Organization', 'Place', 'Project', 'Topic',
                 'Event', 'Preference', 'Habit', 'Goal', 'Fact', 'Emotion', 'Artifact'],
          description: 'Optional: filter by entity type',
        },
        limit: {
          type: 'integer',
          default: 10,
        },
      },
      required: ['query'],
    },
  },
  {
    name: 'memory_create_relation',
    description: 'Create a relationship between two existing entities',
    parameters: {
      type: 'object',
      properties: {
        source_entity_id: { type: 'string' },
        target_entity_id: { type: 'string' },
        relation_type: {
          type: 'string',
          enum: ['KNOWS', 'WORKS_AT', 'MEMBER_OF', 'LOCATED_IN',
                 'WORKS_ON', 'INTERESTED_IN', 'ATTENDED', 'RELATES_TO',
                 'PART_OF', 'CAUSED_BY', 'BLOCKS', 'SUPPORTS',
                 'PRECEDES', 'CONTRADICTS', 'MENTIONED_IN'],
        },
        context: {
          type: 'string',
          description: 'Optional context for the relationship',
        },
      },
      required: ['source_entity_id', 'target_entity_id', 'relation_type'],
    },
  },
];
```

### 8.5 Пример полного цикла

```
User: "Олег сказал что переходит в Сбер. Я за него рад, но буду скучать по нашей команде."

Agent thinking:
1. retrieve("Олег Сбер переход") → находит Entity "Олег" (Person, importance=3)
2. Нужно:
   a. Добавить observation к "Олег" о переходе
   b. Создать entity "Сбер" (Organization) если нет
   c. Создать relation WORKS_AT (Олег → Сбер)
   d. Создать entity "Emotion" (радость за друга + грусть)

Tool calls:
[
  { "name": "memory_add_observation", "arguments": {
    "entity_id": "oleg-uuid",
    "content": "Переходит в Сбер. Пользователь рад за него, но будет скучать.",
    "importance": 3
  }},
  { "name": "memory_create_entity", "arguments": {
    "entity_type": "Organization",
    "label": "Сбер",
    "aliases": ["Сбербанк", "Sber"],
    "summary": "Российский банк и IT-компания",
    "importance": 2
  }},
  { "name": "memory_create_relation", "arguments": {
    "source_entity_id": "oleg-uuid",
    "target_entity_id": "<sber-uuid>",  // from previous call
    "relation_type": "WORKS_AT",
    "context": "Переходит, начало 2026"
  }},
  { "name": "memory_create_entity", "arguments": {
    "entity_type": "Emotion",
    "label": "Радость и грусть из-за ухода Олега",
    "summary": "Рад за Олега (переход в Сбер), но грустит что уходит из команды",
    "importance": 2,
    "related_to": {
      "entity_id": "oleg-uuid",
      "relation_type": "CAUSED_BY"
    }
  }}
]

Agent response: "Записал! Олег переходит в Сбер — хорошие новости для него. 
Понимаю, будет не хватать его в команде. Хочешь, напомню через пару недель 
поинтересоваться, как у него дела на новом месте?"
```

---

## 9. Инфраструктура

### 9.1 Neo4j Deployment

**Рекомендация: Self-hosted Neo4j Community Edition** для старта.

| Вариант | Плюсы | Минусы | Когда |
|---------|-------|--------|-------|
| Self-hosted CE | Бесплатно, полный контроль | Нет multi-db, нет RBAC, ops burden | 0–5K users |
| Neo4j Aura (managed) | Zero ops, auto-backup | Дорого ($65/mo min), vendor lock | 5K+ users, есть деньги |
| Self-hosted EE | Multi-db, clustering, RBAC | Лицензия $$$, ops burden | 10K+ users, compliance |

**Начальная конфигурация:**

```yaml
# docker-compose.yml
services:
  neo4j:
    image: neo4j:5.26-community
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_PLUGINS=["apoc"]
      - NEO4J_server_memory_heap_initial__size=512m
      - NEO4J_server_memory_heap_max__size=1g
      - NEO4J_server_memory_pagecache_size=512m
      - NEO4J_dbms_security_procedures_unrestricted=apoc.*
    volumes:
      - neo4j_data:/data
      - neo4j_backups:/backups
    ports:
      - "7687:7687"   # Bolt
      - "7474:7474"   # Browser (только для dev, закрыть в prod)
    deploy:
      resources:
        limits:
          memory: 2g
          cpus: '2'
    restart: unless-stopped
```

### 9.2 Бэкап стратегия

```bash
#!/bin/bash
# backup_neo4j.sh — запускается cron каждые 6 часов

BACKUP_DIR="/backups/neo4j"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

# Neo4j Community: dump (останавливает БД на время)
# Для zero-downtime: pg_dump + neo4j enterprise online backup
docker exec neo4j neo4j-admin database dump neo4j --to-path=/backups/
mv /var/lib/neo4j/backups/neo4j.dump "${BACKUP_DIR}/neo4j_${DATE}.dump"

# Сжимаем
zstd "${BACKUP_DIR}/neo4j_${DATE}.dump" --rm

# Upload в S3/R2
aws s3 cp "${BACKUP_DIR}/neo4j_${DATE}.dump.zst" \
  "s3://arkadia-backups/neo4j/${DATE}.dump.zst"

# Очистка старых
find "${BACKUP_DIR}" -name "*.dump.zst" -mtime +${RETENTION_DAYS} -delete
```

> **Подводный камень:** `neo4j-admin dump` в Community Edition **останавливает базу**. Для production с SLA нужен онлайн-бэкап (только Enterprise) или реплика для снапшотов.

**Per-tenant export** (для GDPR data portability):

```cypher
// Export все данные одного тенанта в JSON
MATCH (u:UserRoot {tenant_id: $tenantId})-[:OWNS]->(e:Entity)
OPTIONAL MATCH (e)-[:HAS_OBSERVATION]->(o:Observation)
OPTIONAL MATCH (e)-[r]->(target:Entity {tenant_id: $tenantId})
RETURN e, collect(DISTINCT o) AS observations, 
       collect(DISTINCT {type: type(r), target: target.label, context: r.context}) AS relations
```

### 9.3 Мониторинг и observability

```typescript
// Метрики (Prometheus)
const metrics = {
  // Latency
  memory_retrieve_duration_ms: new Histogram({
    name: 'memory_retrieve_duration_ms',
    help: 'Retrieval latency',
    buckets: [10, 25, 50, 100, 250, 500, 1000],
    labelNames: ['level'], // temporal, semantic, graph
  }),
  
  memory_write_duration_ms: new Histogram({
    name: 'memory_write_duration_ms',
    help: 'Write operation latency',
    buckets: [5, 10, 25, 50, 100, 250],
    labelNames: ['operation'], // create_entity, add_observation, create_relation
  }),
  
  // Volume
  memory_entities_total: new Gauge({
    name: 'memory_entities_total',
    help: 'Total entities in graph',
    labelNames: ['entity_type', 'status'],
  }),
  
  memory_observations_total: new Gauge({
    name: 'memory_observations_total',
    help: 'Total observations',
  }),
  
  // Errors
  memory_errors_total: new Counter({
    name: 'memory_errors_total',
    help: 'Memory engine errors',
    labelNames: ['error_code'],
  }),
  
  // Entity resolution
  memory_duplicates_detected: new Counter({
    name: 'memory_duplicates_detected',
    help: 'Possible duplicates detected',
    labelNames: ['match_reason'],
  }),
  
  // Decay
  memory_decay_entities_archived: new Counter({
    name: 'memory_decay_entities_archived',
    help: 'Entities archived by decay',
  }),
};

// Алерты
const ALERTS = {
  // Retrieval > 500ms → warning
  // Retrieval > 1000ms → critical (пользователь ждёт)
  'memory_retrieve_slow': 'memory_retrieve_duration_ms > 500',
  
  // Neo4j connection pool exhausted
  'neo4j_pool_exhausted': 'neo4j_pool_available == 0',
  
  // Graph size approaching limits
  'graph_size_warning': 'memory_entities_total > 50000', // per-tenant
  
  // Decay job failed
  'decay_job_failed': 'last_successful_decay_run > 48h',
};
```

### 9.4 Стоимость

#### 1K пользователей

| Компонент | Спецификация | Стоимость/мес |
|-----------|-------------|---------------|
| Neo4j (self-hosted) | 4 vCPU, 8GB RAM, 100GB SSD | ~$40–60 |
| PostgreSQL | 2 vCPU, 4GB RAM (managed) | ~$30 |
| App servers (2x) | 2 vCPU, 4GB RAM each | ~$40 |
| Object storage (backups) | ~50GB | ~$1 |
| **Total** | | **~$110–130/mo** |

Assumption: ~500 entities/user avg, ~2000 observations/user avg = 500K entities + 2M observations total.

#### 10K пользователей

| Компонент | Спецификация | Стоимость/мес |
|-----------|-------------|---------------|
| Neo4j cluster (self-hosted) | 8 vCPU, 32GB RAM, 500GB SSD + read replica | ~$200–300 |
| PostgreSQL | 4 vCPU, 16GB RAM (managed, HA) | ~$100 |
| App servers (4x) | 4 vCPU, 8GB RAM each | ~$160 |
| Object storage | ~500GB | ~$10 |
| Monitoring (Grafana Cloud) | | ~$50 |
| **Total** | | **~$520–620/mo** |

Assumption: 5M entities + 20M observations. Neo4j может обработать это на одной ноде, но read replica нужна для retrieval без влияния на writes.

> **Подводный камень:** Главная statya расходов — не Neo4j, а LLM API calls. Каждый retrieve() добавляет ~2K tokens в system prompt. При 10K users × 10 msg/day × 2K tokens ≈ 200M tokens/day. Выбор модели для retrieval-augmented generation критичнее выбора базы.

---

## 10. Риски и mitigation

### Risk 1: Tenant Data Leakage

**Severity:** Critical  
**Probability:** Medium (один пропущенный WHERE clause)

**Mitigation:**
1. `TenantScopedNeo4j` wrapper — reject queries без `tenant_id` (compile-time check)
2. Integration tests: каждый API endpoint тестируется на cross-tenant access
3. Quarterly security audit: ревью всех Cypher запросов
4. `tenant_id` денормализован на каждом node — defense in depth
5. Logging: все запросы логируются с tenant_id (без содержимого) для аудита

### Risk 2: Neo4j Performance Degradation

**Severity:** High  
**Probability:** Medium (при росте графа > 10M nodes)

**Mitigation:**
1. **Индексы** — композитные индексы на `(tenant_id, entity_type, status)` покрывают 90% запросов
2. **Query budget** — timeout 5 сек на все запросы, kill slow queries
3. **Read replica** — retrieval с реплики, writes на primary
4. **Sharding by tenant** — готовый план: hash(tenant_id) → partition, миграция в Neo4j Fabric или отдельные instances
5. **Cold storage offloading** — archived entities → S3/object storage quarterly

**Plan B (если Neo4j не справляется):**
- **Шаг 1:** Вертикальное масштабирование (больше RAM, SSD → NVMe)
- **Шаг 2:** Read replicas для retrieval
- **Шаг 3:** Tenant sharding (groups of tenants per instance)
- **Шаг 4:** Миграция на Neo4j Enterprise с clustering
- **Шаг 5 (ядерный):** Переход на MemGraph (compatible Cypher, better performance per core) или ArangoDB (multi-model)

### Risk 3: Entity Resolution False Positives

**Severity:** Medium  
**Probability:** High (имена людей часто совпадают)

**Mitigation:**
1. **Never auto-merge** — архитектурный принцип. Дубликаты лучше, чем неправильные merge.
2. **POSSIBLE_DUPLICATE с UI** — пользователь/агент решают. Фоновый процесс напоминает о pending duplicates.
3. **Context-aware matching** — учитывать не только label, но и связи (два "Олега" в разных компаниях ≠ дубликат)
4. **Undo merge** — при merge source entity не удаляется физически, можно откатить

### Risk 4: Memory Growing Too Large for Context Window

**Severity:** High  
**Probability:** High (у активных пользователей через 6 мес)

**Mitigation:**
1. **Token budget** — жёсткий cap на `maxTokens` в retrieve (default: 2000, max: 4000)
2. **Ranking** — importance × freshness scoring, cut bottom
3. **Summarization** — при >50 observations на entity → LLM summary (background job), старые observations → archived
4. **Hierarchical retrieval** — сначала high-level (entities), потом drill-down по запросу (observations)
5. **User-configurable verbosity** — настройка "how much should I remember in each conversation"

### Risk 5: Data Loss / Corruption

**Severity:** Critical  
**Probability:** Low

**Mitigation:**
1. **Append-only** — физическое удаление запрещено архитектурно
2. **Backups** — каждые 6 часов, 30 дней retention, off-site (S3)
3. **Per-tenant export** — GDPR data portability, можно восстановить отдельного пользователя
4. **Transaction logging** — все write operations логируются в PostgreSQL (audit trail вне Neo4j)
5. **Checksums** — backup integrity verification перед удалением старых бэкапов

### Дополнительный риск: LLM Hallucination в Memory Writes

Хотя LLM не используется для entity resolution (только детерминированный алгоритм), **LLM решает когда вызывать memory tools и с какими параметрами**. Это означает:
- LLM может неправильно категоризировать entity_type
- LLM может записать inference как user_stated
- LLM может пропустить важную информацию

**Mitigation:**
1. `source_type` всегда `agent_inferred` если fact не был явно stated пользователем
2. `confidence` поле для agent_inferred facts
3. Периодический "memory review" — агент предлагает пользователю проверить недавние записи
4. `agent_inferred` facts decay быстрее (см. раздел 6)

---

## Appendix A: Migration Checklist

При расширении онтологии:

```
1. Добавить новый enum в EntityType / RelationType
2. Обновить validation в MemoryEngine
3. Обновить tool definitions для LLM
4. Обновить system prompt triggers
5. Добавить decay rules для нового типа
6. Обновить retrieval ranking (если нужен особый вес)
7. Добавить индексы если нужны
8. Обновить тесты (isolation + CRUD + retrieval)
9. Run migration на всех tenants (background)
10. Update documentation
```

## Appendix B: Glossary

| Термин | Определение |
|--------|-------------|
| Entity | Узел графа, представляющий сущность из жизни пользователя |
| Observation | Атомарный факт, привязанный к Entity (append-only) |
| Relation | Направленная связь между двумя Entity |
| Tenant | Один пользователь SaaS платформы (tenant_id = user_id) |
| Decay | Процесс постепенного уменьшения importance / архивации |
| Retrieval | Процесс извлечения релевантного контекста из графа |
| Entity Resolution | Алгоритм определения, является ли новая сущность дубликатом |
| Source Type | Происхождение факта: сказал пользователь, вывел агент, системное |

---

*End of document. Last updated: 2026-04-01.*
