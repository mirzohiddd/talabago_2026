<script setup>
/**
 * Ish beruvchi monitoringi: e’lonlar, ko‘rishlar, arizalar, qiziqishlar (saqlab qo‘yishlar), soha va ish turi bo‘yicha real statistika.
 * Ma’lumot: GET /employer/insights (demo yo‘q). Kunlik ko‘rishlar shu funksiya ishga tushgan kundan boshlab yig‘iladi.
 */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { Eye, Users, Heart, Briefcase, TrendingUp, Star, CheckCircle2, PlusCircle } from 'lucide-vue-next'
import LineChart from '@/components/charts/LineChart.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import StarRating from '@/components/reviews/StarRating.vue'
import { insightsApi } from '@/services'
import { JOB_TYPES } from '@/config/roles'
import { t } from '@/i18n'

const router = useRouter()
const days = ref('30')
const data = ref(null)
const loading = ref(true)
const error = ref(null)
async function load() {
  loading.value = true; error.value = null
  try { data.value = await insightsApi.get(+days.value) } catch (e) { error.value = t(e.message) }
  loading.value = false
}
onMounted(load)
watch(days, load)
const periodOpts = computed(() => [{ value: '7', label: t('7 kun') }, { value: '30', label: t('30 kun') }, { value: '90', label: t('90 kun') }])

const COLORS = { views: '#10B981', applications: '#111111', interests: '#f59e0b' }
const series = computed(() => data.value ? [
  { key: 'views', label: t('Ko‘rishlar'), color: COLORS.views, fill: true, values: data.value.timeline.map((d) => d.views) },
  { key: 'applications', label: t('Arizalar'), color: COLORS.applications, values: data.value.timeline.map((d) => d.applications) },
  { key: 'interests', label: t('Qiziqishlar'), color: COLORS.interests, values: data.value.timeline.map((d) => d.interests) },
] : [])
const labels = computed(() => data.value?.timeline.map((d) => d.date) || [])
const kpis = computed(() => {
  const x = data.value?.totals
  if (!x) return []
  return [
    { key: 'jobs', label: t('E’lonlar'), value: x.jobs, hint: t('{a} faol · {b} tekshiruvda', { a: x.active, b: x.pending }), icon: Briefcase },
    { key: 'views', label: t('Ko‘rishlar'), value: x.views, hint: t('Davr ichida: {n}', { n: x.periodViews }), icon: Eye },
    { key: 'apps', label: t('Arizalar'), value: x.applications, hint: t('Davr ichida: {n}', { n: x.periodApplications }), icon: Users },
    { key: 'int', label: t('Qiziqishlar'), value: x.interests, hint: t('Saqlab qo‘yganlar'), icon: Heart },
    { key: 'conv', label: t('Konversiya'), value: x.conversion === null ? '—' : `${x.conversion}%`, hint: t('Ariza / ko‘rish'), icon: TrendingUp },
    { key: 'acc', label: t('Qabul qilinganlar'), value: x.accepted, hint: t('Qabul + yakunlangan'), icon: CheckCircle2 },
  ]
})
const typeLabel = (k) => t(JOB_TYPES.find((x) => x.value === k)?.label || k)
const maxOf = (rows, m) => Math.max(1, ...rows.map((r) => r[m]))
const statusMax = computed(() => Math.max(1, ...(data.value?.applicationsByStatus || []).map((s) => s.count)))
const sortKey = ref('views')
const jobsSorted = computed(() => [...(data.value?.jobs || [])].sort((a, b) => b[sortKey.value] - a[sortKey.value]))
</script>

<template>
  <div class="page">
    <PageIntro class="mb-4" />
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <SegmentedControl v-model="days" :options="periodOpts" class="w-full sm:w-80" data-testid="period" />
      <p v-if="data?.rating?.count" class="ml-auto text-sm flex items-center gap-2" data-testid="my-rating"><StarRating readonly :value="data.rating.avg" :size="16" /><b>{{ data.rating.avg }}</b><span class="text-muted">· {{ $t('{n} ta baho', { n: data.rating.count }) }}</span></p>
    </div>

    <SkeletonCard v-if="loading" :count="3" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState v-else-if="data && !data.totals.jobs" :title="$t('Hali e’lon yo‘q')" :text="$t('Birinchi vakansiyangizni joylang — statistika shu yerda paydo bo‘ladi.')" illu="stats">
      <BaseButton :icon="PlusCircle" @click="router.push('/employer/new')">{{ $t('E’lon qo‘shish') }}</BaseButton>
    </EmptyState>
    <template v-else-if="data">
      <!-- KPI -->
      <div class="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 mb-4" data-testid="kpis">
        <div v-for="k in kpis" :key="k.key" class="card p-4">
          <div class="flex items-center gap-2 text-muted text-xs font-semibold"><component :is="k.icon" class="size-4 text-brand-600" />{{ k.label }}</div>
          <p class="text-[26px] font-extrabold tracking-tight mt-1 tabular-nums" :data-testid="`kpi-${k.key}`">{{ k.value }}</p>
          <p class="text-[11.5px] text-muted">{{ k.hint }}</p>
        </div>
      </div>

      <!-- Dinamika -->
      <section class="card p-4 mb-4">
        <div class="flex flex-wrap items-center gap-3 mb-2">
          <h2 class="font-bold text-[17px] mr-auto">{{ $t('Kunlik dinamika') }}</h2>
          <span v-for="s in series" :key="s.key" class="inline-flex items-center gap-1.5 text-xs font-semibold"><span class="size-2.5 rounded-full" :style="{ background: s.color }" />{{ s.label }}</span>
        </div>
        <LineChart :labels="labels" :series="series" data-testid="timeline-chart" />
        <p v-if="data.trackingSince" class="text-[11.5px] text-muted mt-1">{{ $t('Kunlik ko‘rishlar {d} dan beri hisoblanmoqda.', { d: $date(data.trackingSince) }) }}</p>
      </section>

      <div class="grid lg:grid-cols-3 gap-4 mb-4">
        <!-- Sohalar -->
        <section class="card p-4">
          <h2 class="font-bold mb-3">{{ $t('Faoliyat sohalari') }}</h2>
          <ul class="space-y-3" data-testid="by-category">
            <li v-for="c in data.byCategory" :key="c.key">
              <div class="flex items-center text-sm mb-1"><span class="font-semibold truncate flex-1">{{ $t(c.key) }}</span><span class="text-muted text-xs">{{ $t('{n} e’lon', { n: c.jobs }) }}</span></div>
              <div class="h-2 rounded-full bg-surface overflow-hidden"><div class="h-full bg-brand rounded-full" :style="{ width: `${c.views / maxOf(data.byCategory, 'views') * 100}%` }" /></div>
              <p class="text-[11.5px] text-muted mt-0.5">{{ $t('{v} ko‘rish · {a} ariza · {i} qiziqish', { v: c.views, a: c.applications, i: c.interests }) }}</p>
            </li>
          </ul>
        </section>
        <!-- Ish turlari -->
        <section class="card p-4">
          <h2 class="font-bold mb-3">{{ $t('Ish turlari') }}</h2>
          <ul class="space-y-3" data-testid="by-type">
            <li v-for="c in data.byType" :key="c.key">
              <div class="flex items-center text-sm mb-1"><span class="font-semibold flex-1">{{ typeLabel(c.key) }}</span><span class="text-muted text-xs">{{ $t('{n} e’lon', { n: c.jobs }) }}</span></div>
              <div class="h-2 rounded-full bg-surface overflow-hidden"><div class="h-full bg-ink rounded-full" :style="{ width: `${c.applications / maxOf(data.byType, 'applications') * 100}%` }" /></div>
              <p class="text-[11.5px] text-muted mt-0.5">{{ $t('{v} ko‘rish · {a} ariza · {i} qiziqish', { v: c.views, a: c.applications, i: c.interests }) }}</p>
            </li>
          </ul>
        </section>
        <!-- Ariza holatlari -->
        <section class="card p-4">
          <h2 class="font-bold mb-3">{{ $t('Arizalar holati') }}</h2>
          <ul class="space-y-2.5">
            <li v-for="s in data.applicationsByStatus" :key="s.key" class="flex items-center gap-3">
              <StatusBadge :status="s.key" class="w-[150px] justify-start shrink-0" />
              <div class="flex-1 h-2 rounded-full bg-surface overflow-hidden"><div class="h-full bg-brand-400 rounded-full" :style="{ width: `${s.count / statusMax * 100}%` }" /></div>
              <b class="w-6 text-right tabular-nums text-sm">{{ s.count }}</b>
            </li>
          </ul>
        </section>
      </div>

      <!-- E’lonlar kesimida -->
      <section class="card overflow-hidden">
        <div class="flex flex-wrap items-center gap-2 p-4 pb-2">
          <h2 class="font-bold mr-auto">{{ $t('E’lonlar kesimida') }}</h2>
          <SegmentedControl v-model="sortKey" :options="[{ value: 'views', label: $t('Ko‘rishlar') }, { value: 'applications', label: $t('Arizalar') }, { value: 'interests', label: $t('Qiziqishlar') }]" class="w-full sm:w-auto" />
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-sm min-w-[640px]" data-testid="jobs-stats">
            <thead class="bg-surface/70 text-left text-xs font-bold uppercase tracking-wide text-muted">
              <tr><th class="px-4 py-2.5">{{ $t('Vakansiya') }}</th><th class="px-4 py-2.5">{{ $t('Holat') }}</th><th class="px-4 py-2.5 text-right">{{ $t('Ko‘rishlar') }}</th><th class="px-4 py-2.5 text-right">{{ $t('Arizalar') }}</th><th class="px-4 py-2.5 text-right">{{ $t('Qiziqishlar') }}</th><th class="px-4 py-2.5 text-right">{{ $t('Konversiya') }}</th></tr>
            </thead>
            <tbody>
              <tr v-for="j in jobsSorted" :key="j.id" class="border-t border-line">
                <td class="px-4 py-2.5"><p class="font-semibold line-clamp-1">{{ $tc(j.title) }}</p><p class="text-xs text-muted">{{ [j.category && $t(j.category), typeLabel(j.type)].filter(Boolean).join(' · ') }}</p></td>
                <td class="px-4 py-2.5"><StatusBadge :status="j.status" /></td>
                <td class="px-4 py-2.5 text-right tabular-nums font-semibold">{{ j.views }}</td>
                <td class="px-4 py-2.5 text-right tabular-nums font-semibold">{{ j.applications }}</td>
                <td class="px-4 py-2.5 text-right tabular-nums">{{ j.interests }}</td>
                <td class="px-4 py-2.5 text-right tabular-nums">{{ j.conversion === null ? '—' : `${j.conversion}%` }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>
