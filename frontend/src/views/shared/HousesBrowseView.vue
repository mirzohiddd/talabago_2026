<script setup>
/** Turar joy (talaba) va Uylar (uy egasi) — platformadagi barcha faol uy e’lonlari */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, reactive, computed, watch } from 'vue'
import { useRoute } from 'vue-router'
import { SlidersHorizontal, Heart } from 'lucide-vue-next'
import HouseCard from '@/components/cards/HouseCard.vue'
import HouseFilters from '@/components/filters/HouseFilters.vue'
import HouseDetailModal from '@/components/modals/HouseDetailModal.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import Pagination from '@/components/ui/Pagination.vue'
import { useList } from '@/composables/useList'
import { housingApi } from '@/services'
import { HOUSE_TYPES, useOptions } from '@/config/roles'
import { search, toast } from '@/stores/session'
import { t } from '@/i18n'

const route = useRoute()
const isStudent = computed(() => route.meta.role === 'student')
const filters = reactive({ type: 'all', price: 'all', rooms: 'all', audience: 'all', city: 'all', district: 'all', onlyFree: false, saved: route.query.saved === '1' })
const { items, loading, error, reload } = useList(housingApi.list, filters)
const typeOpts = useOptions(HOUSE_TYPES, { all: 'Barchasi' })
const activeCount = computed(() => ['price', 'rooms', 'audience', 'city', 'district'].filter((k) => filters[k] !== 'all').length + (filters.onlyFree ? 1 : 0) + (filters.saved ? 1 : 0))

const PER = 12
const page = ref(1)
watch([filters, () => search.query], () => (page.value = 1), { deep: true })
const rows = computed(() => items.value.slice((page.value - 1) * PER, page.value * PER))

const sheet = ref(false)
const current = ref(null)
const detail = ref(false)
function open(h) { current.value = h; detail.value = true }
function onChanged(h) {
  current.value = h
  const i = items.value.findIndex((x) => x.id === h.id)
  if (i >= 0) items.value[i] = h
}
async function toggleSave(h) {
  const saved = await housingApi.toggleSave(h.id)
  onChanged({ ...h, saved })
  toast(saved ? t('Saqlandi') : t('Saqlanganlardan olib tashlandi'))
  if (filters.saved && !saved) reload()
}
</script>

<template>
  <div class="page">
    <div class="lg:grid lg:grid-cols-[280px_minmax(0,1fr)] lg:gap-8 lg:items-start">
      <aside class="hidden lg:block sticky top-[88px]">
        <div class="card p-5"><h2 class="font-bold text-[17px] mb-4">{{ $t('Filtrlar') }}</h2><HouseFilters v-model="filters" :show-saved="isStudent" /></div>
      </aside>

      <section class="min-w-0">
        <PageIntro class="lg:hidden mb-3" />
        <div class="flex items-center gap-2 mb-3">
          <div class="mr-auto">
            <p class="text-sm text-muted" data-testid="result-count">{{ loading ? $t('Yuklanmoqda...') : $t('{n} ta e’lon', { n: items.length }) }}</p>
          </div>
          <button v-if="isStudent" :class="['lg:hidden h-10 px-3 rounded-xl inline-flex items-center gap-1.5 text-sm font-semibold transition', filters.saved ? 'bg-brand-50 text-brand-700' : 'bg-surface']" :aria-pressed="filters.saved" data-testid="saved-toggle" @click="filters.saved = !filters.saved">
            <Heart class="size-4" :fill="filters.saved ? 'currentColor' : 'none'" />{{ $t('Saqlangan') }}
          </button>
          <button class="lg:hidden relative h-10 px-3 rounded-xl bg-surface inline-flex items-center gap-1.5 text-sm font-semibold" data-testid="filter-btn" @click="sheet = true">
            <SlidersHorizontal class="size-4" />{{ $t('Filtrlar') }}
            <span v-if="activeCount" class="min-w-5 h-5 px-1 grid place-items-center rounded-full bg-brand text-white text-[11px] font-bold">{{ activeCount }}</span>
          </button>
        </div>
        <div class="lg:hidden mb-4"><ChipGroup v-model="filters.type" :options="typeOpts" size="sm" /></div>

        <div v-if="loading" class="grid sm:grid-cols-2 gap-3 lg:gap-4"><SkeletonCard :count="4" media class="contents" /></div>
        <ErrorState v-else-if="error" :message="error" @retry="reload" />
        <EmptyState v-else-if="!items.length" :title="filters.saved ? $t('Saqlangan uylar yo‘q') : $t('Hech narsa topilmadi')" :text="filters.saved ? $t('Yoqqan e’lonlarni ♡ tugmasi bilan saqlang.') : $t('Filtrlarni o‘zgartirib ko‘ring.')" illu="house" />
        <TransitionGroup v-else tag="div" name="list" class="grid sm:grid-cols-2 2xl:grid-cols-3 gap-3 lg:gap-4" data-testid="house-list">
          <HouseCard v-for="h in rows" :key="h.id" :house="h" :show-save="isStudent" @open="open" @save="toggleSave" />
        </TransitionGroup>
        <Pagination v-model="page" :total="items.length" :per-page="PER" />
      </section>
    </div>

    <BaseModal v-model="sheet" :title="$t('Filtrlar')">
      <HouseFilters v-model="filters" :show-saved="isStudent" />
      <template #footer><BaseButton block @click="sheet = false">{{ $t('{n} ta natijani ko‘rsatish', { n: items.length }) }}</BaseButton></template>
    </BaseModal>
    <HouseDetailModal v-model="detail" :house="current" :mode="isStudent ? 'student' : 'viewer'" @changed="onChanged" />
  </div>
</template>
