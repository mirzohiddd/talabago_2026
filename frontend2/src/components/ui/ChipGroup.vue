<script setup>
import { haptic } from '@/services/platform'
/** Filtr chiplari. multiple=true bo‘lsa massiv qaytaradi */
const model = defineModel({ type: [String, Array], default: 'all' })
const props = defineProps({
  options: { type: Array, required: true }, // [{value,label,icon?}]
  multiple: Boolean,
  wrap: Boolean,
  size: { type: String, default: 'md' },
})
function isActive(v) {
  return props.multiple ? model.value.includes(v) : model.value === v
}
function select(v) {
  haptic.select()
  if (!props.multiple) return (model.value = v)
  model.value = isActive(v) ? model.value.filter((x) => x !== v) : [...model.value, v]
}
</script>

<template>
  <div :class="['flex gap-2', wrap ? 'flex-wrap' : 'overflow-x-auto no-scrollbar -mx-4 px-4']">
    <button
      v-for="o in options"
      :key="o.value"
      type="button"
      :class="[
        'shrink-0 inline-flex items-center gap-1.5 rounded-full font-semibold border transition-all duration-200 active:scale-95',
        size === 'sm' ? 'h-8 px-3 text-[13px]' : 'h-9 px-4 text-sm',
        isActive(o.value)
          ? 'bg-brand border-brand text-white shadow-[var(--shadow-brand)] scale-[1.02]'
          : 'bg-surface border-transparent text-ink-2 hover:border-brand-200 hover:bg-brand-25 hover:text-ink',
      ]"
      @click="select(o.value)"
    >
      <component :is="o.icon" v-if="o.icon" class="size-4" />
      {{ o.label }}
    </button>
  </div>
</template>
