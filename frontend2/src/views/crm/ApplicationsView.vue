<script setup>
/** Arizalar va so‘rovlar: kim, qaysi e’longa, qachon va qaysi holatda */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Briefcase, Home } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import Pagination from '@/components/crm/Pagination.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import SideDrawer from '@/components/crm/SideDrawer.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import StatusTimeline from '@/components/ui/StatusTimeline.vue'
import Avatar from '@/components/ui/Avatar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { crmStore, ensureCrmLoaded, fullName } from '@/services/crm'
import { STATUS, RENT_TERMS } from '@/config/status'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))

const tab = ref(route.query.tab === 'requests' ? 'requests' : 'applications')
watch(tab, (v) => router.replace({ query: v === 'requests' ? { tab: v } : {} }))
const tabs = computed(() => [
  { value: 'applications', label: `${t('Ish arizalari')} · ${crmStore.applications.length}`, icon: Briefcase },
  { value: 'requests', label: `${t('Ijara so‘rovlari')} · ${crmStore.requests.length}`, icon: Home },
])
const status = ref('all')
const q = ref('')
const page = ref(1)
const PER = 15
watch([tab, status, q], () => (page.value = 1))
watch(tab, () => (status.value = 'all'))

const user = (id) => crmStore.users.find((u) => u.id === id)
const job = (id) => crmStore.jobs.find((j) => j.id === id)
const house = (id) => crmStore.houses.find((h) => h.id === id)
const rowsAll = computed(() => (tab.value === 'applications'
  ? crmStore.applications.map((a) => { const j = job(a.jobId); return { ...a, target: j?.title || a.jobId, owner: j?.company, ownerId: j?.employerId } })
  : crmStore.requests.map((r) => { const h = house(r.houseId); return { ...r, target: h?.title || r.houseId, owner: fullName(user(h?.ownerId)), ownerId: h?.ownerId } })))
const keys = computed(() => (tab.value === 'applications' ? ['sent', 'viewed', 'interview', 'accepted', 'declined', 'withdrawn'] : ['sent', 'viewed', 'accepted', 'declined', 'withdrawn']))
const chips = computed(() => [{ value: 'all', label: `${t('Barchasi')} · ${rowsAll.value.length}` }, ...keys.value.map((k) => ({ value: k, label: `${t(STATUS[k].label)} · ${rowsAll.value.filter((x) => x.status === k).length}` }))])
const filtered = computed(() => {
  const s = q.value.trim().toLowerCase()
  return rowsAll.value
    .filter((x) => status.value === 'all' || x.status === status.value)
    .filter((x) => !s || [fullName(user(x.studentId)), x.target, x.owner].some((v) => v?.toLowerCase().includes(s)))
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
})
const rows = computed(() => filtered.value.slice((page.value - 1) * PER, page.value * PER))

const current = ref(null)
const drawer = ref(false)
const termLabel = (v) => RENT_TERMS.find((x) => x.value === v)?.label
</script>

<template>
  <div>
    <PageHeader :title="$t('Arizalar va so‘rovlar')" illu="checklist"><SearchBox v-model="q" :placeholder="$t('Talaba, e’lon yoki egasi…')" /></PageHeader>
    <SegmentedControl v-model="tab" :options="tabs" class="mb-3 max-w-lg" data-testid="crm-app-tabs" />
    <ChipGroup v-model="status" :options="chips" size="sm" class="mb-4" />

    <div class="crm-card overflow-hidden">
      <SkeletonRows v-if="loading" :rows="8" :cols="5" />
      <EmptyState v-else-if="!filtered.length" :title="$t('Hech narsa topilmadi')" text="" illu="pen" />
      <template v-else>
        <div class="overflow-x-auto">
          <table class="crm-table min-w-[900px]" data-testid="crm-apps-table">
            <thead><tr><th>{{ $t('Talaba') }}</th><th>{{ tab === 'applications' ? $t('Vakansiya') : $t('Uy') }}</th><th>{{ tab === 'applications' ? $t('Ish beruvchi') : $t('Uy egasi') }}</th><th>{{ $t('Sana') }}</th><th>{{ $t('Holat') }}</th></tr></thead>
            <tbody>
              <tr v-for="x in rows" :key="x.id" class="cursor-pointer" @click="current = x; drawer = true">
                <td><div class="flex items-center gap-3"><Avatar :name="fullName(user(x.studentId))" size="sm" /><div><p class="font-semibold">{{ fullName(user(x.studentId)) }}</p><p class="text-xs text-muted">{{ user(x.studentId)?.university }}</p></div></div></td>
                <td class="max-w-[260px]"><p class="truncate font-medium">{{ x.target }}</p></td>
                <td>{{ x.owner }}</td>
                <td class="tabular-nums whitespace-nowrap">{{ $dateTime(x.createdAt) }}</td>
                <td><StatusBadge :status="x.status" /></td>
              </tr>
            </tbody>
          </table>
        </div>
        <Pagination v-model="page" :total="filtered.length" :per-page="PER" />
      </template>
    </div>

    <SideDrawer v-model="drawer" :title="current?.target" :subtitle="current && fullName(user(current.studentId))">
      <div v-if="current" class="space-y-4 text-sm">
        <StatusBadge :status="current.status" />
        <dl class="grid grid-cols-2 gap-2.5">
          <div class="info"><dt>{{ $t('Talaba') }}</dt><dd><RouterLink :to="{ path: '/users', query: { id: current.studentId } }" class="text-brand-700 hover:underline">{{ fullName(user(current.studentId)) }}</RouterLink></dd></div>
          <div class="info"><dt>{{ tab === 'applications' ? $t('Ish beruvchi') : $t('Uy egasi') }}</dt><dd><RouterLink :to="{ path: '/users', query: { id: current.ownerId } }" class="text-brand-700 hover:underline">{{ current.owner }}</RouterLink></dd></div>
          <div class="info"><dt>{{ $t('Yuborilgan') }}</dt><dd>{{ $dateTime(current.createdAt) }}</dd></div>
          <div v-if="current.interviewAt" class="info"><dt>{{ $t('Suhbat') }}</dt><dd>{{ $dateTime(current.interviewAt) }}</dd></div>
          <div v-if="current.moveIn" class="info"><dt>{{ $t('Ko‘chib o‘tish') }}</dt><dd>{{ $date(current.moveIn) }} · {{ $t(termLabel(current.term) || '') }}</dd></div>
        </dl>
        <p v-if="current.message" class="rounded-xl bg-surface px-3.5 py-3 text-ink-2">“{{ current.message }}”</p>
        <section><h4 class="font-bold mb-2">{{ $t('Tarix') }}</h4><StatusTimeline :history="current.history" /></section>
      </div>
    </SideDrawer>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-semibold; }
</style>
