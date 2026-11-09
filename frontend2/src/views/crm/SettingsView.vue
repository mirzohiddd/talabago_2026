<script setup>
import { ref, reactive, computed } from 'vue'
import { useRouter } from 'vue-router'
import { UserCog, Mail, KeyRound, LogOut, Wrench, RotateCcw, Languages, Building2, Bell, Database, Download, Upload, ImagePlus, Check, Info, Lock, Clock } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import Avatar from '@/components/ui/Avatar.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { crmStore, ensureCrmLoaded, crmApi } from '@/services/crm'
import { useMediaUrl } from '@/composables/useMediaUrl'
import { auth, logout, provider } from '@/services/auth'
import { API_URL, uploadFile } from '@/services/http'
import { formatTashkent, humanDuration } from '@/utils/tashkentTime'
import { useNow } from '@/composables/useNow'
import { toast } from '@/stores/toast'
import { LOCALES, i18n, setLocale, t } from '@/i18n'

const router = useRouter()
const now = useNow()
const draft = reactive({ profile: {}, platform: {}, notifications: {}, system: {} })
const errors = reactive({})
const saving = ref(false)
ensureCrmLoaded().then(() => Object.assign(draft, JSON.parse(JSON.stringify(crmStore.settings))))
const dirty = computed(() => crmStore.loaded && JSON.stringify(draft) !== JSON.stringify(crmStore.settings))

const SYSTEM = [
  { key: 'moderation', label: 'E’lonlarni oldindan tekshirish', text: 'Yangi e’lonlar tasdiqlangandan keyin chiqadi.' },
  { key: 'registrationOpen', label: 'Yangi ro‘yxatdan o‘tish', text: 'O‘chirilsa, yangi hisob ochilmaydi.' },
  { key: 'adsEnabled', label: 'Reklama carousel', text: 'Barcha reklamalarni to‘xtatish.' },
  { key: 'maintenance', label: 'Texnik xizmat rejimi', text: 'Mini App’da “Texnik ishlar” ekrani.' },
]
const NOTIF = [
  { key: 'newTicket', label: 'Yangi support murojaati' },
  { key: 'newListing', label: 'Tekshiruvga yangi e’lon' },
  { key: 'newComplaint', label: 'Yangi shikoyat' },
  { key: 'dailyDigest', label: 'Kunlik hisobot (email)' },
]

async function save() {
  Object.keys(errors).forEach((k) => delete errors[k])
  if (!draft.profile.name?.trim()) errors.name = t('Majburiy maydon')
  if (draft.profile.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(draft.profile.email)) errors.email = t('Email noto‘g‘ri')
  if (!draft.platform.name?.trim()) errors.platform = t('Majburiy maydon')
  if (Object.keys(errors).length) return
  saving.value = true
  try {
    Object.assign(draft, JSON.parse(JSON.stringify(await crmApi.saveSettings(draft))))
    toast(t('Sozlamalar saqlandi'))
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

// ---- Rasm yuklash (avatar / logo) ----
const avatarUrl = useMediaUrl(() => draft.profile?.avatar)
const logoUrl = useMediaUrl(() => draft.platform?.logo)
function pickFile(accept) {
  return new Promise((resolve) => {
    const input = Object.assign(document.createElement('input'), { type: 'file', accept })
    input.onchange = () => resolve(input.files?.[0] || null)
    input.click()
  })
}
async function pickImage(target) {
  const f = await pickFile('image/png,image/jpeg,image/webp')
  if (!f) return
  if (f.size > 2 * 1048576) return toast(t('Rasm 2 MB dan oshmasin'), 'error')
  try {
    const { url } = await uploadFile(f, 'logo')
    if (target === 'avatar') draft.profile.avatar = url
    else draft.platform.logo = url
  } catch (e) { toast(e.message, 'error') }
}

// ---- Parol ----
const pw = reactive({ current: '', next: '', confirm: '' })
const pwErr = reactive({})
const pwBusy = ref(false)
async function changePassword() {
  Object.keys(pwErr).forEach((k) => delete pwErr[k])
  if (!pw.current) pwErr.current = t('Majburiy maydon')
  if (pw.next.length < 10) pwErr.next = t('Kamida {n} ta belgi', { n: 10 })
  else if (pw.next === pw.current) pwErr.next = t('Yangi parol eskisidan farq qilsin')
  else if (!/[A-Za-z]/.test(pw.next) || !/\d/.test(pw.next)) pwErr.next = t('Harf va raqam bo‘lsin')
  if (pw.next !== pw.confirm) pwErr.confirm = t('Parollar mos emas')
  if (Object.keys(pwErr).length) return
  pwBusy.value = true
  try {
    await provider.changePassword(pw.current, pw.next)
    Object.assign(pw, { current: '', next: '', confirm: '' })
    toast(t('Parol o‘zgartirildi'))
  } catch (e) { pwErr.current = t(e.message) }
  pwBusy.value = false
}

const logoutOpen = ref(false)
async function doLogout() { await logout(); router.replace('/login'); toast(t('Tizimdan chiqdingiz')) }
</script>

<template>
  <div class="max-w-5xl">
    <PageHeader :title="$t('Sozlamalar')" illu="code">
      <BaseButton :disabled="!dirty" :loading="saving" data-testid="settings-save" @click="save">{{ $t('Saqlash') }}</BaseButton>
    </PageHeader>

    <div class="grid lg:grid-cols-2 gap-4 stagger">
      <!-- Profil -->
      <section class="crm-card p-5 space-y-4">
        <h2 class="h2"><UserCog class="size-5 text-brand-600" />{{ $t('Administrator profili') }}</h2>
        <div class="flex items-center gap-3">
          <button class="relative group" :aria-label="$t('Rasm yuklash')" @click="pickImage('avatar')">
            <Avatar :name="draft.profile.name" :src="draft.profile.avatar" size="lg" />
            <span class="absolute inset-0 rounded-full bg-ink/40 text-white grid place-items-center opacity-0 group-hover:opacity-100 transition"><ImagePlus class="size-5" /></span>
          </button>
          <div><p class="font-semibold">@{{ auth.user?.username }}</p><p class="text-xs text-muted">{{ $t('Rol') }}: {{ $t('administrator') }}</p></div>
        </div>
        <BaseInput v-model="draft.profile.name" :label="$t('Ko‘rinadigan ism')" :error="errors.name" />
        <BaseInput v-model="draft.profile.email" :label="$t('Email (bildirishnomalar uchun)')" placeholder="support@talabago.uz" :icon="Mail" :error="errors.email" />
      </section>

      <!-- Parol -->
      <section class="crm-card p-5 space-y-3">
        <h2 class="h2"><KeyRound class="size-5 text-brand-600" />{{ $t('Parolni o‘zgartirish') }}</h2>
        <BaseInput v-model="pw.current" type="password" autocomplete="current-password" :label="$t('Joriy parol')" :icon="Lock" :error="pwErr.current" data-testid="pw-current" />
        <BaseInput v-model="pw.next" type="password" autocomplete="new-password" :label="$t('Yangi parol')" :hint="$t('Kamida 10 belgi, harf va raqam')" :error="pwErr.next" data-testid="pw-next" />
        <BaseInput v-model="pw.confirm" type="password" autocomplete="new-password" :label="$t('Yangi parolni takrorlang')" :error="pwErr.confirm" data-testid="pw-confirm" />
        <BaseButton block variant="dark" :loading="pwBusy" data-testid="pw-save" @click="changePassword">{{ $t('Parolni yangilash') }}</BaseButton>
        <p class="text-[12px] text-muted flex gap-1.5"><Info class="size-4 shrink-0" />{{ $t('Parol server tomonida yangilanadi, boshqa barcha sessiyalar yopiladi.') }}</p>
      </section>

      <!-- Til -->
      <section class="crm-card p-5">
        <h2 class="h2 mb-3"><Languages class="size-5 text-brand-600" />{{ $t('Til') }}</h2>
        <div class="grid grid-cols-2 gap-2" role="radiogroup" :aria-label="$t('Til')">
          <button v-for="l in LOCALES" :key="l.value" role="radio" :aria-checked="i18n.state.locale === l.value"
            :class="['h-11 px-3 rounded-xl border-[1.5px] flex items-center gap-2 text-sm font-semibold transition', i18n.state.locale === l.value ? 'border-brand bg-brand-50/70' : 'border-line hover:border-brand-200']"
            :data-testid="`crm-lang-${l.value}`" @click="setLocale(l.value)">
            <span aria-hidden="true">{{ l.flag }}</span><span class="flex-1 text-left truncate">{{ l.label }}</span><Check v-if="i18n.state.locale === l.value" class="size-4 text-brand-600" />
          </button>
        </div>
      </section>

      <!-- Platforma -->
      <section class="crm-card p-5 space-y-4">
        <h2 class="h2"><Building2 class="size-5 text-brand-600" />{{ $t('Platforma') }}</h2>
        <BaseInput v-model="draft.platform.name" :label="$t('Platforma nomi')" :error="errors.platform" />
        <div class="flex items-center gap-3">
          <span class="size-14 rounded-2xl border border-line bg-surface grid place-items-center overflow-hidden"><img v-if="logoUrl" :src="logoUrl" alt="" class="size-full object-contain" /><ImagePlus v-else class="size-5 text-muted" /></span>
          <div class="flex-1"><p class="text-sm font-semibold">{{ $t('Logo') }}</p><p class="text-xs text-muted">PNG/SVG/WebP · 2 MB</p></div>
          <BaseButton size="sm" variant="soft" :icon="Upload" @click="pickImage('logo')">{{ $t('Yuklash') }}</BaseButton>
        </div>
      </section>

      <!-- Bildirishnomalar -->
      <section class="crm-card p-5">
        <h2 class="h2 mb-1"><Bell class="size-5 text-brand-600" />{{ $t('Bildirishnomalar') }}</h2>
        <ul class="divide-y divide-line">
          <li v-for="n in NOTIF" :key="n.key" class="flex items-center gap-4 py-3"><p class="flex-1 text-[14.5px] font-medium">{{ $t(n.label) }}</p><ToggleSwitch v-model="draft.notifications[n.key]" :aria-label="$t(n.label)" /></li>
        </ul>
      </section>

      <!-- Tizim -->
      <section class="crm-card p-5">
        <h2 class="h2 mb-1"><Wrench class="size-5 text-brand-600" />{{ $t('Tizim') }}</h2>
        <ul class="divide-y divide-line">
          <li v-for="s in SYSTEM" :key="s.key" class="flex items-center gap-4 py-3">
            <div class="flex-1"><p class="font-medium text-[14.5px]">{{ $t(s.label) }}</p><p class="text-[12.5px] text-muted">{{ $t(s.text) }}</p></div>
            <ToggleSwitch v-model="draft.system[s.key]" :aria-label="$t(s.label)" />
          </li>
        </ul>
      </section>


      <!-- Sessiya va chiqish -->
      <section class="crm-card p-5 space-y-3 lg:col-span-2">
        <dl class="grid sm:grid-cols-3 gap-3 text-sm">
          <div class="info"><dt>{{ $t('Sessiya tugashiga') }}</dt><dd class="tabular-nums" data-testid="session-left">{{ humanDuration(auth.expiresAt - now) }}</dd></div>
          <div class="info"><dt>{{ $t('Ma’lumot manbasi') }}</dt><dd>FastAPI · JSON <span class="font-mono text-[11px] text-muted block truncate">{{ API_URL }}</span></dd></div>
          <div class="info"><dt>{{ $t('Vaqt zonasi') }}</dt><dd><Clock class="inline size-3.5 -mt-0.5" /> Asia/Tashkent</dd></div>
        </dl>
        <BaseButton variant="danger" :icon="LogOut" data-testid="crm-logout" @click="logoutOpen = true">{{ $t('Akkauntdan chiqish') }}</BaseButton>
      </section>
    </div>

    <ConfirmModal v-model="logoutOpen" :title="$t('Akkauntdan chiqish')" :text="$t('Sessiya yakunlanadi.')" :confirm-text="$t('Chiqish')" danger @confirm="doLogout" />
  </div>
</template>

<style scoped>
@reference "../../style.css";
.h2 { @apply font-bold flex items-center gap-2; }
.info { @apply rounded-xl bg-surface p-3; }
.info dt { @apply text-xs text-muted font-semibold; }
.info dd { @apply mt-1 font-semibold; }
</style>
