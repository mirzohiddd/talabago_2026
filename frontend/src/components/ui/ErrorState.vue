<script setup>
import { WifiOff, RotateCcw } from 'lucide-vue-next'
defineProps({ message: String })
defineEmits(['retry'])
</script>
<template>
  <div class="flex flex-col items-center text-center py-12 px-6" role="alert">
    <span class="size-14 rounded-2xl bg-danger/10 text-danger grid place-items-center"><WifiOff class="size-7" /></span>
    <h4 class="font-bold text-lg mt-4">{{ $t('Ma’lumotni yuklab bo‘lmadi') }}</h4>
    <p class="text-muted text-sm mt-1 max-w-xs">{{ message || $t('Internet aloqasini tekshirib, qayta urinib ko‘ring.') }}</p>
    <button class="mt-5 inline-flex items-center gap-2 h-10 px-4 rounded-xl bg-surface hover:bg-line text-sm font-semibold" @click="$emit('retry')"><RotateCcw class="size-4" />{{ $t('Qayta urinish') }}</button>
  </div>
</template>
