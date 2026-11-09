<script setup>
/** "Ko‘rish" — reklamaning to‘liq ma’lumoti va carousel’dagi jonli ko‘rinishi */
import { t } from '@/i18n'
import { computed } from 'vue'
import { Pencil, ExternalLink, Eye, MousePointerClick, Percent, AlertTriangle } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ToggleSwitch from '@/components/ui/ToggleSwitch.vue'
import AdCarousel from './AdCarousel.vue'
import AdStatus from './AdStatus.vue'
import { AD_TYPES, placementLabels, adState } from '@/config/ads'
import { formatTashkent } from '@/utils/tashkentTime'
import { openLink } from '@/services/platform'

const open = defineModel({ type: Boolean })
const props = defineProps({ ad: Object, now: Number })
defineEmits(['edit', 'toggle'])

const ctr = (a) => (a.views ? ((a.clicks / a.views) * 100).toFixed(1) + '%' : '—')
const mb = (b) => (b ? (b / 1024 / 1024).toFixed(2) + ' MB' : null)
const fileInfo = computed(() => {
  const m = props.ad?.media
  if (!m) return '—'
  return [m.mime?.split('/')[1]?.toUpperCase().replace('JPEG', 'JPG'), mb(m.size), m.width && `${m.width}×${m.height}`, m.duration && `${Math.round(m.duration)} s`]
    .filter(Boolean).join(' · ')
})
const expired = computed(() => props.ad && adState(props.ad, props.now) === 'expired')
</script>

<template>
  <BaseModal v-model="open" :title="ad?.name">
    <div v-if="ad" class="space-y-4">
      <AdCarousel v-if="open" :items="[ad]" preview class="-mt-3" />

      <div class="grid grid-cols-3 gap-2">
        <div class="stat"><Eye class="size-4 text-brand-600" /><b>{{ ad.views.toLocaleString('ru-RU') }}</b><span>{{ $t('Ko‘rishlar') }}</span></div>
        <div class="stat"><MousePointerClick class="size-4 text-brand-600" /><b>{{ ad.clicks.toLocaleString('ru-RU') }}</b><span>{{ $t('Bosishlar') }}</span></div>
        <div class="stat"><Percent class="size-4 text-brand-600" /><b>{{ ctr(ad) }}</b><span>CTR</span></div>
      </div>

      <dl class="rounded-2xl border border-line divide-y divide-line text-[14px]">
        <div class="row"><dt>{{ $t('Holati') }}</dt><dd><AdStatus :ad="ad" :now="now" /></dd></div>
        <div class="row"><dt>{{ $t('Turi') }}</dt><dd>{{ AD_TYPES.find((t) => t.value === ad.type)?.label }} · <span class="text-muted">{{ fileInfo }}</span></dd></div>
        <div class="row"><dt>{{ $t('Boshlanish') }}</dt><dd class="tabular-nums">{{ formatTashkent(ad.startAt) }}</dd></div>
        <div class="row"><dt>{{ $t('Tugash') }}</dt><dd class="tabular-nums">{{ formatTashkent(ad.endAt) }}</dd></div>
        <div class="row"><dt>{{ $t('Joylashuv') }}</dt><dd class="flex flex-wrap gap-1 justify-end"><span v-for="p in placementLabels(ad.placements)" :key="p" class="h-6 px-2 rounded-md bg-surface text-xs font-semibold inline-flex items-center">{{ $t(p) }}</span></dd></div>
        <div class="row"><dt>{{ $t('Sarlavha') }}</dt><dd>{{ ad.title || '—' }}</dd></div>
        <div class="row"><dt>{{ $t('Tavsif') }}</dt><dd>{{ ad.description || '—' }}</dd></div>
        <div class="row"><dt>{{ $t('Havola') }}</dt><dd>
          <button v-if="ad.link" class="text-brand-600 font-semibold inline-flex items-center gap-1 break-all text-right hover:underline" @click="openLink(ad.link)">{{ ad.link }}<ExternalLink class="size-3.5 shrink-0" /></button>
          <span v-else>—</span>
        </dd></div>
      </dl>
      <p class="text-xs text-muted">{{ $t('Vaqtlar Toshkent vaqti (UTC+5) bo‘yicha. CRM preview ko‘rish/bosish statistikasiga qo‘shilmaydi.') }}</p>
    </div>
    <template v-if="ad" #footer>
      <div class="flex items-center gap-3 pb-1">
        <label class="flex items-center gap-2.5 text-sm font-semibold" :title="expired ? $t('Muddati tugagan — tugash sanasini o‘zgartiring') : ''">
          <ToggleSwitch :model-value="ad.enabled" :disabled="expired" :class="expired && 'opacity-40 pointer-events-none'" @update:model-value="$emit('toggle', ad, $event)" />
          {{ ad.enabled ? 'Aktiv' : 'Noaktiv' }}
        </label>
        <BaseButton class="ml-auto" :icon="Pencil" @click="$emit('edit', ad)">{{ $t('Tahrirlash') }}</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>

<style scoped>
@reference "../../style.css";
.stat { @apply rounded-2xl bg-surface p-3 flex flex-col gap-0.5; }
.stat b { @apply text-lg font-extrabold leading-tight tabular-nums; }
.stat span { @apply text-[11.5px] text-muted font-semibold; }
.row { @apply flex items-start justify-between gap-4 px-3.5 py-2.5; }
.row dt { @apply text-muted shrink-0; }
.row dd { @apply text-right font-medium min-w-0; }
</style>
