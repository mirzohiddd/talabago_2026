<script setup>
/** Vakansiya formasi (yaratish va tahrirlash). Yuborilgach TalabaGo Support tasdig‘iga tushadi. */
import { reactive, computed, ref } from 'vue'
import { Briefcase, Building2, Wallet, CalendarClock, Phone, Send, MapPin } from 'lucide-vue-next'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import { JOB_TYPES, SALARY_PERIODS, DEFAULT_PERIOD, WORK_TIMES, JOB_CATEGORIES, CITIES, CITY_LIST, useOptions } from '@/config/roles'
import { validate, rules } from '@/utils/validate'
import { normalizePhone } from '@/utils/format'
import { t } from '@/i18n'

const props = defineProps({ initial: Object, profile: Object, loading: Boolean, submitText: String })
const emit = defineEmits(['submit', 'cancel'])
const src = props.initial || {}
const form = reactive({
  title: src.title || '', company: src.company || props.profile?.company || '', city: src.city || 'Toshkent', district: src.district || '',
  format: src.format || 'offline', type: src.type || 'hourly', salary: src.salary || '', salaryPeriod: src.salaryPeriod || 'hour',
  schedule: src.schedule || '', workTime: src.workTime || 'flexible', category: src.category || '', description: src.description || '',
  requirementsText: (src.requirements || []).join('\n'), phone: src.phone || props.profile?.phone || '', telegram: src.telegram || props.profile?.telegram || '',
})
const typeOpts = useOptions(JOB_TYPES)
const periodOpts = useOptions(SALARY_PERIODS)
const timeOpts = useOptions(WORK_TIMES)
const catOpts = useOptions(JOB_CATEGORIES)
const cityOpts = useOptions(CITY_LIST)
const districtOpts = computed(() => (CITIES[form.city] || []).map((d) => ({ value: d, label: t(d) })))
const formatOpts = computed(() => [{ value: 'offline', label: 'Offline' }, { value: 'online', label: 'Online' }])
function onType(v) { form.salaryPeriod = DEFAULT_PERIOD[v] }

const errors = ref({})
function submit() {
  errors.value = validate(form, {
    title: [rules.required, rules.min(4)], company: [rules.required], salary: [rules.required, rules.positive],
    schedule: [rules.required], description: [rules.required, rules.min(30)], phone: [rules.required, rules.phone], telegram: [rules.telegram],
    ...(form.format === 'offline' ? { district: [rules.required] } : {}),
  })
  if (Object.keys(errors.value).length) {
    document.querySelector('[aria-invalid="true"]')?.focus()
    return
  }
  const { requirementsText, ...rest } = form
  emit('submit', {
    ...rest, salary: +form.salary, phone: normalizePhone(form.phone), telegram: form.telegram ? '@' + form.telegram.replace(/^@/, '') : '',
    district: form.format === 'online' ? null : form.district,
    requirements: requirementsText.split('\n').map((s) => s.trim()).filter(Boolean),
  })
}
</script>

<template>
  <form class="space-y-6" novalidate data-testid="job-form" @submit.prevent="submit">
    <section class="space-y-4">
      <h3 class="sec">{{ $t('Asosiy ma’lumot') }}</h3>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.title" :label="$t('Ish nomi')" :icon="Briefcase" :placeholder="$t('Masalan, Kafe xodimi')" required :maxlength="80" :error="errors.title" data-testid="jf-title" />
        <BaseInput v-model="form.company" :label="$t('Kompaniya')" :icon="Building2" required :error="errors.company" />
        <BaseSelect v-model="form.category" :label="$t('Soha')" :options="catOpts" :placeholder="$t('Tanlang')" />
        <div><span class="label">{{ $t('Format') }} <span class="text-danger">*</span></span><SegmentedControl v-model="form.format" :options="formatOpts" /></div>
      </div>
      <div v-if="form.format === 'offline'" class="grid sm:grid-cols-2 gap-4">
        <BaseSelect v-model="form.city" :label="$t('Shahar')" :icon="MapPin" :options="cityOpts" required @change="form.district = ''" />
        <BaseSelect v-model="form.district" :label="$t('Tuman')" :options="districtOpts" :placeholder="$t('Tanlang')" required :error="errors.district" data-testid="jf-district" />
      </div>
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Ish turi va maosh') }}</h3>
      <div><span class="label">{{ $t('Ish turi') }} <span class="text-danger">*</span></span><ChipGroup v-model="form.type" :options="typeOpts" wrap @update:model-value="onType" /></div>
      <div class="grid grid-cols-[1fr_auto] sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.salary" type="number" inputmode="numeric" min="0" :label="$t('Maosh')" :icon="Wallet" :suffix="$t('so‘m')" required :error="errors.salary" data-testid="jf-salary" />
        <BaseSelect v-model="form.salaryPeriod" :label="$t('To‘lov davri')" :options="periodOpts" required />
      </div>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.schedule" :label="$t('Ish jadvali')" :icon="CalendarClock" :placeholder="$t('Masalan, Dush–Juma, 18:00–23:00')" required :error="errors.schedule" data-testid="jf-schedule" />
        <BaseSelect v-model="form.workTime" :label="$t('Ish vaqti')" :options="timeOpts" />
      </div>
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Tavsif va talablar') }}</h3>
      <BaseTextarea v-model="form.description" :label="$t('Tavsif')" :placeholder="$t('Vazifalar, sharoitlar, nima uchun talabalarga mos...')" :rows="5" :maxlength="1000" required :error="errors.description" data-testid="jf-desc" />
      <BaseTextarea v-model="form.requirementsText" :label="$t('Talablar (har biri yangi qatordan)')" :placeholder="$t('Xushmuomalalik\nHaftasiga kamida 3 kun')" :rows="3" />
    </section>

    <section class="space-y-4">
      <h3 class="sec">{{ $t('Bog‘lanish') }}</h3>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.phone" type="tel" :label="$t('Telefon')" :icon="Phone" required :error="errors.phone" />
        <BaseInput v-model="form.telegram" :label="$t('Telegram')" :icon="Send" placeholder="@username" :error="errors.telegram" />
      </div>
    </section>

    <p class="text-[13px] text-muted rounded-xl bg-surface px-3.5 py-3">{{ $t('E’lon TalabaGo Support tasdig‘idan keyin talabalarga ko‘rinadi. Odatda 1 ish kuni ichida.') }}</p>
    <div class="flex gap-2">
      <BaseButton v-if="initial" variant="soft" @click="emit('cancel')">{{ $t('Bekor qilish') }}</BaseButton>
      <BaseButton type="submit" block size="lg" class="flex-1" :loading="loading" data-testid="jf-submit">{{ submitText || $t('Tekshiruvga yuborish') }}</BaseButton>
    </div>
  </form>
</template>

<style scoped>
@reference "../../style.css";
.sec { @apply text-[13px] font-bold uppercase tracking-wider text-muted; }
</style>
