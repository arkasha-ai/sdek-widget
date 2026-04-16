<template>
  <div class="sdwo-map-col">
    <!-- OpenLayers карта -->
    <div class="sdwo-map" ref="mapContainerRef" />

    <!-- Поиск с подсказками (внутри карты, top-left) -->
    <div class="sdwo-search">
      <div class="sdwo-search-wrap">
        <svg class="sdwo-search__icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
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
        <ul v-if="suggestions.length && isOpen" class="sdwo-suggest-dropdown">
          <li
            v-for="(s, i) in suggestions"
            :key="i"
            :class="{ 'sdwo-suggest-active': i === activeIdx }"
            @mousedown.prevent="selectSuggestion(s)"
            @mouseenter="activeIdx = i"
          >
            {{ s.value }}
          </li>
        </ul>
      </div>
      <div v-if="searchError" class="sdwo-error">{{ searchError }}</div>
    </div>

    <!-- Кнопка тогла списка (top-right) -->
    <div class="sdwo-list-toggle">
      <button class="sdwo-map-btn" @click="$emit('togglepanel')" title="Список ПВЗ">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
    </div>

    <!-- Кнопки zoom / geolocation (bottom-right) -->
    <div class="sdwo-map-controls">
      <button class="sdwo-map-btn" @click="zoomIn" title="Приблизить">+</button>
      <button class="sdwo-map-btn" @click="zoomOut" title="Отдалить">−</button>
      <button class="sdwo-map-btn sdwo-map-btn--geo" @click="geolocate" title="Моё местоположение">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v4M12 18v4M2 12h4M18 12h4"/></svg>
      </button>
    </div>
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
  center:     { type: Array,   default: null },
  zoom:       { type: Number,  default: 12 },
  markers:    { type: Array,   default: () => [] },
  activeCode: { type: String,  default: '' },
  backendUrl: { type: String,  default: '' },
  mode:       { type: String,  default: 'office' }, // 'office' | 'door'
});

const emit = defineEmits(['moveend', 'markerselect', 'togglepanel', 'mapclick']);

// Refs
const mapContainerRef = ref(null);
const query           = ref('');
const searchError     = ref(null);
const mapRef          = ref(null);
const suggestions     = ref([]);
const activeIdx       = ref(-1);
const isOpen          = ref(false);

let searchTimer   = null;
let vectorSource  = null;
let clusterSource = null;

// ---- SVG маркеры (inline data URI) ----
// Пин с иконкой здания внутри (стиль СДЭК)
function makePinSvg(pinColor, strokeColor) {
  return 'data:image/svg+xml;base64,' + btoa(
    `<svg xmlns="http://www.w3.org/2000/svg" width="28" height="36" fill="none">` +
    `<path fill="${pinColor}" d="M28 14.344a14.55 14.55 0 0 1-2.12 7.594C20.2 31.245 14 36 14 36S7.8 31.245 2.12 21.938A14.54 14.54 0 0 1 0 14.343C0 6.422 6.268 0 14 0s14 6.422 14 14.344"/>` +
    `<rect width="22" height="22" x="3" y="3" fill="#fff" rx="11"/>` +
    `<path stroke="${strokeColor}" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.2" ` +
    `d="M8 19h12M9.333 19V9.667L14.667 7v12m4 0v-6.667l-4-2.666M12 11v.007M12 13v.007M12 15v.007M12 17v.007"/>` +
    `</svg>`
  );
}

const PIN_GREEN  = makePinSvg('#1AB248', '#1AB248');
const PIN_PURPLE = makePinSvg('#4B3C87', '#4B3C87');
const PIN_GREEN_ACTIVE = makePinSvg('#158E3A', '#158E3A');

// [lat, lon] → EPSG:3857
function toProj(loc) {
  const [lat, lon] = loc || [];
  if (!lat || !lon) return null;
  return fromLonLat([lon, lat]);
}

// Стиль маркера
function markerStyle(feature) {
  const code     = feature.getId();
  const type     = feature.get('pvzType') || 'PVZ';
  const isActive = code === props.activeCode;

  let src = type === 'POSTAMAT' ? PIN_PURPLE : PIN_GREEN;
  let scale = 0.85;
  if (isActive) { src = PIN_GREEN_ACTIVE; scale = 1.05; }

  return new Style({
    image: new Icon({
      src,
      scale,
      anchor: [0.5, 1.0],
      anchorXUnits: 'fraction',
      anchorYUnits: 'fraction',
    }),
  });
}

// Стиль кластера (зелёная pill)
function clusterStyle(feature) {
  const size = feature.get('features').length;
  return new Style({
    image: new Circle({
      radius: 14,
      fill: new Fill({ color: '#1AB248' }),
      stroke: new Stroke({ color: '#fff', width: 2 }),
    }),
    text: new Text({
      text: String(size),
      fill: new Fill({ color: '#fff' }),
      font: 'bold 11px Roboto, sans-serif',
    }),
  });
}

function updateMarkerStyles() {
  if (!vectorSource) return;
  vectorSource.forEachFeature(f => f.setStyle(markerStyle(f)));
}

function updateMarkers() {
  if (!vectorSource) return;
  vectorSource.clear();
  const features = [];
  props.markers.forEach(pvz => {
    const coords = toProj(pvz.location);
    if (!coords) return;
    const feature = new Feature({ geometry: new Point(coords) });
    feature.setId(pvz.code);
    feature.set('pvzType', pvz.type || 'PVZ');
    feature.setStyle(markerStyle(feature));
    features.push(feature);
  });
  vectorSource.addFeatures(features);
}

// Клик по маркеру / кластеру (stop on first hit)
function onClick(event) {
  let handled = false;
  mapRef.value.forEachFeatureAtPixel(event.pixel, feature => {
    if (handled) return;
    handled = true;
    const features = feature.get('features');
    if (features) {
      if (features.length > 1) {
        mapRef.value.getView().animate({
          center: feature.getGeometry().getCoordinates(),
          zoom: mapRef.value.getView().getZoom() + 2,
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
    return true;
  });

  // Для режима door: если клик не по маркеру — emit координаты
  if (!handled && props.mode === 'door') {
    const coords = toLonLat(event.coordinate);
    emit('mapclick', [coords[1], coords[0]]); // [lat, lon]
  }
}

function onMoveEnd(event) {
  const extent = event.map.getView().calculateExtent(event.map.getSize());
  const sw = toLonLat([extent[0], extent[1]]);
  const ne = toLonLat([extent[2], extent[3]]);
  emit('moveend', [sw[0], sw[1], ne[0], ne[1]]);
}

// ---- Custom zoom / geolocation ----
function zoomIn() {
  const view = mapRef.value?.getView();
  if (view) view.animate({ zoom: view.getZoom() + 1, duration: 200 });
}
function zoomOut() {
  const view = mapRef.value?.getView();
  if (view) view.animate({ zoom: view.getZoom() - 1, duration: 200 });
}
function geolocate() {
  if (!navigator.geolocation) return;
  navigator.geolocation.getCurrentPosition(
    pos => {
      const { latitude, longitude } = pos.coords;
      mapRef.value?.getView().animate({
        center: fromLonLat([longitude, latitude]),
        zoom: 14,
        duration: 500,
      });
    },
    () => { searchError.value = 'Не удалось определить местоположение'; }
  );
}

// ---- DaData suggest ----
async function doSuggest() {
  if (!props.backendUrl) return;
  try {
    let url = props.backendUrl + '?action=suggest&query=' + encodeURIComponent(query.value.trim());
    if (mapRef.value) {
      const center = mapRef.value.getView().getCenter();
      const [lon, lat] = toLonLat(center);
      url += '&lat=' + lat.toFixed(6) + '&lon=' + lon.toFixed(6);
    }
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

  if (s.lat != null && s.lon != null) {
    const zoomMap = { house: 17, street: 15, settlement: 13, city: 12 };
    const zoom = zoomMap[s.type] ?? 12;
    mapRef.value.getView().animate({
      center: fromLonLat([parseFloat(s.lon), parseFloat(s.lat)]),
      zoom,
      duration: 500,
    });
  }
}

// ---- API for parent ----
function panTo([lat, lon], zoom = null) {
  if (!mapRef.value) return;
  mapRef.value.getView().animate({
    center: fromLonLat([lon, lat]),
    zoom: zoom ?? props.zoom,
    duration: 500,
  });
}

function flashError(msg) { searchError.value = msg; }

function getBounds() {
  if (!mapRef.value) return null;
  const extent = mapRef.value.getView().calculateExtent(mapRef.value.getSize());
  const sw = toLonLat([extent[0], extent[1]]);
  const ne = toLonLat([extent[2], extent[3]]);
  return [sw[0], sw[1], ne[0], ne[1]];
}

defineExpose({ panTo, flashError, getBounds });

// Watchers
watch(() => props.center, val => { if (val && mapRef.value) panTo(val); });
watch(() => props.activeCode, () => updateMarkerStyles());
watch(() => props.markers, () => updateMarkers());

// Init OpenLayers
onMounted(() => {
  vectorSource = new VectorSource();
  clusterSource = new Cluster({
    distance: 40,
    minDistance: 20,
    source: vectorSource,
  });

  const vectorLayer = new VectorLayer({
    source: clusterSource,
    style: (f) => {
      const features = f.get('features');
      if (features && features.length > 1) return clusterStyle(f);
      return markerStyle(f);
    },
  });

  const map = new Map({
    target: mapContainerRef.value,
    layers: [
      new TileLayer({ source: new OSM() }),
      vectorLayer,
    ],
    view: new View({
      center: props.center
        ? fromLonLat([props.center[1], props.center[0]])
        : fromLonLat([37.6176, 55.7558]),
      zoom: props.zoom,
    }),
    controls: [], // убираем стандартные OL controls
  });

  mapRef.value = map;
  map.on('click', onClick);
  map.on('moveend', onMoveEnd);
  updateMarkers();

  if (props.center) {
    map.once('postrender', () => panTo(props.center));
  }
});

onBeforeUnmount(() => {
  if (mapRef.value) {
    mapRef.value.setTarget(null);
    mapRef.value = null;
  }
});
</script>
