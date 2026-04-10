<template>
  <div class="sdwo-map-col">
    <!-- Поиск с подсказками Dadata -->
    <div class="sdwo-search-row">
      <div class="sdwo-search-wrap">
        <input
          v-model="query"
          type="text"
          class="sdwo-input"
          placeholder="Поиск адреса…"
          autocomplete="off"
          @input="onSearchInput"
          @keydown.down.prevent="onKeyDown"
          @keydown.up.prevent="onKeyUp"
          @keydown.enter.prevent="onKeyEnter"
          @keydown.escape="closeDropdown"
          @blur="onBlur"
          @focus="onFocus"
        />
        <!-- Выпадающий список -->
        <ul v-if="suggestions.length" class="sdwo-suggest-dropdown">
          <li
            v-for="(s, i) in suggestions"
            :key="i"
            :class="{ 'sdwo-suggest-active': i === activeIdx }"
            @mousedown.prevent="selectSuggestion(s)"
            @mouseenter="activeIdx = i"
          >
            <span class="sdwo-suggest-value">{{ s.value }}</span>
          </li>
        </ul>
      </div>
      <div v-if="searchError" class="sdwo-error">{{ searchError }}</div>
    </div>

    <!-- OpenLayers карта -->
    <div class="sdwo-map" ref="mapContainerRef" style="width:100%;min-height:300px;" />
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue';
import Map from 'ol/Map';
import View from 'ol/View';
import TileLayer from 'ol/layer/Tile';
import VectorLayer from 'ol/layer/Vector';
import OSM from 'ol/source/OSM';
import VectorSource from 'ol/source/Vector';
import Cluster from 'ol/source/Cluster';
import Feature from 'ol/Feature';
import Point from 'ol/geom/Point';
import { fromLonLat, toLonLat } from 'ol/proj';
import { Style, Circle, Stroke, Fill, Text, Icon } from 'ol/style';

const props = defineProps({
  center:      { type: Array,  default: null },
  zoom:        { type: Number, default: 12 },
  markers:     { type: Array,  default: () => [] },
  activeCode: { type: String, default: null },
  backendUrl:  { type: String, default: '' },
});

const emit = defineEmits(['search', 'moveend', 'markerselect']);

// Refs
const mapContainerRef = ref(null);
const query           = ref('');
const searchError     = ref(null);
const mapRef          = ref(null);
const suggestions     = ref([]);
const activeIdx       = ref(-1);
const isOpen          = ref(false);

let searchTimer  = null;
let vectorSource = null;
let clusterSource = null;

// SVG-иконки ПВЗ (CDEK-стиль) — normal и active
const ICON_NORMAL = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyOCIgaGVpZ2h0PSIzNiIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iIzFhYjI0OCIgZD0iTTI4IDE0LjM0NGExNC41NSAxNC41NSAwIDAgMS0yLjEyIDcuNTk0QzIwLjIgMzEuMjQ1IDE0IDM2IDE0IDM2UzcuOCAzMS4yNDUgMi4xMiAyMS45MzhBMTQuNTQgMTQuNTQgMCAwIDEgMCAxNC4zNDNDMCA2LjQyMiA2LjI2OCAwIDE0IDBzMTQgNi40MjIgMTQgMTQuMzQ0Ii8+PHJlY3Qgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB4PSIzIiB5PSIzIiBmaWxsPSIjZmZmIiByeD0iMTEiLz48cGF0aCBmaWxsPSIjMWFiMjQ4IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0yMC43OTQgMTcuNjI0aC0uODE0Yy4xODQuMzA0LjI5Mi42NTYuMjkyIDEuMDMzIDAgMS4xMzgtLjk2OSAyLjA2NS0yLjE2IDIuMDY1LTEuMTkgMC0yLjE2LS45MjctMi4xNi0yLjA2NSAwLS4zNzcuMTA4LS43MjkuMjkzLTEuMDMzaC0yLjU2NGMuMTg1LjMwNC4yOTIuNjU2LjI5MiAxLjAzMyAwIDEuMTM4LS45NjggMi4wNjUtMi4xNTkgMi4wNjVzLTIuMTYtLjkyNy0yLjE2LTIuMDY1YzAtLjM3Ny4xMDgtLjcyOS4yOTMtMS4wMzNoLS44MjNhLjUzLjUzIDAgMCAxLS41NC0uNTE2bC0uMDEtNy4xMjQtMS43NS0xLjY3NGEuNS41IDAgMCAxIDAtLjczLjU2LjU2IDAgMCAxIC43NjQgMGwxLjkyNyAxLjg0M2MuMDA4LjAwNy4wMS4wMTYuMDE2LjAyNGEuNS41IDAgMCAxIC4wNTkuMDgzLjUuNSAwIDAgMSAuMDY0LjM0OWwuMDEgNi43MTJoMTEuMTNhLjUzLjUzIDAgMCAxIC41NC41MTcuNTMuNTMgMCAwIDEtLjU0LjUxNm0tOC45OCAwYy0uNTk1IDAtMS4wOC40NjMtMS4wOCAxLjAzM3MuNDg1IDEuMDMyIDEuMDggMS4wMzIgMS4wOC0uNDYzIDEuMDgtMS4wMzJjMC0uNTctLjQ4NS0xLjAzMy0xLjA4LTEuMDMzbTUuMjE4IDEuMDMzYzAgLjU2OS40ODUgMS4wMzIgMS4wOCAxLjAzMnMxLjA4LS40NjMgMS4wOC0xLjAzMmMwLS41Ny0uNDg0LTEuMDMzLTEuMDgtMS4wMzMtLjU5NSAwLTEuMDguNDYzLTEuMDggMS4wMzNtMi42ODItMy4wOThoLTguNDc2YS41My41MyAwIDAgMS0uNTQtLjUxN1Y3Ljc5M2MwLS4yODUuMjQyLS41MTYuNTQtLjUxNmg0LjgwNWwzLjY3MS4wMmMuMjk4IDAgLjU0LjIzMS41NC41MTZ2Ny4yM2EuNTMuNTMgMCAwIDEtLjU0LjUxNm0tLjU0LTcuMjMtMy4xMzEtLjAydjEuNTVhLjUzLjUzIDAgMCAxLS41NC41MTYuNTMuNTMgMCAwIDEtLjU0LS41MTZ2LTEuNTVoLTMuMTg1djYuMjE3aDcuMzk2eiIgY2xpcC1ydWxlPSJldmVub2RkIi8+PHJlY3Qgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB4PSIzIiB5PSIzIiBmaWxsPSIjZmZmIiByeD0iMTEiLz48cmVjdCB3aWR0aD0iMjIiIGhlaWdodD0iMjIiIHg9IjMiIHk9IjMiIGZpbGw9IiNmZmYiIHJ4PSIxMSIvPjxwYXRoIHN0cm9rZT0iIzFhYjI0OCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBzdHJva2Utd2lkdGg9IjEuMiIgZD0iTTggMTloMTJNOS4zMzMgMTlWOS42NjdMMTQuNjY3IDd2MTJtNCAwdi02LjY2N2wtNC0yLjY2Nk0xMiAxMXYuMDA3TTEyIDEzdi4wMDdNMTIgMTV2LjAwN00xMiAxN3YuMDA3Ii8+PC9zdmc+';
const ICON_ACTIVE = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyOCIgaGVpZ2h0PSIzNiIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iIzFhYjI0OCIgZD0iTTI4IDE0LjM0NGExNC41NSAxNC41NSAwIDAgMS0yLjEyIDcuNTk0QzIwLjIgMzEuMjQ1IDE0IDM2IDE0IDM2UzcuOCAzMS4yNDUgMi4xMiAyMS45MzhBMTQuNTQgMTQuNTQgMCAwIDEgMCAxNC4zNDNDMCA2LjQyMiA2LjI2OCAwIDE0IDBzMTQgNi40MjIgMTQgMTQuMzQ0Ii8+PHJlY3Qgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB4PSIzIiB5PSIzIiBmaWxsPSIjZmZmIiByeD0iMTEiLz48cGF0aCBmaWxsPSIjMWFiMjQ4IiBmaWxsLXJ1bGU9ImV2ZW5vZGQiIGQ9Ik0yMC43OTQgMTcuNjI0aC0uODE0Yy4xODQuMzA0LjI5Mi42NTYuMjkyIDEuMDMzIDAgMS4xMzgtLjk2OSAyLjA2NS0yLjE2IDIuMDY1LTEuMTkgMC0yLjE2LS45MjctMi4xNi0yLjA2NSAwLS4zNzcuMTA4LS43MjkuMjkzLTEuMDMzaC0yLjU2NGMuMTg1LjMwNC4yOTIuNjU2LjI5MiAxLjAzMyAwIDEuMTM4LS45NjggMi4wNjUtMi4xNTkgMi4wNjVzLTIuMTYtLjkyNy0yLjE2LTIuMDY1YzAtLjM3Ny4xMDgtLjcyOS4yOTMtMS4wMzNoLS44MjNhLjUzLjUzIDAgMCAxLS41NC0uNTE2bC0uMDEtNy4xMjQtMS43NS0xLjY3NGEuNS41IDAgMCAxIDAtLjczLjU2LjU2IDAgMCAxIC43NjQgMGwxLjkyNyAxLjg0M2MuMDA4LjAwNy4wMS4wMTYuMDE2LjAyNGEuNS41IDAgMCAxIC4wNTkuMDgzLjUuNSAwIDAgMSAuMDY0LjM0OWwuMDEgNi43MTJoMTEuMTNhLjUzLjUzIDAgMCAxIC41NC41MTcuNTMuNTMgMCAwIDEtLjU0LjUxNm0tOC45OCAwYy0uNTk1IDAtMS4wOC40NjMtMS4wOCAxLjAzM3MuNDg1IDEuMDMyIDEuMDggMS4wMzIgMS4wOC0uNDYzIDEuMDgtMS4wMzJjMC0uNTctLjQ4NS0xLjAzMy0xLjA4LTEuMDMzbTUuMjE4IDEuMDMzYzAgLjU2OS40ODUgMS4wMzIgMS4wOCAxLjAzMnMxLjA4LS40NjMgMS4wOC0xLjAzMmMwLS41Ny0uNDg0LTEuMDMzLTEuMDgtMS4wMzMtLjU5NSAwLTEuMDguNDYzLTEuMDggMS4wMzNtMi42ODItMy4wOThoLTguNDc2YS41My41MyAwIDAgMS0uNTQtLjUxN1Y3Ljc5M2MwLS4yODUuMjQyLS41MTYuNTQtLjUxNmg0LjgwNWwzLjY3MS4wMmMuMjk4IDAgLjU0LjIzMS41NC41MTZ2Ny4yM2EuNTMuNTMgMCAwIDEtLjU0LjUxNm0tLjU0LTcuMjMtMy4xMzEtLjAydjEuNTVhLjUzLjUzIDAgMCAxLS41NC41MTYuNTMuNTMgMCAwIDEtLjU0LS41MTZ2LTEuNTVoLTMuMTg1djYuMjE3aDcuMzk2eiIgY2xpcC1ydWxlPSJldmVub2RkIi8+PHJlY3Qgd2lkdGg9IjIyIiBoZWlnaHQ9IjIyIiB4PSIzIiB5PSIzIiBmaWxsPSIjZmZmIiByeD0iMTEiLz48cmVjdCB3aWR0aD0iMjIiIGhlaWdodD0iMjIiIHg9IjMiIHk9IjMiIGZpbGw9IiNmZmYiIHJ4PSIxMSIvPjxwYXRoIHN0cm9rZT0iIzFhYjI0OCIgc3Ryb2tlLWxpbmVjYXA9InJvdW5kIiBzdHJva2UtbGluZWpvaW49InJvdW5kIiBzdHJva2Utd2lkdGg9IjEuMiIgZD0iTTggMTloMTJNOS4zMzMgMTlWOS42NjdMMTQuNjY3IDd2MTJtNCAwdi02LjY2N2wtNC0yLjY2Nk0xMiAxMXYuMDA3TTEyIDEzdi4wMDdNMTIgMTV2LjAwN00xMiAxN3YuMDA3Ii8+PC9zdmc+';

// Преобразование [lat, lon] → [lon, lat] в EPSG:3857
function toProj(loc) {
  const [lat, lon] = loc || [];
  if (!lat || !lon) return null;
  return fromLonLat([lon, lat]);
}

// Стиль маркера — SVG-иконка ПВЗ (CDEK-стиль)
function markerStyle(feature) {
  const code     = feature.getId();
  const isActive = code === props.activeCode;
  return new Style({
    image: new Icon({
      src:      isActive ? ICON_ACTIVE : ICON_NORMAL,
      scale:    0.9,
      anchor:   [0.5, 1.0],   // низ иконки по центру = точка на карте
      anchorXUnits: 'fraction',
      anchorYUnits: 'fraction',
    }),
  });
}

// Стиль кластера
function clusterStyle(feature, resolution) {
  const size   = feature.get('features').length;
  return new Style({
    image: new Circle({
      radius: 10,                                      // 20px диаметр
      fill: new Fill({ color: '#ffffff' }),
      stroke: new Stroke({ color: '#1AB248', width: 2 }),
    }),
    text: new Text({
      text: String(size),
      fill: new Fill({ color: '#1AB248' }),
      font: 'bold 11px sans-serif',
    }),
  });
}

// Обновить стили всех маркеров (вызывается при смене activeCode)
function updateMarkerStyles() {
  if (!clusterSource) return;
  // Для одиночных маркеров (не кластеры) обновляем стиль
  clusterSource.getSource().forEachFeature(feature => {
    feature.setStyle(markerStyle(feature));
  });
}

// Полностью пересоздать маркеры (вызывается при смене списка)
function updateMarkers() {
  if (!clusterSource) return;
  clusterSource.getSource().clear();
  const features = [];
  props.markers.forEach(pvz => {
    const coords = toProj(pvz.location);
    if (!coords) return;
    const feature = new Feature({ geometry: new Point(coords) });
    feature.setId(pvz.code);
    feature.setStyle(markerStyle(feature));
    features.push(feature);
  });
  clusterSource.getSource().addFeatures(features);
}

// Клик по маркеру / кластеру
function onClick(event) {
  mapRef.value.forEachFeatureAtPixel(event.pixel, feature => {
    const features = feature.get('features');
    if (features) {
      if (features.length > 1) {
        // Кластер — zoom in к центру кластера
        const clusterCenter = feature.getGeometry().getCoordinates();
        mapRef.value.getView().animate({
          center: clusterCenter,
          zoom:   mapRef.value.getView().getZoom() + 2,
          duration: 300,
        });
      } else if (features.length === 1) {
        const code = features[0].getId();
        if (code) emit('markerselect', code);
      }
    } else {
      const code = feature.getId();
      if (code) emit('markerselect', code);
    }
  });
}

// Перемещение карты
function onMoveEnd(event) {
  const extent = event.map.getView().calculateExtent(event.map.getSize());
  // Конвертируем EPSG:3857 → [lon, lat] WGS84 для корректной фильтрации
  const [west, south, east, north] = extent;
  const sw = toLonLat([west, south]);  // [lon, lat]
  const ne = toLonLat([east, north]); // [lon, lat]
  emit('moveend', [sw[0], sw[1], ne[0], ne[1]]); // [minLon, minLat, maxLon, maxLat] WGS84
}

// ---- Dadata suggestions ----
async function doSuggest() {
  console.log('[MapPane] doSuggest backendUrl:', props.backendUrl);
  if (!props.backendUrl) return;
  try {
    const url = props.backendUrl + '?action=suggest&query=' + encodeURIComponent(query.value.trim());
    const res = await fetch(url);
    const json = await res.json();
    suggestions.value = json.suggestions || [];
    isOpen.value = suggestions.value.length > 0;
    activeIdx.value = suggestions.value.length > 0 ? 0 : -1;
  } catch {
    suggestions.value = [];
    isOpen.value = false;
  }
}

function onSearchInput() {
  searchError.value = null;
  activeIdx.value = -1;
  clearTimeout(searchTimer);
  if (query.value.trim().length < 3) {
    suggestions.value = [];
    isOpen.value = false;
    return;
  }
  searchTimer = setTimeout(doSuggest, 300);
}

function onKeyDown() { if (activeIdx.value < suggestions.value.length - 1) activeIdx.value++; }
function onKeyUp()   { if (activeIdx.value > 0) activeIdx.value--; }

function onKeyEnter() {
  if (activeIdx.value >= 0 && suggestions.value[activeIdx.value]) {
    selectSuggestion(suggestions.value[activeIdx.value]);
  }
}

function closeDropdown() { isOpen.value = false; }

function onBlur() { setTimeout(() => { isOpen.value = false; }, 150); }

function onFocus() { if (suggestions.value.length > 0) isOpen.value = true; }

function selectSuggestion(s) {
  query.value = s.value;
  suggestions.value = [];
  isOpen.value = false;
  activeIdx.value = -1;

  if (s.lat && s.lon) {
    // Zoom по типу объекта (дом > улица > нас.пункт > город)
    const zoom = s.house ? 17 : s.street ? 15 : s.settlement ? 13 : 12;
    mapRef.value.getView().animate({
      center: fromLonLat([parseFloat(s.lon), parseFloat(s.lat)]),
      zoom,
      duration: 500,
    });
    emit('search', s.value);
  }
}

// ---- API для родителя ----
function panTo([lat, lon], zoom = null) {
  if (!mapRef.value) return;
  mapRef.value.getView().animate({
    center: fromLonLat([lon, lat]),
    zoom:   zoom ?? props.zoom,
    duration: 500,
  });
}

function flashError(msg) { searchError.value = msg; }

function getBounds() {
  if (!mapRef.value) return null;
  const extent = mapRef.value.getView().calculateExtent(mapRef.value.getSize());
  const [west, south, east, north] = extent;
  const sw = toLonLat([west, south]);
  const ne = toLonLat([east, north]);
  return [sw[0], sw[1], ne[0], ne[1]];
}

defineExpose({ panTo, flashError, getBounds });

// Автопан при смене center
watch(() => props.center, val => {
  if (val && mapRef.value) panTo(val);
});

// Обновлять стили маркеров при смене activeCode
watch(() => props.activeCode, () => updateMarkerStyles());

// Пересоздавать маркеры при изменении списка
watch(() => props.markers, () => updateMarkers(), { deep: true });

// Инициализация OpenLayers
onMounted(() => {
  const container = mapContainerRef.value;

  vectorSource = new VectorSource();
  clusterSource = new Cluster({
    distance: 40,
    minDistance: 20,
    source: vectorSource,
  });

  const vectorLayer = new VectorLayer({
    source: clusterSource,
    style: (f, r) => {
      const features = f.get('features');
      if (features && features.length > 1) return clusterStyle(f, r);
      return markerStyle(f);
    },
  });

  const map = new Map({
    target: container,
    layers: [
      new TileLayer({ source: new OSM() }),
      vectorLayer,
    ],
    view: new View({
      center: props.center ? fromLonLat([props.center[1], props.center[0]]) : fromLonLat([37.6176, 55.7558]),
      zoom:   props.zoom,
    }),
  });

  mapRef.value = map;

  map.on('click',      onClick);
  map.on('moveend',     onMoveEnd);

  // Первичные маркеры
  updateMarkers();

  // Если center задан и карта уже имеет центр — пан
  if (props.center) {
    setTimeout(() => panTo(props.center), 100);
  }
});

onBeforeUnmount(() => {
  if (mapRef.value) {
    mapRef.value.setTarget(null);
    mapRef.value = null;
  }
});
</script>
