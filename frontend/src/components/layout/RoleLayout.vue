<script setup>
import { computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import AppHeader from './AppHeader.vue'
import BottomNav from './BottomNav.vue'
import SideNav from './SideNav.vue'
import AdCarousel from '@/components/ads/AdCarousel.vue'
import PageIntro from './PageIntro.vue'
import { ROLES } from '@/config/roles'
import { session } from '@/stores/session'
import { authApi } from '@/services'

const route = useRoute()
const role = computed(() => ROLES[route.meta.role])
async function loadMe() {
  if (!session.token) return
  try { session.user = await authApi.me() } catch { /* 401 bo‘lsa umumiy ishlovchi kirish sahifasiga yuboradi */ }
}
onMounted(loadMe)
watch(() => session.userId, loadMe)
</script>

<template>
  <div class="min-h-full bg-white">
    <SideNav />
    <div :class="['min-h-full flex flex-col transition-[padding] duration-300', session.sidebarCollapsed ? 'lg:pl-[76px]' : 'lg:pl-[248px]']">
      <AppHeader />
      <main class="flex-1 lg:bg-[#fbfcfb]">
        <!-- Reklama carousel: navbar ostida, faqat shu sahifaga biriktirilgan va hozir aktiv reklamalar -->
        <div v-if="route.meta.ads" class="max-w-2xl lg:max-w-6xl mx-auto px-4 lg:px-8 lg:pt-6">
          <!-- Desktop: chapda sahifa kirish bloki (filtr ustuni kengligida), o‘ngda carousel -->
          <div class="lg:grid lg:grid-cols-[280px_minmax(0,620px)] lg:gap-8 lg:items-stretch">
            <div class="hidden lg:block"><PageIntro vertical /></div>
            <div class="min-w-0"><AdCarousel :key="route.path" :placement="route.path" /></div>
          </div>
        </div>
        <RouterView v-slot="{ Component, route: r }">
          <Transition name="page" mode="out-in">
            <component :is="Component" :key="r.meta.viewKey || r.path" />
          </Transition>
        </RouterView>
      </main>
    </div>
    <BottomNav v-if="role" :items="role.nav" />
  </div>
</template>
