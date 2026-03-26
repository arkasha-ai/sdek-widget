# Few-Shot: Исследование и поиск

## Паттерн: Web Search

**Запросы:**
- Конкретные факты → Google Search
- Технические детали → официальные доки
- Мнения/обзоры → Reddit, forums
- Цены → официальные сайты

**Формат ответа:**
```
Найдено: [краткий ответ]
Источник: [url]
Детали: [если нужно]
```

## Паттерн: Анализ сервиса/API

**Чеклист:**
1. Ping — работает ли вообще
2. Health endpoint — `/health`, `/api/health`
3. Auth — нужен ли токен
4. Rate limits — сколько запросов допустимо
5. Errors — какие status codes что значат

**Пример:**
```bash
curl -s https://api.service.com/health
curl -s -H "Authorization: Bearer $TOKEN" https://api.service.com/v1/data
```

## Паттерн: Сравнение моделей

При выборе модели для задачи:

| Критерий | Модель A | Модель B |
|----------|----------|----------|
| Скорость | fast | medium |
| Качество текста | среднее | высокое |
| Код | слабо | сильно |
| Цена | $0.8/M | $3/M |

**Решение:** Для простых задач — A, для сложных — B.

## Паттерн: Работа с памятью

**Перед ответом о человеке/проекте:**
```bash
# MindGraph
source ~/.openclaw/secrets.env
curl -s -X POST http://127.0.0.1:18790/retrieve \
  -H "Authorization: Bearer $MINDGRAPH_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action":"text","query":"<запрос>","limit":5}'

# Или Qdrant
python3 ~/.openclaw/workspace/scripts/qdrant_indexer.py search "запрос"
```

**Никогда не придумывать факты** — только найденное в памяти или поиске.
