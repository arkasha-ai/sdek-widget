# VK API — Получение постов

## Токен
- Сервисный ключ: `VK_SERVICE_TOKEN` в `~/.openclaw/secrets.env`
- Создаётся на vk.com/apps → Создать приложение (Standalone) → Настройки → Сервисный ключ

## Важно
- Даже для публичных групп нужен токен — без него API возвращает error_code 15
- Сервисного ключа достаточно для чтения публичных групп

## Получение постов
```bash
TOKEN=$(grep VK_SERVICE_TOKEN ~/.openclaw/secrets.env | cut -d= -f2)
curl -s "https://api.vk.com/method/wall.get?domain=<group_id>&count=10&access_token=$TOKEN&v=5.131"
```

## Python
```python
import os, requests

token = os.environ.get('VK_SERVICE_TOKEN')
r = requests.get('https://api.vk.com/method/wall.get', params={
    'domain': 'cafelulu',  # или числовой id группы
    'count': 10,
    'access_token': token,
    'v': '5.131'
})
posts = r.json()['response']['items']
for p in posts:
    print(p['text'][:200])
```

## Тестовая группа
- `cafelulu` — кафе ЛуЛу (Пенза), публичная группа
- Проверено: работает ✅

## Полезные методы
- `wall.get` — посты со стены
- `wall.search` — поиск по постам
- `groups.getById` — инфо о группе
- `photos.get` — фото группы
