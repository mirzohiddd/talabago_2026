<script setup>
import { computed } from 'vue'
import { haptic } from '@/services/telegram'
const model = defineModel({ type: String })
const props = defineProps({ options: { type: Array, required: true } })
const idx = computed(() => Math.max(0, props.options.findIndex((o) => o.value === model.value)))
</script>

<template>
  <div class="relative grid bg-surface rounded-xl p-1" :style="{ gridTemplateColumns: `repeat(${options.length}, 1fr)` }">
    <span
      class="absolute top-1 bottom-1 left-1 rounded-[10px] bg-white shadow-sm transition-transform duration-300 ease-[cubic-bezier(.22,1,.36,1)]"
      :style="{ width: `calc((100% - 8px) / ${options.length})`, transform: `translateX(${idx * 100}%)` }"
    />
    <button
      v-for="o in options" :key="o.value" type="button"
      :class="['relative z-10 h-9 text-[13px] font-semibold rounded-[10px] transition-colors inline-flex items-center justify-center gap-1.5', model === o.value ? 'text-ink' : 'text-muted']"
      @click="haptic.select(); model = o.value"
    >
      <component :is="o.icon" v-if="o.icon" class="size-4" :class="model === o.value && 'text-brand-600'" />
      {{ o.label }}
    </button>
  </div>
</template>
