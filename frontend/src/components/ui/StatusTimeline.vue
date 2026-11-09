<script setup>
/** Ariza / so‘rov holatlari tarixi */
import { STATUS } from '@shared/domain.js'
defineProps({ history: { type: Array, default: () => [] } })
const dot = { green: 'bg-success', red: 'bg-danger', amber: 'bg-warning', blue: 'bg-[#2f6bff]', brand: 'bg-brand', gray: 'bg-[#c7c7cc]' }
</script>
<template>
  <ol class="relative pl-5">
    <li v-for="(h, i) in history" :key="i" class="relative pb-3 last:pb-0">
      <span v-if="i < history.length - 1" class="absolute -left-[13px] top-3 bottom-0 w-px bg-line" />
      <span :class="['absolute -left-[17px] top-1 size-[9px] rounded-full ring-4 ring-white', dot[STATUS[h.status]?.tone || 'gray']]" />
      <p class="text-[13px] font-semibold leading-tight">{{ $t(STATUS[h.status]?.label || h.status) }}</p>
      <p class="text-xs text-muted tabular-nums">{{ $dateTime(h.at) }}</p>
      <p v-if="h.note" class="text-xs text-ink-2 mt-0.5">{{ h.note }}</p>
    </li>
  </ol>
</template>
