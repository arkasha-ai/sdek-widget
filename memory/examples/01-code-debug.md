# Few-Shot: Код и отладка

## Паттерн: Debug Workflow

**Ситуация:** Код не работает, ошибка непонятна.

**План действий:**
1. Воспроизвести ошибку — получить точный стектрейс
2. Изолировать проблему — какой модуль/функция
3. Проверить края: None, пустые значения, некорректные типы
4. Исправить минимально
5. Проверить что не сломалось другое

**Пример запроса:**
```
Есть ошибка: ModuleNotFoundError: No module named 'httpx_socks'
Файл: backend/app/services/image_gen_service.py
Импорт: import httpx_socks
requirements.txt есть, но не добавляется в контейнер
```

**Правильный ответ:**
```
1. Проблема: httpx_socks — это дополнительный extras, не базовый httpx
2. Решение: в requirements.txt должно быть `httpx[http2,socks]` или `httpx-socks[asyncio]`
3. Проверка: requirements.txt содержит `httpx-socks[asyncio]==0.9.2` — правильно
4. Причина: Dokploy собирает образ заново, старый кэш — нужен rebuild
```

## Паттерн: Исправление файла без потери

**Ситуация:** Нужно редактировать файл, write tool может сломать синтаксис.

**Правило:** Если файл ценный — сначала `cp backup`, потом правка.

**Пример:**
```bash
cp backend/app/api/v1/cards.py backend/app/api/v1/cards.py.bak
```

Потом edit tool минимально.

## Паттерн: Python typing check

```python
# Всегда проверяй None перед работой
if value is None:
    return default
# Или
value = value or default

# Проверка типов
if not isinstance(value, dict):
    return {}
```

## Паттерн: Git workflow

1. Проверить статус: `git status`
2. Посмотреть diff: `git diff`
3. Запушить: `git add . && git commit -m "feat: description" && git push`
4. Если конфликт — fetch → merge/rebase
