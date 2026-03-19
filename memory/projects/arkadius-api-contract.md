# Аркадиус — API контракт v1.0

> REST API между OpenClaw-fork (бэкенд) и клиентом (веб/мобильное приложение)
> 
> Base URL: `https://api.arkadius.app/v1`
> Формат: JSON | Auth: Bearer token (JWT) | Encoding: UTF-8

---

## Общие соглашения

- **Auth:** Все защищённые endpoints требуют заголовок `Authorization: Bearer <access_token>`
- **Ошибки:** Стандартный формат `{ "error": { "code": "string", "message": "string" } }`
- **Пагинация:** `?page=1&limit=20` — по умолчанию limit=20, max=100
- **HTTP коды:** 200 OK, 201 Created, 400 Bad Request, 401 Unauthorized, 403 Forbidden, 404 Not Found, 429 Rate Limited, 500 Server Error

---

## 1. Auth

### POST `/auth/register`
Регистрация нового пользователя.

| | |
|---|---|
| **Auth** | ❌ |
| **Request** | `{ "email": "string", "password": "string", "name": "string" }` |
| **Response 201** | `{ "user": { "id": "uuid", "email": "string", "name": "string", "created_at": "iso8601" }, "access_token": "jwt", "refresh_token": "string", "expires_in": 3600 }` |
| **Ошибки** | `409 email_taken` — email уже зарегистрирован |

### POST `/auth/login`
Вход по email/password.

| | |
|---|---|
| **Auth** | ❌ |
| **Request** | `{ "email": "string", "password": "string" }` |
| **Response 200** | `{ "user": { "id": "uuid", "email": "string", "name": "string" }, "access_token": "jwt", "refresh_token": "string", "expires_in": 3600 }` |
| **Ошибки** | `401 invalid_credentials` |

### POST `/auth/refresh`
Обновление access token через refresh token.

| | |
|---|---|
| **Auth** | ❌ |
| **Request** | `{ "refresh_token": "string" }` |
| **Response 200** | `{ "access_token": "jwt", "refresh_token": "string", "expires_in": 3600 }` |
| **Ошибки** | `401 invalid_refresh_token` — токен истёк или отозван |

### POST `/auth/logout`
Отзыв refresh token (инвалидация сессии).

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "refresh_token": "string" }` |
| **Response 200** | `{ "ok": true }` |

---

## 2. User / Agent

### GET `/user/profile`
Получить профиль текущего пользователя.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Response 200** | `{ "id": "uuid", "email": "string", "name": "string", "avatar_url": "string|null", "credits_balance": 0, "agent": { "name": "string", "persona": "string|null", "model": "string" }, "created_at": "iso8601" }` |

### PATCH `/user/profile`
Обновить профиль пользователя.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "name?": "string", "avatar_url?": "string" }` |
| **Response 200** | Обновлённый объект профиля (как GET) |

### GET `/user/agent`
Получить настройки персонального агента.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Response 200** | `{ "agent_id": "uuid", "name": "string", "persona": "string|null", "model": "string", "temperature": 0.7, "system_prompt": "string|null", "tools_enabled": ["web_search", "code_exec"], "memory_enabled": true }` |

### PATCH `/user/agent`
Обновить настройки агента.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "name?": "string", "persona?": "string", "model?": "string", "temperature?": 0.0-2.0, "system_prompt?": "string", "tools_enabled?": ["string"], "memory_enabled?": true }` |
| **Response 200** | Обновлённый объект агента |
| **Ошибки** | `400 invalid_model` — модель не поддерживается |

---

## 3. Credits

### GET `/credits/balance`
Текущий баланс кредитов.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Response 200** | `{ "balance": 1500, "currency": "credits", "usd_equivalent": 1.50 }` |

### POST `/credits/topup`
Пополнение баланса (инициация платежа).

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "amount": 1000, "payment_method": "card|yookassa|crypto", "return_url": "string" }` |
| **Response 200** | `{ "payment_id": "uuid", "payment_url": "string", "amount": 1000, "status": "pending" }` |
| **Примечание** | Клиент редиректит пользователя на `payment_url`. После оплаты — webhook обновляет баланс. |

### GET `/credits/history`
История транзакций (пополнения и списания).

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Query** | `?page=1&limit=20&type=topup|usage|all` |
| **Response 200** | `{ "transactions": [{ "id": "uuid", "type": "topup|usage", "amount": 500, "balance_after": 2000, "description": "Chat message (claude-sonnet)", "created_at": "iso8601" }], "total": 42, "page": 1, "limit": 20 }` |

---

## 4. Chat

### GET `/chats`
Список чатов (разговоров) пользователя.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Query** | `?page=1&limit=20` |
| **Response 200** | `{ "chats": [{ "id": "uuid", "title": "string|null", "last_message_at": "iso8601", "message_count": 15, "model": "string", "created_at": "iso8601" }], "total": 8, "page": 1 }` |

### POST `/chats`
Создать новый чат.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "title?": "string", "model?": "string" }` |
| **Response 201** | `{ "id": "uuid", "title": null, "model": "claude-sonnet-4-6", "created_at": "iso8601" }` |

### GET `/chats/:chatId/messages`
История сообщений в чате.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Query** | `?limit=50&before=<message_id>` (cursor-based pagination, новые сверху) |
| **Response 200** | `{ "messages": [{ "id": "uuid", "role": "user|assistant|system", "content": "string", "attachments": [{ "id": "uuid", "filename": "string", "url": "string", "content_type": "string" }], "credits_used": 12, "model": "string|null", "created_at": "iso8601" }], "has_more": true }` |

### POST `/chats/:chatId/messages`
Отправить сообщение и получить ответ агента (SSE stream).

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Request** | `{ "content": "string", "attachments?": ["file_id1", "file_id2"] }` |
| **Response** | `text/event-stream` (SSE) |
| **Ошибки** | `402 insufficient_credits`, `404 chat_not_found` |

**SSE события:**

```
event: message_start
data: {"message_id": "uuid", "model": "claude-sonnet-4-6"}

event: content_delta
data: {"delta": "Привет! Как "}

event: content_delta
data: {"delta": "я могу помочь?"}

event: tool_use
data: {"tool": "web_search", "input": {"query": "..."}}

event: tool_result
data: {"tool": "web_search", "output": "..."}

event: message_end
data: {"message_id": "uuid", "credits_used": 15, "finish_reason": "end_turn"}

event: error
data: {"code": "rate_limited", "message": "Too many requests"}
```

### DELETE `/chats/:chatId`
Удалить чат и все сообщения.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Response 200** | `{ "ok": true }` |

---

## 5. Files

### POST `/files/upload`
Загрузить файл (для вложений в чат).

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Content-Type** | `multipart/form-data` |
| **Body** | `file` — бинарный файл, max 25MB |
| **Response 201** | `{ "id": "uuid", "filename": "report.pdf", "content_type": "application/pdf", "size": 1048576, "url": "string", "created_at": "iso8601" }` |
| **Ошибки** | `413 file_too_large`, `415 unsupported_type` |
| **Допустимые типы** | `image/*`, `application/pdf`, `text/*`, `application/json`, `application/msword`, `application/vnd.openxmlformats-*` |

### GET `/files`
Список загруженных файлов.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Query** | `?page=1&limit=20` |
| **Response 200** | `{ "files": [{ "id": "uuid", "filename": "string", "content_type": "string", "size": 1048576, "url": "string", "created_at": "iso8601" }], "total": 5, "page": 1 }` |

### DELETE `/files/:fileId`
Удалить загруженный файл.

| | |
|---|---|
| **Auth** | ✅ Bearer |
| **Response 200** | `{ "ok": true }` |
| **Ошибки** | `404 file_not_found` |

---

## 6. Rate Limits

| Endpoint | Лимит | Окно |
|----------|-------|------|
| `POST /auth/*` | 10 req | 1 мин |
| `POST /chats/:id/messages` | 30 req | 1 мин |
| `POST /files/upload` | 20 req | 1 мин |
| Остальные | 120 req | 1 мин |

При превышении: `429 Too Many Requests` + заголовок `Retry-After: <seconds>`.

---

## 7. Webhooks (server-to-server)

### Payment Callback
Вызывается платёжной системой после успешной оплаты.

```
POST /webhooks/payment
{
  "payment_id": "uuid",
  "status": "completed|failed",
  "amount": 1000,
  "provider_tx_id": "string"
}
```

---

## Будущие endpoints (v1.1+)

- `GET /models` — список доступных моделей и их стоимость в кредитах
- `POST /auth/oauth/:provider` — OAuth через Google/GitHub/Telegram
- `POST /chats/:id/fork` — форк чата с определённого сообщения
- `GET /user/usage` — детальная статистика использования
- `WS /chats/:id/stream` — WebSocket альтернатива SSE
