<script setup>
/** Uy e’loni formasi (yaratish va tahrirlash). TalabaGo Support tasdig‘idan keyin talabalarga ko‘rinadi. */
import { reactive, computed, ref } from 'vue'
import { Home, MapPin, Wallet, BedDouble, Users, Send } from 'lucide-vue-next'
import BaseInput from '@/components/ui/BaseInput.vue'
import PhoneInput from '@/components/ui/PhoneInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import PhotoUploader from './PhotoUploader.vue'
import { HOUSE_TYPES, AUDIENCES, AMENITIES, CITIES, CITY_LIST, HOUSE_PHOTOS, DISTRICT_CENTER, CITY_CENTER, useOptions } from '@/config/roles'
import { validate, rules } from '@/utils/validate'
import { normalizePhone } from '@/utils/format'
import { t } from '@/i18n'

const props = defineProps({ initial: Object, profile: Object, loading: Boolean, submitText: String })
const emit = defineEmits(['submit', 'cancel'])
const s = props.initial || {}
const form = reactive({
  title: s.title || '', type: s.type || 'flat', photos: [...(s.photos || [])], city: s.city || props.profile?.city || 'Toshkent', district: s.district || props.profile?.district || '',
  address: s.address || '', rooms: s.rooms || 1, area: s.area || '', price: s.price || '', audience: s.audience || 'any', capacity: s.capacity || 1, freeSpots: s.freeSpots ?? 1,
  amenities: [...(s.amenities || [])], description: s.description || '', phone: s.phone || props.profile?.phone || '', telegram: s.telegram || props.profile?.telegram || '',
})
const typeOpts = useOptions(HOUSE_TYPES)
const audOpts = useOptions(AUDIENCES)
const amenityOpts = useOptions(AMENITIES)
const cityOpts = useOptions(CITY_LIST)
const districtOpts = computed(() => (CITIES[form.city] || []).map((d) => ({ value: d, label: t(d) })))

const errors = ref({})
function submit() {
  errors.value = validate(form, {
    title: [rules.required, rules.min(4)], district: [rules.required], address: [rules.required], price: [rules.required, rules.positive],
    rooms: [rules.positive], capacity: [rules.positive], description: [rules.required, rules.min(20)], phone: [rules.phoneRequired], telegram: [rules.telegram],
    photos: [(v) => (v.length >= HOUSE_PHOTOS.min ? null : t('Kamida {n} ta rasm yuklang', { n: HOUSE_PHOTOS.min }))],
    freeSpots: [(v, f) => (+v >= 0 && +v <= +f.capacity ? null : t('Bo‘sh joylar umumiy joydan oshmasligi kerak'))],
  })
  if (Object.keys(errors.value).length) { document.querySelector('[aria-invalid="true"], [data-testid="add-photo"]')?.scrollIntoView({ behavior: 'smooth', block: 'center' }); return }
  const [lat, lng] = DISTRICT_CENTER[form.district] || CITY_CENTER[form.city] || [41.31, 69.28]
  emit('submit', {
    ...form, price: +form.price, rooms: +form.rooms, area: +form.area || null, capacity: +form.capacity, freeSpots: +form.freeSpots,
    phone: normalizePhone(form.phone), telegram: form.telegram ? '@' + form.telegram.replace(/^@/, '') : '',
    lat: s.lat || +(lat + (Math.random() - 0.5) * 0.008).toFixed(4), lng: s.lng || +(lng + (Math.random() - 0.5) * 0.008).toFixed(4),
  })
}
</script>

<template>
  <form class="space-y-6" novalidate data-testid="house-form" @submit.prevent="submit">
    <section class="space-y-4">
      <h3 class="sec">{{ $t('Asosiy ma’lumot') }}</h3>
      <BaseInput v-model="form.title" :label="$t('E’lon nomi')" :icon="Home" :placeholder="$t('Masalan, 2 xonali kvartira, metro yonida')" required :maxlength="80" :error="errors.title" data-testid="hf-title" />
      <div><span class="label">{{ $t('Uy turi') }} <span class="text-danger">*</span></span><ChipGroup v-model="form.type" :options="typeOpts" wrap /></div>
      <PhotoUploader v-model="form.photos" :error="errors.photos" />
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Manzil') }}</h3>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseSelect v-model="form.city" :label="$t('Shahar')" :icon="MapPin" :options="cityOpts" required @change="form.district = ''" />
        <BaseSelect v-model="form.district" :label="$t('Tuman')" :options="districtOpts" :placeholder="$t('Tanlang')" required :error="errors.district" data-testid="hf-district" />
      </div>
      <BaseInput v-model="form.address" :label="$t('Manzil')" :placeholder="$t('Mavze / ko‘cha (aniq uy raqami shart emas)')" required :error="errors.address" data-testid="hf-address" />
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Narx va joylar') }}</h3>
      <div class="grid grid-cols-2 sm:grid-cols-3 gap-4">
        <BaseInput v-model="form.price" type="number" inputmode="numeric" :label="$t('Oylik ijara narxi')" :icon="Wallet" :suffix="$t('so‘m')" required :error="errors.price" class="col-span-2 sm:col-span-1" data-testid="hf-price" />
        <BaseInput v-model="form.rooms" type="number" min="1" :label="$t('Xonalar soni')" :icon="BedDouble" :error="errors.rooms" />
        <BaseInput v-model="form.area" type="number" min="5" :label="$t('Maydon')" suffix="m²" />
        <BaseInput v-model="form.capacity" type="number" min="1" :label="$t('Jami joylar')" :icon="Users" :error="errors.capacity" />
        <BaseInput v-model="form.freeSpots" type="number" min="0" :label="$t('Bo‘sh joylar soni')" :error="errors.freeSpots" />
        <BaseSelect v-model="form.audience" :label="$t('Kimlar uchun')" :options="audOpts" />
      </div>
      <div><span class="label">{{ $t('Qulayliklar') }}</span><ChipGroup v-model="form.amenities" :options="amenityOpts" multiple wrap size="sm" /></div>
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Tavsif va bog‘lanish') }}</h3>
      <BaseTextarea v-model="form.description" :label="$t('Tavsif')" :placeholder="$t('Uy holati, kommunal to‘lovlar, transport, qoidalar...')" :rows="5" :maxlength="1000" required :error="errors.description" data-testid="hf-desc" />
      <div class="grid sm:grid-cols-2 gap-4">
        <PhoneInput v-model="form.phone" :label="$t('Telefon')" required :error="errors.phone" data-testid="lf-phone" />
        <BaseInput v-model="form.telegram" :label="$t('Telegram')" :icon="Send" placeholder="@username" :error="errors.telegram" />
      </div>
    </section>

    <p class="text-[13px] text-muted rounded-xl bg-surface px-3.5 py-3">{{ $t('E’lon TalabaGo Support tasdig‘idan keyin talabalarga ko‘rinadi. Odatda 1 ish kuni ichida.') }}</p>
    <div class="flex gap-2">
      <BaseButton v-if="initial" variant="soft" @click="emit('cancel')">{{ $t('Bekor qilish') }}</BaseButton>
      <BaseButton type="submit" block size="lg" class="flex-1" :loading="loading" data-testid="hf-submit">{{ submitText || $t('Tekshiruvga yuborish') }}</BaseButton>
    </div>
  </form>
</template>

<style scoped>
@reference "../../style.css";
.sec { @apply text-[13px] font-bold uppercase tracking-wider text-muted; }
</style>