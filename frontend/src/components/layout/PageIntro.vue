<script setup>
/**
 * Sahifa boshidagi ixcham kirish bloki: sarlavha, qisqa izoh va burchakdagi illustratsiya.
 * Matnlar route.meta’dan (title, subtitle, illu) olinadi; kerak bo‘lsa prop bilan almashtiriladi.
 * vertical — desktopda reklama carousel yonidagi ustun uchun.
 */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import RoundIllu from '@/components/brand/RoundIllu.vue'

const props = defineProps({ title: String, subtitle: String, illu: String, vertical: Boolean })
const route = useRoute()
const t = computed(() => props.title ?? route.meta.title)
const sub = computed(() => props.subtitle ?? route.meta.subtitle)
const kind = computed(() => props.illu ?? route.meta.illu)
</script>

<template>
  <section
    :class="['page-intro relative overflow-hidden rounded-[22px] border border-brand-100/80 bg-brand-25 animate-fade-up',
      vertical ? 'h-full p-5 flex flex-col' : 'p-4 pr-3 sm:p-5 lg:px-7 lg:py-6 flex items-center gap-3']"
    data-testid="page-intro"
  >
    <span class="pointer-events-none absolute -right-10 -bottom-14 size-44 rounded-full border-[18px] border-brand-100/60" aria-hidden="true" />
    <div :class="['relative min-w-0', vertical ? 'order-2 mt-auto' : 'flex-1']">
      <h1 class="text-[21px] lg:text-[26px] font-extrabold tracking-tight leading-tight" data-testid="page-title">{{ $t(t || '') }}</h1>
      <p v-if="sub || $slots.subtitle" class="text-[13px] lg:text-sm text-ink-2 mt-1 leading-snug"><slot name="subtitle">{{ $t(sub) }}</slot></p>
      <div v-if="$slots.default" class="mt-3 flex flex-wrap items-center gap-2"><slot /></div>
    </div>
    <div v-if="kind" :class="['relative shrink-0', vertical ? 'order-1 self-center my-2 size-[150px]' : 'size-[78px] sm:size-[96px] lg:size-[118px]']">
      <RoundIllu :kind="kind" size="100%" bare />
    </div>
  </section>
</template>
