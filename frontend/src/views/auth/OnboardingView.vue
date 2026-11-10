<script setup>
/**
 * 6 bosqichli birinchi kirish:
 *  1 Til → 2 Talabalar uchun → 3 Uy egalari uchun → 4 Ish beruvchilar uchun → 5 Rol tanlash → 6 Ro‘yxatdan o‘tish
 * Tanlangan til va rol saqlanadi (sahifa yangilansa ham davom etadi). Mobilda 1–4 bosqichlar swipe bilan almashadi.
 * Desktop: chapda bosqichlar ro‘yxati, o‘ngda forma (website uchun alohida layout).
 */
import { ref, reactive, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, Check, ShieldCheck, Send } from 'lucide-vue-next'
import AppLogo from '@/components/brand/AppLogo.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import ProfileFields from '@/components/forms/ProfileFields.vue'
import { LOCALES, i18n, setLocale, t } from '@/i18n'
import { ROLES } from '@/config/roles'
import { session, signIn, toast } from '@/stores/session'
import { authApi } from '@/services'
import { getTelegramUser, isTelegram, haptic } from '@/services/telegram'
import { validate, registerSchema, rules, serverFieldErrors } from '@/utils/validate'
import { normalizePhone } from '@/utils/format'

const router = useRouter()
const TOTAL = 6
const step = ref(Math.min(Math.max(session.onboarding?.step || 1, 1), TOTAL))
const dir = ref(1)
const role = ref(session.onboarding?.role || null)
watch([step, role], () => { session.onboarding = { step: step.value, role: role.value } })

const INTRO = {
  2: { title: 'Talabamisiz?', text: 'TalabaGo orqali o‘qishingizga mos ish toping, qulay turar joy qidiring va rus hamda ingliz tillarini bepul o‘rganing!', main: 'student', side: ['books', 'laptop'] },
  3: { title: 'Uyingizni ijaraga bermoqchimisiz?', text: 'TalabaGo’da uy yoki xonangizni e’lon qiling va turar joy izlayotgan talabalarni toping!', main: 'house', side: ['keys', 'building'] },
  4: { title: 'Sizga xodim kerakmi?', text: 'TalabaGo orqali ish e’loni joylashtiring va o‘zingizga mos yosh xodimlarni toping!', main: 'worker', side: ['briefcase', 'checklist'] },
}
const STEPS = ['Til', 'Talabalar', 'Uy egalari', 'Ish beruvchilar', 'Rol', 'Ro‘yxatdan o‘tish']

function go(n) {
  if (n < 1 || n > TOTAL) return
  if (n === 6 && !role.value) return
  dir.value = n > step.value ? 1 : -1
  step.value = n
  haptic.select()
}
const next = () => go(step.value + 1)
const back = () => go(step.value - 1)
const canNext = computed(() => (step.value === 5 ? !!role.value : true))

// ---- Swipe (1–4 bosqich) ----
let sx = null, sy = null
function onTouchStart(e) { sx = e.touches[0].clientX; sy = e.touches[0].clientY }
function onTouchEnd(e) {
  if (sx == null || step.value > 4) return
  const dx = e.changedTouches[0].clientX - sx
  const dy = e.changedTouches[0].clientY - sy
  if (Math.abs(dx) > 60 && Math.abs(dx) > Math.abs(dy) * 1.4) dx < 0 ? next() : back()
  sx = null
}
function onKey(e) {
  if (step.value > 4 || ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName)) return
  if (e.key === 'ArrowRight') next()
  if (e.key === 'ArrowLeft') back()
}

// ---- 6-bosqich: ro‘yxatdan o‘tish ----
const tgUser = getTelegramUser()
const form = reactive({
  firstName: tgUser?.first_name || '', lastName: tgUser?.last_name || '', phone: '', telegram: tgUser?.username ? `@${tgUser.username}` : '',
  birthDate: '', university: '', faculty: '', shift: '', course: '', city: 'Toshkent', district: '', skills: [],
  company: '', industry: '', address: '',
})
const pw = reactive({ password: '', confirm: '' })
const errors = ref({})
const loading = ref(false)
async function submit() {
  errors.value = validate(form, registerSchema(role.value))
  if (!isTelegram) {
    const pe = rules.password(pw.password)
    if (pe) errors.value.password = pe
    else if (pw.password !== pw.confirm) errors.value.confirm = t('Parollar mos emas')
  }
  if (Object.keys(errors.value).length) {
    // birinchi xato maydoniga o‘tish (mobil ekranda pastda qolib ketmasin)
    requestAnimationFrame(() => document.querySelector('[aria-invalid="true"]')?.scrollIntoView({ block: 'center', behavior: 'smooth' }))
  }
  if (Object.keys(errors.value).length) { haptic.error(); return }
  loading.value = true
  try {
    const payload = { ...form, phone: normalizePhone(form.phone), telegram: form.telegram ? '@' + form.telegram.replace(/^@/, '') : '', language: i18n.state.locale }
    if (role.value !== 'student') ['birthDate', 'university', 'faculty', 'shift', 'course', 'skills'].forEach((k) => delete payload[k])
    if (role.value !== 'employer') ['company', 'industry', 'address'].forEach((k) => delete payload[k])
    if (!isTelegram) payload.password = pw.password
    const { user, token } = await authApi.register(role.value, payload)
    signIn({ userId: user.id, role: role.value, token })
    session.user = user
    haptic.success()
    toast(t('Xush kelibsiz, {name}!', { name: user.firstName }))
    router.replace(ROLES[role.value].home)
  } catch (e) {
    if (e.status === 409 && /telefon/i.test(e.message)) errors.value = { ...errors.value, phone: t('Bu telefon raqam bilan hisob mavjud. “Kirish” orqali kiring.') }
    if (e.status === 422) errors.value = { ...errors.value, ...serverFieldErrors(e) }
    haptic.error()
    toast(e.message || t('Xatolik yuz berdi'), 'error')
  } finally {
    loading.value = false
  }
}

onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="relative min-h-[100dvh] bg-white lg:bg-[#f7faf8] lg:grid lg:grid-cols-[minmax(320px,420px)_1fr] overflow-hidden" @touchstart.passive="onTouchStart" @touchend="onTouchEnd">
    <!-- ===== Desktop: bosqichlar paneli ===== -->
    <aside class="hidden lg:flex flex-col bg-white border-r border-line p-10 relative overflow-hidden">
      <AppLogo :size="44" />
      <p class="mt-3 text-muted">{{ $t('Talabalar uchun ish, turar joy va bepul kurslar') }}</p>
      <ol class="mt-10 space-y-1" data-testid="steps-list">
        <li v-for="(s, i) in STEPS" :key="s">
          <button
            :class="['w-full flex items-center gap-3 h-12 px-3 rounded-xl text-left transition', step === i + 1 ? 'bg-brand-50' : 'hover:bg-surface', (i + 1 > step && !(i + 1 === 6 && role)) && 'opacity-60']"
            :disabled="i + 1 === 6 && !role" @click="go(i + 1)"
          >
            <span :class="['size-7 rounded-full grid place-items-center text-xs font-bold', i + 1 < step ? 'bg-brand text-white' : step === i + 1 ? 'bg-ink text-white' : 'bg-surface text-muted']">
              <Check v-if="i + 1 < step" class="size-4" /><template v-else>{{ i + 1 }}</template>
            </span>
            <span :class="['font-semibold text-[15px]', step === i + 1 ? 'text-ink' : 'text-ink-2']">{{ $t(s) }}</span>
          </button>
        </li>
      </ol>
      <div class="mt-auto flex items-end gap-3">
        <RoundIllu kind="laptop" :size="96" />
        <RoundIllu kind="books" :size="70" :delay=".3" />
        <RoundIllu kind="plant" :size="58" :delay=".6" />
      </div>
    </aside>

    <!-- ===== Kontent ===== -->
    <section class="relative min-h-[100dvh] flex flex-col lg:items-center lg:justify-center lg:p-10">
      <!-- Burchak illustratsiyalari (mobil: kichik, kontentni to‘smaydi) -->
      <RoundIllu v-if="step <= 4" kind="pen" class="absolute top-16 -right-5 opacity-90 lg:hidden pointer-events-none" :size="68" />
      <RoundIllu v-if="step <= 4" kind="plant" class="absolute bottom-28 -left-6 opacity-80 lg:hidden pointer-events-none" :size="72" :delay=".4" />
      <RoundIllu kind="desk" class="hidden lg:block absolute top-10 right-12" :size="110" />
      <RoundIllu kind="key" class="hidden lg:block absolute bottom-12 right-24" :size="78" :delay=".5" />

      <div class="relative w-full max-w-md lg:max-w-xl mx-auto flex-1 lg:flex-none flex flex-col px-6 pt-[calc(16px+var(--safe-top))] pb-[calc(24px+var(--safe-bottom))] lg:p-10 lg:bg-white lg:rounded-[28px] lg:border lg:border-line lg:shadow-[var(--shadow-card)]">
        <!-- Yuqori qator: orqaga + progress -->
        <div class="flex items-center gap-3 h-11">
          <button v-if="step > 1" class="size-10 -ml-2 grid place-items-center rounded-full hover:bg-surface" :aria-label="$t('Orqaga')" data-testid="ob-back" @click="back"><ArrowLeft class="size-5" /></button>
          <AppLogo v-else :size="34" class="lg:hidden" />
          <div class="flex-1 flex items-center gap-1.5" role="progressbar" :aria-valuenow="step" aria-valuemin="1" :aria-valuemax="TOTAL" :aria-label="$t('Bosqich')">
            <span v-for="i in TOTAL" :key="i" :class="['h-1.5 rounded-full transition-all duration-500', i <= step ? 'bg-brand' : 'bg-line', i === step ? 'flex-[2]' : 'flex-1']" />
          </div>
          <span class="text-[13px] font-bold tabular-nums text-ink-2" data-testid="ob-progress">{{ step }}/{{ TOTAL }}</span>
        </div>

        <Transition :name="dir > 0 ? 'slide-l' : 'slide-r'" mode="out-in">
          <!-- 1. Til -->
          <div v-if="step === 1" key="s1" class="flex-1 flex flex-col pt-8">
            <RoundIllu kind="chat" :size="104" class="mx-auto lg:mx-0" />
            <h1 class="mt-6 text-[28px] font-extrabold tracking-tight leading-tight">{{ $t('Tilni tanlang') }}</h1>
            <p class="text-muted mt-1">{{ $t('Ilova shu tilda ko‘rsatiladi. Keyin Sozlamalarda o‘zgartirish mumkin.') }}</p>
            <div class="mt-6 grid gap-2.5" role="radiogroup" :aria-label="$t('Til')">
              <button
                v-for="l in LOCALES" :key="l.value" role="radio" :aria-checked="i18n.state.locale === l.value"
                :class="['flex items-center gap-3.5 h-[60px] px-4 rounded-2xl border-[1.5px] text-left transition-all active:scale-[.99]', i18n.state.locale === l.value ? 'border-brand bg-brand-50/70' : 'border-line hover:border-brand-200']"
                :data-testid="`lang-${l.value}`" @click="setLocale(l.value)"
              >
                <span class="text-2xl" aria-hidden="true">{{ l.flag }}</span>
                <span class="flex-1"><span class="block font-bold">{{ l.label }}</span><span class="block text-xs text-muted">{{ l.sub }}</span></span>
                <span :class="['size-6 rounded-full grid place-items-center transition', i18n.state.locale === l.value ? 'bg-brand text-white' : 'border-2 border-line']"><Check v-if="i18n.state.locale === l.value" class="size-4" /></span>
              </button>
            </div>
          </div>

          <!-- 2–4. Rollar haqida -->
          <div v-else-if="step <= 4" :key="`s${step}`" class="flex-1 flex flex-col items-center text-center pt-6 lg:pt-4">
            <div class="relative w-full flex justify-center py-4">
              <RoundIllu :kind="INTRO[step].main" :size="190" />
              <RoundIllu :kind="INTRO[step].side[0]" :size="70" class="absolute left-2 bottom-2 sm:left-8" :delay=".25" />
              <RoundIllu :kind="INTRO[step].side[1]" :size="58" class="absolute right-4 top-0 sm:right-10" :delay=".45" />
            </div>
            <h1 class="mt-6 text-[28px] font-extrabold tracking-tight leading-tight" data-testid="ob-title">{{ $t(INTRO[step].title) }}</h1>
            <p class="mt-3 text-ink-2 text-[16px] leading-relaxed max-w-sm">{{ $t(INTRO[step].text) }}</p>
            <p class="mt-auto pt-6 text-xs text-muted lg:hidden">{{ $t('Surib o‘ting') }} →</p>
          </div>

          <!-- 5. Rol tanlash -->
          <div v-else-if="step === 5" key="s5" class="flex-1 flex flex-col pt-8">
            <h1 class="text-[28px] font-extrabold tracking-tight leading-tight">{{ $t('Kim sifatida davom etasiz?') }}</h1>
            <p class="text-muted mt-1">{{ $t('Rolga qarab kabinet va imkoniyatlar ochiladi.') }}</p>
            <div class="mt-6 grid gap-3" role="radiogroup" :aria-label="$t('Rol')">
              <button
                v-for="r in ROLES" :key="r.key" role="radio" :aria-checked="role === r.key"
                :class="['relative flex items-center gap-4 p-4 rounded-[22px] border-[1.5px] text-left transition-all duration-300 active:scale-[.99]', role === r.key ? 'border-brand bg-brand-50/70 shadow-[0_10px_24px_-14px_rgba(5,150,105,.6)]' : 'border-line hover:border-brand-200 hover:bg-brand-25']"
                :data-testid="`role-${r.key}`" @click="role = r.key; haptic.select()"
              >
                <RoundIllu :kind="r.illu" :size="68" :float="false" />
                <span class="flex-1 min-w-0">
                  <span class="block font-bold text-[17px]">{{ $t(r.cta) }}</span>
                  <span class="block text-[13px] text-muted mt-0.5">{{ $t(r.desc) }}</span>
                </span>
                <span :class="['size-7 rounded-full grid place-items-center shrink-0 transition', role === r.key ? 'bg-brand text-white scale-100' : 'border-2 border-line scale-90']"><Check v-if="role === r.key" class="size-4" /></span>
              </button>
            </div>
          </div>

          <!-- 6. Ro‘yxatdan o‘tish -->
          <form v-else key="s6" class="flex-1 flex flex-col pt-6" novalidate @submit.prevent="submit">
            <div class="flex items-center gap-3">
              <RoundIllu :kind="ROLES[role]?.illu" :size="56" :float="false" />
              <div>
                <h1 class="text-[24px] font-extrabold tracking-tight leading-tight">{{ $t('Ro‘yxatdan o‘tish') }}</h1>
                <p class="text-sm text-muted">{{ $t(ROLES[role]?.title) }} · <button type="button" class="text-brand-600 font-semibold hover:underline" @click="go(5)">{{ $t('o‘zgartirish') }}</button></p>
              </div>
            </div>
            <p v-if="tgUser" class="mt-4 flex gap-2 text-[12.5px] rounded-xl px-3 py-2.5 bg-[#2f6bff]/8 text-[#1f4fc7]"><Send class="size-4 shrink-0 mt-px" />{{ $t('Ism Telegram profilingizdan olindi. Tasdiqlash server tomonida amalga oshiriladi.') }}</p>
            <div class="mt-5">
              <ProfileFields v-model="form" :role="role" :errors="errors" compact require-last-name :sections="['personal', 'study', 'company', 'location', 'contact', 'skills']" />
            </div>
            <!-- Brauzer (website) orqali: telefon + parol bilan keyin qayta kirish uchun. Telegram ichida initData yetarli. -->
            <div v-if="!isTelegram" class="mt-4 grid sm:grid-cols-2 gap-3" data-testid="password-fields">
              <BaseInput v-model="pw.password" type="password" :label="$t('Parol') + ' *'" autocomplete="new-password" :hint="$t('Kamida 8 ta belgi')" :error="errors.password" data-testid="f-password" />
              <BaseInput v-model="pw.confirm" type="password" :label="$t('Parolni takrorlang') + ' *'" autocomplete="new-password" :error="errors.confirm" data-testid="f-password2" />
            </div>
            <p class="mt-4 text-xs text-muted flex gap-1.5"><ShieldCheck class="size-4 shrink-0" />{{ $t('* belgili maydonlar majburiy. Qolganlarini keyin profilda to‘ldirishingiz mumkin.') }}</p>
            <div class="pt-5 mt-auto">
              <BaseButton type="submit" block size="lg" :loading="loading" :icon-right="ArrowRight" data-testid="ob-submit">{{ $t('Ro‘yxatdan o‘tish') }}</BaseButton>
            </div>
          </form>
        </Transition>

        <div v-if="step < 6" class="pt-6 mt-auto lg:mt-8 flex gap-3">
          <BaseButton v-if="step > 1" variant="soft" size="lg" class="hidden lg:inline-flex" :icon="ArrowLeft" @click="back">{{ $t('Orqaga') }}</BaseButton>
          <BaseButton block size="lg" class="flex-1" :disabled="!canNext" :icon-right="ArrowRight" data-testid="ob-next" @click="next">
            {{ step === 1 ? $t('Davom etish') : step === 5 ? $t('Davom etish') : $t('Keyingi') }}
          </BaseButton>
        </div>
        <p v-if="step === 1 || step === 6" class="mt-4 text-center text-sm text-muted">
          {{ $t('Hisobingiz bormi?') }} <RouterLink to="/login" class="font-semibold text-brand-600 hover:underline" data-testid="to-login">{{ $t('Kirish') }}</RouterLink>
        </p>
      </div>
    </section>
  </div>
</template>

<style scoped>
.slide-l-enter-active, .slide-l-leave-active, .slide-r-enter-active, .slide-r-leave-active { transition: opacity .25s ease, transform .35s cubic-bezier(.22, 1, .36, 1); }
.slide-l-enter-from, .slide-r-leave-to { opacity: 0; transform: translateX(28px); }
.slide-l-leave-to, .slide-r-enter-from { opacity: 0; transform: translateX(-28px); }
</style>