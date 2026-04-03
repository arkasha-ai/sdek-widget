# Logera — Полный анализ landing-front/, docs/ и конфигурации

> **Дата анализа:** 2026-02-14  
> **Ветка:** `feature/design-improvements`  
> **Репозиторий:** `/tmp/logera.space`

---

## 1. landing-front/ — Лендинг Logera

### 1.1. Общая информация

- **Фреймворк:** SvelteKit (Svelte 5) + TypeScript
- **Пакетный менеджер:** pnpm
- **UI Kit:** shadcn-svelte (Bits UI + Tailwind CSS 4)
- **Стили:** Tailwind CSS 4 с tw-animate-css
- **Порт dev:** 5174 (`vite dev --port 5174`)
- **Адаптер:** `@sveltejs/adapter-node` (SSR)
- **Preprocessors:** `vitePreprocess()` + `mdsvex` (.svx поддержка)
- **Имя пакета:** `organisation-front` (package.json name)
- **Версия:** 0.0.1

### 1.2. Архитектура (Feature-Sliced Design)

```
landing-front/src/
├── app/           # Приложение (пустой, .gitkeep)
├── entities/      # Бизнес-сущности
│   └── user/types.ts   # Типы пользователя
├── features/      # Фичи
│   └── auth/api.ts     # Logout API (POST /api/auth/logout)
├── pages/         # Страницы
│   └── home/Page.svelte  # Главная страница лендинга
├── processes/     # Процессы (пустой)
├── routes/        # SvelteKit routes
│   ├── +page.svelte       # Импортирует HomePage
│   ├── +layout.svelte     # Layout: Header + children + Footer
│   └── api/auth/logout/+server.ts  # Logout endpoint
├── shared/        # Общее
│   ├── assets/    # Логотипы SVG
│   ├── hooks/     # is-mobile.svelte.ts (MediaQuery)
│   ├── lib/       # links.ts (URLs)
│   ├── server/    # Auth + DB (Drizzle + PostgreSQL)
│   ├── ui/        # ~40 shadcn-svelte компонентов
│   └── utils.ts   # cn() хелпер (clsx + tailwind-merge)
└── widgets/       # Виджеты
    ├── header/ui/Header.svelte
    └── footer/ui/Footer.svelte
```

### 1.3. Страницы и секции (Page.svelte)

Единственная страница — `pages/home/Page.svelte`. Содержит **8 секций:**

| # | ID | Заголовок | Описание |
|---|-----|-----------|----------|
| 1 | `#hero` | — | Hero-блок с лого, заголовком, описанием, CTA-кнопками |
| 2 | `#features` | Функционал | 3 карточки: Контекст LLM, Звонки и транскрипт, Wiki-страницы |
| 3 | `#realms` | Реалмы и домены | 2 карточки: Personal (app.logera.space), Organizations ({org}.logera.space) |
| 4 | `#roles` | Роли и доступ | 3 карточки: Scopes, Регистрация и вход, Заявки в организацию |
| 5 | `#entities` | Ключевые сущности | 6 карточек: Project, Wiki Page, File, Call, Speaker, Person |
| 6 | `#admin` | Админ панель | 3 карточки: Requests, Users, Settings |
| 7 | `#states` | Состояния | 4 карточки: Account, Call, Page, Speaker (состояния каждой сущности) |
| 8 | — | Готовы начать? | CTA-блок с кнопками "Начать бесплатно" и "Войти" |

**Hero-секция детали:**
- Badge "Logera" + подпись "Вики с LLM-контекстом"
- H1: "Найдите ответ с цитатами из ваших страниц, файлов и звонков"
- Описание: "Загрузите файлы, добавьте Wiki, подключите звонки..."
- CTA: "Начать бесплатно" (→ APP_SIGNUP) + "Узнать больше" (→ #features)
- Логотип Logera (справа, скрыт на мобильных)
- Ссылки на реалмы Personal/Organizations
- Техническая заметка: "Сессии: access + httpOnly refresh; авто-рефреш, при сбое — выход"

### 1.4. Компоненты

#### Header (widgets/header/ui/Header.svelte)
- Sticky top, backdrop-blur, border-bottom
- Логотип (Logo short.svg) + текст "Logera"
- Навигация (md+): Функционал, Реалмы, Роли, Сущности, Админ, Состояния
- Кнопки: "Войти" (ghost) + "Начать бесплатно" (primary)
- Все ссылки на `APP_SIGNIN` / `APP_SIGNUP` (внешние, app.logera.space)

#### Footer (widgets/footer/ui/Footer.svelte)
- Grid: 4 колонки
- © {year} Logera + описание
- Навигация (те же 6 ссылок)
- "Начать бесплатно" ссылка

### 1.5. Стили и темизация (app.css)

- **Tailwind CSS 4** (через `@import "tailwindcss"`)
- **tw-animate-css** для анимаций
- **Тема:** oklch цветовая система (shadcn-svelte slate palette)
- **Dark mode:** Поддерживается через `.dark` класс (`@custom-variant dark`)
- **Радиус:** `--radius: 0.625rem` (10px)
- **CSS переменные:** 30+ переменных (background, foreground, card, primary, secondary, muted, accent, destructive, border, input, ring, chart-1..5, sidebar-*)
- **Анимаций:** Нет кастомных анимаций, только tw-animate-css (transitions)

### 1.6. SEO и метаданные

- `app.html`: lang="en", viewport meta, `data-sveltekit-preload-data="hover"`
- Favicon: Logo short.svg (через layout)
- `static/robots.txt`: всё разрешено (`Disallow:` пустой)
- **Нет:** title, description, OG-тегов, structured data, sitemap.xml

### 1.7. Серверная часть (Auth + DB)

#### Аутентификация (`shared/server/auth.ts`)
- Сессии на основе cookies (`auth-session`)
- Token: 18 random bytes → Base64url
- SessionId: SHA256(token) → hex
- Срок: 30 дней, авто-продление за 15 дней до истечения
- Хранение: PostgreSQL (через Drizzle ORM)
- Библиотеки: `@oslojs/crypto` (SHA256), `@oslojs/encoding` (Base64url, Hex)

#### База данных (`shared/server/db/`)
- **ORM:** Drizzle ORM
- **БД:** PostgreSQL (через `postgres` npm пакет)
- **Таблицы:**
  - `user`: id (text PK), age (int), username (text unique), password_hash (text)
  - `session`: id (text PK), user_id (FK → user), expires_at (timestamptz)

#### Hooks (`hooks.server.ts`)
- Middleware авторизации: валидация session cookie на каждый запрос
- Устанавливает `event.locals.user` и `event.locals.session`

#### Logout endpoint (`routes/api/auth/logout/+server.ts`)
- POST → invalidate session → delete cookie → 204 No Content

### 1.8. Зависимости

**Runtime:**
- `@node-rs/argon2` — хэширование паролей (Argon2)
- `@oslojs/crypto`, `@oslojs/encoding` — криптография
- `drizzle-orm` + `postgres` — ORM + PostgreSQL driver

**Dev (ключевые):**
- `svelte` ^5.0.0, `@sveltejs/kit` ^2.22.0
- `tailwindcss` ^4.0.0, `@tailwindcss/vite`, `@tailwindcss/forms`, `@tailwindcss/typography`
- `bits-ui` ^2.9.4 — headless UI компоненты
- `storybook` ^9.1.3 + addons (svelte-csf, docs, a11y, vitest, chromatic)
- `mdsvex` ^0.12.3 — Markdown в Svelte
- `layerchart` 2.0.0-next.27 — графики
- `embla-carousel-svelte` ^8.6.0 — карусели
- `sveltekit-superforms` ^2.27.1 — формы
- `formsnap` ^2.0.1 — form bindings
- `vaul-svelte` 1.0.0-next.7 — drawer
- `paneforge` ^1.0.2 — resizable panels
- `mode-watcher` ^1.1.0 — theme mode
- `svelte-sonner` ^1.0.5 — toast notifications

### 1.9. shadcn-svelte UI компоненты (~40 штук)

Полный набор из shadcn-svelte registry (slate base color):

accordion, alert, alert-dialog, aspect-ratio, avatar, badge, breadcrumb, button, calendar, card, carousel, chart, checkbox, collapsible, command, context-menu, data-table, dialog, drawer, dropdown-menu, form, hover-card, input, input-otp, label, menubar, navigation-menu, pagination, popover, progress, radio-group, range-calendar, resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider, sonner, switch, table, tabs, textarea, toggle, toggle-group, tooltip

### 1.10. Конфигурационные файлы landing-front/

| Файл | Описание |
|------|----------|
| `svelte.config.js` | Adapter-node, mdsvex, FSD aliases (@app, @pages, @widgets, @features, @entities, @shared, @ui, @comp, @utils, @hooks) |
| `vite.config.ts` | Tailwind CSS plugin, SvelteKit, devtools-json. allowedHosts: ["logera.space"] |
| `tsconfig.json` | Strict mode, path aliases дублирующие svelte.config |
| `drizzle.config.ts` | PostgreSQL, schema: `./src/lib/server/db/schema.ts` |
| `eslint.config.js` | TypeScript-eslint + svelte + prettier + storybook |
| `components.json` | shadcn-svelte config: slate base, aliases |
| `.prettierrc` | useTabs, singleQuote, trailingComma: none, printWidth: 100, svelte+tailwind plugins |
| `.prettierignore` | lock files, /static/, /drizzle/ |
| `.gitignore` | node_modules, .svelte-kit, build, .env.*, storybook |
| `.npmrc` | engine-strict=true |
| `.env.example` | `DATABASE_URL="postgres://root:mysecretpassword@localhost:5432/local"` |
| `README.md` | Стандартный шаблон sv create |

---

## 2. Storybook

### 2.1. Конфигурация (.storybook/)

**main.ts:**
- Framework: `@storybook/sveltekit`
- Stories: `../src/**/*.mdx`, `../src/**/*.stories.@(js|ts|svelte)`
- Addons:
  - `@storybook/addon-svelte-csf` — Svelte CSF формат
  - `@chromatic-com/storybook` — Chromatic интеграция
  - `@storybook/addon-docs` — документация
  - `@storybook/addon-a11y` — accessibility проверки
  - `@storybook/addon-vitest` — тестирование

**preview.ts:**
- Матчеры: color для background/color, date для Date полей
- Минимальная конфигурация (без тем, без декораторов)

### 2.2. Stories

**Отсутствуют!** В проекте нет файлов `*.stories.ts/svelte/mdx`. Storybook сконфигурирован, но stories не написаны.

**NPM скрипты:**
- `pnpm storybook` — dev на порту 6006
- `pnpm build-storybook` — build

---

## 3. docs/ — Документация (17 файлов, 7542 строк)

### 3.1. OVERVIEW.md (369 строк)

**Содержание:** Обзор системы Logera — "корпоративный второй мозг для команд".

**Ключевые возможности:** Транскрибация (ASR), диаризация, Speaker Linking (по голосовым эмбеддингам), универсальный поиск, multi-tenant, on-prem/SaaS.

**Mermaid диаграммы:**
1. Общая архитектура (flowchart TB) — Browser → Nginx → Frontend/Backend → Workers → Storage

**Список сервисов (18 штук):**
- web (FastAPI :8000), app-front (SvelteKit :3000), landing-front (SvelteKit :3001)
- nginx (:80), db (PostgreSQL :5432), redis (:6379), rabbitmq (:5672)
- minio (:9000), opensearch (:9200), qdrant (:6333)
- prometheus (:9090), grafana (:3000)
- Workers: media_prep (:8080), diarization (:8081 GPU), asr (:8082 GPU), speaker_linking (:8083), nlp_adapter (:8085), indexer (:8084), cleanup (:8087)

**Стек:** FastAPI + Peewee ORM, SvelteKit + TypeScript, Python workers, Docker Compose, Whisper/Pyannote/SpeechBrain ML модели.

---

### 3.2. DATA_MODELS.md (618 строк)

**Содержание:** Полная структура БД PostgreSQL (Peewee ORM).

**Mermaid диаграммы:**
1. ER-диаграмма — все сущности и связи (Organization, User, OrgMember, OrgGroup, FsNode, FsVersion, JobStatus, Transcript, TranscriptSegment, Summary, SpeakerProfile, TranscriptSpeaker, ProjectScope, OAuthClient, OAuthScope, UserScope, RefreshToken)

**Описанные сущности:**
- **Organization** — корневая multi-tenant (name, inn, subdomain, soft delete)
- **User** — email, login, password_hash, is_active, org FK
- **OrgMember** — role (OWNER/ADMIN/EDITOR/VIEWER)
- **OrgGroup / OrgGroupMembership** — группы в организации
- **FsNode** — виртуальная ФС (folder/file, parent-child иерархия)
- **FsVersion** — версии файлов (object_name → MinIO key)
- **JobStatus** — статус обработки медиа
- **Transcript / TranscriptSegment** — транскрипты и сегменты
- **Summary** — саммари звонков
- **SpeakerProfile / TranscriptSpeaker** — профили спикеров
- **ProjectScope** — области проектов (изоляция внутри org)
- **OAuth**: OAuthClient, OAuthScope, UserScope, RefreshToken

Для каждой сущности: таблица полей с типами, описанием, индексы.

---

### 3.3. AUTH_FLOW.md (430 строк)

**Содержание:** OAuth2 авторизация (RFC 6749).

**Grant types:** password, client_credentials, refresh_token, authorization_code (planned).

**Mermaid диаграммы:**
1. Архитектура (flowchart TB) — Clients → AuthServer → ResourceServer → Storage
2. ER-диаграмма — User, RefreshToken, OAuthClient, OAuthScope, UserScope
3. Password Grant flow (sequenceDiagram)
4. Client Credentials flow (sequenceDiagram)
5. Token Refresh flow (sequenceDiagram)

**Детали:** JWT (HS256), access token 30 min, refresh token 7 days, Redis token blacklist, scope-based access control. CORS: regex `https://.*\.logera\.space`.

---

### 3.4. AMQP_EVENTS.md (513 строк)

**Содержание:** RabbitMQ межсервисная коммуникация.

**Mermaid диаграммы:**
1. Архитектура (flowchart TB) — Publishers → RabbitMQ (exchanges, queues) → Consumers
2. Pipeline flow (sequenceDiagram) — полная цепочка обработки

**Exchanges:** `logera.jobs` (topic), `logera.dlx` (dead letter).

**Очереди (8):** q.media_prep, q.diarization, q.asr, q.speaker_linking, q.nlp_adapter, q.indexer, q.cleanup, q.backend.

**Routing keys:** job.created → media.prepared → dia.ready → asr.ready/link.ready → indexed.ready/nlp.ready

**Каждое событие:** payload JSON schema с полями (job_id, org_id, node_id, version, ключи MinIO).

---

### 3.5. MEDIA_PIPELINE.md (605 строк)

**Содержание:** Основной бизнес-процесс — конвейер обработки медиа.

**Mermaid диаграммы:**
1. Общая схема (flowchart LR) — Upload → media_prep → diarization → ASR + speaker_linking (параллельно) → nlp + indexer (параллельно) → cleanup
2. Диаграмма последовательности (sequenceDiagram) — User → API → MinIO → Workers → DB/Qdrant/OpenSearch

**8 этапов pipeline:** Upload, media_prep (FFmpeg + Silero VAD), diarization (Pyannote GPU), ASR (Whisper GPU), speaker_linking (SpeechBrain + Qdrant), nlp_adapter (YAKE + Natasha NER), indexer (OpenSearch), cleanup (удаление temp файлов).

Каждый этап: входные данные, обработка, выходные данные, хранение.

---

### 3.6. FILE_STORAGE.md (383 строки)

**Содержание:** MinIO + FsNode виртуальная файловая система.

**Mermaid диаграммы:**
1. Архитектура (flowchart TB) — API → storage_service → MinIO buckets

**Модели:** FsNode (folder/file, иерархия, soft delete), FsVersion (версионирование, object_name → MinIO key).

**Структура MinIO:**
```
org-{id}/originals/{node_id}/file.ext
org-{id}/prepared/{node_id}/audio.wav
org-{id}/diarization/{node_id}/segments.jsonl
org-{id}/asr/{node_id}/segments.jsonl
org-{id}/link/{node_id}/speakers.json
personal/user-{id}/originals/{node_id}/
```

**API endpoints:** POST /api/v1/files (upload), GET (download), GET /api/v1/files/{id}/versions.

---

### 3.7. ORGANIZATIONS.md (448 строк)

**Содержание:** Multi-tenant модель.

**Mermaid диаграммы:**
1. Multi-tenant архитектура (flowchart TB) — Organizations → изолированные хранилища (MinIO buckets, Qdrant collections)
2. Регистрация (sequenceDiagram)
3. Роли и права (flowchart LR)

**Роли:** OWNER, ADMIN, EDITOR, VIEWER. Scopes: org:members:*, org:settings:*, org:groups:*.

**Изоляция данных:** MinIO (org-{id}/ buckets), Qdrant (speakers_{org_id} collections), OpenSearch (asr_segments-org{id} индексы), PostgreSQL (org_id filter).

**Субдомены:** `{org}.logera.space` — каждая организация на своём субдомене.

---

### 3.8. SPEAKER_LINKING.md (483 строки)

**Содержание:** Связывание спикеров между встречами по голосовым эмбеддингам.

**Mermaid диаграммы:**
1. Архитектура (flowchart TB) — speaker_linking worker → SpeechBrain → Qdrant → PostgreSQL
2. Поток данных (sequenceDiagram) — diarization → speaker_linking → Qdrant search → Backend consumer

**Алгоритм:**
1. Получение dia.ready
2. Загрузка аудио + diarization segments из MinIO
3. Для каждого speaker: извлечение embedding (SpeechBrain ECAPA-TDNN, 192-dim)
4. Поиск в Qdrant (cosine similarity, threshold=0.68)
5. Match → существующий SpeakerProfile, No match → новый профиль
6. Upsert embedding в Qdrant
7. Publish link.ready

**Коллекции Qdrant:** `speakers_{org_id}` (192-dim vectors).

---

### 3.9. SEARCH.md (418 строк)

**Содержание:** Полнотекстовый поиск (OpenSearch).

**Mermaid диаграммы:**
1. Архитектура (flowchart LR) — Backend API → OpenSearch / Indexer worker → OpenSearch

**Индексы:** `asr_segments-org{id}` (один на организацию).

**Mapping fields:** org_id, node_id, version, start_ms, end_ms, speaker_id, text (text type, standard analyzer).

**API:** GET /api/v1/search — query, org_id, file_id, speaker_id, date range filters. Highlighting поддерживается.

---

### 3.10. TEXT_EMBEDDINGS.md (636 строк)

**Содержание:** Семантический поиск по текстам (транскрипты + документы).

**Коллекции Qdrant:**
- `speakers_{org_id}` — 192-dim (голосовые эмбеддинги)
- `texts_{org_id}` — 1536-dim или 384-dim (текстовые эмбеддинги)

**Провайдеры:** LiteLLM (default, text-embedding-3-small) или local (sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2).

**Поддерживаемый контент:** Транскрипты (сегменты с таймкодами), документы (PDF, DOCX, MD, XLSX, PPTX).

**API:** upsert_text_chunks, search_similar_texts, get_context_for_rag, TextSearchFilters.

---

### 3.11. ENV_VARIABLES.md (403 строки)

**Содержание:** Полный список переменных окружения для всех сервисов.

**Секции:** App settings, PostgreSQL, Redis, MinIO, JWT/OAuth, CORS/Security, RabbitMQ/AMQP, Email, OpenSearch, Qdrant, Workers, LLM (LiteLLM).

Каждая переменная: имя, значение по умолчанию, описание.

---

### 3.12. INFRASTRUCTURE.md (436 строк)

**Содержание:** Docker Compose окружение.

**Mermaid диаграммы:**
1. Архитектура сети (flowchart TB) — External → nginx → Apps/Backend/Workers → Storage

**Файлы:** docker-compose.yml (production), docker-compose.dev.yml (development с GPU).

**Сервисы:** 18+ сервисов с портами, образами, зависимостями, health checks. GPU workers с nvidia-container-toolkit.

**Сети:** logera-network (bridge). Volumes для persistent данных.

---

### 3.13. LOCAL_SETUP.md (384 строки)

**Содержание:** Пошаговая инструкция по локальному запуску.

**Требования:** Docker 24+, Docker Compose 2.20+, Node.js 20+, pnpm 8+, NVIDIA GPU (для GPU workers).

**Шаги:** Clone → .env → docker-compose up → миграции → seed OAuth client → проверка health.

---

### 3.14. MACOS_M4_SETUP.md (244 строки)

**Содержание:** Гибридный запуск на macOS M4.

**Проблема:** Docker на macOS не даёт доступ к MPS (Metal Performance Shaders).

**Решение:** Инфраструктура в Docker, GPU workers (ASR + Diarization) нативно на macOS с `DEVICE_TYPE=mps`.

**Шаги:** Docker up (без GPU workers) → venv → pip install → .env.local → python main.py.

---

### 3.15. MONITORING.md (359 строк)

**Содержание:** Prometheus + Grafana мониторинг.

**Mermaid диаграммы:**
1. Архитектура (flowchart LR) — Workers metrics → Prometheus → Grafana

**Метрики workers:** jobs_processed_total, job_duration_seconds, jobs_errors_total, jobs_in_progress.

**Grafana dashboards (5):** Pipeline Overview, Worker Overview, RabbitMQ Overview, GPU Overview, Webhooks Overview.

**Алерты:** WorkerDown, HighErrorRate, QueueBacklog, GPUMemoryHigh.

---

### 3.16. WEBHOOKS.md (315 строк)

**Содержание:** HTTP уведомления для внешних систем.

**События:** media.prepared, dia.ready, asr.ready, link.ready, nlp.ready, indexed.ready.

**Формат:** POST + JSON payload, X-Logera-Event header, HMAC подпись (SHA256).

**Retry:** 3 попытки с exponential backoff.

---

### 3.17. DOCUMENTATION_TASKS.md (498 строк)

**Содержание:** Трекер задач по документации.

**Описание проекта:** Logera — корпоративный «второй мозг» для команд.

**Стек:** FastAPI, Peewee ORM, PostgreSQL 17, SvelteKit, TypeScript, Whisper, Pyannote, Docker, RabbitMQ, MinIO, Redis, OpenSearch, Qdrant, Prometheus, Grafana.

**Статус задач:** Большинство P0/P1 документов помечены как [✓] завершённые.

---

## 4. Корневые скрипты и файлы

### 4.1. analyze_coverage.py

Python-скрипт анализа покрытия между VAD chunks → diarization → ASR segments. Загружает `chunks.json`, `segments (4).jsonl` (diarization), `segments (3).jsonl` (ASR). Выводит: статистику потерь, покрытие VAD, потерянные диапазоны, анализ по спикерам, сегменты вне VAD.

### 4.2. Исследование по ASR.md

Обширный исследовательский документ (~500+ строк) описывающий многоэтапный конвейер:
1. **VAD** — Silero VAD (MIT), threshold 0.5, 1ms на 30ms фрагмент
2. **Диаризация** — PyAnnote 3.x (сегментация, ECAPA-TDNN эмбеддинги 192-dim, AHC кластеризация, overlap detection/handling)
3. **ASR** — Whisper Large-v2 (5-10% WER на русском) vs Silero STT (7-10% WER)
4. **Speaker Linking** — Постобработка спикеров, matching эмбеддингов

Подробные примеры кода (PyTorch, whisper, silero), анализ overlap speech, оценки производительности.

---

## 5. Конфигурационные файлы (корень)

### 5.1. AGENTS.md (~300 строк)

Руководство для AI-ассистента (WARP). Содержит:
- Обзор проекта и стека
- Все команды разработки (Docker, Backend, Frontend, Workers, миграции, тесты)
- Архитектура: Event Flow pipeline (8 этапов), AMQP topology
- Модели данных (core entities, artifacts, индексы)
- MinIO Storage Structure
- Критические паттерны: идемпотентность, оптимизация памяти, tenant isolation, AMQP publishing, MinIO операции
- Multi-tenancy (изоляция данных)
- Speaker Linking алгоритм
- OAuth2 & Security
- Известные техдолги (9 пунктов)
- Шаблон нового воркера

### 5.2. PLAN.md (~700+ строк)

Детальное ТЗ на NLP Worker с Cross-Call Context, Person Management и Memory System:
- **Summary Generation** с cross-call context (hybrid search: semantic + entity-based), explainability
- **Action Items Extraction** с связями между звонками (resolves/continues/blocks)
- **Person Candidate Management** — workflow создания персон для спикеров (LLM extraction → pending → approve/reject/edit)
- **Person Memory System** — заметки: preference, fact, relationship, history
- **Data Model:** 4 новые таблицы (action_items, context_references, person_candidates, person_notes) + расширения speaker_profile, summaries
- **LLM Service:** LangChain + OpenAI (gpt-4o-mini), ContextRetrievalService, PersonManagementService
- **API Endpoints:** Summaries, Action Items, Person Candidates, Person Notes (CRUD)
- **Security:** tenant isolation, access filtering, zero leaks
- **Observability:** Prometheus метрики, structured logging
- **Тесты:** Unit, Integration, Security
- **Миграции:** migration 008_nlp_worker_full.py
- **Timeline:** 5 недель (Foundation → Advanced → Production Ready)

### 5.3. IMPLEMENTATION_SUMMARY.md

Итоги оптимизации хранилища:
- Оптимизированные handlers (media_prep, asr)
- Cleanup worker (новый, порт 8087)
- Результат: -84% storage/file, -92% objects/file, -80-90% ASR load time

### 5.4. TECHNICAL_ANALYSIS_REPORT.md

Детальный архитектурный анализ (1500+ строк). Executive Summary + Repo Map + критические gaps (folder_id, PersonCandidate, NLP, RAG, tenant leaks).

### 5.5. .gitignore (корневой)

Сгенерирован toptal.com для Python + PyCharm. Исключает: __pycache__, .env, venv, .idea, build, dist, coverage, models/whisper/.

### 5.6. .claude/settings.local.json

Разрешения для Claude Code: python, find, grep, pnpm, docker, curl, web fetch (GitHub, OnlyOffice, PyPI, LiteLLM, LangChain).

### 5.7. .vscode/launch.json

Chrome debug config → `https://lumines-fox.logera.space/`, webRoot: `app-front`.

### 5.8. nginx/

**nginx.conf** (production): upstream backend(:8000) + frontend(:3000) + onlyoffice(:80). SSE support (buffering off, 24h timeout), /api/ → backend, /docs → backend, /onlyoffice/ → onlyoffice, / → frontend. client_max_body_size 500M.

**nginx.dev.conf** (development): Аналогичный, frontend на :5173 (Vite dev), WebSocket upgrade map.

---

## 6. Сводная таблица

| Компонент | Технология | Строки кода | Статус |
|-----------|-----------|-------------|--------|
| landing-front | SvelteKit 5 + Tailwind 4 | ~300 (custom) + ~5000 (shadcn) | MVP, русский текст |
| docs/ | Markdown + Mermaid | 7542 строк, 17 файлов | Завершено (P0/P1) |
| Storybook | Storybook 9 + SvelteKit | Конфиг есть, stories нет | Не начато |
| PLAN.md | Markdown | ~700 строк | ТЗ готово |
| AGENTS.md | Markdown | ~300 строк | AI-руководство |
| nginx | nginx.conf | 2 конфига (prod/dev) | Рабочий |

---

## 7. Выводы и наблюдения

1. **Лендинг в состоянии MVP** — одна страница, 8 секций, русский контент, нет кастомных анимаций, SEO минимальный
2. **shadcn-svelte полностью установлен** (~40 компонентов), но большинство не используется на лендинге
3. **Storybook сконфигурирован**, но stories не написаны
4. **Auth система полноценная** (sessions, Argon2, PostgreSQL через Drizzle) — избыточна для лендинга
5. **Документация обширная** (7500+ строк) — покрывает все аспекты системы
6. **Нет Makefile, .editorconfig** в корне
7. **Два фронтенда:** app-front (основное приложение) и landing-front (лендинг) — разные проекты с общим UI kit
