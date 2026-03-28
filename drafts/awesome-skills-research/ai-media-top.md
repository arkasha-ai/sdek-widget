# ТОП-10 скиллов: AI & LLMs + Image & Video Generation

Источник: [awesome-openclaw-skills](https://github.com/VoltAgent/awesome-openclaw-skills)  
Категории: AI & LLMs (184 скилла) + Image & Video Generation (170 скиллов)

---

## ТОП-10 самых полезных скиллов

### 1. agent-memory
**Назначение:** Постоянная память для AI-агентов — сохраняет данные между сессиями.  
**Почему интересен:** Аркаша уже использует MindGraph, но agent-memory может дополнить его — это специализированный скилл для долговременной памяти агента, интеграция с агентом напрямую, без отдельного сервера. Критически важен для агента который работает 24/7.  
**Ссылка:** https://clawskills.sh/skills/dennis-da-menace-agent-memory

---

### 2. metacognition
**Назначение:** Self-reflection engine — заставляет агента думать о своих действиях перед тем как действовать.  
**Почему интересен:** Помогает агенту не делать глупостей "с ходу". Цепочка мыслей перед действием — драматически улучшает качество ответов в сложных задачах. Прямо перекликается с правилом "Chain-of-thought для сложных задач" из SOUL.md.  
**Ссылка:** https://clawskills.sh/skills/meimakes-metacognition

---

### 3. moa (Mixture of Agents)
**Назначение:** Запускает 3 frontier-модели, каждая даёт свой ответ, затем синтезирует лучшее в один superior ответ.  
**Почему интересен:** Один из самых элегантных подходов к качеству — не одна модель, а "коллегия экспертов". Для Аркаши это могло бы значительно улучшить качество анализа и принятия решений. Может использоваться для сложных запросов.  
**Ссылка:** https://clawskills.sh/skills/jscianna-moa

---

### 4. anti-injection-skill
**Назначение:** Многослёвая защита от prompt injection — обёртка над tool calls для защиты памяти и инструкций агента.  
**Почему интересен:** Безопасность критична. Агент с доступом к личным данным Дениса должен быть защищён от внешних инъекций. Библиотека на 361+ skill audit выглядит серьёзно.  
**Ссылка:** https://clawskills.sh/skills/georges91560-anti-injection-skill

---

### 5. context-gatekeeper
**Назначение:** Держит контекст в рамках token-лимита — суммаризирует recent exchanges, вытаскивает pending actions.  
**Почему интересен:** MiniMax-M2.7 имеет лимит контекста. Этот скилл автоматически "подчищает" контекст, чтобы агент не терял нить в длинных сессиях. Прямая польза для Аркаши.  
**Ссылка:** https://clawskills.sh/skills/davienzomq-context-gatekeeper

---

### 6. fal-ai
**Назначение:** Единый доступ к FLUX, SDXL, Whisper, генерации видео и аудио через fal.ai API.  
**Почему интересен:** Один скилл вместо нескольких. Fal.ai — один из лучших API для image/video/audio. Покрывает сразу три модальности. Уже есть `fal-image` скилл, но этот — комплекснее (fal-ai даёт и видео, и аудио).  
**Ссылка:** https://clawskills.sh/skills/agmmnn-fal-ai

---

### 7. eachlabs-image-generation
**Назначение:** Генерация изображений через Flux, GPT Image, Gemini, Imagen — более 200 AI-моделей.  
**Почему интересен:** Самое большое покрытие моделей в одном скилле. Можно выбирать лучшую модель для конкретной задачи, а не зависеть от одной. Для генерации карточек товаров (Paperclip) — идеально.  
**Ссылка:** https://clawskills.sh/skills/eftalyurtseven-eachlabs-image-generation

---

### 8. ai-video-gen
**Назначение:** End-to-end AI video generation — создание видео из текста.  
**Почему интересен:** Видео — следующая модальность. Если Аркаше когда-нибудь понадобится генерировать видео-контент (демо, реклама, аватарки), этот скилл даст такую возможность.  
**Ссылка:** https://clawskills.sh/skills/rhanbourinajd-ai-video-gen

---

### 9. ai-podcast
**Назначение:** PDF или текст → натуральный two-person podcast с двумя голосами.  
**Почему интересен:** У Аркаши уже есть Podcast generator через Yandex, но этот подход — принципиально другой: берёт документ/PDF и превращает в подкаст. Можно слушать документы вместо чтения.  
**Ссылка:** https://clawskills.sh/skills/mogens9-ai-podcast

---

### 10. agentpulse
**Назначение:** Track LLM API costs, tokens, latency и errors.  
**Почему интересен:** MiniMax стоит денег. agentpulse даст полную прозрачность — кто сколько потратил, где latency, какие ошибки. Критически важен для контроля расходов.  
**Ссылка:** https://clawskills.sh/skills/sru4ka-agentpulse

---

## ТОП-5 приоритетов для установки

### Приоритет 1: agent-memory
**Почему первый:** Память — фундамент. Каждая сессия Аркаша читает файлы, но постоянная память между сессиями (в отличие от файлов) — это следующий уровень. Без хорошей памяти любой агент деградирует.  
**Установка:** `clawhub install dennis-da-menace-agent-memory`

### Приоритет 2: context-gatekeeper
**Почему второй:** MiniMax-M2.7 имеет лимит контекста. Аркаша работает в long-running сессиях — без управления контекстом будет терять важное. Быстрая установка, прямая польза каждый день.  
**Установка:** `clawhub install davienzomq-context-gatekeeper`

### Приоритет 3: anti-injection-skill
**Почему третий:** Агент с доступом к личным данным, почте, файлам Дениса. Защита от prompt injection — не "может быть полезно", а "должно быть установлено". Безопасность не терпит отложек.  
**Установка:** `clawhub install georges91560-anti-injection-skill`

### Приоритет 4: fal-ai
**Почему четвёртый:** Fal.ai — один из лучших API для генерации изображений и видео. Уже есть qwen-image-gen и fal-image, но fal-ai даёт ещё и аудио + видео в одном скилле. Стоит попробовать как замену или дополнение.  
**Установка:** `clawhub install agmmnn-fal-ai`

### Приоритет 5: metacognition
**Почему пятый:** Self-reflection engine. Незаменим для сложных задач. Аркаша и так использует chain-of-thought, но скилл формализует это и делает обязательным. Поможет в planning, debugging, и принятии решений.  
**Установка:** `clawhub install meimakes-metacognition`

---

##Honorable mentions (не вошли в топ-10, но интересны)

- **smart-context** — альтернатива context-gatekeeper с focus на delegation
- **tokenguard** — ещё один cost-guardian, стоит попробовать вместе с agentpulse
- **eachlabs-video-generation** — видео от eachlabs (тот же провайдер что и image-gen)
- **comfyui-imagegen** — для тех кто хочет локальную генерацию через Flux
- **agent-autonomy-kit** — proactive agent behavior (не ждёт промпт, сам действует)
- **llmcouncil-router** — умный роутер между LLM на основе peer-reviewed rankings

---

*Составлено на основе анализа 184 + 170 скиллов из awesome-openclaw-skills. Дата: 2026-03-27.*
