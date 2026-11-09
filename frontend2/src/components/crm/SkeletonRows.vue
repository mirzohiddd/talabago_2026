<script setup>
defineProps({ rows: { type: Number, default: 6 }, cols: { type: Number, default: 6 } })
</script>
<template>
  <div class="p-4 space-y-3" aria-busy="true" :aria-label="$t('Yuklanmoqda')">
    <div v-for="r in rows" :key="r" class="flex items-center gap-4">
      <div class="skeleton size-10 shrink-0 rounded-full" />
      <div v-for="c in cols - 1" :key="c" class="skeleton h-4 flex-1" :style="{ maxWidth: c === 1 ? '220px' : '120px' }" />
    </div>
  </div>
</template>
