<script setup>
import { computed } from 'vue'
import { STATUS } from '@shared/domain.js'
const props = defineProps({ status: String, label: String, tone: String })
const tones = {
  brand: 'bg-brand text-white',
  green: 'bg-success/10 text-success',
  red: 'bg-danger/10 text-danger',
  amber: 'bg-warning/15 text-[#a15c00]',
  blue: 'bg-[#2f6bff]/10 text-[#2f6bff]',
  gray: 'bg-surface text-ink-2',
}
const meta = computed(() => STATUS[props.status] || { label: props.label || props.status, tone: props.tone || 'gray' })
</script>

<template>
  <span :class="['inline-flex items-center gap-1.5 h-6 px-2.5 rounded-full text-xs font-semibold whitespace-nowrap', tones[tone || meta.tone]]" :data-status="status">
    <span class="size-1.5 rounded-full bg-current" />{{ label || $t(meta.label) }}
  </span>
</template>
