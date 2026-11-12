<script setup>
/** Dashboard: tanlangan davr (bugun / hafta / oy) bo‘yicha asosiy ko‘rsatkichlar va grafiklar */
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Users, GraduationCap, Briefcase, KeyRound, Building2, Hourglass, FileText, Inbox, LifeBuoy, Megaphone, ArrowRight } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import KpiCard from '@/components/crm/KpiCard.vue'
import TrendChart from '@/components/crm/TrendChart.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Avatar from '@/components/ui/Avatar.vue'
import { crmStore, ensureCrmLoaded, fullName } from '@/services/crm'
import { adsStore, ensureAdsLoaded } from '@/services/ads'
import { adState } from '@/config/ads'
import { useNow } from '@/composables/useNow'
import { t, date } from '@/i18n'

const router = useRouter()
const now = useNow()
const loading = ref(!crmStore.loaded)
Promise.allSettled([ensureCrmLoaded(), ensureAdsLoaded()]).then(() => (loading.value = false))

const period = ref('week')
const periodOpts = computed(() => [{ value: 'today', label: t('Bugun') }, { value: 'week', label: t('Hafta') }, { value: 'month', label: t('Oy') }])
const DAY = 86400000
const since = computed(() => {
  if (period.value === 'today') { const d = new Date(now.value); d.setHours(0, 0, 0, 0); return d.getTime() }
  return now.value - (period.value === 'week' ? 7 : 30) * DAY
})
const inPeriod = (x) => Date.parse(x.createdAt) >= since.value
const c = (list, fn = () => true) => crmStore[list].filter(fn)
const hintNew = computed(() => ({ today: t('bugun'), week: t('shu hafta'), month: t('shu oy') }[period.value]))

const userTotal = computed(() => crmStore.users.length)

const kpis = computed(() => {
  const role = (r) => (u) => u.role === r
  const liveAds = adsStore.items.filter((a) => adState(a, now.value) === 'live')
  return [
    { label: t('Jami foydalanuvchilar'), value: userTotal.value, delta: c('users', inPeriod).length, icon: Users, tone: 'brand', to: '/users' },
    { label: t('Talabalar'), value: c('users', role('student')).length, delta: c('users', (u) => u.role === 'student' && inPeriod(u)).length, icon: GraduationCap, to: { path: '/users', query: { role: 'student' } } },
    { label: t('Ish beruvchilar'), value: c('users', role('employer')).length, delta: c('users', (u) => u.role === 'employer' && inPeriod(u)).length, icon: Briefcase, to: { path: '/users', query: { role: 'employer' } } },
    { label: t('Uy egalari'), value: c('users', role('landlord')).length, delta: c('users', (u) => u.role === 'landlord' && inPeriod(u)).length, icon: KeyRound, to: { path: '/users', query: { role: 'landlord' } } },
    { label: t('Faol ish e’lonlari'), value: c('jobs', (j) => j.status === 'active').length, delta: c('jobs', inPeriod).length, icon: Briefcase, to: '/jobs' },
    { label: t('Faol turar joylar'), value: c('houses', (h) => h.status === 'active').length, delta: c('houses', inPeriod).length, icon: Building2, to: '/housing' },
    { label: t('Tasdiqlashni kutmoqda'), value: c('jobs', (j) => j.status === 'pending').length + c('houses', (h) => h.status === 'pending').length, icon: Hourglass, tone: 'warn', hint: t('ish va uy e’lonlari'), to: { path: '/jobs', query: { status: 'pending' } } },
    { label: t('Arizalar'), value: c('applications').length, delta: c('applications', inPeriod).length, icon: FileText, to: '/applications' },
    { label: t('Ijara so‘rovlari'), value: c('requests').length, delta: c('requests', inPeriod).length, icon: Inbox, to: { path: '/applications', query: { tab: 'requests' } } },
    { label: t('Support murojaatlari'), value: c('tickets', (x) => x.status !== 'resolved').length, delta: c('tickets', inPeriod).length, icon: LifeBuoy, tone: 'dark', hint: t('ochiq'), to: '/support' },
    { label: t('Faol reklamalar'), value: liveAds.length, icon: Megaphone, hint: t('jami {n} ta', { n: adsStore.items.length }), to: '/ads' },
  ].map((k) => ({ ...k, hint: k.delta != null ? hintNew.value : k.hint }))
})

// ---- Grafik ----
const metric = ref('users')
const metricOpts = computed(() => [{ value: 'users', label: t('Ro‘yxatdan o‘tish') }, { value: 'applications', label: t('Arizalar') }, { value: 'requests', label: t('So‘rovlar') }])
const series = computed(() => {
  const list = crmStore[metric.value]
  if (period.value === 'today') {
    return Array.from({ length: 24 }, (_, h) => {
      const from = since.value + h * 3600000
      return { label: `${String(h).padStart(2, '0')}:00`, value: list.filter((x) => { const t0 = Date.parse(x.createdAt); return t0 >= from && t0 < from + 3600000 }).length }
    })
  }
  const n = period.value === 'week' ? 7 : 30
  const start = new Date(now.value); start.setHours(0, 0, 0, 0)
  return Array.from({ length: n }, (_, k) => {
    const from = start.getTime() - (n - 1 - k) * DAY
    return { label: date(new Date(from).toISOString(), { day: 'numeric', month: 'short' }), value: list.filter((x) => { const t0 = Date.parse(x.createdAt); return t0 >= from && t0 < from + DAY }).length }
  })
})
const total = computed(() => series.value.reduce((s, p) => s + p.value, 0))

const roleRows = computed(() => [
  { key: 'student', label: t('Talabalar'), icon: GraduationCap },
  { key: 'employer', label: t('Ish beruvchilar'), icon: Briefcase },
  { key: 'landlord', label: t('Uy egalari'), icon: KeyRound },
].map((r) => ({ ...r, n: c('users', (u) => u.role === r.key).length })))

const pending = computed(() => [
  ...c('jobs', (j) => j.status === 'pending').map((j) => ({ ...j, kind: 'job', to: { path: '/jobs', query: { id: j.id } } })),
  ...c('houses', (h) => h.status === 'pending').map((h) => ({ ...h, kind: 'house', to: { path: '/housing', query: { id: h.id } } })),
].sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt)).slice(0, 6))
const openTickets = computed(() => c('tickets', (x) => x.status === 'new' || x.status === 'in_review' || x.unreadBySupport).sort((a, b) => Date.parse(b.updatedAt) - Date.parse(a.updatedAt)).slice(0, 6))
const userOf = (id) => crmStore.users.find((u) => u.id === id)
</script>

<template>
  <div>
    <PageHeader :title="$t('Dashboard')" illu="stats">
      <SegmentedControl v-model="period" :options="periodOpts" class="w-full sm:w-72" data-testid="period" />
    </PageHeader>


    <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-6 gap-3 stagger">
      <KpiCard v-for="k in kpis" :key="k.label" v-bind="k" :loading="loading" />
    </div>

    <div class="grid xl:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] gap-4 mt-4">
      <section class="crm-card p-5 min-w-0">
        <div class="flex flex-wrap items-start gap-3 mb-3">
          <div class="mr-auto"><h2 class="font-bold">{{ metricOpts.find((m) => m.value === metric)?.label }}</h2><p class="text-sm text-muted"><b class="text-ink tabular-nums" data-testid="chart-total">{{ total }}</b> · {{ periodOpts.find((p) => p.value === period)?.label }}</p></div>
          <SegmentedControl v-model="metric" class="w-full sm:w-80" :options="metricOpts" />
        </div>
        <div v-if="loading" class="skeleton h-[220px]" />
        <TrendChart v-else :key="metric + period" :points="series" />
      </section>
      <section class="crm-card p-5 min-w-0">
        <h2 class="font-bold mb-4">{{ $t('Rollar bo‘yicha') }}</h2>
        <ul class="space-y-4">
          <li v-for="r in roleRows" :key="r.key">
            <button class="w-full text-left group" @click="router.push({ path: '/users', query: { role: r.key } })">
              <div class="flex items-center gap-2 text-sm"><component :is="r.icon" class="size-4 text-brand-600" /><span class="font-semibold">{{ r.label }}</span><span class="ml-auto font-bold tabular-nums">{{ r.n }}</span><span class="text-muted text-xs w-10 text-right tabular-nums">{{ Math.round((r.n / Math.max(1, crmStore.users.length)) * 100) }}%</span></div>
              <div class="h-2 rounded-full bg-surface mt-2 overflow-hidden"><div class="h-full rounded-full bg-brand transition-all duration-700 group-hover:bg-brand-600" :style="{ width: `${(r.n / Math.max(1, crmStore.users.length)) * 100}%` }" /></div>
            </button>
          </li>
        </ul>
        <p v-if="unrecovered" class="mt-4 text-xs text-muted leading-relaxed" data-testid="legacy-note">{{ $t('Jami {total} ta foydalanuvchidan {n} tasining profili eski bazada qolgan va tiklanmagan — rollar faqat bazadagi {db} ta foydalanuvchi bo‘yicha.', { total: userTotal, n: unrecovered, db: crmStore.users.length }) }}</p>
      </section>
    </div>

    <div class="grid xl:grid-cols-2 gap-4 mt-4">
      <section class="crm-card min-w-0">
        <div class="flex items-center px-5 pt-5 pb-3"><h2 class="font-bold mr-auto">{{ $t('Tasdiqlashni kutmoqda') }}</h2><RouterLink :to="{ path: '/jobs', query: { status: 'pending' } }" class="text-sm font-semibold text-brand-600 inline-flex items-center gap-1">{{ $t('Barchasi') }}<ArrowRight class="size-4" /></RouterLink></div>
        <ul class="divide-y divide-line">
          <li v-for="x in pending" :key="x.id"><RouterLink :to="x.to" class="flex items-center gap-3 px-5 py-3 hover:bg-[#fafafb]">
            <span class="size-9 rounded-xl bg-brand-50 text-brand-600 grid place-items-center"><component :is="x.kind === 'job' ? Briefcase : Building2" class="size-4" /></span>
            <span class="min-w-0 flex-1"><span class="block text-sm font-semibold truncate">{{ x.title }}</span><span class="block text-xs text-muted truncate">{{ x.kind === 'job' ? x.company : fullName(userOf(x.ownerId)) }} · {{ $ago(x.createdAt) }}</span></span>
            <StatusBadge status="pending" />
          </RouterLink></li>
          <li v-if="!pending.length" class="px-5 py-8 text-center text-sm text-muted">{{ $t('Hammasi tekshirilgan') }}</li>
        </ul>
      </section>
      <section class="crm-card min-w-0">
        <div class="flex items-center px-5 pt-5 pb-3"><h2 class="font-bold mr-auto">{{ $t('Ochiq support murojaatlari') }}</h2><RouterLink to="/support" class="text-sm font-semibold text-brand-600 inline-flex items-center gap-1">{{ $t('Inbox') }}<ArrowRight class="size-4" /></RouterLink></div>
        <ul class="divide-y divide-line">
          <li v-for="tk in openTickets" :key="tk.id"><RouterLink :to="`/support/${tk.id}`" class="flex items-center gap-3 px-5 py-3 hover:bg-[#fafafb]">
            <Avatar :name="fullName(userOf(tk.userId))" size="sm" />
            <span class="min-w-0 flex-1"><span class="block text-sm font-semibold truncate">{{ tk.subject }}</span><span class="block text-xs text-muted truncate">{{ fullName(userOf(tk.userId)) }} · {{ $ago(tk.updatedAt) }}</span></span>
            <StatusBadge :status="tk.status" />
          </RouterLink></li>
          <li v-if="!openTickets.length" class="px-5 py-8 text-center text-sm text-muted">{{ $t('Ochiq murojaat yo‘q') }}</li>
        </ul>
      </section>
    </div>
  </div>
</template>