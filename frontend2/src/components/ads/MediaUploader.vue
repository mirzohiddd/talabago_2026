<script setup>
/**
 * Rasm/video yuklash: format (kengaytma + MIME + haqiqiy dekodlash), hajm, video davomiyligi tekshiriladi.
 * Video uchun birinchi kadrdan poster (JPEG) yasaladi — carousel’da qora ekran chiqmasligi uchun.
 * Natija: hali saqlanmagan "pending" obyekt (file Blob + previewUrl); saqlash ads servisida.
 */
import { t } from '@/i18n'
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { UploadCloud, RefreshCw, Trash2, AlertTriangle, Loader2, FileImage, FileVideo } from 'lucide-vue-next'
import { MEDIA_RULES, AD_ASPECT } from '@/config/ads'
import { useAdMedia } from '@/composables/useAdMedia'

const model = defineModel({ type: Object, default: null }) // pending
const props = defineProps({
  type: { type: String, required: true }, // image | video
  existing: { type: Object, default: null }, // saqlangan ad.media
  error: String,
})
const emit = defineEmits(['remove-existing'])

const input = ref(null)
const busy = ref(false)
const localError = ref('')
const over = ref(false)
const rules = computed(() => MEDIA_RULES[props.type])
const accept = computed(() => [...rules.value.exts.map((e) => '.' + e), ...rules.value.mimes].join(','))
const shown = computed(() => model.value || props.existing)
const { src, poster } = useAdMedia(shown)

const mb = (b) => (b / 1024 / 1024).toFixed(b < 1024 * 1024 ? 2 : 1) + ' MB'
const fmt = (m) => (m?.mime || '').split('/')[1]?.toUpperCase().replace('JPEG', 'JPG') || '—'
const secs = (d) => (d ? `${Math.round(d)} s` : null)

function revokePending(p) {
  if (p?.previewUrl) URL.revokeObjectURL(p.previewUrl)
  if (p?.posterPreviewUrl) URL.revokeObjectURL(p.posterPreviewUrl)
}
watch(model, (n, o) => { if (o && o !== n) revokePending(o) })
watch(() => props.type, () => { localError.value = '' })
onBeforeUnmount(() => revokePending(model.value))

function loadImage(url) {
  return new Promise((resolve, reject) => {
    const img = new Image()
    img.onload = () => resolve({ width: img.naturalWidth, height: img.naturalHeight })
    img.onerror = reject
    img.src = url
  })
}
function loadVideo(url) {
  return new Promise((resolve, reject) => {
    const v = document.createElement('video')
    v.muted = true; v.playsInline = true; v.preload = 'auto'
    const t = setTimeout(() => reject(new Error('timeout')), 15000)
    v.onloadedmetadata = () => {
      const meta = { width: v.videoWidth, height: v.videoHeight, duration: v.duration }
      if (!meta.width || !Number.isFinite(meta.duration)) { clearTimeout(t); return reject(new Error('meta')) }
      // poster: 0.5-soniyadagi kadr
      v.currentTime = Math.min(0.5, meta.duration / 2)
      v.onseeked = () => {
        clearTimeout(t)
        try {
          const w = Math.min(640, meta.width), h = Math.round((w * meta.height) / meta.width)
          const c = document.createElement('canvas'); c.width = w; c.height = h
          c.getContext('2d').drawImage(v, 0, 0, w, h)
          c.toBlob((poster) => resolve({ ...meta, poster }), 'image/jpeg', 0.78)
        } catch { resolve({ ...meta, poster: null }) }
      }
    }
    v.onerror = () => { clearTimeout(t); reject(new Error('decode')) }
    v.src = url
  })
}

async function handle(file) {
  localError.value = ''
  if (!file) return
  const r = rules.value
  const ext = (file.name.split('.').pop() || '').toLowerCase()
  if (!r.exts.includes(ext) || (file.type && !r.mimes.includes(file.type))) {
    localError.value = t('Format noto‘g‘ri (.{ext}). Ruxsat etilgan: {list}.', { ext: ext || '?', list: t(r.label) })
    return
  }
  if (!file.size) { localError.value = 'Fayl bo‘sh.'; return }
  if (file.size > r.maxBytes) {
    localError.value = `Fayl juda katta: ${mb(file.size)}. Maksimal hajm — ${mb(r.maxBytes)}.`
    return
  }
  busy.value = true
  const url = URL.createObjectURL(file)
  try {
    const mime = file.type || (props.type === 'image' ? `image/${ext === 'jpg' ? 'jpeg' : ext}` : `video/${ext}`)
    let meta
    if (props.type === 'image') meta = await loadImage(url)
    else {
      meta = await loadVideo(url)
      if (meta.duration > r.maxSeconds + 0.5) {
        URL.revokeObjectURL(url)
        localError.value = `Video juda uzun: ${Math.round(meta.duration)} s. Maksimal — ${r.maxSeconds} s.`
        return
      }
    }
    const warnings = []
    const ratio = meta.width / meta.height
    if (Math.abs(ratio - AD_ASPECT) / AD_ASPECT > 0.15) warnings.push(t('Nisbat {w}×{h} — 5:3 emas, chetlari kesib ko‘rsatiladi. Tavsiya: 1200×720.', { w: meta.width, h: meta.height }))
    if (meta.width < 800) warnings.push(t('O‘lcham kichik — banner xira ko‘rinishi mumkin (kamida 800 px kenglik tavsiya etiladi).'))
    if (mime === 'video/webm') warnings.push(t('WebM ba’zi iPhone’larda ijro etilmaydi — MP4 (H.264) tavsiya etiladi.'))
    model.value = {
      file, name: file.name, mime, size: file.size,
      width: meta.width, height: meta.height, duration: meta.duration ?? null,
      poster: meta.poster ?? null,
      previewUrl: url,
      posterPreviewUrl: meta.poster ? URL.createObjectURL(meta.poster) : null,
      warnings,
    }
  } catch {
    URL.revokeObjectURL(url)
    localError.value = 'Faylni o‘qib bo‘lmadi — u buzilgan yoki brauzer bu formatni qo‘llamaydi.'
  } finally {
    busy.value = false
    if (input.value) input.value.value = ''
  }
}

function onDrop(e) { over.value = false; handle(e.dataTransfer?.files?.[0]) }
function remove() {
  if (model.value) model.value = null
  else emit('remove-existing')
}
</script>

<template>
  <div>
    <input ref="input" type="file" class="hidden" :accept="accept" data-testid="ad-file" @change="handle($event.target.files[0])" />

    <!-- Preview -->
    <div v-if="shown && !busy" class="rounded-2xl border border-line overflow-hidden bg-white">
      <div class="relative aspect-[5/3] bg-surface">
        <img v-if="type === 'image' && src" :src="src" alt="Preview" class="size-full object-cover" />
        <video v-else-if="type === 'video' && src" :src="src" :poster="poster || undefined" class="size-full object-cover bg-ink" controls muted playsinline preload="metadata" />
        <span class="absolute left-2.5 top-2.5 h-[22px] px-2 rounded-md bg-black/55 text-white text-[11px] font-semibold inline-flex items-center">{{ $t('Preview') }}</span>
      </div>
      <div class="p-3 flex flex-wrap items-center gap-2">
        <component :is="type === 'image' ? FileImage : FileVideo" class="size-[18px] text-brand-600 shrink-0" />
        <span class="text-sm font-semibold truncate max-w-[45%]">{{ shown.name || 'Joriy fayl' }}</span>
        <span class="chip">{{ fmt(shown) }}</span>
        <span v-if="shown.size" class="chip">{{ mb(shown.size) }}</span>
        <span v-if="shown.width" class="chip">{{ shown.width }}×{{ shown.height }}</span>
        <span v-if="secs(shown.duration)" class="chip">{{ secs(shown.duration) }}</span>
        <div class="ml-auto flex gap-1.5">
          <button type="button" class="act" @click="input.click()"><RefreshCw class="size-4" />{{ $t('Almashtirish') }}</button>
          <button type="button" class="act text-danger! hover:bg-danger/10!" :aria-label="$t('Faylni olib tashlash')" @click="remove"><Trash2 class="size-4" /></button>
        </div>
      </div>
      <ul v-if="model?.warnings?.length" class="px-3 pb-3 space-y-1.5">
        <li v-for="w in model.warnings" :key="w" class="flex gap-2 text-[12.5px] text-[#a15c00] bg-warning/10 rounded-lg px-2.5 py-2"><AlertTriangle class="size-4 shrink-0 mt-px" />{{ w }}</li>
      </ul>
    </div>

    <!-- Yuklash zonasi -->
    <button
      v-else
      type="button"
      :class="[
        'w-full aspect-[5/3] max-h-56 rounded-2xl border-2 border-dashed grid place-items-center text-center px-6 transition-colors',
        over ? 'border-brand bg-brand-50' : (error || localError) ? 'border-danger/60 bg-danger/5' : 'border-line hover:border-brand-200 hover:bg-brand-50/40',
      ]"
      :disabled="busy"
      @click="input.click()"
      @dragover.prevent="over = true"
      @dragleave="over = false"
      @drop.prevent="onDrop"
    >
      <div v-if="busy" class="flex flex-col items-center gap-2 text-muted text-sm"><Loader2 class="size-7 animate-spin text-brand-600" />{{ $t('Fayl tekshirilmoqda…') }}</div>
      <div v-else class="flex flex-col items-center">
        <span class="size-12 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center mb-2"><UploadCloud class="size-6" /></span>
        <p class="font-semibold text-[15px]">{{ type === 'image' ? 'Rasm yuklash' : 'Video yuklash' }}</p>
        <p class="text-[12.5px] text-muted mt-0.5">{{ $t(rules.label) }}</p>
        <p class="text-[12px] text-muted">{{ $t('Tavsiya: 1200×720 (5:3)') }}</p>
      </div>
    </button>
    <p v-if="localError || error" class="mt-1.5 text-xs text-danger" data-error>{{ localError || error }}</p>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.chip { @apply inline-flex items-center h-6 px-2 rounded-md bg-surface text-[12px] font-semibold text-ink-2; }
.act { @apply inline-flex items-center gap-1.5 h-8 px-2.5 rounded-lg text-[13px] font-semibold text-ink-2 hover:bg-surface transition; }
</style>
