<script setup>
/** Foydalanuvchilar: barcha rollar bitta joyda. Qidiruv, filtrlar, rolga mos profil, bloklash va tahrirlash. */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Eye, Ban, CheckCircle2, Pencil, Phone, Send, MapPin, GraduationCap, Building, Calendar, Cake, FileText, Briefcase, Home, BookOpen, LifeBuoy, CalendarDays, Factory, Image as ImageIcon } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import Pagination from '@/components/crm/Pagination.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import SideDrawer from '@/components/crm/SideDrawer.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import Avatar from '@/components/ui/Avatar.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { ROLE_LABELS, SHIFTS, CITIES, CITY_LIST } from '@/config/status'
import { fileSize } from '@/utils/format'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const loading = ref(!crmStore.loaded)

const role = ref(['student', 'employer', 'landlord'].includes(route.query.role) ? route.query.role : 'all')
const status = ref('all')
const q = ref('')
const from = ref('')
const to = ref('')
const page = ref(1)
const PER = 12

const roleOptions = computed(() => [
  { value: 'all', label: `${t('Barchasi')} · ${crmStore.users.length}` },
  ...['student', 'employer', 'landlord'].map((r) => ({ value: r, label: `${t({ student: 'Talabalar', employer: 'Ish beruvchilar', landlord: 'Uy egalari' }[r])} · ${crmStore.users.filter((u) => u.role === r).length}` })),
])
const statusOptions = computed(() => [{ value: 'all', label: t('Barchasi') }, { value: 'active', label: t('Faol') }, { value: 'blocked', label: t('Bloklangan') }])
const filtered = computed(() => {
  const s = q.value.trim().toLowerCase()
  const digits = s.replace(/\D/g, '')
  const f = from.value ? Date.parse(from.value) : 0
  const tt = to.value ? Date.parse(to.value) + 86400000 : Infinity
  return crmStore.users
    .filter((u) => role.value === 'all' || u.role === role.value)
    .filter((u) => status.value === 'all' || u.status === status.value)
    .filter((u) => { const c = Date.parse(u.createdAt); return c >= f && c < tt })
    .filter((u) => !s || [fullName(u), u.telegram, u.company, u.university].some((v) => v?.toLowerCase().includes(s)) || (digits.length >= 3 && u.phone?.replace(/\D/g, '').includes(digits)))
    .sort((a, b) => Date.parse(b.createdAt) - Date.parse(a.createdAt))
})
const rows = computed(() => filtered.value.slice((page.value - 1) * PER, page.value * PER))
watch([role, status, q, from, to], () => (page.value = 1))

// Bog‘liq ma’lumotlar
const rel = (u) => ({
  apps: crmStore.applications.filter((a) => a.studentId === u.id),
  reqs: crmStore.requests.filter((r) => r.studentId === u.id),
  progress: crmStore.progress.filter((p) => p.userId === u.id),
  tickets: crmStore.tickets.filter((x) => x.userId === u.id),
  jobs: crmStore.jobs.filter((j) => j.employerId === u.id),
  houses: crmStore.houses.filter((h) => h.ownerId === u.id),
  incoming: u.role === 'employer' ? crmStore.applications.filter((a) => crmStore.jobs.some((j) => j.id === a.jobId && j.employerId === u.id))
    : crmStore.requests.filter((r) => crmStore.houses.some((h) => h.id === r.houseId && h.ownerId === u.id)),
})
const activity = (u) => {
  const r = rel(u)
  return u.role === 'student' ? t('{n} ta ariza', { n: r.apps.length + r.reqs.length }) : u.role === 'employer' ? t('{n} ta vakansiya', { n: r.jobs.length }) : t('{n} ta e’lon', { n: r.houses.length })
}
const courseTitle = (id) => crmStore.courses.find((c) => c.id === id)
const jobTitle = (id) => crmStore.jobs.find((j) => j.id === id)?.title
const houseTitle = (id) => crmStore.houses.find((h) => h.id === id)?.title
const shiftLabel = (v) => SHIFTS.find((s) => s.value === v)?.label

const current = ref(null)
const drawer = ref(false)
const confirm = ref(false)
const busy = ref(false)
function open(u) { current.value = u; drawer.value = true; router.replace({ query: { ...route.query, id: u.id } }) }
watch(drawer, (v) => { if (!v) { const { id, ...rest } = route.query; router.replace({ query: rest }) } })
function askToggle(u) { current.value = u; confirm.value = true }
async function toggleStatus() {
  busy.value = true
  const next = current.value.status === 'blocked' ? 'active' : 'blocked'
  await crmApi.setUserStatus(current.value.id, next)
  busy.value = false; confirm.value = false
  toast(next === 'blocked' ? t('Foydalanuvchi bloklandi') : t('Foydalanuvchi blokdan chiqarildi'))
}

// Tahrirlash
const editOpen = ref(false)
const form = ref({})
const errors = ref({})
function openEdit(u) { form.value = JSON.parse(JSON.stringify(u)); errors.value = {}; editOpen.value = true }
const cityOpts = computed(() => CITY_LIST.map((c) => ({ value: c, label: t(c) })))
const districtOpts = computed(() => (CITIES[form.value.city] || []).map((d) => ({ value: d, label: t(d) })))
const shiftOpts = computed(() => SHIFTS.map((s) => ({ value: s.value, label: t(s.label) })))
async function saveEdit() {
  errors.value = {}
  if (!form.value.firstName?.trim()) errors.value.firstName = t('Majburiy maydon')
  if (!/^\+?998[\s\d]{9,}$/.test((form.value.phone || '').replace(/\s/g, '').replace(/^\+/, '+'))) errors.value.phone = t('Telefon raqam noto‘g‘ri: +998 XX XXX XX XX')
  if (Object.keys(errors.value).length) return
  const { id, ...body } = form.value
  await crmApi.updateUser(id, body)
  editOpen.value = false
  toast(t('Profil saqlandi'))
}

ensureCrmLoaded().then(() => {
  loading.value = false
  const u = route.query.id && crmStore.users.find((x) => x.id === route.query.id)
  if (u) open(u)
})
</script>

<template>
  <div>
    <PageHeader :title="$t('Foydalanuvchilar')" illu="student">
      <SearchBox v-model="q" :placeholder="$t('Ism, familiya, telefon…')" data-testid="users-search" />
    </PageHeader>

    <div class="flex flex-wrap items-center gap-3 mb-4">
      <div class="min-w-0 flex-1 basis-full xl:basis-0"><ChipGroup v-model="role" :options="roleOptions" size="sm" /></div>
      <SegmentedControl v-model="status" class="w-full sm:w-72" :options="statusOptions" />
      <div class="flex flex-wrap sm:flex-nowrap items-center gap-2 text-sm w-full sm:w-auto">
        <span class="text-muted basis-full sm:basis-auto">{{ $t('Ro‘yxatdan o‘tgan') }}:</span>
        <input v-model="from" type="date" class="h-10 min-w-0 flex-1 sm:flex-none px-2.5 rounded-xl border border-line text-sm" :aria-label="$t('dan')" data-testid="from" />
        <span class="text-muted">—</span>
        <input v-model="to" type="date" class="h-10 min-w-0 flex-1 sm:flex-none px-2.5 rounded-xl border border-line text-sm" :aria-label="$t('gacha')" />
      </div>
    </div>

    <div class="crm-card overflow-hidden animate-fade-up">
      <SkeletonRows v-if="loading" :rows="8" :cols="6" />
      <EmptyState v-else-if="!filtered.length" :title="$t('Foydalanuvchi topilmadi')" :text="$t('Qidiruv yoki filtrlarni o‘zgartiring.')" illu="pen" />
      <template v-else>
        <div class="overflow-x-auto">
          <table class="crm-table min-w-[980px]" data-testid="users-table">
            <thead><tr><th>{{ $t('Foydalanuvchi') }}</th><th>{{ $t('Rol') }}</th><th>{{ $t('Telefon') }}</th><th>Telegram</th><th>{{ $t('Hudud') }}</th><th>{{ $t('Ro‘yxatdan o‘tgan') }}</th><th>{{ $t('Faollik') }}</th><th>{{ $t('Holat') }}</th><th class="text-right">{{ $t('Amallar') }}</th></tr></thead>
            <tbody>
              <tr v-for="u in rows" :key="u.id">
                <td>
                  <button class="flex items-center gap-3 text-left group" @click="open(u)">
                    <Avatar :name="fullName(u)" :src="u.logo" size="sm" />
                    <span class="min-w-0"><span class="block font-semibold group-hover:text-brand-600 transition-colors">{{ fullName(u) }}</span><span class="block text-xs text-muted truncate max-w-[200px]">{{ u.role === 'student' ? u.university : u.role === 'employer' ? u.company : $t('Uy egasi') }}</span></span>
                  </button>
                </td>
                <td><span class="pill">{{ $t(ROLE_LABELS[u.role]) }}</span></td>
                <td class="tabular-nums whitespace-nowrap">{{ u.phone }}</td>
                <td class="text-ink-2">{{ u.telegram || '—' }}</td>
                <td>{{ $t(u.district || '') }}{{ u.district ? ', ' : '' }}{{ $t(u.city || '') }}</td>
                <td class="tabular-nums whitespace-nowrap">{{ $date(u.createdAt) }}</td>
                <td class="text-ink-2 whitespace-nowrap">{{ activity(u) }}</td>
                <td><StatusBadge :status="u.status" /></td>
                <td>
                  <div class="flex justify-end gap-1">
                    <button class="icon-btn" :title="$t('Ko‘rish')" :aria-label="$t('Ko‘rish')" @click="open(u)"><Eye class="size-[18px]" /></button>
                    <button class="icon-btn" :title="$t('Tahrirlash')" :aria-label="$t('Tahrirlash')" @click="openEdit(u)"><Pencil class="size-[17px]" /></button>
                    <button v-if="u.status === 'active'" class="icon-btn icon-btn-danger" :title="$t('Bloklash')" :aria-label="$t('Bloklash')" data-testid="block" @click="askToggle(u)"><Ban class="size-[18px]" /></button>
                    <button v-else class="icon-btn" :title="$t('Blokdan chiqarish')" :aria-label="$t('Blokdan chiqarish')" @click="askToggle(u)"><CheckCircle2 class="size-[18px]" /></button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Pagination v-model="page" :total="filtered.length" :per-page="PER" />
      </template>
    </div>

    <!-- Profil -->
    <SideDrawer v-model="drawer" :title="fullName(current)" :subtitle="current && `${$t(ROLE_LABELS[current.role])} · ${$t('ID')}: ${current.id}`" width="560px">
      <div v-if="current" class="space-y-5" data-testid="user-profile">
        <div class="flex items-center gap-4"><Avatar :name="fullName(current)" :src="current.logo" size="lg" /><div><StatusBadge :status="current.status" /><p class="text-xs text-muted mt-1.5">{{ $t('Oxirgi faollik') }}: {{ $ago(current.lastActiveAt || current.updatedAt) }}</p></div></div>
        <dl class="grid grid-cols-2 gap-2.5 text-sm">
          <div class="info"><dt><Phone class="size-4" />{{ $t('Telefon') }}</dt><dd>{{ current.phone }}</dd></div>
          <div class="info"><dt><Send class="size-4" />Telegram</dt><dd>{{ current.telegram || '—' }}</dd></div>
          <template v-if="current.role === 'student'">
            <div class="info"><dt><Cake class="size-4" />{{ $t('Tug‘ilgan sana') }}</dt><dd>{{ current.birthDate ? $date(current.birthDate) : '—' }}</dd></div>
            <div class="info"><dt><CalendarDays class="size-4" />{{ $t('Smena') }}</dt><dd>{{ $t(shiftLabel(current.shift) || '—') }}</dd></div>
            <div class="info col-span-2"><dt><GraduationCap class="size-4" />{{ $t('O‘quv yurti va yo‘nalish') }}</dt><dd>{{ [current.university, current.faculty, current.course && $t('{n}-kurs', { n: current.course })].filter(Boolean).join(', ') || '—' }}</dd></div>
          </template>
          <template v-if="current.role === 'employer'">
            <div class="info"><dt><Building class="size-4" />{{ $t('Kompaniya') }}</dt><dd>{{ current.company }}</dd></div>
            <div class="info"><dt><Factory class="size-4" />{{ $t('Faoliyat sohasi') }}</dt><dd>{{ $t(current.industry || '—') }}</dd></div>
            <div class="info col-span-2"><dt><MapPin class="size-4" />{{ $t('Manzil') }}</dt><dd>{{ current.address || '—' }}</dd></div>
            <div class="info"><dt><ImageIcon class="size-4" />{{ $t('Logo') }}</dt><dd>{{ current.logo ? $t('Yuklangan') : '—' }}</dd></div>
          </template>
          <div class="info" :class="current.role === 'student' && 'col-span-2'"><dt><MapPin class="size-4" />{{ $t('Hudud') }}</dt><dd>{{ [$t(current.district || ''), $t(current.city || '')].filter(Boolean).join(', ') || '—' }}</dd></div>
          <div class="info"><dt><Calendar class="size-4" />{{ $t('Ro‘yxatdan o‘tgan') }}</dt><dd class="tabular-nums">{{ $dateTime(current.createdAt) }}</dd></div>
        </dl>

        <template v-if="current.role === 'student'">
          <section v-if="current.skills?.length"><h4 class="sec">{{ $t('Ko‘nikmalar') }}</h4><div class="flex flex-wrap gap-1.5"><span v-for="s in current.skills" :key="s" class="pill bg-brand-50! text-brand-700!">{{ $t(s) }}</span></div></section>
          <section><h4 class="sec">CV</h4><p class="text-sm flex items-center gap-2"><FileText class="size-4 text-danger" />{{ current.cv ? `${current.cv.name} · ${fileSize(current.cv.size || 0)}` : $t('CV yuklanmagan') }}</p></section>
          <section><h4 class="sec"><Briefcase class="size-4" />{{ $t('Ish arizalari') }} · {{ rel(current).apps.length }}</h4>
            <ul class="lst"><li v-for="a in rel(current).apps" :key="a.id"><span class="truncate">{{ jobTitle(a.jobId) || a.jobId }}</span><StatusBadge :status="a.status" /></li><li v-if="!rel(current).apps.length" class="text-muted">—</li></ul></section>
          <section><h4 class="sec"><Home class="size-4" />{{ $t('Ijara so‘rovlari') }} · {{ rel(current).reqs.length }}</h4>
            <ul class="lst"><li v-for="r in rel(current).reqs" :key="r.id"><span class="truncate">{{ houseTitle(r.houseId) || r.houseId }}</span><StatusBadge :status="r.status" /></li><li v-if="!rel(current).reqs.length" class="text-muted">—</li></ul></section>
          <section><h4 class="sec"><BookOpen class="size-4" />{{ $t('Kurs progressi') }}</h4>
            <ul class="lst"><li v-for="p in rel(current).progress" :key="p.id"><span>{{ $t(courseTitle(p.courseId)?.title || '') }}</span><span class="font-bold tabular-nums">{{ Math.round((p.completed.length / Math.max(1, courseTitle(p.courseId)?.lessons.length || 1)) * 100) }}%</span></li><li v-if="!rel(current).progress.length" class="text-muted">—</li></ul></section>
        </template>
        <template v-else>
          <section><h4 class="sec"><component :is="current.role === 'employer' ? Briefcase : Home" class="size-4" />{{ current.role === 'employer' ? $t('E’lonlari') : $t('Uy e’lonlari') }} · {{ (current.role === 'employer' ? rel(current).jobs : rel(current).houses).length }}</h4>
            <ul class="lst"><li v-for="x in current.role === 'employer' ? rel(current).jobs : rel(current).houses" :key="x.id"><RouterLink :to="{ path: current.role === 'employer' ? '/jobs' : '/housing', query: { id: x.id } }" class="truncate hover:text-brand-700">{{ x.title }}</RouterLink><StatusBadge :status="x.status" /></li></ul></section>
          <section><h4 class="sec">{{ current.role === 'employer' ? $t('Kelgan arizalar') : $t('Ijara so‘rovlari') }} · {{ rel(current).incoming.length }}</h4></section>
        </template>
        <section><h4 class="sec"><LifeBuoy class="size-4" />{{ $t('Support murojaatlari') }} · {{ rel(current).tickets.length }}</h4>
          <ul class="lst"><li v-for="tk in rel(current).tickets" :key="tk.id"><RouterLink :to="`/support/${tk.id}`" class="truncate hover:text-brand-700">{{ tk.subject }}</RouterLink><StatusBadge :status="tk.status" /></li><li v-if="!rel(current).tickets.length" class="text-muted">—</li></ul></section>
      </div>
      <template #footer>
        <div class="flex gap-2">
          <BaseButton variant="soft" :icon="Pencil" class="flex-1" @click="openEdit(current)">{{ $t('Tahrirlash') }}</BaseButton>
          <BaseButton v-if="current?.status === 'active'" class="flex-1" variant="danger" :icon="Ban" @click="confirm = true">{{ $t('Bloklash') }}</BaseButton>
          <BaseButton v-else class="flex-1" :icon="CheckCircle2" @click="confirm = true">{{ $t('Blokdan chiqarish') }}</BaseButton>
        </div>
      </template>
    </SideDrawer>

    <BaseModal v-model="editOpen" :title="$t('Profilni tahrirlash')" :subtitle="$t('O‘zgarishlar foydalanuvchiga ko‘rinadi')" wide>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.firstName" :label="$t('Ism')" required :error="errors.firstName" />
        <BaseInput v-model="form.lastName" :label="$t('Familiya')" />
        <BaseInput v-model="form.phone" :label="$t('Telefon')" required :error="errors.phone" />
        <BaseInput v-model="form.telegram" label="Telegram" />
        <BaseSelect v-model="form.city" :label="$t('Shahar')" :options="cityOpts" />
        <BaseSelect v-model="form.district" :label="$t('Tuman')" :options="districtOpts" :placeholder="$t('Tanlang')" />
        <template v-if="form.role === 'student'">
          <BaseInput v-model="form.university" :label="$t('O‘quv yurti')" />
          <BaseInput v-model="form.faculty" :label="$t('Yo‘nalish')" />
          <BaseSelect v-model="form.shift" :label="$t('O‘qish smenasi')" :options="shiftOpts" :placeholder="$t('Tanlang')" />
          <BaseInput v-model="form.birthDate" type="date" :label="$t('Tug‘ilgan sana')" />
        </template>
        <template v-if="form.role === 'employer'">
          <BaseInput v-model="form.company" :label="$t('Kompaniya nomi')" />
          <BaseInput v-model="form.industry" :label="$t('Faoliyat sohasi')" />
          <BaseInput v-model="form.address" :label="$t('Kompaniya manzili')" class="sm:col-span-2" />
        </template>
      </div>
      <template #footer><BaseButton block @click="saveEdit">{{ $t('Saqlash') }}</BaseButton></template>
    </BaseModal>

    <ConfirmModal
      v-model="confirm"
      :title="current?.status === 'blocked' ? $t('Blokdan chiqarish') : $t('Foydalanuvchini bloklash')"
      :text="current?.status === 'blocked' ? $t('{x} yana ilovadan foydalana oladi.', { x: fullName(current) }) : $t('{x} ilovaga kira olmaydi va e’lonlari yashiriladi.', { x: fullName(current) })"
      :confirm-text="current?.status === 'blocked' ? $t('Blokdan chiqarish') : $t('Bloklash')"
      :danger="current?.status !== 'blocked'" :loading="busy" @confirm="toggleStatus"
    />
  </div>
</template>

<style scoped>
@reference "../../style.css";
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply flex items-center gap-1.5 text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-semibold; }
.sec { @apply flex items-center gap-1.5 font-bold text-sm mb-2; }
.lst { @apply space-y-1.5 text-sm; }
.lst li { @apply flex items-center justify-between gap-3; }
</style>
