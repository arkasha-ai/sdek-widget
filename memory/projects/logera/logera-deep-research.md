# Logera Deep Research (2026-02-14, обновлено)

## Общая архитектура

**Logera** — платформа для управления знаниями организации с LLM-контекстом. Позиционируется как "Вики с LLM-контекстом" — загрузка файлов, Wiki-страницы, интеграция звонков/транскриптов, поиск и чат-Q&A с цитатами из источников.

**Репозиторий:** `topitip/logera.space` (monorepo)

### Три основные части:
1. **back-end/** — FastAPI (Python), OAuth2 Authorization Server, REST API
2. **app-front/** — SvelteKit 5 + Svelte 5, основное приложение (app.logera.space)
3. **landing-front/** — SvelteKit 5, лендинг (logera.space)

### Мульти-тенантность:
- Организации имеют поддомены: `{org}.logera.space`
- Глобальные пользователи (без организации) + организационные пользователи
- OAuth2 клиенты привязаны к организациям
- Файловое хранилище изолировано по организациям (MinIO бакеты `org-{id}`)

---

## Backend: эндпоинты и модели

### Стек:
- **Framework:** FastAPI 0.115
- **ORM:** Peewee (async через peewee-async + aiopg)
- **БД:** PostgreSQL 17.5
- **Кэш:** Redis 7.2
- **Файлы:** MinIO (S3-совместимое хранилище)
- **Auth:** JWT (PyJWT + python-jose), OAuth2 RFC 6749
- **Email:** fastapi-mail

### Модели данных (10 таблиц):

| Модель | Назначение |
|--------|-----------|
| `Organization` | Организация (name, inn, subdomain, soft delete) |
| `User` | Пользователь (email, login, password, organization FK nullable) |
| `OrgMember` | Участник организации (user FK unique, role: OWNER/ADMIN/EDITOR/VIEWER) |
| `OrgGroup` | Группа внутри организации |
| `OrgGroupMembership` | Связь user↔group |
| `OAuthClient` | OAuth2 клиент (client_id, secret, organization FK, scopes, token lifetimes) |
| `OAuthScope` | Область доступа (hierarchical, default/internal flags) |
| `UserScope` | Связь user↔scope (granted_by, expires_at) |
| `RefreshToken` | Refresh токены (token, scopes, expires_at, revoked_at, ip, user_agent) |
| `FsNode` | Файловый узел: folder или file (organization, parent, name, mime, size, current_version) |
| `FsVersion` | Версия файла (node FK, version, storage_key, size, mime, uploaded_by) |

### API эндпоинты:

**OAuth2 (`/api/oauth2/`):**
- `POST /register` — регистрация глобального пользователя → токены
- `POST /organisation/user/register` — регистрация в организации (pending, без токенов)
- `POST /organisation/user/approve` — одобрение пользователя админом → токены
- `POST /organisation/register` — создание организации + админ + клиент → токены
- `POST /token` — получение токенов (password, client_credentials, refresh_token grants)
- `POST /revoke` — отзыв токена (RFC 7009)
- `POST /introspect` — интроспекция токена (RFC 7662)
- `GET /userinfo` — OIDC UserInfo
- `GET /me` — текущий пользователь с организацией
- `POST /logout` — выход (отзыв + очистка cookie)
- `GET /.well-known/oauth-authorization-server` — метаданные (RFC 8414)

**Organizations (`/api/organizations/`):**
- `GET /` — список активных (admin scope)
- `POST /` — создать организацию
- `GET /{id}` — получить по ID (admin scope)
- `PATCH /{id}` — обновить
- `DELETE /{id}` — soft delete
- `GET /resolve/{subdomain}` — найти по поддомену

**Org Members (`/api/org/members/`):**
- `GET /` — список участников (scope: org:members:read)
- `POST /` — добавить участника
- `PATCH /{user_id}` — изменить роль
- `DELETE /{user_id}` — удалить участника
- `GET /pending` — список pending пользователей

**Org Groups (`/api/org/groups/`):**
- `GET /` — список групп
- `POST /` — создать группу
- `PATCH /{id}` — обновить
- `DELETE /{id}` — удалить

**Org OAuth Clients (`/api/org/clients/`):**
- `GET /` — список клиентов организации
- `POST /` — создать клиента
- `POST /{id}/rotate-secret` — ротация секрета
- `DELETE /{id}` — удалить

**Users (`/api/users/`):**
- `GET /me/full` — полный профиль + scopes
- `GET /{user_id}/scopes` — scopes пользователя
- `POST /{user_id}/scopes` — выдать scope
- `DELETE /{user_id}/scopes/{scope}` — отозвать scope
- `GET /scopes` — список всех scope

**Files (`/api/files/`):**
- `GET /` — список узлов (папки/файлы)
- `GET /{node_id}` — получить узел
- `POST /folders` — создать папку
- `POST /upload` — загрузить файлы
- `PATCH /{node_id}/rename` — переименовать
- `PATCH /{node_id}/move` — переместить
- `DELETE /{node_id}` — удалить
- `GET /{node_id}/download` — скачать файл
- `GET /{node_id}/export` — экспорт файла
- `GET /{node_id}/versions` — список версий
- `POST /{node_id}/upload-version` — загрузить новую версию
- `POST /attachments` — загрузить вложение
- `POST /{node_id}/restore` — восстановить версию

**Health (`/api/health/`):**
- `GET /` — комплексная проверка (DB + Redis + MinIO)
- `GET /ping` — простой pong
- `GET /version` — версия приложения

### Сервисы (бизнес-логика):
- `oauth_authorization_server.py` — ядро OAuth2 (grant types, token generation)
- `oauth_service.py` — управление scopes
- `resource_server.py` — валидация токенов, проверка scopes
- `registration_service.py` — регистрация организации (транзакционно)
- `organization_service.py` + `org_service.py` — CRUD организаций
- `org_members_service.py` — управление участниками
- `org_groups_service.py` — управление группами
- `org_clients_service.py` — управление OAuth клиентами
- `storage_service.py` — работа с MinIO (upload/download/list/delete/presigned URLs)
- `email_service.py` — отправка email

### Безопасность:
- JWT access + refresh токены (httpOnly cookie для refresh)
- Refresh token rotation
- Token blacklist (Redis)
- Role-based scopes: OWNER > ADMIN > EDITOR > VIEWER
- 6 организационных scopes: members:read/write, groups:read/write, clients:manage, settings:write
- CORS с regex для поддоменов `*.logera.space`
- Soft delete везде

---

## Frontend: страницы и компоненты

### Стек:
- **Framework:** SvelteKit 2.38 + Svelte 5.38
- **UI Kit:** shadcn/ui (через bits-ui) — 40+ компонентов
- **Стилизация:** Tailwind CSS 4
- **Иконки:** Lucide
- **Архитектура:** Feature-Sliced Design (entities/features/widgets/pages/shared)

### Маршруты (страницы):

| Маршрут | Назначение | Статус |
|---------|-----------|--------|
| `/` | Главная — файловый менеджер (Page.svelte) | ✅ Реализовано |
| `/auth/login` | Вход (email + пароль) | ✅ Реализовано |
| `/auth/register` | Регистрация (глобальная или организационная) | ✅ Реализовано |
| `/auth/register-org` | Регистрация организации + админа | ✅ Реализовано |
| `/auth/pending` | Ожидание одобрения (org registration) | ✅ Реализовано |
| `/profile` | Профиль пользователя (имя, email, org, scopes) | ✅ Реализовано |
| `/org` | Панель управления организацией (4 вкладки) | ✅ Реализовано |
| `/org/members` | Управление участниками (standalone) | ✅ Реализовано |
| `/org/clients` | OAuth клиенты организации | ✅ Реализовано |
| `/org/groups` | Группы организации | ✅ Реализовано |
| `/api/auth/logout` | Server-side logout endpoint | ✅ Реализовано |
| `/api/search` | Server-side search proxy | ✅ Реализовано |

### Ключевые виджеты (app-main/):

**Файловый менеджер (основной экран):**
- `Sidebar.svelte` — боковая панель: дерево файлов + поиск + квота хранилища
- `TreeSection.svelte` / `TreeArea.svelte` / `TreeNode.svelte` — дерево папок/файлов
- `TreeToolbar.svelte` — панель действий с файлами
- `FileViewer.svelte` — просмотр файлов (поддерживает множество форматов)
- `VideoPlayer.svelte` — видеоплеер
- `ImageLightbox.svelte` / `ZoomableImage.svelte` — просмотр изображений

**Markdown/документы:**
- `MarkdownEditor.svelte` — редактор Markdown
- `MilkdownEditor.svelte` — WYSIWYG редактор (Milkdown)
- `MdRuntime.svelte` — рендеринг Markdown

**Транскрипты:**
- `Transcript.svelte` — панель транскрипта (спикеры, сегменты, таймкоды)
- `TranscriptPanel.svelte` — обёртка транскрипта
- `SegmentView.svelte` — отдельный сегмент транскрипта

**AI/Чат:**
- `ProjectChat.svelte` — чат с LLM-контекстом (drag-and-drop файлов/папок в контекст)
- `SummaryPanel.svelte` / `FileSummary.svelte` — суммаризация

**Поиск:**
- `SearchSection.svelte` / `SearchResults.svelte` — поиск по файлам
- `TokenSearchInput.svelte` — токенизированный поиск

**Управление:**
- `MainTabs.svelte` — вкладки (транскрипт, summary, etc.)
- `ActionsPanel.svelte` — панель действий
- `FolderPickerDialog.svelte` — выбор папки для перемещения

### Entities (данные):
- `entities/fs/` — файловая система (store, types, API: versions, mock data)
- `entities/user/` — пользователь (API: getMe, getMeFull, orgListMembers, orgListClients, etc.)
- `entities/organization/` — организация (API: register, resolve, CRUD)

### Features:
- `features/auth/` — аутентификация (store, API, AuthTabsHeader)

### Зависимости (интересные):
- **Milkdown** — WYSIWYG Markdown редактор
- **CodeMirror** — код-редактор
- **docx-preview** — просмотр DOCX
- **xlsx** — работа с Excel
- **pdfjs-dist** — просмотр PDF
- **html2pdf.js** — экспорт в PDF
- **html-to-docx** — экспорт в DOCX
- **turndown** — HTML→Markdown
- **marked** — Markdown→HTML
- **DOMPurify** — санитизация HTML
- **zoom-image** — зум изображений

---

## Landing

**landing-front/** — лендинг на logera.space

### Содержание (одна страница):
1. **Hero** — "Найдите ответ с цитатами из ваших страниц, файлов и звонков"
2. **Функционал** — 3 карточки: Контекст LLM, Звонки и транскрипт, Wiki-страницы
3. **Реалмы** — Personal (app.logera.space) + Organizations ({org}.logera.space)
4. **Роли и доступ** — Scopes, Регистрация/вход, Заявки в организацию
5. **Ключевые сущности** — Project, Wiki Page, File, Call, Speaker, Person
6. **Админ панель** — Requests, Users, Settings
7. **Состояния** — Account, Call, Page, Speaker (state machines)
8. **CTA** — "Начать бесплатно"

### Отличия от app-front:
- Нет файлового менеджера, чата, транскриптов
- Нет аутентификации (кроме logout)
- Минимальные зависимости (без Milkdown, CodeMirror, xlsx и т.д.)
- Только UI-компоненты shadcn/ui (дублирование с app-front)
- Порт 5174 (app-front на 5173)

---

## Docker Compose конфигурации

### back-end/docker-compose.yml (4 сервиса):
| Сервис | Образ | Порт | Назначение |
|--------|-------|------|-----------|
| `web` | Custom (Dockerfile) | 8000 | FastAPI приложение |
| `db` | postgres:17.5-alpine | 5432 | PostgreSQL |
| `redis` | redis:7.2.4-alpine | 6379 | Кэш/blacklist |
| `minio` | minio:RELEASE.2023-09-07 | 9000/9001 | Файловое хранилище |

- Все 4 сервиса в сети `logera-network`
- Health checks для всех сервисов
- Volumes для данных (persistent)
- Hot reload через mount кода

### app-front/docker-compose.yml (1 сервис):
- Только PostgreSQL (для SSR сессий через Drizzle ORM)
- Минимальная конфигурация

### landing-front/docker-compose.yml (1 сервис):
- Идентична app-front — только PostgreSQL

**Нет** общего docker-compose для всего проекта.

---

## Что реализовано полностью (end-to-end)

### ✅ OAuth2 Authentication:
- Регистрация глобального пользователя → токены → профиль
- Регистрация организации + админ → токены
- Регистрация пользователя в организацию → pending → approve
- Login (password grant) → access + refresh tokens
- Token refresh (httpOnly cookie + localStorage)
- Logout (revoke + clear cookies)
- Token introspection, revocation

### ✅ Управление организацией:
- CRUD организаций (backend + frontend)
- Участники: список, добавление, удаление, смена роли (4 роли)
- Группы: CRUD (backend + frontend)
- OAuth клиенты: создание, ротация секрета, удаление
- Scopes: выдача/отзыв прав пользователям
- Pending users: список + approve

### ✅ Файловое хранилище:
- Backend: полный CRUD файлов/папок через MinIO
- Версионирование файлов (upload-version, list-versions, restore)
- Download/export файлов
- Frontend: дерево файлов, sidebar, загрузка, просмотр

### ✅ Просмотр файлов (frontend):
- Markdown (редактор + WYSIWYG Milkdown)
- PDF (pdfjs-dist)
- DOCX (docx-preview)
- XLSX (xlsx)
- Изображения (zoom)
- Видео/аудио (плеер)

---

## Что есть на бекенде но нет на фронте

1. **Organizations CRUD через `/api/organizations/`** — есть дублирующий роутер (`api/endpoints/organizations.py` + `api/routers/organizations.py`), фронт использует один из них
2. **Export файлов** (`GET /files/{id}/export`) — эндпоинт есть, но UI для экспорта неясен
3. **Attachments upload** (`POST /files/attachments`) — отдельный эндпоинт, на фронте не видно отдельного UI
4. **Email service** (`email_service.py`) — сервис есть, но нигде не вызывается в эндпоинтах (подготовка к email-уведомлениям)
5. **Prometheus metrics** (зависимость `prometheus-client` в requirements) — не подключено

---

## Что начато но не закончено

### 🔶 AI/LLM чат (ProjectChat.svelte):
- **UI готов:** чат с полем ввода, drag-and-drop файлов/папок в контекст, отображение markdown
- **Backend НЕ готов:** нет API для чата, нет LLM интеграции, нет эндпоинтов для Q&A
- Фронтенд использует **только mock данные** (hardcoded спикеры, mock сегменты)

### 🔶 Транскрипты (Transcript.svelte):
- **UI готов:** список сегментов, спикеры с цветами, таймкоды, синхронизация с плеером
- **Backend НЕ готов:** нет модели Call/Transcript в БД, нет API для транскриптов
- Данные **полностью mock** (hardcoded массив из 20 сегментов)

### 🔶 Summary/Суммаризация:
- `SummaryPanel.svelte`, `FileSummary.svelte`, `summary-actions.ts` — UI компоненты есть
- Backend: нет API для суммаризации

### 🔶 Поиск (SearchSection, TokenSearchInput):
- Фронт UI готов, есть серверный прокси `/api/search`
- Backend: нет полнотекстового поиска, нет семантического поиска

### 🔶 Wiki-страницы:
- Описаны на лендинге как ключевая сущность (Draft/Published/Archived)
- Нет модели в БД, нет API

### 🔶 Сущности из лендинга, отсутствующие в коде:
- **Project** — "контейнер знаний" — нет модели
- **Call** — uploaded/processing/ready/error — нет модели
- **Speaker** — candidate/verified/linked — нет модели
- **Person** — связь со Speakers — нет модели
- **Wiki Page** — draft/published/archived — нет модели

### 🔶 Drizzle ORM на фронте:
- `drizzle.config.ts`, `shared/server/db/` — настроен, но используется минимально (сессии?)
- Дублирование ORM (Peewee на бекенде, Drizzle на фронте)

### 🔶 Storybook:
- Настроен для обоих фронтов (`.storybook/`), но нет story файлов

---

## AI компоненты

### Текущее состояние: **Нет AI/LLM/ML кода в репозитории**

**Проверено:**
- `requirements.txt` (backend) — нет LangChain, OpenAI, Ollama, Whisper, ChromaDB, transformers, torch
- Нет Python файлов с AI-логикой
- Нет конфигурации для LLM/STT/TTS

### Однако, **AI задуман как ключевая фича:**

**Из landing-front (описание продукта):**
- "Контекст LLM — ответы с обязательными цитатами: Wiki, файлы и фрагменты транскриптов"
- "Звонки и транскрипт — STT, диаризация, спикеры и персоны"
- "Вики с LLM-контекстом" — основной слоган

**Из ProjectChat.svelte (фронтенд):**
- UI для чата с контекстом (drag файлов/папок)
- Подсчёт токенов (`tokens: 300`)
- Рендеринг markdown ответов
- Дизайн для AI-ассистента с цитатами

**Из Transcript.svelte:**
- Спикеры с диаризацией (цвета, имена)
- Сегменты с таймкодами
- Группировка сегментов по темам

**Вывод:** Фронтенд UI для AI-фич готов (чат, транскрипты, суммаризация), но **бекенд и интеграция с LLM/STT полностью отсутствуют**. Это следующий этап разработки.

---

## Выводы и рекомендации

### Сильные стороны:
1. **Зрелый OAuth2 сервер** — полная реализация RFC 6749, 7009, 7662, 8414 с тестами
2. **Мульти-тенантность** — поддомены, изоляция данных, организационные клиенты
3. **Файловое хранилище** — версионирование, MinIO, множество форматов просмотра
4. **Качественный UI** — shadcn/ui, Feature-Sliced Design, Svelte 5
5. **Ролевая модель** — 4 роли, 6 scopes, гранулярный доступ

### Проблемы:
1. **Разрыв фронт/бек:** UI для AI-фич (чат, транскрипты, summary) готов, но бекенд отсутствует
2. **Mock данные:** транскрипты, спикеры — всё hardcoded
3. **Дублирование кода:** организационные роутеры (`endpoints/organizations.py` vs `routers/organizations.py`)
4. **Дублирование UI-компонентов:** ~40 shadcn компонентов скопированы в обоих фронтах (app + landing)
5. **Отсутствие CI/CD:** нет GitHub Actions, Dockerfile только для бекенда
6. **Нет общего docker-compose:** невозможно поднять всё одной командой
7. **5 из 6 ключевых сущностей (Project, Call, Speaker, Person, WikiPage) — только на лендинге**, не в коде

### Приоритеты для развития:
1. **AI/LLM интеграция** — добавить LLM backend (OpenAI/Ollama), RAG для файлов
2. **STT/Транскрипция** — Whisper для обработки аудио/видео
3. **Модели данных** — создать модели Project, Call, Speaker, Person, WikiPage
4. **Поиск** — полнотекстовый (PostgreSQL FTS) + семантический (embeddings)
5. **CI/CD** — GitHub Actions для тестов, линтинга, деплоя
6. **Общий docker-compose** — для локальной разработки всего стека

---

## Ветка feature/design-improvements

> Анализ на 2026-02-14. Сравнение с main. ~200 изменённых файлов.

### Общий вердикт

Ветка **радикально расширяет** проект: из "OAuth + файловое хранилище" Logera превращается в полноценную **media processing платформу** с AI-агентом. Все сущности, которые ранее были "только на лендинге" (Transcript, Speaker, Summary, Project, Call, Person) — **теперь реализованы на бекенде** с моделями, API и воркерами.

---

### 1. Новые модели данных (back-end/models/)

В main было 10 таблиц. В ветке стало **22+**:

| Новая модель | Таблица | Назначение |
|---|---|---|
| `JobStatus` | `job_status` | Статус обработки медиа (created→prepared→dia_ready→asr_ready→link_ready→indexed→error) |
| `ProjectScope` | `project_scopes` | Группировка файлов по проектам. XOR tenant: org_id ⊕ owner_user_id |
| `Transcript` | `transcripts` | Транскрипт файла (node_id+version). Ключи SRT/VTT/JSONL артефактов в MinIO |
| `TranscriptSegment` | `transcript_segments` | Сегменты транскрипта (start_ms, end_ms, text, speaker_id) |
| `SpeakerProfile` | `speaker_profiles` | Глобальный профиль спикера (name, company, position, consent) |
| `TranscriptSpeaker` | `transcript_speakers` | Связь спикер↔файл (аггрегация speech_ms) |
| `Summary` | `summaries` | Саммари встречи (content_md, source: nlp/manual, LLM tracking) |
| `PersonCandidate` | `person_candidates` | NLP-extracted кандидаты на идентификацию спикера (pending→approved/rejected) |
| `PersonNote` | `person_notes` | Заметки о персонах (preference/fact/relationship/history), LLM или ручные |
| `ActionItem` | `action_items` | Извлечённые задачи из звонков (title, assignee, due_date, priority, status) |
| `ContextReference` | `context_references` | Ссылки саммари на источники (для explainability/цитат) |
| `Conversation` | `chat_conversations` | Чат-сессия с LLM (tenant isolation, token tracking) |
| `ChatMessage` | `chat_messages` | Сообщения чата (role: user/assistant/tool, tool_calls_json) |
| `ChatContextReference` | `chat_context_references` | Контекст, использованный в сообщении чата |

**Все модели** имеют tenant isolation: `org_id` XOR `owner_user_id` (personal space).

---

### 2. Media Processing Pipeline (AMQP Workers)

**Главное нововведение.** 7 воркеров в docker-compose, связанных через RabbitMQ (topic exchange):

```
Upload → job.created → media_prep → media.prepared → diarization (GPU) → dia.ready
  ├→ asr (Whisper, GPU) → asr.ready ├→ nlp_adapter (LLM) → nlp.ready
  │                                   └→ indexer → indexed.ready → cleanup
  └→ speaker_linking (Qdrant embeddings)
```

| Воркер | Runtime | Назначение |
|---|---|---|
| `media_prep` | CPU | Извлечение аудио, VAD, нормализация → `prepared/audio.wav` |
| `diarization` | GPU (pyannote) | Диаризация спикеров, OSD, clustering |
| `asr` | GPU (Whisper) | Транскрибация по сегментам диаризации. Batch inference, prometheus metrics |
| `speaker_linking` | CPU | Embedding-based matching спикеров через Qdrant |
| `indexer` | CPU | Индексация сегментов в OpenSearch, экспорт SRT/VTT/JSONL |
| `nlp_adapter` | CPU (LiteLLM) | Суммаризация через LLM (gpt-4o-mini), extraction person candidates, action items, person notes |
| `cleanup` | CPU | Удаление временных файлов после обработки |

**Инфраструктура:** RabbitMQ, Qdrant (vector DB), OpenSearch (full-text), MinIO, PostgreSQL, Redis, Prometheus+Grafana.

---

### 3. LangGraph Chat Agent (back-end/services/chat/)

Полноценный **AI-агент** на LangGraph с tool calling и SSE streaming:

- **`graph.py`** — StateGraph с nodes: `agent → tools → (process_edits) → agent`. LLM через LiteLLM proxy (ChatOpenAI).
- **`langgraph_agent.py`** — `LangGraphChatAgent` class: загрузка истории, сохранение сообщений, SSE streaming (token/tool_call/tool_result/edit_command/done/error events).
- **`langgraph_tools.py`** — LangChain `@tool`-decorated tools: `semantic_search`, `full_text_search`, `read_file_content`, `get_action_items`, `get_speaker_info`, `edit_document`, `read_document_structure`, `ask_user`.
- **`document_editor.py`** — Генерация Office JS API кода для редактирования документов через OnlyOffice Connector API (insert_heading, insert_paragraph, insert_table, insert_list, replace_text, delete_section и др.).
- **`tools.py`** — OpenAI-формат tool definitions (legacy, параллельно с LangChain tools).
- **`state.py`** — ChatAgentState (TypedDict) с messages, context_items, active_document_id, iteration control.
- **`llm_client.py`** — Базовый LLM клиент.

**System prompt** на русском, включает инструкции по редактированию документов через OnlyOffice (PasteHtml, SearchAndReplace).

---

### 4. Новые API эндпоинты (back-end/api/routers/)

| Роутер | Префикс | Эндпоинты |
|---|---|---|
| `chat.py` | `/v1/chat` | POST conversations, POST messages/stream (SSE), GET conversations, GET conversation/{id}, DELETE |
| `jobs.py` | `/v1/jobs` | GET /{job_id}, GET /by-node/{node_id}, GET /{job_id}/events (SSE live status) |
| `search.py` | `/v1` | POST /search (OpenSearch full-text + facets), GET /search/context (semantic) |
| `projects.py` | `/projects` | CRUD ProjectScope (create, list, get, update, archive) |
| `person_candidates.py` | `/v1/person-candidates` | GET /files/{node_id}, POST /{id}/approve, POST /{id}/reject |
| `person_notes.py` | `/v1/person-notes` | CRUD notes by speaker (list, create, update, verify, delete) |
| `action_items.py` | `/v1/action-items` | GET list (by node/status/assignee), PATCH /{id} (update status) |
| `media_chunks.py` | `/api/media` | GET /{node_id}/chunk?start=&end= — динамическая нарезка WAV из MinIO |
| `onlyoffice.py` | `/onlyoffice` | GET /config/{node_id} (JWT config), POST /callback (save), GET /download/{node_id} |

---

### 5. Docker Compose — единый стек

В main: 3 отдельных docker-compose (back-end, app-front, landing-front) без общего.

В ветке: **1 общий `docker-compose.yml`** (корень) с **20+ сервисами**:
- nginx (reverse proxy), app-front, web (backend), db, redis, minio
- rabbitmq, qdrant, opensearch, opensearch_dashboards
- 7 workers: media_prep, diarization (GPU), asr (GPU), speaker_linking, indexer, nlp_adapter, cleanup
- onlyoffice (Document Server 8.2, JWT auth)
- prometheus, grafana, rabbitmq_exporter (мониторинг)

Дополнительно: `docker-compose.dev.yml`, `docker-compose.test.yml`, `docker-compose.scale.yml`.

---

### 6. Frontend (app-front) — новое

**Новые entity слои (FSD):**
- `entities/chat/` — API клиент чата (createConversation, streamMessage SSE), типы
- `entities/person-candidates/` — API одобрения/отклонения кандидатов, store
- `entities/project-scope/` — CRUD проектов, store, UI (ProjectScopeAssignDialog)
- `entities/job-status/` — Store/context для отслеживания статуса обработки, UI (JobStatusBadge)

**Новые виджеты:**
- `OnlyOfficeEditor.svelte` — Интеграция OnlyOffice Document Server (DOCX/XLSX/PPTX), Connector API, тёмная тема, branding injection
- `SummaryWithCitations.svelte` — Рендеринг саммари с цитатами (:::cite блоки с спикером, таймкодом, файлом)
- `PersonCandidatesModal.svelte` — Модалка одобрения person candidates (name/company/position override, link to org member)
- `DiffOverlay.svelte` — Визуализация diff для AI-edit предложений
- `MermaidEditor.svelte` / `MermaidView.svelte` — Редактор/просмотр Mermaid диаграмм
- `EditorJsEditor.svelte` / `TipTapEditor.svelte` — Альтернативные редакторы (Editor.js, TipTap)
- `PdfViewer.svelte` — PDF просмотр (отдельный компонент)
- `MarkedPreviewWithMermaid.svelte` — Markdown preview с поддержкой Mermaid

**Новые страницы профиля (`/profile/*`):**
- `/profile` — Основной профиль (имя, email, аватар)
- `/profile/voice` — Голосовой профиль (загрузка образцов голоса для speaker recognition)
- `/profile/ai-settings` — AI настройки (стиль саммари, язык, auto-process, custom prompt)
- `/profile/security` — Безопасность (пароль, 2FA)
- `/profile/notifications` — Уведомления
- `/profile/usage` — Статистика использования
- `/profile/organization` — Организация
- `/profile/billing` — Тарифы

**ProjectChat.svelte** — из mock стал **реальным**: создаёт conversation через API, стримит SSE-ответы, поддерживает tool calls, edit commands, drag-and-drop файлов в контекст, интеграцию с OnlyOffice (activeDocumentId).

---

### 7. Backend Services — новые

| Сервис | Назначение |
|---|---|
| `orchestrator_service.py` | Автозапуск pipeline при upload медиа (create job → publish AMQP) |
| `amqp_backend_consumer.py` | Потребитель AMQP событий на бекенде (сохранение результатов workers в БД) |
| `event_bus.py` | In-process pub/sub для SSE стриминга статусов (job events → frontend) |
| `opensearch_service.py` | Клиент OpenSearch (индексация, поиск, tenant-isolated индексы) |
| `tenant_service.py` | Разрешение tenant context (XOR org_id/owner_user_id), валидация |
| `llm_document_service.py` | LLM-driven редактирование документов (DOCX Track Changes, markdown diff) |
| `chat/` (пакет) | LangGraph agent, tools, graph, state, document_editor |

---

### 8. Общая библиотека (packages/logera_common/)

Вынесенный shared-пакет для workers:
- `amqp.py` — Publish/consume через aio-pika (publisher confirms, prefetch, DLX)
- `config.py` — Общие настройки (pydantic-settings)
- `minio_io.py` — MinIO клиент (get/put/resolve bucket)
- `text_embeddings.py` — Text embeddings (для speaker_linking, semantic search)
- `webhooks.py` — Отправка webhook уведомлений

---

### 9. Тесты и CI

Появились **integration тесты** (`tests/integration/`):
- `test_pipeline_e2e.py` — Полный E2E: upload → job.created → ... → indexed.ready
- `test_pipeline_org.py` / `test_pipeline_personal.py` — Tenant isolation для org/personal space
- `test_tenant_isolation.py` — Проверка изоляции данных между tenant'ами
- `test_idempotency.py` — Идемпотентность pipeline
- `test_project_scope.py` — CRUD ProjectScope

Backend unit tests: `test_files.py`, `test_search_leaks.py`, `test_tenant_isolation.py`, `test_register_org_user.py`, `test_register_organisation.py`.

Скрипты: `run_integration_tests.sh`, `run_integration_tests.ps1`, `test_optimization.sh`.

---

### 10. Мониторинг

- **Prometheus** — метрики workers (asr_batch_inference_duration, dia_duration, indexed_docs_total, webhook_requests)
- **Grafana** — 5 дашбордов: GPU overview, Pipeline overview, RabbitMQ overview, Webhooks overview, Worker overview
- **Alert rules** (`alerts.yml`)
- **RabbitMQ Exporter** — метрики очередей
- Workers экспортируют health endpoints (`/healthz`)

---

### 11. Nginx

Полноценный reverse proxy:
- `/api/` → backend
- `/` → frontend (SvelteKit)
- `/onlyoffice/` → OnlyOffice Document Server
- SSE endpoints (buffering off, 24h timeout)
- `client_max_body_size 500M`

---

### 12. Документация

Появилось 15+ docs файлов:
- `MEDIA_PIPELINE.md` — Mermaid-диаграммы полного pipeline
- `AUTH_FLOW.md`, `DATA_MODELS.md`, `ORGANIZATIONS.md`
- `SEARCH.md`, `SPEAKER_LINKING.md`, `TEXT_EMBEDDINGS.md`
- `WEBHOOKS.md`, `MONITORING.md`, `INFRASTRUCTURE.md`
- `ENV_VARIABLES.md`, `LOCAL_SETUP.md`, `MACOS_M4_SETUP.md`
- `AMQP_EVENTS.md`, `FILE_STORAGE.md`
- Worker contracts: `workers/docs/WORKER_CONTRACTS.md`
- Backend: `API_Reference.md`, `SERVICES.md`, `ROUTERS.md`

---

### 13. Итого: что изменилось vs main

| Аспект | main | feature/design-improvements |
|---|---|---|
| Модели БД | 10 | 22+ |
| API роутеры | 6 (OAuth, org, users, files, health) | 14+ (+chat, jobs, search, projects, person-candidates, notes, action-items, media, onlyoffice) |
| AI/LLM | ❌ Нет | ✅ LangGraph agent, tool calling, SSE streaming, LiteLLM proxy |
| Media pipeline | ❌ Нет | ✅ 7 workers (Whisper, pyannote, Qdrant, OpenSearch, LLM) |
| Docker services | 4 (разрозненные) | 20+ (единый compose) |
| Мониторинг | ❌ Нет | ✅ Prometheus + Grafana + 5 дашбордов |
| OnlyOffice | ❌ Нет | ✅ Document Server + Connector API + AI editing |
| Тесты | Минимальные | ✅ Integration E2E pipeline + tenant isolation |
| Документация | Минимальная | ✅ 15+ markdown файлов |
| Профиль пользователя | Базовый | ✅ 8 подстраниц (voice, AI settings, security, billing...) |
| Чат | Mock UI | ✅ Реальный SSE streaming с tool calling |
| Транскрипты | Mock | ✅ Реальные модели + pipeline |
| Поиск | Нет | ✅ OpenSearch full-text + semantic (Qdrant) |
| Personal space | Нет | ✅ owner_user_id XOR org_id на всех моделях |

**Вывод:** Ветка превращает Logera из прототипа auth+файлы в **production-ready платформу** для обработки медиа, транскрибации, AI-чата и collaborative document editing.
