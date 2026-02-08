# План миграции Logera: ONLYOFFICE → Collabora Online

**Дата создания:** 2026-02-06  
**Цель:** Заменить ONLYOFFICE на Collabora Online для on-premise развертываний Logera

---

## 📊 Текущая архитектура ONLYOFFICE

### Backend интеграция (`back-end/api/routers/onlyoffice.py`)

**Ключевые эндпоинты:**
1. `GET /onlyoffice/config/{file_id}` - Получение конфига для редактора
2. `POST /onlyoffice/callback` - Callback при сохранении документа
3. `GET /onlyoffice/file/{file_id}` - Отдача файла ONLYOFFICE (с media token)
4. Conversion API - Конвертация документов в text/html для LLM

**Текущий flow:**
```
1. User открывает документ → GET /onlyoffice/config/{file_id}
2. Backend генерирует JWT token + document config
3. Frontend открывает ONLYOFFICE редактор (DocsAPI.DocEditor)
4. User редактирует → ONLYOFFICE отправляет POST /onlyoffice/callback
5. Backend скачивает обновленный файл и сохраняет в storage
```

**JWT Authentication:**
- `ONLYOFFICE_JWT_SECRET` - секрет для подписи
- Токены для: config, callback, file access
- Media tokens (8 часов) для доступа ONLYOFFICE к файлам без user auth

**Кастомизация UI:**
```python
"customization": {
    "autosave": True,
    "forcesave": True,
    "comments": True,
    "compactHeader": True,
    "compactToolbar": False,
    "feedback": False,  # Убрана обратная связь
    "help": False,      # Убрана помощь
}
```

---

### LLM интеграция (`back-end/services/chat/document_editor.py`)

**Как работает:**
1. LLM в чате генерирует команды редактирования (действие + параметры)
2. Python функция `generate_office_js_code(action, params)` генерирует Office JS API код
3. JS код отправляется в редактор через **OnlyOffice Connector API**
4. Редактор применяет изменения в реальном времени

**Поддерживаемые действия:**
- `insert_text` - вставка текста
- `insert_paragraph` - параграф с стилями
- `insert_heading` - заголовки (1-6 уровней)
- `insert_table` - таблицы с данными
- `insert_list` - маркированные/нумерованные списки
- `insert_chart` - диаграммы (bar, line, pie)
- `format_selection` - форматирование выделенного текста
- `replace_text` - поиск и замена
- `delete_section` - удаление секций по заголовку
- `delete_paragraph` - удаление параграфов

**Чтение документов для LLM:**
- `convert_document_to_text()` - через ONLYOFFICE Conversion API (/ConvertService.ashx)
- `convert_document_to_html()` - с сохранением форматирования
- `generate_read_document_structure_code()` - чтение структуры (параграфы, таблицы, стили)

**Пример генерации JS кода:**
```python
action = "insert_heading"
params = {"text": "Новый раздел", "level": 2, "after_text": "Введение"}

js_code = generate_office_js_code(action, params)
# Возвращает:
# (function() {
#     var oDocument = Api.GetDocument();
#     var oParagraph = Api.CreateParagraph();
#     oParagraph.AddText("Новый раздел");
#     var oStyle = oDocument.GetStyle("Heading 2");
#     oParagraph.SetStyle(oStyle);
#     oDocument.AddElement(insertIndex, oParagraph);
# })();
```

---

### Docker конфиг (`docker-compose.yml`)

```yaml
onlyoffice:
  image: onlyoffice/documentserver:8.2
  container_name: logera-onlyoffice
  ports:
    - "8443:443"
  environment:
    - JWT_ENABLED=true
    - JWT_SECRET=${ONLYOFFICE_JWT_SECRET:-logera-onlyoffice-secret}
    - JWT_HEADER=Authorization
    - JWT_IN_BODY=false
  volumes:
    - onlyoffice_data:/var/www/onlyoffice/Data
    - onlyoffice_logs:/var/log/onlyoffice
  networks:
    - logera-network
  restart: unless-stopped
```

---

## 🎯 План миграции на Collabora Online

### Phase 1: Backend API адаптация (2-3 дня)

**1.1. Переименование эндпоинтов (опционально)**
- `/api/onlyoffice/*` → `/api/editor/*` (универсальное название)
- Или оставить как есть, просто заменить внутреннюю реализацию

**1.2. Изменение формата конфига**

**ONLYOFFICE config:**
```python
config_payload = {
    "document": {
        "fileType": "docx",
        "key": doc_key,
        "title": node.name,
        "url": document_url,
        "permissions": {...}
    },
    "documentType": "word",
    "editorConfig": {
        "callbackUrl": callback_url,
        "lang": "ru",
        "mode": "edit",
        "user": {...},
        "customization": {...}
    },
    "token": jwt_token
}
```

**Collabora config (WOPI discovery):**
```python
# Collabora использует WOPI protocol
# Нужно реализовать WOPI endpoints

config_payload = {
    "wopi_src": f"{INTERNAL_BACKEND_URL}/wopi/files/{file_id}",
    "access_token": wopi_token,
    "access_token_ttl": token_ttl_ms,
}

# Collabora editor URL:
editor_url = f"{COLLABORA_URL}/loleaflet/dist/loleaflet.html?WOPISrc={wopi_src}&access_token={wopi_token}"
```

**1.3. Реализация WOPI endpoints**

WOPI (Web Application Open Platform Interface Protocol) - стандарт для интеграции Office редакторов.

**Требуемые эндпоинты:**

```python
# GET /wopi/files/{file_id}
# Возвращает метаданные файла
{
    "BaseFileName": "document.docx",
    "OwnerId": "user_123",
    "Size": 12345,
    "UserId": "user_123",
    "UserFriendlyName": "Denis Parmeev",
    "Version": "v1",
    "SupportsUpdate": true,
    "SupportsLocks": true,
    "UserCanWrite": true,
    "ReadOnly": false,
}

# GET /wopi/files/{file_id}/contents
# Возвращает бинарный контент файла
# Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document

# POST /wopi/files/{file_id}/contents
# Сохранение обновленного файла (вместо callback)
# Body: binary file content
# Headers: X-WOPI-Lock (если используется locking)

# POST /wopi/files/{file_id}
# Lock/Unlock/RefreshLock/UnlockAndRelock operations
# Для синхронизации при одновременном редактировании
```

**1.4. JWT → WOPI Access Token**
- Collabora использует WOPI access tokens вместо JWT config tokens
- Access token передается в query string: `?access_token=...`
- Нужно генерировать и проверять эти токены

**1.5. Conversion API**

**ONLYOFFICE:**
```python
POST /ConvertService.ashx
{
    "filetype": "docx",
    "outputtype": "txt",
    "url": document_url,
    "token": jwt_token
}
```

**Collabora:**
```python
# Используется тот же WOPI endpoints
# Конвертация происходит через:
POST /lool/convert-to/{format}
# С WOPI access token

# Альтернатива: использовать LibreOffice CLI напрямую:
# docker exec collabora libreoffice --headless --convert-to txt document.docx
```

---

### Phase 2: Office JS API → Collabora JS API (3-5 дней)

**Проблема:**  
ONLYOFFICE использует свой Office JS API (`Api.GetDocument()`, `Api.CreateParagraph()`)  
Collabora основан на LibreOffice и использует **другой API** (UNO API через WebSocket)

**Решение:**

**Вариант A: Переписать генераторы JS кода (рекомендуется)**

Collabora поддерживает управление через **UNO commands** и **JavaScript API** (ограниченный).

**Базовые команды Collabora:**
```javascript
// Insert text
window.app.socket.sendMessage('textinput input=' + JSON.stringify(text));

// Insert paragraph
window.app.socket.sendMessage('uno .uno:InsertPara');

// Format text (bold)
window.app.socket.sendMessage('uno .uno:Bold');

// Insert table
window.app.socket.sendMessage('uno .uno:InsertTable?Columns:long=3&Rows:long=5');

// Search and replace
window.app.socket.sendMessage('uno .uno:SearchDialog');
```

**Нужно переписать функции в `document_editor.py`:**

```python
def _gen_insert_text_collabora(params: dict[str, Any]) -> str:
    """Insert text via Collabora API."""
    text = params.get("text", "")
    text_escaped = json.dumps(text)
    
    return f"""
window.app.socket.sendMessage('textinput input={text_escaped}');
"""

def _gen_insert_heading_collabora(params: dict[str, Any]) -> str:
    """Insert heading via UNO command."""
    text = params.get("text", "")
    level = params.get("level", 1)
    
    # Apply heading style via UNO
    return f"""
window.app.socket.sendMessage('textinput input={json.dumps(text)}');
window.app.socket.sendMessage('uno .uno:StyleApply?Style:string=Heading {level}');
"""

# И так далее для всех действий
```

**Вариант B: Использовать LibreOffice UNO API напрямую (сложнее, мощнее)**

Collabora предоставляет полный UNO API через WebSocket. Можно отправлять UNO commands напрямую.

**Пример:**
```python
def _gen_insert_table_collabora_uno(params: dict[str, Any]) -> str:
    rows = params.get("rows", 3)
    cols = params.get("cols", 3)
    
    # UNO command для вставки таблицы
    uno_cmd = {
        "command": ".uno:InsertTable",
        "arguments": {
            "Columns": {"type": "long", "value": cols},
            "Rows": {"type": "long", "value": rows}
        }
    }
    
    return f"""
window.app.socket.sendMessage('uno {json.dumps(uno_cmd)}');
"""
```

**Матрица совместимости команд:**

| Действие | ONLYOFFICE API | Collabora API | Сложность |
|----------|----------------|---------------|-----------|
| insert_text | `oParagraph.AddText()` | `textinput input=` | ✅ Легко |
| insert_paragraph | `Api.CreateParagraph()` | `.uno:InsertPara` | ✅ Легко |
| insert_heading | `SetStyle("Heading 1")` | `.uno:StyleApply` | ✅ Легко |
| insert_table | `Api.CreateTable()` | `.uno:InsertTable` | ⚠️ Средне |
| insert_list | `CreateNumbering()` | `.uno:DefaultBullet` | ⚠️ Средне |
| insert_chart | `Api.CreateChart()` | `.uno:InsertObjectChart` | ⚠️ Сложно |
| format_selection | `SetBold/Italic()` | `.uno:Bold`, `.uno:Italic` | ✅ Легко |
| replace_text | `SearchAndReplace()` | `.uno:SearchDialog` | ⚠️ Средне |
| delete_section | Custom JS | UNO macro | ⚠️ Сложно |

**⚠️ Потенциальные проблемы:**
1. **Сложные операции (delete_section, insert_chart)** — могут потребовать UNO макросов
2. **Real-time feedback** — ONLYOFFICE API синхронный, Collabora WebSocket асинхронный
3. **Debugging** — сложнее отлаживать UNO commands

**Рекомендация:**
- Начать с базовых операций (insert_text, insert_paragraph, format)
- Сложные (charts, delete_section) — оставить на Phase 3 или использовать альтернативные подходы

---

### Phase 3: Docker конфиг и кастомизация UI (1-2 дня)

**3.1. Docker Compose**

Заменить ONLYOFFICE контейнер на Collabora:

```yaml
collabora:
  image: collabora/code:latest
  container_name: logera-collabora
  ports:
    - "9980:9980"
  environment:
    - domain=logera\\.space  # Regex: домены которым разрешен доступ
    - username=admin
    - password=${COLLABORA_ADMIN_PASSWORD}
    - extra_params=--o:ssl.enable=false --o:ssl.termination=true
    # Кастомизация UI
    - extra_params=--o:welcome.enable=false
    - extra_params=--o:user_interface.mode=compact
    # Брендинг
    - DONT_GEN_SSL_CERT=true
  volumes:
    - collabora_data:/var/lib/loolwsd
    - ./collabora/branding:/etc/loolwsd/branding:ro  # Кастомные файлы брендинга
  networks:
    - logera-network
  restart: unless-stopped
  cap_add:
    - MKNOD
```

**3.2. Брендинг (Logo + Colors)**

Создать `./collabora/branding/` директорию с файлами:

```bash
collabora/branding/
├── logo.svg          # Логотип Logera (заменяет LibreOffice logo)
├── favicon.ico       # Favicon
├── custom.css        # Кастомные стили
└── custom.js         # Кастомный JS (опционально)
```

**custom.css:**
```css
/* Кастомизация Collabora UI для Logera */

/* Header цвета Logera */
.cool-header {
    background-color: #2563eb !important; /* Logera blue */
}

/* Скрыть LibreOffice брендинг */
.cool-header .logo {
    display: none !important;
}

/* Добавить Logera логотип */
.cool-header::before {
    content: "";
    display: inline-block;
    width: 120px;
    height: 40px;
    background-image: url('/branding/logo.svg');
    background-size: contain;
    background-repeat: no-repeat;
}

/* Скрыть ненужные кнопки */
#toolbar-up .w2ui-button[title="Help"] {
    display: none !important;
}

#toolbar-up .w2ui-button[title="About"] {
    display: none !important;
}

/* Compact toolbar */
#toolbar-up {
    height: 42px !important;
}

/* Акцентные цвета */
.w2ui-button.checked {
    background-color: #2563eb !important;
}

/* Кастомные цвета для выделения */
.cool-annotation {
    border-color: #2563eb !important;
}
```

**3.3. Конфиг WOPI в coolwsd.xml**

Монтировать кастомный конфиг:

```xml
<!-- /etc/loolwsd/loolwsd.xml -->
<config>
  <welcome>
    <enable>false</enable>
  </welcome>
  
  <user_interface>
    <mode>compact</mode>
  </user_interface>
  
  <branding>
    <logo>/branding/logo.svg</logo>
    <background_color>#ffffff</background_color>
  </branding>
  
  <wopi>
    <max_file_size>104857600</max_file_size> <!-- 100MB -->
  </wopi>
  
  <storage>
    <wopi>
      <host allow="true">web:8000</host> <!-- Internal backend -->
    </wopi>
  </storage>
</config>
```

---

### Phase 4: Frontend интеграция (1 день)

**Текущий ONLYOFFICE:**
```javascript
// Загружаем DocsAPI
const script = document.createElement('script');
script.src = '/onlyoffice/web-apps/apps/api/documents/api.js';

// Инициализируем редактор
new DocsAPI.DocEditor("editor", {
    document: config.document,
    documentType: config.documentType,
    editorConfig: config.editorConfig,
    token: config.token
});
```

**Collabora (iframe):**
```html
<!-- Простая интеграция через iframe -->
<iframe 
  :src="collaboraUrl" 
  width="100%" 
  height="100%"
  frameborder="0"
>
</iframe>

<script>
// collaboraUrl формируется на backend:
// https://collabora.example.com/loleaflet/dist/loleaflet.html?WOPISrc=...&access_token=...
</script>
```

**Для LLM команд:**
```javascript
// ONLYOFFICE: connector.callCommand()
// Collabora: PostMessage API

const iframe = document.querySelector('#collabora-editor');

// Отправить UNO command
iframe.contentWindow.postMessage({
    MessageId: 'Host_PostmessageReady',
    SendTime: Date.now(),
    Values: {
        Command: 'uno .uno:Bold'
    }
}, '*');

// Получить ответ
window.addEventListener('message', (event) => {
    if (event.data.MessageId === 'Action_Save') {
        // Document saved
    }
});
```

---

### Phase 5: Тестирование (2-3 дня)

**5.1. Unit тесты**
- Генерация Collabora JS API кода
- WOPI endpoints (CheckFileInfo, GetFile, PutFile)
- Access token generation/validation

**5.2. Integration тесты**
- Открытие документа в редакторе
- Сохранение изменений через WOPI
- LLM команды редактирования (базовые операции)
- Конвертация для чтения LLM

**5.3. Manual тесты**
- Открытие разных типов файлов (docx, xlsx, pptx)
- Real-time collaboration (2+ пользователя)
- Форматирование документов
- Вставка таблиц, списков
- LLM редактирование через чат

**5.4. Performance тесты**
- Большие документы (50+ страниц)
- Большие таблицы (1000+ строк)
- Одновременные пользователи (10+)

**5.5. Compatibility тесты**
- Конвертация ONLYOFFICE → Collabora
- Проверка сохранения форматирования
- Excel формулы
- Сложные таблицы Word

---

## 📝 Что нужно переписать: Итоговый чеклист

### Backend (`back-end/api/routers/onlyoffice.py`)

- [x] **Реализовать WOPI endpoints** (~200 строк кода)
  - `GET /wopi/files/{file_id}` - CheckFileInfo
  - `GET /wopi/files/{file_id}/contents` - GetFile
  - `POST /wopi/files/{file_id}/contents` - PutFile (save)
  - `POST /wopi/files/{file_id}` - Lock/Unlock operations

- [x] **Изменить `get_editor_config()`** (~50 строк)
  - Генерировать WOPI URL вместо ONLYOFFICE config
  - Генерировать WOPI access token вместо JWT config token

- [x] **Заменить Conversion API** (~100 строк)
  - `convert_document_to_text()` - через Collabora REST API или LibreOffice CLI
  - `convert_document_to_html()` - аналогично

- [x] **Удалить callback endpoint** (не нужен в WOPI, используется PutFile)

### LLM Integration (`back-end/services/chat/document_editor.py`)

- [x] **Переписать генераторы JS кода** (~500-1000 строк)
  - `_gen_insert_text()` → Collabora WebSocket API
  - `_gen_insert_paragraph()` → UNO commands
  - `_gen_insert_heading()` → UNO StyleApply
  - `_gen_insert_table()` → UNO InsertTable
  - `_gen_insert_list()` → UNO DefaultBullet/DefaultNumbering
  - `_gen_format_selection()` → UNO Bold/Italic/etc
  - `_gen_replace_text()` → UNO SearchDialog
  
  **Сложные (опционально):**
  - `_gen_insert_chart()` → Может потребовать UNO макрос
  - `_gen_delete_section()` → Альтернативный подход через replace

- [x] **Обновить `generate_read_document_structure_code()`** (~200 строк)
  - Заменить Office JS API на UNO API для чтения структуры

### Frontend (если есть Vue компонент)

- [x] **Заменить DocsAPI.DocEditor на iframe** (~50 строк)
- [x] **Реализовать PostMessage API для LLM команд** (~100 строк)
- [x] **Обработка событий от Collabora** (save, error, etc.) (~50 строк)

### Docker & Config

- [x] **Заменить контейнер в `docker-compose.yml`** (~20 строк)
- [x] **Создать брanding файлы** (logo.svg, custom.css) (~100 строк CSS)
- [x] **Настроить coolwsd.xml** (конфиг Collabora) (~50 строк XML)

### Environment Variables

- [x] **Добавить новые ENV vars:**
  ```bash
  COLLABORA_URL=https://collabora.example.com
  COLLABORA_INTERNAL_URL=http://collabora:9980
  WOPI_SECRET=your-wopi-secret-key
  ```

- [x] **Удалить старые:**
  ```bash
  ONLYOFFICE_URL
  ONLYOFFICE_INTERNAL_URL
  ONLYOFFICE_JWT_SECRET
  ```

---

## ⚠️ Риски и ограничения

### Высокий риск

1. **Сложные LLM команды могут не работать**
   - delete_section, insert_chart - требуют глубокой интеграции
   - **Mitigation:** Реализовать базовые операции сначала, сложные - позже

2. **Производительность на больших документах**
   - Collabora медленнее ONLYOFFICE на файлах >50 страниц
   - **Mitigation:** Оптимизация, предупреждение пользователей

3. **Потеря форматирования при миграции существующих документов**
   - ~5-10% edge cases могут сломаться
   - **Mitigation:** Тщательное тестирование, fallback на ONLYOFFICE для критичных файлов

### Средний риск

4. **Debugging сложнее**
   - UNO API менее документирован чем ONLYOFFICE Office JS API
   - **Mitigation:** Создать библиотеку примеров, активное тестирование

5. **Real-time collaboration глюки**
   - WOPI locking может конфликтовать с одновременным редактированием
   - **Mitigation:** Тщательное тестирование race conditions

### Низкий риск

6. **Кастомизация UI может быть неполной**
   - Некоторые элементы сложно переопределить через CSS
   - **Mitigation:** Headless режим с собственным UI (Phase 6)

---

## 🕒 Оценка времени

| Phase | Задача | Время | Приоритет |
|-------|--------|-------|-----------|
| 1 | Backend WOPI API | 2-3 дня | 🔴 Критично |
| 2 | LLM JS генераторы (базовые) | 2 дня | 🔴 Критично |
| 2 | LLM JS генераторы (сложные) | 2-3 дня | 🟡 Средний |
| 3 | Docker + UI брендинг | 1 день | 🔴 Критично |
| 4 | Frontend интеграция | 1 день | 🔴 Критично |
| 5 | Тестирование | 2-3 дня | 🔴 Критично |
| **Итого (MVP)** | | **8-10 дней** | |
| **Итого (Full)** | | **10-13 дней** | |

**MVP (минимально работающий продукт):**
- Открытие/сохранение документов
- Базовые LLM команды (insert_text, insert_paragraph, format)
- Базовый брендинг

**Full (полный функционал):**
- Все LLM команды (включая таблицы, списки, графики)
- Полная кастомизация UI
- Production-ready тестирование

---

## 📌 Рекомендации

### Для начала (Quick Start)

1. **Phase 1 (WOPI API)** - критичная база, без этого ничего не работает
2. **Phase 3 (Docker)** - быстро поднять Collabora для тестов
3. **Phase 2 (базовые LLM команды)** - insert_text, insert_paragraph, format
4. **Phase 4 (Frontend)** - простой iframe для тестов

**Результат:** Работающий редактор за 5-6 дней, LLM с базовыми командами.

### Для Production

1. Полный Phase 2 (все LLM команды)
2. Phase 5 (тщательное тестирование)
3. Performance tuning
4. Мониторинг и логирование

---

## 🔗 Полезные ссылки

**Collabora Documentation:**
- https://sdk.collaboraonline.com/docs/index.html
- https://sdk.collaboraonline.com/docs/How_to_integrate.html (WOPI)
- https://github.com/CollaboraOnline/online (source code)

**WOPI Protocol:**
- https://learn.microsoft.com/en-us/microsoft-365/cloud-storage-partner-program/rest/

**UNO API:**
- https://api.libreoffice.org/
- https://wiki.documentfoundation.org/Development/Uno

**PostMessage API:**
- https://sdk.collaboraonline.com/docs/postmessage_api.html

---

## ✅ Следующие шаги

1. ✅ Создать этот план
2. ⏳ Создать TickTick задачи для каждого Phase
3. ⏳ Поднять Collabora в test environment (docker-compose.dev.yml)
4. ⏳ Реализовать WOPI endpoints (Phase 1)
5. ⏳ Протестировать открытие документа
6. ⏳ Переписать базовые LLM генераторы
7. ⏳ Full testing

**Обновлено:** 2026-02-06
