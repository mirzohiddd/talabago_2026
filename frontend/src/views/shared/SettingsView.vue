<script setup>
/**
 * Sozlamalar — rolga qarab bo‘limlar:
 *  Talaba: shaxsiy profil, o‘qish, ko‘nikmalar, CV, saqlangan e’lonlar, telefon/Telegram, til, bildirishnomalar, yordam, chiqish
 *  Ish beruvchi: kompaniya profili, logo, mas’ul shaxs, telefon/Telegram, manzil, til, bildirishnomalar, yordam, chiqish
 *  Uy egasi: shaxsiy profil, telefon, Telegram, hudud, til, bildirishnomalar, yordam, chiqish
 */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, computed, watch, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { UserPen, Bell, Send, Languages, LogOut, LifeBuoy, ChevronRight, GraduationCap, Sparkles, FileText, Heart, Building2, ImagePlus, Phone, MapPin, UserRound, Upload, Trash2, Check, Database, KeyRound } from 'lucide-vue-next'
import Avatar from '@/components/ui/Avatar.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import ProfileFields from '@/components/forms/ProfileFields.vue'
import { session, logout, toast } from '@/stores/session'
import { ROLES, SHIFTS } from '@/config/roles'
import { authApi, jobsApi, housingApi, uploadFile, fullName } from '@/services'
import { LOCALES, i18n, setLocale, t } from '@/i18n'
import { validate, profileSchema } from '@/utils/validate'
import { normalizePhone, fileSize } from '@/utils/format'

const route = useRoute()
const router = useRouter()
const role = computed(() => ROLES[session.role])
const u = computed(() => session.user || {})
onMounted(async () => { if (!session.user) session.user = await authApi.me() })

// ---- Tahrirlash modali (bo‘lim bo‘yicha) ----
const SECTIONS = {
  profile: { title: 'Shaxsiy profil', parts: ['personal', 'location'] },
  study: { title: 'O‘qish ma’lumotlari', parts: ['study'] },
  skills: { title: 'Ko‘nikmalar', parts: ['skills', 'about'] },
  contact: { title: 'Telefon va Telegram', parts: ['contact'] },
  company: { title: 'Kompaniya profili', parts: ['company'] },
  person: { title: 'Mas’ul shaxs', parts: ['personal'] },
}
const edit = ref(null)
const form = ref({})
const errors = ref({})
const saving = ref(false)
function openEdit(key) { form.value = JSON.parse(JSON.stringify(u.value)); errors.value = {}; edit.value = key }
watch(() => route.query.edit, (v) => { if (v && SECTIONS[v]) { openEdit(v); router.replace({ query: {} }) } }, { immediate: true })
async function save() {
  const schema = profileSchema(session.role)
  errors.value = validate(form.value, schema)
  if (Object.keys(errors.value).length) return
  saving.value = true
  const patch = { ...form.value, phone: normalizePhone(form.value.phone) || form.value.phone, telegram: form.value.telegram ? '@' + form.value.telegram.replace(/^@/, '') : '' }
  try {
    session.user = await authApi.updateProfile(patch)
    edit.value = null
    toast(t('Profil saqlandi'))
  } catch (e) {
    toast(e.message, 'error')
  } finally {
    saving.value = false
  }
}

// ---- Parol (brauzer orqali kirish uchun) ----
// Bildirishnoma sozlamalari serverda saqlanadi va serverda qo‘llanadi (Telegram xabarlari / ilova bildirishnomalari)
async function setPref(key, value) {
  const prev = session.user?.[key]
  if (session.user) session.user = { ...session.user, [key]: value }
  try {
    session.user = await authApi.updateProfile({ [key]: value })
    toast(t('Saqlandi'))
  } catch (e) {
    if (session.user) session.user = { ...session.user, [key]: prev }
    toast(e.message, 'error')
  }
}

const pwOpen = ref(false)
const pw = ref({ current: '', next: '', confirm: '' })
const pwErr = ref({})
const pwSaving = ref(false)
function openPw() { pw.value = { current: '', next: '', confirm: '' }; pwErr.value = {}; pwOpen.value = true }
async function savePw() {
  pwErr.value = {}
  if (u.value.hasPassword && !pw.value.current) pwErr.value.current = t('Majburiy maydon')
  if (pw.value.next.length < 8) pwErr.value.next = t('Kamida {n} ta belgi', { n: 8 })
  else if (pw.value.next !== pw.value.confirm) pwErr.value.confirm = t('Parollar mos emas')
  if (Object.keys(pwErr.value).length) return
  pwSaving.value = true
  try {
    await authApi.changePassword(pw.value.current, pw.value.next)
    session.user = await authApi.me()
    pwOpen.value = false
    toast(t('Parol saqlandi'))
  } catch (e) {
    if (e.status === 400) pwErr.value.current = t('Joriy parol noto‘g‘ri')
    else toast(e.message, 'error')
  } finally {
    pwSaving.value = false
  }
}
const editOpen = computed({ get: () => !!edit.value, set: (v) => { if (!v) edit.value = null } })

// ---- CV / logo ----
const cvInput = ref(null)
const logoInput = ref(null)
const uploading = ref('')
async function onCv(e) {
  const f = e.target.files?.[0]; e.target.value = ''
  if (!f) return
  if (!/\.(pdf|docx?)$/i.test(f.name)) return toast(t('Faqat PDF yoki Word fayl'), 'error')
  if (f.size > 5 * 1048576) return toast(t('Fayl hajmi 5 MB dan oshmasin'), 'error')
  uploading.value = 'cv'
  const url = await uploadFile(f, 'cv')
  session.user = await authApi.updateProfile({ cv: { name: f.name, size: f.size, url } })
  uploading.value = ''
  toast(t('CV yuklandi'))
}
async function removeCv() { session.user = await authApi.updateProfile({ cv: null }); toast(t('CV o‘chirildi')) }
async function onLogo(e) {
  const f = e.target.files?.[0]; e.target.value = ''
  if (!f) return
  if (!/^image\/(png|jpeg|webp)$/.test(f.type) || f.size > 2 * 1048576) return toast(t('Logo: PNG/JPG/WebP, 2 MB gacha'), 'error')
  uploading.value = 'logo'
  session.user = await authApi.updateProfile({ logo: await uploadFile(f, 'logo') })
  uploading.value = ''
  toast(t('Logo yangilandi'))
}

// ---- Saqlanganlar ----
const savedJobs = ref(0)
const savedHouses = ref(0)
onMounted(async () => {
  if (session.role !== 'student') return
  ;[savedJobs.value, savedHouses.value] = await Promise.all([jobsApi.savedCount(), housingApi.savedCount()]).catch(() => [0, 0])
})

// ---- Til va bildirishnomalar ----
async function changeLang(v) {
  setLocale(v)
  session.user = await authApi.updateProfile({ language: v })
  toast(t('Til o‘zgartirildi'))
}
const logoutOpen = ref(false)
function doLogout() { logout(); router.replace('/welcome') }
const shiftLabel = computed(() => SHIFTS.find((s) => s.value === u.value.shift)?.label)
</script>

<template>
  <div class="page lg:max-w-5xl">
    <PageIntro class="mb-4" />

    <!-- Profil sarlavhasi -->
    <section class="card p-5 flex items-center gap-4 animate-fade-up">
      <div class="relative">
        <Avatar :name="session.role === 'employer' ? u.company : fullName(u)" :src="u.logo" size="xl" />
        <button v-if="session.role === 'employer'" class="absolute -right-1 -bottom-1 size-8 rounded-full bg-ink text-white grid place-items-center ring-4 ring-white" :aria-label="$t('Logo yuklash')" data-testid="logo-btn" @click="logoInput.click()"><ImagePlus class="size-4" /></button>
      </div>
      <div class="min-w-0 flex-1">
        <p class="font-extrabold text-[20px] tracking-tight truncate">{{ session.role === 'employer' ? u.company : fullName(u) }}</p>
        <p class="text-sm text-muted truncate">{{ session.role === 'employer' ? fullName(u) + (u.position ? ` · ${u.position}` : '') : u.phone }}</p>
        <span class="inline-flex items-center gap-1 text-xs font-semibold text-brand-700 bg-brand-50 rounded-full h-6 px-2.5 mt-1.5"><component :is="role?.icon" class="size-3.5" />{{ $t(role?.title) }}</span>
      </div>
      <BaseButton variant="soft" size="sm" :icon="UserPen" class="hidden sm:inline-flex" @click="openEdit(session.role === 'employer' ? 'company' : 'profile')">{{ $t('Tahrirlash') }}</BaseButton>
      <input ref="logoInput" type="file" accept="image/png,image/jpeg,image/webp" class="hidden" @change="onLogo" />
    </section>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-4 items-start">
      <!-- ===== Profil bo‘limlari ===== -->
      <section class="card divide-y divide-line">
        <h2 class="sec">{{ $t('Profil') }}</h2>
        <template v-if="session.role === 'employer'">
          <button class="row" data-testid="sec-company" @click="openEdit('company')"><Building2 class="ri" /><span class="rt"><b>{{ $t('Kompaniya profili') }}</b><small>{{ [u.company, $t(u.industry || ''), u.address].filter(Boolean).join(' · ') }}</small></span><ChevronRight class="rc" /></button>
          <button class="row" @click="logoInput.click()"><ImagePlus class="ri" /><span class="rt"><b>{{ $t('Logo') }}</b><small>{{ u.logo ? $t('Yuklangan') : $t('PNG/JPG, 2 MB gacha') }}</small></span><ChevronRight class="rc" /></button>
          <button class="row" @click="openEdit('person')"><UserRound class="ri" /><span class="rt"><b>{{ $t('Mas’ul shaxs') }}</b><small>{{ fullName(u) }}{{ u.position ? ` · ${u.position}` : '' }}</small></span><ChevronRight class="rc" /></button>
          <button class="row" @click="openEdit('company')"><MapPin class="ri" /><span class="rt"><b>{{ $t('Manzil') }}</b><small>{{ u.address || '—' }}</small></span><ChevronRight class="rc" /></button>
        </template>
        <template v-else>
          <button class="row" data-testid="sec-profile" @click="openEdit('profile')"><UserRound class="ri" /><span class="rt"><b>{{ $t('Shaxsiy profil') }}</b><small>{{ fullName(u) }}{{ u.birthDate ? ` · ${$date(u.birthDate)}` : '' }}</small></span><ChevronRight class="rc" /></button>
          <button v-if="session.role === 'landlord'" class="row" @click="openEdit('profile')"><MapPin class="ri" /><span class="rt"><b>{{ $t('Hudud') }}</b><small>{{ [$t(u.district || ''), $t(u.city || '')].filter(Boolean).join(', ') || '—' }}</small></span><ChevronRight class="rc" /></button>
        </template>
        <template v-if="session.role === 'student'">
          <button class="row" @click="openEdit('study')"><GraduationCap class="ri" /><span class="rt"><b>{{ $t('O‘qish ma’lumotlari') }}</b><small>{{ [u.university, u.faculty, u.course && $t('{n}-kurs', { n: u.course }), $t(shiftLabel || '')].filter(Boolean).join(' · ') || $t('To‘ldirilmagan') }}</small></span><ChevronRight class="rc" /></button>
          <button class="row" @click="openEdit('skills')"><Sparkles class="ri" /><span class="rt"><b>{{ $t('Ko‘nikmalar') }}</b><small>{{ (u.skills || []).map((s) => $t(s)).join(', ') || $t('To‘ldirilmagan') }}</small></span><ChevronRight class="rc" /></button>
          <div class="row cursor-default!">
            <FileText class="ri" />
            <span class="rt"><b>CV</b><small>{{ u.cv ? `${u.cv.name} · ${fileSize(u.cv.size || 0)}` : $t('PDF yoki Word, 5 MB gacha') }}</small></span>
            <button v-if="u.cv" class="size-9 grid place-items-center rounded-full hover:bg-danger/10 text-danger" :aria-label="$t('CV ni o‘chirish')" @click="removeCv"><Trash2 class="size-4" /></button>
            <BaseButton size="sm" variant="soft" :icon="Upload" :loading="uploading === 'cv'" data-testid="cv-btn" :aria-label="u.cv ? $t('Almashtirish') : $t('Yuklash')" @click="cvInput.click()"><span class="hidden sm:inline">{{ u.cv ? $t('Almashtirish') : $t('Yuklash') }}</span></BaseButton>
            <input ref="cvInput" type="file" accept=".pdf,.doc,.docx,application/pdf" class="hidden" data-testid="cv-input" @change="onCv" />
          </div>
        </template>
        <button class="row" data-testid="sec-contact" @click="openEdit(session.role === 'employer' ? 'company' : 'contact')"><Phone class="ri" /><span class="rt"><b>{{ $t('Telefon va Telegram') }}</b><small>{{ [u.phone, u.telegram].filter(Boolean).join(' · ') }}</small></span><ChevronRight class="rc" /></button>
        <button class="row" data-testid="sec-password" @click="openPw"><KeyRound class="ri" /><span class="rt"><b>{{ $t('Parol') }}</b><small>{{ u.hasPassword ? $t('Telefon raqam va parol bilan kirish') : $t('Parol o‘rnatilmagan') }}</small></span><ChevronRight class="rc" /></button>
      </section>

      <div class="space-y-4">
        <!-- Saqlanganlar (talaba) -->
        <section v-if="session.role === 'student'" class="card divide-y divide-line">
          <h2 class="sec">{{ $t('Saqlangan e’lonlar') }}</h2>
          <RouterLink to="/student/jobs?saved=1" class="row"><Heart class="ri" /><span class="rt"><b>{{ $t('Saqlangan ishlar') }}</b><small>{{ $t('{n} ta e’lon', { n: savedJobs }) }}</small></span><ChevronRight class="rc" /></RouterLink>
          <RouterLink to="/student/housing?saved=1" class="row"><Heart class="ri" /><span class="rt"><b>{{ $t('Saqlangan uylar') }}</b><small>{{ $t('{n} ta e’lon', { n: savedHouses }) }}</small></span><ChevronRight class="rc" /></RouterLink>
        </section>

        <!-- Til -->
        <section class="card p-4">
          <h2 class="sec px-0! pt-0! flex items-center gap-2"><Languages class="size-4" />{{ $t('Til') }}</h2>
          <div class="grid grid-cols-2 gap-2 mt-2" role="radiogroup" :aria-label="$t('Til')">
            <button v-for="l in LOCALES" :key="l.value" role="radio" :aria-checked="i18n.state.locale === l.value"
              :class="['h-12 px-3 rounded-xl border-[1.5px] flex items-center gap-2 text-left text-sm font-semibold transition', i18n.state.locale === l.value ? 'border-brand bg-brand-50/70' : 'border-line hover:border-brand-200']"
              :data-testid="`set-lang-${l.value}`" @click="changeLang(l.value)">
              <span aria-hidden="true">{{ l.flag }}</span><span class="flex-1 truncate">{{ l.label }}</span><Check v-if="i18n.state.locale === l.value" class="size-4 text-brand-600" />
            </button>
          </div>
        </section>

        <!-- Bildirishnomalar -->
        <section class="card divide-y divide-line">
          <h2 class="sec">{{ $t('Bildirishnomalar') }}</h2>
          <label class="row"><Bell class="ri" /><span class="rt"><b>{{ $t('Ilova bildirishnomalari') }}</b><small>{{ $t('Ariza, so‘rov va support javoblari') }}</small></span><ToggleSwitch :model-value="u.notifyApp !== false" data-testid="pref-app" @update:model-value="setPref('notifyApp', $event)" /></label>
          <label class="row"><Send class="ri" /><span class="rt"><b>{{ $t('Telegram orqali xabar') }}</b><small>{{ u.telegramLinked ? $t('Bot orqali: ariza, so‘rov va Support javoblari') : $t('Telegram hisobi bog‘lanmagan — ilovani Telegram’dan oching') }}</small></span><ToggleSwitch :model-value="u.notifyTelegram !== false" data-testid="pref-tg" @update:model-value="setPref('notifyTelegram', $event)" /></label>
        </section>

        <!-- Yordam va chiqish -->
        <section class="card divide-y divide-line">
          <RouterLink :to="`/${session.role}/support`" class="row" data-testid="settings-support"><LifeBuoy class="ri" /><span class="rt"><b>{{ $t('Texnik yordam') }}</b><small>{{ $t('TalabaGo Support: murojaat va chat') }}</small></span><ChevronRight class="rc" /></RouterLink>
          <button class="row text-danger!" data-testid="logout" @click="logoutOpen = true"><LogOut class="ri text-danger!" /><span class="rt"><b>{{ $t('Chiqish') }}</b></span></button>
        </section>

      </div>
    </div>

    <BaseModal v-model="editOpen" :title="$t(SECTIONS[edit]?.title || '')" wide>
      <ProfileFields v-if="edit" v-model="form" :role="session.role" :errors="errors" :sections="SECTIONS[edit].parts.concat(edit === 'company' ? ['contact'] : [])" />
      <template #footer><BaseButton block :loading="saving" data-testid="save-profile" @click="save">{{ $t('Saqlash') }}</BaseButton></template>
    </BaseModal>
    <BaseModal v-model="pwOpen" :title="$t('Parol')">
      <form class="space-y-4" novalidate @submit.prevent="savePw">
        <BaseInput v-if="u.hasPassword" v-model="pw.current" type="password" :label="$t('Joriy parol')" autocomplete="current-password" :error="pwErr.current" data-testid="pw-current" />
        <BaseInput v-model="pw.next" type="password" :label="$t('Yangi parol')" autocomplete="new-password" :hint="$t('Kamida 8 ta belgi')" :error="pwErr.next" data-testid="pw-next" />
        <BaseInput v-model="pw.confirm" type="password" :label="$t('Yangi parolni takrorlang')" autocomplete="new-password" :error="pwErr.confirm" data-testid="pw-confirm" />
      </form>
      <template #footer><BaseButton block :loading="pwSaving" data-testid="pw-save" @click="savePw">{{ $t('Saqlash') }}</BaseButton></template>
    </BaseModal>
    <ConfirmModal v-model="logoutOpen" :title="$t('Chiqish')" :text="$t('Akkauntdan chiqasizmi? Keyingi safar qayta ro‘yxatdan o‘tish oynasi ochiladi.')" :confirm-text="$t('Chiqish')" danger @confirm="doLogout" />
  </div>
</template>

<style scoped>
@reference "../../style.css";
.sec { @apply px-4 pt-4 pb-2 text-[12px] font-bold uppercase tracking-wider text-muted; }
.row { @apply w-full flex items-center gap-3 px-4 min-h-[60px] py-2.5 text-left hover:bg-surface/60 transition-colors cursor-pointer; }
.ri { @apply size-[20px] text-brand-600 shrink-0; }
.rt { @apply flex-1 min-w-0; }
.rt b { @apply block text-[15px] font-semibold; }
.rt small { @apply block text-[12.5px] text-muted truncate; }
.rc { @apply size-[18px] text-muted shrink-0; }
</style>
