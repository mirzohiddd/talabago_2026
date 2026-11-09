<script setup>
/** Ish filtrlari: desktopda chap panelda, mobilda bottom sheet ichida */
import { computed } from 'vue'
import { RotateCcw, Heart } from 'lucide-vue-next'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import { JOB_TYPES, WORK_TIMES, SALARY_RANGES, CITIES, CITY_LIST, useOptions } from '@/config/roles'
import { t } from '@/i18n'

const f = defineModel({ type: Object, required: true })
defineProps({ showSaved: Boolean })
const typeOpts = useOptions(JOB_TYPES, { all: 'Barchasi' })
const formatOpts = computed(() => [{ value: 'all', label: t('Barchasi') }, { value: 'online', label: 'Online' }, { value: 'offline', label: 'Offline' }])
const cityOpts = useOptions(CITY_LIST, { all: 'Barcha shaharlar' })
const districtOpts = computed(() => [{ value: 'all', label: t('Barcha tumanlar') }, ...(CITIES[f.value.city] || []).map((d) => ({ value: d, label: t(d) }))])
const timeOpts = useOptions(WORK_TIMES, { all: 'Har qanday vaqt' })
const salaryOpts = useOptions(SALARY_RANGES)
function reset() { Object.assign(f.value, { type: 'all', format: 'all', city: 'all', district: 'all', workTime: 'all', salary: 'all', saved: false }) }
</script>

<template>
  <div class="space-y-5">
    <div><span class="label">{{ $t('Ish turi') }}</span><ChipGroup v-model="f.type" :options="typeOpts" size="sm" wrap /></div>
    <div><span class="label">{{ $t('Format') }}</span><SegmentedControl v-model="f.format" :options="formatOpts" /></div>
    <BaseSelect v-model="f.city" :label="$t('Shahar')" :options="cityOpts" @change="f.district = 'all'" />
    <BaseSelect v-model="f.district" :label="$t('Tuman')" :options="districtOpts" :disabled="f.city === 'all'" />
    <BaseSelect v-model="f.workTime" :label="$t('Ish vaqti')" :options="timeOpts" />
    <div>
      <BaseSelect v-model="f.salary" :label="$t('Maosh (oyiga taxminan)')" :options="salaryOpts" />
      <p class="text-[11.5px] text-muted mt-1">{{ $t('Soatlik ×160, kunlik ×22 bo‘yicha hisoblanadi') }}</p>
    </div>
    <label v-if="showSaved" class="flex items-center gap-3 cursor-pointer">
      <Heart class="size-[18px] text-brand-600" /><span class="flex-1 text-[15px] font-semibold">{{ $t('Faqat saqlanganlar') }}</span><ToggleSwitch v-model="f.saved" data-testid="only-saved" />
    </label>
    <button class="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink" @click="reset"><RotateCcw class="size-4" />{{ $t('Filtrlarni tozalash') }}</button>
  </div>
</template>
