<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import AppLogo from '@/components/brand/AppLogo.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import { session, signIn, logout, toast } from '@/stores/session'
import { authApi } from '@/services'
import { isTelegram } from '@/services/telegram'
import { ROLES } from '@/config/roles'

const router = useRouter()
const maintenance = ref(false)
/**
 * Kirish nuqtasi: saqlangan token tekshiriladi (GET /users/me). Token yo‘q bo‘lsa va ilova Telegram ichida ochilgan bo‘lsa —
 * imzolangan initData bilan avtomatik kirishga urinib ko‘riladi; hisob topilmasa onboarding ochiladi.
 */
async function resolveStart() {
  // Texnik ishlar rejimi — tushunarli ekran (aks holda har bir so‘rov 503 bilan bo‘sh sahifa)
  try {
    const cfg = await authApi.publicConfig()
    if (cfg?.maintenance) { maintenance.value = true; return null }
  } catch { /* server javob bermasa quyidagi oqim xatoni ko‘rsatadi */ }

  // Telegram ichida: avval imzolangan initData bilan shu Telegram hisobiga kiramiz.
  // Bu bir qurilmada boshqa Telegram akkaunt ochilganda eski (begona) sessiya ochilib qolishining oldini oladi.
  if (isTelegram) {
    try {
      const { user, token } = await authApi.telegramLogin()
      signIn({ userId: user.id, role: user.role, token })
      session.user = user
      return ROLES[user.role].home
    } catch (e) {
      if (e.status === 403) { logout(); toast(e.message, 'error'); return '/welcome' }
      if (e.status === 0) return session.token && ROLES[session.role]?.home ? ROLES[session.role].home : '/welcome'
      // 404 — bu Telegram hisobi ro‘yxatdan o‘tmagan
    }
  }
  if (session.token) {
    try {
      const user = await authApi.me()
      // Saqlangan sessiya boshqa Telegram hisobiga bog‘langan — bu foydalanuvchiga ochilmaydi
      if (isTelegram && user.telegramLinked) { logout(); return '/welcome' }
      session.user = user
      session.role = user.role
      // Telefon bilan ro‘yxatdan o‘tgan hisob Telegram ichida ochildi — avtomatik bog‘laymiz (bildirishnomalar va keyingi avtokirish uchun)
      if (isTelegram && !user.telegramLinked) authApi.linkTelegram().then((u) => { session.user = u }).catch(() => {})
      return ROLES[user.role].home
    } catch (e) {
      if (e.status === 401 || e.status === 403) logout()
      else return ROLES[session.role]?.home || '/welcome' // tarmoq xatosi — keyinroq qayta urinadi
      if (e.status === 403) toast(e.message, 'error')
    }
  }
  return '/welcome'
}
const reload = () => window.location.reload()
onMounted(async () => {
  const [target] = await Promise.all([resolveStart(), new Promise((r) => setTimeout(r, 1100))])
  if (target) router.replace(target)
})
</script>

<template>
  <div class="min-h-[100dvh] flex flex-col items-center justify-center relative overflow-hidden bg-white px-8 text-center">
    <RoundIllu kind="laptop" :size="110" class="absolute -top-4 -right-6 sm:top-10 sm:right-16" />
    <RoundIllu kind="student" :size="96" class="absolute bottom-24 -left-5 sm:bottom-20 sm:left-16" :delay=".3" />
    <div class="relative scale-in"><AppLogo :size="88" :animated="false" /></div>
    <p class="relative mt-4 text-ink-2 text-[15px] leading-relaxed max-w-[280px] fade-later">{{ $t('Talabalar uchun ish, turar joy va bepul kurslar') }}</p>
    <div v-if="maintenance" class="relative mt-6 max-w-[300px] rounded-2xl bg-surface px-5 py-4" data-testid="maintenance">
      <b class="block">{{ $t('Texnik ishlar olib borilmoqda') }}</b>
      <span class="block mt-1 text-sm text-ink-2">{{ $t('Birozdan so‘ng qayta urinib ko‘ring.') }}</span>
      <button class="mt-3 h-10 px-5 rounded-xl bg-brand text-white font-semibold" @click="reload">{{ $t('Qayta urinish') }}</button>
    </div>
    <div v-else class="absolute bottom-[calc(56px+var(--safe-bottom))] w-36 h-1.5 rounded-full bg-brand-50 overflow-hidden" role="progressbar" :aria-label="$t('Yuklanmoqda')">
      <div class="h-full bg-brand rounded-full progress" />
    </div>
  </div>
</template>

<style scoped>
.scale-in { animation: si .7s cubic-bezier(.22,1,.36,1) both; }
.fade-late { animation: fl .6s ease .3s both; }
.fade-later { animation: fl .6s ease .5s both; }
.progress { animation: pr 1.3s cubic-bezier(.65,0,.35,1) forwards; }
@keyframes si { from { opacity: 0; transform: scale(.8); } to { opacity: 1; transform: none; } }
@keyframes fl { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: none; } }
@keyframes pr { from { width: 0 } to { width: 100% } }
</style>
