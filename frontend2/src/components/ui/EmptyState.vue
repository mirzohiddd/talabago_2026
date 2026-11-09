<script setup>
import RoundIllu from '@/components/brand/RoundIllu.vue'
defineProps({ title: String, text: String, illu: { type: String, default: 'books' } })
</script>
<template>
  <div class="flex flex-col items-center text-center py-10 px-6 animate-fade-up" data-testid="empty">
    <slot name="art"><RoundIllu :kind="illu" :size="112" /></slot>
    <h4 class="font-bold text-lg mt-4">{{ title }}</h4>
    <p class="text-muted text-sm mt-1 max-w-xs">{{ text }}</p>
    <div class="mt-5"><slot /></div>
  </div>
</template>
