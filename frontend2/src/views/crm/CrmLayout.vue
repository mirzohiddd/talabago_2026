<script setup>
/**
 * TalabaGo Support qobig‘i.
 * Desktop: yig‘iladigan sidebar (ochiq — ikonka + nom, yig‘ilgan — faqat ikonka + tooltip), holat localStorage’da.
 * Mobil: sidebar chapdan chiqadigan drawer. Sessiya muddati kuzatiladi.
 */
import { ref, computed, watch, onMounted, onBeforeUnmount, onErrorCaptured } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { LayoutDashboard, Users, Briefcase, Building2, Megaphone, MessageSquareWarning, Settings, LogOut, Menu, X, Clock, GraduationCap, Inbox, LifeBuoy, PanelLeftClose, PanelLeftOpen } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import Avatar from '@/components/ui/Avatar.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import { auth, logout, verifySession } from '@/services/auth'
import { crmStore, ensureCrmLoaded, refreshCrm } from '@/services/crm'
import { startLive, stopLive } from '@/services/live'
import { useNow } from '@/composables/useNow'
import { formatTashkent } from '@/utils/tashkentTime'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const now = useNow()
const drawer = ref(false)
const SKEY = 'talabago_crm_sidebar'
const collapsed = ref((() => { try { return localStorage.getItem(SKEY) === '1' } catch { return false } })())
watch(collapsed, (v) => { try { localStorage.setItem(SKEY, v ? '1' : '0') } catch {} })
ensureCrmLoaded()

const count = (list, fn) => crmStore[list].filter(fn).length
const nav = computed(() => [
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/users', label: 'Foydalanuvchilar', icon: Users },
  { to: '/jobs', label: 'Ish e’lonlari', icon: Briefcase, badge: count('jobs', (x) => x.status === 'pending') },
  { to: '/housing', label: 'Turar joylar', icon: Building2, badge: count('houses', (x) => x.status === 'pending') },
  { to: '/ads', label: 'Reklama boshqaruvi', icon: Megaphone },
  { to: '/courses', label: 'Kurslar boshqaruvi', icon: GraduationCap },
  { to: '/applications', label: 'Arizalar va so‘rovlar', icon: Inbox },
  { to: '/support', label: 'Support', icon: LifeBuoy, badge: count('tickets', (x) => x.status === 'new' || x.unreadBySupport) },
  { to: '/complaints', label: 'Shikoyatlar', icon: MessageSquareWarning, badge: count('complaints', (c) => c.status === 'new') },
  { to: '/settings', label: 'Sozlamalar', icon: Settings },
])
const isActive = (to) => route.path === to || route.path.startsWith(to + '/') || route.meta.section === to
const wide = computed(() => !collapsed.value || drawer.value)

async function doLogout(reason) {
  await logout()
  router.replace({ path: '/login', query: reason ? { expired: '1' } : {} })
  if (!reason) toast(t('Tizimdan chiqdingiz'))
}
let timer = null
let checking = false
// Muddat tugaganga o‘xshasa — serverdan tekshiriladi (sliding sessiya / boshqa tab); faqat server rad etsa chiqariladi
async function checkExpiry() {
  if (checking || !auth.expiresAt || auth.expiresAt > Date.now()) return
  checking = true
  try {
    if (!(await verifySession())) doLogout('expired')
  } finally {
    checking = false
  }
}
// Barcha sahifalar (Dashboard, foydalanuvchilar, e’lonlar, reklama, support, ...) avtomatik yangilanadi — services/live.js
onMounted(() => {
  timer = setInterval(checkExpiry, 15000)
  startLive()
})
onBeforeUnmount(() => { clearInterval(timer); stopLive() })
watch(() => route.path, () => (drawer.value = false))

// Sahifa ichidagi kutilmagan xato (chizish / setup / mount) butun ekranni oq qoldirmasin: xato kartasi + qayta yuklash.
// Tugma bosilgandagi xatolar bu yerda ushlanmaydi — ular odatdagidek toast bo‘lib chiqadi (main.js errorHandler).
const pageError = ref(null)
const FATAL = /render function|setup function|mounted hook|beforeMount hook|#runtime-(0|1|bm|m|sp)$/
onErrorCaptured((err, _inst, info) => {
  if (!FATAL.test(String(info || ''))) return
  console.error(err)
  pageError.value = err?.message || String(err)
  return false
})
watch(() => route.fullPath, () => (pageError.value = null))
const reloadPage = () => window.location.reload()

// Bo‘limlardan biri yuklanmasa (masalan, server uyg‘onayotganda 502) — ogohlantirish va qayta urinish
const retrying = ref(false)
async function retryLoad() {
  retrying.value = true
  try { await refreshCrm() } finally { retrying.value = false }
}
</script>

<template>
  <div class="min-h-full bg-[#fbfbfc]">
    <Transition name="fade"><div v-if="drawer" class="fixed inset-0 z-40 bg-ink/30 lg:hidden" @click="drawer = false" /></Transition>
    <aside
      :class="['fixed z-50 inset-y-0 left-0 bg-white border-r border-line flex flex-col transition-[transform,width] duration-300 ease-[cubic-bezier(.22,1,.36,1)]',
        drawer ? 'translate-x-0 w-[264px]' : '-translate-x-full lg:translate-x-0', collapsed && !drawer ? 'lg:w-[76px]' : 'lg:w-[248px]']"
      :aria-label="$t('CRM bo‘limlari')" data-testid="crm-sidebar" :data-collapsed="collapsed"
    >
      <div :class="['h-16 flex items-center gap-2 border-b border-line', wide ? 'px-5' : 'justify-center']">
        <RouterLink to="/dashboard"><AppLogo :size="wide ? 36 : 40" :variant="wide ? 'full' : 'mark'" /></RouterLink>
        <button class="ml-auto lg:hidden icon-btn" :aria-label="$t('Menyuni yopish')" @click="drawer = false"><X class="size-5" /></button>
      </div>
      <div v-if="wide" class="px-5 pt-4 pb-1"><span class="inline-flex h-6 px-2.5 items-center rounded-full bg-ink text-white text-[11px] font-bold tracking-wide">TALABAGO SUPPORT</span></div>
      <nav :class="['flex-1 px-3 py-3 space-y-0.5', wide ? 'overflow-y-auto' : 'overflow-visible']">
        <RouterLink
          v-for="n in nav" :key="n.to" :to="n.to"
          :class="['group relative flex items-center gap-3 h-11 rounded-xl text-[14px] font-semibold transition-colors', wide ? 'px-3' : 'justify-center', isActive(n.to) ? 'bg-brand-50 text-brand-700' : 'text-ink-2 hover:bg-surface hover:text-ink']"
          :aria-current="isActive(n.to) ? 'page' : undefined" :aria-label="!wide ? $t(n.label) : undefined"
        >
          <span v-if="isActive(n.to)" class="absolute left-0 top-2.5 bottom-2.5 w-[3px] rounded-r-full bg-brand" />
          <component :is="n.icon" class="size-[19px] shrink-0 transition-transform group-hover:scale-110" />
          <span v-if="wide" class="truncate">{{ $t(n.label) }}</span>
          <span v-if="n.badge && wide" class="ml-auto min-w-5 h-5 px-1.5 grid place-items-center rounded-full bg-brand text-white text-[11px] font-bold">{{ n.badge }}</span>
          <span v-else-if="n.badge" class="absolute top-1.5 right-2 size-2 rounded-full bg-brand ring-2 ring-white" />
          <span v-if="!wide" class="tip">{{ $t(n.label) }}<template v-if="n.badge"> · {{ n.badge }}</template></span>
        </RouterLink>
      </nav>
      <div class="p-3 border-t border-line space-y-1">
        <div :class="['flex items-center gap-3 p-2 rounded-xl', !wide && 'justify-center']">
          <Avatar :name="crmStore.settings.profile?.name || auth.user?.name" :src="crmStore.settings.profile?.avatar" size="sm" />
          <div v-if="wide" class="min-w-0 flex-1">
            <p class="text-sm font-semibold truncate">{{ crmStore.settings.profile?.name || auth.user?.name }}</p>
            <p class="text-xs text-muted truncate">@{{ auth.user?.username }}</p>
          </div>
          <button v-if="wide" class="icon-btn icon-btn-danger" :title="$t('Chiqish')" :aria-label="$t('Chiqish')" @click="doLogout()"><LogOut class="size-[18px]" /></button>
        </div>
        <button
          :class="['hidden lg:flex w-full items-center gap-3 h-10 rounded-xl text-[13px] font-semibold text-muted hover:bg-surface hover:text-ink transition', wide ? 'px-3' : 'justify-center']"
          :aria-label="collapsed ? $t('Menyuni ochish') : $t('Menyuni yig‘ish')" :aria-expanded="!collapsed" data-testid="crm-collapse" @click="collapsed = !collapsed"
        >
          <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" class="size-[19px]" /><span v-if="wide">{{ $t('Menyuni yig‘ish') }}</span>
        </button>
      </div>
    </aside>

    <div :class="['min-h-full flex flex-col transition-[padding] duration-300', collapsed ? 'lg:pl-[76px]' : 'lg:pl-[248px]']">
      <header class="sticky top-0 z-30 h-16 bg-white/85 backdrop-blur-xl border-b border-line flex items-center gap-3 px-4 lg:px-8">
        <button class="lg:hidden icon-btn" :aria-label="$t('Menyu')" data-testid="crm-menu" @click="drawer = true"><Menu class="size-5" /></button>
        <p class="font-semibold text-[15px] truncate">{{ $t(route.meta.title || '') }}</p>
        <span class="ml-auto hidden sm:inline-flex items-center gap-1.5 text-[13px] text-muted tabular-nums" data-testid="tz-clock" :title="$t('Barcha vaqtlar Asia/Tashkent bo‘yicha')">
          <Clock class="size-4" />{{ $t('Toshkent') }} · {{ formatTashkent(new Date(now).toISOString(), { seconds: true }) }}
        </span>
      </header>
      <main class="flex-1 w-full max-w-[1400px] mx-auto px-4 lg:px-8 pt-6 pb-16 min-w-0">
        <div v-if="crmStore.failed.length" class="mb-4 flex flex-wrap items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900" role="status" data-testid="load-warning">
          <span class="flex-1 min-w-[200px]">{{ $t('Ba’zi ma’lumotlar yuklanmadi — server javob bermadi. Qolgan bo‘limlar ishlayapti.') }}</span>
          <BaseButton size="sm" variant="soft" :loading="retrying" @click="retryLoad">{{ $t('Qayta urinish') }}</BaseButton>
        </div>
        <div v-if="pageError" class="crm-card p-8 text-center max-w-lg mx-auto mt-6" role="alert" data-testid="page-error">
          <h2 class="font-bold text-lg mb-1">{{ $t('Sahifani ochib bo‘lmadi') }}</h2>
          <p class="text-sm text-muted mb-3">{{ $t('Kutilmagan xato yuz berdi. Sahifani qayta yuklang — muammo takrorlansa, Support’ga xabar bering.') }}</p>
          <p class="text-xs text-muted mb-5 break-all">{{ pageError }}</p>
          <BaseButton @click="reloadPage">{{ $t('Qayta yuklash') }}</BaseButton>
        </div>
        <RouterView v-else v-slot="{ Component, route: r }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="r.meta.viewKey || r.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.tip { @apply pointer-events-none absolute left-full ml-3 px-2.5 h-8 grid place-items-center rounded-lg bg-ink text-white text-xs font-semibold whitespace-nowrap opacity-0 -translate-x-1 transition-all z-50; }
.group:hover .tip, .group:focus-visible .tip { @apply opacity-100 translate-x-0; }
</style>