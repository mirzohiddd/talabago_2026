<script setup>
/**
 * Kelgan arizalar (ish beruvchi) va ijara so‘rovlari (uy egasi).
 * Desktop: jadval; mobil: kartochkalar. Nomzod profili — o‘ngdan chiqadigan panel / bottom sheet.
 */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { Eye, CheckCircle2, XCircle, CalendarClock, FileText, GraduationCap, MapPin, Cake, MessageSquareText, Briefcase, Home, CalendarDays } from 'lucide-vue-next'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import Avatar from '@/components/ui/Avatar.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import StatusTimeline from '@/components/ui/StatusTimeline.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Pagination from '@/components/ui/Pagination.vue'
import ContactButtons from '@/components/shared/ContactButtons.vue'
import { applicationsApi, jobsApi, housingApi } from '@/services'
import { search, toast } from '@/stores/session'
import { SHIFTS, RENT_TERMS, STATUS } from '@/config/roles'
import { fileSize } from '@/utils/format'
import { resolveMedia } from '@/composables/useMediaUrl'
import { openLink } from '@/services/telegram'
import { t } from '@/i18n'

const route = useRoute()
const isJob = computed(() => route.meta.role === 'employer')
const items = ref([])
const listings = ref([])
const loading = ref(true)
const error = ref(null)
async function load() {
  loading.value = true; error.value = null
  try {
    ;[items.value, listings.value] = await Promise.all(isJob.value
      ? [applicationsApi.forEmployer(), jobsApi.mine()]
      : [applicationsApi.forLandlord(), housingApi.mine()])
  } catch (e) { error.value = e.message }
  loading.value = false
}
onMounted(load)

const STATUSES = computed(() => (isJob.value ? ['sent', 'viewed', 'interview', 'accepted', 'declined'] : ['sent', 'viewed', 'accepted', 'declined']))
const status = ref('all')
const listing = ref('all')
const statusOpts = computed(() => [{ value: 'all', label: `${t('Barchasi')} · ${items.value.length}` }, ...STATUSES.value.map((s) => ({ value: s, label: `${t(STATUS[s].label)} · ${items.value.filter((x) => x.status === s).length}` }))])
const listingOpts = computed(() => [{ value: 'all', label: isJob.value ? t('Barcha vakansiyalar') : t('Barcha uylar') }, ...listings.value.map((l) => ({ value: l.id, label: l.title }))])
const target = (x) => (isJob.value ? x.job : x.house)
const filtered = computed(() => {
  const q = search.query.trim().toLowerCase()
  return items.value
    .filter((x) => status.value === 'all' || x.status === status.value)
    .filter((x) => listing.value === 'all' || (isJob.value ? x.jobId : x.houseId) === listing.value)
    .filter((x) => !q || [x.student?.name, x.student?.university, target(x)?.title].some((v) => v?.toLowerCase().includes(q)))
})
const PER = 10
const page = ref(1)
const rows = computed(() => filtered.value.slice((page.value - 1) * PER, page.value * PER))

// ---- Profil paneli ----
const current = ref(null)
const drawer = ref(false)
async function open(x) {
  current.value = x
  drawer.value = true
  if (x.status === 'sent') await setStatus('viewed', {}, true)
}
const shiftLabel = (v) => SHIFTS.find((s) => s.value === v)?.label
const termLabel = (v) => RENT_TERMS.find((s) => s.value === v)?.label
const age = (d) => (d ? Math.floor((Date.now() - Date.parse(d)) / 31557600000) : null)

const busy = ref('')
async function setStatus(s, extra = {}, silent = false) {
  busy.value = s
  const api = isJob.value ? applicationsApi.setEmployerStatus : applicationsApi.setLandlordStatus
  const upd = await api(current.value.id, s, extra)
  Object.assign(current.value, upd)
  const i = items.value.findIndex((x) => x.id === upd.id)
  if (i >= 0) items.value[i] = { ...items.value[i], ...upd }
  busy.value = ''
  if (!silent) toast({ interview: t('Suhbatga taklif yuborildi'), accepted: t('Qabul qilindi'), declined: t('Rad etildi') }[s] || t('Saqlandi'))
}
// Suhbatga chaqirish
const ivOpen = ref(false)
const iv = ref({ date: '', time: '11:00', note: '' })
const ivErr = ref('')
function askInterview() { iv.value = { date: '', time: '11:00', note: '' }; ivErr.value = ''; ivOpen.value = true }
async function sendInterview() {
  if (!iv.value.date) { ivErr.value = t('Majburiy maydon'); return }
  await setStatus('interview', { interviewAt: new Date(`${iv.value.date}T${iv.value.time || '10:00'}:00+05:00`).toISOString(), note: iv.value.note.trim() || undefined })
  ivOpen.value = false
}
// Rad etish (ixtiyoriy sabab)
const rjOpen = ref(false)
const rjNote = ref('')
async function sendReject() { await setStatus('declined', { note: rjNote.value.trim() || undefined }); rjOpen.value = false; rjNote.value = '' }

async function openCv(cv) {
  const url = cv?.url && (await resolveMedia(cv.url))
  if (url) openLink(url)
  else toast(t('Demo: CV fayli faqat nomi bilan saqlangan'), 'error')
}
const today = new Date().toISOString().slice(0, 10)
const final = computed(() => current.value && ['accepted', 'declined'].includes(current.value.status))
</script>

<template>
  <div class="page">
    <PageIntro class="mb-4" />
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <div class="min-w-0 flex-1 basis-full lg:basis-0"><ChipGroup v-model="status" :options="statusOpts" size="sm" data-testid="status-chips" /></div>
      <BaseSelect v-model="listing" :options="listingOpts" class="w-full lg:w-72" :aria-label="isJob ? $t('Vakansiya') : $t('Uy')" />
    </div>

    <SkeletonCard v-if="loading" :count="4" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState v-else-if="!filtered.length" :title="items.length ? $t('Bu filtr bo‘yicha hech narsa yo‘q') : isJob ? $t('Hali ariza kelmagan') : $t('Hali so‘rov kelmagan')" :text="$t('E’lonlaringiz faol bo‘lsa, talabalar tez orada murojaat qiladi.')" :illu="isJob ? 'briefcase' : 'key'" />
    <template v-else>
      <!-- Desktop jadval -->
      <div class="hidden lg:block card overflow-hidden">
        <table class="w-full text-sm" data-testid="incoming-table">
          <thead class="bg-surface/70 text-left text-xs font-bold uppercase tracking-wide text-muted">
            <tr><th class="px-4 py-3">{{ $t('Talaba') }}</th><th class="px-4 py-3">{{ isJob ? $t('Vakansiya') : $t('Uy') }}</th><th class="px-4 py-3">{{ isJob ? $t('Ko‘nikmalar') : $t('Muddat') }}</th><th class="px-4 py-3">{{ $t('Sana') }}</th><th class="px-4 py-3">{{ $t('Holat') }}</th><th class="px-4 py-3 text-right">{{ $t('Amallar') }}</th></tr>
          </thead>
          <tbody>
            <tr v-for="x in rows" :key="x.id" class="border-t border-line hover:bg-brand-25/60 transition-colors">
              <td class="px-4 py-3">
                <button class="flex items-center gap-3 text-left group" @click="open(x)">
                  <Avatar :name="x.student?.name" size="sm" />
                  <span><span class="block font-semibold group-hover:text-brand-700">{{ x.student?.name }}</span><span class="block text-xs text-muted">{{ x.student?.university }}{{ x.student?.course ? `, ${$t('{n}-kurs', { n: x.student.course })}` : '' }}</span></span>
                </button>
              </td>
              <td class="px-4 py-3 max-w-[220px]"><span class="line-clamp-2">{{ $tc(target(x)?.title) }}</span></td>
              <td class="px-4 py-3">
                <div v-if="isJob" class="flex flex-wrap gap-1"><span v-for="s in (x.student?.skills || []).slice(0, 3)" :key="s" class="h-6 px-2 rounded-md bg-surface text-[11.5px] font-semibold grid place-items-center">{{ $t(s) }}</span></div>
                <span v-else>{{ $t(termLabel(x.term) || '') }} · {{ $date(x.moveIn) }}</span>
              </td>
              <td class="px-4 py-3 text-muted whitespace-nowrap">{{ $ago(x.createdAt) }}</td>
              <td class="px-4 py-3"><StatusBadge :status="x.status" /></td>
              <td class="px-4 py-3 text-right"><BaseButton size="sm" variant="soft" :icon="Eye" @click="open(x)">{{ $t('Ko‘rish') }}</BaseButton></td>
            </tr>
          </tbody>
        </table>
      </div>
      <!-- Mobil kartochkalar -->
      <div class="lg:hidden space-y-3 stagger" data-testid="incoming-cards">
        <article v-for="x in rows" :key="x.id" class="card card-hover p-4 cursor-pointer" @click="open(x)">
          <div class="flex items-center gap-3">
            <Avatar :name="x.student?.name" />
            <div class="min-w-0 flex-1"><p class="font-bold truncate">{{ x.student?.name }}</p><p class="text-xs text-muted truncate">{{ x.student?.university }} · {{ $ago(x.createdAt) }}</p></div>
            <StatusBadge :status="x.status" />
          </div>
          <p class="mt-3 text-[13px] text-ink-2 flex items-center gap-1.5"><component :is="isJob ? Briefcase : Home" class="size-4 text-muted shrink-0" /><span class="truncate">{{ $tc(target(x)?.title) }}</span></p>
          <p v-if="x.message" class="mt-1.5 text-[13px] text-muted line-clamp-2">“{{ x.message }}”</p>
        </article>
      </div>
      <Pagination v-model="page" :total="filtered.length" :per-page="PER" />
    </template>

    <!-- Profil paneli -->
    <BaseModal v-model="drawer" drawer :title="current?.student?.name" :subtitle="isJob ? $t('Nomzod profili') : $t('Talaba profili')">
      <div v-if="current" class="space-y-5" data-testid="candidate">
        <div class="flex items-center gap-4">
          <Avatar :name="current.student?.name" size="lg" />
          <div class="min-w-0">
            <StatusBadge :status="current.status" />
            <p class="text-[13px] text-muted mt-1.5">{{ isJob ? $t('Vakansiya') : $t('Uy') }}: <b class="text-ink">{{ $tc(target(current)?.title) }}</b></p>
          </div>
        </div>
        <dl class="grid grid-cols-2 gap-2.5 text-sm">
          <div class="info col-span-2"><dt><GraduationCap class="size-4" />{{ $t('O‘qish') }}</dt><dd>{{ [current.student?.university, current.student?.faculty, current.student?.course && $t('{n}-kurs', { n: current.student.course })].filter(Boolean).join(', ') || '—' }}</dd></div>
          <div class="info"><dt><CalendarDays class="size-4" />{{ $t('Smena') }}</dt><dd>{{ $t(shiftLabel(current.student?.shift) || '—') }}</dd></div>
          <div class="info"><dt><Cake class="size-4" />{{ $t('Yoshi') }}</dt><dd>{{ age(current.student?.birthDate) ?? '—' }}</dd></div>
          <div class="info col-span-2"><dt><MapPin class="size-4" />{{ $t('Hudud') }}</dt><dd>{{ [$t(current.student?.district || ''), $t(current.student?.city || '')].filter(Boolean).join(', ') || '—' }}</dd></div>
          <div v-if="!isJob" class="info"><dt><CalendarClock class="size-4" />{{ $t('Ko‘chib o‘tish') }}</dt><dd>{{ $date(current.moveIn) }}</dd></div>
          <div v-if="!isJob" class="info"><dt><CalendarDays class="size-4" />{{ $t('Ijara muddati') }}</dt><dd>{{ $t(termLabel(current.term) || '—') }}</dd></div>
        </dl>
        <section v-if="current.student?.skills?.length">
          <h4 class="font-bold mb-2">{{ $t('Ko‘nikmalar') }}</h4>
          <div class="flex flex-wrap gap-1.5"><span v-for="s in current.student.skills" :key="s" class="h-7 px-2.5 rounded-full bg-brand-50 text-brand-700 text-[12.5px] font-semibold grid place-items-center">{{ $t(s) }}</span></div>
        </section>
        <section v-if="current.student?.about"><h4 class="font-bold mb-1">{{ $t('O‘zi haqida') }}</h4><p class="text-[14px] text-ink-2">{{ current.student.about }}</p></section>
        <section v-if="current.message">
          <h4 class="font-bold mb-1 flex items-center gap-1.5"><MessageSquareText class="size-4" />{{ $t('Xabar') }}</h4>
          <p class="text-[14px] text-ink-2 rounded-xl bg-surface px-3.5 py-3">{{ current.message }}</p>
        </section>
        <section v-if="isJob">
          <h4 class="font-bold mb-2">CV</h4>
          <button v-if="current.student?.cv" class="w-full flex items-center gap-3 p-3 rounded-xl border border-line hover:border-brand-200 text-left" data-testid="open-cv" @click="openCv(current.student.cv)">
            <span class="size-10 rounded-xl bg-danger/10 text-danger grid place-items-center"><FileText class="size-5" /></span>
            <span class="min-w-0 flex-1"><span class="block font-semibold text-sm truncate">{{ current.student.cv.name }}</span><span class="block text-xs text-muted">{{ fileSize(current.student.cv.size || 0) }}</span></span>
          </button>
          <p v-else class="text-sm text-muted">{{ $t('CV yuklanmagan') }}</p>
        </section>
        <section><h4 class="font-bold mb-2">{{ $t('Bog‘lanish') }}</h4><ContactButtons :phone="current.student?.phone" :telegram="current.student?.telegram" /></section>
        <section><h4 class="font-bold mb-2">{{ $t('Tarix') }}</h4><StatusTimeline :history="current.history" /></section>
      </div>
      <template #footer>
        <div v-if="current && !final" class="grid grid-cols-2 gap-2" :class="isJob && 'sm:grid-cols-3'">
          <BaseButton v-if="isJob" variant="outline" :icon="CalendarClock" :loading="busy === 'interview'" class="col-span-2 sm:col-span-1" data-testid="act-interview" @click="askInterview">{{ $t('Suhbatga chaqirish') }}</BaseButton>
          <BaseButton variant="danger" :icon="XCircle" :loading="busy === 'declined'" data-testid="act-decline" @click="rjOpen = true">{{ $t('Rad etish') }}</BaseButton>
          <BaseButton :icon="CheckCircle2" :loading="busy === 'accepted'" data-testid="act-accept" @click="setStatus('accepted')">{{ $t('Qabul qilish') }}</BaseButton>
        </div>
        <p v-else-if="current" class="text-center text-sm text-muted py-2">{{ $t('Yakuniy holat') }}: <b class="text-ink">{{ $t(STATUS[current.status]?.label) }}</b></p>
      </template>
    </BaseModal>

    <BaseModal v-model="ivOpen" :title="$t('Suhbatga chaqirish')" :subtitle="current?.student?.name">
      <div class="space-y-4">
        <div class="grid grid-cols-2 gap-3">
          <BaseInput v-model="iv.date" type="date" :min="today" :label="$t('Sana')" required :error="ivErr" data-testid="iv-date" />
          <BaseInput v-model="iv.time" type="time" :label="$t('Vaqt')" />
        </div>
        <BaseInput v-model="iv.note" :label="$t('Izoh (manzil, havola)')" :placeholder="$t('Masalan: ofis, 3-qavat yoki Zoom havolasi')" />
      </div>
      <template #footer><BaseButton block :icon="CalendarClock" :loading="busy === 'interview'" data-testid="iv-send" @click="sendInterview">{{ $t('Taklif yuborish') }}</BaseButton></template>
    </BaseModal>
    <BaseModal v-model="rjOpen" :title="$t('Rad etish')" :subtitle="current?.student?.name">
      <BaseInput v-model="rjNote" :label="$t('Sabab (ixtiyoriy, talabaga ko‘rinadi)')" />
      <template #footer><BaseButton block variant="danger" :icon="XCircle" :loading="busy === 'declined'" data-testid="rj-send" @click="sendReject">{{ $t('Rad etish') }}</BaseButton></template>
    </BaseModal>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply flex items-center gap-1.5 text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-semibold; }
</style>
