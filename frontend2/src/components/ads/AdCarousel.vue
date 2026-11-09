<script setup>
/**
 * Header Carousel — sahifa tepasidagi reklama bannerlari.
 *  - Rasm: har 5 soniyada almashadi.
 *  - Video: muted, playsinline, autoplay, loop yo‘q → tugagach keyingi bannerga o‘tadi.
 *  - Swipe, pagination dots, klaviatura (←/→), “Reklama” belgisi.
 *  - Ekranda ko‘rinmasa yoki ilova fonda bo‘lsa — to‘xtaydi.
 *  - Boshlanish/tugash vaqti kelganda reklama avtomatik paydo bo‘ladi / yashiriladi (useNow).
 */
import { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ChevronLeft, ChevronRight } from 'lucide-vue-next'
import AdSlide from './AdSlide.vue'
import { adsStore, ensureAdsLoaded, adsApi } from '@/services/ads'
import { isAdVisible, sortAds, IMAGE_SLIDE_MS } from '@/config/ads'
import { useNow } from '@/composables/useNow'
import { openLink, haptic } from '@/services/platform'

const props = defineProps({
  placement: { type: String, default: '' },
  items: { type: Array, default: null }, // CRM preview: tayyor ro‘yxat
  preview: Boolean, // true → statistika yozilmaydi
})

const VIDEO_FALLBACK_MS = 6000 // autoplay bloklansa yoki video buzilsa
const VIEW_AFTER_MS = 1000 // ≥1 s ko‘rinsa — 1 ta ko‘rish

const now = useNow()
ensureAdsLoaded()

const slides = computed(() =>
  props.items ??
  sortAds(adsStore.items.filter((a) => isAdVisible(a, props.placement, now.value))),
)
const count = computed(() => slides.value.length)
const ids = computed(() => slides.value.map((s) => s.id).join('|'))

const index = ref(0)
const activeId = ref(null)
const progress = ref(0)
const dragging = ref(false)
const dragX = ref(0)
const inView = ref(true)
const pageVisible = ref(!document.hidden)
const videoFailed = ref(false)
const root = ref(null)
const slideRefs = ref([])

let elapsed = 0
let viewTime = 0
let viewLogged = false
let lastCT = -1
let stuckMs = 0
const logged = new Set() // har bir reklama shu sahifada 1 marta hisoblanadi

const playing = computed(() => inView.value && pageVisible.value && !dragging.value)
const current = computed(() => slides.value[index.value])
const activeVideo = () => slideRefs.value[index.value]?.video ?? null

function goTo(i, { user = false } = {}) {
  if (!count.value) return
  index.value = ((i % count.value) + count.value) % count.value
  activeId.value = slides.value[index.value].id
  if (user) haptic.select()
  restart()
}
const next = (o) => goTo(index.value + 1, o)
const prev = (o) => goTo(index.value - 1, o)

function restart() {
  elapsed = 0; viewTime = 0; viewLogged = false; lastCT = -1; stuckMs = 0
  progress.value = 0
  videoFailed.value = false
  nextTick(() => syncVideos(true))
}

function syncVideos(fromStart = false) {
  slideRefs.value.forEach((s, i) => {
    const v = s?.video
    if (!v) return
    if (i === index.value && playing.value) {
      if (fromStart || v.ended) v.currentTime = 0
      v.muted = true
      const p = v.play()
      if (p?.catch) p.catch(() => { if (i === index.value) videoFailed.value = true })
    } else {
      v.pause()
      if (i !== index.value && v.currentTime) v.currentTime = 0
    }
  })
}

function onEnded(i) {
  if (i !== index.value) return
  if (count.value > 1) next()
  else restart() // bitta video bo‘lsa — qaytadan (loop atributisiz)
}
function onError(i) {
  if (i === index.value) videoFailed.value = true
}

// Ro‘yxat o‘zgarsa (reklama vaqti tugadi / boshlandi) — faol slaydni saqlab qolish
watch(ids, () => {
  if (!count.value) { index.value = 0; activeId.value = null; return }
  const i = slides.value.findIndex((s) => s.id === activeId.value)
  if (i >= 0) index.value = i
  else goTo(Math.min(index.value, count.value - 1))
}, { immediate: true })

watch(playing, (p) => {
  const v = activeVideo()
  if (!v) return
  if (p) { v.muted = true; v.play()?.catch?.(() => (videoFailed.value = true)) } else v.pause()
})

// ---------- Vaqt sikli (requestAnimationFrame) ----------
let raf = 0
let last = 0
function frame(t) {
  const dt = last ? Math.min(t - last, 100) : 0
  last = t
  const s = current.value
  if (s && playing.value) {
    if (s.type === 'image' || videoFailed.value) {
      const dur = s.type === 'image' ? IMAGE_SLIDE_MS : VIDEO_FALLBACK_MS
      if (count.value > 1) {
        elapsed += dt
        progress.value = Math.min(1, elapsed / dur)
        if (elapsed >= dur) next()
      }
    } else {
      const v = activeVideo()
      if (v && v.duration) progress.value = Math.min(1, v.currentTime / v.duration)
      // video qotib qolsa (tarmoq) — 8 soniyadan keyin zaxira taymerga o‘tish
      if (v) {
        stuckMs = v.currentTime === lastCT ? stuckMs + dt : 0
        lastCT = v.currentTime
        if (stuckMs > 8000) { videoFailed.value = true; elapsed = 0 }
      }
    }
    viewTime += dt
    if (!viewLogged && viewTime >= VIEW_AFTER_MS) {
      viewLogged = true
      if (!props.preview && !logged.has(s.id)) { logged.add(s.id); adsApi.trackView(s.id) }
    }
  }
  raf = requestAnimationFrame(frame)
}

// ---------- Swipe (pointer events, vertikal scroll saqlanadi) ----------
let sx = 0, sy = 0, pid = null, decided = false, horiz = false, moved = false
function onDown(e) {
  if (e.pointerType === 'mouse' && e.button !== 0) return
  pid = e.pointerId; sx = e.clientX; sy = e.clientY
  decided = horiz = moved = false
}
function onMove(e) {
  if (e.pointerId !== pid) return
  const dx = e.clientX - sx, dy = e.clientY - sy
  if (!decided && (Math.abs(dx) > 8 || Math.abs(dy) > 8)) {
    decided = true
    horiz = Math.abs(dx) > Math.abs(dy)
    if (horiz) { dragging.value = true; root.value?.setPointerCapture?.(pid) }
  }
  if (horiz) { moved = true; dragX.value = count.value > 1 ? dx : dx * 0.25 }
}
function onUp(e) {
  if (e.pointerId !== pid) return
  pid = null
  if (!horiz) return
  const w = root.value?.clientWidth || 1
  const dx = dragX.value
  dragging.value = false
  dragX.value = 0
  if (count.value > 1 && dx < -w * 0.18) next({ user: true })
  else if (count.value > 1 && dx > w * 0.18) prev({ user: true })
  else nextTick(() => syncVideos(false))
}
function onSlideClick(ad) {
  if (moved) { moved = false; return }
  if (!ad.link) return
  haptic.tap()
  if (!props.preview) adsApi.trackClick(ad.id)
  openLink(ad.link)
}
function onKey(e) {
  if (e.key === 'ArrowRight') next({ user: true })
  else if (e.key === 'ArrowLeft') prev({ user: true })
}

// ---------- Ko‘rinish kuzatuvi ----------
let io = null
const onVisibility = () => { pageVisible.value = !document.hidden }
onMounted(() => {
  raf = requestAnimationFrame(frame)
  document.addEventListener('visibilitychange', onVisibility)
  watch(root, (el) => {
    io?.disconnect()
    if (!el || !('IntersectionObserver' in window)) return
    io = new IntersectionObserver(([en]) => { inView.value = en.isIntersecting && en.intersectionRatio >= 0.5 }, { threshold: [0, 0.5, 1] })
    io.observe(el)
  }, { immediate: true })
})
onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  io?.disconnect()
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<template>
  <Transition name="fade">
    <section v-if="count" class="ad-carousel pt-3" aria-roledescription="carousel" :aria-label="$t('Reklama')">
      <div
        ref="root"
        tabindex="0"
        class="group relative overflow-hidden rounded-[22px] bg-brand-50 aspect-[5/3] shadow-[0_10px_30px_-12px_rgba(5,150,105,.45)] select-none outline-none focus-visible:ring-4 focus-visible:ring-brand/20 [touch-action:pan-y] cursor-pointer"
        @pointerdown="onDown"
        @pointermove="onMove"
        @pointerup="onUp"
        @pointercancel="onUp"
        @keydown="onKey"
      >
        <div
          class="flex h-full"
          :style="{
            transform: `translate3d(calc(${-index * 100}% + ${dragX}px),0,0)`,
            transition: dragging ? 'none' : 'transform .45s cubic-bezier(.22,1,.36,1)',
          }"
        >
          <div
            v-for="(ad, i) in slides"
            :key="ad.id"
            class="relative shrink-0 w-full h-full"
            role="group"
            aria-roledescription="slide"
            :aria-label="`${i + 1} / ${count}`"
            :aria-hidden="i !== index"
            @click="onSlideClick(ad)"
          >
            <AdSlide
              :ref="(el) => (slideRefs[i] = el)"
              :ad="ad"
              :eager="i === 0"
              :render-video="Math.abs(i - index) <= 1 || (index === 0 && i === count - 1)"
              @ended="onEnded(i)"
              @error="onError(i)"
            />
          </div>
        </div>

        <template v-if="count > 1">
          <button class="nav-btn left-2" :aria-label="$t('Oldingi reklama')" @pointerdown.stop @click.stop="prev({ user: true })"><ChevronLeft class="size-5" /></button>
          <button class="nav-btn right-2" :aria-label="$t('Keyingi reklama')" @pointerdown.stop @click.stop="next({ user: true })"><ChevronRight class="size-5" /></button>
        </template>
      </div>

      <div v-if="count > 1" class="flex justify-center items-center gap-2 pt-2.5" role="tablist" :aria-label="$t('Reklamalar')">
        <button
          v-for="(ad, i) in slides"
          :key="ad.id"
          role="tab"
          :aria-selected="i === index"
          :aria-label="`${i + 1}-reklama`"
          class="relative h-2 rounded-full overflow-hidden transition-all duration-300 p-0"
          :class="i === index ? 'w-5 bg-brand-200' : 'w-2 bg-[#D9DEDB] hover:bg-[#c3cac6]'"
          @click="goTo(i, { user: true })"
        >
          <span v-if="i === index" class="absolute inset-y-0 left-0 bg-brand rounded-full" :style="{ width: `${Math.max(progress, 0.08) * 100}%` }" />
        </button>
      </div>
    </section>
  </Transition>
</template>

<style scoped>
@reference "../../style.css";
.nav-btn {
  @apply absolute top-1/2 -translate-y-1/2 size-8 rounded-full bg-white/90 text-ink shadow-md hidden place-items-center opacity-0 transition-opacity hover:bg-white;
}
@media (hover: hover) and (pointer: fine) {
  .nav-btn { display: grid; }
  .group:hover .nav-btn, .group:focus-visible .nav-btn { opacity: 1; }
}
</style>
