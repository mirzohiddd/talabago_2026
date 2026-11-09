<script setup>
import { t } from '@/i18n'
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Search, Eye, Pencil, Trash2, Megaphone, Radio, MousePointerClick, RotateCcw, Image as ImageIcon, Clapperboard, ChevronUp, ChevronDown } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import IlluSearchEmpty from '@/components/illustrations/IlluSearchEmpty.vue'
import AdThumb from '@/components/ads/AdThumb.vue'
import AdStatus from '@/components/ads/AdStatus.vue'
import AdPreviewModal from '@/components/ads/AdPreviewModal.vue'
import AdCarousel from '@/components/ads/AdCarousel.vue'
import { adsStore, ensureAdsLoaded, adsApi, refreshAds } from '@/services/ads'
import { AD_STATES, AD_PLACEMENTS, adState, isAdVisible, sortAds } from '@/config/ads'
import { useNow } from '@/composables/useNow'
import { formatTashkent } from '@/utils/tashkentTime'
import { toast } from '@/stores/toast'

const router = useRouter()
const now = useNow()
const loading = ref(!adsStore.loaded)
ensureAdsLoaded().then(() => (loading.value = false))
// Statistika (ko‘rish/bosish) avtomatik yangilanadi: services/live.js reklamalar o‘zgarganini sezsa qayta yuklaydi

const q = ref('')
const filter = ref('all')
const withState = computed(() => adsStore.items.map((a) => ({ ad: a, state: adState(a, now.value) })))
const counts = computed(() => withState.value.reduce((m, x) => ((m[x.state] = (m[x.state] || 0) + 1), m), {}))
const filterOptions = computed(() => [
  { value: 'all', label: `${t('Barchasi')} · ${adsStore.items.length}` },
  ...Object.entries(AD_STATES).map(([k, v]) => ({ value: k, label: `${t(v.label)} · ${counts.value[k] || 0}` })),
])
const rows = computed(() => {
  const s = q.value.trim().toLowerCase()
  return sortAds(withState.value
    .filter((x) => filter.value === 'all' || x.state === filter.value)
    .filter((x) => !s || [x.ad.name, x.ad.title].some((v) => v?.toLowerCase().includes(s)))
    .map((x) => x.ad))
})
const totals = computed(() => {
  const v = adsStore.items.reduce((s, a) => s + a.views, 0)
  const c = adsStore.items.reduce((s, a) => s + a.clicks, 0)
  return { v, c, ctr: v ? ((c / v) * 100).toFixed(1) + '%' : '—' }
})
const tiles = computed(() => [
  { label: t('Jami reklamalar'), value: adsStore.items.length, icon: Megaphone, tone: 'brand' },
  { label: t('Hozir ko‘rsatilmoqda'), value: counts.value.live || 0, icon: Radio },
  { label: t('Ko‘rishlar'), value: totals.value.v.toLocaleString('ru-RU'), icon: Eye },
  { label: `${t('Bosishlar')} · CTR ${totals.value.ctr}`, value: totals.value.c.toLocaleString('ru-RU'), icon: MousePointerClick, tone: 'dark' },
])
const fmtN = (n) => (n || 0).toLocaleString('ru-RU')
/** CTR = bosishlar / ko‘rishlar (serverda hisoblangan real raqamlar) */
const ctr = (ad) => (ad.views ? `${((ad.clicks / ad.views) * 100).toFixed(1)}%` : '—')

// Jonli ko‘rinish
const livePlacement = ref('/student/jobs')
const liveCount = computed(() => adsStore.items.filter((a) => isAdVisible(a, livePlacement.value, now.value)).length)

// Amallar
const viewing = ref(null)
const viewOpen = ref(false)
const deleting = ref(null)
const deleteOpen = ref(false)
const removing = ref(false)

function view(ad) { viewing.value = ad; viewOpen.value = true }
function edit(ad) { viewOpen.value = false; router.push(`/ads/${ad.id}/edit`) }
function askDelete(ad) { deleting.value = ad; deleteOpen.value = true }
async function remove() {
  removing.value = true
  await adsApi.remove(deleting.value.id)
  removing.value = false
  deleteOpen.value = false
  toast(t('Reklama o‘chirildi'))
}
async function toggle(ad, val) {
  if (adState(ad, now.value) === 'expired') return toast(t('Muddati tugagan — avval tugash sanasini o‘zgartiring'), 'error')
  try {
    await adsApi.setEnabled(ad.id, val)
    toast(val ? t('Reklama aktiv qilindi') : t('Reklama noaktiv qilindi'))
  } catch (e) { toast(e.message, 'error') }
}
const ordered = computed(() => sortAds(adsStore.items).map((a) => a.id))
const canMove = (ad, dir) => { const i = ordered.value.indexOf(ad.id); return i + dir >= 0 && i + dir < ordered.value.length }
async function move(ad, dir) { await adsApi.move(ad.id, dir) }

// Boshqa administrator o‘zgartirgan bo‘lsa — yangilash
const refreshing = ref(false)
async function reload() { refreshing.value = true; await refreshAds(); refreshing.value = false }
</script>

<template>
  <div>
    <PageHeader :title="$t('Reklama boshqaruvi')" :subtitle="$t('Barcha vaqtlar Toshkent vaqti (UTC+5) bo‘yicha')" illu="video">
      <BaseButton variant="ghost" size="sm" :icon="RotateCcw" :loading="refreshing" @click="reload">{{ $t('Yangilash') }}</BaseButton>
      <BaseButton size="sm" :icon="Plus" @click="router.push('/ads/new')">{{ $t('Reklama qo‘shish') }}</BaseButton>
    </PageHeader>

    <div class="grid grid-cols-2 lg:grid-cols-4 gap-2 stagger">
      <div v-for="t in tiles" :key="t.label" :class="['rounded-2xl p-3.5 relative overflow-hidden', t.tone === 'brand' ? 'bg-brand text-white' : t.tone === 'dark' ? 'bg-ink text-white' : 'bg-surface']">
        <component :is="t.icon" class="absolute -right-2 -bottom-2 size-14 opacity-15" />
        <p class="text-2xl font-extrabold leading-none tabular-nums">{{ loading ? '–' : t.value }}</p>
        <p class="text-[12px] font-semibold opacity-80 mt-1.5">{{ t.label }}</p>
      </div>
    </div>

    <div class="mt-5 flex flex-col md:flex-row md:items-center gap-3">
      <div class="min-w-0 flex-1"><ChipGroup v-model="filter" :options="filterOptions" size="sm" /></div>
      <label class="flex items-center gap-2 h-10 px-3 rounded-xl border border-line md:w-64 focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10 transition">
        <Search class="size-4 text-muted" />
        <input v-model="q" type="search" :placeholder="$t('Nomi bo‘yicha qidirish')" class="flex-1 min-w-0 outline-none text-sm bg-transparent" />
      </label>
    </div>

    <!-- Yuklanish -->
    <div v-if="loading" class="mt-4 space-y-2"><div v-for="i in 4" :key="i" class="skeleton h-16" /></div>

    <EmptyState v-else-if="!rows.length" :title="adsStore.items.length ? 'Mos reklama topilmadi' : 'Hali reklama yo‘q'" :text="adsStore.items.length ? 'Filtr yoki qidiruvni o‘zgartiring.' : 'Birinchi reklamani qo‘shing — u Header Carousel’da ko‘rinadi.'">
      <template #art><IlluSearchEmpty /></template>
      <BaseButton v-if="!adsStore.items.length" :icon="Plus" @click="router.push('/ads/new')">{{ $t('Reklama qo‘shish') }}</BaseButton>
    </EmptyState>

    <template v-else>
      <!-- Jadval (planshet va kompyuter) -->
      <div class="hidden md:block mt-4 crm-card overflow-x-auto">
        <table class="w-full min-w-[940px] text-[13.5px]" data-testid="ads-table">
          <thead>
            <tr class="text-left text-[11.5px] uppercase tracking-wide text-muted border-b border-line">
              <th class="th">{{ $t('Tartib') }}</th><th class="th">{{ $t('Preview') }}</th><th class="th">{{ $t('Reklama nomi') }}</th><th class="th">{{ $t('Turi') }}</th><th class="th">{{ $t('Boshlanish') }}</th>
              <th class="th">{{ $t('Tugash') }}</th><th class="th">{{ $t('Holati') }}</th><th class="th text-right">{{ $t('Ko‘rishlar') }}</th><th class="th text-right">{{ $t('Bosishlar') }}</th><th class="th text-right">CTR</th><th class="th text-right sticky right-0 bg-white">{{ $t('Amallar') }}</th>
            </tr>
          </thead>
          <TransitionGroup tag="tbody" name="list">
            <tr v-for="ad in rows" :key="ad.id" class="group/row border-b border-line last:border-0 hover:bg-[#fafafb] transition-colors">
              <td class="td">
                <div class="flex items-center gap-1">
                  <span class="w-5 text-center font-bold tabular-nums">{{ ad.order }}</span>
                  <div class="flex flex-col">
                    <button class="order-btn" :disabled="!canMove(ad, -1)" :aria-label="`${ad.name}: yuqoriga`" @click="move(ad, -1)"><ChevronUp class="size-3.5" /></button>
                    <button class="order-btn" :disabled="!canMove(ad, 1)" :aria-label="`${ad.name}: pastga`" @click="move(ad, 1)"><ChevronDown class="size-3.5" /></button>
                  </div>
                </div>
              </td>
              <td class="td"><button class="block rounded-lg hover:ring-2 hover:ring-brand-200 transition" :aria-label="$t('Ko‘rish')" @click="view(ad)"><AdThumb :ad="ad" size="sm" /></button></td>
              <td class="td max-w-[170px]"><p class="font-semibold truncate" :title="ad.name">{{ ad.name }}</p><p class="text-xs text-muted truncate">{{ ad.title || '—' }}</p></td>
              <td class="td"><span class="type"><component :is="ad.type === 'image' ? ImageIcon : Clapperboard" class="size-3.5" />{{ ad.type === 'image' ? 'Rasm' : 'Video' }}</span></td>
              <td class="td tabular-nums whitespace-nowrap"><p>{{ formatTashkent(ad.startAt).split(', ')[0] }}</p><p class="text-xs text-muted">{{ formatTashkent(ad.startAt).split(', ')[1] }}</p></td>
              <td class="td tabular-nums whitespace-nowrap"><p>{{ formatTashkent(ad.endAt).split(', ')[0] }}</p><p class="text-xs text-muted">{{ formatTashkent(ad.endAt).split(', ')[1] }}</p></td>
              <td class="td w-[168px]"><AdStatus :ad="ad" :now="now" wrap /></td>
              <td class="td text-right tabular-nums font-semibold">{{ fmtN(ad.views) }}</td>
              <td class="td text-right tabular-nums font-semibold">{{ fmtN(ad.clicks) }}</td>
              <td class="td text-right tabular-nums text-muted" data-testid="ad-ctr">{{ ctr(ad) }}</td>
              <td class="td sticky right-0 bg-white group-hover/row:bg-[#fafafb] shadow-[-8px_0_12px_-10px_rgba(17,17,17,.25)] xl:shadow-none">
                <div class="flex items-center justify-end gap-0.5">
                  <button class="icon" :title="$t('Ko‘rish')" :aria-label="$t('Ko‘rish')" @click="view(ad)"><Eye class="size-[18px]" /></button>
                  <button class="icon" :title="$t('Tahrirlash')" :aria-label="$t('Tahrirlash')" @click="edit(ad)"><Pencil class="size-[18px]" /></button>
                  <button class="icon hover:text-danger! hover:bg-danger/10!" :title="$t('O‘chirish')" :aria-label="$t('O‘chirish')" @click="askDelete(ad)"><Trash2 class="size-[18px]" /></button>
                  <span class="ml-1" :title="adState(ad, now) === 'expired' ? 'Muddati tugagan — tugash sanasini o‘zgartiring' : ad.enabled ? 'Noaktiv qilish' : 'Aktiv qilish'">
                    <ToggleSwitch :model-value="ad.enabled" :aria-label="`${ad.name}: Aktiv/Noaktiv`" :disabled="adState(ad, now) === 'expired'" :class="adState(ad, now) === 'expired' && 'opacity-40'" @update:model-value="toggle(ad, $event)" />
                  </span>
                </div>
              </td>
            </tr>
          </TransitionGroup>
        </table>
      </div>

      <!-- Kartochkalar (telefon) -->
      <TransitionGroup tag="div" name="list" class="md:hidden mt-4 space-y-3" data-testid="ads-cards">
        <article v-for="ad in rows" :key="ad.id" class="card p-3.5">
          <div class="flex gap-3">
            <button :aria-label="$t('Ko‘rish')" @click="view(ad)"><AdThumb :ad="ad" /></button>
            <div class="min-w-0 flex-1">
              <p class="font-semibold leading-snug line-clamp-2"><span class="text-muted tabular-nums">#{{ ad.order }}</span> {{ ad.name }}</p>
              <span class="type mt-1"><component :is="ad.type === 'image' ? ImageIcon : Clapperboard" class="size-3.5" />{{ ad.type === 'image' ? 'Rasm' : 'Video' }}</span>
            </div>
            <ToggleSwitch class="shrink-0" :model-value="ad.enabled" :aria-label="`${ad.name}: Aktiv/Noaktiv`" :disabled="adState(ad, now) === 'expired'" :class="adState(ad, now) === 'expired' && 'opacity-40'" @update:model-value="toggle(ad, $event)" />
          </div>
          <div class="mt-3"><AdStatus :ad="ad" :now="now" /></div>
          <dl class="grid grid-cols-2 gap-x-3 gap-y-2 mt-3 text-[12.5px]">
            <div><dt class="text-muted">{{ $t('Boshlanish') }}</dt><dd class="font-semibold tabular-nums">{{ formatTashkent(ad.startAt) }}</dd></div>
            <div><dt class="text-muted">{{ $t('Tugash') }}</dt><dd class="font-semibold tabular-nums">{{ formatTashkent(ad.endAt) }}</dd></div>
            <div><dt class="text-muted">{{ $t('Ko‘rishlar') }}</dt><dd class="font-semibold tabular-nums">{{ fmtN(ad.views) }}</dd></div>
            <div><dt class="text-muted">{{ $t('Bosishlar') }}</dt><dd class="font-semibold tabular-nums">{{ fmtN(ad.clicks) }} <span class="text-muted font-normal">· CTR {{ ctr(ad) }}</span></dd></div>
          </dl>
          <div class="flex gap-2 mt-3 pt-3 border-t border-dashed border-line">
            <button class="mbtn" @click="view(ad)"><Eye class="size-4" />{{ $t('Ko‘rish') }}</button>
            <button class="mbtn" @click="edit(ad)"><Pencil class="size-4" />{{ $t('Tahrirlash') }}</button>
            <button class="mbtn text-danger! ml-auto" :aria-label="$t('O‘chirish')" @click="askDelete(ad)"><Trash2 class="size-4" /></button>
          </div>
        </article>
      </TransitionGroup>
    </template>

    <!-- Jonli ko‘rinish -->
    <section class="mt-8 card p-4 md:p-5">
      <div class="flex flex-wrap items-end gap-3 mb-1">
        <div class="mr-auto">
          <h2 class="font-bold text-lg">{{ $t('Jonli ko‘rinish') }}</h2>
          <p class="text-sm text-muted">Tanlangan sahifada foydalanuvchi hozir ko‘radigan carousel · {{ liveCount }} ta reklama</p>
        </div>
        <BaseSelect v-model="livePlacement" :options="AD_PLACEMENTS.map((p) => ({ ...p, label: $t(p.label) }))" class="w-full sm:w-64" />
      </div>
      <div class="max-w-md">
        <AdCarousel :key="livePlacement" :placement="livePlacement" preview />
        <p v-if="!liveCount" class="mt-3 rounded-2xl bg-surface text-muted text-sm text-center py-10">{{ $t('Bu sahifada hozir aktiv reklama yo‘q') }}</p>
      </div>
    </section>

    <AdPreviewModal v-model="viewOpen" :ad="viewing" :now="now" @edit="edit" @toggle="toggle" />
    <ConfirmModal v-model="deleteOpen" :title="$t('Reklamani o‘chirish')" :text="`“${deleting?.name}” va uning fayli o‘chiriladi. Bu amalni ortga qaytarib bo‘lmaydi.`" :confirm-text="$t('O‘chirish')" danger :loading="removing" @confirm="remove" />
  </div>
</template>

<style scoped>
@reference "../../style.css";
.th { @apply px-2.5 py-3 font-semibold whitespace-nowrap; }
.td { @apply px-2.5 py-3 align-middle; }
.type { @apply inline-flex items-center gap-1 h-6 px-2 rounded-md bg-surface text-xs font-semibold text-ink-2; }
.order-btn { @apply size-5 grid place-items-center rounded text-muted hover:bg-brand-50 hover:text-brand-600 disabled:opacity-25 disabled:pointer-events-none; }
.icon { @apply size-8 grid place-items-center rounded-lg text-ink-2 hover:bg-brand-50 hover:text-brand-600 transition active:scale-90; }
.mbtn { @apply inline-flex items-center gap-1.5 h-9 px-3 rounded-xl bg-surface text-[13px] font-semibold text-ink-2 hover:bg-brand-50 hover:text-brand-600 transition; }
</style>