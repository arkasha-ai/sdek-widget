<template>
  <div class="sdwo-panel" :class="{ 'sdwo-panel--hidden': !visible }">
    <!-- Header -->
    <div class="sdwo-panel__head">
      <span>Пункты выдачи</span>
      <span class="sdwo-badge">{{ list.length }}</span>
    </div>

    <!-- Error -->
    <div v-if="error" class="sdwo-panel__err">{{ error }}</div>

    <!-- Body -->
    <div class="sdwo-panel__body">
      <!-- Loading -->
      <template v-if="loading">
        <div v-for="i in 5" :key="i" class="sdwo-skeleton" />
      </template>

      <!-- Empty -->
      <div v-else-if="!list.length" class="sdwo-empty">
        ПВЗ не найдены в видимой области
      </div>

      <!-- Items -->
      <div
        v-if="!loading"
        v-for="pvz in list"
        :key="pvz.code"
        class="sdwo-pvz-item"
        :class="{ 'sdwo-pvz-item--active': active === pvz.code }"
        @click="$emit('select', pvz)"
      >
        <div class="sdwo-pvz-item__code">{{ pvz.code }}</div>
        <div class="sdwo-pvz-item__addr">{{ pvz.address }}</div>
        <div class="sdwo-pvz-item__time" v-if="pvz.work_time">{{ pvz.work_time }}</div>
        <div v-if="pvz._dist" class="sdwo-pvz-item__dist">~ {{ pvz._dist }} км</div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  visible: { type: Boolean, default: true },
  list:    { type: Array,   default: () => [] },
  active:  { type: String,  default: null },
  loading: { type: Boolean, default: false },
  error:   { type: String,  default: null },
});

defineEmits(['select']);
</script>
