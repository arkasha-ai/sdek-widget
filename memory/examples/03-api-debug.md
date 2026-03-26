# Few-Shot: API и интеграции

## Паттерн: Debug HTTP запроса

**Формат отладки любого API:**

```
Метод: GET/POST/PUT/DELETE
URL: https://api.example.com/endpoint
Headers: {key: value}
Body: {...}

Response status: 200/404/500
Response body: {...}

Проблема: [описание]
Вероятная причина: [анализ]
Решение: [конкретное действие]
```

## Паттерн: Telegram Bot Webhook

**Проверка:**
```bash
curl -s http://95.81.99.103:18789/health
curl -s http://localhost:18789/health
```

**Проблемы и решения:**
| Проблема | Решение |
|----------|---------|
| 502 Bad Gateway | Gateway упал — restart |
| Webhook не доходит | Проверить IP whitelist в Telegram |
| Бот не отвечает | Логи: `tail -100 /tmp/openclaw/openclaw-*.log` |
| Rate limit | Подождать, уменьшить частоту запросов |

## Паттерн: Google API через SOCKS5

```python
# Правильный формат
import httpx
from httpx_socks import AsyncProxyTransport

transport = AsyncProxyTransport.from_url(
    "socks5://user:pass@host:port"
)
client = httpx.AsyncClient(transport=transport)
```

**Важно:**
- URL: `socks5://` (не `socks5h://`) — чтобы DNS резолвился локально
- `httpx_socks` импортировать внутри функции (не на уровне модуля)
- Проверять response status — 200 не гарантирует успех

## Паттерн: GitHub API

```bash
# Через SSH
git clone git@github.com:owner/repo.git

# Через token
curl -H "Authorization: token $TOKEN" https://api.github.com/repos/owner/repo

# Проверка 2FA для коммитов
oathtool --totp --base32 "$(grep GITHUB_2FA_SECRET ~/.openclaw/secrets.env | cut -d= -f2)"
```

## Паттерн: Gitea Webhook → Dokploy Deploy

```
Gitea webhook → Dokploy compose auto-deploy
Webhook URL: https://dokploy.jakeberrimor.com/api/deploy/compose/<token>
Branch: должен совпадать с настроенным
Деплой: автоматический при пуше
```
