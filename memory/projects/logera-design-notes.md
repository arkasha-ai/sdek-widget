# Logera — Заметки по дизайну

## Из видео "Fix a SaaS Design in 2 Hours" (Chapos Joe, Babono Studio)
**Источник:** https://youtu.be/ai2vKc1tj4k
**Дата:** 2026-02-21

### Приёмы для Logera:

**Sidebar:**
- Toggle workspace/personal наверху sidebar (org-space/personal-space)
- Иконки: Phosphor Icons (универсальные), фрейм 24×24, выравнивание по высоте текста
- Collapse button для секций

**Типографика:**
- Только кратные 4 для размеров (4, 8, 12, 16, 20, 24...)
- Минимум text styles
- Consistent spacing = professional look

**Карточки контента:**
- Цветовые метки через opacity (8% от основного цвета)
- Auto layout с consistent padding
- Max-width для контента (не растягивать на весь экран)

**Цвета:**
- Минимум цветов в базе
- Акценты через opacity одного цвета (8%, 20%, 75%)
- Тёмный sidebar + светлый контент

**AI prompt bar:**
- Не отдельный чат, а prompt bar прямо в контенте
- На одной ширине с карточками

**Responsive:**
- Container inside container
- Fill container + constraints
- Всё через auto layout

### Конкретные идеи:
1. Переключатель org/personal сверху sidebar
2. Search bar + теги-фильтры под ним
3. AI prompt bar внутри рабочего пространства (не отдельное окно)
4. Карточки страниц: цветовые метки через opacity
5. Spacing system: кратные 4 (Tailwind p-1=4px, p-2=8px)
6. Chevron toggle с анимацией при раскрытии секций

### Главный принцип:
**"Wireframe first, UI second"** — сначала архитектура (расположение, spacing, hierarchy), потом красота (цвета, тени, анимации).
