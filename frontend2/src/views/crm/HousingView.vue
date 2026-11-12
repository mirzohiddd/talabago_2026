<script setup>
import { ref, computed } from 'vue'
import { MapPin, BedDouble, Users, Eye, Phone, Send, UserRound, CheckCircle2 } from 'lucide-vue-next'
import ListingAdmin from '@/components/crm/ListingAdmin.vue'
import MediaImg from '@/components/ui/MediaImg.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { HOUSE_TYPE_LABELS, AUDIENCES } from '@/config/status'
import { priceText } from '@/utils/format'
import { t } from '@/i18n'

const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))
const owner = (id) => crmStore.users.find((u) => u.id === id)
const reqCount = (id) => crmStore.requests.filter((r) => r.houseId === id && r.status !== 'withdrawn').length
const columns = computed(() => [
  { key: 'title', label: t('E’lon') },
  { key: 'owner', label: t('Uy egasi') },
  { key: 'type', label: t('Turi') },
  { key: 'price', label: t('Narx') },
  { key: 'district', label: t('Hudud') },
  { key: 'spots', label: t('Bo‘sh joylar') },
  { key: 'createdAt', label: t('Joylangan') },
])
const typeOpts = computed(() => Object.entries(HOUSE_TYPE_LABELS).map(([value, label]) => ({ value, label: t(label) })))
const editFields = computed(() => [
  { key: 'title', label: t('E’lon nomi'), wide: true }, { key: 'price', label: t('Oylik ijara narxi'), type: 'number' }, { key: 'freeSpots', label: t('Bo‘sh joylar soni'), type: 'number' },
  { key: 'address', label: t('Manzil'), wide: true }, { key: 'description', label: t('Tavsif'), textarea: true },
])
const REASONS = ['Rasmlar sifati past', 'Manzil to‘liq emas', 'Narx noto‘g‘ri ko‘rsatilgan', 'Qoidalarga zid mazmun']
const audience = (v) => AUDIENCES.find((a) => a.value === v)?.label
</script>

<template>
  <ListingAdmin illu="building"
    :title="$t('Turar joylar')" :items="crmStore.houses" :loading="loading" :columns="columns" testid="houses-table"
    filter-key="type" :filter-options="typeOpts" :search-fields="['title', 'district', 'address', 'city']"
    :api="crmApi.houses" :edit-fields="editFields" :reject-reasons="REASONS" kind="house" :add-label="$t('Turar joy qo‘shish')"
  >
    <template #title="{ item }">
      <div class="flex items-center gap-3"><MediaImg :src="item.photos?.[0]" class="size-11 rounded-lg object-cover bg-brand-50 shrink-0" /><p class="font-semibold max-w-[200px] truncate">{{ item.title }}</p></div>
    </template>
    <template #owner="{ item }"><span class="whitespace-nowrap">{{ item.ownerId ? fullName(owner(item.ownerId)) : (item.contactName || $t('Akkauntsiz (admin e’loni)')) }}</span></template>
    <template #type="{ item }"><span class="pill">{{ $t(HOUSE_TYPE_LABELS[item.type]) }}</span></template>
    <template #price="{ item }"><span class="font-semibold tabular-nums whitespace-nowrap">{{ priceText(item) }}</span></template>
    <template #district="{ item }">{{ $t(item.district) }}, {{ $t(item.city) }}</template>
    <template #spots="{ item }"><span class="tabular-nums">{{ item.freeSpots }} / {{ item.capacity }}</span> <span v-if="item.occupancy === 'occupied'" class="pill">{{ $t('Band') }}</span></template>
    <template #createdAt="{ item }"><span class="tabular-nums whitespace-nowrap">{{ $date(item.createdAt) }}</span></template>
    <template #detail="{ item }">
      <div class="grid grid-cols-3 gap-2" data-testid="house-photos">
        <MediaImg v-for="(p, i) in item.photos" :key="i" :src="p" :class="['w-full aspect-[4/3] object-cover rounded-xl bg-brand-50', i === 0 && 'col-span-3 aspect-[16/9]']" />
      </div>
      <div class="grid grid-cols-2 gap-2.5 text-sm">
        <div class="info font-bold!">{{ priceText(item) }}</div>
        <div class="info"><MapPin class="size-4 text-brand-600" />{{ $t(item.district) }}, {{ item.address }}</div>
        <div class="info"><BedDouble class="size-4 text-brand-600" />{{ $t('{n} xona', { n: item.rooms }) }} · {{ item.area || '—' }} m²</div>
        <div class="info"><Users class="size-4 text-brand-600" />{{ item.freeSpots }} / {{ item.capacity }} · {{ $t(audience(item.audience) || '') }}</div>
        <div class="info"><Eye class="size-4 text-brand-600" />{{ item.views }} · {{ $t('{n} ta so‘rov', { n: reqCount(item.id) }) }}</div>
      </div>
      <div class="flex flex-wrap gap-x-4 gap-y-1.5 text-sm"><span v-for="a in item.amenities" :key="a" class="inline-flex items-center gap-1 text-ink-2"><CheckCircle2 class="size-4 text-brand-600" />{{ $t(a) }}</span></div>
      <p class="text-[14.5px] text-ink-2 leading-relaxed whitespace-pre-line">{{ item.description }}</p>
      <div class="rounded-xl border border-line p-3.5 text-sm space-y-1.5">
        <p class="font-bold flex items-center gap-1.5"><UserRound class="size-4" />{{ $t('Uy egasi') }}</p>
        <RouterLink v-if="item.ownerId" :to="{ path: '/users', query: { id: item.ownerId } }" class="block font-semibold text-brand-700 hover:underline">{{ fullName(owner(item.ownerId)) }}</RouterLink>
        <p v-else class="font-semibold">{{ item.contactName || $t('Akkauntsiz (admin e’loni)') }}</p>
        <p class="flex items-center gap-1.5 text-ink-2"><Phone class="size-4" />{{ item.phone || '—' }} <Send class="size-4 ml-2" />{{ item.telegram || '—' }}</p>
      </div>
    </template>
  </ListingAdmin>
</template>

<style scoped>
@reference "../../style.css";
.info { @apply flex items-center gap-2 rounded-xl bg-surface px-3 py-2.5 font-medium; }
</style>