# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Проект

`SdekPvzWidget` — встраиваемый JS-виджет для выбора ПВЗ СДЭК на карте с расчётом тарифа на лету. Собирается в UMD для подключения обычным `<script>`-тегом. Фронтенд — Vue 3 + OpenLayers, бэкенд — один PHP-файл, проксирующий DaData и СДЭК API. Интерфейс на русском.

## Команды

```bash
npm install
npm run dev       # Vite HMR на :5173 (standalone) или :5177 (в docker)
npm run build     # → dist/SdekPvzWidget.js (UMD, CSS встроен)
npm run preview
```

Полный стек (фронт + PHP-бэк):

```bash
cp example.env .env   # заполнить SDEK_CLIENT_ID / SDEK_CLIENT_SECRET / DADATA_API_KEY
docker compose up -d  # фронт :5177, php -S :8080
```

Скрипты тестов, линтера и typecheck не настроены.

При отладке геокодинга: результаты кешируются в `geocode_cache.json` в корне репозитория (TTL 24 часа) — удалить файл, чтобы форсировать обновление.

## Архитектура

### Сборка
`vite.config.js` собирает два формата — `dist/SdekPvzWidget.umd.js` и `dist/SdekPvzWidget.es.js`, CSS инлайнится в JS через `vite-plugin-css-injected-by-js`. `inlineDynamicImports: true` — всё одним файлом на формат. `package.json` экспорты синхронизированы с выходом.

### Поток на фронте
`src/index.js` → класс `SdekPvzWidget` (ваниль, без фреймворка). Потребитель создаёт экземпляр, вызывает `widget.open()`, который императивно создаёт overlay `<div>`, монтирует в него Vue 3 app через `createApp()` с render-функцией на `h()` (без runtime-компилятора шаблонов в бандле), затем `_loadInitial()` геокодит `defaultLocation` и загружает все ПВЗ.

Корневой Vue-компонент держит реактивное состояние (`list`, `active`, `tariff`, `pvz`, `mapCenter`) и двух детей:
- `MapPane.vue` — карта OpenLayers напрямую через `ol/Map`, `ol/source/Cluster` и т.д. (импортирует `ol/ol.css`). Поле поиска использует подсказки DaData (`action=suggest`) и эмитит только `moveend` / `markerselect`. Экспортирует императивные методы (`getBounds`, `panTo`, `flashError`), к которым корневой виджет обращается через `ref`.
- `PvzList.vue` — скроллируемый список + панель тарифа + кнопка «Выбрать».

Путь данных: `_loadInitial` параллельно геокодит `defaultLocation` и тащит полный список ПВЗ в `this._pvzAll`, далее `onMapMoveend(bounds)` фильтрует и через helper `sortByBounds` (модульный, возвращает shallow-клоны с полем `_dist`) сортирует по расстоянию от центра в `vm.list`. Расстояния считаются грубо — евклидова метрика на lat/lon с коэффициентом ×111 км, не геодезически. Клик по маркеру или строке вызывает `_selectPvz()`, который панорамирует карту и запрашивает `calculate` через POST. По кнопке «Выбрать» вызывается `onChoose(type, tariff, address)` потребителя в try/finally — виджет закрывается даже если callback бросил.

### Изоляция стилей
Все CSS-классы с префиксом `sdwo-` (см. `src/style.css`), потому что виджет монтируется в произвольные хост-страницы. При добавлении стилей префикс сохранять.

### Бэкенд (`sdek-backend.php`)
Однофайловый роутер, диспетчер по `?action=`:

| action      | назначение |
|-------------|------------|
| `suggest`   | Подсказки адресов DaData (с опциональным bias по lat/lon) |
| `geocode`   | Прямой геокод DaData → `{lat, lon, city, city_code}`, fallback на Nominatim, если нет токена. Файловый кеш (`geocode_cache.json`, TTL 24ч) с эвикцией протухших записей при записи. |
| `pvzlist`   | СДЭК `/v2/deliverypoints`, опционально с фильтром по `bbox`. Bbox-фильтр умеет оба формата `location`: `{latitude, longitude}` (API) и `[lat, lon]` (CSV-fallback). |
| `calculate` | СДЭК `/v2/calculator/tarifflist` — нужны `from_city`, `to_pvz_code` (должен быть `city_code` СДЭК) и JSON-массив `packages`. Принимается и через POST, и через GET (`$_REQUEST`). |

**Env-переменные:**
- `SDEK_CLIENT_ID`, `SDEK_CLIENT_SECRET`, `DADATA_API_KEY` — ключи внешних API.
- `SDEK_ALLOWED_ORIGINS` — whitelist доменов через запятую для CORS. Пустое значение = `*` (dev-режим, в проде обязательно задать).
- `SDEK_CACHE_DIR` — директория кешей/логов (по умолчанию `__DIR__`). Вынести за пределы docroot в проде, чтобы `cdek_token.json` / `geocode_cache.json` / `pvz_cache.json` не торчали наружу.
- `SDEK_DEBUG=1` — включает запись в `geocode_debug.log` и `tariff_debug.log` (иначе логи не пишутся).

Все кеши и токены пишутся атомарно (`atomicWrite`: tmp-файл + `rename`, `LOCK_EX` на временный файл) — безопасно при конкурентных запросах.

Бэкенд возвращает `{error: "..."}` при ошибке с HTTP 4xx/5xx; хелпер `_fetch` на фронте превращает это в JS-исключение.

### Контракт фронт↔бэк
`to_pvz_code` в запросе calculate: фронт передаёт `pvz.city_code || pvz.code` — СДЭК-тариф ждёт именно `city_code`. Если видишь ошибки тарифа — проверь, что у выбранного ПВЗ реально заполнен `city_code`.

`_fetch` на фронте — обычно GET, для `calculate` форсится POST с form-urlencoded телом (чтобы не упирались в лимит URL при длинном JSON `packages`). Таймаут — 15с через `AbortSignal.timeout`.

## Подводные камни

- В `SdekPvzWidget.js` используется render-функция, не SFC-шаблон — чтобы в бандле не оказался runtime-компилятор Vue. При расширении корневого компонента это свойство сохранять.
- `sortByBounds` возвращает shallow-клоны с полем `_dist`, **не мутируя** оригинальные объекты из `_pvzAll`. Вотчер на `props.markers` в `MapPane.vue` не `deep` — полагается на то, что родитель передаёт новый массив при каждом `moveend`.
- Две HTML-точки входа: `index.html` (dev — импортирует `src/index.js`) и `index-dist.html` (демо против собранного бандла).
- В `$CONFIG` у ключей есть плейсхолдеры `YOUR_...` — проверка `str_starts_with($token, 'YOUR_')` используется как сигнал «не настроено», поэтому новые placeholder-значения должны сохранять этот префикс.
