<script setup>
/** Taxminiy joylashuv: aniq manzil emas, ~500 m radiusli hudud (OpenStreetMap). */
import { computed, ref } from 'vue'
import { MapPinned, ExternalLink } from 'lucide-vue-next'
import { openLink } from '@/services/telegram'
const props = defineProps({ lat: Number, lng: Number, label: String })
const show = ref(false)
const src = computed(() => `https://www.openstreetmap.org/export/embed.html?bbox=${props.lng - 0.012},${props.lat - 0.007},${props.lng + 0.012},${props.lat + 0.007}&layer=mapnik`)
const ext = computed(() => `https://www.openstreetmap.org/?mlat=${props.lat}&mlon=${props.lng}#map=15/${props.lat}/${props.lng}`)
</script>
<template>
  <div class="rounded-2xl overflow-hidden border border-line">
    <div class="relative aspect-[16/9] bg-brand-25 bg-dots">
      <iframe v-if="show" :src="src" class="absolute inset-0 size-full border-0" loading="lazy" :title="$t('Xarita')" referrerpolicy="no-referrer" />
      <button v-else class="absolute inset-0 grid place-items-center text-center" @click="show = true">
        <span><MapPinned class="size-8 mx-auto text-brand-600" /><span class="block mt-2 text-sm font-semibold">{{ $t('Xaritani ko‘rsatish') }}</span><span class="block text-xs text-muted">{{ label }}</span></span>
      </button>
      <span class="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 size-28 rounded-full bg-brand/20 ring-2 ring-brand/60" />
    </div>
    <div class="flex items-center gap-2 px-3 py-2.5 text-xs text-muted">
      <span class="flex-1">{{ $t('Taxminiy joylashuv (~500 m). Aniq manzilni uy egasi beradi.') }}</span>
      <button class="inline-flex items-center gap-1 font-semibold text-brand-600 hover:underline" @click="openLink(ext)">{{ $t('Ochish') }}<ExternalLink class="size-3.5" /></button>
    </div>
  </div>
</template>
