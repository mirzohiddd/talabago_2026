<script setup>
import { haptic } from '@/services/platform'
const model = defineModel({ type: Boolean })
</script>
<template>
  <button
    type="button" role="switch" :aria-checked="model"
    :class="['relative w-12 h-7 rounded-full transition-colors duration-300', model ? 'bg-brand' : 'bg-[#dcdce0]']"
    @click="haptic.select(); model = !model"
  >
    <span :class="['absolute top-1 left-1 size-5 rounded-full bg-white shadow transition-transform duration-300 ease-[cubic-bezier(.34,1.56,.64,1)]', model && 'translate-x-5']" />
  </button>
</template>
