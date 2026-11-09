<script setup>
/** Holat belgisi + keyingi o‘zgarishgacha teskari sanoq (Toshkent vaqti bo‘yicha) */
import { t } from '@/i18n'
import { computed } from 'vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { AD_STATES, adState, msToNextChange } from '@/config/ads'
import { formatTashkent, humanDuration } from '@/utils/tashkentTime'

const props = defineProps({ ad: Object, now: Number, compact: Boolean, wrap: Boolean })
const state = computed(() => adState(props.ad, props.now))
const meta = computed(() => AD_STATES[state.value])
const hint = computed(() => {
  const ms = msToNextChange(props.ad, props.now)
  switch (state.value) {
    case 'live': return t('tugashiga {d}', { d: humanDuration(ms) })
    case 'scheduled': return t('boshlanishiga {d}', { d: humanDuration(ms) })
    case 'inactive': return t('qo‘lda o‘chirilgan')
    default: return t('{d} da tugagan', { d: formatTashkent(props.ad.endAt) })
  }
})
</script>

<template>
  <div class="min-w-0">
    <StatusBadge :label="$t(meta.label)" :tone="meta.tone" />
    <p v-if="!compact" :class="['text-[11.5px] text-muted mt-1 tabular-nums leading-snug', !wrap && 'whitespace-nowrap']">{{ hint }}</p>
  </div>
</template>
