<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
const page = defineModel({ type: Number, default: 1 })
const props = defineProps({ total: Number, perPage: { type: Number, default: 10 } })
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))
const from = computed(() => (props.total ? (page.value - 1) * props.perPage + 1 : 0))
const to = computed(() => Math.min(props.total, page.value * props.perPage))
</script>
<template>
  <div class="flex items-center justify-between gap-3 px-4 py-3 border-t border-line text-sm">
    <span class="text-muted tabular-nums">{{ from }}–{{ to }} / {{ total }}</span>
    <div class="flex items-center gap-1">
      <button class="icon-btn disabled:opacity-30 disabled:pointer-events-none" :disabled="page <= 1" :aria-label="$t('Oldingi sahifa')" @click="page--"><ChevronLeft class="size-4" /></button>
      <button v-for="p in pages" :key="p" :class="['size-8 rounded-lg text-[13px] font-semibold transition', p === page ? 'bg-ink text-white' : 'hover:bg-surface text-ink-2']" @click="page = p">{{ p }}</button>
      <button class="icon-btn disabled:opacity-30 disabled:pointer-events-none" :disabled="page >= pages" :aria-label="$t('Keyingi sahifa')" @click="page++"><ChevronRight class="size-4" /></button>
    </div>
  </div>
</template>
