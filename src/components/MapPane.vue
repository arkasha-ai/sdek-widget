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
import { Style, Circle, Stroke, Fill, Text } from 'ol/style';

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

// Преобразование [lat, lon] → [lon, lat] в EPSG:3857
function toProj(loc) {
  const [lat, lon] = loc || [];
  if (!lat || !lon) return null;
  return fromLonLat([lon, lat]);
}

// Стиль маркера
function markerStyle(feature) {
  const code     = feature.getId();
  const isActive = code === props.activeCode;
  const radius   = isActive ? 10 : 8;
  return new Style({
    image: new Circle({
      radius,
      fill: new Fill({ color: isActive ? '#e53935' : '#c69b3c' }),
      stroke: new Stroke({ color: isActive ? '#b80000' : '#fff', width: 2 }),
    }),
  });
}

// Стиль кластера
function clusterStyle(feature, resolution) {
  const size   = feature.get('features').length;
  const isBig  = size > 10;
  const radius = isBig ? 24 : 16;
  return new Style({
    image: new Circle({
      radius,
      fill: new Fill({ color: size > 10 ? '#2b7bb9' : '#c69b3c' }),
      stroke: new Stroke({ color: '#fff', width: 2 }),
    }),
    text: new Text({
      text: String(size),
      fill: new Fill({ color: '#fff' }),
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
