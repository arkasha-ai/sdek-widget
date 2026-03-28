# Research: Search & Research + Productivity & Tasks + Communication
**Источник:** https://github.com/VoltAgent/awesome-openclaw-skills  
**Категории:** Search & Research (352 скилла), Productivity & Tasks (205 скиллов), Communication (146 скиллов)  
**Дата:** 2026-03-27

---

## ТОП-10 самых интересных скиллов

### 1. meyhem-researcher
**ClawHub:** https://clawskills.sh/skills/c5huracan-meyhem-researcher  
**Для чего:** Multi-query deep research с отслеживанием результатов. Каждый следующий поиск улучшает будущие результаты для всех агентов — накапливающаяся база знаний.  
**Почему интересен:** Крайне редкий паттерн — скилл учится. Чем больше используешь, тем точнее становится. Для Дениса (корпоративная база знаний, исследования) — это следующий уровень: не просто ищет, а запоминает, что сработало.

---

### 2. meyhem-search
**ClawHub:** https://clawskills.sh/skills/c5huracan-meyhem-search  
**Для чего:** Agent-native поиск, ранжированный по тому, что реально помогает агенту выполнить задачу. Без API-ключей, без регистрации.  
**Почему интересен:** Free, privacy-first, rank по полезности для агента, а не по SEO. Прямая альтернатива Brave Search / Perplexity. Zero cost — критично для регулярного использования.

---

### 3. openclaw-free-web-search
**ClawHub:** https://clawskills.sh/skills/wd041216-bit-openclaw-free-web-search  
**Для чего:** Free, private web search для OpenClaw через self-hosted SearXNG + Scrapling anti-bot + мульти-источник с кросс-валидацией. Умеет оценивать доверие к ответу.  
**Почему интересен:** SearXNG — это open-source метапоисковик, можно развернуть на своём VPS. Scrapling обходит anti-bot защиты. Zero API keys, zero cost. Оценка доверия к ответу — отличная фича для исследований.

---

### 4. todo-boss
**ClawHub:** https://clawskills.sh/skills/ukraecho-todo-boss  
**Для чего:** Task capture + delegation tracking + ежедневный отчёт оставшихся задач. Заточен под Telegram.  
**Почему интересен:** Единственный скилл в категории Productivity, который紧密结合 Telegram и task delegation. Захват задач из чата + трекинг что передал sub-agent + ежедневный remainder — это exactly то, чего не хватает Аркаше для полноценной работы с задачами Дениса.

---

### 5. context-aware-delegation
**ClawHub:** https://clawskills.sh/skills/rgba-research-context-aware-delegation  
**Для чего:** Дай изолированным сессиям (cron jobs, sub-agents, event handlers) полный контекст из основной сессии. Решает проблему "sub-agent не знает что уже сделано".  
**Почему интересен:** Боль Аркаши — когда sub-agent запускается без контекста предыдущей работы. Этот скилл буквально делает sub-agent умнее, давая им память основной сессии. Совместим с текущим MindGraph подходом.

---

### 6. super-research
**ClawHub:** https://clawskills.sh/skills/heldinhow-super-research  
**Для чего:** Ultimate AI research system — комбинирует 8 лучших research skills в один фреймворк.  
**Почему интересен:** Комбайн из 8 топовых скиллов. Может заменить несколько специализированных скиллов одним. Для глубоких исследований (то, чем занимается Денис с корпоративной базой знаний) — мощный инструмент.

---

### 7. social-intelligence
**ClawHub:** https://clawskills.sh/skills/atyachin-social-intelligence  
**Для чего:** AI-powered social media research через Twitter, Instagram, Reddit. 1.5B+ постов проиндексировано.  
**Почему интересен:** Быстрая разведка по теме/бренду/конкуренту за минуты. 1.5B постов это больше чем большинство специализированных инструментов. Для Дениса — мгновенный Social Listening без отдельного сервиса.

---

### 8. twitter-api-alternative
**ClawHub:** https://clawskills.sh/skills/atyachin-twitter-api-alternative  
**Для чего:** Twitter API Alternative — Search 1B+ tweets с natural language queries, boolean filters, one-click CSV export.  
**Почему интересен:** 1 миллиард твитов без Twitter API (который стоит $100+/мес). Natural language queries + CSV export — можно сразу загружать в свою базу знаний для анализа.

---

### 9. agent-deep-research
**ClawHub:** https://clawskills.sh/skills/24601-agent-deep-research  
**Для чего:** Autonomous deep research, powered by Google Gemini.  
**Почему интересен:** Gemini в основе — одна из самых сильных моделей для reasoning. Полностью автономный research workflow. Если Денис хочет ставить исследовательские задачи и получать готовый отчёт — это next step после базового поиска.

---

### 10. session-watchdog
**ClawHub:** https://clawskills.sh/skills/xbillwatsonx-session-watchdog  
**Для чего:** Мониторит уровень контекста сессии и проактивно сохраняет checkpoint'ы перед compaction.  
**Почему интересен:** Решает реальную проблему: контекст сжимается и важные данные теряются. Watchdog сохраняет состояние до compaction — можно восстановить. Для долгих исследовательских сессий — страховка от потери данных.

---

## ТОП-5 приоритетов для установки

| # | Скилл | Почему приоритет 1 | ClawHub |
|---|-------|-------------------|---------|
| **1** | `todo-boss` | Самая большая боль Аркаши сейчас — нет полноценного управления задачами в Telegram. Этот скилл решает конкретную проблему: task capture + delegation tracking + daily report. Plug-and-play. | https://clawskills.sh/skills/ukraecho-todo-boss |
| **2** | `context-aware-delegation` | Sub-agents работают вслепую без контекста основной сессии. Это фундаментальное улучшение для multi-agent архитектуры Аркаши. С небольшой адаптацией под текущий MindGraph workflow. | https://clawskills.sh/skills/rgba-research-context-aware-delegation |
| **3** | `openclaw-free-web-search` | Zero-cost, privacy-first веб-поиск с кросс-валидацией источников и оценкой доверия. Заменяет платные API (Brave Search, Perplexity) для регулярных исследований. | https://clawskills.sh/skills/wd041216-bit-openclaw-free-web-search |
| **4** | `meyhem-search` + `meyhem-researcher` | Пара: быстрый поиск + глубокое исследование. Оба учатся со временем. Оба бесплатные, без API-key. Идеально для корпоративной базы знаний Дениса — собирают и структурируют информацию. | https://clawskills.sh/skills/c5huracan-meyhem-search + https://clawskills.sh/skills/c5huracan-meyhem-researcher |
| **5** | `session-watchdog` | Страховка от потери контекста при compaction. Чем больше Аркаша работает с долгими сессиями (исследования, документы), тем критичнее. Простой скилл, большая польза. | https://clawskills.sh/skills/xbillwatsonx-session-watchdog |

---

## Что не попало в TOP, но值得关注

- **`super-research`** (#6 в TOP-10) — мощный комбайн, но требует настройки и может конфликтовать с уже установленными research-скиллами. Поставить после освоения базовых.
- **`social-intelligence`** (#7) — отличный инструмент для Social Listening, но требует отдельного аккаунта/регистрации на платформе. Для Дениса пока вторичен.
- **`competitor-analysis-report`** — узкоспециализированный B2B-инструмент, не так универсален для текущих задач.
- **`agent-autopilot`** — автономный self-driving workflow, но слишком heavy для текущего использования Аркаши.

---

## Выводы по категориям

**Search & Research:** Огромное поле, но большинство — нишевые (crypto, academic,法律). Реально универсальных штук 5-7. Лидеры: meyhem, openclaw-free-web-search, super-research.

**Productivity & Tasks:** 205 скиллов — море специализированных интеграций (Asana, ClickUp, Wrike и т.д.). Скиллы общего назначения редки. `todo-boss` выделяется как самый практичный для Telegram-centric workflow. `context-aware-delegation` — архитектурно важный.

**Communication:** 146 скиллов, половина — социальные сети и мессенджеры. Для Аркаши (Telegram) критичны: voice/sms/outbound-call интеграции, но они требуют внешних сервисов (Twilio, ElevenLabs). Пока не приоритет без конкретного use case.
