<script setup>
/** Shikoyatlar: ko‘rib chiqish, hal qilish, e’lonni yashirish, akkauntni bloklash */
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { Briefcase, Building2, User, Smartphone, MessageSquareText, Clock, Send, EyeOff, Ban, ExternalLink } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import SideDrawer from '@/components/crm/SideDrawer.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Avatar from '@/components/ui/Avatar.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { STATUS, PRIORITY, COMPLAINT_STATUSES, ROLE_LABELS } from '@/config/status'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const loading = ref(!crmStore.loaded)
const TARGET_ICON = { job: Briefcase, house: Building2, user: User, app: Smartphone }
const TARGET_LABEL = { job: 'Vakansiya', house: 'Turar joy', user: 'Foydalanuvchi', app: 'Ilova' }

const status = ref('open')
const priority = ref('all')
const q = ref('')
const isOpen = (c) => ['new', 'in_review'].includes(c.status)
const chips = computed(() => [
  { value: 'open', label: `${t('Ochiq')} · ${crmStore.complaints.filter(isOpen).length}` },
  ...COMPLAINT_STATUSES.map((s) => ({ value: s, label: `${t(STATUS[s].label)} · ${crmStore.complaints.filter((c) => c.status === s).length}` })),
  { value: 'all', label: `${t('Barchasi')} · ${crmStore.complaints.length}` },
])
const PR = { high: 0, medium: 1, low: 2 }
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return crmStore.complaints
    .filter((c) => status.value === 'all' || (status.value === 'open' ? isOpen(c) : c.status === status.value))
    .filter((c) => priority.value === 'all' || c.priority === priority.value)
    .filter((c) => !s || [c.subject, c.message, c.category, c.from.name, c.target.label].some((v) => v?.toLowerCase().includes(s)))
    .sort((a, b) => PR[a.priority] - PR[b.priority] || Date.parse(b.createdAt) - Date.parse(a.createdAt))
})
const prioOpts = computed(() => [{ value: 'all', label: t('Barcha darajalar') }, ...Object.entries(PRIORITY).map(([value, p]) => ({ value, label: t(p.label) }))])
const stateOpts = computed(() => COMPLAINT_STATUSES.map((s) => ({ value: s, label: t(STATUS[s].label) })))

const current = ref(null)
const drawer = ref(false)
const form = ref({ status: 'new', note: '' })
const saving = ref(false)
function open(c) { current.value = c; form.value = { status: c.status === 'new' ? 'in_review' : c.status, note: '' }; drawer.value = true }
async function save() {
  saving.value = true
  await crmApi.updateComplaint(current.value.id, form.value)
  saving.value = false; form.value.note = ''
  toast(t('Shikoyat yangilandi'))
}

// Nishon: e’lon / foydalanuvchi
const listing = computed(() => {
  const tg = current.value?.target
  if (tg?.type === 'job') return crmStore.jobs.find((j) => j.id === tg.id)
  if (tg?.type === 'house') return crmStore.houses.find((h) => h.id === tg.id)
  return null
})
const accused = computed(() => {
  const tg = current.value?.target
  if (tg?.type === 'user') return crmStore.users.find((u) => u.id === tg.id)
  if (listing.value) return crmStore.users.find((u) => u.id === (listing.value.employerId || listing.value.ownerId))
  return null
})
async function hideListing() {
  const api = current.value.target.type === 'job' ? crmApi.jobs : crmApi.houses
  await api.setStatus(listing.value.id, 'hidden')
  await crmApi.updateComplaint(current.value.id, { status: 'resolved', note: t('E’lon yashirildi') })
  form.value.status = 'resolved'
  toast(t('E’lon yashirildi'))
}
const blockOpen = ref(false)
async function blockUser() {
  await crmApi.setUserStatus(accused.value.id, 'blocked')
  await crmApi.updateComplaint(current.value.id, { status: 'resolved', note: t('{x} bloklandi', { x: fullName(accused.value) }) })
  form.value.status = 'resolved'
  blockOpen.value = false
  toast(t('Foydalanuvchi bloklandi'))
}

ensureCrmLoaded().then(() => {
  loading.value = false
  const c = route.query.id && crmStore.complaints.find((x) => x.id === route.query.id)
  if (c) { status.value = 'all'; open(c) }
})
</script>

<template>
  <div>
    <PageHeader :title="$t('Shikoyatlar')" illu="mail"><SearchBox v-model="q" /></PageHeader>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <div class="min-w-0 flex-1"><ChipGroup v-model="status" :options="chips" size="sm" /></div>
      <BaseSelect v-model="priority" class="w-52" :options="prioOpts" />
    </div>

    <div class="crm-card overflow-hidden animate-fade-up">
      <SkeletonRows v-if="loading" :rows="7" :cols="5" />
      <EmptyState v-else-if="!list.length" :title="$t('Shikoyat yo‘q')" :text="$t('Bu holatda murojaatlar topilmadi.')" illu="pen" />
      <ul v-else class="divide-y divide-line" data-testid="complaints-list">
        <li v-for="c in list" :key="c.id">
          <button class="w-full text-left flex items-start gap-4 px-5 py-4 hover:bg-[#fafafb] transition-colors" @click="open(c)">
            <span :class="['mt-1.5 size-2.5 rounded-full shrink-0', c.status === 'new' ? 'bg-brand animate-pulse' : 'bg-transparent']" />
            <div class="min-w-0 flex-1">
              <div class="flex flex-wrap items-center gap-2">
                <p class="font-semibold">{{ $t(c.subject) }}</p>
                <StatusBadge :label="$t(PRIORITY[c.priority].label)" :tone="PRIORITY[c.priority].tone" />
                <span class="pill">{{ $t(c.category) }}</span>
              </div>
              <p class="text-sm text-ink-2 mt-1 line-clamp-1">{{ c.message }}</p>
              <p class="text-xs text-muted mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
                <span class="inline-flex items-center gap-1"><component :is="TARGET_ICON[c.target.type]" class="size-3.5" />{{ c.target.label }}</span>
                <span>{{ c.from.name }}</span>
                <span class="inline-flex items-center gap-1"><Clock class="size-3.5" />{{ $ago(c.createdAt) }}</span>
              </p>
            </div>
            <StatusBadge :status="c.status" class="shrink-0" />
          </button>
        </li>
      </ul>
    </div>

    <SideDrawer v-model="drawer" :title="$t(current?.subject || '')" :subtitle="current && `${$t(current.category)} · ${$dateTime(current.createdAt)}`" width="560px">
      <div v-if="current" class="space-y-5" data-testid="complaint-detail">
        <div class="flex flex-wrap gap-2"><StatusBadge :status="current.status" /><StatusBadge :label="`${$t('Muhimlik')}: ${$t(PRIORITY[current.priority].label)}`" :tone="PRIORITY[current.priority].tone" /></div>
        <div class="flex items-center gap-3 rounded-2xl border border-line p-3">
          <Avatar :name="current.from.name" />
          <div class="min-w-0"><RouterLink :to="{ path: '/users', query: { id: current.from.id } }" class="font-semibold hover:text-brand-700">{{ current.from.name }}</RouterLink><p class="text-xs text-muted">{{ $t(ROLE_LABELS[current.from.role] || 'Talaba') }} · {{ $t('murojaat egasi') }}</p></div>
        </div>
        <p class="rounded-2xl bg-surface p-4 text-[14.5px] leading-relaxed flex gap-2"><MessageSquareText class="size-4 text-muted shrink-0 mt-1" />{{ current.message }}</p>
        <div class="rounded-2xl border border-line p-3 text-sm space-y-3">
          <div class="flex items-center gap-3">
            <span class="size-9 rounded-xl bg-brand-50 text-brand-600 grid place-items-center"><component :is="TARGET_ICON[current.target.type]" class="size-[18px]" /></span>
            <div class="min-w-0 flex-1"><p class="text-xs text-muted">{{ $t(TARGET_LABEL[current.target.type]) }}</p><p class="font-semibold truncate">{{ current.target.label }}</p></div>
            <StatusBadge v-if="listing" :status="listing.status" />
            <RouterLink v-if="listing" :to="{ path: current.target.type === 'job' ? '/jobs' : '/housing', query: { id: listing.id } }" class="icon-btn" :aria-label="$t('Ochish')"><ExternalLink class="size-4" /></RouterLink>
          </div>
          <div class="flex flex-wrap gap-2">
            <BaseButton v-if="listing && listing.status !== 'hidden'" size="sm" variant="soft" :icon="EyeOff" data-testid="hide-listing" @click="hideListing">{{ $t('E’lonni yashirish') }}</BaseButton>
            <BaseButton v-if="accused && accused.status !== 'blocked'" size="sm" variant="danger" :icon="Ban" data-testid="block-accused" @click="blockOpen = true">{{ $t('Akkauntni bloklash') }}: {{ fullName(accused) }}</BaseButton>
            <span v-else-if="accused" class="text-xs text-danger font-semibold">{{ fullName(accused) }} · {{ $t('Bloklangan') }}</span>
          </div>
        </div>
        <div v-if="current.notes.length">
          <p class="label">{{ $t('Ichki izohlar') }}</p>
          <ol class="relative border-l-2 border-line ml-1.5 space-y-3 pl-4">
            <li v-for="(n, i) in current.notes" :key="i" class="relative">
              <span class="absolute -left-[23px] top-1 size-3 rounded-full bg-brand ring-4 ring-white" />
              <p class="text-xs text-muted tabular-nums">{{ $dateTime(n.at) }}</p><p class="text-sm">{{ n.text }}</p>
            </li>
          </ol>
        </div>
        <div class="space-y-3 pt-1">
          <BaseSelect v-model="form.status" :label="$t('Holat')" :options="stateOpts" />
          <BaseTextarea v-model="form.note" :label="$t('Ichki izoh (foydalanuvchiga ko‘rinmaydi)')" :rows="3" :maxlength="500" />
        </div>
      </div>
      <template #footer>
        <BaseButton block :icon="Send" :loading="saving" :disabled="current && form.status === current.status && !form.note.trim()" data-testid="complaint-save" @click="save">{{ $t('Saqlash') }}</BaseButton>
      </template>
    </SideDrawer>
    <ConfirmModal v-model="blockOpen" :title="$t('Akkauntni bloklash')" :text="$t('{x} ilovaga kira olmaydi va e’lonlari yashiriladi.', { x: fullName(accused) })" :confirm-text="$t('Bloklash')" danger @confirm="blockUser" />
  </div>
</template>
