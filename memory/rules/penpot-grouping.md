# Правила группировки в UI дизайне (Penpot/Figma)

> Источники: Figma Best Practices (groups-vs-frames, component-architecture), опыт ошибок в Nota App

---

## Главный тест

> **"Это один компонент?"** → Если разработчик написал бы это одним React-компонентом или одним HTML-элементом — это ОДИН объект в дизайне.

---

## Атомарная иерархия (Atomic Design)

```
ATOMS      — одиночный элемент: текст, rect, иконка, divider
MOLECULES  — 2+ атома с единым смыслом: кнопка, бейдж, инпут, аватар
ORGANISMS  — группа молекул: карточка, nav bar, toolbar, header
SCREENS    — полный экран / артборд
```

---

## Правило 1: Фон + контент = всегда группа

Любой элемент, у которого есть **подложка (bg rect/circle) + что-то сверху** — обязательный subframe.

```
bg rect + текст              → Button, Badge, Pill, Tag, Chip
bg circle + текст            → Avatar, FAB, Icon Button  
bg rect + иконка + текст     → Search Bar, Input Field, List Item
bg rect + несколько текстов  → Card, Tooltip, Dropdown Item
```

---

## Правило 2: Интерактивный элемент = всегда группа

Всё что **можно нажать** — один subframe, независимо от количества слоёв.

```
✅ Кнопка (даже если текст без bg)
✅ Tab в nav bar
✅ Card (по ней кликают целиком)
✅ Chip / Pill / Badge
✅ FAB
✅ Toggle, Checkbox, Radio
✅ Nav item (icon + label)
```

---

## Правило 3: Секция экрана = группа

Логические зоны экрана — в subframe. Это помогает при редактировании и отражает структуру кода.

```
✅ App Bar / Header      (title + avatar + back btn)
✅ Nav Bar               (bg + все tab items)
✅ Toolbar               (bg + все кнопки форматирования)
✅ Search Section        (поиск + категории)
✅ Content Area          (основной контент)
✅ Modal / Dialog        (overlay + контент)
✅ Bottom Sheet          
```

---

## Правило 4: Что НЕ нужно группировать

```
❌ Одиночный текст (заголовок, параграф, метка секции)
   → "Notes", "CATEGORIES", "Key points" — OK без группы

❌ Одиночный divider / разделитель
   → тонкая линия между секциями — OK без группы

❌ Одиночная декоративная фигура
   → фоновый rect самого экрана — он и есть frame

❌ Тело текста (body copy)
   → отдельные строки контента в editor — OK без групп
```

---

## Иерархия именования

```
Компонент / Вариант
└── Section / Element

Примеры:
  "Nav Bar"
    └── "Nav / Notes"    (активный)
    └── "Nav / Search"   (неактивный)
  
  "Card / Meeting Notes"
    └── "Badge / Work"
    └── "Card Title"
    └── "Card Preview"
    └── "Card Date"
  
  "App Bar"
    └── "App Title"
    └── "Avatar"
        └── "Avatar Circle"
        └── "Avatar Initial"
  
  "Toolbar"
    └── "TB / Bold"
    └── "TB / Italic"
    └── "TB / List"
```

---

## Полный чеклист перед сборкой экрана

Перед написанием кода — пройтись по списку:

- [ ] Каждая кнопка (любого вида) — в subframe?
- [ ] Каждый badge / tag / chip — в subframe?
- [ ] Каждая карточка (card) — в subframe?
- [ ] Avatar / Profile pic — в subframe?
- [ ] FAB — в subframe?
- [ ] Search bar (input) — в subframe?
- [ ] Nav bar — в subframe, и каждый tab внутри тоже в subframe?
- [ ] Toolbar — в subframe, и каждая кнопка внутри тоже?
- [ ] App bar / Header — в subframe?
- [ ] Modal / Bottom sheet — в subframe?

---

## Глубина вложенности

```
Screen (artboard)
├── Section Frame          ← логическая зона
│   ├── Component Frame    ← визуальный компонент
│   │   ├── Sub-component  ← если есть (badge внутри card)
│   │   │   ├── bg rect
│   │   │   └── text
│   │   ├── text
│   │   └── text
│   └── Component Frame
└── Standalone Text        ← ТОЛЬКО если одиночный
```

**Максимальная разумная глубина: 4 уровня.**  
Глубже — сигнал что компонент слишком сложный.

---

## Частые ошибки (из опыта)

| Ошибка | Правильно |
|--------|-----------|
| bg rect + text как отдельные объекты | Обернуть в subframe |
| Nav bar bg + nav items порознь | Nav Bar frame содержит bg + items |
| Toolbar bg + кнопки порознь | Toolbar frame содержит bg + кнопки |
| Avatar circle + initial порознь | Avatar frame содержит оба слоя |
| FAB circle + icon порознь | FAB frame содержит оба |
| Badge bg + text порознь | Badge frame содержит оба |

---

## Правило для Penpot API

В коде каждый "виджет" оборачивать через `mkframe()` ПЕРЕД добавлением дочерних элементов:

```python
# ✅ Правильно: кнопка как subframe
btn_fid = uid()
mkframe(btn_fid, "Btn Primary", x, y, w, h, screen_id, parent_id, bg=IND, r_=8)
TC("Btn Label", screen_id, btn_fid, x, y, w, h, "Save", 14, "600", WH)

# ❌ Неправильно: bg и текст как отдельные объекты
R("Btn bg",  screen_id, parent_id, x, y, w, h, IND, r_=8)
TC("Btn tx", screen_id, parent_id, x, y, w, h, "Save", ...)
```

---

_Создано: 2026-03-13 на основе Figma Best Practices + опыт Nota App v1-v11_
