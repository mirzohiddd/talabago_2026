<script setup>
/** Yulduzli baho: ko‘rsatish (readonly) yoki tanlash (v-model, 1–5). Klaviatura bilan ham boshqariladi. */
import { Star } from 'lucide-vue-next'
const model = defineModel({ type: Number, default: 0 })
const props = defineProps({ readonly: Boolean, size: { type: Number, default: 18 }, value: Number })
const shown = () => (props.readonly ? props.value ?? model.value : model.value)
function pick(n) { if (!props.readonly) model.value = n }
</script>

<template>
  <span :class="['inline-flex items-center gap-0.5', !readonly && 'gap-1']" :role="readonly ? 'img' : 'radiogroup'" :aria-label="readonly ? `${$t('Baho')}: ${shown()}/5` : $t('Baho')">
    <component :is="readonly ? 'span' : 'button'" v-for="n in 5" :key="n" :type="readonly ? undefined : 'button'"
      :role="readonly ? undefined : 'radio'" :aria-checked="readonly ? undefined : model === n" :aria-label="readonly ? undefined : `${n}`"
      :class="['leading-none', !readonly && 'p-1 rounded-lg hover:bg-brand-50 transition']" :data-testid="readonly ? undefined : `star-${n}`" @click="pick(n)">
      <Star :style="{ width: `${size}px`, height: `${size}px` }" :class="n <= Math.round(shown() || 0) ? 'fill-[#f5b301] text-[#f5b301]' : 'text-[#d4d8dd]'" />
    </component>
  </span>
</template>
