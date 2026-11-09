<script setup>
import { t } from '@/i18n'
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ChevronLeft } from 'lucide-vue-next'
import AdForm from '@/components/ads/AdForm.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import LogoLoader from '@/components/brand/LogoLoader.vue'
import { adsStore, ensureAdsLoaded, adsApi } from '@/services/ads'
import { toast } from '@/stores/toast'
import { haptic } from '@/services/platform'

const route = useRoute()
const router = useRouter()
const id = route.params.id
const ready = ref(adsStore.loaded)
ensureAdsLoaded().then(() => (ready.value = true))
const ad = computed(() => (id ? adsStore.items.find((a) => a.id === id) : null))
const saving = ref(false)

async function save({ data, pending }) {
  saving.value = true
  try {
    if (id) await adsApi.update(id, data, pending)
    else await adsApi.create(data, pending)
    haptic.success()
    toast(id ? 'Reklama yangilandi' : 'Reklama qo‘shildi')
    router.push('/ads')
  } catch (e) {
    toast(e.message || t('Saqlab bo‘lmadi'), 'error')
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="max-w-6xl">
    <RouterLink to="/ads" class="inline-flex items-center gap-1 text-sm font-semibold text-muted hover:text-ink mb-3"><ChevronLeft class="size-4" />{{ $t('Reklamalar') }}</RouterLink>
    <h1 class="h-title mb-5">{{ id ? 'Reklamani tahrirlash' : 'Yangi reklama' }}</h1>
    <div v-if="!ready" class="py-16 grid place-items-center"><LogoLoader :text="$t('Yuklanmoqda…')" /></div>
    <div v-else-if="id && !ad" class="card p-6 text-center">
      <p class="font-bold">{{ $t('Reklama topilmadi') }}</p>
      <p class="text-sm text-muted mt-1">{{ $t('U o‘chirilgan bo‘lishi mumkin.') }}</p>
      <BaseButton class="mt-4" @click="router.push('/ads')">{{ $t('Ro‘yxatga qaytish') }}</BaseButton>
    </div>
    <AdForm v-else :key="id || 'new'" :ad="ad" :saving="saving" @submit="save" @cancel="router.push('/ads')" />
  </div>
</template>
