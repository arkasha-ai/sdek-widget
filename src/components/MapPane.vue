<template>
  <div class="sdwo-map-col">
    <!-- Поиск -->
    <div class="sdwo-search-row">
      <input
        v-model="query"
        type="text"
        class="sdwo-input"
        placeholder="Поиск адреса…"
        autocomplete="off"
        @input="onSearch"
      />
      <div v-if="searchError" class="sdwo-error">{{ searchError }}</div>
    </div>

    <!-- OpenLayers карта — создаём в onMounted -->
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
  center:     { type: Array,  default: null },  // [lat, lon]
  zoom:       { type: Number, default: 12 },
  markers:    { type: Array,  default: () => [] },
  activeCode: { type: String, default: null },
});

const emit = defineEmits(['search', 'moveend', 'markerselect']);

// Refs
const mapContainerRef = ref(null);
const query          = ref('');
const searchError     = ref(null);
const mapRef         = ref(null); // OpenLayers Map instance

let searchTimer  = null;
let vectorSource = null;
let clusterSource = null;

// SVG-иконки ПВЗ (CDEK-стиль) — normal и active
const ICON_NORMAL = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyOCIgaGVpZ2h0PSIzNiIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iIzFBQjI0OCIgZD0iTTI4IDE0LjM0NGMwIDIuNzg4LS43NzcgNS4zOTEtMi4xMiA3LjU5NEMyMC4yIDMxLjI0NSAxNCAzNiAxNCAzNlM3LjggMzEuMjQ1IDIuMTIgMjEuOTM4QTE0LjU0IDE0LjU0IDAgMCAxIDAgMTQuMzQzQzAgNi40MjIgNi4yNjggMCAxNCAwczE0IDYuNDIyIDE0IDE0LjM0NCI+PC9wYXRoPjxyZWN0IHdpZHRoPSIyMiIgaGVpZ2h0PSIyMiIgeD0iMyIgeT0iMyIgZmlsbD0iI2ZmZiIgcng9IjExIj48L3JlY3Q+PHBhdGggZmlsbD0iIzFBQjI0OCIgZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMjAuNzk0IDE3LjYyNGgtLjgxNGMuMTg0LjMwNC4yOTIuNjU2LjI5MiAxLjAzMyAwIDEuMTM4LS45NjkgMi4wNjUtMi4xNiAyLjA2NS0xLjE5IDAtMi4xNi0uOTI3LTIuMTYtMi4wNjUgMC0uMzc3LjEwOC0uNzI5LjI5My0xLjAzM2gtMi41NjRjLjE4NS4zMDQuMjkyLjY1Ni4yOTIgMS4wMzMgMCAxLjEzOC0uOTY4IDIuMDY1LTIuMTU5IDIuMDY1cy0yLjE2LS45MjctMi4xNi0yLjA2NWMwLS4zNzcuMTA4LS43MjkuMjkzLTEuMDMzaC0uODIzYS41My41MyAwIDAgMS0uNTQtLjUxNmwtLjAxLTcuMTI0LTEuNzUtMS42NzRhLjUuNSAwIDAgMSAwLS43M2MuMjEtLjIwMS41NTQtLjIwMS43NjQgMGwxLjkyNyAxLjg0M2MuMDA4LjAwNy4wMS4wMTYuMDE2LjAyNGEuNS41IDAgMCAxIC4wNTkuMDgzLjQ5LjQ5IDAgMCAxIC4wNjQuMzQ5bC4wMSA2LjcxMmgxMS4xM2EuNTMuNTMgMCAwIDEgLjU0LjUxNy41My41MyAwIDAgMS0uNTQuNTE2bS04Ljk4IDBjLS41OTUgMC0xLjA4LjQ2My0xLjA4IDEuMDMzcy40ODUgMS4wMzIgMS4wOCAxLjAzMiAxLjA4LS40NjMgMS4wOC0xLjAzMmMwLS41Ny0uNDg1LTEuMDMzLTEuMDgtMS4wMzNtNS4yMTggMS4wMzNjMCAuNTY5LjQ4NSAxLjAzMiAxLjA4IDEuMDMyczEuMDgtLjQ2MyAxLjA4LTEuMDMyYzAtLjU3LS40ODQtMS4wMzMtMS4wOC0xLjAzMy0uNTk1IDAtMS4wOC40NjMtMS4wOCAxLjAzM20yLjY4Mi0zLjA5OGgtOC40NzZhLjUzLjUzIDAgMCAxLS41NC0uNTE3VjcuNzkzYzAtLjI4NS4yNDItLjUxNi41NC0uNTE2aDQuODA1bDMuNjcxLjAyYy4yOTggMCAuNTQuMjMxLjU0LjUxNnY3LjIzYS41My41MyAwIDAgMS0uNTQuNTE2bS0uNTQtNy4yMy0zLjEzMS0uMDJ2MS41NWEuNTMuNTMgMCAwIDEtLjU0LjUxNi41My41MyAwIDAgMS0uNTQtLjUxNnYtMS41NWgtMy4xODV2Ni4yMTdoNy4zOTZ6IiBjbGlwLXJ1bGU9ImV2ZW5vZGQiPjwvcGF0aD48cGF0aCBzdHJva2U9IiMxQUIyNDgiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgc3Ryb2tlLXdpZHRoPSIxLjIiIGQ9Ik04IDE5aDEyTTkuMzMzIDE5VjkuNjY3TDE0LjY2NyA3djEybTQgMHYtNi42NjdsLTQtMi42NjZNMTIgMTF2LjAwN00xMiAxM3YuMDA3TTEyIDE1di4wMDdNMTIgMTd2LjAwNyI+PC9wYXRoPjwvc3ZnPg==';
const ICON_ACTIVE = 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyOCIgaGVpZ2h0PSIzNiIgZmlsbD0ibm9uZSI+PHBhdGggZmlsbD0iI2U1MzkzNSIgZD0iTTI4IDE0LjM0NGMwIDIuNzg4LS43NzcgNS4zOTEtMi4xMiA3LjU5NEMyMC4yIDMxLjI0NSAxNCAzNiAxNCAzNlM3LjggMzEuMjQ1IDIuMTIgMjEuOTM4QTE0LjU0IDE0LjU0IDAgMCAxIDAgMTQuMzQzQzAgNi40MjIgNi4yNjggMCAxNCAwczE0IDYuNDIyIDE0IDE0LjM0NCI+PC9wYXRoPjxyZWN0IHdpZHRoPSIyMiIgaGVpZ2h0PSIyMiIgeD0iMyIgeT0iMyIgZmlsbD0iI2ZmZiIgcng9IjExIj48L3JlY3Q+PHBhdGggZmlsbD0iI2U1MzkzNSIgZmlsbC1ydWxlPSJldmVub2RkIiBkPSJNMjAuNzk0IDE3LjYyNGgtLjgxNGMuMTg0LjMwNC4yOTIuNjU2LjI5MiAxLjAzMyAwIDEuMTM4LS45NjkgMi4wNjUtMi4xNiAyLjA2NS0xLjE5IDAtMi4xNi0uOTI3LTIuMTYtMi4wNjUgMC0uMzc3LjEwOC0uNzI5LjI5My0xLjAzM2gtMi41NjRjLjE4NS4zMDQuMjkyLjY1Ni4yOTIgMS4wMzMgMCAxLjEzOC0uOTY4IDIuMDY1LTIuMTU5IDIuMDY1cy0yLjE2LS45MjctMi4xNi0yLjA2NWMwLS4zNzcuMTA4LS43MjkuMjkzLTEuMDMzaC0uODIzYS41My41MyAwIDAgMS0uNTQtLjUxNmwtLjAxLTcuMTI0LTEuNzUtMS42NzRhLjUuNSAwIDAgMSAwLS43M2MuMjEtLjIwMS41NTQtLjIwMS43NjQgMGwxLjkyNyAxLjg0M2MuMDA4LjAwNy4wMS4wMTYuMDE2LjAyNGEuNS41IDAgMCAxIC4wNTkuMDgzLjQ5LjQ5IDAgMCAxIC4wNjQuMzQ5bC4wMSA2LjcxMmgxMS4xM2EuNTMuNTMgMCAwIDEgLjU0LjUxNy41My41MyAwIDAgMS0uNTQuNTE2bS04Ljk4IDBjLS41OTUgMC0xLjA4LjQ2My0xLjA4IDEuMDMzcy40ODUgMS4wMzIgMS4wOCAxLjAzMiAxLjA4LS40NjMgMS4wOC0xLjAzMmMwLS41Ny0uNDg1LTEuMDMzLTEuMDgtMS4wMzNtNS4yMTggMS4wMzNjMCAuNTY5LjQ4NSAxLjAzMiAxLjA4IDEuMDMyczEuMDgtLjQ2MyAxLjA4LTEuMDMyYzAtLjU3LS40ODQtMS4wMzMtMS4wOC0xLjAzMy0uNTk1IDAtMS4wOC40NjMtMS4wOCAxLjAzM20yLjY4Mi0zLjA5OGgtOC40NzZhLjUzLjUzIDAgMCAxLS41NC0uNTE3VjcuNzkzYzAtLjI4NS4yNDItLjUxNi41NC0uNTE2aDQuODA1bDMuNjcxLjAyYy4yOTggMCAuNTQuMjMxLjU0LjUxNnY3LjIzYS41My41MyAwIDAgMS0uNTQuNTE2bS0uNTQtNy4yMy0zLjEzMS0uMDJ2MS41NWEuNTMuNTMgMCAwIDEtLjU0LjUxNi41My41MyAwIDAgMS0uNTQtLjUxNnYtMS41NWgtMy4xODV2Ni4yMTdoNy4zOTZ6IiBjbGlwLXJ1bGU9ImV2ZW5vZGQiPjwvcGF0aD48cGF0aCBzdHJva2U9IiNlNTM5MzUiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIgc3Ryb2tlLXdpZHRoPSIxLjIiIGQ9Ik04IDE5aDEyTTkuMzMzIDE5VjkuNjY3TDE0LjY2NyA3djEybTQgMHYtNi42NjdsLTQtMi42NjZNMTIgMTF2LjAwN00xMiAxM3YuMDA3TTEyIDE1di4wMDdNMTIgMTd2LjAwNyI+PC9wYXRoPjwvc3ZnPg==';

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

// Поиск
function onSearch() {
  searchError.value = null;
  clearTimeout(searchTimer);
  if (query.value.trim().length < 3) return;
  searchTimer = setTimeout(() => emit('search', query.value.trim()), 400);
}

// ---- API для родителя ----
function panTo([lat, lon]) {
  if (!mapRef.value) return;
  mapRef.value.getView().animate({
    center: fromLonLat([lon, lat]),
    zoom:   props.zoom,
    duration: 500,
  });
}

function flashError(msg) {
  searchError.value = msg;
}

function getBounds() {
  if (!mapRef.value) return null;
  const extent = mapRef.value.getView().calculateExtent(mapRef.value.getSize());
  // EPSG:3857 → WGS84 [lon, lat]
  const [west, south, east, north] = extent;
  const sw = toLonLat([west, south]);
  const ne = toLonLat([east, north]);
  return [sw[0], sw[1], ne[0], ne[1]]; // [minLon, minLat, maxLon, maxLat] WGS84
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
