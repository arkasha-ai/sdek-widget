<template>
  <div class="sdwo-sidebar">
    <!-- Header -->
    <div class="sdwo-sidebar__head">
      <span>ПВЗ в видимой области</span>
      <span class="sdwo-badge">{{ list.length }}</span>
    </div>

    <!-- Error -->
    <div v-if="error" class="sdwo-sidebar__err">{{ error }}</div>

    <!-- List -->
    <div class="sdwo-sidebar__list">
      <!-- Skeleton loading -->
      <template v-if="loading">
        <div v-for="i in 3" :key="i" class="sdwo-skeleton" />
      </template>

      <!-- Empty -->
      <div v-else-if="!list.length" class="sdwo-empty">
        ПВЗ не найдены
      </div>

      <!-- Items -->
      <div
        v-for="pvz in list"
        :key="pvz.code"
        class="sdwo-pvz-item"
        :class="{ 'sdwo-pvz-item--active': active === pvz.code }"
        @click="$emit('select', pvz)"
      >
        <div class="sdwo-pvz-item__name">{{ pvz.name || pvz.address }}</div>
        <div class="sdwo-pvz-item__addr">{{ pvz.address }}</div>
        <div class="sdwo-pvz-item__time">{{ pvz.work_time || '' }}</div>
        <div v-if="pvz._dist" class="sdwo-pvz-item__dist">
          ~ {{ pvz._dist }} км
        </div>
      </div>
    </div>

    <!-- Tariff -->
    <div v-if="tariff" class="sdwo-tariff">
      <div class="sdwo-tariff__label">Стоимость доставки</div>
      <div class="sdwo-tariff__price">
        {{ tariff.price ?? tariff.delivery_sum ?? '—' }} ₽
      </div>
      <div class="sdwo-tariff__days">
        Срок: {{ tariff.period_min ?? '?' }}–{{ tariff.period_max ?? '?' }} дн.
      </div>
    </div>

    <!-- Footer -->
    <div class="sdwo-sidebar__foot">
      <button
        class="sdwo-btn"
        :disabled="!pvz || !tariff"
        @click="handleChoose"
      >
        Выбрать
      </button>
    </div>
  </div>
</template>

<script setup>
const props = defineProps({
  list:    { type: Array,   default: () => [] },
  active:  { type: String,  default: null },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
  tariff:  { type: Object,  default: null },
  pvz:     { type: Object,  default: null },
});

const emit = defineEmits(['select', 'choose']);

function handleChoose() {
  if (props.pvz && props.tariff) {
    emit('choose', props.pvz, props.tariff);
  }
}
</script>
