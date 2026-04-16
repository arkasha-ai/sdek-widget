<?php
/**
 * sdek-backend.php
 * Бэкенд для виджета SdekPvzWidget
 *
 * Endpoints (параметр action):
 *   suggest   — подсказки адресов DaData
 *   geocode   — прямой геокод через DaData (fallback Nominatim)
 *   pvzlist   — список ПВЗ СДЭК (фильтр по стране, bbox)
 *   calculate — расчёт тарифа доставки до выбранного ПВЗ
 *
 * Конфигурация через env-переменные:
 *   DADATA_API_KEY, DADATA_SECRET
 *   SDEK_CLIENT_ID, SDEK_CLIENT_SECRET
 *   SDEK_ALLOWED_ORIGINS — список доменов через запятую, напр. "https://a.ru,https://b.ru" (по умолчанию "*" — небезопасно)
 *   SDEK_CACHE_DIR       — путь к директории кешей/логов (по умолчанию __DIR__)
 *   SDEK_DEBUG           — "1" включает запись в *_debug.log
 */

// ================================================================
// КОНФИГУРАЦИЯ
// ================================================================
$CONFIG = [
    'DADATA_TOKEN'       => getenv('DADATA_API_KEY')   ?: 'YOUR_DADATA_TOKEN',
    'DADATA_SECRET'      => getenv('DADATA_SECRET')    ?: 'YOUR_DADATA_SECRET',
    'CDEK_CLIENT_ID'     => getenv('SDEK_CLIENT_ID')   ?: 'YOUR_CDEK_CLIENT_ID',
    'CDEK_CLIENT_SECRET' => getenv('SDEK_CLIENT_SECRET') ?: 'YOUR_CDEK_CLIENT_SECRET',
    'ALLOWED_ORIGINS'    => array_filter(array_map('trim', explode(',', getenv('SDEK_ALLOWED_ORIGINS') ?: ''))),
    'CACHE_DIR'          => rtrim(getenv('SDEK_CACHE_DIR') ?: __DIR__, '/'),
    'DEBUG'              => getenv('SDEK_DEBUG') === '1',
];

if (!is_dir($CONFIG['CACHE_DIR'])) {
    @mkdir($CONFIG['CACHE_DIR'], 0755, true);
}

// ================================================================
// Утилиты: пути, атомарная запись, логи
// ================================================================
function cachePath(string $name): string {
    global $CONFIG;
    return $CONFIG['CACHE_DIR'] . '/' . $name;
}

/**
 * Атомарная запись с эксклюзивной блокировкой.
 * Пишем во временный файл + rename — чтобы читатели не видели половину JSON.
 */
function atomicWrite(string $path, string $content): bool {
    $tmp = $path . '.tmp.' . bin2hex(random_bytes(4));
    if (file_put_contents($tmp, $content, LOCK_EX) === false) {
        return false;
    }
    return rename($tmp, $path);
}

function debugLog(string $file, string $message): void {
    global $CONFIG;
    if (!$CONFIG['DEBUG']) return;
    @file_put_contents(cachePath($file), date('Y-m-d H:i:s') . ' ' . $message . "\n", FILE_APPEND | LOCK_EX);
}

// ================================================================
// Геокод-кеш (24 часа, city_name → {lat, lon, city, city_code})
// ================================================================
function geocodeCacheGet(string $query): ?array {
    $cacheFile = cachePath('geocode_cache.json');
    if (!file_exists($cacheFile)) return null;

    $raw = file_get_contents($cacheFile);
    $cache = json_decode($raw, true);
    if (!is_array($cache)) return null;

    $key = mb_strtolower(trim($query));
    if (!isset($cache[$key])) return null;

    $entry = $cache[$key];
    if (($entry['_cached_at'] ?? 0) + 86400 < time()) {
        return null;
    }

    unset($entry['_cached_at']);
    return $entry;
}

function geocodeCacheSet(string $query, array $data): void {
    $cacheFile = cachePath('geocode_cache.json');
    $cache = [];
    if (file_exists($cacheFile)) {
        $cache = json_decode(file_get_contents($cacheFile), true) ?: [];
    }

    // Эвикция протухших записей во время записи (TTL 24ч)
    $now = time();
    foreach ($cache as $k => $entry) {
        if (!is_array($entry) || ($entry['_cached_at'] ?? 0) + 86400 < $now) {
            unset($cache[$k]);
        }
    }

    $key = mb_strtolower(trim($query));
    $cache[$key] = $data + ['_cached_at' => $now];

    atomicWrite($cacheFile, json_encode($cache, JSON_UNESCAPED_UNICODE));
}

// ================================================================
// Заголовки (CORS — whitelist из env)
// ================================================================
header('Content-Type: application/json; charset=utf-8');

$origin = $_SERVER['HTTP_ORIGIN'] ?? '';
if ($CONFIG['ALLOWED_ORIGINS']) {
    if (in_array($origin, $CONFIG['ALLOWED_ORIGINS'], true)) {
        header("Access-Control-Allow-Origin: $origin");
        header('Vary: Origin');
    }
    // Иначе CORS-заголовок не выставляется — браузер заблокирует.
} else {
    // Пустой whitelist = открытый режим (dev). В проде указывать SDEK_ALLOWED_ORIGINS.
    header('Access-Control-Allow-Origin: *');
}
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');

if (($_SERVER['REQUEST_METHOD'] ?? 'GET') === 'OPTIONS') {
    http_response_code(204);
    exit;
}

// ================================================================
// Роутер
// ================================================================
$action = $_REQUEST['action'] ?? '';

try {
    $result = match ($action) {
        'suggest'   => handleSuggest(
            $_REQUEST['query'] ?? '',
            (isset($_REQUEST['lat']) && $_REQUEST['lat'] !== '') ? (float) $_REQUEST['lat'] : null,
            (isset($_REQUEST['lon']) && $_REQUEST['lon'] !== '') ? (float) $_REQUEST['lon'] : null
        ),
        'geocode'   => handleGeocode($_REQUEST['query'] ?? ''),
        'reverse_geocode' => handleReverseGeocode(
            (float) ($_REQUEST['lat'] ?? 0),
            (float) ($_REQUEST['lon'] ?? 0)
        ),
        'pvzlist'   => handlePvzList(
            $_REQUEST['country_code'] ?? 'RU',
            $_REQUEST['bbox'] ?? null
        ),
        'calculate' => handleCalculate(
            $_REQUEST['from_city']    ?? '',
            $_REQUEST['to_pvz_code'] ?? '',
            json_decode($_REQUEST['packages'] ?? '[]', true) ?: []
        ),
        '' => ['status' => 'ok', 'actions' => ['suggest','geocode','reverse_geocode','pvzlist','calculate']],
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

    return [
        'city_kladr_id'   => $d['city_kladr_id']   ?? null,
        'region_kladr_id' => $d['region_kladr_id'] ?? null,
        'city'            => $d['city']            ?? null,
        'region'          => $d['region']          ?? null,
    ];
}

// ================================================================
// 0b. REVERSE GEOCODE (для режима "до двери")
// --------
// Вход:  lat, lon — координаты клика на карте
// Выход: { address, city, city_code, precision }
// ================================================================
function handleReverseGeocode(float $lat, float $lon): array {
    global $CONFIG;

    if ($lat == 0 && $lon == 0) {
        throw new InvalidArgumentException('lat and lon are required');
    }

    $token = $CONFIG['DADATA_TOKEN'];
    if (!$token || str_starts_with($token, 'YOUR_')) {
        // Fallback: Nominatim reverse
        return reverseGeocodeNominatim($lat, $lon);
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
            'lat'   => $lat,
            'lon'   => $lon,
            'count' => 1,
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    $d = $resp['suggestions'][0]['data'] ?? [];

    if (empty($d)) {
        return reverseGeocodeNominatim($lat, $lon);
    }

    $cityName = $d['city'] ?? $d['settlement'] ?? '';
    $cdekCityCode = findCdekCityCode($cityName);

    // Определяем точность: house > street > settlement > city
    $precision = 'city';
    if (!empty($d['house'])) $precision = 'house';
    elseif (!empty($d['street'])) $precision = 'street';
    elseif (!empty($d['settlement'])) $precision = 'settlement';

    return [
        'address'   => $resp['suggestions'][0]['value'] ?? '',
        'city'      => $cityName,
        'city_code' => $cdekCityCode ? (string) $cdekCityCode : ($d['city_kladr_id'] ?? null),
        'precision' => $precision,
        'lat'       => $d['geo_lat'] ?? $lat,
        'lon'       => $d['geo_lon'] ?? $lon,
    ];
}

function reverseGeocodeNominatim(float $lat, float $lon): array {
    $url = "https://nominatim.openstreetmap.org/reverse?lat={$lat}&lon={$lon}&format=json&zoom=18";
    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_HTTPHEADER     => ['User-Agent: SdekWidget/1.0'],
        CURLOPT_TIMEOUT        => 8,
    ]);
    $resp = curlExecJson($ch);

    return [
        'address'   => $resp['display_name'] ?? '',
        'city'      => $resp['address']['city'] ?? $resp['address']['town'] ?? '',
        'city_code' => null,
        'precision' => !empty($resp['address']['house_number']) ? 'house' : 'street',
        'lat'       => $resp['lat'] ?? $lat,
        'lon'       => $resp['lon'] ?? $lon,
    ];
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

    $cached = geocodeCacheGet($query);
    if ($cached !== null) {
        return $cached;
    }

    $token = $CONFIG['DADATA_TOKEN'];
    if (!$token || str_starts_with($token, 'YOUR_')) {
        $result = geocodeNominatim($query);
        // Nominatim не знает CDEK-коды — ищем в PVZ-кеше
        if (empty($result['city_code'])) {
            $cdekCode = findCdekCityCode($result['city'] ?: $query);
            if ($cdekCode) $result['city_code'] = (string) $cdekCode;
        }
        geocodeCacheSet($query, $result);
        return $result;
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
            'query'     => $query,
            'count'     => 1,
            'locations' => [['country' => 'Россия']],
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

    // Dadata может вернуть область/район вместо города. Если не совпадает — берём вторую подсказку.
    if ($dCity && mb_stripos($dCity, $query) !== 0 && mb_stripos($query, $dCity) !== 0) {
        if (count($suggestions) > 1) {
            $d = $suggestions[1]['data'] ?? [];
            $dCity = trim($d['city'] ?? $d['settlement'] ?? '');
        }
        if ($dCity && mb_stripos($dCity, $query) !== 0 && mb_stripos($query, $dCity) !== 0) {
            debugLog('geocode_debug.log', "FUZZY_MISMATCH {$query} vs {$dCity} | raw: " . substr(json_encode($suggestions[0] ?? [], JSON_UNESCAPED_UNICODE), 0, 300));
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

    geocodeCacheSet($query, $result);

    debugLog('geocode_debug.log', "{$query} => " . json_encode($result, JSON_UNESCAPED_UNICODE) . " | raw: " . substr(json_encode($suggestions[0] ?? [], JSON_UNESCAPED_UNICODE), 0, 500));

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
 */
function findCdekCityCode(string $cityName): ?int {
    $cacheFile = cachePath('pvz_cache.json');
    if (!file_exists($cacheFile)) return null;

    $raw = file_get_contents($cacheFile);
    $pvzList = json_decode($raw, true);
    if (!is_array($pvzList)) return null;

    $normalized = trim(mb_strtolower($cityName));

    foreach ($pvzList as $p) {
        $pCity = trim(mb_strtolower($p['city'] ?? ($p['location']['city'] ?? '')));
        if (!$pCity) continue;

        $code = (int) ($p['city_code'] ?? $p['location']['city_code'] ?? null);
        if (!$code) continue;

        if ($pCity === $normalized) {
            debugLog('geocode_debug.log', "findCdekCityCode EXACT '{$cityName}' => {$code} ({$pCity})");
            return $code;
        }
    }

    foreach ($pvzList as $p) {
        $pCity = trim(mb_strtolower($p['city'] ?? ($p['location']['city'] ?? '')));
        if (!$pCity) continue;

        $code = (int) ($p['city_code'] ?? $p['location']['city_code'] ?? null);
        if (!$code) continue;

        if (strpos($pCity, $normalized) === 0 || strpos($normalized, $pCity) === 0) {
            debugLog('geocode_debug.log', "findCdekCityCode PARTIAL '{$cityName}' => {$code} ({$pCity})");
            return $code;
        }
    }

    debugLog('geocode_debug.log', "findCdekCityCode NOT_FOUND '{$cityName}'");
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

    $pvz = array_filter($pvz, fn($p) =>
        ($p['country_code'] ?? '') === $country ||
        ($p['location']['country_code'] ?? '') === $country
    );

    if ($bbox && count($bbox) === 4) {
        [$minLon, $minLat, $maxLon, $maxLat] = $bbox;
        $pvz = array_filter($pvz, function ($p) use ($minLon, $minLat, $maxLon, $maxLat) {
            // Поддержка двух форматов location:
            //   - API /v2/deliverypoints: { latitude, longitude }
            //   - CSV-fallback: [lat, lon] индексированный
            $loc = $p['location'] ?? null;
            if (!is_array($loc)) return false;
            if (isset($loc['latitude'], $loc['longitude'])) {
                $lat = $loc['latitude'];
                $lon = $loc['longitude'];
            } elseif (isset($loc[0], $loc[1])) {
                $lat = $loc[0];
                $lon = $loc[1];
            } else {
                return false;
            }
            if (!is_numeric($lat) || !is_numeric($lon)) return false;
            return $lon >= $minLon && $lon <= $maxLon
                && $lat >= $minLat && $lat <= $maxLat;
        });
    }

    return array_values(array_map('normalizePvz', $pvz));
}

/**
 * Загрузка ПВЗ: кэш → API → CSV-fallback
 */
function pvzLoadFromCdek(): array {
    $cacheFile = cachePath('pvz_cache.json');
    $cacheMax  = 3600;

    if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheMax) {
        $raw = file_get_contents($cacheFile);
        $dec = json_decode($raw, true);
        if (is_array($dec)) return $dec;
    }

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
            $flat = [];
            foreach ($resp as $item) {
                $flat[] = $item['entity'] ?? $item;
            }
            atomicWrite($cacheFile, json_encode($flat, JSON_UNESCAPED_UNICODE));
            return $flat;
        }
    }

    return pvzLoadFromCsv();
}

/**
 * CSV-fallback — официальная выгрузка
 * https://www.cdek.ru/csv/directory-of-goods-issue-points.csv
 */
function pvzLoadFromCsv(): array {
    $csvUrl = 'https://www.cdek.ru/csv/directory-of-goods-issue-points.csv';
    $cacheFile = cachePath('pvz_csv_cache.json');
    $cacheMax  = 86400;

    if (file_exists($cacheFile) && (time() - filemtime($cacheFile)) < $cacheMax) {
        $dec = json_decode(file_get_contents($cacheFile), true);
        if (is_array($dec)) return $dec;
    }

    $ch = curl_init($csvUrl);
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 20,
        CURLOPT_FOLLOWLOCATION => true,
    ]);

    $csv = curlExecRaw($ch);
    curl_close($ch);

    if (!$csv) return [];

    $lines = explode("\n", trim($csv));
    if (count($lines) < 2) return [];

    $headers = str_getcsv(array_shift($lines), ';');
    $idx = array_flip(array_map('trim', $headers));

    $pvz = [];
    foreach ($lines as $line) {
        if (!trim($line)) continue;
        $v = str_getcsv($line, ';');
        $lat = trim($v[$idx['Latitude']  ?? 7]  ?? '');
        $lon = trim($v[$idx['Longitude'] ?? 8]  ?? '');
        $pvz[] = [
            'code'            => $v[$idx['Code']         ?? 0] ?? '',
            'name'            => $v[$idx['Name']         ?? 1] ?? '',
            'city'            => $v[$idx['City']         ?? 2] ?? '',
            'address'         => $v[$idx['Address']      ?? 3] ?? '',
            'work_time'       => $v[$idx['WorkTime']     ?? 4] ?? '',
            'country_code'    => 'RU',
            'location'        => [
                is_numeric($lat) ? (float) $lat : 0.0,
                is_numeric($lon) ? (float) $lon : 0.0,
            ],
            'have_cash'       => ($v[$idx['IsCash']      ?? 9]  ?? '') === '1',
            'have_cashless'   => ($v[$idx['IsImposed']   ?? 10] ?? '') === '1',
            'allowed_cod'     => true,
            'is_dressing_room'=> ($v[$idx['DressingRoom'] ?? 11] ?? '') === '1',
        ];
    }

    atomicWrite($cacheFile, json_encode($pvz, JSON_UNESCAPED_UNICODE));

    return $pvz;
}

/**
 * Приведение записи ПВЗ к единому формату
 */
function normalizePvz(array $p): array {
    $loc = $p['location'] ?? [];

    if (is_array($loc) && isset($loc[0]) && is_numeric($loc[0])) {
        $lat = $loc[0];
        $lon = $loc[1] ?? 0.0;
    } else {
        $lat = $loc['latitude']  ?? 0.0;
        $lon = $loc['longitude'] ?? 0.0;
    }

    $address = $p['address'] ?? ($loc['address_full'] ?? $loc['address'] ?? '');
    $cityName = $p['city'] ?? ($loc['city'] ?? '');
    $cityCode = $loc['city_code'] ?? ($p['city_code'] ?? '');
    $postalCode = $loc['postal_code'] ?? $p['postal_code'] ?? '';
    $countryCode = $loc['country_code'] ?? $p['country_code'] ?? 'RU';
    $region = $loc['region'] ?? $p['region'] ?? '';
    $workTime = $p['work_time'] ?? $p['workTime'] ?? '';

    return [
        'city_code'        => $cityCode,
        'city'             => $cityName,
        'type'             => $p['type'] ?? 'PVZ',
        'postal_code'      => $postalCode,
        'country_code'     => $countryCode,
        'region'           => $region,
        'have_cashless'    => $p['have_cashless']    ?? true,
        'have_cash'        => $p['have_cash']        ?? true,
        'allowed_cod'      => $p['allowed_cod']      ?? true,
        'is_dressing_room' => $p['is_dressing_room'] ?? false,
        'code'             => $p['code'] ?? '',
        'name'             => $p['name'] ?? ($p['code'] ?? ''),
        'address'          => $address,
        'work_time'        => $workTime,
        'location'         => [(float) $lat, (float) $lon],
        'weight_min'       => $p['weight_min'] ?? 0,
        'weight_max'       => $p['weight_max'] ?? 100000000,
        'dimensions'       => $p['dimensions'] ?? null,
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

    // --- 1. city_code отправителя ---
    $geo = handleGeocode($fromCity);
    if (empty($geo['city_code'])) {
        throw new InvalidArgumentException("Не удалось определить код города для: {$fromCity}. Проверьте название города или настройте DADATA_TOKEN.");
    }
    $fromCode = $geo['city_code'];

    // --- 2. city_code получателя ---
    // Widget шлёт pvz.city_code || pvz.code; если пришёл code — ищем city_code в кеше
    $toCode = is_numeric($toPvzCode) ? (int) $toPvzCode : null;
    if (!$toCode) {
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

    // --- 3. Посылки (вес в граммах) ---
    $pkgItems = [];
    foreach ($packages ?: [[]] as $pkg) {
        $pkgItems[] = [
            'weight' => (float) ($pkg['weight'] ?? 1000),
            'length' => (float) ($pkg['length'] ?? 10),
            'width'  => (float) ($pkg['width']  ?? 10),
            'height' => (float) ($pkg['height'] ?? 10),
        ];
    }

    // --- 4. Запрос тарифа ---
    $token = cdekGetToken();
    if (!$token) {
        // Dev-mode: мок-тарифы без ключей СДЭК (в проде задать SDEK_CLIENT_ID/SECRET)
        return ['tariff_codes' => [
            ['tariff_code' => 136, 'tariff_name' => 'Посылка склад-склад',    'delivery_sum' => 350, 'period_min' => 3, 'period_max' => 5, 'delivery_mode' => 2],
            ['tariff_code' => 137, 'tariff_name' => 'Посылка склад-дверь',     'delivery_sum' => 450, 'period_min' => 3, 'period_max' => 5, 'delivery_mode' => 1],
            ['tariff_code' => 233, 'tariff_name' => 'Экономичная посылка',     'delivery_sum' => 250, 'period_min' => 5, 'period_max' => 8, 'delivery_mode' => 2],
            ['tariff_code' => 234, 'tariff_name' => 'Экономичная до двери',    'delivery_sum' => 320, 'period_min' => 5, 'period_max' => 8, 'delivery_mode' => 1],
        ]];
    }

    $payload = [
        'type'          => 1,
        'date'          => date('Y-m-d\TH:i:sO'),
        'currency'      => 1,
        'from_location' => ['code' => (int) $fromCode],
        'to_location'   => ['code' => (int) $toCode],
        'packages'      => $pkgItems,
    ];

    debugLog('tariff_debug.log', 'REQUEST: ' . json_encode($payload, JSON_UNESCAPED_UNICODE));

    $ch = curl_init('https://api.cdek.ru/v2/calculator/tarifflist');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => [
            'Content-Type: application/json',
            'Authorization: Bearer ' . $token,
        ],
        CURLOPT_POSTFIELDS => json_encode($payload),
        CURLOPT_TIMEOUT    => 15,
    ]);

    $resp = curlExecJson($ch);

    debugLog('tariff_debug.log', 'RESPONSE: ' . substr(json_encode($resp, JSON_UNESCAPED_UNICODE), 0, 1000));

    if (!is_array($resp) || empty($resp)) {
        throw new RuntimeException('Empty response from CDEK');
    }

    // tarifflist: возвращаем весь массив тарифов — фронт покажет выбор
    if (isset($resp['tariff_codes']) && is_array($resp['tariff_codes'])) {
        $tariffs = [];
        foreach ($resp['tariff_codes'] as $t) {
            $sum = (float) ($t['delivery_sum'] ?? 0);
            if ($sum <= 0) continue;
            $tariffs[] = [
                'delivery_sum'  => $t['delivery_sum']  ?? null,
                'period_min'    => $t['period_min']    ?? null,
                'period_max'    => $t['period_max']    ?? null,
                'tariff_name'   => $t['tariff_name']   ?? null,
                'tariff_code'   => $t['tariff_code']   ?? null,
                'delivery_mode' => $t['delivery_mode'] ?? null,
            ];
        }
        // Сортируем по цене
        usort($tariffs, fn($a, $b) => ($a['delivery_sum'] ?? 0) <=> ($b['delivery_sum'] ?? 0));
        return ['tariff_codes' => $tariffs];
    }

    // Старый формат /calculator/tariff — одиночный ответ → оборачиваем в массив
    if (!isset($resp[0]) && isset($resp['total_sum'])) {
        return ['tariff_codes' => [[
            'delivery_sum'  => $resp['total_sum']    ?? null,
            'period_min'    => $resp['period_min']   ?? null,
            'period_max'    => $resp['period_max']   ?? null,
            'tariff_name'   => $resp['tariff_name']  ?? null,
            'tariff_code'   => $resp['tariff_code']  ?? null,
            'delivery_mode' => $resp['delivery_mode'] ?? null,
        ]]];
    }

    throw new RuntimeException('Unexpected CDEK response format');
}

// ================================================================
// OAuth-токен СДЭК (кеширование в файл)
// ================================================================
function cdekGetToken(): ?string {
    global $CONFIG;
    $cacheFile = cachePath('cdek_token.json');

    $cached = @json_decode(@file_get_contents($cacheFile) ?: '', true);
    if ($cached && ($cached['expires_at'] ?? 0) > time() + 120) {
        return $cached['access_token'];
    }

    $clientId     = $CONFIG['CDEK_CLIENT_ID']     ?? '';
    $clientSecret = $CONFIG['CDEK_CLIENT_SECRET'] ?? '';

    if (!$clientId || str_starts_with($clientId, 'YOUR_')) {
        return null;
    }

    $ch = curl_init('https://api.cdek.ru/v2/oauth/token');
    curl_setopt_array($ch, [
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_POST           => true,
        CURLOPT_HTTPHEADER     => ['Content-Type: application/x-www-form-urlencoded'],
        CURLOPT_POSTFIELDS     => http_build_query([
            'grant_type'    => 'client_credentials',
            'client_id'     => $clientId,
            'client_secret' => $clientSecret,
        ]),
        CURLOPT_TIMEOUT => 10,
    ]);

    $resp = curlExecJson($ch);
    curl_close($ch);

    if (empty($resp['access_token'])) return null;

    atomicWrite($cacheFile, json_encode([
        'access_token' => $resp['access_token'],
        'expires_at'   => time() + ($resp['expires_in'] ?? 3600),
    ]));

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
