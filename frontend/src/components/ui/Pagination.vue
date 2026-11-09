<script setup>
import { computed } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
const page = defineModel({ type: Number, default: 1 })
const props = defineProps({ total: Number, perPage: { type: Number, default: 12 } })
const pages = computed(() => Math.max(1, Math.ceil(props.total / props.perPage)))
const list = computed(() => {
  const p = page.value, n = pages.value
  const s = new Set([1, n, p - 1, p, p + 1].filter((x) => x >= 1 && x <= n))
  const arr = [...s].sort((a, b) => a - b)
  return arr.flatMap((x, i) => (i && x - arr[i - 1] > 1 ? ['…', x] : [x]))
})
function go(p) { page.value = p; window.scrollTo({ top: 0, behavior: 'smooth' }) }
</script>
<template>
  <nav v-if="pages > 1" class="flex items-center justify-center gap-1 pt-6" :aria-label="$t('Sahifalar')">
    <button class="pg" :disabled="page === 1" :aria-label="$t('Oldingi')" @click="go(page - 1)"><ChevronLeft class="size-4" /></button>
    <template v-for="(p, i) in list" :key="i">
      <span v-if="p === '…'" class="w-8 text-center text-muted">…</span>
      <button v-else :class="['pg', p === page && 'bg-ink! text-white!']" :aria-current="p === page ? 'page' : undefined" @click="go(p)">{{ p }}</button>
    </template>
    <button class="pg" :disabled="page === pages" :aria-label="$t('Keyingi')" @click="go(page + 1)"><ChevronRight class="size-4" /></button>
  </nav>
</template>
<style scoped>
@reference "../../style.css";
.pg { @apply min-w-9 h-9 px-2 grid place-items-center rounded-xl text-sm font-semibold text-ink-2 bg-surface hover:bg-line disabled:opacity-40 transition tabular-nums; }
</style>
