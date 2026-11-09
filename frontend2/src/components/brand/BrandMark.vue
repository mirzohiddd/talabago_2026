<script setup>
/** TalabaGo belgisi — logodagi “T” (qalpoq va aylana bilan). Yig‘ilgan sidebar, splash va favicon uchun. */
import mark from '@/assets/brand/logo-mark.webp'
defineProps({ size: { type: Number, default: 40 }, animated: { type: Boolean, default: true } })
</script>

<template>
  <img :src="mark" alt="TalabaGo" :width="size" :height="size" draggable="false" class="shrink-0 self-start object-contain select-none" :class="animated && 'mark-in'" />
</template>

<style scoped>
.mark-in { animation: mark-in .6s cubic-bezier(.22, 1, .36, 1) both; }
@keyframes mark-in { from { opacity: 0; transform: translateY(-6px) scale(.9) rotate(-6deg); } to { opacity: 1; transform: none; } }
@media (prefers-reduced-motion: reduce) { .mark-in { animation: none; } }
</style>
