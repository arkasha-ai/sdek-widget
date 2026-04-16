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
    'DADATA_TOKEN' => 'YOUR_DADATA_TOKEN',          // Token из ЛК DaData
    'DADATA_SECRET'=> 'YOUR_DADATA_SECRET',          // Secret (для подсказок, опц.)

    // СДЭК OAuth2 (https://www.cdek.ru/api/)
    'CDEK_CLIENT_ID'     => 'YOUR_CDEK_CLIENT_ID',      // client_id
    'CDEK_CLIENT_SECRET' => 'YOUR_CDEK_CLIENT_SECRET',  // client_secret
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

try {
    $result = match ($action) {
        'geocode'   => handleGeocode($_REQUEST['query'] ?? ''),
        'pvzlist'   => handlePvzList(
            $_REQUEST['country_code'] ?? 'RU',
            $_REQUEST['bbox'] ?? null,   // [minLon,minLat,maxLon,maxLat]
            (int) ($_REQUEST['page'] ?? 1),
            (int) ($_REQUEST['size'] ?? 500)
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
function handlePvzList(string $country, ?array $bbox, int $page, int $size): array {
    $page  = max(1, $page);
    $size  = min(max(1, $size), 200); // лимит на стороне API

    $pvzData = pvzLoadFromCdek($country, $page, $size);

    // bbox-фильтр применяется post-factum (城区 фильтрует сервер СДЭК)
    if ($bbox && count($bbox) === 4) {
        [$minLon, $minLat, $maxLon, $maxLat] = $bbox;
        $pvzData['items'] = array_filter($pvzData['items'], function ($p) use ($minLon, $minLat, $maxLon, $maxLat) {
            [$lat, $lon] = $p['location'] ?? [];
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

/**
 * Загрузка ПВЗ с пагинацией через /v2/deliverypoints
 * Кэш: ключ = md5(country|page|size), TTL 1 час
 */
function pvzLoadFromCdek(string $country, int $page, int $size): array {
    $cacheDir  = __DIR__ . '/pvz_cache';
    $cacheMax  = 3600;
    $cacheKey  = md5("{$country}|{$page}|{$size}");
    $cacheFile = $cacheDir . '/' . $cacheKey . '.json';

    if (!is_dir($cacheDir)) {
        @mkdir($cacheDir, 0755, true);
    }

    if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheMax) {
        $dec = json_decode(file_get_contents($cacheFile), true);
        if (is_array($dec)) return $dec;
    }

    // Запрос к официальному API СДЭК с пагинацией и фильтрами
    $token = cdekGetToken();
    if ($token) {
        $query = http_build_query([
            'country_code' => $country,
            'type'         => 'PVZ',
            'is_handout'   => 'true',
            'page'         => $page,
            'size'         => $size,
        ]);
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
        'city_code'       => $p['city_code']     ?? $p['city_uuid'] ?? '',
        'city'           => $p['city']           ?? '',
        'type'           => $p['type']           ?? 'PVZ',
        'postal_code'    => $p['postal_code']    ?? '',
        'country_code'   => $p['country_code']   ?? 'RU',
        'region'         => $p['region']         ?? '',
        'have_cashless'  => $p['have_cashless']  ?? true,
        'have_cash'      => $p['have_cash']       ?? true,
        'allowed_cod'    => $p['allowed_cod']    ?? true,
        'is_dressing_room' => $p['is_dressing_room'] ?? false,
        'code'           => $p['code']            ?? '',
        'name'           => $p['name']            ?? ($p['code'] ?? ''),
        'address'        => $p['address']        ?? '',
        'work_time'      => $p['work_time']      ?? '',
        'location'       => [
            $loc[0] ?? 0.0,
            $loc[1] ?? 0.0,
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
    global $CONFIG;

    if (!$fromCity || !$toPvzCode) {
        throw new InvalidArgumentException('from_city and to_pvz_code are required');
    }

    // --- 1. Определяем city_code города-отправителя ---
    $geo = handleGeocode($fromCity);
    if (empty($geo['city_code'])) {
        // Пробуем из PVZ по коду
        $pvzAll = pvzLoadFromCdek();
        $target = null;
        foreach ($pvzAll as $p) {
            if (($p['code'] ?? '') == $toPvzCode) {
                $target = $p;
                break;
            }
        }

        $fromCode = kladrRegionCode($geo['city'] ?? $fromCity);
        $toCode   = $target['city_code'] ?? $toPvzCode;
    } else {
        $fromCode = $geo['city_code'];
        // КЛАДР code для получателя — из PVZ
        $pvzAll   = pvzLoadFromCdek();
        $toCode   = null;
        foreach ($pvzAll as $p) {
            if (($p['code'] ?? '') == $toPvzCode) {
                $toCode = $p['city_code'] ?? null;
                break;
            }
        }
        if (!$toCode) $toCode = $toPvzCode;
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
            'delivery_sum' => null,
            'period_min'   => null,
            'period_max'   => null,
            'tariff_name'  => null,
            'tariff_code'  => null,
        ];
    }

    $payload = [
        'type'          => 1,                               // забор груза
        'date'          => date('Y-m-d'),
        'currency'      => 1,                               // рубли
        'from_location' => ['code' => $fromCode],
        'to_location'   => ['code' => $toCode],
        'packages'      => [['items' => $items]],
    ];

    $ch = curl_init('https://api.cdek.ru/v2/calculator/tarifflist');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST          => true,
        CURLOPT_HTTPHEADER    => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $token,
        ],
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_TIMEOUT    => 15,
    ]);

    $resp = curlExecJson($ch);

    // tarifflist возвращает массив тарифов — берём первый (самый быстрый/дешёвый)
    if (is_array($resp) && isset($resp[0])) {
        $tariff = $resp[0];
        return [
            'delivery_sum' => $tariff['total_sum']      ?? null,
            'period_min'   => $tariff['period_min']    ?? null,
            'period_max'   => $tariff['period_max']    ?? null,
            'tariff_name'  => $tariff['tariff_name']   ?? null,
            'tariff_code'  => $tariff['tariff_code']   ?? null,
        ];
    }

    // одиночный ответ (старый формат /calculator/tariff)
    if (is_array($resp) && !isset($resp[0])) {
        return [
            'delivery_sum' => $resp['total_sum']      ?? null,
            'period_min'   => $resp['period_min']    ?? null,
            'period_max'   => $resp['period_max']    ?? null,
            'tariff_name'  => $resp['tariff_name']   ?? null,
            'tariff_code'  => $resp['tariff_code']   ?? null,
        ];
    }

    return [
        'error'        => 'Empty response from CDEK',
        'delivery_sum' => null,
        'period_min'   => null,
        'period_max'   => null,
        'tariff_name'  => null,
        'tariff_code'  => null,
    ];
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
