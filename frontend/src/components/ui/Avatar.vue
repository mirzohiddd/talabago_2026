<script setup>
import { initials } from '@/utils/format'
import { useMediaUrl } from '@/composables/useMediaUrl'
const props = defineProps({ name: String, src: String, size: { type: String, default: 'md' } })
const url = useMediaUrl(() => props.src)
const sz = { lg: 'size-16 text-xl', sm: 'size-8 text-xs', md: 'size-11 text-sm', xl: 'size-20 text-2xl' }
</script>
<template>
  <span :class="['grid place-items-center rounded-full bg-brand-50 text-brand-700 font-bold shrink-0 overflow-hidden', sz[size]]">
    <img v-if="url" :src="url" alt="" loading="lazy" decoding="async" class="size-full object-cover" />
    <template v-else>{{ initials(name) }}</template>
  </span>
</template>