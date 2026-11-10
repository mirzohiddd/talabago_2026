<script setup>
/**
 * Kirish: telefon raqam + parol (website / brauzer).
 * Telegram Mini App ichida — imzolangan initData orqali bir bosishda kirish (server HMAC bilan tekshiradi).
 */
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Phone, Lock, ArrowRight, Send, Eye, EyeOff } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import { authApi } from '@/services'
import { isTelegram, haptic } from '@/services/telegram'
import { session, signIn, toast } from '@/stores/session'
import { ROLES } from '@/config/roles'
import { normalizePhone } from '@/utils/format'
import { phoneProblem, PHONE_MESSAGES } from '@shared/phone'
import PhoneInput from '@/components/ui/PhoneInput.vue'
import { t } from '@/i18n'

const router = useRouter()
const form = reactive({ phone: '', password: '' })
const show = ref(false)
const errors = ref({})
const loading = ref(false)
const tgLoading = ref(false)

function enter({ user, token }) {
  signIn({ userId: user.id, role: user.role, token })
  session.user = user
  if (isTelegram && !user.telegramLinked) authApi.linkTelegram().then((u) => { session.user = u }).catch(() => {})
  haptic.success()
  toast(t('Xush kelibsiz, {name}!', { name: user.firstName }))
  router.replace(ROLES[user.role].home)
}

async function submit() {
  errors.value = {}
  const phone = normalizePhone(form.phone)
  const problem = phoneProblem(form.phone)
  if (problem) errors.value.phone = t(PHONE_MESSAGES[problem])
  if (!form.password) errors.value.password = t('Majburiy maydon')
  if (Object.keys(errors.value).length) return
  loading.value = true
  try {
    enter(await authApi.login(phone, form.password))
  } catch (e) {
    form.password = ''
    haptic.error()
    if (e.status === 401) errors.value.password = t('Telefon raqam yoki parol noto‘g‘ri')
    else toast(e.message, 'error')
  } finally {
    loading.value = false
  }
}

async function telegram() {
  tgLoading.value = true
  try {
    enter(await authApi.telegramLogin())
  } catch (e) {
    if (e.status === 404) { toast(t('Bu Telegram hisobi hali ro‘yxatdan o‘tmagan'), 'error'); router.replace('/welcome') }
    else toast(e.message, 'error')
  } finally {
    tgLoading.value = false
  }
}
onMounted(() => { if (isTelegram) telegram() })
</script>

<template>
  <div class="relative min-h-[100dvh] bg-white lg:bg-[#f7faf8] grid place-items-center px-5 py-10 overflow-hidden">
    <RoundIllu kind="laptop" :size="120" class="absolute -top-6 -right-8 hidden sm:block" />
    <RoundIllu kind="keys" :size="92" class="absolute bottom-10 -left-6 hidden sm:block" :delay=".3" />
    <div class="relative w-full max-w-[400px] lg:bg-white lg:border lg:border-line lg:rounded-[28px] lg:p-9 lg:shadow-[0_24px_60px_-30px_rgba(6,95,70,.35)] animate-fade-up">
      <AppLogo :size="44" />
      <h1 class="mt-7 text-[28px] font-extrabold tracking-tight">{{ $t('Kirish') }}</h1>
      <p class="text-muted mt-1">{{ $t('Ro‘yxatdan o‘tgan telefon raqam va parolingizni kiriting.') }}</p>

      <BaseButton v-if="isTelegram" block size="lg" variant="soft" class="mt-6" :icon="Send" :loading="tgLoading" data-testid="tg-login" @click="telegram">{{ $t('Telegram orqali kirish') }}</BaseButton>

      <form class="mt-6 space-y-4" novalidate @submit.prevent="submit">
        <PhoneInput v-model="form.phone" :label="$t('Telefon')" :error="errors.phone" :validate-on-blur="false" data-testid="login-phone" />
        <div class="relative">
          <BaseInput v-model="form.password" :type="show ? 'text' : 'password'" :label="$t('Parol')" :icon="Lock" autocomplete="current-password" :error="errors.password" data-testid="login-password" />
          <button type="button" class="absolute right-3 top-[34px] size-8 grid place-items-center text-muted hover:text-ink" :aria-label="show ? $t('Parolni yashirish') : $t('Parolni ko‘rsatish')" @click="show = !show">
            <component :is="show ? EyeOff : Eye" class="size-[18px]" />
          </button>
        </div>
        <BaseButton type="submit" block size="lg" :loading="loading" :icon-right="ArrowRight" data-testid="login-submit">{{ $t('Kirish') }}</BaseButton>
      </form>
      <p class="mt-6 text-center text-sm text-muted">
        {{ $t('Hisobingiz yo‘qmi?') }} <RouterLink to="/welcome" class="font-semibold text-brand-600 hover:underline">{{ $t('Ro‘yxatdan o‘tish') }}</RouterLink>
      </p>
      <p class="mt-3 text-center text-xs text-muted">{{ $t('Parolni unutdingizmi? Texnik yordamga Telegram orqali yozing.') }}</p>
    </div>
  </div>
</template>