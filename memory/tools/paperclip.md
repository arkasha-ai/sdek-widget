# Paperclip — правила работы

## Конфигурация
- API URL: `https://paperclip.znaemai.ru`
- API Key: `~/.openclaw/workspace/paperclip-claimed-api-key.json`
- Agent ID: `7fba4a1f-dbb5-49a9-ad74-4840f5556a52`
- Company ID: `b246cf3d-2eda-4223-8ff6-5be30c598eca`

## Моя роль
Я — **посредник** между Денисом (заказчик) и командой (Максим CEO + Дмитрий Engineer).
- Команда работает в Paperclip
- Денис общается со мной в Telegram
- Я транслирую решения заказчика команде и обратно

## Как писать команде
**ТОЛЬКО через Paperclip API** — комментарии к задачам:
```bash
curl -s -X POST "$PAPERCLIP_API_URL/api/issues/$ISSUE_ID/comments" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"body": "@Максим, ..."}'
```
**НЕ через Redis relay** — это не работает для Paperclip агентов!

## Как передавать ответы заказчика
1. Получил вопрос от команды в Paperclip
2. Написал в ZnaemAI (`-1003831241406`) — кратко, с конкретными вопросами
3. Дождался ответа Дениса
4. Написал в Paperclip комментарий с ответом

## Когда НЕ выдумывать ответы
Если заказчик не давал ответ — **не придумывать самому**. Писать команде что жду ответа заказчика.

## Назначение задач
- Создаю задачи через: `POST /api/companies/$COMPANY_ID/issues`
- **⚠️ ОБЯЗАТЕЛЬНО ставить исполнителя при создании** — `assigneeAgentId` в теле запроса
- CEO ID: `a5893697-cd59-40e4-b7f7-51ccd26b77b5`
- Engineer ID: `5a630270-602f-434a-bedf-8c244f04cc61`
- Если 403 при назначении в create → создать задачу без assignee, потом `PATCH /api/issues/$ISSUE_ID` с `{"assigneeAgentId": "..."}`

## Cron мониторинг
Каждые 30 минут проверяю активность. Если ничего нового — молчу.
Если есть что-то важное — пишу в ZnaemAI.

## Проекты
- **Product Card Generator** — `znaem-ai/product-card-generator` на Gitea
  - Формат карточки: 4:5
  - Хранилище: S3 (FirstVDS)
  - Авторизация: не нужна
  - Vision-модель: claude-sonnet через litellm
