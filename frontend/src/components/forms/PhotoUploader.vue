<script setup>
/**
 * 3–10 ta rasm: qo‘shish, tartiblash (drag & drop yoki tugmalar), asosiy rasmni belgilash, o‘chirish.
 * Rasm yuklashdan oldin brauzerda kichraytiriladi (max 1600px, JPEG) va IndexedDB / serverga yoziladi.
 */
import { ref } from 'vue'
import { ImagePlus, Star, ChevronLeft, ChevronRight, X, Loader2 } from 'lucide-vue-next'
import { uploadFile } from '@/services'
import { useMediaList } from '@/composables/useMediaUrl'
import { HOUSE_PHOTOS } from '@/config/roles'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const photos = defineModel({ type: Array, default: () => [] })
defineProps({ error: String })
const urls = useMediaList(photos)
const busy = ref(0)
const input = ref(null)
const dragFrom = ref(null)

async function shrink(file) {
  const bmp = await createImageBitmap(file).catch(() => null)
  if (!bmp) return file
  const k = Math.min(1, 1600 / Math.max(bmp.width, bmp.height))
  const c = Object.assign(document.createElement('canvas'), { width: Math.round(bmp.width * k), height: Math.round(bmp.height * k) })
  c.getContext('2d').drawImage(bmp, 0, 0, c.width, c.height)
  return new Promise((r) => c.toBlob((b) => r(b || file), 'image/jpeg', 0.82))
}
async function onFiles(e) {
  const files = [...(e.target.files || e.dataTransfer?.files || [])].filter((f) => /^image\/(jpeg|png|webp)$/.test(f.type))
  e.target.value = ''
  const room = HOUSE_PHOTOS.max - photos.value.length
  if (files.length > room) toast(t('Ko‘pi bilan {n} ta rasm', { n: HOUSE_PHOTOS.max }), 'error')
  // defineModel qiymati ota komponent qayta chizilgunga qadar eskirgan bo‘lishi mumkin — mahalliy ro‘yxat bilan ishlaymiz
  const list = [...photos.value]
  for (const f of files.slice(0, room)) {
    if (f.size > 15 * 1048576) { toast(t('Rasm hajmi juda katta'), 'error'); continue }
    busy.value++
    try { list.push(await uploadFile(await shrink(f), 'ph')); photos.value = [...list] } catch { toast(t('Rasmni yuklab bo‘lmadi'), 'error') }
    busy.value--
  }
}
function move(i, d) {
  const a = [...photos.value]; const j = i + d
  if (j < 0 || j >= a.length) return
  ;[a[i], a[j]] = [a[j], a[i]]; photos.value = a
}
function makeMain(i) { const a = [...photos.value]; a.unshift(...a.splice(i, 1)); photos.value = a }
function remove(i) { photos.value = photos.value.filter((_, k) => k !== i) }
function onDrop(i) {
  if (dragFrom.value == null || dragFrom.value === i) return
  const a = [...photos.value]; const [x] = a.splice(dragFrom.value, 1); a.splice(i, 0, x); photos.value = a
  dragFrom.value = null
}
</script>

<template>
  <div>
    <div class="flex items-baseline justify-between mb-1.5">
      <span class="label mb-0!">{{ $t('Rasmlar') }} <span class="text-danger">*</span></span>
      <span class="text-xs text-muted tabular-nums" data-testid="photo-count">{{ photos.length }} / {{ HOUSE_PHOTOS.max }} · {{ $t('kamida {n} ta', { n: HOUSE_PHOTOS.min }) }}</span>
    </div>
    <div class="grid grid-cols-3 sm:grid-cols-4 gap-2.5" @dragover.prevent @drop.prevent="!dragFrom && onFiles($event)">
      <div
        v-for="(u, i) in urls" :key="photos[i]" draggable="true"
        :class="['group relative aspect-square rounded-xl overflow-hidden bg-surface border-2', i === 0 ? 'border-brand' : 'border-transparent']"
        @dragstart="dragFrom = i" @dragover.prevent @drop.stop.prevent="onDrop(i)"
      >
        <img :src="u" alt="" class="size-full object-cover pointer-events-none" />
        <span v-if="i === 0" class="absolute left-1.5 top-1.5 h-5 px-1.5 rounded-full bg-brand text-white text-[10px] font-bold inline-flex items-center gap-0.5"><Star class="size-3" fill="currentColor" />{{ $t('Asosiy') }}</span>
        <button type="button" class="pbtn right-1.5 top-1.5" :aria-label="$t('O‘chirish')" @click="remove(i)"><X class="size-3.5" /></button>
        <div class="absolute inset-x-1.5 bottom-1.5 flex gap-1 justify-between">
          <button type="button" class="pbtn static!" :disabled="i === 0" :aria-label="$t('Chapga')" @click="move(i, -1)"><ChevronLeft class="size-3.5" /></button>
          <button v-if="i !== 0" type="button" class="pbtn static! w-auto! px-1.5 text-[10px] font-bold" :aria-label="$t('Asosiy qilish')" @click="makeMain(i)"><Star class="size-3" /></button>
          <button type="button" class="pbtn static!" :disabled="i === photos.length - 1" :aria-label="$t('O‘ngga')" @click="move(i, 1)"><ChevronRight class="size-3.5" /></button>
        </div>
      </div>
      <button
        v-if="photos.length < HOUSE_PHOTOS.max" type="button"
        :class="['aspect-square rounded-xl border-2 border-dashed grid place-items-center text-center transition hover:border-brand hover:bg-brand-25', error ? 'border-danger' : 'border-line']"
        data-testid="add-photo" @click="input.click()"
      >
        <span><component :is="busy ? Loader2 : ImagePlus" :class="['size-6 mx-auto text-brand-600', busy && 'animate-spin']" /><span class="block text-[11px] font-semibold mt-1 text-ink-2">{{ $t('Rasm qo‘shish') }}</span></span>
      </button>
    </div>
    <input ref="input" type="file" accept="image/jpeg,image/png,image/webp" multiple class="hidden" data-testid="photo-input" @change="onFiles" />
    <p v-if="error" class="mt-1 text-xs text-danger" role="alert">{{ error }}</p>
    <p v-else class="mt-1 text-xs text-muted">{{ $t('Birinchi rasm — asosiy. Tartibni sudrab yoki tugmalar bilan o‘zgartiring.') }}</p>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.pbtn { @apply absolute size-6 grid place-items-center rounded-full bg-white/95 text-ink shadow disabled:opacity-30; }
</style>
