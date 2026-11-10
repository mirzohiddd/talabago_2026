<script setup>
/** Ish beruvchi / uy egasining o‘z e’loni: holat, rad etish sababi va boshqaruv amallari */
import { ref } from 'vue'
import { Pencil, Copy, Trash2, Power, MoreHorizontal, Eye, Users, AlertTriangle, Clock, Briefcase } from 'lucide-vue-next'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import { useMediaUrl } from '@/composables/useMediaUrl'
const props = defineProps({ item: Object, kind: { type: String, default: 'job' }, subtitle: String, count: Number, countLabel: String })
const emit = defineEmits(['edit', 'duplicate', 'toggle', 'remove', 'occupancy', 'open'])
const menu = ref(false)
const cover = useMediaUrl(() => props.item.photos?.[0])
function act(e) { menu.value = false; emit(e, props.item) }
</script>

<template>
  <article class="card p-4" data-testid="my-listing" :data-status="item.status">
    <div class="flex gap-3">
      <img v-if="kind === 'house' && cover" :src="cover" alt="" loading="lazy" decoding="async" class="size-16 rounded-xl object-cover shrink-0" />
      <span v-else class="size-12 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center shrink-0"><Briefcase class="size-5" /></span>
      <div class="min-w-0 flex-1">
        <div class="flex items-start gap-2">
          <button class="font-bold leading-snug text-left flex-1 line-clamp-2 hover:text-brand-700" @click="emit('open', item)">{{ $tc(item.title) }}</button>
          <div class="relative">
            <button class="size-8 -mr-1 -mt-1 grid place-items-center rounded-full hover:bg-surface" :aria-label="$t('Amallar')" :aria-expanded="menu" data-testid="listing-menu" @click="menu = !menu"><MoreHorizontal class="size-5" /></button>
            <Transition name="pop">
              <div v-if="menu" class="absolute right-0 top-9 z-20 w-52 bg-white border border-line rounded-xl shadow-[var(--shadow-lift)] p-1.5" @mouseleave="menu = false">
                <button class="mi" data-testid="act-edit" @click="act('edit')"><Pencil class="size-4" />{{ $t('Tahrirlash') }}</button>
                <button class="mi" data-testid="act-duplicate" @click="act('duplicate')"><Copy class="size-4" />{{ $t('Nusxalash') }}</button>
                <button v-if="item.status !== 'rejected'" class="mi" data-testid="act-toggle" @click="act('toggle')"><Power class="size-4" />{{ item.status === 'closed' ? $t('Qayta ochish') : $t('Yopish') }}</button>
                <button class="mi text-danger!" data-testid="act-remove" @click="act('remove')"><Trash2 class="size-4" />{{ $t('O‘chirish') }}</button>
              </div>
            </Transition>
          </div>
        </div>
        <p class="text-[13px] text-muted mt-0.5 truncate">{{ subtitle }}</p>
        <div class="flex flex-wrap items-center gap-2 mt-2">
          <StatusBadge :status="item.status" />
          <span class="text-xs text-muted inline-flex items-center gap-1"><Eye class="size-3.5" />{{ item.views || 0 }}</span>
          <span class="text-xs text-muted inline-flex items-center gap-1"><Users class="size-3.5" />{{ count || 0 }} {{ countLabel }}</span>
          <span class="text-xs text-muted">· {{ $ago(item.updatedAt || item.createdAt) }}</span>
        </div>
      </div>
    </div>
    <p v-if="item.status === 'pending'" class="mt-3 flex gap-2 text-[12.5px] rounded-xl px-3 py-2 bg-warning/10 text-[#8a5300]"><Clock class="size-4 shrink-0 mt-px" />{{ $t('TalabaGo Support tasdig‘ini kutmoqda. Tasdiqlangach talabalarga ko‘rinadi.') }}</p>
    <div v-if="item.status === 'rejected'" class="mt-3 rounded-xl px-3 py-2.5 bg-danger/8 text-danger text-[12.5px]" data-testid="reject-reason">
      <p class="font-bold flex items-center gap-1.5"><AlertTriangle class="size-4" />{{ $t('Rad etish sababi') }}</p>
      <p class="mt-0.5 text-ink-2">{{ item.rejectReason || '—' }}</p>
      <button class="mt-1.5 font-semibold underline" @click="emit('edit', item)">{{ $t('Tuzatib qayta yuborish') }}</button>
    </div>
    <div v-if="kind === 'house' && item.status === 'active'" class="mt-3 pt-3 border-t border-line flex items-center gap-3">
      <span class="text-[13px] font-semibold flex-1">{{ $t('Uy holati') }}: <span :class="item.occupancy === 'free' ? 'text-success' : 'text-ink-2'">{{ item.occupancy === 'free' ? $t('Bo‘sh') : $t('Band') }}</span></span>
      <ToggleSwitch :model-value="item.occupancy === 'free'" :aria-label="$t('Bo‘sh / Band')" data-testid="occupancy" @update:model-value="emit('occupancy', item, $event ? 'free' : 'occupied')" />
    </div>
  </article>
</template>

<style scoped>
@reference "../../style.css";
.mi { @apply w-full flex items-center gap-2.5 h-10 px-2.5 rounded-lg text-sm font-medium hover:bg-surface text-ink; }
</style>