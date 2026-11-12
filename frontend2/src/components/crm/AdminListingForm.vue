<script setup>
/**
 * Admin (Support) e’lon qo‘shish / tahrirlash — ish beruvchi yoki uy egasi akkauntisiz.
 * Telegram kanal/guruhdan olingan, egasi bilan tekshirilgan e’lonlar uchun:
 *   asosiy ma’lumotlar + manba (source) + tekshiruv va rozilik (verification) + “darhol nashr qilish”.
 * Nashr faqat “egasi bilan bog‘lanildi” va “egasi rozi” belgilanganda mumkin (server ham tekshiradi).
 * Majburiy (*): lavozim / e’lon nomi, ish yoki uy turi, (uy uchun) tuman va manba nomi. Qolgan barcha maydonlar ixtiyoriy;
 * maosh yoki narx noma’lum bo‘lsa — “Kelishiladi”. Tekshiruvsiz e’lon “Tasdiqlashni kutmoqda” holatida saqlanadi.
 */
import { computed, reactive, ref, watch } from 'vue'
import { ImagePlus, X, Send, ShieldCheck, Link2, Loader2 } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import PhoneInput from '@/components/ui/PhoneInput.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import MediaImg from '@/components/ui/MediaImg.vue'
import { JOB_TYPES, JOB_FORMATS, SALARY_PERIODS, WORK_TIMES, HOUSE_TYPES, AUDIENCES, AMENITIES, CITIES, CITY_LIST } from '@/config/status'
import { phoneProblem, PHONE_MESSAGES } from '@shared/phone'
import { uploadFile } from '@/services/http'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const open = defineModel({ type: Boolean, default: false })
const props = defineProps({
  kind: { type: String, required: true }, // 'job' | 'house'
  item: { type: Object, default: null }, // tahrirlash uchun (admin e’loni)
  api: { type: Object, required: true }, // crmApi.jobs | crmApi.houses
})
const emit = defineEmits(['saved'])
const isJob = computed(() => props.kind === 'job')
const editing = computed(() => !!props.item)

const SOURCE_TYPES = [
  { value: 'telegram_channel', label: 'Telegram kanal' }, { value: 'telegram_group', label: 'Telegram guruh' },
  { value: 'phone', label: 'Telefon orqali' }, { value: 'other', label: 'Boshqa' },
]
const METHODS = [{ value: 'phone', label: 'Telefon qo‘ng‘irog‘i' }, { value: 'telegram', label: 'Telegram yozishma' }, { value: 'in_person', label: 'Shaxsan' }, { value: 'other', label: 'Boshqa' }]
const opts = (arr) => arr.map((o) => ({ value: o.value, label: t(o.label) }))

const editingItem = (s) => !!s.id
function blank() {
  const s = props.item || {}
  const v = s.verification || {}
  const src = s.source || {}
  return {
    title: s.title || '', company: s.company || '', type: s.type || (isJob.value ? 'hourly' : 'flat'), format: s.format || 'offline',
    salary: s.salary ?? '', salaryPeriod: s.salaryPeriod || 'month', salaryNegotiable: editingItem(s) ? !!(s.salaryNegotiable || s.salary == null) : false, workTime: s.workTime || 'flexible', schedule: s.schedule || '',
    city: s.city || 'Toshkent', district: s.district || '', address: s.address || '', requirementsText: (s.requirements || []).join('\n'),
    description: s.description || '', phone: s.phone || '', telegram: (s.telegram || '').replace(/^@/, ''), contactName: s.contactName || '',
    price: s.price ?? '', priceNegotiable: editingItem(s) ? !!(s.priceNegotiable || s.price == null) : false, rooms: s.rooms ?? 1, capacity: s.capacity ?? 1, freeSpots: s.freeSpots ?? 1, area: s.area ?? '', audience: s.audience || 'any',
    amenities: [...(s.amenities || [])], photos: [...(s.photos || [])],
    srcType: src.type || 'telegram_channel', srcName: src.name || '', srcUrl: src.url || '', srcPostedAt: src.postedAt || '',
    ownerContacted: !!v.ownerContacted, ownerConsent: !!v.ownerConsent, phoneConsent: !!v.phoneConsent, method: v.method || 'phone', note: v.note || '',
    publish: false,
  }
}
const form = reactive(blank())
const errors = reactive({})
const busy = ref(false)
const uploading = ref(false)
watch(open, (v) => { if (v) { Object.assign(form, blank()); Object.keys(errors).forEach((k) => delete errors[k]) } })

const districts = computed(() => (CITIES[form.city] || []).map((d) => ({ value: d, label: t(d) })))
const canPublish = computed(() => form.ownerContacted && form.ownerConsent)
watch(canPublish, (v) => { if (!v) form.publish = false })

function validate() {
  Object.keys(errors).forEach((k) => delete errors[k])
  const need = (k, ok, msg = t('Majburiy maydon')) => { if (!ok) errors[k] = msg }
  // majburiy — faqat eng zarurlari
  need('title', form.title.trim().length >= 3, form.title.trim() ? t('Kamida 3 ta belgi') : t('Majburiy maydon'))
  need('srcName', form.srcName.trim().length >= 2, t('Manba nomini yozing (kanal / guruh)'))
  if (!isJob.value) need('district', !!form.district)
  // ixtiyoriy — faqat to‘ldirilgan bo‘lsa tekshiriladi
  if (form.srcUrl && !/^https?:\/\//.test(form.srcUrl)) errors.srcUrl = t('Havola https:// bilan boshlansin')
  const pp = phoneProblem(form.phone)
  if (form.phone && pp && pp !== 'empty') errors.phone = t(PHONE_MESSAGES[pp])
  const num = (k, neg) => { if (!form[neg] && form[k] !== '' && form[k] != null && !(+form[k] > 0)) errors[k] = t('Musbat son kiriting yoki “Kelishiladi”ni tanlang') }
  if (isJob.value) num('salary', 'salaryNegotiable')
  else {
    num('price', 'priceNegotiable')
    for (const k of ['rooms', 'capacity']) if (form[k] !== '' && !(+form[k] >= 1)) errors[k] = t('Kamida 1')
    if (form.freeSpots !== '' && !(+form.freeSpots >= 0)) errors.freeSpots = t('Manfiy bo‘lmasin')
    if (form.area !== '' && form.area != null && !(+form.area > 0)) errors.area = t('Musbat son kiriting')
  }
  return !Object.keys(errors).length
}

function payload() {
  const common = {
    title: form.title.trim(), city: form.city, description: form.description.trim(), phone: form.phone || null,
    telegram: form.telegram ? '@' + form.telegram.replace(/^@/, '') : null, contactName: form.contactName.trim(),
  }
  const meta = {
    source: { type: form.srcType, name: form.srcName.trim(), url: form.srcUrl.trim(), postedAt: form.srcPostedAt },
    verification: { ownerContacted: form.ownerContacted, ownerConsent: form.ownerConsent, phoneConsent: form.phoneConsent, method: form.method, note: form.note.trim() },
  }
  const body = isJob.value
    ? { ...common, company: form.company.trim(), type: form.type, format: form.format, workTime: form.workTime,
        salary: form.salaryNegotiable || form.salary === '' ? null : +form.salary, salaryNegotiable: form.salaryNegotiable || form.salary === '', salaryPeriod: form.salaryPeriod,
        schedule: form.schedule.trim(), district: form.format === 'online' ? null : form.district || null, address: form.address.trim(),
        requirements: form.requirementsText.split('\n').map((x) => x.trim()).filter(Boolean).slice(0, 20) }
    : { ...common, type: form.type, price: form.priceNegotiable || form.price === '' ? null : +form.price, priceNegotiable: form.priceNegotiable || form.price === '',
        district: form.district, address: form.address.trim(), rooms: +form.rooms || 1, capacity: +form.capacity || 1,
        freeSpots: form.freeSpots === '' ? 1 : +form.freeSpots, area: form.area === '' ? null : +form.area, audience: form.audience, amenities: form.amenities, photos: form.photos }
  return { ...body, ...meta }
}

function toggleNego(k) {
  const f = k + 'Negotiable'
  form[f] = !form[f]
  if (form[f]) { form[k] = ''; delete errors[k] }
}

async function addPhotos(e) {
  const files = [...(e.target.files || [])].slice(0, 10 - form.photos.length)
  e.target.value = ''
  uploading.value = true
  try {
    for (const f of files) form.photos.push((await uploadFile(f, 'photo')).url)
    delete errors.photos
  } catch (err) { toast(t(err.message), 'error') } finally { uploading.value = false }
}

async function save() {
  if (!validate()) return
  busy.value = true
  try {
    const body = payload()
    let item
    if (editing.value) {
      // tahrirlash: holat alohida (Tasdiqlash / Yashirish tugmalari) — bu yerda faqat ma’lumotlar, manba va tekshiruv
      item = await props.api.update(props.item.id, body)
      toast(t('Saqlandi'))
    } else {
      item = await props.api.create({ ...body, publish: form.publish })
      toast(form.publish ? t('E’lon nashr qilindi — foydalanuvchilarga ko‘rinadi') : t('E’lon saqlandi — tasdiqlashni kutmoqda'))
    }
    open.value = false
    emit('saved', item)
  } catch (err) {
    for (const fe of err.data?.errors || []) if (fe.field && fe.field !== 'body') errors[fe.field] = t(fe.message)
    toast(t(err.message), 'error')
  } finally { busy.value = false }
}
</script>

<template>
  <BaseModal v-model="open" wide :title="editing ? $t('E’lonni tahrirlash') : (isJob ? $t('Ish e’loni qo‘shish') : $t('Turar joy qo‘shish'))"
    :subtitle="$t('Telegram kanal yoki guruhdan olingan, egasi bilan tekshirilgan e’lon')">
    <form class="space-y-6" novalidate data-testid="admin-listing-form" @submit.prevent="save">
      <!-- Asosiy ma’lumotlar -->
      <section class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.title" :label="isJob ? $t('Lavozim') : $t('E’lon nomi')" :error="errors.title" required class="sm:col-span-2" data-testid="al-title" />
        <template v-if="isJob">
          <BaseInput v-model="form.company" :label="$t('Ish joyi / kompaniya')" :placeholder="$t('Ixtiyoriy')" :error="errors.company" data-testid="al-company" />
          <BaseSelect v-model="form.type" :label="$t('Ish turi')" :options="opts(JOB_TYPES)" required />
          <div class="sm:col-span-2">
            <div class="flex items-end gap-2">
              <BaseInput v-model="form.salary" type="number" inputmode="numeric" min="1" :label="$t('Maosh (so‘m)')" :error="errors.salary" :disabled="form.salaryNegotiable"
                :placeholder="form.salaryNegotiable ? $t('Kelishiladi') : $t('Ixtiyoriy')" class="flex-1 min-w-0" data-testid="al-salary" />
              <BaseSelect v-if="!form.salaryNegotiable" v-model="form.salaryPeriod" :options="opts(SALARY_PERIODS)" class="w-32 sm:w-40 shrink-0" :aria-label="$t('Maosh davri')" />
            </div>
            <button type="button" :class="['nego', form.salaryNegotiable ? 'bg-brand text-white border-brand' : 'bg-white border-line hover:border-brand']" :aria-pressed="form.salaryNegotiable" data-testid="al-salary-nego" @click="toggleNego('salary')">{{ $t('Kelishiladi') }}</button>
          </div>
          <BaseSelect v-model="form.workTime" :label="$t('Ish vaqti')" :options="opts(WORK_TIMES)" />
          <BaseInput v-model="form.schedule" :label="$t('Ish jadvali')" :placeholder="$t('Masalan: Du–Ju, 18:00–23:00')" data-testid="al-schedule" />
          <BaseSelect v-model="form.format" :label="$t('Format')" :options="opts(JOB_FORMATS)" />
        </template>
        <template v-else>
          <BaseSelect v-model="form.type" :label="$t('Turar joy turi')" :options="opts(HOUSE_TYPES)" required />
          <div>
            <BaseInput v-model="form.price" type="number" inputmode="numeric" min="1" :label="$t('Oylik narx (so‘m)')" :error="errors.price" :disabled="form.priceNegotiable"
              :placeholder="form.priceNegotiable ? $t('Kelishiladi') : $t('Ixtiyoriy')" data-testid="al-price" />
            <button type="button" :class="['nego', form.priceNegotiable ? 'bg-brand text-white border-brand' : 'bg-white border-line hover:border-brand']" :aria-pressed="form.priceNegotiable" data-testid="al-price-nego" @click="toggleNego('price')">{{ $t('Kelishiladi') }}</button>
          </div>
          <BaseInput v-model="form.rooms" type="number" inputmode="numeric" min="1" :label="$t('Xonalar soni')" :error="errors.rooms" data-testid="al-rooms" />
          <BaseInput v-model="form.area" type="number" inputmode="numeric" min="1" :label="$t('Maydoni (m²)')" :placeholder="$t('Ixtiyoriy')" :error="errors.area" />
          <BaseInput v-model="form.capacity" type="number" inputmode="numeric" min="1" :label="$t('Necha kishilik')" :error="errors.capacity" />
          <BaseInput v-model="form.freeSpots" type="number" inputmode="numeric" min="0" :label="$t('Bo‘sh joylar')" :error="errors.freeSpots" />
          <BaseSelect v-model="form.audience" :label="$t('Kim uchun')" :options="opts(AUDIENCES)" />
        </template>
        <BaseSelect v-model="form.city" :label="$t('Shahar')" :options="CITY_LIST.map((c) => ({ value: c, label: $t(c) }))" @update:model-value="form.district = ''" />
        <BaseSelect v-if="!isJob || form.format === 'offline'" v-model="form.district" :label="$t('Tuman')" :placeholder="$t('Tanlang')" :options="districts" :error="errors.district" :required="!isJob" data-testid="al-district" />
        <BaseInput v-model="form.address" :label="$t('Manzil')" :placeholder="$t('Ixtiyoriy')" :error="errors.address" class="sm:col-span-2" data-testid="al-address" />
        <BaseTextarea v-if="isJob" v-model="form.requirementsText" :label="$t('Talablar (har biri yangi qatorda)')" :rows="3" class="sm:col-span-2" data-testid="al-req" />
        <div v-else class="sm:col-span-2">
          <p class="label">{{ $t('Sharoitlar') }}</p>
          <div class="flex flex-wrap gap-1.5">
            <button v-for="a in AMENITIES" :key="a" type="button" :class="['h-8 px-3 rounded-full text-[12.5px] font-semibold border transition', form.amenities.includes(a) ? 'bg-brand text-white border-brand' : 'bg-white border-line hover:border-brand']"
              @click="form.amenities = form.amenities.includes(a) ? form.amenities.filter((x) => x !== a) : [...form.amenities, a]">{{ $t(a) }}</button>
          </div>
        </div>
        <BaseTextarea v-model="form.description" :label="$t('Tavsif')" :placeholder="$t('Ixtiyoriy')" :rows="4" :error="errors.description" class="sm:col-span-2" data-testid="al-desc" />
      </section>

      <!-- Rasmlar -->
      <section v-if="!isJob">
        <p class="label">{{ $t('Rasmlar') }} <span class="text-muted font-normal">({{ form.photos.length }}/10 · {{ $t('ixtiyoriy') }})</span></p>
        <div class="grid grid-cols-3 sm:grid-cols-5 gap-2">
          <div v-for="(p, i) in form.photos" :key="p" class="relative">
            <MediaImg :src="p" class="w-full aspect-[4/3] object-cover rounded-xl bg-brand-50" />
            <button type="button" class="absolute top-1 right-1 size-7 grid place-items-center rounded-full bg-black/60 text-white" :aria-label="$t('O‘chirish')" @click="form.photos.splice(i, 1)"><X class="size-4" /></button>
          </div>
          <label v-if="form.photos.length < 10" class="aspect-[4/3] grid place-items-center rounded-xl border-2 border-dashed border-line hover:border-brand cursor-pointer text-muted">
            <Loader2 v-if="uploading" class="size-6 animate-spin" />
            <span v-else class="flex flex-col items-center gap-1 text-xs font-semibold"><ImagePlus class="size-6" />{{ $t('Rasm qo‘shish') }}</span>
            <input type="file" accept="image/*" multiple class="sr-only" data-testid="al-photos" @change="addPhotos" />
          </label>
        </div>
        <p v-if="errors.photos" class="text-danger text-xs mt-1" role="alert">{{ errors.photos }}</p>
      </section>

      <!-- Aloqa -->
      <section class="grid sm:grid-cols-3 gap-4">
        <BaseInput v-model="form.contactName" :label="isJob ? $t('Aloqa uchun shaxs') : $t('Uy egasining ismi')" />
        <PhoneInput v-model="form.phone" :label="$t('Telefon')" :error="errors.phone" data-testid="al-phone" />
        <BaseInput v-model="form.telegram" :label="$t('Telegram')" :icon="Send" placeholder="@username" />
      </section>

      <!-- Manba -->
      <section class="rounded-2xl border border-line p-4 space-y-4">
        <p class="font-bold flex items-center gap-2"><Link2 class="size-4 text-brand-600" />{{ $t('Manba') }}</p>
        <div class="grid sm:grid-cols-2 gap-4">
          <BaseSelect v-model="form.srcType" :label="$t('Manba turi')" :options="opts(SOURCE_TYPES)" />
          <BaseInput v-model="form.srcName" :label="$t('Kanal / guruh nomi')" placeholder="@kanal_nomi" :error="errors.srcName" required data-testid="al-src-name" />
          <BaseInput v-model="form.srcUrl" :label="$t('E’lon havolasi')" placeholder="https://t.me/..." :error="errors.srcUrl" />
          <BaseInput v-model="form.srcPostedAt" type="date" :label="$t('Manbada joylangan sana')" />
        </div>
      </section>

      <!-- Tekshiruv va rozilik -->
      <section class="rounded-2xl border border-line p-4 space-y-3" data-testid="al-verification">
        <p class="font-bold flex items-center gap-2"><ShieldCheck class="size-4 text-brand-600" />{{ $t('Tekshiruv va rozilik') }}</p>
        <label class="flex items-center justify-between gap-3 text-sm"><span>{{ $t('E’lon egasi bilan bog‘lanib, ma’lumotlar tasdiqlandi') }}</span><ToggleSwitch v-model="form.ownerContacted" data-testid="al-contacted" /></label>
        <label class="flex items-center justify-between gap-3 text-sm"><span>{{ $t('Egasi TalabaGo’da joylashga rozi') }}</span><ToggleSwitch v-model="form.ownerConsent" data-testid="al-consent" /></label>
        <label class="flex items-center justify-between gap-3 text-sm"><span>{{ $t('Egasi telefon va Telegram talabalarga ko‘rsatilishiga rozi') }}</span><ToggleSwitch v-model="form.phoneConsent" data-testid="al-phone-consent" /></label>
        <div class="grid sm:grid-cols-2 gap-4 pt-1">
          <BaseSelect v-model="form.method" :label="$t('Qanday tekshirildi')" :options="opts(METHODS)" />
          <BaseInput v-model="form.note" :label="$t('Izoh (ichki)')" :placeholder="$t('Masalan: 12.11 da qo‘ng‘iroq qilindi')" />
        </div>
        <p v-if="!form.phoneConsent" class="text-xs text-muted">{{ $t('Rozilik bo‘lmasa telefon va Telegram talabalarga ko‘rsatilmaydi — arizalar Support’ga keladi.') }}</p>
      </section>

      <label v-if="!editing" :class="['flex items-center justify-between gap-3 rounded-2xl p-4 text-sm font-semibold', canPublish ? 'bg-brand-50' : 'bg-surface text-muted']">
        <span>{{ canPublish ? $t('Darhol tasdiqlab nashr qilish') : $t('Nashr qilish uchun egasi bilan bog‘lanib, roziligini belgilang') }}</span>
        <ToggleSwitch v-model="form.publish" :disabled="!canPublish" data-testid="al-publish" />
      </label>
    </form>
    <template #footer>
      <p v-if="!editing && !form.publish" class="text-xs text-muted text-center mb-2">{{ $t('E’lon “Tasdiqlashni kutmoqda” holatida saqlanadi — tekshiruvdan so‘ng ro‘yxatdan tasdiqlaysiz.') }}</p>
      <BaseButton block :loading="busy" data-testid="al-save" @click="save">{{ editing ? $t('Saqlash') : form.publish ? $t('Nashr qilish') : $t('Saqlash (tasdiqlashni kutadi)') }}</BaseButton>
    </template>
  </BaseModal>
</template>

<style scoped>
@reference "../../style.css";
.nego { @apply mt-2 inline-flex items-center h-8 px-3.5 rounded-full border text-[12.5px] font-semibold transition; }
</style>