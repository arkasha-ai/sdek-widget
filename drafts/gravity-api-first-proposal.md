# Технико-коммерческое предложение

## Архитектура и оценка сроков/бюджета мультиканальной платформы

**Версия документа:** 1.0  
**Дата:** 06.04.2026  
**Статус:** черновик для внутреннего использования

---

## Содержание

1. [Архитектура системы](#1-архитектура-системы)
2. [Технологический стек](#2-технологический-стек)
3. [Этапность реализации](#3-этапность-реализации)
4. [Оценка трудоёмкости](#4-оценка-трудоёмкости)
5. [Бюджетная оценка](#5-бюджетная-оценка)
6. [Рекомендации](#6-рекомендации)

---

## 1. Архитектура системы

### 1.1 Общая схема: Domain Core + Channels

Рекомендуемая архитектура — **Vertical Slice + Hexagonal (Ports & Adapters)**. Это обеспечивает:

- Независимость домена от инфраструктуры
- Возможность развивать каналы параллельно без конфликтов
- Тестируемость бизнес-логики без зависимости от API или UI
- Лёгкую замену внешних систем (маркетплейсы, CRM, аналитика)

```
┌─────────────────────────────────────────────────────────┐
│                      CLIENTS                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌───────────┐  │
│  │ Mobile  │  │Web Store│  │  Admin  │  │ Mini Apps │  │
│  │   App   │  │ (Next.js│  │  Panel  │  │ Telegram/ │  │
│  │         │  │  Store) │  │         │  │    VK     │  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └─────┬─────┘  │
│       │            │            │             │         │
│  ┌────▼────────────▼────────────▼─────────────▼─────┐  │
│  │                  BFF Layer                        │  │
│  │  Mobile BFF   Web BFF   Admin BFF   MiniApps BFF  │  │
│  │   (NestJS)    (Next.js   (NestJS)   (NestJS/     │  │
│  │               API Routes)               Fastify)  │  │
│  └────────────────────────┬──────────────────────────┘  │
│                          │                              │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │                  API Gateway                        │ │
│  │         (Kong / NGINX + OAuth2 + Rate Limiting)      │ │
│  └────────────────────────┬──────────────────────────┘  │
│                           │                             │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │                 DOMAIN CORE                        │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│  │  │ Products │ │  Orders  │ │  Users   │          │ │
│  │  │ Service  │ │ Service  │ │ Service  │          │ │
│  │  └──────────┘ └──────────┘ └──────────┘          │ │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐          │ │
│  │  │Payments  │ │Analytics │ │ Notif.   │          │ │
│  │  │ Service  │ │ Service  │ │ Service  │          │ │
│  │  └──────────┘ └──────────┘ └──────────┘          │ │
│  └────────────────────────┬──────────────────────────┘  │
│                           │                             │
│  ┌────────────────────────▼──────────────────────────┐ │
│  │              INFRASTRUCTURE LAYER                   │ │
│  │  PostgreSQL │ Redis │ S3/MinIO │ RabbitMQ/Kafka   │ │
│  └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

**Почему такое разделение:**

- **Domain Core** — вся бизнес-логика в чистом виде. Не знает, кто его вызывает. Это позволяет переиспользовать одну и ту же логику для мобильного приложения, веб-витрины и любых Mini Apps без дублирования кода.
- **BFF (Backend for Frontend)** — отдельный слой для каждого канала. Mobile BFF оптимизирован под формат мобильного API (пагинация, offline-first), Web BFF — под SSR и SEO-требования, Admin BFF — под пакетные операции и экспорт данных. Это убирает компромиссы: не нужно городить один API, который пытается угодить всем.
- **API Gateway** — единая точка входа. Аутентификация, rate limiting, логирование, маршрутизация. Без него каждый BFF изобретает это самостоятельно.

### 1.2 API-first: какой протокол выбрать

| Критерий | REST | GraphQL | tRPC | gRPC |
|---|---|---|---|---|
| Типизация | нет (OpenAPI добавляет) | встроена | встроена (TypeScript) | встроена (Protobuf) |
| Кривая обучения | низкая | средняя | низкая (TS-специфик) | крутая |
| Производительность | средняя | ниже REST (парсинг) | высокая |最高 |
| Browser-native | да | да (CORS) | нет (только TS) | нет (Protobuf) |
| Стриминг | WebSocket/ SSE | subscriptions | subscriptions | bidirectional streaming |
| Code generation | OpenAPI generator | codegen | автоматически | protoc |
| Ideal для | CRUD, публичные API | сложные UI, dynamic queries | TypeScript monorepo | микросервисы, IoT |
| Debugging | Postman/curl | GraphiQL | TypeScript | grpcurl |

**Рекомендация: REST + WebSocket для real-time.**

Обоснование:

- **REST** — зрелый, понятный, легко интегрируется с любым клиентом (мобильные SDK, веб-фреймворки, инхаус-системы). OpenAPI spec генерируется автоматически и используется для документации, mock-серверов и генерации клиентского кода.
- **GraphQL** — соблазняет гибкостью, но добавляет сложности: N+1 проблема, complexity analysis, кэширование на клиенте ломается. Имеет смысл, если у каналов radically different data requirements и команда готова платить за эту гибкость.
- **tRPC** — отличный выбор в TypeScript monorepo, где backend и frontend в одном репозитории и команда одна. Но в нашем случае каналов несколько, и tRPC плохо подходит для публичного API (TypeScript-only, нет стандартного клиента на Swift/Kotlin).
- **gRPC** — overkill для 90% случаев. Protobuf компиляция, сложность с браузером (нужен gRPC-web proxy), экосистема инструментов менее развита.

**Для маркетплейсов (WB, Ozon):** они предоставляют REST API. REST — естественный выбор и для интеграции с ними.

**WebSocket / SSE** — для уведомлений в реальном времени (статусы заказов, чат поддержки, push-нотификации).

### 1.3 Аутентификация и авторизация

**Стек: JWT + OAuth2 + Refresh Tokens**

```
┌─────────┐    ┌─────────────┐    ┌──────────────────┐
│  Client │───▶│  API Gateway│───▶│  Auth Service    │
│         │    │  (verify    │    │  - Issue JWT     │
│         │    │   JWT)      │    │  - Refresh Token │
│         │    │             │    │  - OAuth2 flow   │
└─────────┘    └─────────────┘    └──────────────────┘
```

**Почему JWT (а не сессии):**

- **Stateless** — не нужен centralized session store для валидации. JWT валиден на любом инстансе. Масштабируется горизонтально без проблем.
- **Portable** — работает одинаково для всех каналов. Mobile app, web, Mini Apps — один и тот же механизм.
- **Short-lived access tokens (15 мин) + long-lived refresh tokens (30 дней)** — компромисс между безопасностью и UX. Access token нельзя отозвать мгновенно, но 15 минут — приемлемый window. Refresh token можно отозвать.

**OAuth2 сценарии:**

- **Authorization Code + PKCE** — для мобильного приложения и веб-витрины. PKCE защищает от перехвата кода на клиенте.
- **Client Credentials** — для сервис-сервис взаимодействия (backend → маркетплейсы, webhook handlers).
- **Device Code** — для admin panel (если админ не через браузер).

**SSO (Single Sign-On):** если у заказчика уже есть SSO-инфраструктура (Keycloak, Active Directory, Google Workspace), подключаем через SAML2 или OIDC. Это не входит в MVP, но закладывается на этапе проектирования.

**Для Mini Apps (Telegram/VK):** используем их нативные механизмы аутентификации:

- **Telegram Mini App:** `Telegram.WebApp.initData` — данные о пользователе от Telegram, подписанные HMAC. Валидируем на бэкенде.
- **VK Mini Apps:** аналогичный механизм через `VK.WebApp.getUserId()`.

Это позволяет войти в приложение без пароля, что критично для UX в Mini Apps.

### 1.4 Выгрузка данных в маркетплейсы (WB, Ozon)

**Стратегия: централизованный Inventory/Order Management с адаптерами на каждый маркетплейс.**

```
┌─────────────────────────────────────────────────┐
│              Domain Core (Products, Orders)      │
└─────────────────────────┬───────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌───────────────┐ ┌───────────────┐ ┌───────────────┐
│  WB Adapter   │ │ Ozon Adapter  │ │ Future:       │
│  - Products   │ │ - Products    │ │ Яндекс.Маркет │
│  - Inventory  │ │ - Inventory   │ │ Amazon        │
│  - Orders     │ │ - Orders      │ │ ...           │
│  - Returns    │ │ - Returns     │ │               │
└───────────────┘ └───────────────┘ └───────────────┘
```

**Что это даёт:**

- **Single source of truth** — товар один раз создаётся в системе, автоматически синхронизируется на все маркетплейсы.
- **Inventory pooling** — общий остаток, распределяется по каналам (собственный сайт, WB, Ozon).
- **Price management** — разные цены для разных каналов, но единый прайс-лист с правилами.
- **Order aggregation** — заказы со всех каналов стекаются в одну систему.

**Реализация:** сервис **Marketplace Sync Service** — периодически (или по webhook от маркетплейса) синхронизирует данные. Для Ozon и WB есть официальные API и SDK (Python, Node.js), которые покрывают 90% сценариев.

**Важно:** маркетплейсы не любят, когда товаров слишком много обновлений в день. Нужна стратегия батчинга и кэширования. Закладываем очередь (Redis/RabbitMQ) и schedule-based sync.

### 1.5 Подключение к внешним системам

Если у заказчика есть:

- **1С / МойСклад / Битрикс24** — это ERP/CRM. Подключение через их REST API. Для 1С чаще всего используют HTTP-сервисы 1С или промежуточный файл (CommerceML).
- **CRM (amoCRM, Bitrix24)** — webhook-driven интеграция. Заказы автоматически создают сделки.
- **Складские системы (ScanService, Axelot)** — REST или SOAP.
- **Платёжные системы (ЮKassa, Сбер, Тинькофф)** — готовые SDK, интеграция через iframe или redirect.

**Рекомендация:** на этапе MVP подключаем только платёжную систему (ЮKassa — самый простой старт для российского e-commerce). Остальное — по приоритету после запуска.

---

## 2. Технологический стек

### 2.1 Backend

**Рекомендация: Node.js (NestJS) + TypeScript**

| Альтернатива | Плюсы | Минусы | Вердикт |
|---|---|---|---|
| **NestJS + TypeScript** | Мощная модульная система, DI из коробки, TypeScript everywhere, огромная экосистема, легко нанимать | Бывают проблемы с перформансом на high-load | **Выбор** |
| Fastify | Быстрый, low-overhead | Меньше структуры, больше "ручного" кода | Для BFF и микросервисов (не для Domain Core) |
| Go (Gin/Echo) | Быстрый, single binary | Меньше экосистемы для enterprise, сложнее нанимать | Для high-performance микросервисов (логи, очереди) |
| Python (FastAPI) | Быстрая разработка, ML integration | GIL, медленнее на CPU-bound | Для ML/analytics-сервисов |
| Java/Kotlin (Spring) | Зрелый, enterprise | Verbose, тяжёлый, долгая компиляция | Если есть команда с опытом |

**Почему NestJS:**

- Модульная архитектура enforce-ит Vertical Slice. Каждый модуль — это feature folder с контроллерами, сервисами, DTO и тестами.
- Встроенный DI (Dependency Injection) — позволяет легко подменять реализации (например, для тестов).
- TypeScript от начала до конца — от бэкенда до мобильного приложения. Один язык, единый tooling.
- Guards, Interceptors, Pipes — мощные абстракции для cross-cutting concerns (auth, validation, logging).
- OpenAPI/Swagger из коробки — автогенерация документации.

**Для BFF слоя:** можно использовать NestJS или Next.js API Routes. Next.js API Routes удобен для Web BFF, потому что лежит в том же репозитории что и frontend. Для Mobile BFF и Admin BFF — отдельные NestJS-сервисы.

### 2.2 База данных

**Рекомендация: PostgreSQL + Redis + S3 (MinIO/AWS S3)**

| БД | Назначение | Почему |
|---|---|---|
| **PostgreSQL 15+** | Основное хранилище (products, orders, users, transactions) | ACID, JSONB для гибких схем, PostGIS если нужна геолокация, partitioning для больших таблиц |
| **Redis** | Кэш, сессии, очереди, rate limiting, pub/sub | sub-ms latency, встроенные структуры данных |
| **S3 (MinIO on-prem / AWS S3)** | Файлы, изображения, экспорты | бесконечное масштабирование, дешево |

**Почему не NoSQL (MongoDB, DynamoDB):**

- E-commerce domain — это прежде всего транзакции с деньгами. PostgreSQL с его ACID-гарантиями — стандарт индустрии.
- MongoDB заманчива гибкостью схемы, но приводит к проблемам с миграциями и целостностью данных на больших объёмах.
- Если в будущем появится need в документоориентированном хранилище (например, для отзывов или характеристик товаров) — можно добавить MongoDB как дополнительный store. Domain Core от этого не пострадает.

**Шардирование и репликация:**

- MVP: одна PostgreSQL instance + 1 read replica. Read replica для аналитических запросов (отчёты, дашборды).
- При росте нагрузки: Citus для horizontal scaling (шардирование PostgreSQL без перехода на распределённую БД).

### 2.3 Frontend Web (веб-витрина)

**Рекомендация: Next.js 14+ (App Router) + TypeScript + TailwindCSS**

| Альтернатива | Плюсы | Минусы | Вердикт |
|---|---|---|---|
| **Next.js (App Router)** | SSR/SSG из коробки, файловая маршрутизация, React Server Components,的强大 SEO | Большой bundle, сложнее чем просто React | **Выбор** |
| Nuxt (Vue) | SSR, хорош для Vue-команд | Vue vs React — зависит от команды. Экосистема меньше. | Если команда Vue-native |
| Vite + React | Быстрая разработка, low overhead | Нет SSR из коробки, SPA-only | Для B2B-панелей (не для витрины) |
| Remix | Server-centric, progressive enhancement | Меньше экосистема, чем Next.js | Нишевое решение |

**Почему Next.js:**

- **SEO критичен для e-commerce.** SSR/SSG позволяет отдавать готовый HTML поисковикам. Это напрямую влияет на organic traffic.
- **App Router + React Server Components** — данные загружаются на сервере, уменьшают client-side JS, ускоряют First Contentful Paint.
- **Image optimization, font optimization** — встроены и работают out of the box.
- **API Routes** можно использовать как BFF layer — не нужен отдельный сервис для web-канала.

**TailwindCSS** — ускоряет разработку, уменьшает CSS bundle за счёт purge. Особенно удобен в команде: дизайн-систему можно выразить как набор компонентов с predefined tailwind-конфигом.

### 2.4 Mobile (мобильное приложение)

**Рекомендация: React Native (Expo) + TypeScript**

| Критерий | React Native (Expo) | Flutter | Kotlin/Swift (Native) |
|---|---|---|---|
| Code sharing | 90%+ logic shared | 70-80% (Dart) | 0% |
| Time to market | быстрее всего | среднее | slowest |
| Native feel | близко к нативному | отличный | идеальный |
| Hot reload | да | да | limited |
| Learning curve | React devs = готовы | новый язык | новые языки |
| Maintenance | 1 codebase | 1 codebase | 2 codebase |
| Complex animations | возможно (Reanimated) | excellent | excellent |
| Перспективы рынка | большое community, Meta поддерживает | большое, Google | лидирует Apple |

**Почему React Native (Expo):**

- **Один код на iOS и Android** — 90% переиспользования. Команда может быть smaller и быстрее.
- **JavaScript/TypeScript ecosystem** — если уже есть React-девелоперы (для веб-витрины), они могут работать и над мобильным приложением.
- **Expo** убирает pain points нативной разработки: hot reload, push notifications, maps, camera — всё через единый SDK. Не нужно настраивать Xcode/Android Studio проекты.
- **Ejected к bare workflow** — если нужен нативный доступ, всегда можно выйти из Expo и работать как с нативным RN-проектом.

**Почему не Flutter:**

- Dart — отдельный язык, отдельная экосистема. Нужна отдельная команда или переучивание.
- Flutter отличен для сложных анимаций и игровых элементов. Для типичного e-commerce приложения (каталог, корзина, заказ, профиль) — overkill.
- React Native имеет больший пул доступных разработчиков на рынке.

**Почему не натив (Kotlin/Swift):**

- В 2 раза больше работы. iOS + Android = 2 codebase.
- Оправдано только если нужна best-in-class performance или сложные нативные фичи (AR, сложная графика).

### 2.5 Admin Panel

**Рекомендация: React Admin (Raermost) + NestJS BFF**

| Альтернатива | Плюсы | Минусы | Вердикт |
|---|---|---|---|
| **React Admin** | Специализированный фреймворк для admin-панелей, 70% UI из коробки, generator для CRUD | Opinionated, нужно встроить в свой дизайн | **Выбор** |
| Refine | Modern, TypeScript-first, хороший DX | Моложе, меньше компонентов из коробки | Второй выбор |
| Strapi (Headless CMS) | Готовый admin из коробки, Headless CMS | Привязка к Strapi, ограниченная кастомизация | Только если CMS подходит |
| Forest Admin | SaaS, быстрый старт | Vendor lock-in, дорого | Не рекомендуем |
| Кастомный (Next.js + UI library) | Полный контроль | Долго, дорого | Не для MVP |

**Почему React Admin:**

- Фреймворк заточен именно под admin-панели: list views, filters, forms, pagination, bulk actions — всё есть.
- **Data Provider** абстракция — подключается к любому API (REST, GraphQL, Prisma).
- **Начинаем с React Admin, уходим в кастом**, когда UI перестаёт удовлетворять. Это gradual approach.
- Снижает time-to-market для MVP значительно: не нужно строить базовый CRUD с нуля.

**Для сложных сценариев (категории товаров, матрица атрибутов, промо-акции):** кастомные React-компоненты поверх React Admin.

### 2.6 Infrastructure

**Рекомендация: Kubernetes (managed — Yandex Cloud / VK Cloud) + Docker + GitHub Actions / GitLab CI**

| Компонент | Выбор | Обоснование |
|---|---|---|
| **Cloud** | Yandex Cloud или VK Cloud | Российские провайдеры, соответствие 152-ФЗ, low latency для российских пользователей, нативная интеграция с российскими сервисами (ЮKassa, Сбер) |
| **Kubernetes** | Yandex Managed Service for Kubernetes (K8s) | Managed, не нужно управлять control plane. Autoscaling, load balancing, secrets — из коробки. |
| **Container registry** | Yandex Container Registry | Интегрирован с K8s, быстрый pull образов |
| **CI/CD** | GitHub Actions или GitLab CI | GitHub Actions проще, GitLab CI лучше для сложных pipeline. Оба — standard. |
| **Object Storage** | Yandex Object Storage (S3-compatible) | Дешевле чем AWS S3 для российских проектов |
| **Database hosting** | Yandex Managed Service for PostgreSQL | Автоматические бэкапы, failover, патчи — без ручной работы |
| **Cache/Queue** | Yandex Message Queue или self-hosted Redis | Для MVP self-hosted Redis в K8s. При росте — Yandex MQ. |

**Почему не bare metal / VPS:**

- Kubernetes даёт declarative infrastructure и autoscaling. При резких всплесках (распродажи, новый продукт на маркетплейсе) — автоматически добавляет инстансы.
- Managed-сервисы экономят 20-30 часов в месяц на operational overhead (бэкапы, обновления, мониторинг).

**CI/CD Pipeline:**

1. PR → lint + unit tests + type check → автоматический merge или reject
2. Merge to main → build Docker image → push to registry → deploy to staging
3. Staging → E2E tests (Playwright) → ручное approve → deploy to production
4. Secrets — через Kubernetes Secrets или HashiCorp Vault

### 2.7 Mini Apps (Telegram / VK)

**Telegram Mini App:**

- **SDK:** `@twa/jsdk` (JS SDK от Telegram) или vanilla `Telegram.WebApp` API
- **Frontend:** это web-приложение (SPA на React), которое встраивается в Telegram WebView
- **BFF:** отдельный MiniApps BFF, который валидирует `initData` и добавляет пользователя в систему
- **Что нужно:** Telegram Bot (для уведомлений) + Mini App URL (должен быть HTTPS, желательно с CDN для скорости)

**VK Mini Apps:**

- **SDK:** `@vkontakte/vkui` (UI-kit для VK Mini Apps) + `vk-bridge`
- **Frontend:** React + VKUI (компоненты стилизованные под VK)
- **Аналогично:** MiniApps BFF для валидации

**Общий BFF для Mini Apps:**

```
┌─────────────────┐    ┌─────────────────────────┐
│ Telegram WebView│    │     VK WebView           │
└────────┬────────┘    └───────────┬─────────────┘
         │                         │
         └──────────┬──────────────┘
                    ▼
          ┌─────────────────────┐
          │   MiniApps BFF      │
          │  (NestJS / Fastify) │
          │  - initData validate│
          │  - normalize user   │
          │  - channel-specific │
          │    features         │
          └──────────┬──────────┘
                     │
          ┌──────────▼──────────┐
          │    Domain Core       │
          └─────────────────────┘
```

**Важно:** Mini Apps — это тот же web frontend, что и веб-витрина, но с адаптированным UI. Shared domain logic, разные presentation layer.

---

## 3. Этапность реализации

### 3.1 Фаза 0: Discovery & Design (2 недели)

**Цель:** утвердить архитектуру, дизайн-систему, список фич MVP.

**Что входит:**

- Сессии с заказчиком: уточнение доменной модели (products, orders, users, fulfillment)
- Проектирование Data Model (ER-диаграмма, API contracts)
- Проектирование UI/UX (wireframes ключевых экранов)
- Выбор стека и облака (согласование)
- Техническое задание (ТЗ) — структурированный документ

**Результат:** утверждённое ТЗ, согласованные wireframes, технические решения зафиксированы.

**Может выполняться параллельно:** пока команда делает discovery, параллельно можно начинать infra setup (Kubernetes cluster, CI/CD).

---

### 3.2 Фаза 1: MVP (8-10 недель)

**Цель:** работающий продукт с минимальным функционалом для первых пользователей и проверки гипотез.

**Критичные фичи для запуска:**

| Компонент | Фича |
|---|---|
| Domain Core | Products CRUD, Users (регистрация/авторизация), Orders |
| BFF | Web BFF, Auth BFF |
| Web Storefront | Каталог, карточка товара, корзина, оформление заказа, авторизация |
| Mobile | Каталог, корзина, заказ (MV, упрощённый checkout) |
| Admin | Управление товарами, просмотр заказов |
| Infrastructure | PostgreSQL, Redis, S3, CI/CD, мониторинг (Grafana/Prometheus) |

**Не входит в MVP:**

- Маркетплейсы (WB, Ozon)
- Push-уведомления (мобильные)
- Сложная аналитика / дашборды
- Mini Apps
- SSO
- Полноценная система возвратов
- Программа лояльности

**Команда:**

- 1 Tech Lead / Architect (выделяет 50%)
- 2 Backend (NestJS)
- 1-2 Frontend (Next.js)
- 1 Mobile (React Native)
- 1 Designer (UI/UX, wireframes)

**Срок:** 8 недель (реалистичный) / 10 недель (пессимистичный)

---

### 3.3 Фаза 2: Beta (4-6 недель)

**Цель:** расширение фич, улучшение UX, подготовка к боевой нагрузке.

**Что добавляется:**

| Компонент | Фича |
|---|---|
| Domain Core | Reviews/Ratings, Wishlist, promo codes, интеграция с платёжными системами (ЮKassa) |
| BFF | Mobile BFF (если ещё нет), WebSocket для real-time уведомлений |
| Web Storefront | Search + filters, reviews, wishlist, checkout с оплатой |
| Mobile | Search, reviews, wishlist, push notifications (Expo Push) |
| Admin | Inventory management, promotional tools, базовая аналитика (продажи) |
| Infrastructure | Рассылка email (Yandex/UniSender), SMS (о статусах заказов) |

**Команда:** та же, что на MVP.

**Срок:** 4 недели (реалистичный) / 6 недель (пессимистичный)

---

### 3.4 Фаза 3: Production Hardening (3-4 недели)

**Цель:** подготовка к боевой эксплуатации, нагрузочное тестирование, security hardening.

**Что делается:**

- Нагрузочное тестирование (k6 / Locust): 1000 concurrent users, выявление bottlenecks
- Оптимизация запросов к БД (explain, indexes, query optimization)
- Настройка autoscaling (K8s HPA — Horizontal Pod Autoscaler)
- Rate limiting, circuit breaker (для устойчивости к DDoS)
- Security audit: OWASP Top 10 check, penetration testing (automated)
- Мониторинг и alerting (Grafana dashboards, PagerDuty/Telegram alerting)
- Backup/restore procedures, disaster recovery plan
- Документация для support team
- Go-live checklist, rollback procedures

**Команда:** Tech Lead + DevOps + Backend (оптимизация БД)

**Срок:** 3 недели (реалистичный) / 4 недели (пессимистичный)

---

### 3.5 Фаза 4: Маркетплейсы (4-6 недель)

**Цель:** интеграция с Wildberries, Ozon, подготовка к синхронизации товаров и заказов.

**Что входит:**

- **WB API интеграция:** products.upload, offers.update, orders.get, stocks.sync
- **Ozon API интеграция:** аналогичный набор (products, orders, analytics)
- **Marketplace Sync Service:** централизованный сервис для синхронизации
- **Inventory pooling:** общий остаток с учётом всех каналов
- **Admin расширение:** UI для управления маркетплейс-каталогом, price rules
- **Webhook handlers:** обработка обновлений от маркетплейсов (new orders, status changes)

**Сложность:** API маркетплейсов имеют свои ограничения (rate limits, требования к карточкам товаров, валидация). Это может занять время.

**Команда:** 1 Backend + 1 Frontend (Admin)

**Срок:** 4 недели (WB + Ozon по отдельности, последовательно) / 6 недель (параллельно, если 2 разработчика)

---

### 3.6 Фаза 5: Mini Apps (3-5 недель)

**Цель:** Telegram Mini App и VK Mini App.

**Что входит:**

- **Telegram Mini App:** Web app + Telegram Bot для уведомлений, WebView integration
- **VK Mini App:** Web app + VKUI integration
- **Shared MiniApps BFF:** валидация initData, normalize user data
- **UX adaptation:** mobile-first, touch-optimized, compact UI для WebView
- **Mono-brand:** единый аккаунт с основным приложением

**Примечание:** Mini Apps — это по сути отдельный presentation layer для того же Domain Core. Основная работа — UI/UX adaptation, не backend.

**Команда:** 1 Frontend (React) + 1 Backend (если нужен BFF)

**Срок:** 3 недели (одна платформа) / 5 недель (обе)

---

### 3.7 Общий Timeline

```
Фаза 0:  Discovery & Design     ████                    2 нед
Фаза 1:  MVP                    ████████████████        8-10 нед
Фаза 2:  Beta                   ████████████           4-6 нед
Фаза 3:  Production Hardening   ████████                3-4 нед
Фаза 4:  Маркетплейсы           ████████████            4-6 нед
Фаза 5:  Mini Apps              █████████               3-5 нед

Итого (последовательно):        ~24-33 недель (6-8 месяцев)
Итого (с перекрытием фаз):       ~18-24 недели (4.5-6 месяцев)
```

**Оптимистичный сценарий (параллельные команды):**

- MVP + Beta: 10 недель (1 команда, sequentially)
- С 3-й недели MVP: infra setup (параллельно с разработкой)
- Production hardening: после MVP + Beta
- Маркетплейсы: после MVP (нужен базовый каталог)
- Mini Apps: после MVP (если UX stable)

**Critical path:** MVP — самая длинная фаза. Всё остальное может строиться на базе Domain Core.

---

## 4. Оценка трудоёмкости

### 4.1 Принципы оценки

- Оценка дана в человеко-днях (8 часов = 1 день)
- Команда: 5-6 человек (Backend × 2, Frontend × 2, Mobile × 1, Tech Lead × 0.5)
- Не включает: discovery (Фаза 0), project management, QA (отдельная строка)
- UI/UX: дизайн-макеты, дизайн-система, component library
- Backend: Domain Core + BFFs + Infrastructure as Code
- Mobile: React Native (iOS + Android)

### 4.2 Фаза 1: MVP

| Компонент | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| **UI/UX (Web + Mobile)** | | | |
| Дизайн-система (colors, typography, components) | 5 | 7 | 10 |
| Web витрина: каталог, карточка товара, корзина, checkout flow | 12 | 15 | 20 |
| Mobile: каталог, корзина, упрощённый checkout | 8 | 10 | 14 |
| Admin панель: товары + заказы (React Admin) | 8 | 10 | 14 |
| **Backend** | | | |
| Domain Core: Products, Users, Orders (CQRS-lite) | 18 | 22 | 28 |
| Auth (JWT, OAuth2, refresh tokens) | 5 | 7 | 10 |
| Web BFF (Next.js API Routes) | 5 | 7 | 10 |
| Admin BFF | 4 | 5 | 7 |
| Infrastructure (K8s, CI/CD, DB migrations) | 8 | 10 | 14 |
| **Mobile (React Native Expo)** | | | |
| App setup + navigation + auth | 5 | 7 | 10 |
| Каталог, поиск, фильтры | 6 | 8 | 12 |
| Корзина, checkout | 6 | 8 | 12 |
| Профиль пользователя | 3 | 4 | 6 |
| **Итого (человеко-дни)** | **93** | **120** | **157** |

**Разбивка по типам (реалистичный):**

- UI/UX: 42 дня (35%)
- Backend: 51 день (42%)
- Mobile: 27 дней (23%)

### 4.3 Фаза 2: Beta

| Компонент | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| Reviews/Ratings (backend + web + mobile) | 6 | 8 | 12 |
| Wishlist (backend + web + mobile) | 4 | 5 | 8 |
| Promo codes + discount rules | 5 | 7 | 10 |
| Платёжная интеграция (ЮKassa) | 5 | 7 | 10 |
| Search + filters (Elasticsearch/Algolia) | 8 | 10 | 14 |
| WebSocket notifications (real-time order status) | 5 | 7 | 10 |
| Mobile push notifications (Expo Push) | 4 | 5 | 8 |
| Admin: inventory management, promo tools | 6 | 8 | 12 |
| Email/SMS notifications | 4 | 5 | 8 |
| **Итого (человеко-дни)** | **47** | **62** | **92** |

### 4.4 Фаза 3: Production Hardening

| Компонент | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| Нагрузочное тестирование + оптимизация | 5 | 8 | 12 |
| Autoscaling setup | 3 | 4 | 6 |
| Security audit + hardening | 3 | 5 | 8 |
| Мониторинг + alerting | 4 | 5 | 7 |
| Backup/restore + DR procedures | 2 | 3 | 5 |
| Documentation | 2 | 3 | 5 |
| **Итого (человеко-дни)** | **19** | **28** | **43** |

### 4.5 Фаза 4: Маркетплейсы

| Компонент | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| WB API integration | 10 | 14 | 20 |
| Ozon API integration | 10 | 14 | 20 |
| Marketplace Sync Service | 5 | 7 | 10 |
| Inventory pooling logic | 4 | 6 | 9 |
| Admin UI: маркетплейс-менеджмент | 5 | 7 | 10 |
| Webhook handlers (marketplace events) | 4 | 6 | 9 |
| **Итого (человеко-дни)** | **38** | **54** | **78** |

**Примечание:** WB и Ozon имеют похожие, но не идентичные API. Если делать параллельно (2 разработчика) — 4 недели. Последовательно — 8 недель.

### 4.6 Фаза 5: Mini Apps

| Компонент | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| Telegram Mini App (web + bot) | 8 | 10 | 14 |
| VK Mini App (web + VKUI) | 6 | 8 | 12 |
| Shared MiniApps BFF (initData validation) | 4 | 5 | 7 |
| Mono-account system (unified users) | 3 | 4 | 6 |
| **Итого (человеко-дни)** | **21** | **27** | **39** |

### 4.7 Сводная таблица

| Фаза | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| Фаза 1: MVP | 93 | 120 | 157 |
| Фаза 2: Beta | 47 | 62 | 92 |
| Фаза 3: Production | 19 | 28 | 43 |
| Фаза 4: Маркетплейсы | 38 | 54 | 78 |
| Фаза 5: Mini Apps | 21 | 27 | 39 |
| **Всего (без Discovery)** | **218** | **291** | **409** |

**Discovery (Фаза 0):** +15-25 человеко-дней (Tech Lead + Designer, parallel to initial development).

**Project Management (10-15%):** добавить +22-44 человеко-дня (в зависимости от размера команды и сложности коммуникации с заказчиком).

**QA (10-15%):** добавить +22-44 человеко-дня (manual + automated, если есть требование к качеству).

---

## 5. Бюджетная оценка

### 5.1 Методология

**Исходные данные:**

- Ставка: backend/frontend/mobile — 8 000 - 15 000 руб/час (зависит от уровня: junior/middle/senior, город, формат)
- Используем среднюю ставку: **10 000 руб/час** (опытная команда, удалённо, Россия)
- Рабочая неделя: 5 дней × 8 часов = 40 часов

**Команда (расчётная):**

- Tech Lead (0.5 ставки): ~400 000 руб/мес
- Senior Backend × 2: ~300 000 × 2 = 600 000 руб/мес
- Senior Frontend × 1: ~280 000 руб/мес
- Middle Frontend × 1: ~200 000 руб/мес
- Senior Mobile × 1: ~280 000 руб/мес
- Designer × 0.5: ~150 000 руб/мес

**Итого команда (месяц): ~1 630 000 руб/мес**

### 5.2 Бюджет по фазам (реалистичный сценарий)

| Фаза | Человеко-дни | Часы | Бюджет (тыс. руб) |
|---|---|---|---|
| Фаза 0: Discovery | 20 | 160 | 1 600 |
| Фаза 1: MVP | 120 | 960 | 9 600 |
| Фаза 2: Beta | 62 | 496 | 4 960 |
| Фаза 3: Production | 28 | 224 | 2 240 |
| Фаза 4: Маркетплейсы | 54 | 432 | 4 320 |
| Фаза 5: Mini Apps | 27 | 216 | 2 160 |
| PM (12%) | 37 | 298 | 2 980 |
| QA (10%) | 31 | 248 | 2 480 |
| **Итого разработка** | **379** | **3 034** | **30 340** |

**Infrastructure (ежемесячно, на prod):**

| Компонент | Стоимость (руб/мес) |
|---|---|
| Yandex Cloud (Managed K8s, PostgreSQL, Redis, S3, CDN) | 80 000 - 200 000 |
| Мониторинг (Grafana Cloud или self-hosted) | 0 - 15 000 |
| Домены, SSL | 5 000 |
| Рассылки (UniSender / Yandex) | 5 000 - 20 000 |
| SMS-шлюз | 10 000 - 30 000 |
| **Итого infra (prod)** | **100 000 - 270 000 / мес** |

### 5.3 Диапазоны по фазам

| Фаза | Min (тыс. руб) | Mid (тыс. руб) | Max (тыс. руб) |
|---|---|---|---|
| Фаза 0 + 1 (Discovery + MVP) | 8 000 | 11 200 | 16 800 |
| Фаза 2 (Beta) | 3 500 | 4 960 | 7 400 |
| Фаза 3 (Production) | 1 500 | 2 240 | 3 400 |
| Фаза 4 (Маркетплейсы) | 3 000 | 4 320 | 6 200 |
| Фаза 5 (Mini Apps) | 1 700 | 2 160 | 3 100 |
| **Итого** | **17 700** | **24 880** | **36 900** |

**Что влияет на бюджет в каждую сторону:**

**Вниз (дешевле):**

- Не full-time команда (частичная занятость)
- Junior/middle mix вместо senior
- Готовые решения (Strapi, Shopify) — уменьшают custom development
- Ограниченный MVP (меньше фич)
- Региональные разработчики (не Москва/Питер)

**Вверх (дороже):**

- Наличие legacy-систем для интеграции (1С, SAP)
- Сложные бизнес-правила (скидки, программы лояльности, B2B-прайсы)
- Требования к compliance (152-ФЗ, PCI DSS)
- Дизайн-система с нуля (а не адаптация существующей)
- Тестирование覆盖率 > 80%
- Дополнительные языки (english UI, i18n)
- Legal overhead (договоры, NDA)

### 5.4 Прозрачность оценки

**Важные оговорки:**

1. **Оценки даны без учёта discovery-сессий с заказчиком.** После discovery (Фаза 0) фичи и сроки могут измениться. Это нормально.
2. **Ставки разработчиков** — ориентир для рынка (середина 2026, Россия, удалёнка). Может варьироваться в 2-3 раза.
3. **Стоимость infrastructure** — для MVP/pre-production можно уложиться в 30 000 - 50 000 руб/мес. Production — 100 000 - 300 000 руб/мес.
4. **Маркетплейсы** — если заказчик уже имеет карточки на WB/Ozon и нужна только синхронизация остатков/цен —budget уменьшается в 2 раза. Если нужно создание карточек с нуля и SEO-оптимизация —budget увеличивается.
5. **Mobilе** — React Native дешевле нативной разработки в 1.5-2 раза. Но если заказчику критична производительность (сложная анимация, AR) — нужен Flutter или натив.

---

## 6. Рекомендации

### 6.1 Что критично для первого запуска

1. **Domain Core + Web Storefront + Admin + Auth** — это минимум для working product.
2. **Next.js для веб-витрины** — SSR критичен для SEO. Без него продукт не найдут.
3. **PostgreSQL с самого начала** — миграция с MongoDB/MySQL later будет болезненной.
4. **Infrastructure as Code (Terraform/Pulumi)** — не начинать с hand-made servers.
5. **CI/CD с первого дня** — каждый PR автоматически deploy-ится в staging.

### 6.2 Что можно отложить

1. **Mobile app** — первым запускаем web. Mobile добавляем после validation.
2. **Маркетплейсы** — отдельная большая фаза. Запускаем после стабильного web.
3. **Mini Apps** — third priority. Важно для reach, не для revenue на старте.
4. **Полноценная аналитика** — на старте достаточно Metabase/Superset (free, self-hosted).
5. **SSO** — добавляем когда появится второй product line или enterprise-клиент.

### 6.3 Приоритет фич для MVP

**Must have:**

- Регистрация / авторизация (email + phone)
- Каталог товаров (категории, фильтры, поиск)
- Карточка товара (фото, описание, характеристики)
- Корзина
- Оформление заказа (address, delivery)
- Личный кабинет (история заказов)
- Admin: управление товарами

**Should have (добавить если есть время):**

- Wishlist
- Reviews
- Promo codes

**Won't have (MVP):**

- Интеграция с маркетплейсами
- Push-уведомления
- Программа лояльности
- Сложная аналитика
- Mini Apps

### 6.4 Точки неопределённости (нужно уточнить с заказчиком)

1. **Domain model:** какие сущности есть? Products (variants, attributes)? Orders (fulfillment states)? Users (B2C, B2B, or both)?
2. **Legacy systems:** есть ли 1С, CRM, складская система? Это определяет объём интеграций.
3. **Compliance:** нужен ли 152-ФЗ compliance (хранение персональных данных)? Влияет на выбор cloud и architecture.
4. **Платёжные системы:** какие? ЮKassa, Сбер, Тинькофф? Это определяет integration complexity.
5. **Дизайн:** есть ли готовый бренд-бук и дизайн-макеты? Или начинаем с нуля?
6. **Команда:** какая команда есть у заказчика? Что планируется набирать?

---

## Резюме

| Метрика | Оптимистичный | Реалистичный | Пессимистичный |
|---|---|---|---|
| **Срок (мес)** | 4.5 | 6 | 9 |
| **Разработка (тыс. руб)** | 17 700 | 24 880 | 36 900 |
| **Infra/мес (prod)** | 100 000 | 150 000 | 270 000 |

**Ключевое:**

- **API-first, Domain Core + Channels** — это позволяет запускать новые каналы (mobile, Mini Apps) без переписывания логики.
- **NestJS + TypeScript + PostgreSQL** — зрелый, maintainable, легко масштабировать команду.
- **Next.js для web, React Native для mobile** — максимальное переиспользование кода и людей.
- **Yandex Cloud** — российское облако, соответствует законодательству, интеграция с российскими сервисами.
- **4.5-6 месяцев до production** (без маркетплейсов и Mini Apps).

---

*Документ подготовлен для внутреннего использования. Оценки носят ориентировочный характер и подлежат уточнению после discovery-сессий с заказчиком.*
