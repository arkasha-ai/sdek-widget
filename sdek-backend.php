<?php
/**
 * sdek-backend.php
 * Бэкенд для виджета SdekPvzWidget
 *
 * Endpoints (параметр action):
 *   geocode   — прямой геокодинг через DaData API
 *   pvzlist   — список ПВЗ СДЭК (фильтр по стране, bbox)
 *   calculate — расчёт тарифа доставки до выбранного ПВЗ
 *
 * Все ключи — в массив $CONFIG в начале файла.
 */

// ================================================================
// КОНФИГУРАЦИЯ  ← заполнить перед использованием
// ================================================================
$CONFIG = [
    // DaData API (https://dadata.ru/api/)
    'DADATA_TOKEN' => getenv('DADATA_API_KEY') ?: 'YOUR_DADATA_TOKEN',          // Token из ЛК DaData
    'DADATA_SECRET'=> getenv('DADATA_SECRET') ?:'YOUR_DADATA_SECRET',          // Secret (для подсказок, опц.)

    // СДЭК OAuth2 (https://www.cdek.ru/api/)
    'CDEK_CLIENT_ID'     => getenv('SDEK_CLIENT_ID') ?: 'YOUR_CDEK_CLIENT_ID',      // client_id
    'CDEK_CLIENT_SECRET' => getenv('SDEK_CLIENT_SECRET') ?: 'YOUR_CDEK_CLIENT_SECRET',  // client_secret
];

// ================================================================
// Заголовки
// ================================================================
header('Content-Type: application/json; charset=utf-8');
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST');
header('Access-Control-Allow-Headers: Content-Type, Authorization');

// ================================================================
// Роутер
// ================================================================
$action = $_REQUEST['action'] ?? '';
$cacheDir  = __DIR__ . '/pvz_cache';

try {
    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }
    $result = match ($action) {
        'suggest'   => handleSuggest(
            $_REQUEST['query'] ?? '',
            (isset($_REQUEST['lat']) && $_REQUEST['lat'] !== '') ? (float) $_REQUEST['lat'] : null,
            (isset($_REQUEST['lon']) && $_REQUEST['lon'] !== '') ? (float) $_REQUEST['lon'] : null
        ),
        'geocode'   => handleGeocode($_REQUEST['query'] ?? ''),
        'pvzlist'   => handlePvzList(
            $_REQUEST['country_code'] ?? 'RU',
            $_REQUEST['bbox'] ?? null,   // [minLon,minLat,maxLon,maxLat]
            $_REQUEST['page'] ?? null,
            $_REQUEST['size'] ?? null
        ),
        'calculate' => handleCalculate(
            $_REQUEST['from_city']    ?? '',
            $_REQUEST['to_pvz_code'] ?? '',
            json_decode($_REQUEST['packages'] ?? '[]', true)
        ),
        default => throw new InvalidArgumentException("Unknown action: {$action}"),
    };

    echo json_encode($result, JSON_UNESCAPED_UNICODE);

} catch (InvalidArgumentException $e) {
    http_response_code(400);
    echo json_encode(['error' => $e->getMessage()], JSON_UNESCAPED_UNICODE);

} catch (Exception $e) {
    http_response_code(500);
    echo json_encode([
        'error'   => 'Internal server error',
        'detail'  => $e->getMessage(),
    ], JSON_UNESCAPED_UNICODE);
}

// ================================================================
// 0. SUGGEST
// --------
// Вход:  query — строка поиска, lat/lon — координаты центра карты для приоритизации
// Выход: { suggestions: [{value, lat, lon, city, city_code, region}] }
// ================================================================
function handleSuggest(string $query, ?float $lat = null, ?float $lon = null): array {
    global $CONFIG;

    if (trim($query) === '') {
        return ['suggestions' => []];
    }

    $token = $CONFIG['DADATA_TOKEN'];
    if (!$token || str_starts_with($token, 'YOUR_')) {
        return ['suggestions' => []];
    }

    // Reverse geocode координат карты → city/region с kladr_id для приоритизации
    $locationsBoost = [['country' => 'Россия']];
    if ($lat !== null && $lon !== null) {
        $location = handleGeolocate($lat, $lon);
        $kladrIds = [];
        if (!empty($location['city_kladr_id']))   $kladrIds[] = $location['city_kladr_id'];
        if (!empty($location['region_kladr_id'])) $kladrIds[] = $location['region_kladr_id'];
        foreach ($kladrIds as $kladrId) {
            $locationsBoost[] = ['kladr_id' => $kladrId];
        }
    }

    $suggestions = handleSuggestRequest($token, $locationsBoost, $query, $lat, $lon);

    $result = [];
    foreach ($suggestions as $s) {
        $d = $s['data'] ?? [];

        $type = 'city';
        if (!empty($d['house'])) {
            $type = 'house';
        } elseif (!empty($d['street'])) {
            $type = 'street';
        } elseif (!empty($d['settlement'])) {
            $type = 'settlement';
        }

        $result[] = [
            'value'     => $s['value'] ?? '',
            'lat'       => $d['geo_lat']    ?? null,
            'lon'       => $d['geo_lon']    ?? null,
            'city'      => $d['city']       ?? $d['settlement'] ?? '',
            'city_code' => $d['city_kladr_id'] ?? null,
            'region'    => $d['region'] ?? '',
            'type'      => $type,
            'house'     => $d['house'] ?? null,
            'street'    => $d['street'] ?? null,
            'settlement'=> $d['settlement'] ?? null,
        ];
    }

    return ['suggestions' => $result];
}

function handleSuggestRequest(string $token, array $locationsBoost, string $query, ?float $lat = null, ?float $lon = null): array {
    global $cacheDir;
    $cacheMaxSec  = 3600;
    $cacheKey  = "suggest_".md5("{$query}|{$lat}|{$lon}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (file_exists($cacheFile)) {
        if ((time() - filemtime($cacheFile)) < $cacheMaxSec) {
            return json_decode(file_get_contents($cacheFile), true);
        }
        // remove old cache file
        if (!unlink($cacheFile)) {
            echo json_encode(['error' => 'error delete cache file: '.$cacheFile], JSON_UNESCAPED_UNICODE);
        }
    }

    $ch = curl_init('https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Token ' . $token,
        ],
        CURLOPT_POSTFIELDS => json_encode([
            'query'           => $query,
            'count'           => 8,
            'locations_boost' => $locationsBoost,
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    $suggestions = $resp['suggestions'] ?? [];
    file_put_contents($cacheFile, json_encode($suggestions, JSON_UNESCAPED_UNICODE));

    return $suggestions;
}

/**
 * Обратное геокодирование: координаты → адрес (город/область с kladr_id)
 * Используется для приоритизации поиска по текущему положению карты
 */
function handleGeolocate(float $lat, float $lon): array {
    global $CONFIG;

    $token = $CONFIG['DADATA_TOKEN'];
    if (!$token || str_starts_with($token, 'YOUR_')) {
        return [];
    }

    $d = handleGeolocateRequest($token, $lat, $lon);

    return [
        'city_kladr_id'   => $d['city_kladr_id']   ?? null,
        'region_kladr_id' => $d['region_kladr_id'] ?? null,
        'city'            => $d['city']            ?? null,
        'region'          => $d['region']          ?? null,
    ];
}

function handleGeolocateRequest(string $token, float $lat, float $lon): array
{
    global $cacheDir;
    $cacheMaxSec  = 3600;
    $cacheKey  = "geolocate_".md5("{$lat}|{$lon}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (file_exists($cacheFile)) {
        if ((time() - filemtime($cacheFile)) < $cacheMaxSec) {
            return json_decode(file_get_contents($cacheFile), true);
        }
        // remove old cache file
        if (!unlink($cacheFile)) {
            echo json_encode(['error' => 'error delete cache file: '.$cacheFile], JSON_UNESCAPED_UNICODE);
        }
    }
    $ch = curl_init('https://suggestions.dadata.ru/suggestions/api/4_1/rs/geolocate/address');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Token ' . $token,
        ],
        CURLOPT_POSTFIELDS => json_encode([
            'lat' => $lat,
            'lon' => $lon,
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    if (!is_array($resp) || empty($resp)) {
        return [];
    }
    $d = $resp['suggestions'][0]['data'] ?? [];
    file_put_contents($cacheFile, json_encode($d, JSON_UNESCAPED_UNICODE));

    return $d;
}

// ================================================================
// 1. GEOCODE
// ----------
// Вход:  query — строка адреса
// Выход: { lat, lon, city, city_code }
// ================================================================
function handleGeocode(string $query): array {
    global $CONFIG;

    if (trim($query) === '') {
        throw new InvalidArgumentException('query is required');
    }

    $token = $CONFIG['DADATA_TOKEN'];
    if (!$token || str_starts_with($token, 'YOUR_')) {
        // fallback через Nominatim (без ключа)
        return geocodeNominatim($query);
    }

    $suggestions = handleGeocodeRequest($token, $query);

    if (!$suggestions) {
        return geocodeNominatim($query);
    }

    $d = $suggestions[0]['data'] ?? [];
    return [
        'lat'       => $d['geo_lat']    ?? null,
        'lon'       => $d['geo_lon']    ?? null,
        'city'      => $d['city']       ?? $d['settlement'] ?? $query,
        'city_code' => $d['city_kladr_id'] ?? null,
    ];
}

function handleGeocodeRequest(string $token, string $query): array {
    global $cacheDir;
    $cacheMaxSec  = 3600;
    $cacheKey  = "geocode_".md5("{$query}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (file_exists($cacheFile)) {
        if ((time() - filemtime($cacheFile)) < $cacheMaxSec) {
            return json_decode(file_get_contents($cacheFile), true);
        }
        // remove old cache file
        if (!unlink($cacheFile)) {
            echo json_encode(['error' => 'error delete cache file: '.$cacheFile], JSON_UNESCAPED_UNICODE);
        }
    }
    $ch = curl_init('https://suggestions.dadata.ru/suggestions/api/4_1/rs/geolocate/address');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type:  application/json',
            'Authorization: Token ' . $token,
        ],
        CURLOPT_POSTFIELDS => json_encode([
            'query'       => $query,
            'count'       => 1,
            'locations'   => [['country' => 'Россия']],
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    $suggestions = $resp['suggestions'] ?? [];
    file_put_contents($cacheFile, json_encode($suggestions, JSON_UNESCAPED_UNICODE));

    return $suggestions;
}

/**
 * Fallback-геокодер через Nominatim (OpenStreetMap) — без ключа
 */
function geocodeNominatim(string $query): array {
    $q = urlencode($query . ', Россия');
    $url = "https://nominatim.openstreetmap.org/search?q={$q}&format=json&limit=1&countrycodes=ru";

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ['User-Agent: SdekWidget/1.0'],
        CURLOPT_TIMEOUT        => 8,
    ]);

    $resp = curlExecJson($ch);
    if (!$resp || !is_array($resp)) {
        return ['error' => 'Geocoding failed', 'lat' => null, 'lon' => null];
    }

    $r = $resp[0] ?? [];
    return [
        'lat'       => $r['lat']    ?? null,
        'lon'       => $r['lon']    ?? null,
        'city'      => parseOsmDisplayName($r['display_name'] ?? $query),
        'city_code' => null,
    ];
}

function parseOsmDisplayName(string $name): string {
    $parts = explode(',', $name);
    return trim($parts[0]);
}

// ================================================================
// 2. PVZLIST
// ----------
// Вход:  country_code='RU', bbox=null, page=1, size=50
// Выход: { items: [...], total, page, size, total_pages }
// Заголовки: x-total-elements, x-total-pages
// Фильтры: type=PVZ, is_handout=true, country_code
// ================================================================
function handlePvzList(string $country, ?array $bbox, ?int $page, ?int $size): array {
    $page  = is_null($page) ? $page : max(0, $page);
    $size  = is_null($size) ? $size : min(max(0, $size), 500); // лимит на стороне API

    $pvzData = pvzLoadFromCdek($country, $page, $size);

    // bbox-фильтр применяется post-factum (城区 фильтрует сервер СДЭК)
    if ($bbox && count($bbox) === 4) {
        [$minLon, $minLat, $maxLon, $maxLat] = $bbox;
        $pvzData['items'] = array_filter($pvzData['items'], function ($p) use ($minLon, $minLat, $maxLon, $maxLat) {
            list ('latitude' => $lat, 'longitude' => $lon) = $p['location'] ?? [];
            if ($lat === null || $lon === null) return false;
            return $lon >= $minLon && $lon <= $maxLon
                && $lat >= $minLat && $lat <= $maxLat;
        });
        $pvzData['items'] = array_values($pvzData['items']);
        // после bbox-фильтра количество может быть < size — корректируем total
        $pvzData['total'] = count($pvzData['items']);
    }

    // приводим к нужному формату
    $pvzData['items'] = array_values(array_map('normalizePvz', $pvzData['items']));

    // проксируем заголовки пагинации
    header('x-total-elements: ' . $pvzData['total']);
    header('x-total-pages: '    . $pvzData['total_pages']);

    return $pvzData;
}

function pvzLoadFromCdekAll(string $country): array {
    $page = -1;
    $items = [];
    do {
        $page++;
        $result = pvzLoadFromCdek($country, $page, 500);
        $items = array_merge($items, $result['items']);
    } while ($result['total_pages'] > $page);
    return $items;
}

/**
 * Загрузка ПВЗ с пагинацией через /v2/deliverypoints
 * Кэш: ключ = md5(country|page|size), TTL 1 час
 */
function pvzLoadFromCdek(string $country, ?int $page, ?int $size): array {
    global $cacheDir;

    $cacheMax  = 3600 * 2;
    $cacheKey  = md5("{$country}|{$page}|{$size}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (file_exists($cacheFile)) {
        if ((time() - filemtime($cacheFile)) < $cacheMax) {
            $dec = json_decode(file_get_contents($cacheFile), true);
            if (is_array($dec)) return $dec;
        } else {
            // remove old cache file
            if (!unlink($cacheFile)) {
                echo json_encode(['error' => 'error delete cache file: ' . $cacheFile], JSON_UNESCAPED_UNICODE);
            }
        }
    }

    // Запрос к официальному API СДЭК с пагинацией и фильтрами
    $token = cdekGetToken();
    if ($token) {
        $query = http_build_query(array_filter([
            'country_code' => $country,
            'type'         => 'PVZ',
            'is_handout'   => 'true',
            'page'         => $page,
            'size'         => $size,
        ]));
        $url = 'https://api.cdek.ru/v2/deliverypoints?' . $query;
        $result = curlExecWithHeaders($url, [
            'Authorization: Bearer ' . $token,
            'Accept: application/json',
        ]);

        $respHeaders = $result['headers'];
        $resp = json_decode($result['body'], true);

        if (is_array($resp) && !empty($resp)) {
            // Извлекаем пагинацию из заголовков
            $total    = (int) ($respHeaders['x-total-elements'] ?? count($resp));
            $totalPages = (int) ($respHeaders['x-total-pages'] ?? 1);

            $result = [
                'items'      => $resp,
                'total'      => $total,
                'page'       => $page,
                'size'       => $size,
                'total_pages'=> $totalPages,
            ];

            file_put_contents($cacheFile, json_encode($result, JSON_UNESCAPED_UNICODE));
            return $result;
        }
    }

    // Fallback: CSV — без пагинации (весь файл), эмулируем пагинацию
    $allPvz = pvzLoadFromCsv();

    // фильтр по country_code (у CSV всегда RU)
    $filtered = array_filter($allPvz, fn($p) => ($p['country_code'] ?? 'RU') === $country);
    $filtered = array_values($filtered);

    $total = count($filtered);
    $offset = ($page - 1) * $size;
    $items  = array_slice($filtered, $offset, $size);

    return [
        'items'       => $items,
        'total'       => $total,
        'page'        => $page,
        'size'        => $size,
        'total_pages' => (int) ceil($total / $size),
    ];
}

/**
 * CSV-fallback — официальная выгрузка
 * https://www.cdek.ru/csv/directory-of-goods-issue-points.csv
 */
function pvzLoadFromCsv(): array {
    $csvUrl = 'https://www.cdek.ru/csv/directory-of-goods-issue-points.csv';
    $cacheFile = __DIR__ . '/pvz_csv_cache.json';
    $cacheMax  = 86400; // сутки

    if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheMax) {
        $dec = json_decode(file_get_contents($cacheFile), true);
        if (is_array($dec)) return $dec;
    }

    $ch = curl_init($csvUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_FOLLOWLOCATION=> true,
    ]);

    $csv = curlExecRaw($ch);
    curl_close($ch);

    if (!$csv) return [];

    $lines    = explode("\n", trim($csv));
    if (count($lines) < 2) return [];

    $headers  = str_getcsv(array_shift($lines), ';');
    $idx = array_flip(array_map('trim', $headers));

    $pvz = [];
    foreach ($lines as $line) {
        if (!trim($line)) continue;
        $v = str_getcsv($line, ';');
        $lat = trim($v[$idx['Latitude']  ?? 7]  ?? '');
        $lon = trim($v[$idx['Longitude'] ?? 8]  ?? '');
        $pvz[] = [
            'code'           => $v[$idx['Code']           ?? 0] ?? '',
            'name'           => $v[$idx['Name']           ?? 1] ?? '',
            'city'           => $v[$idx['City']           ?? 2] ?? '',
            'address'        => $v[$idx['Address']        ?? 3] ?? '',
            'work_time'      => $v[$idx['WorkTime']       ?? 4] ?? '',
            'country_code'   => 'RU',
            'location'       => [
                is_numeric($lat) ? (float) $lat : 0.0,
                is_numeric($lon) ? (float) $lon : 0.0,
            ],
            'have_cash'      => ($v[$idx['IsCash']        ?? 9]  ?? '') === '1',
            'have_cashless'  => ($v[$idx['IsImposed']     ?? 10] ?? '') === '1',
            'allowed_cod'    => true,
            'is_dressing_room'=> ($v[$idx['DressingRoom']  ?? 11] ?? '') === '1',
        ];
    }

    $encoded = json_encode($pvz, JSON_UNESCAPED_UNICODE);
    file_put_contents($cacheFile, $encoded);

    return $pvz;
}

/**
 * Приведение записи ПВЗ к нужному формату
 */
function normalizePvz(array $p): array {
    $loc = $p['location'] ?? [];
    return [
        'city_code'       => $loc['city_code']     ?? $loc['city_uuid'] ?? '',
        'city'           => $loc['city']           ?? '',
        'type'           => $p['type']           ?? 'PVZ',
        'postal_code'    => $loc['postal_code']    ?? '',
        'country_code'   => $loc['country_code']   ?? 'RU',
        'region'         => $loc['region']         ?? '',
        'have_cashless'  => $p['have_cashless']  ?? true,
        'have_cash'      => $p['have_cash']       ?? true,
        'allowed_cod'    => $p['allowed_cod']    ?? true,
        'is_dressing_room' => $p['is_dressing_room'] ?? false,
        'code'           => $p['code']            ?? '',
        'name'           => $p['name']            ?? ($p['code'] ?? ''),
        'address'        => $loc['address']        ?? '',
        'work_time'      => $p['work_time']      ?? '',
        'location'       => [
            $loc['latitude'] ?? 0.0,
            $loc['longitude'] ?? 0.0,
        ],
        'weight_min'     => $p['weight_min']     ?? 0,
        'weight_max'     => $p['weight_max']     ?? 100000000,
        'dimensions'     => $p['dimensions']      ?? null,
    ];
}

// ================================================================
// 3. CALCULATE
// ------------
// Вход:  from_city, to_pvz_code, packages=[{length,width,height,weight}]
// Выход: { delivery_sum, period_min, period_max, tariff_name, tariff_code }
// ================================================================
function handleCalculate(string $fromCity, string $toPvzCode, array $packages): array {

    if (!$fromCity || !$toPvzCode) {
        throw new InvalidArgumentException('from_city and to_pvz_code are required');
    }

    // --- 1. Определяем city_code города-отправителя и city_code места доставки ---
    $geo = handleGeocode($fromCity);

    // Пробуем из PVZ по коду
    $pvzAll = pvzLoadFromCdekAll($geo['country_iso_code'] ?? 'RU');
    $target = null;
    $fromCode = null; //kladrRegionCode($geo['city'] ?? $fromCity);
    if (isset($geo['city_code'])) {
        $fromCode = $geo['city_code'];
    }
    foreach ($pvzAll as $p) {
        if (isset($target) && isset($fromCode)) {
            break;
        }
        if (($p['code'] ?? '') == $toPvzCode) {
            $target = $p;
        }
        if (!isset($fromCode) && isset($p['location']) && $p['location']['city'] == trim($fromCity)) {
            $fromCode = $p['location']['city_code'];
        }
    }
    $toCode   = (isset($target) && isset($target['location'])) ? $target['location']['city_code'] : null;

    if (!isset($fromCode) || !isset($toCode)) {
        return [
            'error'        => 'Incorrect from or to city code',
            'tariff_codes' => null,
        ];
    }

    // --- 2. Собираем посылки ---
    $items = [];
    foreach ($packages ?: [[]] as $pkg) {
        $items[] = [
            'weight'  => (float) ($pkg['weight'] ?? 1000) / 1000, // г → кг
            'length'  => (float) ($pkg['length'] ?? 10),
            'width'   => (float) ($pkg['width']  ?? 10),
            'height'  => (float) ($pkg['height'] ?? 10),
        ];
    }

    // --- 3. Запрос тарифа ---
    $token = cdekGetToken();
    if (!$token) {
        return [
            'error'        => 'CDEK authorization failed',
            'tariff_codes' => null,
        ];
    }

    $payload = [
        'type'          => 1,                               // интернет-магазин
        'date'          => date('Y-m-d\TH:i:sO'), // текущая по-умолчанию
        'currency'      => 1,                               // рубли
        'from_location' => ['code' => $fromCode], // Код населенного пункта СДЭК (city_code)
        'to_location'   => ['code' => $toCode], // Код населенного пункта СДЭК (city_code)
        'packages'      => $items,
    ];

    $resp = handleCalculateRequest($token, json_encode($payload));
    if (isset($resp['tariff_codes'])) {
        $resp = $resp['tariff_codes'];
    }

    // tarifflist возвращает массив тарифов — берём первый (самый быстрый/дешёвый)
    if (is_array($resp)) {
        $resultTariff = [];
        foreach ($resp as $tariff) {
            if (
                $tariff['delivery_mode'] !== 4  // только склад-склад
                || str_contains(mb_strtolower($tariff['tariff_name']), 'возврат') // только доставка
            ) {
                continue;
            }
            $resultTariff[] = [
                'delivery_sum' => $tariff['delivery_sum'] ?? null,
                'period_min' => $tariff['period_min'] ?? null,
                'period_max' => $tariff['period_max'] ?? null,
                'tariff_name' => $tariff['tariff_name'] ?? null,
                'tariff_code' => $tariff['tariff_code'] ?? null,
            ];
        }
        return [
            'error' => null,
            'tariff_codes' => $resultTariff
        ];
    }

    return [
        'error' => null,
        'tariff_codes' => [],
    ];
}

function handleCalculateRequest(string $token, string $payload): array {
    global $cacheDir;
    $cacheMaxSec  = 3600;
    $cacheKey  = "calculate_".md5("{$payload}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (file_exists($cacheFile)) {
        if ((time() - filemtime($cacheFile)) < $cacheMaxSec) {
            return json_decode(file_get_contents($cacheFile), true);
        }
        // remove old cache file
        if (!unlink($cacheFile)) {
            echo json_encode(['error' => 'error delete cache file: '.$cacheFile], JSON_UNESCAPED_UNICODE);
        }
    }

    $ch = curl_init('https://api.cdek.ru/v2/calculator/tarifflist');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST          => true,
        CURLOPT_HTTPHEADER    => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $token,
        ],
        CURLOPT_POSTFIELDS => $payload,
        CURLOPT_TIMEOUT    => 15,
    ]);

    $resp = curlExecJson($ch);
    file_put_contents($cacheFile, json_encode($resp, JSON_UNESCAPED_UNICODE));

    return $resp;
}


/**
 * Код региона по КЛАДР (заглушка — первые 2 цифры)
 * Для точного расчёта нужен реальный city_code
 */
function kladrRegionCode(string $city): string {
    // Берём часть КЛАДР-кода — СДЭК понимает 2-значный код региона
    return $city . '00000000000';
}

// ================================================================
// OAuth-токен СДЭК (кеширование в файл)
// ================================================================
function cdekGetToken(): ?string {
    global $CONFIG;
    $cacheFile = __DIR__ . '/cdek_token.json';

    $cached = @json_decode(file_get_contents($cacheFile), true);
    if ($cached && ($cached['expires_at'] ?? 0) > time() + 120) {
        return $cached['access_token'];
    }

    $clientId     = $CONFIG['CDEK_CLIENT_ID']     ?? '';
    $clientSecret = $CONFIG['CDEK_CLIENT_SECRET'] ?? '';

    if (!$clientId || str_starts_with($clientId, 'YOUR_')) {
        return null; // не настроен
    }

    $ch = curl_init('https://api.cdek.ru/v2/oauth/token');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST          => true,
        CURLOPT_HTTPHEADER    => ['Content-Type: application/x-www-form-urlencoded'],
        CURLOPT_POSTFIELDS    => http_build_query([
            'grant_type'    => 'client_credentials',
            'client_id'     => $clientId,
            'client_secret' => $clientSecret,
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    curl_close($ch);

    if (empty($resp['access_token'])) return null;

    $data = [
        'access_token' => $resp['access_token'],
        'expires_at'   => time() + ($resp['expires_in'] ?? 3600),
    ];
    @file_put_contents($cacheFile, json_encode($data));

    return $resp['access_token'];
}

// ================================================================
// Утилиты cURL
// ================================================================
function curlExecJson($ch): array {
    $raw = curlExecRaw($ch);
    curl_close($ch);
    if (!$raw) return [];
    $dec = json_decode($raw, true);
    return is_array($dec) ? $dec : [];
}

function curlExecRaw($ch): string {
    // Получаем response headers отдельно
    $responseHeaders = [];
    curl_setopt($ch, CURLOPT_HEADERFUNCTION, function($ch, $header) use (&$responseHeaders) {
        $len = strlen($header);
        $header = trim($header);
        if (!empty($header) && strpos($header, ':') !== false) {
            $parts = explode(':', $header, 2);
            $responseHeaders[strtolower(trim($parts[0]))] = trim($parts[1]);
        }
        return $len;
    });

    $out = curl_exec($ch);
    if (curl_errno($ch)) {
        error_log('cURL error: ' . curl_error($ch));
        return '';
    }
    return $out ?: '';
}

/**
 * cURL-exec с извлечением заголовков (используется в pvzLoadFromCdek)
 * Возвращает ['body' => string, 'headers' => [string=>string]]
 */
function curlExecWithHeaders(string $url, array $headers): array {
    $ch = curl_init($url);
    $responseHeaders = [];
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => $headers,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_HEADERFUNCTION => function($ch, $header) use (&$responseHeaders) {
            $len = strlen($header);
            $header = trim($header);
            if (!empty($header) && strpos($header, ':') !== false) {
                $parts = explode(':', $header, 2);
                $responseHeaders[strtolower(trim($parts[0]))] = trim($parts[1]);
            }
            return $len;
        },
    ]);
    $body = curl_exec($ch);
    curl_close($ch);
    return ['body' => $body ?: '', 'headers' => $responseHeaders];
}
