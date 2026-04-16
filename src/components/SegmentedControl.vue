<template>
  <div class="sdwo-segment">
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
</template>

<script setup>
defineProps({
  modelValue: { type: String, default: 'office' },
});
defineEmits(['update:modelValue']);
</script>
