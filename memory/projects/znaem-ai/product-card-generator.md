# Product Card Generator — Шпаргалка

## Репозиторий
- Git: `git.jakeberrimor.com/znaem-ai/product-card-generator`
- Ветки: `develop` (рабочая) + `master` (прод)
- Dokploy деплоит **обе** ветки

## Стек
- **Backend:** FastAPI + SQLAlchemy async + asyncpg + Alembic + Redis
- **Bot:** aiogram 3.x + RedisStorage (FSM)
- **DB:** PostgreSQL (внешний Dokploy сервис)
- **Redis:** внешний Dokploy сервис
- **Генерация:** Gemini/FLUX через LiteLLM + Replicate + fal.ai

## Структура backend/
```
app/
  api/v1/          — роутеры (auth, cards, payments)
  core/            — pipeline, store, user_store (обёртки над repo)
  db/              — SQLAlchemy модели + session.py
  models/          — Pydantic схемы (request/response)
  repositories/    — CRUD (user_repo, job_repo, payment_repo)
  services/        — image_gen, layout, overlay, prompt, vision, audit
alembic/           — миграции (001_initial.py)
entrypoint.sh      — wait-for-db → alembic upgrade head → uvicorn
```

## Структура telegram-bot/
```
bot.py             — main() + Dispatcher + RedisStorage
config.py          — все константы и env
states.py          — FSM StatesGroup
handlers/          — start, balance, payment, generate, feedback, fallback
keyboards/         — menu, subscription, topup, generation, feedback
services/          — api_client (singleton session), auth (ensure_token), llm
utils/             — progress, image, polling, logger
```

## ENV переменные (важные)
```
DATABASE_URL=postgresql://...   # без +asyncpg, session.py сам заменяет
REDIS_URL=redis://...
TELEGRAM_BOT_TOKEN=...
TELEGRAM_PROVIDER_TOKEN=...     # YooKassa провайдер токен
LITELLM_BASE_URL=...
LITELLM_API_KEY=...
S3_ENDPOINT_URL / S3_ACCESS_KEY / S3_SECRET_KEY / S3_BUCKET_NAME
JWT_SECRET=...
ADMIN_API_KEY=...               # для admin эндпоинтов
```

## Сети Dokploy
- Все сервисы подключены к `dokploy-network` (external)
- Postgres hostname: `jakeberrimor-postgres-oifqsh`
- Redis hostname: `jakeberrimor-redis-iyoxgx`
- IP: `80.87.197.0` (работает с хоста, но не всегда из контейнера)

## DB таблицы
- `users` — email + telegram auth, credits
- `jobs` — задания генерации (JSONB для scenarios/analysis)
- `payments` — YooKassa платежи (idempotency через external_id)
- `credit_transactions` — лог кредитов
- `audit_log` — лог действий и LLM вызовов

## Важные файлы для дебага
- `backend/app/db/session.py` — движок SQLAlchemy (ssl=False!)
- `backend/alembic/env.py` — миграции (ssl=False, +asyncpg в URL)
- `backend/app/core/store.py` → `repositories/job_repo.py`
- `backend/app/core/user_store.py` → `repositories/user_repo.py`

## Правила работы с кодом
⚠️ НИКОГДА не пушить без локальной проверки!

Проверка бэкенда:
```bash
cd backend && DATABASE_URL="..." REDIS_URL="..." DEBUG_LOGS_DIR="/tmp/dl" \
  python3 -m uvicorn app.main:app --port 800X &
sleep 5 && curl -s http://localhost:800X/health
```

Проверка бота (импорты):
```bash
cd telegram-bot && TELEGRAM_BOT_TOKEN=test API_BASE_URL=http://localhost \
  python3 -c "from handlers import register_all_routers; print('OK')"
```

Алembic (миграции):
```bash
cd backend && DATABASE_URL="..." python3 -m alembic upgrade head
```

## Известные проблемы / решения (все закрыты ✅)
- **Сеть контейнеров:** все сервисы в `dokploy-network` — внутренние hostname резолвятся ✅
- **asyncpg SSL таймаут:** `ssl=False` в session.py и alembic/env.py ✅
- **Docker кэш pip:** cache-bust комментарий в Dockerfile ✅
- **Migrate on start:** entrypoint.sh ждёт порт БД (30 попыток × 2 сек) потом alembic upgrade head ✅
- **FSM слетает при рестарте:** RedisStorage в боте ✅
- **OOM риск:** photo_file_id вместо байтов в FSM, result_urls вместо байтов ✅
