# SellerShot — Информация о проекте

## Общее

- **Название:** SellerShot
- **Что делает:** Telegram-бот для автоматической генерации профессиональных карточек товаров для маркетплейсов
- **Маркетплейсы:** Wildberries, Ozon, Яндекс Маркет, Aliexpress, Avito
- **Telegram бот:** [@sellershot_bot](https://t.me/sellershot_bot)
- **Домен:** sellershot.ru
- **MVP URL:** https://znaemai-card-generator.jakeberrimor.com
- **TG-канал:** [@znaem_ai](https://t.me/znaem_ai)
- **Дисклеймер:** https://telegra.ph/Pravila-ispolzovaniya-03-30

---

## Команда

| Имя | Роль | Контакт |
|-----|------|---------|
| Денис Пармеев | Технический основатель | @JakeBerrimor |
| Михаил Коржов | Со-основатель, бизнес и продажи | @mskorzhov |
| Аркадий | AI-ассистент, посредник | в боте |
| Максим | AI CEO (Paperclip) — планирование | Paperclip |
| Дмитрий | AI Engineer (Paperclip) — разработка | Paperclip |

---

## Технический стек

### Backend (FastAPI)
- **Python 3.10+**, FastAPI, Uvicorn
- **PostgreSQL** — хранение пользователей, заказов, платежей (Alembic для миграций)
- **Redis** — кэширование, верификационные токены
- **LiteLLM Proxy** — единый интерфейс к LLM моделям

### Telegram Bot (aiogram 3)
- **aiogram 3.15** — асинхронный Telegram Bot API
- **Pillow** — сжатие изображений перед отправкой (лимит Telegram 10MB)
- FSM (Finite State Machine) для управления диалогом

### Генерация изображений
- **BananaHub API** (api.bananalab.pw) — прокси для Google Gemini моделей, в 2 раза дешевле
- **Google Gemini** — генерация изображений (img2img)
- **Playwright** — HTML/CSS overlay для текста на карточках
- **S3** (firstvds.ru) — хранение результатов

### Инфраструктура
- **Dokploy** — деплой через Docker Compose
- **Traefik** — reverse proxy, SSL
- **Nginx** — внутренний reverse proxy (rate limiting)
- **Gitea** — git-репозиторий (git.jakeberrimor.com/znaem-ai/product-card-generator)

---

## Модели генерации

| Тариф | Модель | BananaHub цена | Кредитов |
|-------|--------|---------------|----------|
| ⭐ Стандарт | gemini-2.5-flash-image | $0.0195 | 5 |
| 💎 Про | gemini-3.1-flash-image-preview | $0.0225 | 10 |
| 👑 Премиум | gemini-3-pro-image-preview | $0.0670 | 15 |

**Разрешение:** 4K
**Fallback:** если BananaHub недоступен → Google AI Studio напрямую

### LLM модели (бэкенд)
- **claude-haiku-4-5** — анализ фото, сценарии, промпты, HTML layout
- **Qwen3-Coder-480B** — генерация HTML/CSS для текстового overlay

---

## Форматы карточек

| Формат | Маркетплейс |
|--------|-------------|
| 3:4 | Wildberries, Ozon |
| 1:1 | Ozon, WB, Aliexpress |
| 4:3 | Avito, Яндекс Маркет |
| 9:16 | Stories, Shorts |

---

## Монетизация

### Кредитная система
- Новый пользователь: **50 бесплатных кредитов** (за подписку на @znaem_ai)
- 1 карточка = 5–15 кредитов (зависит от модели)

### Пакеты пополнения
| Пакет | Кредиты | Цена |
|-------|---------|------|
| Мини-пакет | 100 | 1 000 ₽ |
| Стандарт | 220 | 2 000 ₽ |
| Про | 600 | 5 000 ₽ |
| Бизнес | 2 000 | 15 000 ₽ |

### Оплата
- **ЮКасса** — нативные Telegram Payments (sendInvoice)
- Provider token подключён через @BotFather
- Автоматические чеки (фискализация)

---

## Пайплайн генерации карточки

```
1. Пользователь загружает фото товара
2. claude-haiku-4-5 анализирует фото (товар, категория, цвет, размер, ЦА)
3. claude-haiku-4-5 генерирует N сценариев (бассейн, дом, офис и т.д.)
4. Автоматический approve всех сценариев
5. Для каждого сценария:
   a. claude-haiku-4-5 строит image prompt
   b. BananaHub/Gemini генерирует изображение (img2img)
   c. claude-haiku-4-5 генерирует HTML/CSS layout с текстом
   d. Playwright рендерит HTML поверх изображения
   e. Результат загружается в S3
6. Бот отправляет карточки пользователю
```

---

## Фичи бота

- 📸 Загрузка фото → выбор формата → выбор количества → пожелания → генерация
- 🔄 Перегенерация отдельной карточки (новый сценарий)
- ✏️ Редактирование текста на карточке
- 📄 Скачивание файлов (по одной или ZIP)
- 💳 Пополнение баланса через ЮКассу
- 💰 Просмотр баланса кредитов
- 📢 Проверка подписки на канал @znaem_ai

---

## Git workflow

- **master** — продакшн, деплоится автоматически через Dokploy webhook
- **develop** — разработка, тестирование
- Merge через PR в Gitea (https://git.jakeberrimor.com/znaem-ai/product-card-generator)

---

## Env переменные (бэкенд)

| Переменная | Описание |
|-----------|----------|
| DATABASE_URL | PostgreSQL connection string |
| REDIS_URL | Redis connection string |
| LITELLM_BASE_URL | LiteLLM proxy URL |
| LITELLM_API_KEY | LiteLLM API key |
| BANANAHUB_API_KEY | BananaHub API key |
| GOOGLE_AI_KEY | Google AI Studio key (fallback) |
| S3_ENDPOINT_URL | S3 storage endpoint |
| S3_ACCESS_KEY / S3_SECRET_KEY | S3 credentials |
| JWT_SECRET | JWT signing secret |
| YOOKASSA_SHOP_ID | ЮКасса Shop ID |
| YOOKASSA_SECRET_KEY | ЮКасса Secret Key |
| ADMIN_API_KEY | API key для админ-эндпоинтов |
| TELEGRAM_BOT_TOKEN | Telegram Bot API token |
| TELEGRAM_PROVIDER_TOKEN | ЮКасса payment provider token |

---

*Последнее обновление: 30 марта 2026*
