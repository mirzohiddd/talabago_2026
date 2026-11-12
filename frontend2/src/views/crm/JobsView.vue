<script setup>
import { ref, computed } from 'vue'
import { Wallet, MapPin, CalendarClock, Eye, Users, Wifi, Building2, Phone, Send, UserRound } from 'lucide-vue-next'
import ListingAdmin from '@/components/crm/ListingAdmin.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { JOB_TYPE_LABELS } from '@/config/status'
import { salaryText } from '@/utils/format'
import { t } from '@/i18n'

const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))
const employer = (id) => crmStore.users.find((u) => u.id === id)
const appsCount = (id) => crmStore.applications.filter((a) => a.jobId === id && a.status !== 'withdrawn').length
const columns = computed(() => [
  { key: 'title', label: t('Vakansiya') },
  { key: 'employer', label: t('Ish beruvchi') },
  { key: 'type', label: t('Turi') },
  { key: 'salary', label: t('Maosh') },
  { key: 'city', label: t('Joylashuv') },
  { key: 'createdAt', label: t('Joylangan') },
  { key: 'applications', label: t('Arizalar'), class: 'text-right' },
])
const typeOpts = computed(() => Object.entries(JOB_TYPE_LABELS).map(([value, label]) => ({ value, label: t(label) })))
const editFields = computed(() => [
  { key: 'title', label: t('Ish nomi'), wide: true }, { key: 'company', label: t('Kompaniya') }, { key: 'salary', label: t('Maosh'), type: 'number' },
  { key: 'schedule', label: t('Ish jadvali'), wide: true }, { key: 'description', label: t('Tavsif'), textarea: true },
])
const REASONS = ['Maosh yoki ish vaqti aniq emas', 'Tavsif juda qisqa', 'Aloqa ma’lumotlari noto‘g‘ri', 'Qoidalarga zid mazmun']
</script>

<template>
  <ListingAdmin
    :title="$t('Ish e’lonlari')" :items="crmStore.jobs" :loading="loading" :columns="columns" testid="jobs-table" illu="briefcase"
    filter-key="type" :filter-options="typeOpts" :search-fields="['title', 'company', 'category', 'city', 'district']"
    :api="crmApi.jobs" :edit-fields="editFields" :reject-reasons="REASONS" kind="job" :add-label="$t('E’lon qo‘shish')"
  >
    <template #title="{ item }"><p class="font-semibold max-w-[220px] truncate">{{ item.title }}</p><p class="text-xs text-muted">{{ $t(item.category || '') }}</p></template>
    <template #employer="{ item }"><p class="font-medium max-w-[160px] truncate">{{ item.company }}</p><p class="text-xs text-muted truncate">{{ item.employerId ? fullName(employer(item.employerId)) : $t('Akkauntsiz (admin e’loni)') }}</p></template>
    <template #type="{ item }"><span class="pill">{{ $t(JOB_TYPE_LABELS[item.type]) }}</span> <span class="pill"><component :is="item.format === 'online' ? Wifi : Building2" class="size-3.5" />{{ item.format === 'online' ? 'Online' : 'Offline' }}</span></template>
    <template #salary="{ item }"><span class="font-semibold tabular-nums whitespace-nowrap">{{ salaryText(item) }}</span></template>
    <template #city="{ item }">{{ item.format === 'online' ? $t('Masofaviy') : `${$t(item.district || '')}, ${$t(item.city)}` }}</template>
    <template #createdAt="{ item }"><span class="tabular-nums whitespace-nowrap">{{ $date(item.createdAt) }}</span></template>
    <template #applications="{ item }"><span class="tabular-nums font-semibold">{{ appsCount(item.id) }}</span></template>
    <template #detail="{ item }">
      <div class="grid grid-cols-2 gap-2.5 text-sm">
        <div class="info"><Wallet class="size-4 text-brand-600" />{{ salaryText(item) }}</div>
        <div class="info"><MapPin class="size-4 text-brand-600" />{{ item.format === 'online' ? $t('Masofaviy') : `${$t(item.district || '')}, ${$t(item.city)}` }}</div>
        <div class="info"><CalendarClock class="size-4 text-brand-600" />{{ item.schedule || '—' }}</div>
        <div v-if="item.address" class="info col-span-2"><MapPin class="size-4 text-brand-600" />{{ item.address }}</div>
        <div class="info"><Eye class="size-4 text-brand-600" />{{ item.views }} · <Users class="size-4 text-brand-600" />{{ appsCount(item.id) }}</div>
      </div>
      <p class="text-[14.5px] text-ink-2 leading-relaxed whitespace-pre-line">{{ item.description }}</p>
      <ul v-if="item.requirements?.length" class="text-sm list-disc pl-5 text-ink-2"><li v-for="r in item.requirements" :key="r">{{ r }}</li></ul>
      <div class="rounded-xl border border-line p-3.5 text-sm space-y-1.5">
        <p class="font-bold flex items-center gap-1.5"><UserRound class="size-4" />{{ $t('Ish beruvchi') }}</p>
        <RouterLink v-if="item.employerId" :to="{ path: '/users', query: { id: item.employerId } }" class="block font-semibold text-brand-700 hover:underline">{{ item.company }} · {{ fullName(employer(item.employerId)) }}</RouterLink>
        <p v-else class="font-semibold">{{ item.company }}<span v-if="item.contactName"> · {{ item.contactName }}</span></p>
        <p class="flex items-center gap-1.5 text-ink-2"><Phone class="size-4" />{{ item.phone || '—' }} <Send class="size-4 ml-2" />{{ item.telegram || '—' }}</p>
        <p class="text-xs text-muted">{{ $t('Joylangan') }}: {{ $dateTime(item.createdAt) }}</p>
      </div>
    </template>
  </ListingAdmin>
</template>

<style scoped>
@reference "../../style.css";
.info { @apply flex items-center gap-2 rounded-xl bg-surface px-3 py-2.5 font-medium; }
</style>