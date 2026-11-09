<script setup>
/** Desktop sidebar: yig‘iladi/ochiladi (holat saqlanadi), yig‘ilganda faqat ikonkalar + tooltip */
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { PanelLeftClose, PanelLeftOpen, LifeBuoy } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import Avatar from '@/components/ui/Avatar.vue'
import { session } from '@/stores/session'
import { ROLES } from '@/config/roles'
import { fullName } from '@/services'

const route = useRoute()
const role = computed(() => ROLES[session.role])
const collapsed = computed(() => session.sidebarCollapsed)
const active = (it) => route.path === it.to || route.path.startsWith(it.to + '/')
</script>

<template>
  <aside
    :class="['hidden lg:flex fixed inset-y-0 left-0 z-40 flex-col bg-white border-r border-line transition-[width] duration-300 ease-[cubic-bezier(.22,1,.36,1)]', collapsed ? 'w-[76px]' : 'w-[248px]']"
    :aria-label="$t('Asosiy menyu')" data-testid="sidenav"
  >
    <div :class="['h-[64px] flex items-center border-b border-line', collapsed ? 'justify-center' : 'px-5']">
      <RouterLink :to="role?.home || '/'"><AppLogo :size="collapsed ? 42 : 40" :variant="collapsed ? 'mark' : 'full'" /></RouterLink>
    </div>
    <p v-if="!collapsed" class="px-5 pt-5 pb-2 text-[11px] font-bold uppercase tracking-wider text-muted">{{ $t(role?.title) }}</p>
    <nav :class="['flex-1 overflow-y-auto px-3 space-y-1', collapsed && 'pt-4']">
      <RouterLink
        v-for="it in role?.nav" :key="it.to" :to="it.to"
        :class="['group relative flex items-center gap-3 h-11 rounded-xl text-[14.5px] font-semibold transition-colors', collapsed ? 'justify-center' : 'px-3', active(it) ? 'bg-brand-50 text-brand-700' : 'text-ink-2 hover:bg-surface hover:text-ink']"
        :aria-current="active(it) ? 'page' : undefined" :title="collapsed ? $t(it.label) : undefined"
      >
        <span v-if="active(it)" class="absolute left-0 top-2.5 bottom-2.5 w-[3px] rounded-r-full bg-brand" />
        <component :is="it.icon" class="size-[20px] shrink-0 transition-transform group-hover:scale-110" />
        <span v-if="!collapsed" class="truncate">{{ $t(it.label) }}</span>
        <span v-else class="tip">{{ $t(it.label) }}</span>
      </RouterLink>
    </nav>
    <div class="p-3 border-t border-line space-y-1">
      <RouterLink :to="`/${session.role}/support`" :class="['group relative flex items-center gap-3 h-11 rounded-xl text-[14px] font-semibold text-ink-2 hover:bg-surface', collapsed ? 'justify-center' : 'px-3', route.path.includes('/support') && 'bg-brand-50 text-brand-700']">
        <LifeBuoy class="size-[20px] shrink-0" /><span v-if="!collapsed">{{ $t('Texnik yordam') }}</span><span v-else class="tip">{{ $t('Texnik yordam') }}</span>
      </RouterLink>
      <div :class="['flex items-center gap-3 p-2 rounded-xl', collapsed && 'justify-center']">
        <Avatar :name="fullName(session.user)" :src="session.user?.logo" size="sm" />
        <div v-if="!collapsed" class="min-w-0"><p class="text-sm font-semibold truncate">{{ fullName(session.user) }}</p><p class="text-xs text-muted truncate">{{ session.user?.company || session.user?.telegram || session.user?.phone }}</p></div>
      </div>
      <button
        :class="['w-full flex items-center gap-3 h-10 rounded-xl text-[13px] font-semibold text-muted hover:bg-surface hover:text-ink transition', collapsed ? 'justify-center' : 'px-3']"
        :aria-label="collapsed ? $t('Menyuni ochish') : $t('Menyuni yig‘ish')" :aria-expanded="!collapsed" data-testid="sidebar-toggle"
        @click="session.sidebarCollapsed = !collapsed"
      >
        <component :is="collapsed ? PanelLeftOpen : PanelLeftClose" class="size-[19px]" /><span v-if="!collapsed">{{ $t('Menyuni yig‘ish') }}</span>
      </button>
    </div>
  </aside>
</template>

<style scoped>
@reference "../../style.css";
.tip { @apply pointer-events-none absolute left-full ml-3 px-2.5 h-8 grid place-items-center rounded-lg bg-ink text-white text-xs font-semibold whitespace-nowrap opacity-0 -translate-x-1 transition-all z-50; }
.group:hover .tip, .group:focus-visible .tip { @apply opacity-100 translate-x-0; }
</style>
