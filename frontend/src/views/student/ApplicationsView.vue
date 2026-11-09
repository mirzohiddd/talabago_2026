<script setup>
/** Arizalarim: ikki ichki bo‘lim — Ish arizalarim / Ijara so‘rovlarim (status va tarix bilan) */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Briefcase, Home, ChevronDown, CalendarClock, XCircle, MessageSquareText } from 'lucide-vue-next'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import StatusTimeline from '@/components/ui/StatusTimeline.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { applicationsApi } from '@/services'
import { search, toast } from '@/stores/session'
import { salaryText, priceText } from '@/utils/format'
import { RENT_TERMS } from '@/config/roles'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const tab = ref(route.query.tab === 'requests' ? 'requests' : 'jobs')
watch(tab, (v) => router.replace({ query: v === 'requests' ? { tab: v } : {} }))
const jobs = ref([])
const reqs = ref([])
const loading = ref(true)
const error = ref(null)
async function load() {
  loading.value = true; error.value = null
  try { [jobs.value, reqs.value] = await Promise.all([applicationsApi.myJobs(), applicationsApi.myRequests()]) }
  catch (e) { error.value = e.message }
  loading.value = false
}
onMounted(load)

const tabs = computed(() => [
  { value: 'jobs', label: `${t('Ish arizalarim')} · ${jobs.value.length}`, icon: Briefcase },
  { value: 'requests', label: `${t('Ijara so‘rovlarim')} · ${reqs.value.length}`, icon: Home },
])
const status = ref('all')
watch(tab, () => (status.value = 'all'))
const statusOpts = computed(() => {
  const keys = tab.value === 'jobs' ? ['sent', 'viewed', 'interview', 'accepted', 'declined', 'withdrawn'] : ['sent', 'viewed', 'accepted', 'declined', 'withdrawn']
  const src = tab.value === 'jobs' ? jobs.value : reqs.value
  return [{ value: 'all', label: t('Barchasi') }, ...keys.filter((k) => src.some((x) => x.status === k)).map((k) => ({ value: k, label: `${t(STATUS_LABEL[k])} · ${src.filter((x) => x.status === k).length}` }))]
})
const STATUS_LABEL = { sent: 'Yuborildi', viewed: 'Ko‘rildi', interview: 'Suhbatga chaqirildi', accepted: 'Qabul qilindi', declined: 'Rad etildi', withdrawn: 'Bekor qilindi' }
const list = computed(() => {
  const q = search.query.trim().toLowerCase()
  return (tab.value === 'jobs' ? jobs.value : reqs.value)
    .filter((x) => status.value === 'all' || x.status === status.value)
    .filter((x) => !q || [x.job?.title, x.job?.company, x.house?.title, x.house?.district].some((v) => v?.toLowerCase().includes(q)))
})

const openId = ref(null)
const confirm = ref(false)
const target = ref(null)
const busy = ref(false)
const canWithdraw = (x) => ['sent', 'viewed'].includes(x.status)
function ask(x) { target.value = x; confirm.value = true }
async function withdraw() {
  busy.value = true
  await applicationsApi.withdraw(tab.value === 'jobs' ? 'job' : 'housing', target.value.id)
  busy.value = false; confirm.value = false
  toast(tab.value === 'jobs' ? t('Ariza bekor qilindi') : t('So‘rov bekor qilindi'))
  load()
}
const termLabel = (v) => RENT_TERMS.find((x) => x.value === v)?.label
</script>

<template>
  <div class="page-narrow lg:max-w-5xl!">
    <PageIntro class="mb-4" />
    <SegmentedControl v-model="tab" :options="tabs" class="mb-3 lg:max-w-xl" data-testid="app-tabs" />
    <ChipGroup v-model="status" :options="statusOpts" size="sm" class="mb-4" />

    <div v-if="loading" class="grid lg:grid-cols-2 gap-3"><SkeletonCard :count="4" class="contents" /></div>
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState v-else-if="!list.length"
      :title="tab === 'jobs' ? $t('Hali ariza yubormagansiz') : $t('Hali ijara so‘rovi yo‘q')"
      :text="tab === 'jobs' ? $t('Ishlar bo‘limidan mos vakansiyani tanlang.') : $t('Turar joy bo‘limidan uy tanlang.')" :illu="tab === 'jobs' ? 'briefcase' : 'house'">
      <BaseButton @click="router.push(tab === 'jobs' ? '/student/jobs' : '/student/housing')">{{ tab === 'jobs' ? $t('Ishlarni ko‘rish') : $t('Uylarni ko‘rish') }}</BaseButton>
    </EmptyState>
    <TransitionGroup v-else tag="div" name="list" class="grid lg:grid-cols-2 gap-3 items-start" :data-testid="`list-${tab}`">
      <article v-for="x in list" :key="x.id" class="card p-4" :data-testid="`app-${x.id}`">
        <div class="flex gap-3">
          <span class="size-11 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center shrink-0"><component :is="tab === 'jobs' ? Briefcase : Home" class="size-5" /></span>
          <div class="min-w-0 flex-1">
            <div class="flex items-start gap-2">
              <h3 class="font-bold leading-snug flex-1 line-clamp-2">{{ $tc(x.job?.title || x.house?.title || '—') }}</h3>
              <StatusBadge :status="x.status" />
            </div>
            <p class="text-[13px] text-muted mt-0.5 truncate">
              <template v-if="tab === 'jobs'">{{ x.job?.company }} · {{ x.job && salaryText(x.job) }}</template>
              <template v-else>{{ $t(x.house?.district || '') }} · {{ x.house && priceText(x.house) }}</template>
            </p>
          </div>
        </div>
        <p v-if="x.status === 'interview' && x.interviewAt" class="mt-3 flex items-center gap-2 text-[13px] font-semibold rounded-xl bg-warning/12 text-[#8a5300] px-3 py-2"><CalendarClock class="size-4" />{{ $t('Suhbat') }}: {{ $dateTime(x.interviewAt) }}</p>
        <p v-if="tab === 'requests'" class="mt-3 text-[13px] text-ink-2">{{ $t('Ko‘chib o‘tish') }}: <b>{{ $date(x.moveIn) }}</b> · {{ $t('Muddat') }}: <b>{{ $t(termLabel(x.term) || '') }}</b></p>
        <p v-if="x.message" class="mt-2 text-[13px] text-ink-2 flex gap-1.5"><MessageSquareText class="size-4 text-muted shrink-0 mt-px" /><span class="line-clamp-2">{{ x.message }}</span></p>
        <div class="mt-3 pt-3 border-t border-line flex items-center gap-2">
          <button class="inline-flex items-center gap-1 text-[13px] font-semibold text-ink-2 hover:text-ink" :aria-expanded="openId === x.id" @click="openId = openId === x.id ? null : x.id">
            {{ $t('Tarix') }} ({{ x.history?.length || 1 }})<ChevronDown :class="['size-4 transition-transform', openId === x.id && 'rotate-180']" />
          </button>
          <span class="text-xs text-muted ml-auto">{{ $ago(x.createdAt) }}</span>
          <button v-if="canWithdraw(x)" class="inline-flex items-center gap-1 text-[13px] font-semibold text-danger hover:underline" data-testid="withdraw" @click="ask(x)"><XCircle class="size-4" />{{ $t('Bekor qilish') }}</button>
        </div>
        <Transition name="fade"><div v-if="openId === x.id" class="mt-3"><StatusTimeline :history="x.history" /></div></Transition>
      </article>
    </TransitionGroup>

    <ConfirmModal v-model="confirm" :title="tab === 'jobs' ? $t('Arizani bekor qilish') : $t('So‘rovni bekor qilish')" :text="$t('Bu amalni ortga qaytarib bo‘lmaydi.')" :confirm-text="$t('Bekor qilish')" danger :loading="busy" @confirm="withdraw" />
  </div>
</template>
