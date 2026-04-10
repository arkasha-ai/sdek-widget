# SdekPvzWidget — Виджет выбора ПВЗ СДЭК

## Структура проекта

```
sdek-widget/
├── package.json              — зависимости (ol, vue, vue3-openlayers, vite)
├── vite.config.js            — билд: UMD + ES модули, external dependencies
├── index.html                — demo-страница (запуск через `npm run dev`)
├── README.md                 — этот файл
├── sdek-backend.php          — бэкенд (geocode, pvzlist, calculate)
└── src/
    ├── index.js              — точка входа, экспорты
    ├── SdekPvzWidget.js      — основной класс (open/close, монтирует Vue app)
    ├── style.css             — изолированные стили (префикс sdwo-)
    └── components/
        ├── MapPane.vue       — OpenLayers карта (vue3-openlayers компоненты)
        └── PvzList.vue       — список ПВЗ + блок тарифа + кнопка «Выбрать»
```

## Быстрый старт

### Установка и билд

```bash
npm install
npm run build
```

После билда в `dist/`:
- `SdekPvzWidget.es.js` — ES-модуль (для webpack/rollup/vite)
- `SdekPvzWidget.umd.js` — UMD (для обычного `<script>`-тега)

### Подключение в браузере (после билда)

```html
<!-- OpenLayers CSS (обязательно) -->
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/ol@10.6.0/ol.css" />

<script src="dist/SdekPvzWidget.umd.js"></script>
<link  href="dist/style.css" rel="stylesheet" />

<script>
  const widget = new SdekPvzWidget({
    defaultLocation: 'Краснокамск',
    fromLocation:    'Челябинск',
    packages: [
      { length: 30, width: 20, height: 15, weight: 1000 }
    ],
    backendUrl: '/sdek-backend.php',
    onChoose: (type, tariff, address) => {
      console.log('Выбран ПВЗ:', address);
      console.log('Тариф:', tariff);
    }
  });

  document.getElementById('open-btn').addEventListener('click', () => widget.open());
</script>
```

### Dev-сервер

```bash
npm run dev      # http://localhost:5173  (Vite HMR)
npm run build    # production build → dist/
npm run preview  # preview production build
```

### Docker Compose (рекомендуется)

```bash
# 1. Создать .env из example.env
cp example.env .env

# 2. Заполнить ключи в .env
#    SDEK_CLIENT_ID=...
#    SDEK_CLIENT_SECRET=...
#    DADATA_API_KEY=...

# 3. Запустить
docker compose up -d
```

После запуска:
- **Frontend**: http://localhost:5177 (Vite dev server с HMR)
- **Backend**: http://localhost:8080 (PHP dev server)

> **Важно**: для production-сборки используйте `npm run build` и настройте свой веб-сервер (nginx/apache) для раздачи статики и проксирования запросов к бэкенту.

## Настройка бэкенда

В файле `sdek-backend.php` заполнить массив `$CONFIG`:

```php
$CONFIG = [
    'DADATA_TOKEN'     => 'YOUR_DADATA_TOKEN',       // https://dadata.ru/api/
    'DADATA_SECRET'   => 'YOUR_DADATA_SECRET',
    'CDEK_CLIENT_ID'     => 'YOUR_CDEK_CLIENT_ID',   // СДЭК OAuth2
    'CDEK_CLIENT_SECRET' => 'YOUR_CDEK_SECURE_PASSWORD',
];
```

Если ключи не заданы — geocode падает в fallback на Nominatim (без ключа).

## API виджета

### SdekPvzWidget(options)

| Параметр          | Тип       | Обяз. | Описание                          |
|-------------------|-----------|--------|----------------------------------|
| `defaultLocation`  | `string`  | Да     | Город для фокуса карты           |
| `fromLocation`     | `string`  | Да     | Город отправления                |
| `packages`         | `Array`   | Нет    | `[{length, width, height, weight}]` |
| `onChoose`        | `Function`| Нет    | callback(type, tariff, address)   |
| `backendUrl`       | `string`  | Нет    | URL sdek-backend.php (default: `./`) |

### Методы

- `widget.open()` — показать popup
- `widget.close()` — закрыть popup

## Бэкенд-эндпоинты

| action      | Метод | Параметры                                | Описание                   |
|-------------|-------|------------------------------------------|----------------------------|
| `geocode`   | GET   | `query` — строка адреса                 | Координаты + city_code     |
| `pvzlist`   | GET   | `country_code=RU`, `bbox` (опц.)        | Список ПВЗ СДЭК           |
| `calculate` | GET   | `from_city`, `to_pvz_code`, `packages`  | Стоимость и срок доставки  |

## Формат данных

### address (onChoose callback)

```json
{
  "city_code": 588,
  "city": "Краснокамск",
  "type": "PVZ",
  "code": "KPS4",
  "name": "KPS4, Краснокамск, Комсомольский проспект",
  "address": "Комсомольский проспект, 9",
  "work_time": "Пн-Пт 10:00-20:00, Сб 10:00-18:00",
  "location": [55.753883, 58.082108],
  "have_cash": true,
  "have_cashless": true
}
```

### tariff (onChoose callback)

```json
{
  "delivery_sum": 350,
  "period_min": 3,
  "period_max": 5,
  "tariff_name": "Экономичная доставка",
  "tariff_code": "136"
}
```
