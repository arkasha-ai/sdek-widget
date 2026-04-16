<template>
  <div class="sdwo-panel" :class="{ 'sdwo-panel--hidden': !visible }">
    <div class="sdwo-panel__head">
      Доставка до двери
    </div>

    <div class="sdwo-panel__body">
      <!-- Загрузка (до получения адреса) -->
      <div v-if="loading && !address" class="sdwo-loader">
        <div class="sdwo-spinner" />
      </div>

      <!-- Ничего не выбрано -->
      <div v-else-if="!address && !loading" class="sdwo-door__empty">
        Нажмите на карту, чтобы выбрать адрес доставки
      </div>

      <template v-else-if="address">
        <!-- Адрес -->
        <div class="sdwo-door__addr">{{ address }}</div>
        <div v-if="hint" class="sdwo-door__hint">{{ hint }}</div>

        <!-- Тарифы -->
        <div v-if="loading" class="sdwo-loader">
          <div class="sdwo-spinner" />
        </div>

        <template v-else-if="tariffs.length">
          <div class="sdwo-tariffs-title">Способы доставки</div>
          <div
            v-for="t in tariffs"
            :key="t.tariff_code"
            class="sdwo-tariff"
            :class="{ 'sdwo-tariff--selected': selectedCode === t.tariff_code }"
            @click="selectTariff(t)"
          >
            <svg class="sdwo-tariff__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
            <div class="sdwo-tariff__name">{{ t.tariff_name }}</div>
            <div class="sdwo-tariff__row">
              <span class="sdwo-tariff__days">{{ t.period_min }}–{{ t.period_max }} дн.</span>
              <span class="sdwo-tariff__price">{{ formatPrice(t.delivery_sum) }} ₽</span>
            </div>
          </div>
        </template>

        <div v-else-if="error" class="sdwo-panel__err">{{ error }}</div>
        <div v-else-if="!loading" class="sdwo-empty">Выберите адрес точнее</div>
      </template>
    </div>

    <!-- Footer -->
    <div class="sdwo-panel__foot">
      <button
        class="sdwo-btn"
        :disabled="!selectedCode || !address"
        @click="handleChoose"
      >
        Выбрать
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue';

const props = defineProps({
  visible:  { type: Boolean, default: false },
  address:  { type: String,  default: null },
  hint:     { type: String,  default: null },
  tariffs:  { type: Array,   default: () => [] },
  loading:  { type: Boolean, default: false },
  error:    { type: String,  default: null },
  location: { type: Array,   default: null }, // [lat, lon]
  cityCode: { type: [String, Number], default: null },
});

const emit = defineEmits(['choose']);

const selectedCode = ref(null);

// Сброс при смене адреса
watch(() => props.address, () => { selectedCode.value = null; });

watch(() => props.tariffs, (list) => {
  if (list.length === 1) selectedCode.value = list[0].tariff_code;
}, { immediate: true });

function selectTariff(t) {
  selectedCode.value = t.tariff_code;
}

function formatPrice(v) {
  if (v == null) return '—';
  return Math.round(v).toLocaleString('ru-RU');
}

function handleChoose() {
  const t = props.tariffs.find(t => t.tariff_code === selectedCode.value);
  if (t && props.address) {
    emit('choose', {
      address: props.address,
      location: props.location,
      city_code: props.cityCode,
    }, t);
  }
}
</script>
