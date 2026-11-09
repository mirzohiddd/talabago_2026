<script setup>
/**
 * Ish e’lonlari va Turar joylar uchun umumiy moderatsiya jadvali.
 * Amallar: ko‘rish, tasdiqlash, sabab bilan rad etish, yashirish / qayta ko‘rsatish, tahrirlash, o‘chirish.
 */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, EyeOff, CheckCircle2, XCircle, Trash2, Pencil, RotateCcw } from 'lucide-vue-next'
import PageHeader from './PageHeader.vue'
import SearchBox from './SearchBox.vue'
import Pagination from './Pagination.vue'
import SkeletonRows from './SkeletonRows.vue'
import SideDrawer from './SideDrawer.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { STATUS } from '@/config/status'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const props = defineProps({
  title: String,
  items: Array,
  loading: Boolean,
  columns: Array, // [{ key, label, class? }]
  filterKey: String,
  filterOptions: Array,
  searchFields: Array,
  api: Object, // { approve, reject, setStatus, update, remove }
  editFields: Array, // [{ key, label, type?, textarea? }]
  rejectReasons: Array,
  testid: String,
  illu: String,
})
const route = useRoute()
const router = useRouter()
const STATES = ['pending', 'active', 'rejected', 'hidden', 'closed']
const status = ref(STATES.includes(route.query.status) ? route.query.status : 'all')
const filter = ref('all')
const q = ref('')
const page = ref(1)
const PER = 12
const statusChips = computed(() => [
  { value: 'all', label: `${t('Barchasi')} · ${props.items.length}` },
  ...STATES.map((s) => ({ value: s, label: `${t(STATUS[s].label)} · ${props.items.filter((i) => i.status === s).length}` })),
])
const filtered = computed(() => {
  const s = q.value.trim().toLowerCase()
  return props.items
    .filter((i) => status.value === 'all' || i.status === status.value)
    .filter((i) => filter.value === 'all' || i[props.filterKey] === filter.value)
    .filter((i) => !s || props.searchFields.some((f) => String(i[f] ?? '').toLowerCase().includes(s)))
    .sort((a, b) => (a.status === 'pending' ? -1 : 0) - (b.status === 'pending' ? -1 : 0) || Date.parse(b.createdAt) - Date.parse(a.createdAt))
})
const rows = computed(() => filtered.value.slice((page.value - 1) * PER, page.value * PER))
watch([status, filter, q], () => (page.value = 1))

const current = ref(null)
const drawer = ref(false)
function view(i) { current.value = i; drawer.value = true }
watch(() => [props.loading, route.query.id], () => {
  const x = !props.loading && route.query.id && props.items.find((i) => i.id === route.query.id)
  if (x) view(x)
}, { immediate: true })
watch(drawer, (v) => { if (!v && route.query.id) { const { id, ...rest } = route.query; router.replace({ query: rest }) } })

async function approve(i) { await props.api.approve(i.id); toast(t('Tasdiqlandi — foydalanuvchilarga ko‘rinadi')) }
async function hide(i) { await props.api.setStatus(i.id, 'hidden'); toast(t('Yashirildi')) }
async function unhide(i) { await props.api.setStatus(i.id, 'active'); toast(t('Qayta ko‘rsatildi')) }

// Rad etish
const rjOpen = ref(false)
const rjReason = ref('')
const rjErr = ref('')
function askReject(i) { current.value = i; rjReason.value = ''; rjErr.value = ''; rjOpen.value = true }
async function reject() {
  if (rjReason.value.trim().length < 5) { rjErr.value = t('Sababni yozing (kamida 5 belgi)'); return }
  await props.api.reject(current.value.id, rjReason.value.trim())
  rjOpen.value = false
  toast(t('Rad etildi, sabab egasiga yuboriladi'))
}

// Tahrirlash
const edOpen = ref(false)
const form = ref({})
function askEdit(i) { current.value = i; form.value = Object.fromEntries(props.editFields.map((f) => [f.key, i[f.key]])); edOpen.value = true }
async function saveEdit() {
  const body = Object.fromEntries(props.editFields.map((f) => [f.key, f.type === 'number' ? +form.value[f.key] : form.value[f.key]]))
  await props.api.update(current.value.id, body)
  edOpen.value = false
  toast(t('Saqlandi'))
}

// O‘chirish
const del = ref(false)
const busy = ref(false)
function askDelete(i) { current.value = i; del.value = true }
async function remove() {
  busy.value = true
  await props.api.remove(current.value.id)
  busy.value = false; del.value = false; drawer.value = false
  toast(t('O‘chirildi'))
}
</script>

<template>
  <div>
    <PageHeader :title="title" :illu="illu"><SearchBox v-model="q" /></PageHeader>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <div class="min-w-0 flex-1"><ChipGroup v-model="status" :options="statusChips" size="sm" data-testid="mod-status" /></div>
      <BaseSelect v-model="filter" class="w-56" :options="[{ value: 'all', label: $t('Barcha turlar') }, ...filterOptions]" />
    </div>

    <div class="crm-card overflow-hidden animate-fade-up">
      <SkeletonRows v-if="loading" :rows="8" :cols="columns.length" />
      <EmptyState v-else-if="!filtered.length" :title="$t('Hech narsa topilmadi')" :text="$t('Qidiruv yoki filtrlarni o‘zgartiring.')" illu="pen" />
      <template v-else>
        <div class="overflow-x-auto">
          <table class="crm-table min-w-[1000px]" :data-testid="testid">
            <thead><tr><th v-for="c in columns" :key="c.key" :class="c.class">{{ c.label }}</th><th>{{ $t('Holat') }}</th><th class="text-right">{{ $t('Amallar') }}</th></tr></thead>
            <tbody>
              <tr v-for="i in rows" :key="i.id" :class="['closed', 'hidden'].includes(i.status) && 'opacity-70'" :data-id="i.id">
                <td v-for="c in columns" :key="c.key" :class="c.class"><slot :name="c.key" :item="i">{{ i[c.key] }}</slot></td>
                <td><StatusBadge :status="i.status" /></td>
                <td>
                  <div class="flex justify-end gap-1">
                    <button class="icon-btn" :title="$t('Ko‘rish')" :aria-label="$t('Ko‘rish')" @click="view(i)"><Eye class="size-[18px]" /></button>
                    <template v-if="i.status === 'pending'">
                      <button class="icon-btn text-success!" :title="$t('Tasdiqlash')" :aria-label="$t('Tasdiqlash')" data-testid="approve" @click="approve(i)"><CheckCircle2 class="size-[18px]" /></button>
                      <button class="icon-btn icon-btn-danger" :title="$t('Rad etish')" :aria-label="$t('Rad etish')" data-testid="reject" @click="askReject(i)"><XCircle class="size-[18px]" /></button>
                    </template>
                    <button v-else-if="i.status === 'active'" class="icon-btn" :title="$t('Yashirish')" :aria-label="$t('Yashirish')" @click="hide(i)"><EyeOff class="size-[18px]" /></button>
                    <button v-else-if="i.status === 'hidden'" class="icon-btn" :title="$t('Qayta ko‘rsatish')" :aria-label="$t('Qayta ko‘rsatish')" @click="unhide(i)"><RotateCcw class="size-[18px]" /></button>
                    <button class="icon-btn" :title="$t('Tahrirlash')" :aria-label="$t('Tahrirlash')" @click="askEdit(i)"><Pencil class="size-[17px]" /></button>
                    <button class="icon-btn icon-btn-danger" :title="$t('O‘chirish')" :aria-label="$t('O‘chirish')" @click="askDelete(i)"><Trash2 class="size-[18px]" /></button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Pagination v-model="page" :total="filtered.length" :per-page="PER" />
      </template>
    </div>

    <SideDrawer v-model="drawer" :title="current?.title" width="560px">
      <div v-if="current" class="space-y-4" data-testid="listing-detail">
        <StatusBadge :status="current.status" />
        <p v-if="current.status === 'rejected'" class="text-[13px] rounded-xl bg-danger/8 text-danger px-3 py-2.5"><b>{{ $t('Rad etish sababi') }}:</b> {{ current.rejectReason }}</p>
        <slot name="detail" :item="current" />
      </div>
      <template #footer>
        <div v-if="current" class="flex flex-wrap gap-2">
          <template v-if="current.status === 'pending' || current.status === 'rejected'">
            <BaseButton class="flex-1" :icon="CheckCircle2" data-testid="d-approve" @click="approve(current)">{{ $t('Tasdiqlash') }}</BaseButton>
            <BaseButton v-if="current.status === 'pending'" variant="danger" class="flex-1" :icon="XCircle" @click="askReject(current)">{{ $t('Rad etish') }}</BaseButton>
          </template>
          <BaseButton v-else-if="current.status === 'active'" variant="soft" class="flex-1" :icon="EyeOff" @click="hide(current)">{{ $t('Yashirish') }}</BaseButton>
          <BaseButton v-else-if="current.status === 'hidden'" variant="soft" class="flex-1" :icon="RotateCcw" @click="unhide(current)">{{ $t('Qayta ko‘rsatish') }}</BaseButton>
          <BaseButton variant="soft" :icon="Pencil" @click="askEdit(current)">{{ $t('Tahrirlash') }}</BaseButton>
          <BaseButton variant="danger" :icon="Trash2" :aria-label="$t('O‘chirish')" @click="del = true" />
        </div>
      </template>
    </SideDrawer>

    <BaseModal v-model="rjOpen" :title="$t('Rad etish')" :subtitle="current?.title">
      <div class="space-y-3">
        <div class="flex flex-wrap gap-1.5">
          <button v-for="r in rejectReasons" :key="r" class="h-8 px-3 rounded-full bg-surface hover:bg-brand-50 text-[12.5px] font-semibold" @click="rjReason = $t(r)">{{ $t(r) }}</button>
        </div>
        <BaseTextarea v-model="rjReason" :label="$t('Sabab (e’lon egasiga ko‘rinadi)')" :rows="3" :maxlength="300" :error="rjErr" required data-testid="reject-reason" />
      </div>
      <template #footer><BaseButton block variant="danger" :icon="XCircle" data-testid="reject-send" @click="reject">{{ $t('Rad etish') }}</BaseButton></template>
    </BaseModal>

    <BaseModal v-model="edOpen" :title="$t('Tahrirlash')" :subtitle="current?.title" wide>
      <div class="grid sm:grid-cols-2 gap-4">
        <template v-for="f in editFields" :key="f.key">
          <BaseTextarea v-if="f.textarea" v-model="form[f.key]" :label="f.label" :rows="4" class="sm:col-span-2" />
          <BaseInput v-else v-model="form[f.key]" :label="f.label" :type="f.type || 'text'" :class="f.wide && 'sm:col-span-2'" />
        </template>
      </div>
      <template #footer><BaseButton block @click="saveEdit">{{ $t('Saqlash') }}</BaseButton></template>
    </BaseModal>

    <ConfirmModal v-model="del" :title="$t('O‘chirish')" :text="$t('“{x}” butunlay o‘chiriladi. Bu amalni ortga qaytarib bo‘lmaydi.', { x: current?.title })" :confirm-text="$t('O‘chirish')" danger :loading="busy" @confirm="remove" />
  </div>
</template>
