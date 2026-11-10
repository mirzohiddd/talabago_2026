<script setup>
/**
 * Rolga qarab profil maydonlari — ro‘yxatdan o‘tishda va Sozlamalarda bir xil komponent.
 * Majburiy: ism, telefon (+ ish beruvchi uchun kompaniya). Qolganlarini keyin to‘ldirish mumkin.
 */
import { computed, ref } from 'vue'
import { User, Send, Building2, MapPin, GraduationCap, Calendar, Plus, X } from 'lucide-vue-next'
import BaseInput from '@/components/ui/BaseInput.vue'
import PhoneInput from '@/components/ui/PhoneInput.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import { CITIES, CITY_LIST, SHIFTS, UNIVERSITIES, INDUSTRIES, SKILLS, useOptions } from '@/config/roles'
import { t } from '@/i18n'

const form = defineModel({ type: Object, required: true })
const props = defineProps({ role: String, errors: { type: Object, default: () => ({}) }, compact: Boolean, requireLastName: Boolean, sections: { type: Array, default: () => ['personal', 'study', 'skills', 'company', 'location', 'contact'] } })

const cityOpts = useOptions(CITY_LIST)
const districtOpts = computed(() => (CITIES[form.value.city] || []).map((d) => ({ value: d, label: t(d) })))
const shiftOpts = useOptions(SHIFTS)
const industryOpts = useOptions(INDUSTRIES)
const has = (s) => props.sections.includes(s)

const skillDraft = ref('')
function toggleSkill(s) {
  const list = form.value.skills || []
  form.value.skills = list.includes(s) ? list.filter((x) => x !== s) : [...list, s]
}
function addSkill() {
  const s = skillDraft.value.trim()
  if (s && !(form.value.skills || []).includes(s)) form.value.skills = [...(form.value.skills || []), s]
  skillDraft.value = ''
}
function onCity() { if (!(CITIES[form.value.city] || []).includes(form.value.district)) form.value.district = '' }
</script>

<template>
  <div class="space-y-4">
    <div v-if="has('personal')" class="grid sm:grid-cols-2 gap-4">
      <BaseInput v-model="form.firstName" :label="$t('Ism')" :icon="User" required autocomplete="given-name" :error="errors.firstName" data-testid="f-first" />
      <BaseInput v-model="form.lastName" :label="$t('Familiya')" :required="requireLastName" autocomplete="family-name" :error="errors.lastName" data-testid="f-last" />
      <BaseInput v-if="role === 'student'" v-model="form.birthDate" type="date" :label="$t('Tug‘ilgan sana')" :icon="Calendar" max="2012-12-31" :error="errors.birthDate" />
      <PhoneInput v-model="form.phone" :label="$t('Telefon')" required :error="errors.phone" data-testid="f-phone" />
    </div>

    <template v-if="role === 'student' && has('study')">
      <datalist id="unis"><option v-for="u in UNIVERSITIES" :key="u" :value="u" /></datalist>
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.university" :label="$t('O‘quv yurti')" :icon="GraduationCap" list="unis" :placeholder="$t('Masalan, TATU')" />
        <BaseInput v-model="form.faculty" :label="$t('Yo‘nalish')" :placeholder="$t('Masalan, Dasturiy injiniring')" />
        <BaseSelect v-model="form.shift" :label="$t('O‘qish smenasi')" :options="shiftOpts" :placeholder="$t('Tanlang')" />
        <BaseSelect v-model.number="form.course" :label="$t('Kurs')" :options="[1, 2, 3, 4, 5, 6].map((n) => ({ value: n, label: $t('{n}-kurs', { n }) }))" :placeholder="$t('Tanlang')" />
      </div>
    </template>

    <template v-if="role === 'employer' && has('company')">
      <div class="grid sm:grid-cols-2 gap-4">
        <BaseInput v-model="form.company" :label="$t('Kompaniya nomi')" :icon="Building2" required :error="errors.company" data-testid="f-company" />
        <BaseSelect v-model="form.industry" :label="$t('Faoliyat sohasi')" :options="industryOpts" :placeholder="$t('Tanlang')" />
        <BaseInput v-if="!compact" v-model="form.position" :label="$t('Mas’ul shaxs lavozimi')" :placeholder="$t('Masalan, HR menejer')" />
      </div>
      <BaseInput v-model="form.address" :label="$t('Kompaniya manzili')" :icon="MapPin" :placeholder="$t('Shahar, tuman, ko‘cha')" />
    </template>

    <div v-if="role !== 'employer' && has('location')" class="grid sm:grid-cols-2 gap-4">
      <BaseSelect v-model="form.city" :label="$t('Shahar')" :options="cityOpts" :placeholder="$t('Tanlang')" @change="onCity" />
      <BaseSelect v-model="form.district" :label="$t('Tuman')" :options="districtOpts" :placeholder="$t('Tanlang')" />
    </div>

    <PhoneInput v-if="has('contact') && !has('personal')" v-model="form.phone" :label="$t('Telefon')" required :error="errors.phone" />
    <BaseInput v-if="role !== 'student' && has('contact')" v-model="form.telegram" :label="$t('Telegram')" :icon="Send" placeholder="@username" :error="errors.telegram" autocomplete="off" />

    <div v-if="role === 'student' && has('skills')">
      <span class="label">{{ $t('Ko‘nikmalar') }}</span>
      <div class="flex flex-wrap gap-2">
        <button v-for="s in [...new Set([...SKILLS, ...(form.skills || [])])]" :key="s" type="button"
          :class="['h-9 px-3.5 rounded-full text-[13px] font-semibold border transition-all active:scale-95', (form.skills || []).includes(s) ? 'bg-brand border-brand text-white' : 'bg-white border-line text-ink-2 hover:border-brand-200']"
          :aria-pressed="(form.skills || []).includes(s)" @click="toggleSkill(s)">
          {{ $t(s) }}<X v-if="(form.skills || []).includes(s) && !SKILLS.includes(s)" class="inline size-3.5 ml-1 -mr-1" />
        </button>
      </div>
      <form class="flex gap-2 mt-2" @submit.prevent="addSkill">
        <input v-model="skillDraft" :placeholder="$t('Boshqa ko‘nikma qo‘shish')" class="flex-1 min-w-0 h-10 px-3 rounded-xl border border-line outline-none focus:border-brand text-sm" />
        <button type="submit" class="h-10 px-3 rounded-xl bg-surface hover:bg-line text-sm font-semibold inline-flex items-center gap-1" :disabled="!skillDraft.trim()"><Plus class="size-4" />{{ $t('Qo‘shish') }}</button>
      </form>
    </div>
    <BaseTextarea v-if="role === 'student' && has('about') && !compact" v-model="form.about" :label="$t('O‘zim haqimda')" :rows="3" :maxlength="300" />
    <BaseInput v-if="role === 'student' && has('contact')" v-model="form.telegram" :label="$t('Telegram')" :icon="Send" placeholder="@username" :error="errors.telegram" />
  </div>
</template>