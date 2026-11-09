<script setup>
import { computed } from 'vue'
import { MapPin, Heart, BedDouble, Users, Images, CheckCircle2 } from 'lucide-vue-next'
import { priceText } from '@/utils/format'
import { HOUSE_TYPES, AUDIENCES } from '@/config/roles'
import { useMediaUrl } from '@/composables/useMediaUrl'

const props = defineProps({ house: { type: Object, required: true }, showSave: Boolean })
defineEmits(['open', 'save'])
const cover = useMediaUrl(() => props.house.photos?.[0])
const typeLabel = computed(() => HOUSE_TYPES.find((x) => x.value === props.house.type)?.label)
const audience = computed(() => AUDIENCES.find((x) => x.value === props.house.audience)?.label)
</script>

<template>
  <article class="card card-hover overflow-hidden cursor-pointer flex flex-col" tabindex="0" role="button" :aria-label="house.title" data-testid="house-card" @click="$emit('open', house)" @keydown.enter="$emit('open', house)">
    <div class="relative aspect-[16/10] bg-brand-50 overflow-hidden">
      <img v-if="cover" :src="cover" :alt="house.title" loading="lazy" class="size-full object-cover transition-transform duration-500 hover:scale-[1.04]" />
      <span class="absolute left-3 top-3 h-7 px-2.5 rounded-full bg-white/95 text-[12px] font-bold grid place-items-center">{{ $t(typeLabel) }}</span>
      <span v-if="house.photos?.length > 1" class="absolute left-3 bottom-3 h-6 px-2 rounded-full bg-ink/70 text-white text-[11px] font-semibold inline-flex items-center gap-1"><Images class="size-3.5" />{{ house.photos.length }}</span>
      <span v-if="house.occupancy === 'occupied' || !house.freeSpots" class="absolute right-3 bottom-3 h-6 px-2 rounded-full bg-ink text-white text-[11px] font-bold grid place-items-center">{{ $t('Band') }}</span>
      <button
        v-if="showSave" :class="['absolute right-3 top-3 size-9 grid place-items-center rounded-full bg-white/95 transition active:scale-90', house.saved ? 'text-brand-600' : 'text-ink-2']"
        :aria-label="house.saved ? $t('Saqlanganlardan olib tashlash') : $t('Saqlash')" :aria-pressed="house.saved" data-testid="save-house" @click.stop="$emit('save', house)"
      ><Heart class="size-[18px]" :fill="house.saved ? 'currentColor' : 'none'" /></button>
    </div>
    <div class="p-4 flex-1 flex flex-col">
      <p class="font-extrabold text-[18px] tracking-tight">{{ priceText(house) }}</p>
      <h3 class="font-semibold text-[15px] leading-snug mt-0.5 line-clamp-2">{{ $tc(house.title) }}</h3>
      <p class="mt-1.5 text-[13px] text-ink-2 flex items-center gap-1.5"><MapPin class="size-3.5 text-muted shrink-0" /><span class="truncate">{{ $t(house.district) }}, {{ $t(house.city) }}</span><span class="text-muted shrink-0">· {{ $ago(house.createdAt) }}</span></p>
      <div class="mt-3 pt-3 border-t border-line flex flex-wrap items-center gap-x-3 gap-y-1 text-[12.5px] text-ink-2 mt-auto">
        <span class="inline-flex items-center gap-1"><BedDouble class="size-4 text-muted" />{{ $t('{n} xona', { n: house.rooms }) }}</span>
        <span class="inline-flex items-center gap-1"><Users class="size-4 text-muted" />{{ $t('{n} ta bo‘sh joy', { n: house.freeSpots }) }}</span>
        <span class="text-muted">{{ $t(audience) }}</span>
        <span v-if="house.requested" class="ml-auto inline-flex items-center gap-1 font-semibold text-success"><CheckCircle2 class="size-4" />{{ $t('So‘rov yuborilgan') }}</span>
      </div>
    </div>
  </article>
</template>
