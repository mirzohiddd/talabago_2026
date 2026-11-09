<script setup>
import BrandMark from './BrandMark.vue'
defineProps({ text: { type: String, default: '' }, size: { type: Number, default: 64 } })
</script>

<template>
  <div class="flex flex-col items-center gap-4">
    <div class="relative grid place-items-center" :style="{ width: `${size + 32}px`, height: `${size + 32}px` }">
      <svg class="absolute inset-0 size-full animate-spin [animation-duration:1.1s]" viewBox="0 0 100 100">
        <circle cx="50" cy="50" r="46" fill="none" stroke="#ECFDF5" stroke-width="4" />
        <circle cx="50" cy="50" r="46" fill="none" stroke="#10B981" stroke-width="4" stroke-linecap="round" stroke-dasharray="70 220" />
      </svg>
      <div class="animate-[float_2.4s_ease-in-out_infinite]"><BrandMark :size="size" :animated="false" /></div>
    </div>
    <p v-if="text" class="text-sm text-muted font-medium animate-pulse">{{ text }}</p>
  </div>
</template>
