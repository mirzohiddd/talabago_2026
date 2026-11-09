<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { UserPen, Settings, LogOut, Phone, MapPin, LifeBuoy, Building } from 'lucide-vue-next'
import PopoverPanel from './PopoverPanel.vue'
import Avatar from '@/components/ui/Avatar.vue'
import { session, logout } from '@/stores/session'
import { ROLES } from '@/config/roles'
import { fullName } from '@/services'

const open = defineModel({ type: Boolean })
const router = useRouter()
const role = computed(() => ROLES[session.role])
const u = computed(() => session.user)

function go(path) { open.value = false; router.push(path) }
function doLogout() { open.value = false; logout(); router.replace('/welcome') }
</script>

<template>
  <PopoverPanel v-model="open" :title="null">
    <div class="p-4 flex items-center gap-3 border-b border-line">
      <Avatar :name="fullName(u)" :src="u?.logo" size="lg" />
      <div class="min-w-0">
        <p class="font-bold text-[17px] truncate">{{ fullName(u) }}</p>
        <span class="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 bg-brand-50 rounded-full h-6 px-2.5 mt-1">
          <component :is="role?.icon" class="size-3.5" />{{ $t(role?.title) }}
        </span>
      </div>
    </div>
    <div class="px-4 py-3 space-y-1.5 text-sm text-ink-2 border-b border-line">
      <p v-if="u?.company" class="flex items-center gap-2"><Building class="size-4 text-muted" />{{ u.company }}</p>
      <p class="flex items-center gap-2"><Phone class="size-4 text-muted" />{{ u?.phone || '—' }}</p>
      <p class="flex items-center gap-2"><MapPin class="size-4 text-muted" />{{ [$t(u?.city || 'Toshkent'), u?.district && $tc(u.district)].filter(Boolean).join(', ') }}</p>
    </div>
    <nav class="p-2">
      <button class="menu-item" @click="go(`/${session.role}/settings?edit=profile`)"><UserPen class="size-[18px]" />{{ $t('Profilni tahrirlash') }}</button>
      <button class="menu-item" @click="go(`/${session.role}/settings`)"><Settings class="size-[18px]" />{{ $t('Sozlamalar') }}</button>
      <button class="menu-item" @click="go(`/${session.role}/support`)"><LifeBuoy class="size-[18px]" />{{ $t('Texnik yordam') }}</button>
      <button class="menu-item text-danger! hover:bg-danger/5!" @click="doLogout"><LogOut class="size-[18px]" />{{ $t('Chiqish') }}</button>
    </nav>
  </PopoverPanel>
</template>

<style scoped>
@reference "../../style.css";
.menu-item { @apply w-full flex items-center gap-3 h-11 px-3 rounded-xl text-[15px] font-medium text-ink hover:bg-surface transition-colors; }
</style>
