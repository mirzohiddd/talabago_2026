<script setup>
/** Kurs sertifikatlari va yakuniy test urinishlari (Support): bekor qilish / tiklash, talabaga qayta topshirishga ruxsat */
import { ref, computed, watch } from 'vue'
import { Award, ListChecks, ExternalLink, RotateCcw, Ban, CheckCircle2 } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SearchBox from '@/components/crm/SearchBox.vue'
import Pagination from '@/components/crm/Pagination.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { crmStore, ensureCrmLoaded, crmApi } from '@/services/crm'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))
const tab = ref('certs')
const tabs = computed(() => [
  { value: 'certs', label: `${t('Sertifikatlar')} · ${crmStore.certificates.length}`, icon: Award },
  { value: 'attempts', label: `${t('Test urinishlari')} · ${crmStore.exams.length}`, icon: ListChecks },
])
const q = ref('')
const page = ref(1)
const PER = 15
watch([tab, q], () => (page.value = 1))
const match = (...v) => { const s = q.value.trim().toLowerCase(); return !s || v.some((x) => String(x || '').toLowerCase().includes(s)) }
const certs = computed(() => crmStore.certificates.filter((c) => match(c.fullName, c.code, c.courseTitle)))
const attempts = computed(() => crmStore.exams.filter((e) => match(e.userName, e.courseTitle)))
const list = computed(() => (tab.value === 'certs' ? certs.value : attempts.value))
const rows = computed(() => list.value.slice((page.value - 1) * PER, page.value * PER))
const kpi = computed(() => {
  const ex = crmStore.exams.filter((e) => !e.voided)
  return { certs: crmStore.certificates.filter((c) => c.status === 'valid').length, attempts: ex.length,
    passRate: ex.length ? Math.round(ex.filter((e) => e.passed).length / ex.length * 100) : null }
})

// bekor qilish / tiklash
const rvOpen = ref(false)
const rvTarget = ref(null)
const reason = ref('')
const busy = ref(false)
function askRevoke(c) { rvTarget.value = c; reason.value = ''; rvOpen.value = true }
async function setStatus(c, status) {
  busy.value = true
  try { await crmApi.setCertificateStatus(c.id, status, reason.value.trim()); toast(status === 'revoked' ? t('Sertifikat bekor qilindi') : t('Sertifikat tiklandi')); rvOpen.value = false }
  catch (e) { toast(t(e.message), 'error') } finally { busy.value = false }
}
// qayta topshirishga ruxsat
const rsOpen = ref(false)
const rsTarget = ref(null)
const canReset = (e) => !e.passed && !e.voided && !crmStore.certificates.some((c) => c.userId === e.userId && c.courseId === e.courseId && c.status === 'valid')
async function reset() {
  busy.value = true
  try { const r = await crmApi.resetExam(rsTarget.value.userId, rsTarget.value.courseId); toast(t('{n} ta urinish bekor qilindi — talaba qayta topshira oladi', { n: r.reset })); rsOpen.value = false }
  catch (e) { toast(t(e.message), 'error') } finally { busy.value = false }
}
const openUrl = (u) => window.open(u, '_blank', 'noopener')
</script>

<template>
  <div>
    <PageHeader :title="$t('Sertifikatlar va testlar')" illu="trophy"><SearchBox v-model="q" :placeholder="$t('Talaba, kurs yoki raqam…')" /></PageHeader>
    <div class="grid grid-cols-3 gap-3 mb-4">
      <div class="crm-card p-4"><p class="text-xs text-muted font-semibold">{{ $t('Amaldagi sertifikatlar') }}</p><p class="text-2xl font-extrabold tabular-nums">{{ kpi.certs }}</p></div>
      <div class="crm-card p-4"><p class="text-xs text-muted font-semibold">{{ $t('Test urinishlari') }}</p><p class="text-2xl font-extrabold tabular-nums">{{ kpi.attempts }}</p></div>
      <div class="crm-card p-4"><p class="text-xs text-muted font-semibold">{{ $t('O‘tish ulushi') }}</p><p class="text-2xl font-extrabold tabular-nums">{{ kpi.passRate === null ? '—' : `${kpi.passRate}%` }}</p></div>
    </div>
    <SegmentedControl v-model="tab" :options="tabs" class="mb-4 max-w-lg" />
    <div class="crm-card overflow-hidden">
      <SkeletonRows v-if="loading" :rows="6" :cols="5" />
      <EmptyState v-else-if="!list.length" :title="tab === 'certs' ? $t('Hali sertifikat berilmagan') : $t('Hali test topshirilmagan')" :text="$t('Talabalar yakuniy testni topshirganda shu yerda ko‘rinadi.')" illu="trophy" />
      <div v-else class="overflow-x-auto">
        <table v-if="tab === 'certs'" class="crm-table min-w-[880px]" data-testid="certs-table">
          <thead><tr><th>{{ $t('Talaba') }}</th><th>{{ $t('Kurs') }}</th><th>{{ $t('Natija') }}</th><th>{{ $t('Raqam') }}</th><th>{{ $t('Sana') }}</th><th>{{ $t('Holat') }}</th><th class="text-right">{{ $t('Amallar') }}</th></tr></thead>
          <tbody>
            <tr v-for="c in rows" :key="c.id">
              <td><RouterLink :to="{ path: '/users', query: { id: c.userId } }" class="font-semibold hover:text-brand-700">{{ c.fullName }}</RouterLink></td>
              <td>{{ $t(c.courseTitle) }}</td>
              <td class="tabular-nums font-bold">{{ c.percent }}%</td>
              <td class="font-mono text-xs">{{ c.code }}</td>
              <td class="whitespace-nowrap">{{ $date(c.issuedAt) }}</td>
              <td><StatusBadge :status="c.status" /><p v-if="c.revokeReason" class="text-[11px] text-muted mt-0.5">{{ c.revokeReason }}</p></td>
              <td class="text-right whitespace-nowrap">
                <button class="icon-btn" :title="$t('Tekshirish sahifasi')" :aria-label="$t('Tekshirish sahifasi')" @click="openUrl(c.verifyUrl)"><ExternalLink class="size-4" /></button>
                <BaseButton v-if="c.status === 'valid'" size="sm" variant="danger" :icon="Ban" data-testid="cert-revoke" @click="askRevoke(c)">{{ $t('Bekor qilish') }}</BaseButton>
                <BaseButton v-else size="sm" variant="soft" :icon="CheckCircle2" :loading="busy" @click="setStatus(c, 'valid')">{{ $t('Tiklash') }}</BaseButton>
              </td>
            </tr>
          </tbody>
        </table>
        <table v-else class="crm-table min-w-[820px]" data-testid="attempts-table">
          <thead><tr><th>{{ $t('Talaba') }}</th><th>{{ $t('Kurs') }}</th><th>{{ $t('Urinish') }}</th><th>{{ $t('Natija') }}</th><th>{{ $t('Sana') }}</th><th class="text-right">{{ $t('Amallar') }}</th></tr></thead>
          <tbody>
            <tr v-for="e in rows" :key="e.id" :class="e.voided && 'opacity-55'">
              <td class="font-semibold">{{ e.userName }}</td>
              <td>{{ $t(e.courseTitle) }}</td>
              <td class="tabular-nums">#{{ e.attemptNo }}<span v-if="e.voided" class="ml-1.5 text-[11px] text-muted">({{ $t('bekor qilingan') }})</span></td>
              <td><span :class="['font-bold tabular-nums', e.passed ? 'text-brand-700' : 'text-danger']">{{ e.score }}/{{ e.total }} · {{ e.percent }}%</span></td>
              <td class="whitespace-nowrap text-muted">{{ $dateTime(e.createdAt) }}</td>
              <td class="text-right"><BaseButton v-if="canReset(e)" size="sm" variant="soft" :icon="RotateCcw" data-testid="exam-reset" @click="rsTarget = e; rsOpen = true">{{ $t('Qayta topshirishga ruxsat') }}</BaseButton></td>
            </tr>
          </tbody>
        </table>
      </div>
      <Pagination v-model="page" :total="list.length" :per-page="PER" />
    </div>

    <BaseModal v-model="rvOpen" :title="$t('Sertifikatni bekor qilish')" :subtitle="rvTarget && `${rvTarget.fullName} · ${rvTarget.code}`">
      <BaseInput v-model="reason" :label="$t('Sabab (ixtiyoriy)')" :placeholder="$t('Masalan: test qoidalari buzilgan')" />
      <p class="text-xs text-muted mt-2">{{ $t('QR-kod orqali tekshirilganda “bekor qilingan” deb ko‘rinadi.') }}</p>
      <template #footer><BaseButton block variant="danger" :loading="busy" data-testid="cert-revoke-confirm" @click="setStatus(rvTarget, 'revoked')">{{ $t('Bekor qilish') }}</BaseButton></template>
    </BaseModal>
    <ConfirmModal v-model="rsOpen" :title="$t('Qayta topshirishga ruxsat berasizmi?')" :text="$t('{name} uchun “{course}” bo‘yicha urinishlar bekor qilinadi (tarix saqlanadi).', { name: rsTarget?.userName, course: rsTarget?.courseTitle })" :confirm-text="$t('Ruxsat berish')" :loading="busy" @confirm="reset" />
  </div>
</template>
