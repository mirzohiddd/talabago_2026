<script setup>
/**
 * Reklama qo‘shish / tahrirlash formasi.
 * Vaqtlar Toshkent vaqtida kiritiladi va UTC ISO ko‘rinishida saqlanadi.
 */
import { t } from '@/i18n'
import { reactive, ref, computed, watch, nextTick } from 'vue'
import { ListOrdered, Megaphone, Link2, Image as ImageIcon, Clapperboard, CalendarClock, Info, AlertTriangle, CheckCircle2 } from 'lucide-vue-next'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import MediaUploader from './MediaUploader.vue'
import AdSlide from './AdSlide.vue'
import { AD_PLACEMENTS } from '@/config/ads'
import { useNow } from '@/composables/useNow'
import { tashkentInputToISO, isoToTashkentInput, humanDuration } from '@/utils/tashkentTime'
import { haptic } from '@/services/platform'

const props = defineProps({
  ad: { type: Object, default: null },
  saving: Boolean,
})
const emit = defineEmits(['submit', 'cancel'])
const now = useNow()

const DAY = 86400000
function roundedNow() {
  const t = Date.now()
  return new Date(Math.ceil(t / 300000) * 300000).toISOString() // keyingi 5 daqiqaga yaxlitlash
}
const startDefault = roundedNow()

const form = reactive({
  name: props.ad?.name ?? '',
  type: props.ad?.type ?? 'image',
  title: props.ad?.title ?? '',
  description: props.ad?.description ?? '',
  link: props.ad?.link ?? '',
  placements: [...(props.ad?.placements ?? ['/student/jobs'])],
  start: isoToTashkentInput(props.ad?.startAt ?? startDefault),
  end: isoToTashkentInput(props.ad?.endAt ?? new Date(Date.parse(startDefault) + 7 * DAY).toISOString()),
  enabled: props.ad?.enabled ?? true,
  order: props.ad?.order ?? '',
})
const pending = ref(null)
const existing = ref(props.ad?.media ?? null)
const errors = reactive({})
const formEl = ref(null)

const typeOptions = [
  { value: 'image', label: t('Rasm'), icon: ImageIcon },
  { value: 'video', label: 'Video', icon: Clapperboard },
]
const placementOptions = [{ value: 'all', label: t('Barcha sahifalar') }, ...AD_PLACEMENTS.map((p) => ({ ...p, label: t(p.label) }))]

// Turi o‘zgarsa — boshqa turdagi fayl yaroqsiz
watch(() => form.type, (t) => {
  if (pending.value) pending.value = null
  if (existing.value && props.ad?.type !== t) existing.value = null
  else if (!existing.value && props.ad?.type === t) existing.value = props.ad.media
})
// "Barcha sahifalar" boshqalarini almashtiradi
watch(() => form.placements, (n, o) => {
  if (n.includes('all') && !o.includes('all')) form.placements = ['all']
  else if (n.includes('all') && n.length > 1) form.placements = n.filter((x) => x !== 'all')
})
// Maydon o‘zgarishi bilan uning xatosi o‘chadi
for (const k of ['name', 'title', 'link', 'start', 'end', 'placements', 'order']) watch(() => form[k], () => delete errors[k], { deep: true })
watch(pending, () => delete errors.media)

const startISO = computed(() => tashkentInputToISO(form.start))
const endISO = computed(() => tashkentInputToISO(form.end))

/** Jadval bo‘yicha jonli xulosa */
const schedule = computed(() => {
  const s = Date.parse(startISO.value), e = Date.parse(endISO.value), n = now.value
  if (!s || !e) return null
  if (e <= s) return { tone: 'error', text: t('Tugash vaqti boshlanish vaqtidan keyin bo‘lishi kerak.') }
  const len = humanDuration(e - s)
  if (e <= n) return { tone: 'warn', text: t('Tugash vaqti o‘tib ketgan — saqlansa, reklama “Muddati tugagan” bo‘ladi.') }
  if (!form.enabled) return { tone: 'info', text: t('Noaktiv — siz yoqmaguningizcha ko‘rsatilmaydi. Davomiyligi: {len}.', { len }) }
  if (s > n) return { tone: 'info', text: t('{a} dan keyin avtomatik ko‘rsatiladi va {len} davom etadi.', { a: humanDuration(s - n), len }) }
  return { tone: 'ok', text: t('Saqlangach darhol ko‘rsatiladi · {a} dan keyin avtomatik yashiriladi.', { a: humanDuration(e - n) }) }
})

function setStartNow() { form.start = isoToTashkentInput(new Date().toISOString()) }
function setDuration(days) {
  const s = startISO.value || new Date().toISOString()
  form.end = isoToTashkentInput(new Date(Date.parse(s) + days * DAY).toISOString())
}

function normalizeLink() {
  const v = form.link.trim()
  if (v && !/^[a-z][a-z0-9+.-]*:\/\//i.test(v)) form.link = 'https://' + v
}

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!form.name.trim()) errors.name = t('Reklama nomini kiriting')
  else if (form.name.trim().length > 80) errors.name = t('Nom 80 belgidan oshmasin')
  if (!pending.value && !existing.value) errors.media = form.type === 'image' ? 'Rasm yuklang' : 'Video yuklang'
  if (form.title.length > 60) errors.title = t('Sarlavha 60 belgidan oshmasin')
  normalizeLink()
  if (form.link) {
    try {
      const u = new URL(form.link)
      if (!['http:', 'https:'].includes(u.protocol) || !u.hostname.includes('.')) throw 0
    } catch { errors.link = t('To‘g‘ri havola kiriting, masalan: https://example.uz') }
  }
  if (!startISO.value) errors.start = t('Boshlanish vaqtini tanlang')
  if (!endISO.value) errors.end = t('Tugash vaqtini tanlang')
  if (startISO.value && endISO.value && Date.parse(endISO.value) <= Date.parse(startISO.value)) {
    errors.end = t('Tugash sanasi boshlanish sanasidan keyin bo‘lishi shart')
  }
  if (!form.placements.length) errors.placements = t('Kamida bitta sahifani tanlang')
  if (form.order !== '' && form.order !== null && !(Number.isInteger(+form.order) && +form.order >= 1 && +form.order <= 999)) errors.order = t('1 dan 999 gacha butun son')
  return !Object.keys(errors).length
}

async function submit() {
  if (!validate()) {
    haptic.error()
    await nextTick()
    formEl.value?.querySelector('.text-danger:not(:empty)')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    return
  }
  emit('submit', {
    data: {
      name: form.name.trim(), type: form.type, title: form.title.trim(), description: form.description.trim(),
      link: form.link.trim(), placements: [...form.placements],
      startAt: startISO.value, endAt: endISO.value, enabled: form.enabled,
      ...(form.order !== '' && form.order !== null ? { order: +form.order } : {}),
    },
    pending: pending.value,
  })
}

const previewAd = computed(() => ({ ...form, media: pending.value ?? existing.value }))
</script>

<template>
  <form ref="formEl" class="grid lg:grid-cols-[minmax(0,1fr)_340px] gap-x-10 gap-y-6 items-start" novalidate @submit.prevent="submit">
   <div class="space-y-7 min-w-0">
    <section class="space-y-4">
      <BaseInput v-model="form.name" :label="$t('Reklama nomi *')" :placeholder="$t('Masalan: CodeStart — kuzgi kurs')" :icon="Megaphone" :error="errors.name" :hint="$t('Faqat CRM’da ko‘rinadi')" />
      <div>
        <span class="label">{{ $t('Reklama turi') }}</span>
        <SegmentedControl v-model="form.type" :options="typeOptions" />
      </div>
      <div>
        <span class="label">{{ form.type === 'image' ? $t('Rasm') : $t('Video') }} *</span>
        <MediaUploader v-model="pending" :type="form.type" :existing="existing" :error="errors.media" @remove-existing="existing = null" />
      </div>
    </section>

    <section class="space-y-4">
      <BaseInput v-model="form.title" :label="$t('Sarlavha')" :placeholder="$t('Banner ustidagi asosiy matn')" :error="errors.title" :hint="`${form.title.length}/60`" />
      <BaseTextarea v-model="form.description" :label="$t('Qisqa tavsif')" :placeholder="$t('Bir qatorli izoh')" :rows="2" :maxlength="120" />
      <BaseInput v-model="form.link" :label="$t('Reklama havolasi')" placeholder="https://example.uz" :icon="Link2" inputmode="url" :error="errors.link" :hint="$t('Banner bosilganda ochiladi. t.me havolalari Telegram ichida ochiladi.')" @blur="normalizeLink" />
    </section>

    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h3 class="font-bold flex items-center gap-2"><CalendarClock class="size-[18px] text-brand-600" />{{ $t('Ko‘rsatish muddati') }}</h3>
        <span class="text-[12px] font-semibold text-muted bg-surface rounded-full h-6 px-2.5 inline-flex items-center">{{ $t('Toshkent vaqti · UTC+5') }}</span>
      </div>
      <div class="grid sm:grid-cols-2 gap-3">
        <BaseInput v-model="form.start" type="datetime-local" :label="$t('Boshlanish *')" :error="errors.start" data-testid="ad-start" />
        <BaseInput v-model="form.end" type="datetime-local" :label="$t('Tugash *')" :error="errors.end" data-testid="ad-end" />
      </div>
      <div class="flex flex-wrap gap-2">
        <button type="button" class="preset" @click="setStartNow">{{ $t('Hozirdan boshlash') }}</button>
        <button v-for="d in [1, 7, 30]" :key="d" type="button" class="preset" @click="setDuration(d)">{{ d }} kun</button>
      </div>
      <p
        v-if="schedule && !(schedule.tone === 'error' && errors.end)"
        :class="[
          'flex gap-2 text-[13px] rounded-xl px-3 py-2.5',
          schedule.tone === 'error' ? 'bg-danger/10 text-danger' : schedule.tone === 'warn' ? 'bg-warning/10 text-[#a15c00]' : schedule.tone === 'ok' ? 'bg-success/10 text-success' : 'bg-[#2f6bff]/8 text-[#2f6bff]',
        ]"
      >
        <component :is="schedule.tone === 'ok' ? CheckCircle2 : schedule.tone === 'info' ? Info : AlertTriangle" class="size-4 shrink-0 mt-px" />{{ schedule.text }}
      </p>
    </section>

    <section>
      <span class="label">{{ $t('Joylashuv — qaysi sahifalarda ko‘rsatilsin *') }}</span>
      <ChipGroup v-model="form.placements" :options="placementOptions" multiple wrap size="sm" />
      <p v-if="errors.placements" class="mt-1.5 text-xs text-danger">{{ errors.placements }}</p>
    </section>

   </div>

   <aside class="space-y-4 lg:sticky lg:top-24">
    <section>
      <span class="label">{{ $t('Ko‘rinishi (Mini App · Header Carousel)') }}</span>
      <div class="relative aspect-[5/3] rounded-2xl overflow-hidden border border-line bg-surface">
        <AdSlide v-if="previewAd.media" :ad="previewAd" :media="previewAd.media" :render-video="false" />
        <p v-else class="absolute inset-0 grid place-items-center text-sm text-muted">{{ $t('Fayl yuklang') }}</p>
      </div>
    </section>

    <section class="card p-4 flex items-center gap-3">
      <div class="flex-1">
        <p class="font-semibold">Holati: {{ form.enabled ? 'Aktiv' : 'Noaktiv' }}</p>
        <p class="text-[13px] text-muted">{{ $t('Noaktiv reklama muddati kelsa ham ko‘rsatilmaydi.') }}</p>
      </div>
      <ToggleSwitch v-model="form.enabled" :aria-label="$t('Aktiv / Noaktiv')" />
    </section>

    <BaseInput v-model="form.order" type="number" inputmode="numeric" :label="$t('Reklama tartibi')" :placeholder="$t('Avtomatik (oxiriga)')" :icon="ListOrdered" :error="errors.order" :hint="$t('1 — carousel’da birinchi chiqadi')" data-testid="ad-order" />

    <div class="flex gap-2 pt-1">
      <BaseButton variant="soft" @click="emit('cancel')">{{ $t('Bekor qilish') }}</BaseButton>
      <BaseButton type="submit" class="flex-1" :loading="saving">{{ ad ? 'O‘zgarishlarni saqlash' : 'Reklamani saqlash' }}</BaseButton>
    </div>
   </aside>
  </form>
</template>

<style scoped>
@reference "../../style.css";
.preset { @apply h-8 px-3 rounded-full bg-surface text-[13px] font-semibold text-ink-2 hover:bg-brand-50 hover:text-brand-600 transition active:scale-95; }
</style>
