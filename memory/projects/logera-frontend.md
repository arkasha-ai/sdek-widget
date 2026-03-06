# Logera Frontend — Полный справочник модуля `app-front/`

> **Ветка:** `feature/design-improvements`  
> **Фреймворк:** SvelteKit (Svelte 5) + Tailwind CSS 4  
> **Архитектура:** Feature-Sliced Design (FSD)  
> **Adapter:** `@sveltejs/adapter-node`  
> **Дата анализа:** 2026-02-14

---

## Содержание

1. [Общая архитектура](#1-общая-архитектура)
2. [Маршруты и страницы](#2-маршруты-и-страницы)
3. [Entities](#3-entities)
4. [Features](#4-features)
5. [Widgets](#5-widgets)
6. [Shared](#6-shared)
7. [Pages](#7-pages)
8. [Стили и темы](#8-стили-и-темы)
9. [Зависимости](#9-зависимости)
10. [Конфигурация](#10-конфигурация)

---

## 1. Общая архитектура

### FSD-структура

```
src/
├── app.css                    # Глобальные стили + Tailwind + CSS variables (тема)
├── app.html                   # HTML шаблон SvelteKit
├── app.d.ts                   # Глобальные TypeScript типы (App.Locals)
├── hooks.server.ts            # Server hooks (multi-tenant org resolution)
├── types/                     # Ambient type declarations (.d.ts)
├── routes/                    # SvelteKit маршруты
├── pages/                     # FSD pages (композиция виджетов)
├── widgets/                   # FSD widgets (самостоятельные UI-блоки)
├── features/                  # FSD features (auth)
├── entities/                  # FSD entities (fs, chat, user, etc.)
├── shared/                    # FSD shared (UI kit, утилиты, API client)
└── processes/                 # FSD processes (пока пуст)
```

### Path aliases (svelte.config.js + tsconfig.json)

| Alias | Путь |
|-------|------|
| `@shared` | `src/shared` |
| `@ui` | `src/shared/ui` |
| `@comp` | `src/shared/components` |
| `@utils` | `src/shared/utils.ts` |
| `@hooks` | `src/shared/hooks` |
| `@widgets` | `src/widgets` |
| `@pages` | `src/pages` |
| `@features` | `src/features` |
| `@entities` | `src/entities` |
| `@processes` | `src/processes` |
| `$lib` | `src/shared/lib` |

---

## 2. Маршруты и страницы

### hooks.server.ts — Server Hooks

**Multi-tenant organization resolution по субдомену:**
- Извлекает субдомен из hostname (`{org}.logera.space`)
- Резолвит организацию через API: `GET /api/organizations/resolve/{subdomain}`
- Записывает `event.locals.org` (тип `OrganizationRead | null`)
- `www` и `app` субдомены игнорируются

### Root Layout

#### `+layout.server.ts`
- Передаёт `user` (из locals) и `org` (из locals) на клиент
- Scopes загружаются на клиенте

#### `+layout.ts` (universal load)
- Устанавливает `currentUser`, `currentOrg`, `currentScopes` в shared stores
- Вызывает `getMeFull(fetch)` — `/api/users/me/full` для получения полного профиля + scopes
- Обновляет stores при успехе, молча обрабатывает ошибки

#### `+layout.svelte`
- Подключает `app.css`
- Показывает `Header` виджет (скрыт на auth-страницах)
- Redirect на `/auth/login` если нет access token (через `onMount`)
- Используется favicon из `Logo short.svg`

### `/ (root)` — `+page.svelte`
- Рендерит `HomePage` из `@pages/app/Page.svelte`
- Redirect на `/auth/register` если нет токена

---

### Auth маршруты (`/auth/`)

#### `+layout@.svelte` (breaks layout inheritance — `@`)
- Собственный layout: центрированная карточка на градиентном фоне
- Декоративные размытые круги (brand-цвет)
- Показывает лого Logera, название организации (если есть)
- Card с `backdrop-blur`

#### `+layout.server.ts`
- Передаёт `org` из locals

#### `+page.server.ts`
- Redirect `/auth` → `/auth/login` (307)

#### `/auth/login` — Страница входа
- Поля: email, password (с toggle показа пароля)
- Кнопка "Войти" → `loginWithPassword()` → redirect `/profile`
- Ссылки на регистрацию и создание организации
- UI: Eye/EyeOff иконки, disabled при загрузке, ошибки

#### `/auth/register` — Регистрация пользователя
- Поля: first_name, last_name, email, phone, password
- Логика:
  - Если субдомен орг → `POST /api/oauth2/organisation/user/register` + redirect `/auth/pending`
  - Иначе → `POST /api/oauth2/register` → сохраняет токены → redirect `/profile`
- Показ/скрытие пароля, обработка ошибок

#### `/auth/register-org` — Создание организации
- Поля организации: name, inn, subdomain (`.logera.space`)
- Поля администратора: first_name, last_name, email, phone, password
- `registerOrganisation()` → сохраняет токены → redirect `/org`

#### `/auth/pending` — Ожидание одобрения
- Информационная страница после регистрации в организации
- Показывает email из query param
- Ссылка "Вернуться ко входу"

---

### Profile маршруты (`/profile/`)

#### `+layout.svelte` — Layout профиля
- Sidebar навигация (8 пунктов) с иконками Lucide
- Mobile: hamburger + overlay sidebar
- Auth guard: redirect на login если нет токена
- Загружает `getMeFull()` → обновляет stores
- Навигация:
  - `/profile` — Профиль (User)
  - `/profile/voice` — Голос (Mic)
  - `/profile/ai-settings` — AI настройки (Bot)
  - `/profile/security` — Безопасность (Shield)
  - `/profile/notifications` — Уведомления (Bell)
  - `/profile/usage` — Использование (BarChart3)
  - `/profile/organization` — Организация (Building2)
  - `/profile/billing` — Тарифы (CreditCard)

#### `/profile` — Основной профиль
- Аватар с инициалами (градиент), hover для камеры
- Форма: имя, фамилия, email (disabled), телефон
- Кнопки: Сохранить, Отмена

#### `/profile/voice` — Голосовой профиль
- Запись голосового образца (микрофон)
- Загрузка файла (WAV, MP3 до 10 МБ)
- Список образцов: Play, Badge "Активен", Delete
- Для улучшения распознавания спикера

#### `/profile/ai-settings` — AI настройки
- Стиль саммари: Краткий / Подробный / Список (карточки-выбор)
- Язык обработки: RU / EN / Авто
- Автоматизация: Автообработка, Детекция спикеров (Switch)
- Кастомный промпт (Textarea)

#### `/profile/security` — Безопасность
- Смена пароля (текущий, новый, подтверждение)
- 2FA (кнопка "Включить")
- Активные сессии: устройство, IP, дата, "Завершить"

#### `/profile/notifications` — Уведомления
- Каналы: Email, Push (Switch)
- События: Транскрипция завершена, Саммари готово, Еженедельный дайджест, Хранилище < 10%

#### `/profile/billing` — Тарифы (пустая страница)
#### `/profile/usage` — Использование (пустая страница)
#### `/profile/organization` — Организация (пустая страница)

---

### Org маршруты (`/org/`)

#### `/org` — Главная страница организации
- **Обзор:** Реквизиты (название, ИНН, поддомен, лимиты), Активность (заглушка графика), Последние изменения
- **Пользователи:** Заявки на вступление (approve), Участники (таблица с ролями, правами, удалением)
- **OAuth клиенты:** CRUD, rotate secret
- **Настройки:** Ограничение заявок, автоодобрение, удаление организации (soft delete)
- Боковая панель: быстрые действия, документация API, подписка
- Диалоги: редактирование орг, приглашение по email, управление правами (scopes), подтверждение удаления, создание клиента

#### `/org/members` — Участники
- Server-side guard: `requireAuth` + `requireScopes(MEMBERS_READ)`
- Таблица: ID, ФИО, Email, Роль (Badge), Действия
- Действия: Сменить роль (dropdown), Выдать scope, Права, Удалить
- Диалоги: Добавить участника, Выдать scope, Подтвердить удаление

#### `/org/clients` — OAuth клиенты
- Таблица: client_id (monospace), Название, Статус, Действия
- Создание клиента (name, scopes)
- Ротация секрета, удаление

#### `/org/groups` — Группы
- CRUD групп (name, description)
- Scope guard: `GROUPS_WRITE`
- Таблица + диалог создания/редактирования

---

### API Routes (server-side)

#### `/api/search` — `GET`
- Mock search endpoint для поиска по файлам/сегментам/задачам
- Параметры: `q`, `types`, `cursor`, `limit`, `folder`, `project`, `speaker`, `date_from`, `date_to`
- Возвращает: `{ items, total, nextCursor, counts }`
- Строит сниппеты с контекстом (±40/60 символов)

#### `/api/search/context` — `POST`
- Прокси к backend API (`/api/search/context` или `/api/v1/search/context`)
- Пробрасывает Authorization, X-Org-Domain, cookies
- Fallback на `/api/v1/...` при 404

---

## 3. Entities

### 3.1 `entities/fs` — Файловая система

**Экспорт:** `types`, `store`, `api`

#### Типы (`model/types.ts`)
```ts
type FsNodeType = "folder" | "file";
type TreeItem = {
  id: string;
  type: FsNodeType;
  name: string;
  open?: boolean;
  children?: TreeItem[];
  shared?: boolean;
  readOnly?: boolean;
  isLoadingChildren?: boolean;
  childrenLoaded?: boolean;
  projectScopeId?: number | null;
};
type BreadcrumbSeg = { id: string; label: string };
```

#### Store (`model/store.ts`) — `fsStore`
Центральный store файловой системы. Svelte writable stores:
- `tree` — дерево файлов/папок
- `breadcrumb` — хлебные крошки
- `currentOpenFileId` — ID открытого файла (синхронизируется с URL `?file=ID`)
- `currentFileMeta` — метаданные файла (id, name, mime, version)
- `layoutSplit` — пропорции разделителя (group + percent)
- `loading` — флаг загрузки
- `selectedIds` — множество выделенных ID
- `expandedIds` — множество раскрытых папок (persisted в localStorage)
- `uploadQueue` — очередь загрузки файлов

**Ключевые методы:**
- `loadTree()` — загрузка корня из API
- `openFile(node)` — открыть файл, обновить breadcrumb, dispatch `open-app-document`
- `closeCurrentFile()` — закрыть файл, dispatch `close-app-document`
- `toggleFolder(node)` — раскрыть/свернуть папку (lazy load детей)
- `moveNode(nodeId, targetFolderId)` — перемещение с валидацией (depth limit 5, no self-nesting)
- `enqueueUploads(targetFolderId, files)` — multipart upload через XHR с прогрессом
- `createMarkdownFile(name, parentId)` — создание .md файла
- `createFolder(name, parentId)` — создание папки
- `removeById(id)` / `removeByIds(ids)` — удаление с откатом при ошибке
- `renameNode(targetId, newName)` — переименование
- `updateNodeProjectScope(nodeId, scopeId)` — обновление project scope в дереве

**Persistence:** `expandedIds` и `breadcrumb path` сохраняются в localStorage. Текущий файл — в URL (`?file=ID`).

**Upload:** XHR multipart `POST /api/files/upload` с `Authorization: Bearer`, `X-Org-Domain`, прогресс через `xhr.upload.onprogress`.

#### API (`api/mock.ts`) — `fsApi`
Несмотря на имя "mock", это реальные API вызовы:
- `list(path)` → `GET /api/files?parent_id=...` → `TreeItem[]`
- `getDownloadUrl(id)` → `GET /api/files/{id}/download` → `{ url, expires_in }`
- `uploadVersion(id, file)` → `POST /api/files/{id}/upload-version`
- `create(parentId, node)` → `POST /api/files/folders` (для папок, form-encoded)
- `rename(id, name)` → `PATCH /api/files/{id}/rename`
- `remove(id)` → `DELETE /api/files/{id}?hard=true`
- `move(id, targetParentId)` → `PATCH /api/files/{id}/move`

#### API (`api/versions.ts`)
- `listVersions(nodeId)` → `GET /api/files/{nodeId}/versions`
- `restoreVersion(nodeId, version)` → `POST /api/files/{nodeId}/restore`

---

### 3.2 `entities/chat` — Чат с LLM

**Экспорт:** `types`, `api`

#### Типы (`model/types.ts`)
```ts
interface Conversation { id, title, projectScopeId, totalTokensUsed, createdAt, updatedAt }
interface ChatMessage { id, role: 'user'|'assistant'|'tool', content, toolCalls?, toolName?, model?, tokensUsed?, isStreaming? }
interface ToolCall { id, type: 'function', function: { name, arguments } }
interface ContextItem { type: 'segment'|'file'|'folder'|'wiki'|'text', id, label, nodeId?, tokens?, text? }
interface SSEEvent {
  type: 'token'|'tool_call'|'tool_result'|'edit_command'|'read_structure_request'|'user_input_request'|'done'|'error';
  data: { text?, id?, name?, arguments?, action?, js_code?, question?, options?, ... }
}
```

**SSE Event Types:**
- `token` — streaming текст
- `tool_call` — LLM вызывает инструмент
- `tool_result` — результат инструмента
- `edit_command` — команда редактирования OnlyOffice Connector (`action`, `js_code`)
- `read_structure_request` — запрос структуры документа для spreadsheet/document
- `user_input_request` — Human-in-the-Loop: вопрос с опциями
- `done` / `error`

#### API (`api/chat.ts`)
- `createConversation(request?)` → `POST /api/v1/chat/conversations`
- `getConversation(id, limit, offset)` → `GET /api/v1/chat/conversations/{id}`
- `listConversations(limit, offset, projectScopeId?)` → `GET /api/v1/chat/conversations`
- `deleteConversation(id)` → `DELETE /api/v1/chat/conversations/{id}`
- `streamMessage(conversationId, content, contextItems, activeDocumentId?)` → async generator SSE
  - `POST /api/v1/chat/conversations/{id}/messages/stream`
  - Поддерживает `active_document_id` для document editing через OnlyOffice Connector
  - Парсит SSE `data:` lines, yield `SSEEvent`

---

### 3.3 `entities/user` — Пользователи и организация

#### API (`api.ts`)
**User:**
- `getMe()` → `/api/oauth2/me`
- `getUserInfo()` → `/api/oauth2/userinfo`
- `getMeFull(fetch?)` → `/api/users/me/full` → `{ user, scopes }`

**Scopes:**
- `grantUserScope(userId, scope)` → `POST /api/users/{id}/scopes`
- `getUserScopes(userId)` → `GET /api/users/{id}/scopes`
- `revokeUserScope(userId, scope)` → `DELETE /api/users/{id}/scopes/{scope}`
- `listAllScopes()` → `GET /api/users/scopes`

**Org Members:**
- `orgListMembers()` → `GET /api/org/members`
- `orgAddMember(body)` → `POST /api/org/members`
- `orgUpdateMemberRole(userId, body)` → `PATCH /api/org/members/{id}`
- `orgRemoveMember(userId)` → `DELETE /api/org/members/{id}`
- `orgListPendingUsers()` → `GET /api/org/members/pending`
- `approveOrgUser(body)` → `POST /api/oauth2/organisation/user/approve`

**Org Groups:**
- `orgListGroups()` / `orgCreateGroup()` / `orgUpdateGroup()` / `orgDeleteGroup()` → `/api/org/groups`

**Org OAuth Clients:**
- `orgListClients()` / `orgCreateClient()` / `orgRotateClientSecret()` / `orgDeleteClient()` → `/api/org/clients`

#### Типы (`types.ts`)
```ts
type AuthUser = { id: string; username: string };
```

---

### 3.4 `entities/organization` — Организации

#### API (`api.ts`)
- `registerOrganisation(body)` → `POST /api/oauth2/organisation/register` (form-encoded)
- `resolveOrganisationBySubdomain(sub)` → `GET /api/organizations/resolve/{sub}`
- `listOrganizations()` → `GET /api/organizations`
- `getOrganization(id)` → `GET /api/organizations/{id}`
- `updateOrganization(id, data)` → `PATCH /api/organizations/{id}`
- `deleteOrganization(id)` → `DELETE /api/organizations/{id}`

---

### 3.5 `entities/job-status` — Статус обработки файлов

#### Store (`model/store.ts`) — `createJobStatusController()`
- Реактивный контроллер отслеживания статуса job (транскрипция, диаризация и т.д.)
- `setNode(nodeId, version?)` — получает jobId через `GET /api/v1/jobs/by-node/{id}`, подписывается на SSE `/api/v1/jobs/{jobId}/events`
- `reset()` — сброс
- `destroy()` — cleanup SSE

#### Состояние: `{ jobId, status, lastEvent }`

**Статусы job:** `created` → `prepared` → `dia_ready` → `asr_ready` → `link_ready` → `indexed` | `error`

#### UI: `JobStatusBadge.svelte`
- Badge с иконкой Loader2 (spinner для in-progress статусов)
- Лейблы: Загружен, Подготовка, Диаризация, Распознавание, Линковка, Готово, Ошибка

#### Context (`model/context.ts`)
- Синглтоны: `jobStatusController`, `jobStatusState`

---

### 3.6 `entities/person-candidates` — Кандидаты-спикеры

**Для привязки извлечённых имён/компаний к пользователям организации.**

#### Типы (`types.ts`)
```ts
interface PersonCandidate { id, speaker_profile_id, extracted_name, extracted_company, extracted_position, source_node_id, confidence, status: 'pending'|'approved'|'rejected', ... }
interface PersonCandidateExtended extends PersonCandidate { speaker_label, current_name, linked_user_id, ... }
interface PersonCandidateApproveData { name?, company?, position?, link_user_id? }
interface OrgMember { user_id, user: { id, email, first_name?, last_name? } }
```

#### API (`api.ts`)
- `getByFile(nodeId, status?)` → `GET /api/v1/person-candidates/files/{nodeId}`
- `approve(candidateId, data)` → `POST /api/v1/person-candidates/{id}/approve`
- `reject(candidateId)` → `POST /api/v1/person-candidates/{id}/reject`
- `getOrgMembers()` → `GET /api/org/members`

#### Store (`model/store.ts`)
- `pendingCounts` — Map<nodeId, count>
- `currentFileId` — текущий файл
- `pendingCandidatesCount` — derived count для текущего файла
- `refreshPendingCount(nodeId)`, `clearPendingCount(nodeId)`

---

### 3.7 `entities/project-scope` — Проектные контексты

**Группировка файлов по проектам.**

#### Типы (`model/types.ts`)
```ts
interface ProjectScope { id, org_id, owner_user_id, name, description, is_archived, created_at, updated_at }
interface ProjectScopeCreate { name, description? }
interface ProjectScopeUpdate { name?, description?, is_archived? }
```

#### API (`api.ts`)
- `list(includeArchived?)` → `GET /api/projects`
- `get(id)` → `GET /api/projects/{id}`
- `create(data)` → `POST /api/projects`
- `update(id, data)` → `PATCH /api/projects/{id}`
- `archive(id)` → `update(id, { is_archived: true })`
- `assignToNode(nodeId, projectScopeId)` → `PATCH /api/files/{nodeId}/project-scope` (FormData)

#### Store (`model/store.ts`)
- `projectScopeStore` — writable<ProjectScope[]> с методами load/create/updateScope/archive/reset
- `activeProjects` — derived store (не архивные)

#### UI: `ProjectScopeAssignDialog.svelte`
- Dialog для назначения проекта файлу/папке
- Select из существующих проектов + кнопка "Создать новый"
- Форма создания: name, description

---

## 4. Features

### 4.1 `features/auth` — Аутентификация

#### API (`api.ts`)
- `postLogout()` → `POST /api/auth/logout`
- `token(body)` → `POST /api/oauth2/token` (form-encoded)
- `oauthLogout(clientId?)` → `POST /api/oauth2/logout`

#### Store (`store.ts`)
- `authState` — writable `{ isAuthenticated, loading, error }`
- `loginWithPassword(username, password)` — определяет `client_id` по субдомену (`org_{sub}_web` или `default_web_client`), запрашивает scope (read, write, profile, email, org:*), сохраняет токены
- `logoutLocal()` — очистка токенов + state
- `logoutAll()` — server logout + local cleanup

#### UI: `AuthTabsHeader.svelte`
- Tabs "Вход" / "Регистрация" с ссылками на `/auth/login` и `/auth/register`

---

## 5. Widgets

### 5.1 `widgets/header` — Header

**`Header.svelte`** — Sticky header приложения:
- Лого Logera (ссылка на `/`)
- Кнопка toggle sidebar (mobile, dispatches `toggle-app-sidebar`)
- Dropdown организации (если есть): Обзор, Участники, Группы (с Can guards)
- User dropdown: аватар с инициалами, имя, email → Профиль и настройки, Выйти

### 5.2 `widgets/footer` — Footer

**`Footer.svelte`** — Footer лендинга:
- © Logera, описание "Вики с LLM-контекстом и цитатами"
- Навигация по якорям (#features, #realms, #roles, #entities, #admin, #states)
- Ссылка "Начать бесплатно" → `APP_SIGNUP`

### 5.3 `widgets/profile` — Profile Preview

**`Preview.svelte`** — Card с базовой информацией:
- Имя, email, организация
- Кнопка "Перейти в профиль"

### 5.4 `widgets/search-panel` — SearchPanel

**`SearchPanel.svelte`** — Полнотекстовый поиск:
- Input с иконкой Search + горячая клавиша `Ctrl+K`
- HoverCard с подсказками синтаксиса (области `/Wiki`, типы, спикеры, даты)
- Debounce 350ms, кеширование результатов (TTL 60s)
- Сортировка: релевантность, дата, имя
- Группировка результатов по `path`
- Infinite scroll (IntersectionObserver)
- Навигация по результатам (Arrow Up/Down, Enter)
- Highlight найденного текста
- При клике: dispatch `open-app-document` и `seek-to-timecode`

### 5.5 `widgets/app-main` — Основной рабочий виджет

**Главный виджет приложения** содержит файловую систему, viewer, редакторы, транскрипт, саммари, чат.

#### 5.5.1 `Sidebar.svelte`
- Card на всю высоту (`100vh - 6rem`)
- Tabs: "Дерево" / "Поиск"
- **Дерево:** `TreeSection` — дерево файлов/папок
- **Поиск:** `SearchSection` — поиск внутри файловой системы
- Footer: индикатор хранилища (Progress bar), очередь загрузок
- Скрытые input'ы для загрузки файлов и папок

#### 5.5.2 `TreeSection.svelte` (406 строк)
- Toolbar: поиск в дереве + dropdown "Создать" (папку/документ, загрузить файлы/папку)
- `TreeArea` — основная область дерева
- Breadcrumb навигация
- Контекстное меню (drag & drop)
- Lazy loading детей папок

#### 5.5.3 `TreeArea.svelte` (328 строк)
- Рендер дерева файлов/папок
- Drag & Drop (файлы можно перетаскивать между папками)
- Множественное выделение
- Фильтрация по поисковому запросу

#### 5.5.4 `TreeNode.svelte` (328 строк)
- Отображение одного узла дерева (файл или папка)
- Иконки по типу файла
- Контекстное меню: переименование, удаление, перемещение, назначение проекта
- Индикатор загрузки детей (Loader2)
- Drag handle

#### 5.5.5 `TreeToolbar.svelte`
- Input поиска в дереве
- Dropdown "+" с опциями: Папку, Документ, Файлы…, Папку…

#### 5.5.6 `SidebarDialogs.svelte` (147 строк)
- Dialog создания папки/документа
- Dialog подтверждения удаления (множественное)
- Dialog переименования
- `ProjectScopeAssignDialog` для назначения проекта
- `FolderPickerDialog` для выбора целевой папки

#### 5.5.7 `SidebarFooter.svelte`
- Progress bar хранилища
- Список последних 3 загрузок с прогрессом

#### 5.5.8 `FileViewer.svelte` (383 строки)
- **Универсальный просмотрщик файлов** на основе MIME-типа/расширения:
  - `video/*`, `audio/*` → `VideoPlayer`
  - `.md`, `text/markdown` → `TipTapEditor` (WYSIWYG)
  - `.docx`, `.xlsx`, `.pptx` → `OnlyOfficeEditor`
  - `.pdf` → `PdfViewer`
  - `.mermaid` → `MermaidEditor`
  - `image/*` → `ZoomableImage` + `ImageLightbox`
  - Fallback: иконка файла + кнопка скачивания
- Header: имя файла, `JobStatusBadge`, кнопка PersonCandidates (UserCheck), кнопка Download
- Загружает метаданные через `GET /api/files/{id}`
- Для markdown: `GET /api/files/{id}/download` → fetch content → TipTapEditor
- Для docx: `DocxPreview` (docx-preview library)
- Конвертация в Markdown (`mammoth`)

#### 5.5.9 `VideoPlayer.svelte`
- HTML5 `<video>` элемент
- Синхронизация с `playerTimeSec` store (текущее время)
- Программная перемотка через `playerSeekRequest` store
- Обработка metadata load, seeking, seeked

#### 5.5.10 `TipTapEditor.svelte` (657 строк)
- **WYSIWYG Markdown редактор** на основе TipTap (ProseMirror)
- Extensions: StarterKit, TextAlign, Table (row, cell, header), Image, Link, Placeholder, tiptap-markdown
- Toolbar: Bold, Italic, Strikethrough, Code, H1-H3, BulletList, OrderedList, Quote, CodeBlock, Table, Image, Link, Undo/Redo, TextAlign
- Автосохранение (debounce) → `PUT /api/files/{id}/content` (text/markdown)
- DiffOverlay для показа изменений
- Поддержка Mermaid блоков через `MarkedPreviewWithMermaid`
- HTML → Markdown конвертация

#### 5.5.11 `OnlyOfficeEditor.svelte` (1046 строк — самый большой виджет)
- Интеграция с OnlyOffice Document Server
- Загружает OnlyOffice API через `<script>` (`api.js`)
- Поддерживает: `.docx`, `.xlsx`, `.pptx`, `.csv`, `.txt`, `.odt` и др.
- Config: documentType (word/cell/slide), permissions (edit/download/print/comment)
- Token-based auth
- Callback URL для сохранения
- **Интеграция с LLM Chat:**
  - Выполняет `edit_command` (js_code) из SSE через `executeCommand()`
  - Отвечает на `read_structure_request` — выполняет JS в контексте OnlyOffice и отправляет результат обратно
  - Connector plugin pattern
- Версионирование файлов
- Fallback на другие viewer'ы при ошибках

#### 5.5.12 `MilkdownEditor.svelte` (608 строк)
- Альтернативный Markdown WYSIWYG-редактор на основе Milkdown (ProseMirror)
- Block handle с tooltip (DragHandleTooltipPlugin)
- Slash commands
- Поддержка таблиц, списков, code blocks
- Автосохранение

#### 5.5.13 `EditorJsEditor.svelte` (188 строк)
- Редактор на основе Editor.js
- Динамическая загрузка plugins (Header, List, Checklist, Quote, Table, Code, Delimiter, Image)
- Конвертация Editor.js ↔ Markdown через `MarkdownConverter`

#### 5.5.14 `MarkdownEditor.svelte`
- CodeMirror-based Markdown редактор (raw editing)
- Extensions: basicSetup, markdown language, code language data
- Autosave с debounce 500ms

#### 5.5.15 `PdfViewer.svelte` (494 строки)
- Viewer PDF через pdfjs-dist
- Lazy rendering страниц (IntersectionObserver)
- Zoom (50%-200%), page navigation, download
- Поддержка text layer для выделения текста

#### 5.5.16 `MainTabs.svelte`
- Card с Tabs: Транскрипт / Саммари / Действия
- Транскрипт показывается только для audio/video файлов
- Дочерние компоненты: `TranscriptPanel`, `SummaryPanel`, `ActionsPanel`

#### 5.5.17 `Transcript.svelte` (202 строки)
- Загрузка транскрипта: `GET /api/v1/files/{id}/transcript?version=...&limit=500`
- Парсинг: `start_ms`, `end_ms`, `speaker_id`, `text` → `SegmentView`
- Палитра цветов для спикеров (5 цветов)
- Фильтр по спикерам, поиск по тексту
- Синхронизация с `playerTimeSec` (active segment подсветка)
- Автообновление при событии `indexed` от JobStatus SSE

#### 5.5.18 `TranscriptPanel.svelte`
- Обёртка над `Transcript.svelte`

#### 5.5.19 `SegmentView.svelte`
- Компонент одного сегмента транскрипта
- Цветная метка спикера, таймкод (duration), текст
- Active state (цветная полоса слева)

#### 5.5.20 `SummaryPanel.svelte` (152 строки)
- Загрузка саммари: `GET /api/v1/files/{id}/summary?version=...`
- Markdown рендеринг через `SummaryWithCitations`
- Интеграция с PersonCandidates (автоматически показывает modal при pending candidates)
- Автообновление при SSE событии `indexed`
- Exported writable store: `personCandidatesModalState`

#### 5.5.21 `SummaryWithCitations.svelte` (148 строк)
- Рендеринг Markdown с поддержкой цитат/ссылок на сегменты транскрипта
- При клике на цитату: `playerSeekRequest.set(seconds)` — перемотка видео

#### 5.5.22 `ActionsPanel.svelte`
- Загрузка действий/задач: `GET /api/v1/files/{id}/actions?version=...&limit=50`
- Список: title, description, assignee (Users icon), priority (Badge), due date, status
- Completed items: перечёркнуты, с иконкой Check

#### 5.5.23 `ProjectChat.svelte` (908 строк)
- **AI Chat с LLM** привязанный к проекту
- Список conversations (sidebar): создание, удаление, переключение
- Context items: прикрепление файлов/сегментов/текста к сообщениям
- Streaming ответов через SSE (`streamMessage()`)
- Рендеринг сообщений: `MdRuntime` для markdown
- Tool calls visualization
- **Edit commands** (OnlyOffice integration): выполняет JS-код в редакторе
- **Read structure requests**: запрашивает структуру документа/spreadsheet
- **Human-in-the-Loop**: `user_input_request` → отображает вопрос с кнопками-опциями
- Props: `fullHeight`, `onClose`, `activeDocumentId`
- Автоскролл к последнему сообщению

#### 5.5.24 `MermaidView.svelte`
- Рендер Mermaid диаграммы из code string
- Dynamic import `mermaid/dist/mermaid.esm.min.mjs`
- Поддержка тем (default/dark)

#### 5.5.25 `MermaidEditor.svelte`
- Split view: Textarea (код) | MermaidView (preview)
- ResizablePaneGroup для регулировки ширины
- Кнопки: Сохранить, Отмена

#### 5.5.26 `MarkedPreviewWithMermaid.svelte`
- Парсит markdown, находит блоки ````mermaid```
- Рендерит HTML через `marked`, Mermaid через `MermaidView`
- Диалог редактирования Mermaid блоков (`MermaidEditor`)

#### 5.5.27 `MdRuntime.svelte`
- Runtime-рендерер Markdown с поддержкой:
  - `<segment>` тегов → `SegmentView` компонент
  - highlight.js для подсветки кода
  - `<think>` blocks (LLM thinking indicator — "Думаю...")
  - GFM, breaks

#### 5.5.28 `DiffOverlay.svelte` (349 строк)
- Overlay для показа diff между версиями документа
- Использует `diff-match-patch` library
- Подсветка добавленных/удалённых блоков

#### 5.5.29 `PersonCandidatesModal.svelte` (379 строк)
- Modal для привязки извлечённых спикеров к пользователям организации
- Таблица кандидатов: speaker_label, extracted_name/company/position, confidence
- Действия: Approve (с редактированием данных + привязкой к org member), Reject
- Форма: name, company, position, link to user (select из org members)

#### 5.5.30 `ImageLightbox.svelte` (143 строки)
- Fullscreen lightbox для просмотра изображений
- Навигация: prev/next, keyboard (←→, Esc)
- `ZoomableImage` внутри

#### 5.5.31 `ZoomableImage.svelte`
- Масштабирование изображений: колесо мыши + клик
- Библиотека: `@zoom-image/svelte`

#### 5.5.32 `TokenSearchInput.svelte` (230 строк)
- Продвинутый поиск с токенами/тегами
- Подсказки, фильтры, автокомплит

#### 5.5.33 `SearchSection.svelte` (178 строк)
- Поиск внутри sidebar: input, результаты, фильтры по типам

#### 5.5.34 `SearchResults.svelte`
- Рендер результатов поиска, группировка по path
- Expand/collapse сниппетов, infinite scroll

#### 5.5.35 `FileSummary.svelte`
- Tabs: Саммари / Действия (без транскрипта)
- Для файлов не-audio/video

#### 5.5.36 `FolderPickerDialog.svelte`
- Dialog выбора папок (чекбоксы) для фильтрации поиска

---

### Библиотеки виджетов (`widgets/app-main/lib/`)

#### `EditorUtils.ts`
- Константы: AUTOSAVE_MS (800), debounce timers, MIME types, file extensions
- Типы: EditorState, TooltipPosition, BlockAction
- TOOLTIP_ACTIONS — действия для блочного tooltip (headings, lists, quote, code, table)
- ProseMirror commands helpers

#### `MarkdownConverter.ts`
- Конвертация Editor.js blocks ↔ Markdown
- Использует `unified`/`remark-parse`/`remark-gfm`/`remark-stringify`
- Fallback через `turndown` + `turndown-plugin-gfm` (HTML → Markdown)
- Поддержка вложенных списков

#### `MermaidRenderer.ts`
- Singleton Mermaid instance с dark theme
- `renderMermaid(container, source)` — render с error handling
- Render queue для batch rendering

#### `PasteHandler.ts`
- Обработка вставки в ProseMirror-based редакторы
- Определение Markdown vs plain text (`markdownScore()`)
- Очистка MS Office HTML
- TSV → Markdown table conversion

#### `TableProcessor.ts`
- TSV → Markdown table
- GFM table normalization
- Pipe splitting с учётом экранирования
- Align cell sanitization

#### `FileOperations.ts`
- File System Access API (open/save/saveas)
- Fallback для браузеров без FSA API
- Integration с `TableProcessor`

#### `DragHandleTooltipPlugin.ts`
- Plugin для Milkdown: tooltip при hover над drag handle
- Показывает блочные действия (heading, list, etc.)
- Delay show/hide для UX

#### `treeUtils.ts`
- `escapeHtml()`, `highlightByQuery()`
- `findPathById()` — поиск пути в дереве
- `getNodeDepthById()` — глубина узла
- `flattenVisible()` — плоский список видимых узлов
- `getFilteredChildren()` — фильтрация детей

---

## 6. Shared

### 6.1 Stores (`shared/stores/`)

#### `auth.ts`
```ts
currentUser: Writable<UserReadWithOrganization | null>
currentOrg: Writable<OrganizationRead | null>
currentScopes: Writable<string[]>
```

#### `player.ts`
```ts
playerTimeSec: Writable<number>       // текущее время воспроизведения (сек)
playerSeekRequest: Writable<number | null>  // запрос перемотки
```

### 6.2 Lib (`shared/lib/`)

#### `apiClient.ts` — HTTP клиент
- **Token management:** `getAccessToken()`, `getRefreshToken()`, `setTokens()`, `clearTokens()` — localStorage
- **`apiFetch(input, init)`** — основной HTTP клиент:
  - Добавляет `Authorization: Bearer` и `X-Org-Domain`
  - Auto-refresh на 401 (с lock — один refresh за раз)
  - Retry после refresh
  - URL resolution: `PUBLIC_API_BASE` (client) / `PUBLIC_SSR_API_BASE` (server)
- **`apiFetchWith(fetchImpl)`** — то же с кастомным fetch (для SvelteKit load)
- **`formEncode(body)`** — URL-encoded form body
- **`buildApiUrl(input)`** — resolves relative path to full API URL
- **`getApiBase()`** — returns API base URL

#### `openapi.types.ts` — Типы API (110 строк, 21 export)
Основные типы:
- `TokenResponse`, `UserRead`, `OrganizationRead`, `UserReadWithOrganization`
- `OrgRole`, `OrgMemberRead`, `OrgMemberWithUserRead`
- `OrgGroupRead/Create/Update`, `OrgClientRead/Create/SecretRead`
- `RegisterGlobalBody`, `RegisterOrgBody`, `RegisterOrganisationBody`
- `ApproveOrgUserBody`, `TokenRequestBody`
- `OAuthScopeRead`

#### `permissions.ts` — RBAC
- Роли: `OWNER(4) > ADMIN(3) > EDITOR(2) > VIEWER(1)`
- `hasScope()`, `hasAllScopes()`, `hasAnyScopes()`
- `isRoleAtLeast(current, required)`
- `checkPermission({ scopes, role }, { any?, all?, roleAtLeast? })`
- Constants: `ORG_SCOPES` (MEMBERS_READ/WRITE, GROUPS_READ/WRITE, CLIENTS_MANAGE, SETTINGS_WRITE)

#### `sse.ts` — Server-Sent Events
- `sseSubscribe(urlOrPath, onEvent, onError?)` → returns cleanup function
- EventSource с `withCredentials: true`
- Парсит JSON из `update` и `snapshot` events

#### `links.ts`
```ts
APP_BASE = "https://app.logera.space"
APP_SIGNIN = "https://app.logera.space/auth/signin"
APP_SIGNUP = "https://app.logera.space/auth/signup"
```

#### `search/parseQuery.ts` — Парсер поисковых запросов
- Разбирает NLP-like запросы: `/Wiki отчёт`, `от Denis`, `2024-10-01..2024-10-10`
- Поддержка: paths, type (doc/segment/task), speaker, date_from/date_to, lang
- `toSearchParams()` — конвертация в URL params

#### `search/highlight.ts`
- `highlightText(text, query)` — HTML-safe highlight с `<mark>`

### 6.3 Hooks (`shared/hooks/`)

#### `guards.ts` — Server-side guards
- `requireAuth({ user })` → redirect 307 `/auth/login`
- `requireScopes({ scopes }, required)` → error 403
- `requirePermission(ctx, expr)` → error 403

#### `is-mobile.svelte.ts`
- `IsMobile` class extends `MediaQuery` — реактивное определение мобильного устройства (breakpoint 768px)

### 6.4 Components (`shared/components/`)

#### States
- `Loading.svelte` — индикатор загрузки
- `Empty.svelte` — пустое состояние
- `ErrorState.svelte` — состояние ошибки

### 6.5 UI Kit (`shared/ui/`) — shadcn-svelte

**Полный набор shadcn-svelte компонентов (Tailwind + bits-ui + Svelte 5):**

| Компонент | Описание |
|-----------|----------|
| `accordion` | Аккордеон (item, trigger, content) |
| `alert` | Алерт (title, description) |
| `alert-dialog` | Модальный алерт (action, cancel, content, header, footer) |
| `aspect-ratio` | Соотношение сторон |
| `avatar` | Аватар (image, fallback) |
| `badge` | Бейдж (variants: default, secondary, destructive, outline) |
| `breadcrumb` | Хлебные крошки (item, link, separator, ellipsis, page) |
| `button` | Кнопка (variants: default, destructive, outline, secondary, ghost, link; sizes: default, sm, lg, icon) |
| `calendar` | Календарь (полный набор подкомпонентов) |
| `card` | Карточка (header, title, description, content, footer, action) |
| `carousel` | Карусель (embla-carousel-svelte) |
| `chart` | Графики (container, style, tooltip; layerchart) |
| `checkbox` | Чекбокс |
| `collapsible` | Сворачиваемый блок |
| `command` | Command palette (input, list, group, item, empty, dialog, shortcut, link-item) |
| `context-menu` | Контекстное меню (полный набор) |
| `data-table` | Таблица данных (@tanstack/table-core) |
| `dialog` | Диалог (trigger, content, header, footer, title, description, overlay, close) |
| `drawer` | Drawer (vaul-svelte) |
| `dropdown-menu` | Dropdown меню (полный набор) |
| `form` | Формы (sveltekit-superforms + formsnap) |
| `hover-card` | Hover-карточка |
| `input` | Input |
| `input-otp` | OTP ввод (группы, слоты, разделители) |
| `label` | Label |
| `menubar` | Menubar |
| `navigation-menu` | Навигационное меню |
| `pagination` | Пагинация |
| `popover` | Popover |
| `progress` | Progress bar |
| `radio-group` | Radio группа |
| `range-calendar` | Календарь диапазона дат |
| `resizable` | Resizable panels (paneforge) |
| `scroll-area` | Область прокрутки |
| `select` | Select (trigger, content, item, group) |
| `separator` | Разделитель |
| `sheet` | Sheet (side panel) |
| `sidebar` | Sidebar (provider, content, header, footer, group, menu, rail, trigger, etc.) |
| `skeleton` | Skeleton loader |
| `slider` | Slider |
| `sonner` | Toast notifications (svelte-sonner) |
| `switch` | Switch toggle |
| `table` | Таблица (header, body, row, cell, head, footer, caption) |
| `tabs` | Tabs (list, trigger, content) |
| `textarea` | Textarea |
| `toggle` | Toggle |
| `toggle-group` | Toggle группа |
| `tooltip` | Tooltip |

**Кастомный компонент:**
- `Can.svelte` — Declarative permission check. Props: `any?: string[]`, `all?: string[]`, `roleAtLeast?: OrgRole`. Shows children only if `checkPermission()` passes. Has `fallback` slot.

### 6.6 Assets (`shared/assets/`)
- `Logera logo.svg` — полное лого
- `Logo short.svg` — favicon/иконка

### 6.7 Utils (`shared/utils.ts`)
- `cn(...inputs)` — `clsx` + `twMerge` (Tailwind class merge)
- Type helpers: `WithoutChild<T>`, `WithoutChildren<T>`, `WithElementRef<T>`

---

## 7. Pages

### `pages/app/Page.svelte` — Главная страница приложения

**Layout (3-column ResizablePaneGroup):**

```
┌──────────┬─────────────────────────────┬──────────┐
│ Sidebar  │         Main Area           │   Chat   │
│  (20%)   │ ┌─────────────────────────┐ │  (20%)   │
│          │ │     FileViewer          │ │          │
│ TreeSection │ │     (video/doc/pdf)     │ │ ProjectChat │
│ SearchSection │ ├─────────────────────────┤ │          │
│          │ │     MainTabs            │ │          │
│          │ │ (Transcript/Summary/    │ │          │
│          │ │  Actions)               │ │          │
│          │ └─────────────────────────┘ │          │
└──────────┴─────────────────────────────┴──────────┘
```

- **Sidebar** (20%, min 10%, max 30%): `Sidebar.svelte` — файловое дерево/поиск
- **Main** (60%, min 40%): Vertical split:
  - **Top:** `FileViewer` — просмотрщик файлов
  - **Bottom:** `MainTabs` — Транскрипт / Саммари / Действия
  - Split сохраняется в localStorage по типу файла
- **Chat** (20%, min 260px, hidden <XL): `ProjectChat` — AI чат
- Mobile: FAB "Chat" button → Sheet (side panel)

**Логика:**
- Пропорции layout сохраняются в localStorage по group (markdown, video, audio, pdf, docx, sheet)
- `layoutKey` включает fileId + сохранённое значение для ремонтирования ResizablePaneGroup
- Custom events: `toggle-app-sidebar`, `open-app-chat`, `close-app-chat`
- ResizeObserver для отслеживания пропорций

---

## 8. Стили и темы

### Tailwind CSS 4

**Конфигурация через `app.css`** (не отдельный `tailwind.config.js`):

```css
@import "tailwindcss";
@import "tw-animate-css";
@custom-variant dark (&:is(.dark *));
```

### Цветовая схема

#### Светлая тема (`:root`)

| Переменная | Значение | Назначение |
|------------|----------|------------|
| `--brand-primary` | `#2481fe` | Основной синий |
| `--brand-secondary` | `#113ba1` | Вторичный тёмно-синий |
| `--background` | `#f6f9ff` | Фон страницы |
| `--foreground` | `#0b1220` | Основной текст |
| `--card` | `#ffffff` | Фон карточек |
| `--primary` | `var(--brand-primary)` | Primary actions |
| `--secondary` | `var(--brand-secondary)` | Secondary actions |
| `--muted` | `#edf3ff` | Muted фон |
| `--muted-foreground` | `#3c4a67` | Muted текст |
| `--accent` | `#e7f2ff` | Accent фон |
| `--destructive` | `#ef4444` | Опасные действия |
| `--border` | `#d6e4ff` | Рамки |
| `--ring` | `#bbd7ff` | Focus ring |

#### Тёмная тема (`.dark`)

| Переменная | Значение |
|------------|----------|
| `--brand-primary` | `#4f9dff` |
| `--brand-secondary` | `#2a4daf` |
| `--background` | `#0b1220` |
| `--foreground` | `#ffffff` |
| `--card` | `#101826` |
| `--muted` | `#121a2b` |
| `--muted-foreground` | `#98a4c7` |
| `--accent` | `#0f2a57` |
| `--border` | `#27324c` |
| `--ring` | `#1d4ed8` |

### Шрифты
- Sans/Serif: `DM Sans, sans-serif`
- Mono: `Space Mono, monospace`

### Radius
- Base: `0.575rem`
- sm: `calc(var(--radius) - 4px)`
- md: `calc(var(--radius) - 2px)`
- lg: `var(--radius)`
- xl: `calc(var(--radius) + 4px)`

### Chart Colors
- chart-1: Blue (`#2563eb` / `#60a5fa`)
- chart-2: Green (`#10b981` / `#34d399`)
- chart-3: Amber (`#f59e0b` / `#fbbf24`)
- chart-4: Pink (`#ec4899` / `#f472b6`)
- chart-5: Green (`#22c55e` / `#4ade80`)

### Sidebar
- Отдельные переменные: `--sidebar`, `--sidebar-foreground`, `--sidebar-primary`, `--sidebar-accent`, `--sidebar-border`, `--sidebar-ring`

### Dark Mode
- Через `mode-watcher` library
- CSS: `@custom-variant dark (&:is(.dark *))`

---

## 9. Зависимости

### Runtime Dependencies

| Библиотека | Версия | Назначение |
|------------|--------|------------|
| **TipTap** (`@tiptap/core`, `@tiptap/starter-kit`, + extensions) | ^2.11 | WYSIWYG Markdown редактор (основной) |
| `tiptap-markdown` | ^0.8.10 | Markdown serialization для TipTap |
| **ProseMirror** (`prosemirror-*`) | ^1.x | Низкоуровневая основа для TipTap и Milkdown |
| **CodeMirror** (`@codemirror/*`, `codemirror`) | ^6.x | Raw Markdown редактор (MarkdownEditor) |
| **Mermaid** | ^11.4 | Рендеринг диаграмм |
| **marked** | ^16.2 | Markdown → HTML парсер |
| **DOMPurify** | ^3.2 | HTML sanitization |
| **highlight.js** | ^11.11 | Подсветка синтаксиса кода |
| **pdfjs-dist** | ^5.4 | PDF рендеринг |
| **docx-preview** | ^0.3.6 | DOCX preview в браузере |
| **mammoth** | ^1.11 | DOCX → HTML/Markdown конвертация |
| **xlsx** | ^0.18.5 | Excel файлы парсинг |
| **html-to-docx** | ^1.8 | HTML → DOCX экспорт |
| **html2pdf.js** | ^0.12 | HTML → PDF экспорт |
| **turndown** + gfm plugin | ^7.2 | HTML → Markdown конвертация |
| **unified/remark-*** | ^15/^11 | Markdown AST processing |
| **diff-match-patch** | ^1.0.5 | Text diff для DiffOverlay |
| **@zoom-image/svelte** | ^0.3.4 | Zoom для изображений |
| **postgres** | ^3.4.7 | PostgreSQL client (для server-side) |
| **drizzle-orm** | ^0.40 | ORM (server-side) |
| **@node-rs/argon2** | ^2.0 | Password hashing (server) |
| **@oslojs/crypto** + encoding | ^1.0 | Crypto utilities (server) |

### Dev Dependencies (ключевые)

| Библиотека | Назначение |
|------------|------------|
| **Svelte 5** (`svelte` ^5.38) | UI framework |
| **SvelteKit** (`@sveltejs/kit` ^2.38) | Full-stack framework |
| **Tailwind CSS 4** + plugins (forms, typography) | Стилизация |
| **bits-ui** ^2.9 | Headless UI primitives (основа shadcn-svelte) |
| **paneforge** ^1.0 | Resizable panels |
| **vaul-svelte** 1.0-next | Drawer component |
| **mode-watcher** ^1.1 | Dark mode management |
| **svelte-sonner** ^1.0 | Toast notifications |
| **sveltekit-superforms** ^2.27 | Form handling + validation |
| **formsnap** ^2.0 | Form components |
| **@tanstack/table-core** ^8.21 | Data table logic |
| **embla-carousel-svelte** ^8.6 | Carousel |
| **layerchart** 2.0-next | Charts |
| **@lucide/svelte** ^0.515 | Icons (Lucide) |
| **Storybook 9** | Component documentation/testing |
| **tailwind-merge** + **tailwind-variants** | Utility class management |
| **tw-animate-css** | Tailwind animations |
| **@internationalized/date** | Date internationalization |
| **mdsvex** ^0.12 | Markdown in Svelte files (.svx) |
| **drizzle-kit** ^0.30 | DB migrations |

---

## 10. Конфигурация

### `svelte.config.js`
- Preprocessors: `vitePreprocess()`, `mdsvex()`
- Adapter: `adapter-node`
- Extensions: `.svelte`, `.svx`
- Aliases: полный набор FSD aliases

### `vite.config.ts`
- Plugins: `tailwindcss()`, `sveltekit()`, `devtoolsJson()`
- Vue feature flags (для Mermaid): `__VUE_OPTIONS_API__`, `__VUE_PROD_DEVTOOLS__`
- HMR: clientPort 80, ws protocol (Docker)
- File watch: polling mode (Windows + Docker)

### Environment Variables
- `PUBLIC_API_BASE` — Public API URL (default: `http://localhost`)
- `PUBLIC_SSR_API_BASE` — Internal API URL для SSR (Docker internal)
- `PUBLIC_APP_HOST` — Hostname приложения

### TypeScript
- Strict mode
- `moduleResolution: "bundler"`
- Extends `.svelte-kit/tsconfig.json`
- Custom types: `turndown`, `mermaid`, `html2pdf`, `prosemirror-*`, `editorjs-plugins`, `env`

---

## Диаграмма потока данных

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│ hooks.server │────▶│ +layout.server│────▶│ +layout.ts      │
│ (org resolve)│     │ (user, org)   │     │ (getMeFull,     │
└─────────────┘     └──────────────┘     │  set stores)    │
                                          └────────┬────────┘
                                                   ▼
                    ┌──────────────────────────────────────────┐
                    │            +layout.svelte                 │
                    │  ┌─────────┐  ┌─────────────────────┐   │
                    │  │ Header  │  │ Page Content         │   │
                    │  └─────────┘  └─────────────────────┘   │
                    └──────────────────────────────────────────┘
                                                   ▼
                    ┌──────────────────────────────────────────┐
                    │        pages/app/Page.svelte              │
                    │  ┌────────┐ ┌──────────┐ ┌───────────┐  │
                    │  │Sidebar │ │FileViewer│ │ProjectChat│  │
                    │  │        │ │          │ │           │  │
                    │  │ fsStore │ │ apiFetch │ │ chat API  │  │
                    │  │ tree   │ │ download │ │ SSE stream│  │
                    │  │ upload │ │ TipTap   │ │ context   │  │
                    │  │ search │ │ OnlyOffice│ │ edit cmds │  │
                    │  └────────┘ │ PDF/Video│ └───────────┘  │
                    │             ├──────────┤                 │
                    │             │ MainTabs │                 │
                    │             │Transcript│                 │
                    │             │ Summary  │                 │
                    │             │ Actions  │                 │
                    │             └──────────┘                 │
                    └──────────────────────────────────────────┘
```
