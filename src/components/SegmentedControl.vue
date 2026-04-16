<template>
  <div class="sdwo-segment">
    <div class="sdwo-segment__tabs">
      <button
        class="sdwo-segment__btn"
        :class="{ 'sdwo-segment__btn--active': modelValue === 'office' }"
        @click="$emit('update:modelValue', 'office')"
      >
        До пункта выдачи
      </button>
      <button
        class="sdwo-segment__btn"
        :class="{ 'sdwo-segment__btn--active': modelValue === 'door' }"
        @click="$emit('update:modelValue', 'door')"
      >
        До двери
      </button>
    </div>
    <div class="sdwo-segment__actions">
      <button class="sdwo-segment__icon" @click="$emit('togglepanel')" title="Список ПВЗ">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="3" y1="6" x2="21" y2="6"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="3" y1="18" x2="21" y2="18"/></svg>
      </button>
      <button class="sdwo-segment__icon" @click="$emit('close')" title="Закрыть">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: 'office' },
});
defineEmits(['update:modelValue', 'togglepanel', 'close']);
</script>
