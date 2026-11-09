<script setup>
defineProps({ label: String, value: [String, Number], icon: [Object, Function], tone: { type: String, default: 'soft' }, hint: String, delta: Number, loading: Boolean, to: [String, Object] })
</script>
<template>
  <component :is="to ? 'RouterLink' : 'div'" :to="to" :class="['relative overflow-hidden rounded-2xl p-4 border transition-all duration-300 hover:-translate-y-0.5 block', tone === 'brand' ? 'bg-brand text-white border-brand' : tone === 'dark' ? 'bg-ink text-white border-ink' : tone === 'warn' ? 'bg-warning/10 border-warning/30' : 'bg-white border-line hover:border-brand-100 hover:shadow-[var(--shadow-card)]']" data-testid="kpi">
    <div class="flex items-start gap-2">
      <p class="text-[12.5px] font-semibold opacity-80 flex-1 leading-tight">{{ label }}</p>
      <component :is="icon" :class="['size-[18px] shrink-0', tone === 'soft' ? 'text-brand-600' : 'opacity-80']" />
    </div>
    <div v-if="loading" class="skeleton h-7 w-16 mt-3 opacity-60" />
    <p v-else class="text-[26px] font-extrabold leading-none tabular-nums mt-3">{{ value }}</p>
    <p v-if="delta != null && !loading" :class="['text-[12px] font-semibold mt-1.5', tone === 'soft' || tone === 'warn' ? (delta ? 'text-success' : 'text-muted') : 'opacity-80']">+{{ delta }} <span class="font-medium opacity-80">{{ hint }}</span></p>
    <p v-else-if="hint && !loading" class="text-[12px] opacity-70 mt-1.5">{{ hint }}</p>
  </component>
</template>
