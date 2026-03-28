# Awesome OpenClaw Skills: Web, Docs, PKM — TOP-10

**Источник:** [VoltAgent/awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills)
**Категории:** Web & Frontend Development (924), PDF & Documents (110), Notes & PKM (71)
**Дата:** 2026-03-27

---

## ТОП-10 самых интересных скиллов

### 1. anti-slop-design
**Ссылка:** https://clawskills.sh/skills/kjaylee-anti-slop-design

**Для чего:** Создание distinctive, production-grade frontend interfaces, которые избегают_generic AI aesthetics_ (Inter шрифт, фиолетовые градиенты, карточки в карточках).

**Почему интересен:** В SOUL.md есть правило "Be the assistant you'd actually want to talk to" и отсылка к `frontend-design` skill. Anti-slop-design — это прямая антитеза генеративному UI-мусору. Совместим с уже установленным `superdesign` skill: вместе дадут Аркаше возможность генерировать по-настоящему уникальные интерфейсы, а не очередной "modern SaaS dashboard". Особенно ценно для: карточки товаров (Wb-card-generator), презентации, лендинги.

---

### 2. apify-ultimate-scraper
**Ссылка:** https://clawskills.sh/skills/protoss70-apify-ultimate-scraper

**Для чего:** Universal AI-powered web scraper для любых платформ через Apify API.

**Почему интересен:** Apify — один из самых мощных инструментов для веб-скрапинга. В отличие от ad-hoc решений, Apify имеет готовые "actors" для Amazon, LinkedIn, Google Maps, Twitter и т.д. Сейчас у Аркаши есть `scrapling-official` и `web_fetch`, но Apify — это следующий уровень: готовые интеграции без написания парсеров с нуля. Критично для: исследования конкурентов, сбор данных для Paperclip, мониторинг цен.

---

### 3. agentic-security-audit
**Ссылка:** https://clawskills.sh/skills/kingrubic-agentic-security-audit

**Для чего:** Аудит кодовых баз, инфраструктуры И агентных AI-систем на предмет уязвимостей.

**Почему интересен:** Аркаша работает с агентами и пайплайнами. Agentic security — это отдельная дисциплина (prompt injection, tool poisoning, context manipulation). AGENTS.md говорит "Be careful with external actions". Этот скилл формализует то, что сейчас делается интуитивно. Особенно актуален для: аудита внешних скиллов перед установкой, проверки пайплайнов Paperclip.

---

### 4. docx
**Ссылка:** https://clawskills.sh/skills/seanphan-docx

**Для чего:** Comprehensive document creation, editing, analysis с поддержкой tracked changes.

**Почему интересен:** У Аркаши уже есть `docx-mastery` skill, но этот — альтернативная реализация. По description: "support for tracked changes" — это то, чего может не хватать текущему скиллу. Может быть полезен как backup или как дополнение для сложных сценариев (юридические документы, контракты с версионированием). В категории PDF & Docs это самый серьёзный инструмент для работы с Word.

---

### 5. contract-generator
**Ссылка:** https://clawskills.sh/skills/seanwyngaard-contract-generator

**Для чего:** Генерация professional freelance contracts, SOWs, NDAs для клиентских проектов.

**Почему интересен:** Аркаша делает Paperclip — продукт для команды. Контракты и SOW — постоянная боль для любого разработчика/фрилансера. Не требует внешних API, генерирует PDF. Может использоваться для: предложений клиентам Paperclip, внутренних договорённостей команды. Связка с `invoice-generator` (есть в том же репозитории) = полный цикл pre-sale.

---

### 6. meeting-to-action
**Ссылка:** https://clawskills.sh/skills/codedao12-meeting-to-action

**Для чего:** Конвертация заметок или транскриптов встреч в структурированные summary, decisions, action items с owners и due dates.

**Почему интересен:** Аркаша ведёт память (`memory/YYYY-MM-DD.md`), но формат — поток сознания, не структурированные решения. meeting-to-action даст возможность превращать голосовые/текстовые записи в actionable items. Особенно ценно для: стендапов команды Paperclip, ретроспектив, стратегических сессий. Работает с транскриптами — совместимо с Whisper (который уже настроен).

---

### 7. axe-devtools
**Ссылка:** https://clawskills.sh/skills/dylanb-axe-devtools

**Для чего:** Accessibility testing и remediation через axe MCP Server.

**Почему интересен:** accessibility — это не "доброе дело", это качество. Продукты Paperclip должны быть доступны. Axe — индустриальный стандарт (Google, Microsoft, Amazon его используют). Встроить проверку accessibility в пайплайн — значит делать продукт, который не стыдно показать. Особенно важен для: карточек товаров WB (визуальный контент должен быть accessibility-compliant).

---

### 8. context-slimmer
**Ссылка:** https://clawskills.sh/skills/sundevilatb-context-slimmer

**Для чего:** Audit and slim down always-loaded context files (AGENTS.md, TOOLS.md, USER.md, MEMORY.md, HEARTBEAT.md, SOUL.md).

**Почему интересен:** Аркаша загружает 6+ контекстных файлов при каждом старте сессии. В TOOLS.md есть раздел "Context Management" и упоминание "compaction death spirals". context-slimmer — это проактивный инструмент для борьбы с ростом контекста. Прямая польза: меньше токенов → быстрее ответы → ниже стоимость. Учитывая, что используется MiniMax-M2.7 (не самая дешёвая модель), это экономит деньги напрямую.

---

### 9. firecrawler
**Ссылка:** https://clawskills.sh/skills/capt-marbles-firecrawler

**Для чего:** Web scraping и crawling через Firecrawl API.

**Почему интересен:** Firecrawl — это open-source альтернатива Apify для сложных сайтов (SPA, Cloudflare, anti-bot). В отличие от Apify, может быть запущен локально (self-hosted). Apify + Firecrawler = покрытие 95% сценариев веб-скрапинга. Для оставшихся 5% — `scrapling-official` (уже установлен). Эта тройка делает Аркашу практически неуязвимым для задач сбора данных из веба.

---

### 10. failure-memory
**Ссылка:** https://clawskills.sh/skills/leegitw-failure-memory

**Для чего:** Превращение ошибок в паттерны, которые предотвращают рецидив. "Stop making the same mistakes."

**Почему интересен:** В SOUL.md записано: "Если A command fails unexpectedly → log it". failure-memory — это автоматизация этого процесса. В USER.md есть `.learnings/ERRORS.md` который ведётся вручную. failure-memory может делать это системно: отслеживать pattern'ы ошибок, предлагать исправления, не давать повторять одни и те же грабли. SOUL.md учит: "Earn trust through competence" — этот скилл делает Аркашу объективно лучше с каждым фейлом.

---

## ТОП-5 приоритетов для установки

| # | Скилл | Категория | Приоритет | Обоснование |
|---|-------|-----------|-----------|-------------|
| 1 | **anti-slop-design** | Web/Frontend | ВЫСШИЙ | Уникальный UI — отстройка от конкурентов Paperclip. Напрямую влияет на качество карточек и презентаций |
| 2 | **meeting-to-action** | PKM/Notes | ВЫСШИЙ | Структурирует рабочие процессы команды. Whisper уже настроен — порог входа минимальный |
| 3 | **apify-ultimate-scraper** | Web | ВЫСОКИЙ | Универсальный скрапинг без написания парсеров. Заменяет 10+ одноразовых скриптов |
| 4 | **context-slimmer** | Инфраструктура | ВЫСОКИЙ | Прямая экономия токенов и ускорение ответов. Борьба с контекстным голодом |
| 5 | **agentic-security-audit** | Security | СРЕДНИЙ | Для задач с высоким риском: аудит внешних скиллов, пайплайнов, интеграций |

### Почему именно эти 5 первыми:

1. **anti-slop-design** — даёт результат, который видно сразу (UI отличается от 99% AI-генерированного мусора)
2. **meeting-to-action** — превращает хаос памяти в структуру. SOUL.md учит "Write it down" — этот скилл делает это автоматически
3. **apify-ultimate-scraper** — заменяет ручные парсеры. Аркаша часто исследует — это ускоряет работу в разы
4. **context-slimmer** — чем меньше контекст, тем быстрее и дешевле каждая сессия. Особенно важно для MiniMax-M2.7
5. **agentic-security-audit** — последним не потому что неважен, а потому что требует ручного запуска (аудит), а не фоновой работы

### Что не вошло в ТОП-5 и почему:

- **docx / contract-generator** — полезны, но docx-mastery уже покрывает основные сценарии. Контракты — точечная потребность
- **axe-devtools** — важен, но требует отдельного MCP сервера и не является blocker'ом
- **firecrawler** — отличный, но Apify покрывает большинство сценариев. Локальный Firecrawler — для параноидальных случаев
- **failure-memory** — ценен, но требует интеграции с текущим .learnings/ERRORS.md. Можно поставить после context-slimmer

---

## Уже установленные скиллы (не нужно дублировать)

- `docx-mastery` — покрывает DOCX лучше чем generic `docx`
- `excel-mastery` — покрывает XLSX лучше чем generic решения
- `scrapling-official` — покрывает сложный скрапинг (Cloudflare, Turnstile)
- `mindgraph-rs` — покрывает PKM лучше чем большинство generic memory скиллов
- `pptx-mastery` — покрывает презентации
