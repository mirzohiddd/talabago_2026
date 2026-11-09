<script setup>
import { Search, X } from 'lucide-vue-next'
const model = defineModel({ type: String, default: '' })
defineProps({ placeholder: { type: String, default: 'Qidirish…' } })
</script>
<template>
  <label class="flex items-center gap-2 h-10 px-3 rounded-xl border border-line bg-white w-full sm:w-72 focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10 transition">
    <Search class="size-4 text-muted shrink-0" />
    <input v-model="model" type="search" :placeholder="placeholder" class="flex-1 min-w-0 outline-none text-sm bg-transparent" />
    <button v-if="model" type="button" class="text-muted hover:text-ink" :aria-label="$t('Tozalash')" @click="model = ''"><X class="size-4" /></button>
  </label>
</template>
