# Logera — Единый справочник проекта

> **Платформа управления знаниями с LLM-контекстом**
> "Найдите ответ с цитатами из ваших страниц, файлов и звонков"

**Репозиторий:** `topitip/logera.space` (приватный, GitHub)
**Основная ветка:** `feature/design-improvements`
**Статус:** Активный pet-проект

---

## 📁 Детальная документация (ссылки)

| Файл | Размер | Что внутри |
|-------|--------|-----------|
| [logera-backend.md](logera-backend.md) | ~39KB | 24 модели, ~50 API endpoints, 15 сервисов, LangGraph agent, конфиг, тесты |
| [logera-frontend.md](logera-frontend.md) | ~45KB | 20+ страниц, 7 entities, 35+ виджетов, shadcn UI kit, стили/темы |
| [logera-workers.md](logera-workers.md) | ~51KB | 7 воркеров, AMQP routing, pipeline flow, logera_common, тесты |
| [logera-infrastructure.md](logera-infrastructure.md) | ~30KB | 21 Docker сервис, nginx, Prometheus+Grafana, Dockerfiles, ENV |
| [logera-landing-docs.md](logera-landing-docs.md) | ~24KB | Лендинг, 17 docs файлов, Storybook, скрипты, конфигурация |
| [logera-deep-research.md](logera-deep-research.md) | ~25KB | Первичный аудит (сравнение main vs feature branch) |
| [logera-collabora-migration.md](logera-collabora-migration.md) | ~5KB | План миграции OnlyOffice → Collabora |

---

## Архитектура

### Структура репозитория
```
logera.space/
├── app-front/             # SvelteKit 5 — основное приложение
├── back-end/              # FastAPI — API + OAuth2 + LangGraph agent
├── landing-front/         # SvelteKit 5 — лендинг
├── workers/               # 7 AMQP воркеров (media pipeline)
│   ├── media_prep/        # CPU — аудио extraction, VAD
│   ├── diarization/       # GPU — pyannote speaker diarization
│   ├── asr/               # GPU — Whisper транскрибация
│   ├── speaker_linking/   # CPU — Qdrant embedding matching
│   ├── indexer/           # CPU — OpenSearch индексация
│   ├── nlp_adapter/       # CPU — LLM суммаризация (LiteLLM)
│   ├── cleanup/           # CPU — удаление temp файлов
│   └── shared/            # Общий пакет
├── packages/logera_common/# Shared: AMQP, config, MinIO, embeddings, webhooks
├── docs/                  # 17 markdown документов (7500+ строк)
├── docker-compose.yml     # 21 сервис (prod)
├── docker-compose.dev.yml # Dev (localhost, HMR, нет мониторинга)
├── docker-compose.test.yml# Test (изоляция, лёгкие модели)
├── docker-compose.scale.yml# Scale (2x ASR workers)
├── nginx/                 # Reverse proxy (SSE, OnlyOffice, HMR)
├── scripts/               # analyze_coverage.py
├── tests/                 # Integration tests
└── docs/                  # 17 файлов документации
```

### Multi-tenancy (XOR)
- **org-space:** `org_id NOT NULL`, `owner_user_id NULL` → данные организации
- **personal-space:** `org_id NULL`, `owner_user_id NOT NULL` → личное пространство
- Организации имеют поддомены: `{org}.logera.space`
- MinIO бакеты: `org-{id}` / `personal`

---

## Стек технологий

### Frontend
- **SvelteKit 2.38 + Svelte 5.38** (SSR, adapter-node)
- **UI:** shadcn-svelte (bits-ui) — 40+ компонентов
- **Tailwind CSS 4** + oklch цвета, light/dark themes
- **Архитектура:** Feature-Sliced Design
- **Редакторы:** Milkdown (WYSIWYG), CodeMirror, TipTap, Editor.js, OnlyOffice
- **Документы:** docx-preview, xlsx, pdfjs-dist, html2pdf.js, pypandoc
- **Диаграммы:** Mermaid
- **pnpm**

### Backend
- **FastAPI 0.115** + Uvicorn + Gunicorn
- **Peewee** (async через peewee-async + aiopg)
- **OAuth2 RFC 6749** (JWT, refresh rotation, token blacklist в Redis)
- **LangGraph + LangChain + LiteLLM** (AI agent)
- **pytest** + pytest-asyncio
- **ruff, mypy, black, isort, bandit**

### Инфраструктура (21 Docker сервис)
| Сервис | Образ / Роль |
|--------|-------------|
| nginx | Reverse proxy, SSE support, 500MB upload |
| app-front | SvelteKit SSR (:3000) |
| web | FastAPI (:8000) |
| db | PostgreSQL 17.5-alpine |
| redis | Redis 7.2-alpine (token blacklist) |
| minio | MinIO (S3, console :9001) |
| rabbitmq | RabbitMQ (AMQP :5672, mgmt :15672) |
| qdrant | Vector DB (semantic search, :6333) |
| opensearch | Full-text search (:9200) |
| opensearch_dashboards | UI (:5601) |
| 7x workers | media_prep, diarization(GPU), asr(GPU), speaker_linking, indexer, nlp_adapter, cleanup |
| onlyoffice | Document Server 8.2 (JWT, :8443) |
| prometheus | Мониторинг (:9090) |
| grafana | Дашборды (:3001), 5 dashboards |
| rabbitmq_exporter | Метрики очередей |

→ Детали: [logera-infrastructure.md](logera-infrastructure.md)

---

## Модели данных (24 таблицы)

### Core (9)
| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| Organization | `organization` | name, inn(UNIQUE), subdomain(UNIQUE), soft delete |
| User | `user` | email, login, password, org FK(nullable), is_superuser |
| OrgMember | `org_member` | org FK, user FK(UNIQUE), role: OWNER/ADMIN/EDITOR/VIEWER |
| OrgGroup | `org_group` | org FK, name(unique per org) |
| OrgGroupMembership | `org_group_membership` | group FK, user FK |
| OAuthClient | `oauth_client` | client_id(UNIQUE), secret, org FK, scopes(JSON), token lifetimes |
| OAuthScope | `oauth_scope` | name(UNIQUE), parent_scope FK, is_default, is_internal |
| UserScope | `user_scope` | user FK, scope FK, granted_by, expires_at |
| RefreshToken | `refresh_tokens` | token(UNIQUE), scopes(CSV), user FK, client FK, ip, user_agent |

### Файлы (2)
| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| FsNode | `fs_node` | org FK/owner_user FK(XOR), parent FK(self), type(folder/file), name, mime, size, project_scope_id |
| FsVersion | `fs_version` | node FK, version, storage_key, size, mime, uploaded_by |

### Media Processing (8)
| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| JobStatus | `job_status` | job_id(UNIQUE), org_id/owner_user_id, node_id, version, status(created→indexed/error) |
| Transcript | `transcripts` | org_id/owner_user_id, node_id, version, srt_key, vtt_key, jsonl_key |
| TranscriptSegment | `transcript_segments` | node_id, version, start_ms, end_ms, text, speaker_id, overlap |
| SpeakerProfile | `speaker_profiles` | org_id, user_id, label, name, company, position, consent |
| TranscriptSpeaker | `transcript_speakers` | org_id, node_id, version, speaker_id, total_speech_ms |
| Summary | `summaries` | node_id, version, content_md, source(nlp/manual), llm_model, llm_tokens_used |
| PersonCandidate | `person_candidates` | speaker_profile_id, extracted_name/company/position, status(pending/approved/rejected) |
| PersonNote | `person_notes` | speaker_profile_id, note_type(preference/fact/relationship/history), content, source(llm_auto/user_manual) |

### AI/Chat (4)
| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| ActionItem | `action_items` | node_id, title, description, assignee, due_date, priority(high/medium/low), status(open/in_progress/completed/cancelled) |
| Conversation | `chat_conversations` | org_id/owner_user_id, user FK, title, project_scope_id, total_tokens_used |
| ChatMessage | `chat_messages` | conversation FK, role(user/assistant/tool), content, tool_calls_json, model, tokens_used |
| ChatContextReference | `chat_context_references` | message FK, ref_type(segment/file/folder/wiki/text), node_id, start_ms/end_ms, text_snippet |

### Projects (1)
| Модель | Таблица | Ключевые поля |
|--------|---------|--------------|
| ProjectScope | `project_scopes` | org_id/owner_user_id(XOR), name, description, created_by_user FK, is_archived |

→ Детали: [logera-backend.md](logera-backend.md) §2

---

## API Эндпоинты (сводка)

### OAuth2 (`/api/oauth2/`) — 11 endpoints
register, org/user/register, org/user/approve, org/register, token(3 grant types), revoke, introspect, userinfo, me, logout, .well-known

### Organizations (`/api/organizations/`) — 6 endpoints
CRUD + resolve by subdomain + soft delete

### Org Management — 12 endpoints
- Members: list, add, update role, delete, pending
- Groups: CRUD (4)
- Clients: list, create, rotate-secret, delete

### Users/Scopes (`/api/users/`) — 5 endpoints
me/full, get scopes, grant scope, revoke scope, list all scopes

### Files (`/api/files/`) — 15 endpoints
list, get, create folder, upload(multi-file+tree), rename, move, delete(soft/hard), download(proxy+Range), stream(JWT media token), export(md→pdf/docx), versions, upload-version, attachments, restore, set project-scope

### Chat (`/v1/chat`) — 5 endpoints
| Endpoint | Метод | Описание |
|----------|-------|----------|
| `/conversations` | POST | Создать conversation |
| `/conversations/{id}/messages/stream` | POST | SSE streaming (token/tool_call/tool_result/edit_command/done/error) |
| `/conversations/{id}` | GET | Получить с историей сообщений |
| `/conversations` | GET | Список conversations (filter: project_scope_id) |
| `/conversations/{id}` | DELETE | Удалить (cascade) |

### Jobs (`/v1/jobs`) — 4 endpoints
get, list(filter: status/org_id), by-node/{node_id}, events(SSE live status)

### Search (`/v1`) — 2 endpoints
POST /search (OpenSearch full-text + facets), GET /search/context (semantic via Qdrant)

### Projects (`/projects`) — 5 endpoints
CRUD ProjectScope + archive

### Person Candidates (`/v1/person-candidates`) — 3 endpoints
GET /files/{node_id}, POST /{id}/approve, POST /{id}/reject

### Person Notes (`/v1/person-notes`) — 5 endpoints
CRUD by speaker + verify

### Action Items (`/v1/action-items`) — 3 endpoints
list(filter: node/status/assignee), get, update(status/priority/assignee)

### Media (`/api/media`) — 1 endpoint
GET /{node_id}/chunk?start=&end= (динамическая нарезка WAV)

### OnlyOffice (`/onlyoffice`) — 3 endpoints
GET /config/{node_id}(JWT), POST /callback(save), GET /download/{node_id}

### Health — 3 endpoints
/ (DB+Redis+MinIO), /ping, /version

→ Детали: [logera-backend.md](logera-backend.md) §3

---

## Сервисы Backend (15)

| Сервис | Назначение |
|--------|-----------|
| `oauth_authorization_server` | Ядро OAuth2: grant types, token generation, refresh rotation |
| `resource_server` | Валидация JWT, проверка scopes, RBAC dependencies |
| `registration_service` | Транзакционная регистрация org + admin + client |
| `tenant_service` | Resolve tenant context (XOR org/personal), валидация |
| `storage_service` | MinIO: upload, download, stream, delete, presigned URLs, bucket resolution |
| `orchestrator_service` | Автозапуск pipeline при upload медиа (create job → publish AMQP) |
| `amqp_backend_consumer` | RabbitMQ consumer: обновление JobStatus, сохранение Transcript/Segments/Speakers/Summary/PersonCandidates/ActionItems в БД |
| `event_bus` | In-process pub/sub для SSE стриминга job статусов |
| `opensearch_service` | Full-text поиск, индексация, tenant-isolated индексы |
| `organization_service` | CRUD организаций |
| `org_members_service` | Участники: add, update role, delete, pending |
| `org_groups_service` | Группы: CRUD |
| `org_clients_service` | OAuth клиенты: create, rotate-secret, delete |
| `email_service` | Отправка email (fastapi-mail) |
| `llm_document_service` | LLM-driven редактирование документов (DOCX Track Changes, markdown diff) |

→ Детали: [logera-backend.md](logera-backend.md) §4

---

## LangGraph Chat Agent

**Архитектура:** StateGraph → `agent → tools → [process_edits] → agent`

### State
- `messages: list` — LangChain messages
- `context_items: list[ContextItem]` — прикреплённые файлы/сегменты
- `active_document_id: int?` — ID открытого документа (включает editing)
- `pending_edit_commands: list[dict]` — команды редактирования OnlyOffice
- `iteration: int` — счётчик (max 10)

### 7 Tools
| Tool | Что делает |
|------|-----------|
| `semantic_search` | Qdrant vector search по сегментам транскриптов |
| `full_text_search` | OpenSearch full-text поиск с фасетами |
| `read_file_content` | Чтение файла из MinIO (markdown, text) |
| `get_action_items` | Список action items (filter: node/status) |
| `get_speaker_info` | Информация о спикере + notes |
| `edit_document` | Генерация Office JS API кода для OnlyOffice (13+ действий) |
| `ask_user` | Human-in-the-loop: задать вопрос пользователю |

### Document Editor (13+ действий)
insert_heading, insert_paragraph, insert_table, insert_list, insert_image, replace_text, delete_section, format_text, add_comment, add_hyperlink, insert_page_break, create_toc, set_page_margins

### SSE Events
`token` → `tool_call` → `tool_result` → `edit_command` → `done` / `error`

→ Детали: [logera-backend.md](logera-backend.md) §5

---

## Media Processing Pipeline

```
Upload → job.created
  → media_prep (CPU) → media.prepared
    → diarization (GPU, pyannote) → dia.ready
      ├→ asr (GPU, Whisper) → asr.ready
      │    ├→ nlp_adapter (LiteLLM) → nlp.ready
      │    └→ indexer (OpenSearch) → indexed.ready → cleanup
      └→ speaker_linking (Qdrant) → link.ready
```

### AMQP
- **Exchange:** `logera.jobs` (topic, durable)
- **DLX:** `logera.dlx` (topic, durable)

| Воркер | Queue | Consume | Publish | GPU | Health |
|--------|-------|---------|---------|-----|--------|
| media_prep | `q.media_prep` | `job.created` | `media.prepared` | — | :8081 |
| diarization | `q.diarization` | `media.prepared` | `dia.ready` | pyannote | :8081 |
| asr | `q.asr` | `dia.ready` | `asr.ready` | Whisper | :8082 |
| speaker_linking | `q.speaker_linking` | `dia.ready` | `link.ready` | — | :8084 |
| nlp_adapter | `q.nlp_adapter` | `asr.ready` | `nlp.ready` | — | :8085 |
| indexer | `q.indexer` | `asr.ready` | `indexed.ready` | — | :8085 |
| cleanup | `q.cleanup` | `indexed.ready` | — | — | :8087 |

### Артефакты в MinIO
- `prepared/audio.wav` — 16kHz mono WAV
- `transcripts/{job_id}.srt/.vtt/.jsonl` — экспорт транскрипта
- Исходный файл удаляется cleanup'ом

### logera_common (shared package)
- `amqp.py` — publisher/consumer (aio-pika, DLX, prefetch, retries)
- `config.py` — pydantic-settings
- `minio_io.py` — bucket resolution, tenant mapping
- `text_embeddings.py` — Qdrant + dual provider embeddings
- `webhooks.py` — HMAC, retry logic

→ Детали: [logera-workers.md](logera-workers.md)

---

## Frontend — ключевые модули

### Entities (7 FSD слоёв)
| Entity | Что содержит |
|--------|-------------|
| `fs` | Файловая система: store с lazy loading, drag-drop, upload queue, URL sync |
| `chat` | LLM чат: SSE streaming, tool calls, edit commands, human-in-the-loop |
| `user` | Пользователи, org members/groups/clients, scopes |
| `organization` | CRUD организаций, multi-tenant |
| `job-status` | Tracking обработки файлов через SSE |
| `person-candidates` | Привязка спикеров к пользователям |
| `project-scope` | Группировка файлов по проектам |

### Ключевые виджеты
| Виджет | Строк | Что делает |
|--------|-------|-----------|
| **OnlyOfficeEditor** | 1046 | DOCX/XLSX/PPTX editing, Connector API, тёмная тема, AI edit commands |
| **ProjectChat** | 908 | Реальный SSE чат с LLM, drag-drop файлов в контекст, tool calls |
| **Sidebar** | ~500 | Дерево файлов, поиск, квота, создание папок |
| **FileViewer** | ~400 | Просмотр: markdown, PDF, DOCX, XLSX, изображения, видео/аудио |
| **Transcript** | ~350 | Спикеры с цветами, таймкоды, синхронизация с плеером |
| **SummaryWithCitations** | ~300 | Саммари с :::cite блоками (спикер, таймкод, файл) |
| **MermaidEditor** | ~200 | Редактор/просмотр Mermaid диаграмм |
| **DiffOverlay** | ~150 | Визуализация AI-edit предложений |

### Страницы
- **Auth:** login, register, register-org, pending
- **Profile:** 8 подстраниц (основной, voice, ai-settings, security, notifications, usage, organization, billing)
- **Org:** overview, members, clients, groups
- **Root:** файловый менеджер (главный экран)

### Стили
- Tailwind CSS 4 + oklch цвета
- CSS variables: `--background`, `--foreground`, `--primary`, `--accent`, etc.
- Light/Dark themes (prefers-color-scheme + class toggle)
- 40+ shadcn-svelte компонентов

→ Детали: [logera-frontend.md](logera-frontend.md)

---

## Лендинг

**URL:** logera.space | **Порт dev:** 5174

8 секций: Hero, Функционал (3 карточки), Реалмы (Personal/Organizations), Роли и доступ, Ключевые сущности (Project, Wiki Page, File, Call, Speaker, Person), Админ панель, Состояния (state machines), CTA

→ Детали: [logera-landing-docs.md](logera-landing-docs.md) §1

---

## Документация (17 файлов, 7500+ строк)

| Файл | Строк | Содержание |
|------|-------|-----------|
| OVERVIEW.md | 369 | Общий обзор архитектуры |
| DATA_MODELS.md | 618 | Все модели + Mermaid ER-диаграмма |
| AUTH_FLOW.md | 430 | OAuth2 flow + sequence diagrams |
| AMQP_EVENTS.md | 513 | Все routing keys + payloads |
| MEDIA_PIPELINE.md | 605 | Pipeline Mermaid диаграммы |
| FILE_STORAGE.md | 383 | MinIO buckets, paths, versioning |
| ORGANIZATIONS.md | 448 | Multi-tenancy, roles, scopes |
| SPEAKER_LINKING.md | 483 | Embedding matching, Qdrant |
| SEARCH.md | 418 | OpenSearch + semantic search |
| TEXT_EMBEDDINGS.md | 636 | Embedding models, dual provider |
| ENV_VARIABLES.md | 403 | Полный список ENV |
| INFRASTRUCTURE.md | 436 | Docker, networks, volumes |
| LOCAL_SETUP.md | 384 | Инструкция по развёртыванию |
| MACOS_M4_SETUP.md | 244 | Инструкция для Mac M4 |
| MONITORING.md | 359 | Prometheus + Grafana |
| WEBHOOKS.md | 315 | HMAC webhooks |
| DOCUMENTATION_TASKS.md | 498 | Трекер задач по документации |

→ Детали: [logera-landing-docs.md](logera-landing-docs.md) §3

---

## Безопасность

- JWT access + refresh tokens (httpOnly cookie)
- Refresh token rotation + blacklist (Redis)
- 4 роли: OWNER > ADMIN > EDITOR > VIEWER
- 6 org scopes: members:read/write, groups:read/write, clients:manage, settings:write
- CORS regex для `*.logera.space`
- Soft delete везде
- OnlyOffice JWT auth
- bandit (security linter)
- Media tokens (JWT, 30 мин TTL) для стриминга

---

## Мониторинг

- **Prometheus** — 7 scrape targets, 3 alert rules
- **Grafana** — 5 дашбордов: Pipeline, Workers, GPU, RabbitMQ, Webhooks
- **Workers:** `/healthz` endpoints + Prometheus metrics (asr_batch_duration, dia_duration, indexed_docs_total)

→ Детали: [logera-infrastructure.md](logera-infrastructure.md) §4

---

_Обновлено: 2026-02-14 (полный аудит репозитория, 5 агентов на Opus)_
