<script setup>
/** Jadvaldagi kichik preview: rasm yoki video posteri + ▶ belgisi */
import { Play, ImageOff } from 'lucide-vue-next'
import { useAdMedia } from '@/composables/useAdMedia'
const props = defineProps({ ad: Object, size: { type: String, default: 'md' } })
const { src, poster, missing } = useAdMedia(() => props.ad.media)
</script>

<template>
  <div :class="['relative shrink-0 overflow-hidden rounded-lg bg-surface border border-line', size === 'sm' ? 'w-[70px] h-[42px]' : 'w-20 h-12']">
    <img v-if="ad.type === 'image' && src" :src="src" alt="" class="size-full object-cover" loading="lazy" />
    <template v-else-if="ad.type === 'video'">
      <img v-if="poster" :src="poster" alt="" class="size-full object-cover" loading="lazy" />
      <video v-else-if="src" :src="`${src}#t=0.5`" muted playsinline preload="metadata" class="size-full object-cover" />
      <span class="absolute inset-0 grid place-items-center"><span class="size-5 rounded-full bg-black/60 text-white grid place-items-center"><Play class="size-3" fill="currentColor" /></span></span>
    </template>
    <span v-if="missing" class="absolute inset-0 grid place-items-center text-muted"><ImageOff class="size-4" /></span>
  </div>
</template>
