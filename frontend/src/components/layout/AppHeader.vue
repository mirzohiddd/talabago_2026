<script setup>
/**
 * Yuqori panel. Mobil: logo + ikonkalar (qidiruv ochiladigan). Desktop: sahifa nomi + doimiy qidiruv maydoni.
 * Ikonkalar: qidiruv, texnik yordam (Support), bildirishnomalar, profil.
 */
import { ref, nextTick, watch, computed, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Search, Bell, X, LifeBuoy } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import Avatar from '@/components/ui/Avatar.vue'
import NotificationsPopover from './NotificationsPopover.vue'
import ProfilePopover from './ProfilePopover.vue'
import { search, session } from '@/stores/session'
import { supportApi, fullName } from '@/services'
import { haptic } from '@/services/telegram'

const route = useRoute()
const router = useRouter()
const notifOpen = ref(false)
const profileOpen = ref(false)
const unread = ref(0)
const supportUnread = ref(0)
const input = ref(null)
const hasSearch = computed(() => !!route.meta.search)

async function openSearch() {
  haptic.tap()
  search.open = true
  await nextTick()
  input.value?.focus()
}
function closeSearch() { search.open = false; search.query = '' }
// Support javoblari belgisi: sahifa almashganda ko‘pi bilan 30 soniyada bir marta (har o‘tishda so‘rov yuborilmaydi) + har 60 s
let supportAt = 0
async function refreshSupport(force = false) {
  if (!session.token || (!force && Date.now() - supportAt < 30000)) return
  supportAt = Date.now()
  try { supportUnread.value = (await supportApi.list()).filter((t) => t.unreadByUser).length } catch { supportAt = 0 }
}
const timer = setInterval(() => { if (document.visibilityState === 'visible') refreshSupport(true) }, 60000)
onBeforeUnmount(() => clearInterval(timer))

watch(() => route.path, () => { search.query = ''; search.open = false; notifOpen.value = false; profileOpen.value = false; refreshSupport() }, { immediate: true })
</script>

<template>
  <header class="sticky top-0 z-30 bg-white/90 backdrop-blur-xl safe-top lg:border-b lg:border-line">
    <div class="h-[64px] px-4 lg:px-8 flex items-center gap-1 relative max-w-2xl lg:max-w-none mx-auto">
      <!-- Mobil -->
      <Transition name="fade" mode="out-in">
        <div v-if="!search.open" key="bar" class="flex items-center gap-1 w-full">
          <RouterLink :to="route.meta.home || '/'" class="mr-auto lg:hidden" :aria-label="$t('Bosh sahifa')"><AppLogo :size="40" /></RouterLink>
          <h1 v-if="!route.meta.illu" class="hidden lg:block mr-6 text-[20px] font-extrabold tracking-tight truncate">{{ $t(route.meta.title || '') }}</h1>
          <!-- Desktop: doimiy qidiruv -->
          <label v-if="hasSearch" class="hidden lg:flex flex-1 max-w-md mr-auto items-center gap-2 h-11 px-3.5 rounded-xl bg-surface border border-transparent focus-within:border-brand focus-within:bg-white focus-within:ring-4 focus-within:ring-brand/10 transition-all">
            <Search class="size-[18px] text-muted" />
            <input v-model="search.query" type="search" :placeholder="$t(route.meta.search)" class="flex-1 bg-transparent outline-none text-[15px] placeholder:text-muted" data-testid="desktop-search" />
            <button v-if="search.query" class="text-muted" :aria-label="$t('Tozalash')" @click="search.query = ''"><X class="size-4" /></button>
          </label>
          <span v-else class="hidden lg:block mr-auto" />
          <button v-if="hasSearch" class="icon-btn lg:hidden" :aria-label="$t('Qidiruv')" @click="openSearch"><Search class="size-[22px]" /></button>
          <button class="icon-btn relative" :aria-label="$t('Texnik yordam')" :title="$t('Texnik yordam')" data-testid="help-btn" @click="router.push(`/${session.role}/support`)">
            <LifeBuoy class="size-[22px]" />
            <span v-if="supportUnread" class="absolute top-2 right-2 size-2.5 rounded-full bg-brand ring-2 ring-white" />
          </button>
          <button class="icon-btn relative" :aria-label="$t('Bildirishnomalar')" :aria-expanded="notifOpen" data-testid="bell" @click="haptic.tap(); notifOpen = !notifOpen; profileOpen = false">
            <Bell class="size-[22px]" :class="unread && 'bell-ring'" />
            <span v-if="unread" class="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] px-1 grid place-items-center rounded-full bg-brand text-white text-[10px] font-bold ring-2 ring-white animate-pop">{{ unread }}</span>
          </button>
          <button class="ml-1 rounded-full ring-2 ring-transparent hover:ring-brand-100 transition" :aria-label="$t('Profil')" :aria-expanded="profileOpen" data-testid="profile-btn" @click="haptic.tap(); profileOpen = !profileOpen; notifOpen = false">
            <Avatar :name="fullName(session.user)" :src="session.user?.logo" size="sm" class="size-9!" />
          </button>
        </div>
        <div v-else key="search" class="flex items-center gap-2 w-full lg:hidden">
          <div class="flex-1 flex items-center gap-2 h-11 px-3.5 rounded-xl bg-surface border border-transparent focus-within:border-brand focus-within:bg-white focus-within:ring-4 focus-within:ring-brand/10 transition-all">
            <Search class="size-[18px] text-muted" />
            <input ref="input" v-model="search.query" type="search" enterkeyhint="search" :placeholder="$t(route.meta.search || 'Qidirish...')" class="flex-1 bg-transparent outline-none text-[15px] placeholder:text-muted" />
            <button v-if="search.query" class="text-muted" :aria-label="$t('Tozalash')" @click="search.query = ''"><X class="size-4" /></button>
          </div>
          <button class="text-sm font-semibold text-brand-600 px-1" @click="closeSearch">{{ $t('Bekor') }}</button>
        </div>
      </Transition>
    </div>
    <NotificationsPopover v-model="notifOpen" @count="unread = $event" />
    <ProfilePopover v-model="profileOpen" />
  </header>
</template>

<style scoped>
@reference "../../style.css";
.icon-btn { @apply size-11 grid place-items-center rounded-full text-ink hover:bg-brand-50 hover:text-brand-600 transition-all active:scale-90; }
.bell-ring { animation: ring 2.8s ease-in-out infinite; transform-origin: 50% 10%; }
@keyframes ring { 0%, 80%, 100% { transform: rotate(0) } 84% { transform: rotate(14deg) } 88% { transform: rotate(-12deg) } 92% { transform: rotate(8deg) } 96% { transform: rotate(-4deg) } }
</style>