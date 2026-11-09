<script setup>
import { t } from '@/i18n'
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { User, Lock, Eye, EyeOff, ArrowRight, ShieldCheck, AlertTriangle, Terminal, Clock } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import { login, AuthError } from '@/services/auth'

const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const show = ref(false)
const caps = ref(false)
const loading = ref(false)
const error = ref('')
const lockedUntil = ref(0)
const now = ref(Date.now())
const expired = route.query.expired === '1'
let timer = null
onMounted(() => { timer = setInterval(() => (now.value = Date.now()), 1000) })
onBeforeUnmount(() => clearInterval(timer))

const lockLeft = computed(() => Math.max(0, Math.ceil((lockedUntil.value - now.value) / 1000)))
const lockText = computed(() => `${Math.floor(lockLeft.value / 60)}:${String(lockLeft.value % 60).padStart(2, '0')}`)
const canSubmit = computed(() => username.value.trim() && password.value && !lockLeft.value)

async function submit() {
  if (!canSubmit.value) return
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
    password.value = ''
    const to = typeof route.query.redirect === 'string' && route.query.redirect.startsWith('/') && !route.query.redirect.startsWith('//') ? route.query.redirect : '/dashboard'
    router.replace(to)
  } catch (e) {
    password.value = ''
    if (e instanceof AuthError && e.code === 'locked') { lockedUntil.value = e.until; error.value = '' }
    else if (e instanceof AuthError && e.code === 'invalid') error.value = e.left != null && e.left <= 2 ? `${t(e.message)}. ${t('Yana {n} ta urinish qoldi.', { n: e.left })}` : t(e.message)
    else error.value = t(e.message || 'Kirishda xatolik')
  } finally {
    loading.value = false
  }
}
const onKey = (e) => { caps.value = e.getModifierState?.('CapsLock') ?? false }
</script>

<template>
  <div class="min-h-full grid lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)] bg-white">
    <!-- Brend paneli -->
    <section class="relative hidden lg:flex flex-col justify-between overflow-hidden bg-brand text-white p-12">
      <svg class="absolute -left-24 -bottom-40 w-[520px] opacity-20" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="#fff" stroke-width="9" /></svg>
      <svg class="absolute -right-16 -top-16 w-72 opacity-15" viewBox="0 0 100 100"><circle cx="50" cy="50" r="40" fill="none" stroke="#fff" stroke-width="12" /></svg>
      <div class="relative inline-flex items-center gap-3 bg-white rounded-2xl px-4 py-3 w-fit shadow-lg animate-fade-up"><AppLogo :size="44" /></div>
      <div class="relative max-w-md animate-fade-up [animation-delay:.1s]">
        <h1 class="text-[40px] font-extrabold leading-[1.08] tracking-tight">{{ $t('TalabaGo Support') }}</h1>
        <p class="text-white/85 text-lg mt-3">{{ $t('Foydalanuvchilar, e’lonlar, reklamalar va shikoyatlarni bir joydan boshqaring.') }}</p>
      </div>
      <div class="relative self-end flex items-end gap-4"><RoundIllu kind="stats" :size="120" :delay=".3" /><RoundIllu kind="office-worker" :size="220" /></div>
    </section>

    <!-- Forma -->
    <section class="flex items-center justify-center p-6 sm:p-10">
      <div class="w-full max-w-[400px] animate-fade-up">
        <div class="lg:hidden mb-8"><AppLogo :size="44" /></div>
        <p class="inline-flex items-center gap-1.5 h-6 px-2.5 rounded-full bg-ink text-white text-[11px] font-bold tracking-wide">TALABAGO SUPPORT</p>
        <h2 class="text-[28px] font-extrabold tracking-tight mt-3">{{ $t('Tizimga kirish') }}</h2>
        <p class="text-muted mt-1">{{ $t('Faqat vakolatli administratorlar uchun.') }}</p>

        <p v-if="expired" class="mt-5 flex gap-2 text-[13px] rounded-xl px-3 py-2.5 bg-[#2f6bff]/8 text-[#2f6bff]"><Clock class="size-4 shrink-0 mt-px" />{{ $t('Sessiya muddati tugadi. Qaytadan kiring.') }}</p>


        <form class="mt-7 space-y-4" novalidate @submit.prevent="submit">
          <label class="block">
            <span class="label">{{ $t('Username') }}</span>
            <div class="field"><User class="size-[18px] text-muted" />
              <input v-model="username" name="username" autocomplete="username" autocapitalize="off" spellcheck="false" placeholder="login" class="flex-1 min-w-0 bg-transparent outline-none text-[15px]" :disabled="!!lockLeft" />
            </div>
          </label>
          <label class="block">
            <span class="label">{{ $t('Parol') }}</span>
            <div class="field"><Lock class="size-[18px] text-muted" />
              <input v-model="password" name="password" :type="show ? 'text' : 'password'" autocomplete="current-password" placeholder="••••••••••" class="flex-1 min-w-0 bg-transparent outline-none text-[15px]" :disabled="!!lockLeft" @keyup="onKey" @keydown="onKey" />
              <button type="button" class="text-muted hover:text-ink" :aria-label="show ? $t('Parolni yashirish') : $t('Parolni ko‘rsatish')" @click="show = !show"><component :is="show ? EyeOff : Eye" class="size-[18px]" /></button>
            </div>
            <span v-if="caps" class="block mt-1 text-xs text-[#a15c00]">{{ $t('Caps Lock yoqilgan') }}</span>
          </label>

          <Transition name="fade">
            <p v-if="lockLeft" class="flex gap-2 text-[13px] rounded-xl px-3 py-2.5 bg-danger/10 text-danger" data-testid="locked"><AlertTriangle class="size-4 shrink-0 mt-px" />Juda ko‘p noto‘g‘ri urinish. {{ lockText }} dan keyin qayta urinib ko‘ring.</p>
            <p v-else-if="error" class="flex gap-2 text-[13px] rounded-xl px-3 py-2.5 bg-danger/10 text-danger animate-[wiggle_.4s]" role="alert" data-testid="login-error"><AlertTriangle class="size-4 shrink-0 mt-px" />{{ error }}</p>
          </Transition>

          <BaseButton type="submit" block size="lg" :loading="loading" :disabled="!canSubmit" :icon-right="ArrowRight">{{ $t('Kirish') }}</BaseButton>
        </form>

        <p class="mt-8 flex gap-2 text-[12px] text-muted leading-relaxed">
          <ShieldCheck class="size-4 shrink-0 mt-px" />
          <span>{{ $t('Kirish server tomonida tekshiriladi. Sessiya xavfsiz cookie’da saqlanadi.') }}</span>
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
@reference "../../style.css";
.field { @apply flex items-center gap-2.5 h-12 px-3.5 rounded-xl border border-line bg-white transition-all focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10; }
code { @apply bg-white/70 rounded px-1 font-semibold; }
</style>
