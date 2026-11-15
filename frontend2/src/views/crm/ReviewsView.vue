<script setup>
/** Baholar nazorati (Support): talaba ↔ ish beruvchi o‘zaro baholari; nojo‘ya izohli bahoni yashirish (o‘rtacha bahoga kirmaydi) */
import { ref, computed, watch } from 'vue'
import { EyeOff, Eye, Star } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import Pagination from '@/components/crm/Pagination.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { crmStore, ensureCrmLoaded, crmApi } from '@/services/crm'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))
const q = ref('')
const filter = ref('all')
const page = ref(1)
const PER = 15
watch([q, filter], () => (page.value = 1))
const chips = computed(() => [
  { value: 'all', label: `${t('Barchasi')} · ${crmStore.reviews.length}` },
  { value: 'low', label: `${t('Past baholar (1–2★)')} · ${crmStore.reviews.filter((r) => r.stars <= 2).length}` },
  { value: 'hidden', label: `${t('Yashirilgan')} · ${crmStore.reviews.filter((r) => r.hidden).length}` },
])
const list = computed(() => {
  const s = q.value.trim().toLowerCase()
  return crmStore.reviews
    .filter((r) => filter.value === 'all' || (filter.value === 'low' ? r.stars <= 2 : r.hidden))
    .filter((r) => !s || [r.fromName, r.toName, r.jobTitle, r.comment].some((v) => v?.toLowerCase().includes(s)))
})
const rows = computed(() => list.value.slice((page.value - 1) * PER, page.value * PER))
const avg = computed(() => { const v = crmStore.reviews.filter((r) => !r.hidden); return v.length ? (v.reduce((a, r) => a + r.stars, 0) / v.length).toFixed(1) : '—' })

const open = ref(false)
const target = ref(null)
const note = ref('')
const busy = ref(false)
function ask(r) { target.value = r; note.value = ''; open.value = true }
async function setHidden(r, hidden) {
  busy.value = true
  try { await crmApi.setReviewHidden(r.id, hidden, note.value.trim()); toast(hidden ? t('Baho yashirildi') : t('Baho qayta ko‘rsatildi')); open.value = false }
  catch (e) { toast(t(e.message), 'error') } finally { busy.value = false }
}
const ROLE = { student: 'Talaba', employer: 'Ish beruvchi' }
</script>

<template>
  <div>
    <PageHeader :title="$t('Baholar nazorati')" illu="trophy"><SearchBox v-model="q" :placeholder="$t('Ism, vakansiya yoki izoh…')" /></PageHeader>
    <div class="flex flex-wrap items-center gap-3 mb-4">
      <ChipGroup v-model="filter" :options="chips" size="sm" />
      <p class="ml-auto text-sm"><Star class="inline size-4 text-[#f5b301] fill-[#f5b301] -mt-0.5" /> {{ $t('O‘rtacha') }}: <b>{{ avg }}</b></p>
    </div>
    <div class="crm-card overflow-hidden">
      <SkeletonRows v-if="loading" :rows="6" :cols="5" />
      <EmptyState v-else-if="!list.length" :title="$t('Baholar yo‘q')" :text="$t('Ish yakunlangach talaba va ish beruvchi bir-birini baholaydi.')" illu="trophy" />
      <div v-else class="overflow-x-auto">
        <table class="crm-table min-w-[900px]" data-testid="crm-reviews-table">
          <thead><tr><th>{{ $t('Kim') }}</th><th>{{ $t('Kimga') }}</th><th>{{ $t('Baho') }}</th><th>{{ $t('Izoh') }}</th><th>{{ $t('Vakansiya') }}</th><th>{{ $t('Sana') }}</th><th class="text-right">{{ $t('Amallar') }}</th></tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r.id" :class="r.hidden && 'opacity-55'">
              <td><RouterLink :to="{ path: '/users', query: { id: r.fromId } }" class="font-semibold hover:text-brand-700">{{ r.fromName }}</RouterLink><p class="text-[11px] text-muted">{{ $t(ROLE[r.fromRole]) }}</p></td>
              <td><RouterLink :to="{ path: '/users', query: { id: r.toId } }" class="hover:text-brand-700">{{ r.toName }}</RouterLink></td>
              <td class="whitespace-nowrap font-bold text-[#a15c00]">{{ '★'.repeat(r.stars) }}<span class="text-[#d4d8dd]">{{ '★'.repeat(5 - r.stars) }}</span></td>
              <td class="max-w-[280px]"><p class="line-clamp-2 text-ink-2">{{ r.comment || '—' }}</p><p v-if="r.moderationNote" class="text-[11px] text-danger">{{ r.moderationNote }}</p></td>
              <td class="max-w-[200px]"><p class="truncate">{{ r.jobTitle }}</p></td>
              <td class="whitespace-nowrap text-muted">{{ $date(r.createdAt) }}</td>
              <td class="text-right">
                <BaseButton v-if="!r.hidden" size="sm" variant="danger" :icon="EyeOff" data-testid="review-hide" @click="ask(r)">{{ $t('Yashirish') }}</BaseButton>
                <BaseButton v-else size="sm" variant="soft" :icon="Eye" :loading="busy" @click="setHidden(r, false)">{{ $t('Ko‘rsatish') }}</BaseButton>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination v-model="page" :total="list.length" :per-page="PER" />
    </div>
    <BaseModal v-model="open" :title="$t('Bahoni yashirish')" :subtitle="target && `${target.fromName} → ${target.toName}`">
      <BaseInput v-model="note" :label="$t('Sabab (ixtiyoriy)')" :placeholder="$t('Masalan: haqoratli izoh')" />
      <p class="text-xs text-muted mt-2">{{ $t('Yashirilgan baho foydalanuvchi reytingiga kirmaydi.') }}</p>
      <template #footer><BaseButton block variant="danger" :loading="busy" data-testid="review-hide-confirm" @click="setHidden(target, true)">{{ $t('Yashirish') }}</BaseButton></template>
    </BaseModal>
  </div>
</template>
