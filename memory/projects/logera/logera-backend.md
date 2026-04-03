# Logera Backend — Полный справочник

> Ветка: `feature/design-improvements` | Стек: FastAPI + Peewee (async) + PostgreSQL + MinIO + RabbitMQ + OpenSearch + Qdrant + LangGraph
> Дата анализа: 2026-02-14

---

## Содержание

1. [Архитектура](#1-архитектура)
2. [Модели](#2-модели)
3. [API Эндпоинты](#3-api-эндпоинты)
4. [Сервисы](#4-сервисы)
5. [LangGraph Chat Agent](#5-langgraph-chat-agent)
6. [Конфигурация](#6-конфигурация)
7. [Тесты](#7-тесты)

---

## 1. Архитектура

### Общая схема

```
Client → FastAPI (app.py)
            ├── api/endpoints/ (OAuth2, health, webhooks)
            ├── api/routers/ (files, jobs, chat, search, organizations, ...)
            ├── services/ (бизнес-логика)
            │    ├── chat/ (LangGraph agent + tools)
            │    ├── tenant_service.py (multi-tenancy)
            │    ├── storage_service.py (MinIO)
            │    └── amqp_backend_consumer.py (RabbitMQ consumer)
            ├── models/ (Peewee ORM)
            ├── crud/ (CRUD операции)
            └── security/ (org scopes, RBAC)
```

### Multi-tenancy

Два режима (XOR — ровно один из них):
- **org-space**: `org_id NOT NULL`, `owner_user_id NULL` — файлы/данные организации
- **personal-space**: `org_id NULL`, `owner_user_id NOT NULL` — личное пространство пользователя

Все модели данных (FsNode, Transcript, Summary, ActionItem и др.) содержат оба поля для tenant isolation.

### Внешние зависимости

| Сервис | Назначение |
|--------|-----------|
| PostgreSQL | Основная БД (Peewee async) |
| MinIO | Объектное хранилище файлов (buckets: `org-{id}`, `personal`) |
| RabbitMQ | Очередь событий пайплайна обработки медиа |
| OpenSearch | Полнотекстовый поиск по сегментам транскриптов |
| Qdrant | Семантический (vector) поиск |
| Redis | Blacklist токенов (JWT revocation) |
| LiteLLM | Прокси к LLM (для chat agent) |
| OnlyOffice | Редактирование документов в браузере |

---

## 2. Модели

Все модели наследуют `BaseModel` (peewee_async `AioModel` с `AutoField id`).

### 2.1 Organization

**Таблица:** `organization`

| Поле | Тип | Constraints |
|------|-----|------------|
| `id` | AutoField | PK |
| `name` | CharField(255) | NOT NULL |
| `inn` | CharField(12) | NOT NULL, UNIQUE |
| `subdomain` | CharField(63) | NULL, UNIQUE |
| `limit_application_submitted` | BooleanField | default=False |
| `created_at` | DateTimeField | NOT NULL |
| `updated_at` | DateTimeField | NOT NULL |
| `deleted_at` | DateTimeField | NULL (soft delete) |

**Индексы:** `(inn, UNIQUE)`, `(subdomain, UNIQUE)`

### 2.2 User

**Таблица:** `user`

| Поле | Тип | Constraints |
|------|-----|------------|
| `id` | AutoField | PK |
| `email` | CharField | NOT NULL |
| `login` | CharField | NOT NULL |
| `password` | CharField | NOT NULL (hashed) |
| `first_name` | CharField | NULL |
| `last_name` | CharField | NULL |
| `phone` | CharField(32) | NULL |
| `organization` | FK → Organization | NULL (NULL = глобальный) |
| `is_active` | BooleanField | default=True |
| `is_superuser` | BooleanField | default=False |
| `created_at` | DateTimeField | NOT NULL |
| `updated_at` | DateTimeField | NOT NULL |
| `deleted_at` | DateTimeField | NULL |

**Индексы:** `(email, organization) UNIQUE`, `(organization)`

### 2.3 OrgMember

**Таблица:** `org_member`

| Поле | Тип | Constraints |
|------|-----|------------|
| `id` | AutoField | PK |
| `organization` | FK → Organization | NOT NULL |
| `user` | FK → User | NOT NULL, UNIQUE |
| `role` | CharField(16) | default='VIEWER'. Значения: OWNER, ADMIN, EDITOR, VIEWER |
| `created_at` | DateTimeField | NOT NULL |
| `updated_at` | DateTimeField | NOT NULL |
| `deleted_at` | DateTimeField | NULL |

**Индексы:** `(organization, user) UNIQUE`, `(organization)`

### 2.4 OrgGroup

**Таблица:** `org_group`

| Поле | Тип | Constraints |
|------|-----|------------|
| `id` | AutoField | PK |
| `organization` | FK → Organization | NOT NULL |
| `name` | CharField(255) | NOT NULL |
| `description` | TextField | NULL |
| `created_at/updated_at/deleted_at` | DateTimeField | — |

**Индексы:** `(organization, name) UNIQUE`, `(organization)`

### 2.5 OrgGroupMembership

**Таблица:** `org_group_membership`

| Поле | Тип | Constraints |
|------|-----|------------|
| `group` | FK → OrgGroup | NOT NULL |
| `user` | FK → User | NOT NULL |
| `created_at` | DateTimeField | NOT NULL |
| `deleted_at` | DateTimeField | NULL |

**Индексы:** `(group, user) UNIQUE`, `(group)`

### 2.6 OAuthClient

**Таблица:** `oauth_client`

| Поле | Тип | Constraints |
|------|-----|------------|
| `client_id` | CharField(255) | UNIQUE |
| `client_secret` | CharField(255) | NULL (NULL = публичный клиент) |
| `name` | CharField(255) | NOT NULL |
| `description` | TextField | NULL |
| `is_trusted` | BooleanField | default=False |
| `is_active` | BooleanField | default=True |
| `organization` | FK → Organization | NULL (NULL = глобальный) |
| `access_token_lifetime` | IntegerField | default=900 (минуты) |
| `refresh_token_lifetime` | IntegerField | default=2592000 (дни) |
| `allowed_scopes` | TextField | default='["read"]' (JSON) |
| `created_at/updated_at/deleted_at` | DateTimeField | — |

### 2.7 OAuthScope

**Таблица:** `oauth_scope`

| Поле | Тип | Constraints |
|------|-----|------------|
| `name` | CharField(100) | UNIQUE |
| `description` | TextField | NULL |
| `parent_scope` | FK → self | NULL |
| `is_default` | BooleanField | default=False |
| `is_internal` | BooleanField | default=False |
| `created_at` | DateTimeField | — |

### 2.8 UserScope

**Таблица:** `user_scope`

| Поле | Тип | Constraints |
|------|-----|------------|
| `user` | FK → User | NOT NULL |
| `scope` | FK → OAuthScope | NOT NULL |
| `granted_by` | FK → User | NULL |
| `granted_at` | DateTimeField | NOT NULL |
| `expires_at` | DateTimeField | NULL |
| `is_active` | BooleanField | default=True |

**Индексы:** `(user, scope) UNIQUE`

### 2.9 RefreshToken

**Таблица:** `refresh_tokens`

| Поле | Тип | Constraints |
|------|-----|------------|
| `user` | FK → User | NULL (NULL for client_credentials), ON DELETE CASCADE |
| `client` | FK → OAuthClient(client_id) | NOT NULL, ON DELETE CASCADE |
| `token` | TextField | UNIQUE, INDEX |
| `scopes` | TextField | default='read' (CSV) |
| `expires_at` | DateTimeField | NOT NULL |
| `created_at` | DateTimeField | — |
| `is_active` | BooleanField | default=True |
| `revoked_at` | DateTimeField | NULL |
| `ip_address` | CharField(45) | NULL |
| `user_agent` | TextField | NULL |

### 2.10 FsNode

**Таблица:** `fs_node`

| Поле | Тип | Constraints |
|------|-----|------------|
| `organization` | FK → Organization | NULL |
| `owner_user` | FK → User | NULL |
| `parent` | FK → self | NULL (NULL = root) |
| `type` | CharField(10) | 'folder' или 'file' |
| `name` | CharField(255) | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `size` | BigIntegerField | NULL (только для файлов) |
| `mime` | CharField(255) | NULL |
| `current_version` | IntegerField | NULL |
| `created_at/updated_at` | DateTimeField | NOT NULL |
| `deleted_at` | DateTimeField | NULL (soft delete) |

**Индексы:** `(organization, parent, name)`, `(organization)`, `(parent)`, `(owner_user, parent, name)`, `(owner_user)`, `(project_scope_id)`

### 2.11 FsVersion

**Таблица:** `fs_version`

| Поле | Тип | Constraints |
|------|-----|------------|
| `node` | FK → FsNode | ON DELETE CASCADE |
| `version` | IntegerField | NOT NULL |
| `storage_key` | TextField | NOT NULL (ключ в MinIO) |
| `size` | BigIntegerField | NOT NULL |
| `mime` | CharField(255) | NOT NULL |
| `created_at` | DateTimeField | NOT NULL |
| `uploaded_by` | FK → User | NOT NULL |

**Индексы:** `(node, version) UNIQUE`, `(node)`

### 2.12 JobStatus

**Таблица:** `job_status`

| Поле | Тип | Constraints |
|------|-----|------------|
| `job_id` | CharField | UNIQUE, INDEX |
| `org_id` | IntegerField | NULL |
| `owner_user_id` | BigIntegerField | NULL |
| `node_id` | IntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `status` | CharField | default='created'. Значения: created → prepared → dia_ready → asr_ready → link_ready → indexed → error |
| `last_event` | CharField | NULL |
| `payload` | TextField | NULL (raw JSON) |

### 2.13 ProjectScope

**Таблица:** `project_scopes`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL, INDEX |
| `owner_user_id` | BigIntegerField | NULL, INDEX |
| `name` | CharField(255) | NOT NULL |
| `description` | TextField | NULL |
| `created_by_user` | FK → User | NULL |
| `is_archived` | BooleanField | default=False |
| `created_at/updated_at` | DateTimeField | NOT NULL |

**XOR constraint:** ровно один из `org_id`/`owner_user_id` должен быть NOT NULL (проверка в `save()`).

### 2.14 Transcript

**Таблица:** `transcripts`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL |
| `owner_user_id` | BigIntegerField | NULL |
| `node_id` | BigIntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `srt_key` | TextField | NULL (MinIO key) |
| `vtt_key` | TextField | NULL |
| `jsonl_key` | TextField | NULL |
| `created_at` | DateTimeField | — |

**Индексы:** `(org_id, node_id, version) UNIQUE`

### 2.15 TranscriptSegment

**Таблица:** `transcript_segments`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL |
| `owner_user_id` | BigIntegerField | NULL |
| `node_id` | BigIntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `start_ms` | IntegerField | NOT NULL |
| `end_ms` | IntegerField | NOT NULL |
| `text` | TextField | NOT NULL |
| `overlap` | BooleanField | default=False |
| `speaker_id` | BigIntegerField | NULL (FK → SpeakerProfile) |
| `speaker_temp_label` | TextField | NULL |

**Индексы:** `(org_id, node_id, version, start_ms)`

### 2.16 SpeakerProfile

**Таблица:** `speaker_profiles`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL |
| `user_id` | BigIntegerField | NULL |
| `label` | TextField | NULL |
| `name` | TextField | NULL |
| `company` | TextField | NULL |
| `position` | TextField | NULL |
| `total_speech_ms` | IntegerField | default=0 |
| `consent` | BooleanField | default=False |
| `created_at/updated_at` | DateTimeField | — |

**Индексы:** `(org_id, user_id)`

### 2.17 TranscriptSpeaker

**Таблица:** `transcript_speakers`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NOT NULL |
| `node_id` | BigIntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `speaker_id` | BigIntegerField | NOT NULL |
| `total_speech_ms` | IntegerField | default=0 |

**Индексы:** `(org_id, node_id, version, speaker_id) UNIQUE`

### 2.18 Summary

**Таблица:** `summaries`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL |
| `owner_user_id` | BigIntegerField | NULL |
| `node_id` | BigIntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `source` | CharField(16) | default='nlp'. Значения: nlp, manual, import |
| `lang` | CharField(8) | NULL |
| `model_name` | CharField(64) | NULL |
| `model_ver` | CharField(32) | NULL |
| `content_md` | TextField | NOT NULL (markdown) |
| `llm_model` | CharField(64) | NULL |
| `llm_tokens_used` | IntegerField | NULL |
| `llm_latency_ms` | IntegerField | NULL |
| `context_calls_count` | IntegerField | default=0 |
| `created_at` | DateTimeField | — |

**Индексы:** `(org_id, node_id, version, source) UNIQUE`

### 2.19 ActionItem

**Таблица:** `action_items`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id/owner_user_id` | Int/BigInt | tenant isolation |
| `node_id` | BigIntegerField | NOT NULL |
| `version` | IntegerField | NOT NULL |
| `project_scope_id` | BigIntegerField | NULL |
| `title` | TextField | NOT NULL |
| `description` | TextField | NULL |
| `assignee_speaker_id` | BigIntegerField | NULL |
| `assignee_name` | TextField | NULL |
| `due_date` | DateField | NULL |
| `due_date_text` | TextField | NULL (оригинал: "next week") |
| `source_segment_start_ms/end_ms` | IntegerField | NULL |
| `source_text` | TextField | NULL |
| `confidence` | FloatField | default=0.0 |
| `priority` | CharField(16) | NULL. Значения: high, medium, low |
| `relationship_type` | CharField(16) | NULL. Значения: resolves, continues, blocks |
| `related_action_item_id` | BigIntegerField | NULL (self FK) |
| `status` | CharField(16) | default='open'. Значения: open, in_progress, completed, cancelled |
| `status_updated_by` | BigIntegerField | NULL |
| `status_updated_at` | DateTimeField | NULL |
| `created_at/updated_at` | DateTimeField | — |

### 2.20 PersonCandidate

**Таблица:** `person_candidates`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id/owner_user_id` | Int/BigInt | tenant |
| `speaker_profile_id` | BigIntegerField | NOT NULL |
| `extracted_name/company/position` | TextField | NULL |
| `source_node_id` | BigIntegerField | NOT NULL |
| `source_version` | IntegerField | NOT NULL |
| `confidence` | FloatField | default=0.0 |
| `extraction_context` | TextField | NULL (JSON) |
| `status` | CharField(16) | default='pending'. Значения: pending, approved, rejected |
| `resolved_by_user_id` | BigIntegerField | NULL |
| `resolved_at` | DateTimeField | NULL |

### 2.21 PersonNote

**Таблица:** `person_notes`

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id/owner_user_id` | Int/BigInt | tenant |
| `speaker_profile_id` | BigIntegerField | NOT NULL |
| `note_type` | CharField(32) | preference, fact, relationship, history |
| `content` | TextField | NOT NULL |
| `source` | CharField(16) | default='llm_auto'. Значения: llm_auto, user_manual |
| `is_verified` | BooleanField | default=False |
| `source_node_id/version/segment_start_ms` | — | NULL |
| `confidence` | FloatField | default=1.0 |
| `created_by_user_id/verified_by_user_id` | BigIntegerField | NULL |
| `deleted_at` | DateTimeField | NULL (soft delete) |

### 2.22 ContextReference

**Таблица:** `context_references`

Связь summary с контекстными источниками из прошлых звонков.

| Поле | Тип |
|------|-----|
| `summary_id` | BigIntegerField |
| `source_node_id` | BigIntegerField |
| `source_version` | IntegerField |
| `source_segment_start_ms/end_ms` | IntegerField (NULL) |
| `reference_type` | CharField(32): entity_match, semantic_similarity, speaker_history |
| `relevance_score` | FloatField |
| `referenced_text` | TextField (NULL) |
| `speaker_id` | BigIntegerField (NULL) |

### 2.23 Chat Models

#### Conversation (`chat_conversations`)

| Поле | Тип | Constraints |
|------|-----|------------|
| `org_id` | IntegerField | NULL, INDEX |
| `owner_user_id` | BigIntegerField | NULL, INDEX |
| `user` | FK → User | ON DELETE CASCADE |
| `title` | CharField(255) | NULL |
| `project_scope_id` | BigIntegerField | NULL, INDEX |
| `total_tokens_used` | IntegerField | default=0 |
| `created_at/updated_at` | DateTimeField | — |

#### ChatMessage (`chat_messages`)

| Поле | Тип | Constraints |
|------|-----|------------|
| `conversation` | FK → Conversation | ON DELETE CASCADE |
| `role` | CharField(20) | user, assistant, tool |
| `content` | TextField | NOT NULL |
| `tool_calls_json` | TextField | NULL (JSON array) |
| `tool_call_id` | CharField(100) | NULL |
| `tool_name` | CharField(100) | NULL |
| `model` | CharField(100) | NULL |
| `tokens_used` | IntegerField | NULL |
| `created_at` | DateTimeField | — |

#### ChatContextReference (`chat_context_references`)

| Поле | Тип |
|------|-----|
| `message` | FK → ChatMessage (CASCADE) |
| `ref_type` | CharField(20): segment, file, folder, search_result, wiki, text |
| `node_id` | IntegerField (NULL) |
| `start_ms/end_ms/speaker_id` | IntegerField (NULL) |
| `label` | CharField(255) (NULL) |
| `text_snippet` | TextField (NULL) |
| `tokens` | IntegerField (NULL) |

---

## 3. API Эндпоинты

### Префикс: `/api`

### 3.1 OAuth2 (`/api/oauth2/...`)

| Method | Path | Описание | Auth |
|--------|------|----------|------|
| POST | `/oauth2/token` | Получение токенов (password, client_credentials, refresh_token grant) | Client ID |
| POST | `/oauth2/register` | Регистрация пользователя | Client ID |
| POST | `/oauth2/register-organisation` | Регистрация организации + админа + OAuth клиента | No auth |
| POST | `/oauth2/register-org-user` | Регистрация пользователя в организации | Client auth |
| POST | `/oauth2/revoke` | Отзыв токена (RFC 7009) | Token |
| POST | `/oauth2/introspect` | Интроспекция токена (RFC 7662) | Client auth |
| GET | `/oauth2/userinfo` | Информация о текущем пользователе | Bearer token |
| GET | `/oauth2/me` | Профиль + организация + лимиты | Bearer token |
| POST | `/oauth2/logout` | Выход (отзыв токена + clear cookies) | Bearer token |
| GET | `/oauth2/.well-known/openid-configuration` | OpenID Connect Discovery | No auth |

### 3.2 Files (`/api/files/...`)

| Method | Path | Описание | Auth Scopes |
|--------|------|----------|-------------|
| GET | `/files` | Список файлов/папок (query: `parent_id`) | org:members:read |
| GET | `/files/{node_id}` | Метаданные файла/папки | org:members:read |
| POST | `/files/folders` | Создание папки (Form: `name`, `parent_id`) | org:settings:write |
| POST | `/files/upload` | Загрузка файлов (multipart, поддержка `paths[]` для дерева) | org:settings:write |
| PATCH | `/files/{node_id}/rename` | Переименование (Form: `name`) | org:settings:write |
| PATCH | `/files/{node_id}/move` | Перемещение (Form: `target_parent_id`) | org:settings:write |
| DELETE | `/files/{node_id}` | Удаление (query: `hard=true` для жёсткого) | org:settings:write |
| GET | `/files/{node_id}/download` | Скачивание файла (прокси MinIO, поддержка Range) | org:members:read |
| GET | `/files/{node_id}/media-token` | Получение JWT media token для стриминга | org:members:read |
| GET | `/files/{node_id}/stream` | Стриминг по media token (для `<video>`/`<audio>`) | media token |
| GET | `/files/{node_id}/export` | Экспорт (md→pdf/docx через pypandoc) | org:members:read |
| GET | `/files/{node_id}/versions` | Список версий файла | org:members:read |
| POST | `/files/{node_id}/upload-version` | Загрузка новой версии | org:settings:write |
| POST | `/files/attachments` | Загрузка вложения (возвращает URL) | org:settings:write |
| POST | `/files/{node_id}/restore` | Восстановление версии (Form: `version`) | org:settings:write |
| PATCH | `/files/{node_id}/project-scope` | Привязка к ProjectScope | org:settings:write |

**Авто-обработка:** При загрузке audio/video автоматически создаётся Job через AMQP (`create_job_and_publish`).

### 3.3 Jobs (`/api/v1/jobs/...`)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/v1/jobs` | Список jobs (query: `status`, `org_id`, `limit`, `offset`) |
| GET | `/v1/jobs/{job_id}` | Получить job по ID |
| GET | `/v1/jobs/by-node/{node_id}` | Последний job для файла (query: `version`) |
| GET | `/v1/jobs/{job_id}/events` | SSE-стрим событий job (EventBus + heartbeat) |

### 3.4 Search (`/api/v1/search/...`)

Полнотекстовый и семантический поиск (через OpenSearch и Qdrant).

### 3.5 Chat (`/api/v1/chat/...`)

| Method | Path | Описание |
|--------|------|----------|
| POST | `/v1/chat/conversations` | Создать conversation (body: `title?`, `project_scope_id?`) |
| POST | `/v1/chat/conversations/{id}/messages/stream` | Отправить сообщение → SSE-стрим ответа |
| GET | `/v1/chat/conversations/{id}` | Conversation + история сообщений |
| GET | `/v1/chat/conversations` | Список conversations (query: `project_scope_id`, `limit`, `offset`) |
| DELETE | `/v1/chat/conversations/{id}` | Удалить conversation (CASCADE messages + refs) |

**SSE события стрима:**
- `token` — токен ответа
- `tool_call` — вызов инструмента
- `tool_result` — результат инструмента
- `edit_command` — команда редактирования документа (OnlyOffice)
- `read_structure_request` — запрос чтения структуры документа
- `user_input_request` — запрос ввода от пользователя (HITL)
- `frontend_execution_request` — запрос выполнения JS на фронте
- `done` — завершение
- `error` — ошибка

**Request body `SendMessageRequest`:**
```json
{
  "content": "текст сообщения",
  "context_items": [{"type": "file", "id": "1", "label": "...", "node_id": 1, "text": "..."}],
  "active_document_id": 42  // опционально, включает инструменты редактирования
}
```

### 3.6 Action Items (`/api/v1/action-items/...`)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/v1/action-items` | Список (query: `node_id`, `status`, `assignee_speaker_id`, `limit`, `offset`) |
| GET | `/v1/action-items/{id}` | Один action item |
| PATCH | `/v1/action-items/{id}` | Обновление (body: `status`, `assignee_name`, `priority`) |

### 3.7 Person Notes (`/api/v1/person-notes/...`)

CRUD для заметок о людях (спикерах).

### 3.8 Person Candidates (`/api/v1/person-candidates/...`)

CRUD для кандидатов на идентификацию спикеров.

### 3.9 Organizations (`/api/v1/organizations/...`)

CRUD организаций, резолв по субдомену.

### 3.10 Org Members (`/api/v1/org-members/...`)

Управление участниками: list, add, update role, remove, list pending.

### 3.11 Org Groups (`/api/v1/org-groups/...`)

CRUD групп внутри организации.

### 3.12 Org Clients (`/api/v1/org-clients/...`)

Управление OAuth-клиентами организации: list, create, rotate secret, delete.

### 3.13 Projects (`/api/v1/projects/...`)

CRUD проектных scope'ов (ProjectScope).

### 3.14 OnlyOffice (`/api/onlyoffice/...`)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/onlyoffice/config/{file_id}` | Конфигурация редактора (JWT-подписанная) |
| POST | `/onlyoffice/callback` | Callback от OnlyOffice при сохранении |
| GET | `/onlyoffice/file/{file_id}` | Отдача файла OnlyOffice серверу (auth через media token) |
| GET | `/onlyoffice/health` | Проверка интеграции |

### 3.15 Media Chunks (`/api/media/...`)

| Method | Path | Описание |
|--------|------|----------|
| GET | `/media/{node_id}/chunk` | Аудио-фрагмент по start/end (секунды) |
| GET | `/media/{node_id}/segment/{id}/audio` | Аудио для конкретного сегмента |

### 3.16 Health & Webhooks

| Method | Path | Описание |
|--------|------|----------|
| GET | `/health` | Health check |
| POST | `/webhooks/...` | Webhooks |

---

## 4. Сервисы

### 4.1 `oauth_authorization_server.py` — OAuth2AuthorizationServer

**Singleton:** `oauth_server`

Полноценный OAuth2 Authorization Server (RFC 6749, 7009, 7662).

**Методы:**
- `authenticate_client(client_id, client_secret?)` → OAuthClient
- `get_default_client()` → default_web_client (публичный, trusted)
- `init_default_external_client()` — из ENV
- `password_grant(username, password, client, scopes)` → tokens
- `client_credentials_grant(client, scopes)` → tokens
- `refresh_token_grant(refresh_token, client, scopes?)` → new tokens
- `create_user_tokens(user_id, client, scopes, grant_type)` → tokens
- `validate_scopes(requested, client, user?)` → filtered scopes
- `verify_token(token, audience?, token_type?)` → payload
- `revoke_token(token, client_id)` — blacklist via Redis
- `introspect_token(token, client_id)` → RFC 7662 response

**JWT payload:**
```json
{
  "sub": "user_id или client_id",
  "aud": "client_id",
  "scopes": ["read", "write"],
  "token_type": "bearer",
  "org_id": 1,
  "iat": ..., "exp": ..., "jti": "..."
}
```

### 4.2 `resource_server.py` — ResourceServer

**Singleton:** `resource_server`

Защита API endpoints. FastAPI dependencies:
- `get_token_payload` — извлечение + валидация access token
- `get_current_user` — User из токена
- `get_current_client` — OAuthClient из токена
- `require_user_context_with_organization` — User + Organization + лимиты
- `require_scopes_dependency(scopes)` — проверка scopes

### 4.3 `tenant_service.py` — Tenant Resolution

**Функции:**
- `resolve_tenant_context(node_id)` → `TenantContext(org_id, owner_user_id, node_id, folder_id)`
- `resolve_effective_project_scope_id(node_id)` → int|None (recursive CTE по предкам)
- `validate_scope_tenant_match(ctx, scope_org, scope_owner)` — проверка совпадения

### 4.4 `storage_service.py` — StorageService

**Singleton:** `storage_service`

Обёртка MinIO:
- `resolve_bucket(org_id)` → `org-{id}` или `personal`
- `upload_file(org_id, key, bytes, mime, metadata?)`
- `delete_file(org_id, key)`
- `get_file_stream(org_id, key, range_headers?)`
- `get_file_stat(org_id, key)`
- `get_presigned_url(org_id, key, expires?)`
- `list_files(org_id)`

### 4.5 `orchestrator_service.py` — Job Creation

- `should_autostart(mime)` — проверка по whitelist (audio/*, video/*)
- `create_job_and_publish(org_id, node_id, version, storage_key, mime, ...)` — создаёт JobStatus + публикует `job.created` в AMQP

### 4.6 `amqp_backend_consumer.py` — AMQP Consumer

**Routing keys:** `media.prepared`, `dia.ready`, `asr.ready`, `link.ready`, `indexed.ready`, `nlp.ready`

**Обработка событий:**
- `asr.ready` → `_persist_asr_ready` — сохранение TranscriptSegment из JSONL в MinIO, восстановление speaker_id
- `link.ready` → `_persist_link_ready` → `_apply_speaker_link` — линковка спикеров (SpeakerProfile, TranscriptSpeaker), обновление OpenSearch
- `indexed.ready` → `_persist_indexed_ready` — обновление ключей экспорта (srt, vtt, jsonl)
- `nlp.ready` → `_persist_nlp_ready` — Summary + ActionItems + PersonCandidates + PersonNotes (event_version≥2)

Все события обновляют `JobStatus` и публикуют в `EventBus` для SSE.

### 4.7 `event_bus.py` — In-Memory Event Bus

Async pub/sub для SSE стриминга job events.
- `publish(topic, message)` — non-blocking, drop if queue full (100)
- `subscribe(topic)` → AsyncIterator

### 4.8 `opensearch_service.py`

- `index_name(org_id?, owner_user_id?)` → `asr_segments-org{id}` или `asr_segments-personal-u{id}`
- `ensure_index_exists(...)` — создаёт индекс с маппингом
- `update_speaker_name_across_files(...)` — update_by_query

### 4.9 `organization_service.py` / `org_service.py`

CRUD для организаций: create, get, list_active, update, delete, resolve_by_subdomain.

### 4.10 `org_members_service.py`

- `list_members(org_id)` — JOIN с User
- `add_member`, `update_role`, `remove_member` (soft delete)
- `list_pending_users` — неактивные пользователи организации

### 4.11 `org_groups_service.py`

CRUD для групп: list, create, update, delete (soft).

### 4.12 `org_clients_service.py`

Управление OAuth-клиентами организации: list, create, rotate_secret, delete.

### 4.13 `registration_service.py`

- `register_org_user(client, form)` — создание пользователя в организации + токены
- `register_organization(org_data, admin_data, ...)` — полная регистрация: Organization + OAuthClient + Admin User + OrgMember(OWNER) + scopes + токены

### 4.14 `email_service.py`

FastAPI-Mail: `send_email(to, subject, template_name, template_body)`. Шаблоны в `templates/emails/`.

### 4.15 `llm_document_service.py`

Редактирование документов с Track Changes:
- `edit_markdown(original, instructions, llm_response)` → modified markdown
- `edit_docx(content_bytes, changes, author)` → DOCX с revision marks
- `edit_xlsx(content_bytes, changes, author)` → XLSX с highlighting
- `extract_text_from_docx(bytes)` → plain text
- `extract_data_from_xlsx(bytes)` → dict sheets

---

## 5. LangGraph Chat Agent

### 5.1 Архитектура

```
User Message → LangGraphChatAgent.process_message_stream()
    → Load history from DB
    → Build state (ChatAgentState)
    → get_chat_graph().astream(state)
        → agent node (call_model) ──→ should_continue?
            ├── "tools" → ToolNode → [process_edits] → agent
            └── "end" → END
    → Yield SSE events
    → Save to DB
```

### 5.2 State (`state.py`)

**`ChatAgentState` (TypedDict):**
- `messages: Annotated[list[BaseMessage], add_messages]` — история с автослиянием
- `user_context: dict` — `{user_id, org_id, owner_user_id}`
- `conversation_id: int`
- `context_items: list[dict]` — прикреплённые контексты
- `active_document_id: int?` — ID открытого документа (включает editing tools)
- `pending_edit_commands: list[dict]`
- `iteration_count: int` / `max_iterations: int` (default=10)
- `final_response: str?` / `error: str?`

**`UserContext` (dataclass):** user_id, org_id?, owner_user_id?
**`ContextItem` (dataclass):** type, id, label, node_id?, tokens?, text?

### 5.3 Graph (`graph.py`)

**Ноды:**
1. **`agent`** (`call_model`) — вызов LLM через ChatOpenAI (LiteLLM proxy), привязка tools
2. **`tools`** (`ToolNode` из langgraph.prebuilt) — выполнение инструментов
3. **`process_edits`** (опционально, если `include_document_editing`) — извлечение edit commands из tool results

**Edges:**
- `agent` → conditional: если `tool_calls` → `tools`, иначе → `END`
- `tools` → `process_edits` → `agent` (с editing)
- `tools` → `agent` (без editing)

**LLM:**
```python
ChatOpenAI(
    model=env.CHAT_LLM_MODEL (default "gpt-4o-mini"),
    openai_api_key=env.LITELLM_API_KEY,
    openai_api_base=env.LITELLM_BASE_URL,
    temperature=0.3,
    max_tokens=4096,
    streaming=True,
    request_timeout=300,
)
```

**Singleton:** `get_chat_graph(include_document_editing=False)` — кеширует compiled graph.

### 5.4 System Prompt

**Базовый:**
```
Ты — интеллектуальный ассистент для работы с записями встреч и документами.
- Поиск по файлам и транскриптам (semantic_search, full_text_search)
- Чтение саммари и транскриптов (read_file_content)
- Action items (get_action_items)
- Спикеры (get_speaker_info)
- Редактирование документов (edit_document, read_document_structure)
- Вопросы пользователю (ask_user)
```

**Дополнение при `active_document_id`:** Детальные инструкции по редактированию через OnlyOffice:
- `read_document_structure` — чтение через JS API
- `edit_document` — вставка/замена/удаление через executeMethod API
- Позиционирование через `after_text`
- Workflow: read → find position → edit

### 5.5 Tools (`langgraph_tools.py`)

Все tools — `@tool`-декорированные async функции с Pydantic input schemas.

#### `semantic_search`
- **Input:** `query: str`, `content_types?: list[str]`, `file_types?: list[str]`, `node_ids?: list[int]`, `limit: int (1-20)`
- **Backend:** Qdrant vector search через `logera_common.text_embeddings`
- **Access control:** фильтрация по accessible nodes

#### `full_text_search`
- **Input:** `text: str`, `speaker_name?: str`, `node_id?: int`, `limit: int (1-20)`
- **Backend:** OpenSearch `match` query

#### `read_file_content`
- **Input:** `node_id: int`, `content_type: str` ('summary'|'transcript'|'full'), `start_ms?`, `end_ms?`
- summary → Summary.content_md
- transcript → TranscriptSegment (ordered by start_ms, limit 100)
- full → OnlyOffice conversion → markdown, fallback python-docx/openpyxl/pypdf

#### `get_action_items`
- **Input:** `node_id?: int`, `assignee?: str`, `status: str` ('open'|'in_progress'|'completed'|'all'), `limit: int (1-50)`

#### `get_speaker_info`
- **Input:** `name: str`, `speaker_id?: int`
- Returns: SpeakerProfile + PersonNotes

#### `edit_document`
- **Input:** `action: str`, `params: dict`, `description: str`
- **Actions:** insert_heading, insert_paragraph, insert_list, insert_table, insert_text, replace_text, delete_section, delete_paragraph
- **Output:** JSON command для frontend (executeMethod API): `{method, html/text/search/replace, position, execute_on_frontend: true}`

#### `read_document_structure`
- **Input:** `include_formatting?: bool`, `include_charts?: bool`
- **Output:** JS code для OnlyOffice Connector, `requires_frontend_execution: true`
- Frontend выполняет JS → отправляет результат как новое сообщение

#### `ask_user` (Human-in-the-Loop)
- **Input:** `question: str`, `options?: list[str]`, `context?: str`
- **Output:** `{requires_user_input: true, question, options, context}`

### 5.6 Tool Executor (`tool_executor.py`)

**`ToolExecutor(user_ctx: UserContext)`**

Выполняет tools с tenant isolation:
- `_get_accessible_nodes()` — lazy load всех доступных node_id
- `_filter_node_ids()` — фильтрация по доступу
- `_check_node_access()` — проверка доступа к конкретному node

Поддержка чтения документов:
- `_convert_via_onlyoffice()` — конвертация через OnlyOffice Conversion API → HTML → Markdown
- `_extract_docx_text()` — python-docx с сохранением структуры (headings, lists, tables)
- `_extract_xlsx_data()` — openpyxl → Markdown tables
- `_extract_pdf_text()` — pypdf
- `_html_to_markdown()` — конвертация HTML (headings, bold/italic, lists, tables)

### 5.7 Document Editor (`document_editor.py`)

Генерация Office JS API кода и executeMethod команд.

**Два API:**

1. **Legacy (callCommand):** `generate_office_js_code(action, params)` → JS string
2. **New (executeMethod):** `generate_edit_command(action, params)` → `{method, html/text/search/replace, position}`

**Поддерживаемые действия:**
- `insert_text/paragraph/heading/list/table/chart`
- `replace_text` (SearchAndReplace)
- `delete_section` (от заголовка до следующего)
- `delete_paragraph`
- `format_selection` (bold, italic, underline, font, color)
- `insert_page_break/horizontal_line`
- `set_paragraph_spacing`

**Чтение структуры:**
- `generate_read_document_structure_code()` — JS для Word/PowerPoint
- `generate_read_spreadsheet_structure_code()` — JS для Excel

### 5.8 Legacy Agent (`agent.py`)

Manual agentic loop (до LangGraph). Сохранён для backward compatibility:
- `ChatAgent.process_message_stream()` — до 15 итераций
- Direct httpx streaming к LiteLLM

### 5.9 LLM Client (`llm_client.py`)

Low-level streaming client:
- `ChatLLMClient.chat_stream()` → AsyncGenerator[StreamChunk]
- `ChatLLMClient.chat()` → ChatResponse
- SSE parsing, tool call accumulation
- Env: `LITELLM_BASE_URL`, `LITELLM_API_KEY`, `CHAT_LLM_MODEL`

---

## 6. Конфигурация

### 6.1 Config (`config.py`)

Pydantic BaseSettings, загрузка из `.env`.

| Переменная | Default | Описание |
|-----------|---------|----------|
| `PROJECT_NAME` | "FastAPI OAuth Server" | — |
| `APP_MODE` | "development" | development/production |
| `DEBUG` | True | — |
| `LOG_LEVEL` | "INFO" | — |
| **PostgreSQL** | | |
| `POSTGRES_HOST/PORT/USER/PASSWORD/DB` | localhost:5432/postgres/postgres/oauth_server | — |
| **Redis** | | |
| `REDIS_HOST/PORT/DB` | localhost:6379/0 | Token blacklist |
| **MinIO** | | |
| `MINIO_ENDPOINT/ACCESS_KEY/SECRET_KEY/SECURE` | minio:9000/minioadmin/minioadmin/False | — |
| **JWT** | | |
| `JWT_SECRET_KEY` | "your-secret-key..." | MUST change in production |
| `JWT_ALGORITHM` | "HS256" | — |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | 30 | — |
| **CORS** | | |
| `CORS_ORIGINS` | "http://localhost:3000,...,https://*.logera.space" | CSV |
| `CORS_ORIGIN_REGEX` | `https://.*\\.logera\\.space` | — |
| **OAuth** | | |
| `DEFAULT_EXTERNAL_CLIENT_ID/SECRET` | — | External integration client |
| **Email** | | |
| `MAIL_USERNAME/PASSWORD/FROM/PORT/SERVER` | — | SMTP settings |
| **AMQP** | | |
| `AMQP_URL` | amqp://guest:guest@rabbitmq:5672/ | — |
| `AMQP_EXCHANGE_MAIN` | "logera.jobs" | — |
| **Media** | | |
| `AUTO_START_JOBS_ON_UPLOAD` | True | Auto-process audio/video |
| `REPROCESS_ON_NEW_VERSION` | False | — |
| `MEDIA_MIME_WHITELIST` | ["audio/", "video/"] | — |
| `MAX_FILE_SIZE_MB` | 5000 | — |
| **OnlyOffice** | | |
| `ONLYOFFICE_JWT_SECRET` | "logera-onlyoffice-secret" | — |
| `ONLYOFFICE_URL` | "/onlyoffice" | — |
| `INTERNAL_BACKEND_URL` | "http://web:8000" | Docker internal |
| **LLM (Chat)** | | |
| `CHAT_LLM_MODEL` / `LLM_MODEL` | "gpt-4o-mini" | — |
| `LITELLM_API_KEY` | "sk-1234" | — |
| `LITELLM_BASE_URL` | "http://litellm:4000" | — |
| `CHAT_LLM_TIMEOUT_SEC` | 120 | — |

### 6.2 Database (`db.py`)

```python
db = PooledPostgresqlDatabase(max_connections=20)
```

`BaseModel` добавляет:
- `aio_get_by_id(pk)` — raises ModelNotFoundError
- `aio_get_by_id_or_none(pk)` — returns None

### 6.3 Миграции

Используется `peewee-migrate`. Файлы в `migrations/`:

| Файл | Описание |
|------|----------|
| `001_init.py` | Все основные таблицы: Organization, User, FsNode, FsVersion, JobStatus, OAuthClient, OAuthScope, OrgGroup, OrgGroupMembership, OrgMember, ProjectScope, RefreshToken, SpeakerProfile, TranscriptSpeaker, Summary, Transcript, TranscriptSegment, ActionItem, PersonCandidate, PersonNote, ContextReference, UserScope |
| `002_auto.py` | Автоматические изменения |
| `003_chat.py` | Chat models: Conversation, ChatMessage, ChatContextReference |

**Запуск:** `python migrate.py migrate`

### 6.4 Security — Org Scopes

```python
ORG_SCOPES = {
    "ORG_MEMBERS_READ": "org:members:read",
    "ORG_MEMBERS_WRITE": "org:members:write",
    "ORG_GROUPS_READ": "org:groups:read",
    "ORG_GROUPS_WRITE": "org:groups:write",
    "ORG_CLIENTS_MANAGE": "org:clients:manage",
    "ORG_SETTINGS_WRITE": "org:settings:write",
}

ROLE_TO_SCOPES = {
    "OWNER": [все],
    "ADMIN": [все],
    "EDITOR": [members:read, groups:read],
    "VIEWER": [members:read],
}
```

---

## 7. Тесты

### Расположение: `tests/`

**Conftest:** `create_test_app()` без lifespan, TestClient. Fixtures: `valid_user_data`, `invalid_user_data`.

### Покрытие:

| Файл | Что тестирует |
|------|--------------|
| `test_tenant_isolation.py` | Tenant isolation (cross-org access denied) |
| `test_search_leaks.py` | Поиск не утекает между tenant'ами |
| `test_files.py` | CRUD файлов |
| **OAuth2:** | |
| `test_password_grant.py` | Password grant flow |
| `test_client_credentials.py` | Client credentials flow |
| `test_refresh.py` | Refresh token flow |
| `test_errors.py` | Error handling в token endpoint |
| `test_register.py` | Регистрация пользователя |
| `test_register_organisation.py` | Регистрация организации |
| `test_register_org_user.py` | Регистрация пользователя в организации |
| `test_revoke.py` | Revocation (RFC 7009) |
| `test_introspect.py` | Introspection (RFC 7662) |
| `test_well_known.py` | OpenID Connect Discovery |
| `test_userinfo.py` | /userinfo endpoint |
| `test_me.py` | /me endpoint |
| `test_logout.py` | Logout flow |

### Что НЕ покрыто тестами:

- Chat agent (LangGraph flow, tools execution, SSE streaming)
- OnlyOffice integration (config generation, callback handling)
- AMQP consumer (event processing, speaker linking)
- Media chunks (audio extraction)
- Document editing (JS code generation, executeMethod commands)
- Search endpoints (OpenSearch, Qdrant)
- Action items / Person notes / Person candidates CRUD
- Org groups / Org clients management
- ProjectScope CRUD
- Job events SSE streaming
- Storage service (MinIO operations)
- Email service

---

## Приложение: Ключевые зависимости (Python)

- `fastapi`, `uvicorn`
- `peewee`, `peewee-async`, `peewee-migrate`
- `pydantic`, `pydantic-settings`
- `PyJWT`
- `httpx` (async HTTP client)
- `minio` (MinIO SDK)
- `aio-pika` (AMQP/RabbitMQ)
- `opensearch-py`
- `langchain-core`, `langchain-openai`, `langgraph`
- `python-docx`, `openpyxl`, `pypdf` (document extraction)
- `soundfile`, `numpy` (audio chunks)
- `fastapi-mail`
- `pypandoc` (md→pdf/docx export)
