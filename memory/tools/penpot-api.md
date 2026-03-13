# Penpot API — Практическое руководство

_Обновлено по результатам анализа Plants-app + Black-&-White-Mobile-Templates. 2026-03-12_

---

## Работа ТОЛЬКО через MCP

**Всегда использовать penpot-mcp инструменты.** Прямые HTTP запросы — только когда MCP недостаточен (создание/изменение объектов).

```bash
# Список файлов проекта
mcporter call penpot-mcp.get_project_files \
  --args '{"project_id":"PROJECT_ID"}' --output json

# Найти объекты по имени или regex
mcporter call penpot-mcp.search_object \
  --args '{"file_id":"FILE_ID","query":"Home"}' --output json

# Дерево объектов с нужными полями
mcporter call penpot-mcp.get_object_tree \
  --args '{"file_id":"FILE_ID","object_id":"OBJ_ID",
           "fields":["name","type","x","y","width","height","fills","r1","strokes","content"],
           "depth":3}' --output json

# Все экраны — поиск по типичным именам
mcporter call penpot-mcp.search_object \
  --args '{"file_id":"FILE_ID","query":"(Home|Login|Profile|Settings|Dashboard|Form|Card)"}' \
  --output json
```

⚠️ `get_file` обрезается на 65KB на больших файлах — не использовать для структуры. Только `search_object` + `get_object_tree`.

---

## Структура проекта в Penpot

Типичная организация файла:
```
File
├── Page: Cover          — обложка / превью
├── Page: Templates/Design — экраны приложения
└── Page: Main components — переиспользуемые компоненты
```

Все экраны расставлены сеткой на canvas. Стандартный шаг: 464px по X (ширина 414 + 50 gap), 786–800px по Y.

---

## Координатная система

**ВСЕ координаты абсолютные (page-level).**

Если экран `Home` стоит на `x=928, y=0`, то его дочерний элемент с внутренним отступом 30px будет иметь `x=958`.

```python
# Правильно:
screen_x = 928
padding = 30
content_x = screen_x + padding  # = 958

# НЕ:
content_x = padding  # = 30 — появится в другом месте страницы!
```

---

## Типовые размеры экранов

| Проект | Размер экрана | Шаг сетки |
|--------|--------------|-----------|
| Plants-app | 390×844 | ~460px по X, ~800px по Y |
| B&W Templates | 414×736 | 464px по X, 787px по Y |
| Стандарт iOS | 390×844 | — |
| Стандарт Android | 360×800 | — |

---

## Паттерны компонентов

### 1. Экран (Screen Frame)

```
Frame "ScreenName" (x, y) 390×844 bg=#FFFFFF или #f7f7f7
├── Group "logo"           (x+30, y+70)   60×11   — SVG пути
├── Group "icon-menu"      (x+360, y+70)  24×11   — 3 горизонтальные линии
├── Text h1                (x+..., y+124) ...×36  fs=24 ff=Inter
├── Frame "Component-N"    ...            — вложенные компоненты
└── Frame "Button..."      ...            — кнопки
```

**Стандартные отступы (B&W Templates):**
- Контент от края: 30px
- Ширина контента: `экран_ширина - 60` (414-60=354)
- Заголовок h1: y_экрана + 124, fs=24
- Лого: x_экрана+30, y_экрана+70
- Меню-иконка: x_экрана+360, y_экрана+70

### 2. Инпут-поле (Form field)

```
Frame "Component-N" (x+30, y+183) 354×59
├── Text "label"    (x+30, y+183) ... fs=11 col=#000000  — лейбл сверху
├── Rect            (x+30, y+202) 354×40 bg=#ececec stroke=#000000 r=6  — пустой
│   или bg=#cacaca stroke=#000000 r=6  — active/selected
│   или bg=#ffffff stroke=#000000 r=6  — outlined/focused
└── Text "value"    (x+45, y+214) ... fs=13 col=#000000  — значение (15px от левого края rect)
```

| Состояние | Фон | Stroke | Описание |
|-----------|-----|--------|---------|
| Empty | `#ececec` | `#000000` | Пустое поле |
| Filled | `#cacaca` | `#000000` | Заполненное |
| Outlined | `#ffffff` | `#000000` | Выделенное |

### 3. Кнопки (4 стандартных вида)

```
# Button filled (primary)
Frame 354×50:
  Rect  354×50  bg=#000000  r=6
  Text  fs=13  ff=Inter  col=#ffffff  — текст по центру

# Button outlined (secondary)  
Frame 177×50:
  Rect  177×50  bg=#ffffff  stroke=#000000 w=1  r=6
  Text  fs=13  ff=Inter  col=#000000

# Button Rounded filled (CTA)
Frame 354×50:
  Rect  354×50  bg=#000000  r=30
  Text  fs=13  ff=Inter  col=#ffffff

# Button Rounded Outlined
Frame 167×50:
  Rect  167×50  bg=#ffffff  stroke=#000000 w=1  r=30
  Text  fs=13  ff=Inter  col=#000000
```

### 4. Toggle (переключатель)

```
# OFF state
Frame 55×32:
  Rect   55×32  bg=#f3f3f3  r=30
  Circle 28×28  bg=#ffffff  — LEFT position (x+2, y+2)

# ON state
Frame 55×32:
  Rect   55×32  bg=#000000  r=30
  Circle 28×28  bg=#ffffff  — RIGHT position (x+25, y+2)
```

### 5. Карточка новости (News card)

```
Frame 354×120:
  Rect             354×120  bg=#ffffff  r=4   — фон карточки
  Text "category"  ...      fs=10  col=#757575  — категория
  Text "title"     201×51   fs=18  col=#000000  — заголовок
  Rect "image"     128×120  fillImage  — фото справа
```

### 6. Info bubble (Plants-app)

```
Frame 98×98:
  Rect  98×98   bg=#ffffff  r=30  — фон
  Rect  37×37   fillImage         — иконка
  Text  73×18   fs=...  col=...   — подпись снизу
```

### 7. Карточка товара (Plants-app Plant-card)

```
Frame 249×431:
  Rect  249×431  bg=#ffffff  r=30   — фон карточки
  Rect  237×259  fillImage          — фото растения
  Text  204×24   fs=16  col=#000000  — название
  Text  204×18   fs=14  col=#666666  — описание
  Text  66×24    fs=16  col=#000000  — цена
  Frame 52×42:                       — кнопка добавить
    Rect  52×42  bg=#000000  r=8
    Text  "+",   col=#ffffff  fs=20
```

---

## Типографика

### B&W Templates (Inter)

| Роль | Font | Size | Weight | Color |
|------|------|------|--------|-------|
| h1 заголовок | Inter | 24 | 400 | #000000 |
| h2 подзаголовок | Inter | 16-18 | 400 | #000000 |
| body | Inter | 13 | 400 | #000000 |
| label | Inter | 11 | 400 | #000000 |
| caption | Inter | 10 | 400 | #757575 |
| кнопки | Inter | 13 | 400 | #ffffff/#000000 |

### Plants-app (Work Sans)

| Роль | Font-id | Size |
|------|---------|------|
| Основной текст | gfont-work-sans | 14-18 |
| Цена | gfont-work-sans | 16 |
| Мелкий | gfont-work-sans | 12 |

---

## Цветовые схемы

### B&W / Минималистичная

| Имя | Hex | Использование |
|-----|-----|--------------|
| White | #ffffff | Фон, карточки, кнопки outlined |
| Off-white | #f7f7f7 | Альтернативный фон страницы |
| Light gray | #ececec | Пустые инпуты |
| Medium gray | #cacaca | Заполненные инпуты |
| Text secondary | #757575 | Категории, лейблы |
| Near-black logo | #424454 | Логотип |
| Black | #000000 | Кнопки, текст, stroke |

### Plants-app / Природная

| Имя | Hex | Использование |
|-----|-----|--------------|
| Page BG | #ebeaef | Фон всех экранов |
| White | #ffffff | Карточки, панели |
| Black | #000000 | CTA кнопки |
| Orange | #ec8049 | Badges, акценты |
| Inactive | #b3b3b3 | Inactive dots |

---

## Именование объектов

```
Экраны: Home, Login, Register, Settings, Profile, Inbox, Cart, Detail, Search, Tags
Компоненты (category/name): 
  NAV / Header-nav
  NAV / Header-title  
  UI / Dots
  UI / Counter
  UI / info-bubble
  UI / Settings-item
  UI / Plant-item-1
  CARDS / Plant-card
  CARDS / Plant-small-card
  BUTTONS / Btn-text
  BUTTONS / Btn-icon
Иконки: icon-menu, icon-home, icon - plus, icon - drag left
Группы путей SVG: svg-path-N, svg-g-N, Layer_N
```

---

## Z-порядок (index)

```python
"~:index", 9999  # поверх всех (ПРАВИЛЬНО для добавления)
"~:index", 0     # под всё (НЕ использовать для текста/иконок)
```

Добавляй в порядке снизу вверх: фон → декор → иконки → текст — каждый с `index=9999`.

---

## Transit JSON — формат API

```python
# Все ключи объекта: "~:key"
# Тип объекта: "~:frame", "~:rect", "~:circle", "~:text", "~:path"
# UUID: "~uXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"
# Массив-мап: ["^ ", "~:key1", val1, "~:key2", val2]

# ИСКЛЮЧЕНИЕ — текстовый content:
# type = "root", "paragraph-set", "paragraph" — обычные строки (НЕ "~:root")
# fontSize, fontFamily, fontWeight — обычные строки
```

### Обязательные поля каждого объекта

```python
{
    "~:id": "~uXXX",
    "~:type": "~:rect",       # или frame, circle, text, path
    "~:name": "Name",
    "~:frame-id": "~uFRAME",  # id родительского frame (или собственный для top-level frame)
    "~:parent-id": "~uPARENT",
    "~:x": 0, "~:y": 0,
    "~:width": 100, "~:height": 50,
    "~:fills": [...],
    "~:selrect": {"~:x":0,"~:y":0,"~:width":100,"~:height":50,"~:x1":0,"~:y1":0,"~:x2":100,"~:y2":50},
    "~:points": [{"~:x":0,"~:y":0},{"~:x":100,"~:y":0},{"~:x":100,"~:y":50},{"~:x":0,"~:y":50}],
    "~:transform": {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0},
    "~:transform-inverse": {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}
}
```

### Стандартные структуры fills

```python
# Сплошной цвет
{"~:fill-color": "#000000", "~:fill-opacity": 1.0}

# Изображение
{"~:fill-image": {"~:id": "UUID", "~:mtype": "image/png", "~:width": W, "~:height": H}}
```

### Stroke

```python
"~:strokes": [{
    "~:stroke-color": "#000000",
    "~:stroke-opacity": 1.0,
    "~:stroke-width": 1,
    "~:stroke-style": "~:solid",       ← ПРАВИЛЬНО (не stroke-type!)
    "~:stroke-alignment": "~:inner"    ← ПРАВИЛЬНО (не stroke-position!)
    // Варианты stroke-style: ~:solid | ~:dashed | ~:dotted | ~:mixed
    // Варианты stroke-alignment: ~:inner | ~:outer | ~:center
}]
```

### Radius

```python
"~:r1": 6, "~:r2": 6, "~:r3": 6, "~:r4": 6  # все углы одинаково
```

### Текст content

```python
"~:content": {
    "~:type": "root",             # plain string (НЕ "~:root")
    "~:children": [{
        "~:type": "paragraph-set",
        "~:children": [{
            "~:type": "paragraph",
            "~:text-align": "center",        # ← ЗДЕСЬ: paragraph level! left|center|right
            "~:paragraph-spacing": 0,        # ← ОБЯЗАТЕЛЬНО: убирает нижний отступ параграфа
            "~:children": [{
                "~:text": "Hello",
                "~:font-size": "16",         # строка
                "~:font-family": "Inter",    # строка
                "~:font-weight": "400",      # строка
                "~:line-height": "1",        # ← ОБЯЗАТЕЛЬНО: точная высота = font-size
                "~:fills": [{"~:fill-color": "#000000", "~:fill-opacity": 1.0}]
            }]
        }]
    }]
}

# ✅ ВЕРТИКАЛЬНОЕ ЦЕНТРИРОВАНИЕ — ПРАВИЛЬНЫЙ ПАТТЕРН (проверено 2026-03-13):
#
# Метод: vertical-align "center" в content root (plain string, НЕ Transit keyword!)
# grow-type: fixed, высота = высота контейнера — формулы НЕ НУЖНЫ
#
# РЕЗУЛЬТАТЫ ТЕСТА (4 значения, scale=3 PNG):
#   "center"  → ✅ идеальная центровка
#   "top"     → текст сверху
#   "bottom"  → текст снизу
#   "middle"  → ОШИБКА, едет вверх (это CSS baseline trick, не то)
#   "~:center"/"~:middle" → validation error (нельзя как Transit keyword)
#
# НЕПРАВИЛЬНО:
#   "~:vertical-align": "~:middle"   — validation error
#   ty = cy + (ch - fs * 1.4) / 2    — работает, но не нужно когда есть vertical-align
```

---

## Добавление объекта (update-file)

```python
import requests, json, uuid

session = requests.Session()
BASE = "https://penpot.jakeberrimor.com/api/rpc/command"
HDRS = {"Content-Type": "application/transit+json"}

session.post(f"{BASE}/login-with-password", headers=HDRS,
    data='["^ ","~:email","spam@jakeberrimor.com","~:password","q25RiI#L"]')

revn = 0  # обновлять из ответа после каждого вызова

def find(arr, key):
    if not isinstance(arr, list): return None
    for i, v in enumerate(arr):
        if v == key and i+1 < len(arr): return arr[i+1]
    return None

def add_obj(obj, frame_id, parent_id, file_id, page_id):
    global revn
    oid = obj["~:id"].replace("~u","")
    payload = ["^ ",
        "~:id", f"~u{file_id}",
        "~:revn", revn,
        "~:vern", 0,
        "~:session-id", f"~u{str(uuid.uuid4())}",
        "~:changes", [["^ ",
            "~:type", "~:add-obj",
            "~:id", f"~u{oid}",
            "~:frame-id", f"~u{frame_id}",
            "~:parent-id", f"~u{parent_id}",
            "~:page-id", f"~u{page_id}",
            "~:index", 9999,
            "~:obj", obj
        ]]
    ]
    r = session.post(f"{BASE}/update-file", headers=HDRS, data=json.dumps(payload))
    revn = find(r.json(), "~:revn") or revn + 1
    return r.status_code
```

---

## Helper функции

```python
T = {"~:a":1,"~:b":0,"~:c":0,"~:d":1,"~:e":0,"~:f":0}

def uid(): return str(uuid.uuid4())

def sr(x, y, w, h):
    return {"~:x":x,"~:y":y,"~:width":w,"~:height":h,
            "~:x1":x,"~:y1":y,"~:x2":x+w,"~:y2":y+h}

def pts(x, y, w, h):
    return [{"~:x":x,"~:y":y},{"~:x":x+w,"~:y":y},
            {"~:x":x+w,"~:y":y+h},{"~:x":x,"~:y":y+h}]

def fill(color, opacity=1.0):
    return {"~:fill-color": color, "~:fill-opacity": opacity}

def mk_frame(fid, name, x, y, w, h, bg=None, parent=None, page_id=None):
    return {"~:id":f"~u{fid}", "~:type":"~:frame", "~:name":name,
            "~:frame-id":f"~u{fid}", "~:parent-id":f"~u{parent or page_id}",
            "~:x":x, "~:y":y, "~:width":w, "~:height":h,
            "~:fills":[fill(bg)] if bg else [],
            "~:selrect":sr(x,y,w,h), "~:points":pts(x,y,w,h),
            "~:transform":T, "~:transform-inverse":T, "~:shapes":[]}

def mk_rect(name, fid, x, y, w, h, color, opacity=1.0, radius=0, stroke=None, stroke_w=1):
    obj = {"~:id":f"~u{uid()}", "~:type":"~:rect", "~:name":name,
           "~:frame-id":f"~u{fid}", "~:parent-id":f"~u{fid}",
           "~:x":x, "~:y":y, "~:width":w, "~:height":h,
           "~:fills":[fill(color, opacity)],
           "~:selrect":sr(x,y,w,h), "~:points":pts(x,y,w,h),
           "~:transform":T, "~:transform-inverse":T}
    if radius:
        obj["~:r1"]=obj["~:r2"]=obj["~:r3"]=obj["~:r4"]=radius
    if stroke:
        obj["~:strokes"]=[{"~:stroke-color":stroke,"~:stroke-opacity":1.0,
                           "~:stroke-width":stroke_w,"~:stroke-style":"~:solid",
                           "~:stroke-alignment":"~:inner"}]
    return obj

def mk_text(name, fid, x, y, w, h, text_str, font_size=16, font_family="Inter",
            font_weight="400", color="#000000"):
    return {"~:id":f"~u{uid()}", "~:type":"~:text", "~:name":name,
            "~:frame-id":f"~u{fid}", "~:parent-id":f"~u{fid}",
            "~:x":x, "~:y":y, "~:width":w, "~:height":h, "~:fills":[],
            "~:selrect":sr(x,y,w,h), "~:points":pts(x,y,w,h),
            "~:transform":T, "~:transform-inverse":T,
            "~:content":{"~:type":"root","~:children":[{"~:type":"paragraph-set","~:children":[{
                "~:type":"paragraph","~:children":[{
                    "~:text":text_str,
                    "~:font-size":str(font_size),
                    "~:font-family":font_family,
                    "~:font-weight":str(font_weight),
                    "~:fills":[fill(color)]
                }]
            }]}]}}
```

---

## API эндпоинты

```python
POST /create-file   {"name", "project-id", "is-shared"}
POST /update-file   {"id", "revn", "vern", "session-id", "changes"}
POST /get-page      {"file-id", "page-id"}
POST /get-file      {"id"}  ← обрезается на 65KB!
POST /delete-file   {"id"}
POST /get-project-files  {"project-id"}
```

## Экспорт объекта в PNG/SVG

```python
# POST /api/export (НЕ /api/rpc/command!)
# Возвращает URI на скачивание

def export_object(s, profile_id, file_id, page_id, obj_id, name, type_="png", scale=1):
    export_item = ["^ ",
        "~:type", f"~:{type_}",      # "~:png" или "~:svg"
        "~:scale", scale,
        "~:suffix", "",
        "~:name", name,
        "~:file-id", f"~u{file_id}",
        "~:page-id", f"~u{page_id}",
        "~:object-id", f"~u{obj_id}"
    ]
    payload = ["^ ",
        "~:cmd", "~:export-shapes",
        "~:profile-id", f"~u{profile_id}",
        "~:file-id", f"~u{file_id}",
        "~:exports", [export_item]
    ]
    r = s.post("https://penpot.jakeberrimor.com/api/export",
        data=json.dumps(payload),
        headers={"Content-Type": "application/transit+json"})
    data = r.json()
    uri_wrapper = data.get("~:uri", {})
    uri = uri_wrapper.get("~#uri") if isinstance(uri_wrapper, dict) else None
    # Download image
    img = s.get(uri)
    with open(f'/tmp/{name}.{type_}', 'wb') as f: f.write(img.content)
    return f'/tmp/{name}.{type_}'

# profile_id — из ответа login-with-password, поле ~:id
```

**Важно:**
- Эндпоинт `/api/export` (не `/api/rpc/command/...`)
- `cmd = export-shapes` (не `export-object`)
- `exports` — это вектор объектов, каждый содержит file-id, page-id, object-id
- Ответ содержит `~:uri` → `{"~#uri": "https://..."}` — нужно скачать отдельным GET запросом

---

## Константы

| Параметр | Значение |
|---|---|
| Penpot URL | https://penpot.jakeberrimor.com |
| Аккаунт | spam@jakeberrimor.com / q25RiI#L |
| Default project-id | 0c5e8ab1-14d8-805c-8007-b3d9d06a56af |
| Team-id | 0c5e8ab1-14d8-805c-8007-b3d9d0675f3c |
| penpot-mcp SSE | https://penpot-mcp.jakeberrimor.com/sse |

**Примеры файлов для изучения:**
| Файл | ID | Что интересно |
|------|----|--------------|
| Plants-app | `4b85babb-b10c-8109-8007-b3ea8d8b6511` | Компоненты, Work Sans, цветная схема |
| B&W Templates | `4b85babb-b10c-8109-8007-b3ebcdcc607a` | Форм-поля, toggles, типографика Inter |

## Workspace URL

```
https://penpot.jakeberrimor.com/#/workspace?team-id=TEAM_ID&file-id=FILE_ID&page-id=PAGE_ID
```

---

## Экспорт объекта как PNG

```python
import requests, json

def export_object_png(session, file_id, page_id, object_id, name="export", scale=2.0):
    """Рендерит объект Penpot в PNG. Возвращает bytes изображения."""
    H = {"Content-Type": "application/transit+json"}
    
    # Получить profile-id из сессии
    r = session.post("https://penpot.jakeberrimor.com/api/rpc/command/get-profile", headers=H, data='["^ "]')
    def find(arr, key):
        for i, v in enumerate(arr):
            if v == key and i+1 < len(arr): return arr[i+1]
    profile_id = find(r.json(), "~:id").replace("~u","")
    
    payload = json.dumps(["^ ",
        "~:cmd", "~:export-shapes",
        "~:profile-id", f"~u{profile_id}",
        "~:wait", True,
        "~:exports", [["^ ",
            "~:page-id", f"~u{page_id}",
            "~:file-id", f"~u{file_id}",
            "~:object-id", f"~u{object_id}",
            "~:type", "~:png",
            "~:scale", scale,
            "~:suffix", "",
            "~:name", name
        ]]
    ])
    r = session.post("https://penpot.jakeberrimor.com/api/export", headers=H, data=payload, timeout=30)
    if r.status_code != 200:
        raise Exception(f"Export failed: {r.text[:200]}")
    
    result = r.json()
    uri_obj = find(result, "~:uri")
    # uri_obj = {"~#uri": "https://penpot.jakeberrimor.com/assets/by-id/..."}
    if isinstance(uri_obj, dict):
        img_url = uri_obj.get("~#uri", "")
    else:
        img_url = str(uri_obj)
    
    img_r = session.get(img_url)
    return img_r.content  # PNG bytes

# Использование:
# png_bytes = export_object_png(session, file_id, page_id, object_id, name="Home", scale=2.0)
# with open('/path/to/save.png', 'wb') as f: f.write(png_bytes)
```

⚠️ Для работы нужен запущенный `penpot-exporter` контейнер (уже в compose).

---

## ПРАВИЛО ГРУППИРОВКИ (обязательно!)

**Любой визуальный «виджет» из 2+ слоёв — ВСЕГДА subframe.**

```
✅ Нужен subframe:          ❌ НЕ нужен:
────────────────────────    ──────────────────────
bg rect + текст             одиночный текст (заголовок, параграф)
bg rect + иконка + текст    одиночный divider rect
circle + текст              одиночная иллюстрация
badge (bg + label)
pill (bg + label)
card (bg + несколько текстов + badge)
button (bg + label/icon)
avatar (circle + initials)
nav bar (bg + все слоты)
toolbar (bg + все кнопки)
app bar (bg + title + avatar)
nav slot (pill bg + label)
fab (circle + icon)
search bar (bg + icon + hint)
```

**Иерархия группировки:**
- screen → app bar → [title, avatar]
- screen → nav bar → [nav slot 1, nav slot 2, ...]
- screen → toolbar → [btn 1, btn 2, ...]
- screen → card → [badge, title text, preview text, date text]
- screen → fab → [circle, icon text]

---

## Вертикальное центрирование — итоговый паттерн (2026-03-13)

```python
# ПРАВИЛЬНЫЕ helper-функции (проверено):

def T(name, sid, par, x, y, w, h, t, fs=14, fw="400", col="#111827", align="left", opacity=1.0):
    """Текстовый объект. y — верхний край текста."""
    o = {"~:id": f"~u{uid()}", "~:type": "~:text", "~:name": name,
         "~:frame-id": f"~u{sid}", "~:parent-id": f"~u{par}",
         "~:x": x, "~:y": y, "~:width": w, "~:height": fs,
         "~:fills": [], "~:selrect": sr(x,y,w,fs), "~:points": pts(x,y,w,fs),
         "~:transform": TF, "~:transform-inverse": TF,
         "~:content": {"~:type": "root", "~:vertical-align": "~:top", "~:children": [
             {"~:type": "paragraph-set", "~:children": [
                 {"~:type": "paragraph", "~:text-align": align, "~:paragraph-spacing": 0,
                  "~:children": [{"~:text": t, "~:font-size": str(fs), "~:font-family": "Inter",
                                   "~:font-weight": str(fw), "~:line-height": "1.4",
                                   "~:fills": [fill(col, opacity)]}]}]}]}}
    _add(o, sid, par)

def TC(name, sid, par, x, cy, w, ch, t, fs=14, fw="400", col="#111827", align="center", opacity=1.0):
    """Вертикально центрированный текст. cy — верхний край контейнера, ch — высота контейнера."""
    ty = cy + (ch - fs * 1.4) / 2   # ← ПРАВИЛЬНАЯ ФОРМУЛА
    T(name, sid, par, x, ty, w, fs, t, fs, fw, col, align, opacity)
```

**Ключевые правила:**
- `line-height: "1.4"` — стандарт Inter, именно так работает Penpot внутри
- `paragraph-spacing: 0` — убрать нежелательный отступ параграфа
- `vertical-align: "~:top"` в content root — дефолт, НЕ менять на `"~:middle"`  
- Формула: `ty = cy + (ch - fs * 1.4) / 2`
- height текстового объекта = `fs` (Penpot хранит tight height)

---

## ✅ ФИНАЛЬНЫЙ ПАТТЕРН: вертикальное центрирование (2026-03-13, v2)

```python
# TC — текст вертикально центрированный в контейнере
# x, cy = левый верхний угол контейнера; w, ch = ширина/высота контейнера

def TC(name, sid, par, x, cy, w, ch, t, fs=14, fw="400", col="#111827", align="center", opacity=1.0):
    """Вертикально центрированный текст. Никакой формулы — vertical-align делает сам."""
    o = {"~:id": f"~u{uid()}", "~:type": "~:text", "~:name": name,
         "~:frame-id": f"~u{sid}", "~:parent-id": f"~u{par}",
         "~:x": x, "~:y": cy,       # ← y = container_y (не смещать!)
         "~:width": w, "~:height": ch,  # ← height = container_height
         "~:fills": [], "~:grow-type": "~:fixed",  # ← FIXED, не auto-height
         "~:selrect": sr(x,cy,w,ch), "~:points": pts(x,cy,w,ch),
         "~:transform": TF, "~:transform-inverse": TF,
         "~:content": {
             "~:type": "root",
             "~:vertical-align": "center",   # ← PLAIN STRING "center" (не "~:center"!)
             "~:children": [{"~:type": "paragraph-set", "~:children": [
                 {"~:type": "paragraph", "~:text-align": align, "~:paragraph-spacing": 0,
                  "~:children": [{"~:text": t, "~:font-size": str(fs), "~:font-family": "Inter",
                                   "~:font-weight": str(fw), "~:line-height": "1.4",
                                   "~:fills": [fill(col, opacity)]}]}]}]}}
    _add(o, sid, par)

# ⚠️ ВАЖНО:
# "center"  → идеальная центровка ✅
# "middle"  → НЕВЕРНО (baseline trick, текст едет вверх) ✗
# "~:center" или "~:middle" → validation error ✗

---

## Lucide иконки через API (2026-03-13)

**Скрипт:** `scripts/lucide_penpot.py`

```python
from scripts.lucide_penpot import penpot_icon

# Разместить иконку в Penpot
penpot_icon("search", px=100, py=200, ps=24, color="#4F46E5",
            frame_id=artboard_id, parent_id=artboard_id, add_fn=add)
```

**Формат path сегментов (найден экспериментально):**
```python
{"~:command": "~:move-to",  "~:params": {"~:x": x, "~:y": y}}
{"~:command": "~:line-to",  "~:params": {"~:x": x, "~:y": y}}
{"~:command": "~:curve-to", "~:params": {"~:c1x":x1,"~:c1y":y1,"~:c2x":x2,"~:c2y":y2,"~:x":x,"~:y":y}}
{"~:command": "~:close-path"}
```

**Stroke поля (schema closed — лишние ключи = ERR):**
```python
{"~:stroke-color": "#000", "~:stroke-opacity": 1.0,
 "~:stroke-width": 2, "~:stroke-style": "~:solid",
 "~:stroke-alignment": "~:center",
 "~:stroke-cap-start": "~:round", "~:stroke-cap-end": "~:round"}
# ⚠️ stroke-line-join НЕ поддерживается!
```

**Координаты:** абсолютные canvas-level, без transform матрицы.
Scale: умножить src coords на (ps/24) и добавить (px, py).

**Доступные иконки:** house, search, plus, arrow-left, bookmark, ellipsis, 
tag, settings, more-vertical, bold, italic, list, hash, star, type, check, 
x, chevron-down, clock, calendar
