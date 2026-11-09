<script setup>
/**
 * TalabaGo logotipi (src/assets/brand/logo.webp): qora “T” va “alaba”, yashil qalpoq, aylana va “Go”.
 * variant="mark" — faqat “T” belgisi (yig‘ilgan sidebar).
 */
import logo from '@/assets/brand/logo.webp'
import BrandMark from './BrandMark.vue'
defineProps({
  variant: { type: String, default: 'full' }, // full | mark
  size: { type: Number, default: 34 }, // balandlik (px)
  animated: { type: Boolean, default: true },
})
</script>

<template>
  <BrandMark v-if="variant === 'mark'" :size="size" :animated="animated" />
  <img
    v-else :src="logo" alt="TalabaGo" draggable="false"
    class="block w-auto max-w-none shrink-0 self-start object-contain select-none" :class="animated && 'logo-in'"
    :style="{ height: `${size}px` }"
  />
</template>

<style scoped>
.logo-in { animation: logo-in .55s cubic-bezier(.22, 1, .36, 1) both; }
@keyframes logo-in { from { opacity: 0; transform: translateX(-8px); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .logo-in { animation: none; } }
</style>
