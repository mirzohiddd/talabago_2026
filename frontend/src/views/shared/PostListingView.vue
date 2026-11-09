<script setup>
/**
 * “E’lon qo‘shish”: ikki bo‘lim — Mening e’lonlarim / Yangi e’lon.
 * Ish beruvchi (vakansiya) va uy egasi (uy) uchun umumiy; forma va API rolga qarab tanlanadi.
 * Holatlar: Tekshiruvda → Faol | Rad etilgan; Yopilgan. Tahrirlash e’lonni qayta tekshiruvga yuboradi.
 */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, List } from 'lucide-vue-next'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import MyListingCard from '@/components/cards/MyListingCard.vue'
import JobForm from '@/components/forms/JobForm.vue'
import HouseForm from '@/components/forms/HouseForm.vue'
import JobDetailModal from '@/components/modals/JobDetailModal.vue'
import HouseDetailModal from '@/components/modals/HouseDetailModal.vue'
import { jobsApi, housingApi } from '@/services'
import { session, search, toast } from '@/stores/session'
import { LISTING_STATUSES, STATUS } from '@/config/roles'
import { salaryText, priceText } from '@/utils/format'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const kind = computed(() => (route.meta.role === 'employer' ? 'job' : 'house'))
const api = computed(() => (kind.value === 'job' ? jobsApi : housingApi))

const tab = ref(route.query.tab === 'new' || route.query.edit ? 'new' : 'mine')
const editing = ref(null)
const items = ref([])
const loading = ref(true)
const error = ref(null)
async function load() {
  loading.value = true; error.value = null
  try { items.value = await api.value.mine({}) } catch (e) { error.value = e.message }
  loading.value = false
  if (route.query.edit) editing.value = items.value.find((x) => x.id === route.query.edit) || null
}
onMounted(load)
watch(tab, (v) => { if (v === 'mine') { editing.value = null; router.replace({ query: {} }) } })

const tabs = computed(() => [
  { value: 'mine', label: `${t('Mening e’lonlarim')} · ${items.value.length}`, icon: List },
  { value: 'new', label: editing.value ? t('Tahrirlash') : t('Yangi e’lon'), icon: Plus },
])
const status = ref('all')
const statusOpts = computed(() => [{ value: 'all', label: t('Barchasi') }, ...LISTING_STATUSES.map((s) => ({ value: s, label: `${t(STATUS[s].label)} · ${items.value.filter((x) => x.status === s).length}` }))])
const list = computed(() => {
  const q = search.query.trim().toLowerCase()
  return items.value.filter((x) => status.value === 'all' || x.status === status.value).filter((x) => !q || [x.title, x.district].some((v) => v?.toLowerCase().includes(q)))
})

const saving = ref(false)
async function submit(payload) {
  saving.value = true
  try {
    // Xabar serverdagi haqiqiy holatga qarab (Support’da moderatsiya o‘chirilgan bo‘lsa e’lon darhol chiqadi)
    if (editing.value) {
      const r = await api.value.update(editing.value.id, payload)
      toast(r?.status === 'pending' ? t('O‘zgarishlar saqlandi va qayta tekshiruvga yuborildi') : t('O‘zgarishlar saqlandi'))
    } else {
      const r = await api.value.create(payload)
      toast(r?.status === 'active' ? t('E’lon joylandi') : t('E’lon tekshiruvga yuborildi'))
    }
    editing.value = null
    tab.value = 'mine'
    status.value = 'all'
    await load()
  } catch (e) { toast(e.message || t('Xatolik yuz berdi'), 'error') }
  saving.value = false
}
function edit(x) { editing.value = x; tab.value = 'new'; router.replace({ query: { edit: x.id } }); window.scrollTo({ top: 0 }) }
async function duplicate(x) {
  const copy = await api.value.duplicate(x.id)
  toast(copy?.status === 'active' ? t('Nusxa yaratildi va e’lon qilindi') : t('Nusxa yaratildi va tekshiruvga yuborildi'))
  load()
}
async function toggle(x) {
  const active = x.status === 'closed'
  await api.value.setActive(x.id, active)
  toast(active ? t('E’lon qayta ochildi') : t('E’lon yopildi'))
  load()
}
async function occupancy(x, v) {
  await housingApi.setOccupancy(x.id, v)
  x.occupancy = v
  toast(v === 'free' ? t('Holat: Bo‘sh') : t('Holat: Band'))
}
const confirm = ref(false)
const target = ref(null)
const busy = ref(false)
function askRemove(x) { target.value = x; confirm.value = true }
async function remove() {
  busy.value = true
  await api.value.remove(target.value.id)
  busy.value = false; confirm.value = false
  toast(t('E’lon o‘chirildi'))
  load()
}
const preview = ref(null)
const previewOpen = ref(false)
function open(x) { preview.value = x; previewOpen.value = true }

const subtitle = (x) => (kind.value === 'job' ? `${salaryText(x)} · ${x.format === 'online' ? 'Online' : t(x.district || '')}` : `${priceText(x)} · ${t(x.district)}`)
</script>

<template>
  <div class="page-narrow lg:max-w-5xl!">
    <PageIntro class="mb-4" />
    <SegmentedControl v-model="tab" :options="tabs" class="mb-4 lg:max-w-md" data-testid="post-tabs" />

    <template v-if="tab === 'mine'">
      <div class="flex flex-wrap items-center gap-2 mb-4">
        <div class="min-w-0 flex-1"><ChipGroup v-model="status" :options="statusOpts" size="sm" /></div>
      </div>
      <div v-if="loading" class="grid lg:grid-cols-2 gap-3"><SkeletonCard :count="4" class="contents" /></div>
      <ErrorState v-else-if="error" :message="error" @retry="load" />
      <EmptyState v-else-if="!list.length" :title="items.length ? $t('Bu holatda e’lon yo‘q') : $t('Hali e’lon joylamagansiz')" :text="$t('Birinchi e’loningizni 2 daqiqada qo‘shing.')" :illu="kind === 'job' ? 'briefcase' : 'house'">
        <BaseButton :icon="Plus" @click="tab = 'new'">{{ $t('Yangi e’lon') }}</BaseButton>
      </EmptyState>
      <TransitionGroup v-else tag="div" name="list" class="grid lg:grid-cols-2 gap-3 items-start" data-testid="my-listings">
        <MyListingCard
          v-for="x in list" :key="x.id" :item="x" :kind="kind" :subtitle="subtitle(x)"
          :count="kind === 'job' ? x.applicationsCount : x.requestsCount" :count-label="kind === 'job' ? $t('ariza') : $t('so‘rov')"
          @open="open" @edit="edit" @duplicate="duplicate" @toggle="toggle" @remove="askRemove" @occupancy="occupancy"
        />
      </TransitionGroup>
    </template>

    <div v-else class="card p-5 lg:p-7 animate-fade-up">
      <h2 class="text-[20px] font-extrabold tracking-tight mb-5">{{ editing ? $t('E’lonni tahrirlash') : kind === 'job' ? $t('Yangi vakansiya') : $t('Yangi uy e’loni') }}</h2>
      <JobForm v-if="kind === 'job'" :key="editing?.id || 'new'" :initial="editing" :profile="session.user" :loading="saving" :submit-text="editing ? $t('Saqlash va qayta yuborish') : undefined" @submit="submit" @cancel="tab = 'mine'" />
      <HouseForm v-else :key="editing?.id || 'new'" :initial="editing" :profile="session.user" :loading="saving" :submit-text="editing ? $t('Saqlash va qayta yuborish') : undefined" @submit="submit" @cancel="tab = 'mine'" />
    </div>

    <ConfirmModal v-model="confirm" :title="$t('E’lonni o‘chirish')" :text="$t('“{x}” butunlay o‘chiriladi. Bu amalni ortga qaytarib bo‘lmaydi.', { x: target?.title })" :confirm-text="$t('O‘chirish')" danger :loading="busy" @confirm="remove" />
    <JobDetailModal v-if="kind === 'job'" v-model="previewOpen" :job="preview" mode="viewer" />
    <HouseDetailModal v-else v-model="previewOpen" :house="preview && { ...preview, owner: { name: [session.user?.firstName, session.user?.lastName].join(' ') } }" mode="viewer" />
  </div>
</template>
