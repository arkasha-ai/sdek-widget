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

    <!-- OpenLayers карта -->
    <div class="sdwo-map" ref="mapContainerRef" style="width:100%;min-height:300px;">
      <ol-map
        ref="olMapRef"
        :load-tiles-while-animating="true"
        :load-tiles-while-interacting="true"
        style="width:100%;height:100%;"
        @click="onClick"
        @moveend="onMoveEnd"
      >
        <!-- Тайловый слой OSM -->
        <ol-tile-layer>
          <ol-source-osm />
        </ol-tile-layer>

        <!-- Векторный слой маркеров -->
        <ol-vector-layer :style="markerStyleFn">
          <ol-source-vector>
            <ol-feature
              v-for="pvz in markers"
              :key="pvz.code"
              :id="pvz.code"
            >
              <!-- coords: [lon, lat] — projection EPSG:3857 -->
              <ol-geom-point :coordinates="toProj(pvz.location)" />
            </ol-feature>
          </ol-source-vector>
        </ol-vector-layer>
      </ol-map>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, inject } from 'vue';
import { fromLonLat } from 'ol/proj';
import { Style, Circle, Stroke, Fill } from 'ol/style';

const props = defineProps({
  center:     { type: Array,  default: null },  // [lat, lon]
  zoom:       { type: Number, default: 12 },
  markers:    { type: Array,  default: () => [] },
  activeCode: { type: String, default: null },
});

const emit = defineEmits(['search', 'moveend', 'markerselect']);

// ol-map создаёт OlMap instance и provide'ит его — забираем через inject
const olMap = inject('map');

const olMapRef    = ref(null);
const mapContainerRef = ref(null);
const query       = ref('');
const searchError = ref(null);

let searchTimer = null;

// CDEK returns [lat, lon], OpenLayers needs [lon, lat] in EPSG:3857
function toProj(loc) {
  const [lat, lon] = loc || [];
  if (!lat || !lon) return [0, 0];
  return fromLonLat([lon, lat]);
}

// Стиль маркера — factory function для каждого feature
function markerStyleFn(feature) {
  const code      = feature.getId();
  const isActive  = code === props.activeCode;
  const radius    = isActive ? 10 : 8;
  const fillColor = isActive ? '#e53935' : '#c69b3c';
  const strokeColor = isActive ? '#b80000' : '#fff';
  const strokeWidth = 2;

  return new Style({
    image: new Circle({
      radius,
      fill: new Fill({ color: fillColor }),
      stroke: new Stroke({ color: strokeColor, width: strokeWidth }),
    }),
  });
}

// клик по маркеру
function onClick(event) {
  event.map.forEachFeatureAtPixel(event.pixel, feature => {
    const code = feature.getId();
    if (code) emit('markerselect', code);
  });
}

// перемещение карты
function onMoveEnd(event) {
  emit('moveend', event.map.getView().calculateExtent(event.map.getSize()));
}

// поиск
function onSearch() {
  searchError.value = null;
  clearTimeout(searchTimer);
  if (query.value.trim().length < 3) return;
  searchTimer = setTimeout(() => emit('search', query.value.trim()), 400);
}

// ---- exposing для родителя ----
function panTo([lat, lon]) {
  if (!olMap) return;
  const view = olMap.getView();
  if (!view) return;
  view.animate({ center: fromLonLat([lon, lat]), zoom: props.zoom });
}

function flashError(msg) {
  searchError.value = msg;
}

function getBounds() {
  if (!olMap) return null;
  const view = olMap.getView();
  if (!view) return null;
  return view.calculateExtent(olMap.getSize());
}

defineExpose({ panTo, flashError, getBounds });

// автопан при смене center — только когда карта готова
watch(() => props.center, val => {
  if (val && olMap) panTo(val);
});

// Исправление width:0 — после монтирования сообщаем OL размеры контейнера
onMounted(() => {
  if (olMap) {
    setTimeout(() => olMap.updateSize(), 50);
  }
});
</script>
