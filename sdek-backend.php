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
    'DADATA_TOKEN' => getenv('DADATA_API_KEY') ?: 'YOUR_DADATA_TOKEN',  // Token из ЛК DaData
    'DADATA_SECRET'=> getenv('DADATA_SECRET')  ?: 'YOUR_DADATA_SECRET', // Secret (для подсказок, опц.)

    // СДЭК OAuth2 (https://www.cdek.ru/api/)
    'CDEK_CLIENT_ID'     => getenv('SDEK_CLIENT_ID')     ?: 'YOUR_CDEK_CLIENT_ID',     // client_id
    'CDEK_CLIENT_SECRET' => getenv('SDEK_CLIENT_SECRET') ?: 'YOUR_CDEK_CLIENT_SECRET', // client_secret
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
            $_REQUEST['bbox'] ?? null   // [minLon,minLat,maxLon,maxLat]
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

    // Dadata suggest/address — прямое геокодирование (город → координаты + КЛАДР)
    $ch = curl_init('https://suggestions.dadata.ru/suggestions/api/4_1/rs/suggest/address');
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
    $dCity = trim($d['city'] ?? $d['settlement'] ?? '');

    // Dadata может вернуть область/район вместо города ("Челябинская обл" вместо "Челябинск")
    // Если returned city не похож на query — пытаемся найти более точный результат
    if ($dCity && mb_stripos($dCity, $query) !== 0 && mb_stripos($query, $dCity) !== 0) {
        // Город в ответе не совпадает с запросом — попробуем взять следующую подсказку
        if (count($suggestions) > 1) {
            $d = $suggestions[1]['data'] ?? [];
            $dCity = trim($d['city'] ?? $d['settlement'] ?? '');
        }
        // Если всё ещё не совпадает — доверяем Dadata, но логируем
        if ($dCity && mb_stripos($dCity, $query) !== 0 && mb_stripos($query, $dCity) !== 0) {
            file_put_contents(__DIR__ . '/geocode_debug.log',
                date('Y-m-d H:i:s') . " FUZZY_MISMATCH {$query} vs {$dCity} | raw: " . substr(json_encode($suggestions[0] ?? [], JSON_UNESCAPED_UNICODE), 0, 300) . "\n",
                FILE_APPEND);
        }
    }

    $result = [
        'lat'       => $d['geo_lat']    ?? null,
        'lon'       => $d['geo_lon']    ?? null,
        'city'      => $dCity ?: $query,
        'city_code' => $d['city_kladr_id'] ?? null,
    ];

    // КЛАДР-код Dadata не совпадает с кодом города CDEK — ищем в PVZ cache
    $cdekCityCode = findCdekCityCode($result['city'] ?? $query);
    if ($cdekCityCode) {
        $result['city_code'] = (string) $cdekCityCode;
    }

    file_put_contents(__DIR__ . '/geocode_debug.log',
        date('Y-m-d H:i:s') . " {$query} => " . json_encode($result, JSON_UNESCAPED_UNICODE)
        . " | raw: " . substr(json_encode($suggestions[0] ?? [], JSON_UNESCAPED_UNICODE), 0, 500) . "\n",
        FILE_APPEND);

    return $result;
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

/**
 * Найти city_code CDEK по имени города, используя кэш ПВЗ
 * (КЛАДР-коды Dadata не совпадают с кодами CDEK — ищем в PVZ cache)
 */
function findCdekCityCode(string $cityName): ?int {
    $cacheFile = __DIR__ . '/pvz_cache.json';
    if (!file_exists($cacheFile)) return null;

    $raw = file_get_contents($cacheFile);
    $pvzList = json_decode($raw, true);
    if (!is_array($pvzList)) return null;

    $normalized = trim(mb_strtolower($cityName));

    foreach ($pvzList as $p) {
        // Поддержка двух форматов кэша: топ-level city (старый) и location.city (новый)
        $pCity = trim(mb_strtolower($p['city'] ?? ($p['location']['city'] ?? '')));
        if (!$pCity) continue;

        $code = (int) ($p['city_code'] ?? $p['location']['city_code'] ?? null);
        if (!$code) continue;

        // Точное совпадение
        if ($pCity === $normalized) {
            file_put_contents(__DIR__ . '/geocode_debug.log',
                date('Y-m-d H:i:s') . " findCdekCityCode EXACT '{$cityName}' => {$code} ({$pCity})\n",
                FILE_APPEND);
            return $code;
        }
    }

    // Частичное совпадение: query "Челябинск" matches "Челябинск, Челябинская область"
    foreach ($pvzList as $p) {
        $pCity = trim(mb_strtolower($p['city'] ?? ($p['location']['city'] ?? '')));
        if (!$pCity) continue;

        $code = (int) ($p['city_code'] ?? $p['location']['city_code'] ?? null);
        if (!$code) continue;

        if (strpos($pCity, $normalized) === 0 || strpos($normalized, $pCity) === 0) {
            file_put_contents(__DIR__ . '/geocode_debug.log',
                date('Y-m-d H:i:s') . " findCdekCityCode PARTIAL '{$cityName}' => {$code} ({$pCity})\n",
                FILE_APPEND);
            return $code;
        }
    }

    file_put_contents(__DIR__ . '/geocode_debug.log',
        date('Y-m-d H:i:s') . " findCdekCityCode NOT_FOUND '{$cityName}'\n",
        FILE_APPEND);
    return null;
}

// ================================================================
// 2. PVZLIST
// ----------
// Вход:  country_code='RU', bbox=null|[minLon,minLat,maxLon,maxLat]
// Выход: массив ПВЗ
// ================================================================
function handlePvzList(string $country, ?array $bbox): array {
    $pvz = pvzLoadFromCdek();

    // фильтр по стране
    $pvz = array_filter($pvz, fn($p) =>
        ($p['country_code'] ?? '') === $country ||
        ($p['location']['country_code'] ?? '') === $country
    );

    // фильтр по bbox
    if ($bbox && count($bbox) === 4) {
        [$minLon, $minLat, $maxLon, $maxLat] = $bbox;
        $pvz = array_filter($pvz, function ($p) use ($minLon, $minLat, $maxLon, $maxLat) {
            list ('latitude' => $lat, 'longitude' => $lon) = $p['location'] ?? [];
            if ($lat === null || $lon === null) return false;
            return $lon >= $minLon && $lon <= $maxLon
                && $lat >= $minLat && $lat <= $maxLat;
        });
    }

    // приводим к нужному формату
    return array_values(array_map('normalizePvz', $pvz));
}

/**
 * Загрузка ПВЗ: кэш → API → CSV-fallback
 */
function pvzLoadFromCdek(): array {
    $cacheFile = __DIR__ . '/pvz_cache.json';
    $cacheMax  = 3600; // 1 час

    if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheMax) {
        $raw = file_get_contents($cacheFile);
        $dec = json_decode($raw, true);
        if (is_array($dec)) return $dec;
    }

    // Запрос к официальному API СДЭК
    $token = cdekGetToken();
    if ($token) {
        $ch = curl_init('https://api.cdek.ru/v2/deliverypoints');
        curl_setopt_array($ch, [
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_HTTPHEADER     => ['Authorization: Bearer ' . $token],
            CURLOPT_TIMEOUT        => 15,
        ]);
        $resp = curlExecJson($ch);

        if (is_array($resp) && !empty($resp)) {
            // Новый формат /v2/deliverypoints оборачивает данные в ключ 'entity'
            $flat = [];
            foreach ($resp as $item) {
                if (isset($item['entity'])) {
                    $flat[] = $item['entity'];
                } else {
                    $flat[] = $item;
                }
            }
            file_put_contents($cacheFile, json_encode($flat, JSON_UNESCAPED_UNICODE));
            return $flat;
        }
    }

    // Fallback: CSV-выгрузка с сайта СДЭК
    return pvzLoadFromCsv();
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
    // Поддержка двух форматов:
    // 1. CSV:                location=[lat, lon], address=строка, city=строка
    // 2. /v2/deliverypoints: location={latitude,longitude,address,address_full,city,...}, address=строка, city=строка
    $loc = $p['location'] ?? [];

    // location.latitude / location.longitude
    if (is_array($loc) && isset($loc[0]) && is_numeric($loc[0])) {
        // CSV формат: [lat, lon]
        $lat = $loc[0];
        $lon = $loc[1] ?? 0.0;
    } else {
        // API формат: {latitude, longitude}
        $lat = $loc['latitude']  ?? 0.0;
        $lon = $loc['longitude'] ?? 0.0;
    }

    // address — строка на верхнем уровне, либо из location.address
    $address = $p['address']
        ?? ($loc['address_full'] ?? $loc['address'] ?? '');

    // city — строка на верхнем уровне (из API), city_code — из location или корня (старый кэш)
    $cityName = $p['city'] ?? '';
    $cityCode = $loc['city_code'] ?? ($p['city_code'] ?? '');

    // postal_code — из location
    $postalCode = $loc['postal_code'] ?? $p['postal_code'] ?? '';

    // country_code — из location, region — из location
    $countryCode = $loc['country_code'] ?? $p['country_code'] ?? 'RU';
    $region      = $loc['region'] ?? $p['region'] ?? '';

    // work_time
    $workTime = $p['work_time'] ?? $p['workTime'] ?? '';

    return [
        'city_code'        => $cityCode,
        'city'            => $cityName,
        'type'            => $p['type']           ?? 'PVZ',
        'postal_code'     => $postalCode,
        'country_code'    => $countryCode,
        'region'          => $region,
        'have_cashless'   => $p['have_cashless']  ?? true,
        'have_cash'       => $p['have_cash']       ?? true,
        'allowed_cod'     => $p['allowed_cod']    ?? true,
        'is_dressing_room'=> $p['is_dressing_room'] ?? false,
        'code'            => $p['code']            ?? '',
        'name'            => $p['name']            ?? ($p['code'] ?? ''),
        'address'         => $address,
        'work_time'       => $workTime,
        'location'        => [
            (float) $lat,
            (float) $lon,
        ],
        'weight_min'      => $p['weight_min']     ?? 0,
        'weight_max'      => $p['weight_max']     ?? 100000000,
        'dimensions'      => $p['dimensions']      ?? null,
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
        throw new InvalidArgumentException("Не удалось определить код города для: {$fromCity}. Проверьте название города или настройте DADATA_TOKEN.");
    }
    $fromCode = $geo['city_code'];

    // --- 2. city_code получателя ---
    // Widget отправляет city_code напрямую (pvz.city_code || pvz.code)
    $toCode = is_numeric($toPvzCode) ? (int) $toPvzCode : null;
    if (!$toCode) {
        // Fallback: ищем по коду ПВЗ (если widget всё же отправил code вместо city_code)
        $pvzAll = pvzLoadFromCdek();
        foreach ($pvzAll as $p) {
            if (($p['code'] ?? '') == $toPvzCode) {
                $toCode = (int) ($p['city_code'] ?? null) ?: null;
                break;
            }
        }
    }
    if (!$toCode) {
        throw new InvalidArgumentException("Не удалось найти city_code для PVZ: {$toPvzCode}");
    }

    // --- 3. Собираем посылки (вес в граммах) ---
    $pkgItems = [];
    foreach ($packages ?: [[]] as $pkg) {
        $pkgItems[] = [
            'weight'  => (float) ($pkg['weight'] ?? 1000),       // граммы
            'length'  => (float) ($pkg['length'] ?? 10),
            'width'   => (float) ($pkg['width']  ?? 10),
            'height'  => (float) ($pkg['height'] ?? 10),
        ];
    }

    // --- 4. Запрос тарифа ---
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

    // Приводим коды к int32 для CDEK API
    $fromCodeInt = (int) $fromCode;
    $toCodeInt   = (int) $toCode;

    $payload = [
        'type'          => 1,                               // забор груза
        'date'          => date('Y-m-d\TH:i:sO'),  // yyyy-MM-dd'T'HH:mm:ss+HHMM
        'currency'      => 1,                               // рубли
        'from_location' => ['code' => $fromCodeInt],
        'to_location'   => ['code' => $toCodeInt],
        'packages'      => $pkgItems,
    ];

    // DEBUG: записываем запрос в лог
    file_put_contents(__DIR__ . '/tariff_debug.log',
        date('Y-m-d H:i:s') . ' REQUEST: ' . json_encode($payload, JSON_UNESCAPED_UNICODE) . "\n",
        FILE_APPEND);

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
    $out = curl_exec($ch);
    if (curl_errno($ch)) {
        error_log('cURL error: ' . curl_error($ch));
        return '';
    }
    return $out ?: '';
}
