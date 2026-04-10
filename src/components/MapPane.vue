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

    <!-- OpenLayers карта (vue3-openlayers компоненты) -->
    <div class="sdwo-map">
      <ol-map
        ref="olMapRef"
        :load-tiles-while-animating="true"
        :load-tiles-while-interacting="true"
        @click="onClick"
        @moveend="onMoveEnd"
      >
        <!-- Тайловый слой OSM -->
        <ol-tile-layer>
          <ol-source-osm />
        </ol-tile-layer>

        <!-- Векторный слой маркеров -->
        <ol-vector-layer>
          <ol-source-vector>
            <ol-feature
              v-for="pvz in markers"
              :key="pvz.code"
              :id="pvz.code"
            >
              <!-- coords: [lon, lat] — projection EPSG:3857 -->
              <ol-geom-point :coordinates="toProj(pvz.location)" />
              <ol-style>
                <ol-style-circle :radius="pvz.code === activeCode ? 10 : 8">
                  <ol-stroke
                    :color="pvz.code === activeCode ? '#b80000' : '#fff'"
                    :width="2"
                  />
                  <ol-fill
                    :color="pvz.code === activeCode ? '#e53935' : '#c69b3c'"
                  />
                </ol-style-circle>
                <ol-style-text :text="pvz.code" :offset-y="-14" />
              </ol-style>
            </ol-feature>
          </ol-source-vector>
        </ol-vector-layer>
      </ol-map>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';
import { fromLonLat } from 'ol/proj';

const props = defineProps({
  center:     { type: Array,  default: null },  // [lat, lon]
  zoom:       { type: Number, default: 12 },
  markers:    { type: Array,  default: () => [] },
  activeCode: { type: String, default: null },
});

const emit = defineEmits(['search', 'moveend', 'markerselect']);

const olMapRef   = ref(null);
const query      = ref('');
const searchError = ref(null);

let searchTimer = null;

// CDEK returns [lat, lon], OpenLayers needs [lon, lat] in EPSG:3857
function toProj(loc) {
  const [lat, lon] = loc || [];
  if (!lat || !lon) return [0, 0];
  return fromLonLat([lon, lat]);
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
  if (!olMapRef.value) return;
  const view = olMapRef.value.getView();
  if (!view) return;
  view.animate({ center: fromLonLat([lon, lat]), zoom: props.zoom });
}

function flashError(msg) {
  searchError.value = msg;
}

function getBounds() {
  if (!olMapRef.value) return null;
  const view = olMapRef.value.getView();
  if (!view) return null;
  return view.calculateExtent(olMapRef.value.getSize());
}

defineExpose({ panTo, flashError, getBounds });

// автопан при смене center
watch(() => props.center, val => {
  if (val) panTo(val);
});
</script>
