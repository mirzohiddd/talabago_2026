<script setup>
import { useRoute } from 'vue-router'
import { haptic } from '@/services/telegram'
defineProps({ items: { type: Array, required: true } })
const route = useRoute()
const active = (it) => route.path === it.to || route.path.startsWith(it.to + '/')
</script>

<template>
  <nav class="lg:hidden fixed bottom-0 inset-x-0 z-30 bg-white/95 backdrop-blur-xl border-t border-line safe-bottom" :aria-label="$t('Asosiy menyu')" data-testid="bottom-nav">
    <div class="max-w-2xl mx-auto grid px-1 pt-1.5" :style="{ gridTemplateColumns: `repeat(${items.length}, minmax(0,1fr))` }">
      <RouterLink
        v-for="it in items" :key="it.to" :to="it.to"
        class="relative flex flex-col items-center justify-center gap-1 h-[54px] rounded-2xl transition-colors active:scale-95 min-w-0"
        :class="active(it) ? 'text-brand-600' : 'text-[#7C8580] hover:text-ink'"
        :aria-current="active(it) ? 'page' : undefined"
        @click="haptic.select()"
      >
        <span :class="['grid place-items-center h-7 w-12 rounded-full transition-all duration-300', active(it) && 'bg-brand-50']">
          <component :is="it.icon" class="size-[21px]" :stroke-width="active(it) ? 2.4 : 2" />
        </span>
        <span :class="['text-[10.5px] leading-none truncate max-w-full px-0.5', active(it) ? 'font-bold' : 'font-medium']">{{ $t(it.label) }}</span>
      </RouterLink>
    </div>
  </nav>
</template>
