<script setup>
import { computed } from 'vue'
import { RotateCcw, Heart, DoorOpen } from 'lucide-vue-next'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseSelect from '@/components/ui/BaseSelect.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import { HOUSE_TYPES, PRICE_RANGES, ROOM_FILTERS, AUDIENCES, CITIES, CITY_LIST, useOptions } from '@/config/roles'
import { t } from '@/i18n'

const f = defineModel({ type: Object, required: true })
defineProps({ showSaved: Boolean })
const typeOpts = useOptions(HOUSE_TYPES, { all: 'Barchasi' })
const priceOpts = useOptions(PRICE_RANGES)
const roomOpts = useOptions(ROOM_FILTERS)
const audOpts = useOptions(AUDIENCES.filter((a) => a.value !== 'any'), { all: 'Hammasi' })
const cityOpts = useOptions(CITY_LIST, { all: 'Barcha shaharlar' })
const districtOpts = computed(() => [{ value: 'all', label: t('Barcha tumanlar') }, ...(CITIES[f.value.city] || []).map((d) => ({ value: d, label: t(d) }))])
function reset() { Object.assign(f.value, { type: 'all', price: 'all', rooms: 'all', audience: 'all', city: 'all', district: 'all', onlyFree: false, saved: false }) }
</script>

<template>
  <div class="space-y-5">
    <div><span class="label">{{ $t('Uy turi') }}</span><ChipGroup v-model="f.type" :options="typeOpts" size="sm" wrap /></div>
    <BaseSelect v-model="f.price" :label="$t('Oylik narx')" :options="priceOpts" />
    <div><span class="label">{{ $t('Xonalar') }}</span><ChipGroup v-model="f.rooms" :options="roomOpts" size="sm" wrap /></div>
    <BaseSelect v-model="f.city" :label="$t('Shahar')" :options="cityOpts" @change="f.district = 'all'" />
    <BaseSelect v-model="f.district" :label="$t('Hudud (tuman)')" :options="districtOpts" />
    <BaseSelect v-model="f.audience" :label="$t('Kimlar uchun')" :options="audOpts" />
    <label class="flex items-center gap-3 cursor-pointer"><DoorOpen class="size-[18px] text-brand-600" /><span class="flex-1 text-[15px] font-semibold">{{ $t('Faqat bo‘sh joyi borlar') }}</span><ToggleSwitch v-model="f.onlyFree" /></label>
    <label v-if="showSaved" class="flex items-center gap-3 cursor-pointer"><Heart class="size-[18px] text-brand-600" /><span class="flex-1 text-[15px] font-semibold">{{ $t('Faqat saqlanganlar') }}</span><ToggleSwitch v-model="f.saved" data-testid="only-saved" /></label>
    <button class="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink" @click="reset"><RotateCcw class="size-4" />{{ $t('Filtrlarni tozalash') }}</button>
  </div>
</template>
