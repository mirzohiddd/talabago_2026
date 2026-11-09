<script setup>
/**
 * Bitta reklama banneri (rasm yoki video) — carousel, CRM preview va forma ko‘rinishida ishlatiladi.
 * Video doim: muted + playsinline, loop YO‘Q (carousel "ended" hodisasida keyingisiga o‘tadi).
 */
import { ref, watch } from 'vue'
import { ArrowRight, ImageOff } from 'lucide-vue-next'
import { useAdMedia } from '@/composables/useAdMedia'

const props = defineProps({
  ad: { type: Object, required: true },
  media: { type: Object, default: null }, // forma uchun: hali saqlanmagan fayl
  renderVideo: { type: Boolean, default: true }, // faqat faol va qo‘shni slaydlarda <video> yaratiladi
  eager: Boolean,
})
const emit = defineEmits(['ended', 'error'])
const { src, poster, missing } = useAdMedia(() => props.media ?? props.ad.media)
const video = ref(null)

// Vue "muted" atributini har doim DOM property sifatida qo‘ymaydi — iOS autoplay uchun qo‘lda o‘rnatamiz
watch(video, (v) => {
  if (!v) return
  v.muted = true
  v.defaultMuted = true
  v.setAttribute('muted', '')
  v.setAttribute('playsinline', '')
  v.setAttribute('webkit-playsinline', '')
})

defineExpose({ video })
</script>

<template>
  <div class="ad-slide absolute inset-0 bg-brand-50 overflow-hidden">
    <template v-if="ad.type === 'video'">
      <video
        v-if="renderVideo && src"
        ref="video"
        :src="src"
        :poster="poster || undefined"
        muted
        playsinline
        preload="auto"
        disablepictureinpicture
        disableremoteplayback
        class="size-full object-cover pointer-events-none"
        @ended="emit('ended')"
        @error="emit('error')"
      />
      <img v-else-if="poster" :src="poster" alt="" class="size-full object-cover" draggable="false" />
    </template>
    <img
      v-else-if="src"
      :src="src"
      :alt="ad.title || ad.name"
      :loading="eager ? 'eager' : 'lazy'"
      decoding="async"
      draggable="false"
      class="size-full object-cover"
      @error="emit('error')"
    />
    <div v-if="missing" class="absolute inset-0 grid place-items-center text-muted text-xs gap-1 content-center">
      <ImageOff class="size-6 mx-auto" />{{ $t('Fayl topilmadi') }}
    </div>

    <!-- Matn bloki (dizayn: chapda “Reklama” belgisi, katta sarlavha, tavsif, “Batafsil” tugmasi) -->
    <div v-if="ad.title || ad.description" class="absolute inset-0 bg-gradient-to-r from-[#053B2C]/85 via-[#053B2C]/45 to-transparent pointer-events-none" />
    <div class="absolute inset-y-0 left-0 w-[64%] px-4 py-4 flex flex-col justify-center text-white pointer-events-none">
      <span class="inline-flex items-center h-[22px] px-2.5 rounded-full bg-white text-brand-700 text-[11px] font-semibold w-fit shadow-sm">{{ $t('Reklama') }}</span>
      <p v-if="ad.title" class="font-extrabold text-[19px] leading-[1.15] tracking-[-0.01em] line-clamp-2 mt-2 drop-shadow-sm">{{ ad.title }}</p>
      <p v-if="ad.description" class="text-[12px] leading-snug text-white/90 line-clamp-1 mt-1">{{ ad.description }}</p>
      <span v-if="ad.link" class="ad-cta mt-3 inline-flex items-center gap-1.5 h-8 pl-3.5 pr-3 rounded-full bg-white text-ink text-[12.5px] font-semibold w-fit shadow-md">
        {{ $t('Batafsil') }}<ArrowRight class="size-3.5 transition-transform" />
      </span>
    </div>
  </div>
</template>

<style scoped>
.ad-slide:hover .ad-cta svg { transform: translateX(3px); }
.ad-slide img, .ad-slide video { transition: transform 6s ease-out; }
.ad-slide:hover img { transform: scale(1.04); }
</style>
