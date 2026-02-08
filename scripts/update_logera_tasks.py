#!/usr/bin/env python3
"""
Logera Tasks Updater
Updates TickTick tasks for Logera ONLYOFFICE → Collabora migration project.
Adds detailed descriptions with implementation steps, timings, and links.

Project IDs:
- Back-end: 695bfb7263635125f7366b1d
- Front-end: 695bfb43ab63d125f7366aa6
"""
import json
import os
import urllib.request
import time

TOKEN_FILE = os.path.expanduser("~/.openclaw/workspace/.ticktick_token.json")
BASE_URL = "https://api.ticktick.com/open/v1"

def load_token():
    with open(TOKEN_FILE) as f:
        return json.load(f)['access_token']

def update_task(project_id, task_id, content):
    """Update task with content (description)"""
    token = load_token()
    url = f"{BASE_URL}/task/{task_id}"
    
    data = {
        "id": task_id,
        "projectId": project_id,
        "content": content
    }
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    req_data = json.dumps(data).encode()
    request = urllib.request.Request(url, data=req_data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())
    except Exception as e:
        return {"error": str(e)}

# Task descriptions mapping (title -> content)
BACKEND_TASKS = {
    "🔴 Phase 1: WOPI CheckFileInfo endpoint (GET /wopi/files/{id})": """
**Что делать:**
- Создать endpoint `GET /wopi/files/{file_id}` в back-end/api/routers/onlyoffice.py
- Вернуть JSON метаданных: BaseFileName, OwnerId, Size, Version, UserCanWrite, SupportsUpdate
- Проверять WOPI access token из query string

**Результат:** Collabora может запросить метаданные файла

**Время:** 4-6 часов
**Ссылка:** См. memory/logera-collabora-migration.md Phase 1.2
""",

    "🔴 Phase 1: WOPI GetFile endpoint (GET /wopi/files/{id}/contents)": """
**Что делать:**
- Создать endpoint `GET /wopi/files/{file_id}/contents`
- Вернуть binary stream файла из storage
- Headers: Content-Type (mime), Content-Disposition (filename)

**Результат:** Collabora может скачать файл для редактирования

**Время:** 2-3 часа
""",

    "🔴 Phase 1: WOPI PutFile endpoint (POST для сохранения)": """
**Что делать:**
- Создать endpoint `POST /wopi/files/{file_id}/contents`
- Принять binary body (обновленный файл)
- Сохранить в storage, создать новую версию (FsVersion)
- Обработать X-WOPI-Lock header если есть

**Результат:** Collabora может сохранять изменения

**Время:** 4-6 часов
""",

    "🔴 Phase 1: WOPI Access Token (генерация и валидация)": """
**Что делать:**
- Функция генерации WOPI access token (JWT с file_id, user_id, permissions)
- Middleware для проверки токена в WOPI endpoints
- TTL: 8 часов (как у текущих media tokens)

**Результат:** Безопасный доступ к WOPI API

**Время:** 2-3 часа
""",

    "🟡 Phase 2: Изучить Collabora PostMessage API": """
**Что делать:**
- Прочитать https://sdk.collaboraonline.com/docs/postmessage_api.html
- Изучить UNO commands: https://api.libreoffice.org/
- Понять разницу с ONLYOFFICE Office JS API
- Создать примеры базовых команд

**Результат:** Понимание как отправлять команды в Collabora

**Время:** 2-3 часа
""",

    "🟡 Phase 2: Переписать insert_text() для Collabora": """
**Что делать:**
- Заменить Office JS API на Collabora WebSocket
- Код: `window.app.socket.sendMessage('textinput input=' + JSON.stringify(text))`
- Обновить функцию `_gen_insert_text()` в document_editor.py

**Результат:** LLM может вставлять текст

**Время:** 1-2 часа
""",

    "🟡 Phase 2: Переписать insert_heading() с UNO": """
**Что делать:**
- Использовать `.uno:StyleApply?Style:string=Heading {level}`
- Обновить `_gen_insert_heading()` в document_editor.py
- Поддержка уровней 1-6

**Результат:** LLM может создавать заголовки

**Время:** 2-3 часа
""",

    "🟡 Phase 2: Переписать format_selection() для Collabora": """
**Что делать:**
- Использовать UNO commands: `.uno:Bold`, `.uno:Italic`, `.uno:Underline`
- Обновить `_gen_format_selection()` в document_editor.py
- Поддержка: bold, italic, underline, fontSize, color

**Результат:** LLM может форматировать текст

**Время:** 2-3 часа
""",

    "🔴 Phase 3: Обновить docker-compose.yml (collabora/code)": """
**Что делать:**
- Заменить onlyoffice контейнер на collabora/code
- Environment: domain, username, password, extra_params
- Volumes для брендинга: ./collabora/branding:/etc/loolwsd/branding:ro
- Port: 9980:9980

**Результат:** Collabora поднимается в Docker

**Время:** 1-2 часа
**Ссылка:** См. docker-compose.yml пример в плане миграции
""",

    "🟡 Phase 2B: Переписать insert_table() с UNO": """
**Что делать:**
- Использовать `.uno:InsertTable?Columns:long=3&Rows:long=5`
- Заполнение данных через последовательные UNO команды
- Обновить `_gen_insert_table()` в document_editor.py

**Результат:** LLM может создавать таблицы

**Время:** 4-6 часов
""",

    "🟡 Phase 2B: Переписать insert_list() с UNO": """
**Что делать:**
- Использовать `.uno:DefaultBullet` / `.uno:DefaultNumbering`
- Обновить `_gen_insert_list()` в document_editor.py

**Результат:** LLM может создавать списки

**Время:** 3-4 часа
""",

    "🟡 Phase 2B: Переписать replace_text() для Collabora": """
**Что делать:**
- Использовать `.uno:SearchDialog` или search API
- Обновить `_gen_replace_text()` в document_editor.py

**Результат:** LLM может заменять текст

**Время:** 3-4 часа
""",

    "🟢 Phase 5: Unit тесты WOPI endpoints": """
**Что делать:**
- pytest для CheckFileInfo, GetFile, PutFile, Lock
- Проверить edge cases: invalid token, missing file, large files

**Результат:** WOPI API работает корректно

**Время:** 4-6 часов
""",

    "🟢 Phase 5: Integration тест открытия документа": """
**Что делать:**
- End-to-end тест: создать файл → открыть в Collabora → проверить загрузку
- Использовать Playwright/Selenium для проверки iframe

**Результат:** Документы открываются без ошибок

**Время:** 2-3 часа
""",

    "🔵 Phase 6: Conversion API (txt/html для LLM)": """
**Что делать:**
- Заменить convert_document_to_text() на Collabora API или LibreOffice CLI
- `docker exec collabora libreoffice --headless --convert-to txt`
- Обновить convert_document_to_html()

**Результат:** LLM может читать документы

**Время:** 3-4 часа
""",

    "📝 Обновить README.md с инструкциями Collabora": """
**Что делать:**
- Документировать setup Collabora (Docker, ENV vars)
- Добавить troubleshooting секцию
- Migration guide для существующих ONLYOFFICE инсталляций

**Результат:** Команда знает как деплоить

**Время:** 2-3 часа
""",
}

FRONTEND_TASKS = {
    "🔴 Phase 3: Создать custom.css для брендинга": """
**Что делать:**
- Создать файл collabora/branding/custom.css
- Logera цвета (#2563eb), скрыть LibreOffice брендинг
- Кастомизация toolbar, header
- Добавить Logera logo

**Результат:** Collabora выглядит как часть Logera

**Время:** 2-3 часа
**Пример:** См. custom.css в плане миграции
""",

    "🔴 Phase 4: Создать CollaboraEditor.vue (iframe)": """
**Что делать:**
- Vue компонент с iframe для Collabora редактора
- Props: fileId, editable
- Загрузка config через API: GET /api/editor/config/{fileId}
- iframe src = collaboraUrl + WOPISrc + access_token

**Результат:** Базовый редактор работает

**Время:** 2-3 часа
""",

    "🔴 Phase 4: PostMessage API для LLM команд": """
**Что делать:**
- Реализовать отправку UNO commands через iframe.contentWindow.postMessage()
- Обработка ответов от Collabora (Action_Save, errors)
- Интеграция с существующим LLM чатом

**Результат:** LLM команды выполняются в редакторе

**Время:** 3-4 часа
""",

    "🟡 Phase 4B: Включить Track Changes режим для LLM": """
**Что делать:**
- Перед LLM командами отправить: `uno .uno:TrackChanges`
- Установить автора: "AI Co-pilot"
- Все изменения автоматически tracked

**Результат:** LLM изменения видны как tracked changes

**Время:** 2-3 часа
**Ключевая фича:** Пользователь видит ЧТО изменил LLM
""",

    "🟡 Phase 4B: Создать LLMChangesPanel.vue (боковая панель)": """
**Что делать:**
- Vue компонент - боковая панель справа
- Запрос tracked changes: `commandvalues command=.uno:TrackedChanges`
- Отображение списка изменений: тип, текст, позиция
- Кнопки: Accept, Reject для каждого изменения
- Batch buttons: Принять все / Отклонить все

**Результат:** UI для управления LLM изменениями

**Время:** 4-6 часов
""",

    "🟡 Phase 4B: Accept/Reject API для tracked changes": """
**Что делать:**
- Accept button → `uno .uno:AcceptTrackedChange?Index:long=X`
- Reject button → `uno .uno:RejectTrackedChange?Index:long=X`
- Batch: AcceptAllTrackedChanges / RejectAllTrackedChanges
- Обновление списка после операций

**Результат:** Пользователь контролирует изменения

**Время:** 3-4 часа
""",

    "🟡 Phase 4B: Навигация между изменениями (Next/Prev)": """
**Что делать:**
- Кнопки Next/Prev → `uno .uno:NextTrackedChange` / `.uno:PreviousTrackedChange`
- Collabora автоматически скроллит к изменению
- Подсветка активного изменения в панели

**Результат:** Удобная навигация по LLM изменениям

**Время:** 2-3 часа
""",

    "🟢 Phase 5: Manual тест LLM команд + Track Changes": """
**Что делать:**
- Протестировать базовые команды через чат: "добавь параграф", "создай заголовок"
- Проверить Track Changes: зелёный фон для добавлений
- Проверить LLMChangesPanel: Accept/Reject работает
- Протестировать навигацию между изменениями

**Результат:** LLM + Track Changes работает end-to-end

**Время:** 3-4 часа
""",
}

def main():
    print("Получаю список задач...")
    
    # Get Backend tasks
    os.system('cd ~/.openclaw/workspace/skills/ticktick-tasks && ./ticktick tasks 695bfb7263635125f7366b1d > /tmp/backend_tasks.json')
    # Get Frontend tasks
    os.system('cd ~/.openclaw/workspace/skills/ticktick-tasks && ./ticktick tasks 695bfb43ab63d125f7366aa6 > /tmp/frontend_tasks.json')
    
    # Load tasks
    with open('/tmp/backend_tasks.json') as f:
        backend_tasks = json.load(f)
    with open('/tmp/frontend_tasks.json') as f:
        frontend_tasks = json.load(f)
    
    updated = 0
    
    # Update Backend tasks
    for task in backend_tasks:
        title = task.get('title', '')
        if title in BACKEND_TASKS:
            print(f"Обновляю: {title[:50]}...")
            result = update_task(
                task['projectId'],
                task['id'],
                BACKEND_TASKS[title]
            )
            if 'error' not in result:
                updated += 1
                print("  ✓")
            else:
                print(f"  ✗ {result['error']}")
            time.sleep(0.5)  # Rate limit
    
    # Update Frontend tasks
    for task in frontend_tasks:
        title = task.get('title', '')
        if title in FRONTEND_TASKS:
            print(f"Обновляю: {title[:50]}...")
            result = update_task(
                task['projectId'],
                task['id'],
                FRONTEND_TASKS[title]
            )
            if 'error' not in result:
                updated += 1
                print("  ✓")
            else:
                print(f"  ✗ {result['error']}")
            time.sleep(0.5)
    
    print(f"\n✅ Обновлено {updated} задач с описаниями!")

if __name__ == "__main__":
    main()
