<template>
  <div class="sdwo-panel" :class="{ 'sdwo-panel--hidden': !visible }">
    <!-- Header with back button -->
    <div class="sdwo-panel__head">
      <button class="sdwo-panel__back" @click="$emit('back')">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 12H5"/><polyline points="12 19 5 12 12 5"/></svg>
        Назад
      </button>
    </div>

    <div class="sdwo-panel__body" v-if="pvz">
      <!-- PVZ info -->
      <div class="sdwo-detail__info">
        <div class="sdwo-detail__code">{{ pvz.code }}</div>
        <div class="sdwo-detail__addr">{{ pvz.city ? pvz.city + ', ' : '' }}{{ pvz.address }}</div>
        <div class="sdwo-detail__time" v-if="pvz.work_time">{{ pvz.work_time }}</div>
      </div>

      <!-- Tariffs -->
      <div v-if="loading" class="sdwo-loader">
        <div class="sdwo-spinner" />
      </div>

      <template v-else-if="tariffs.length">
        <div class="sdwo-tariffs-title">Способы доставки</div>
        <div
          v-for="t in tariffs"
          :key="t.tariff_code"
          class="sdwo-tariff"
          :class="{ 'sdwo-tariff--selected': selectedTariffCode === t.tariff_code }"
          @click="selectTariff(t)"
        >
          <!-- Checkmark -->
          <svg class="sdwo-tariff__check" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
          <div class="sdwo-tariff__name">{{ t.tariff_name }}</div>
          <div class="sdwo-tariff__row">
            <span class="sdwo-tariff__days">{{ t.period_min }}–{{ t.period_max }} дн.</span>
            <span class="sdwo-tariff__price">{{ formatPrice(t.delivery_sum) }} ₽</span>
          </div>
        </div>
      </template>

      <div v-else-if="error" class="sdwo-panel__err">{{ error }}</div>
<!--      <div v-else class="sdwo-empty">Нет доступных тарифов</div>-->
    </div>

    <!-- Footer -->
    <div class="sdwo-panel__foot">
      <button
        class="sdwo-btn"
        :disabled="tariffs.length && !selectedTariffCode"
        @click="handleChoose"
      >
        Выбрать
      </button>
    </div>
  </div>
</template>

<script setup>
import {ref, watch} from 'vue';

const props = defineProps({
  visible:  { type: Boolean, default: false },
  pvz:      { type: Object,  default: null },
  tariffs:  { type: Array,   default: () => [] },
  loading:  { type: Boolean, default: false },
  error:    { type: String,  default: null },
});

const emit = defineEmits(['back', 'choose']);

const selectedTariffCode = ref(null);

// Сброс выбранного тарифа при смене ПВЗ
watch(() => props.pvz, () => { selectedTariffCode.value = null; });

// Автовыбор если один тариф
watch(() => props.tariffs, (list) => {
  if (list.length === 1) selectedTariffCode.value = list[0].tariff_code;
}, { immediate: true });

function selectTariff(t) {
  selectedTariffCode.value = t.tariff_code;
}

function formatPrice(v) {
  if (v == null) return '—';
  return Math.round(v).toLocaleString('ru-RU');
}

function handleChoose() {
  const t = props.tariffs.find(t => t.tariff_code === selectedTariffCode.value);
  if (props.pvz) emit('choose', props.pvz, t);
}
</script>
