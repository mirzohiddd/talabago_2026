<script setup>
/** Ish yakunlangach baholash oynasi (talaba → ish beruvchi yoki ish beruvchi → talaba). Bir marta; server takroriyni bloklaydi. */
import { ref, watch } from 'vue'
import { Send } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import StarRating from './StarRating.vue'
import { reviewsApi } from '@/services'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const open = defineModel({ type: Boolean, default: false })
const props = defineProps({ applicationId: String, name: String, subtitle: String })
const emit = defineEmits(['done'])
const stars = ref(0)
const comment = ref('')
const err = ref('')
const busy = ref(false)
watch(open, (v) => { if (v) { stars.value = 0; comment.value = ''; err.value = '' } })
const HINT = { 1: 'Juda yomon', 2: 'Yomon', 3: 'O‘rtacha', 4: 'Yaxshi', 5: 'A’lo' }
async function send() {
  if (!stars.value) { err.value = t('Yulduzlardan birini tanlang'); return }
  busy.value = true; err.value = ''
  try {
    const r = await reviewsApi.create(props.applicationId, { stars: stars.value, comment: comment.value.trim() })
    toast(t('Rahmat! Bahoyingiz saqlandi'))
    open.value = false
    emit('done', r)
  } catch (e) { err.value = t(e.message) } finally { busy.value = false }
}
</script>

<template>
  <BaseModal v-model="open" :title="$t('Baholash')" :subtitle="subtitle">
    <div class="space-y-4" data-testid="review-modal">
      <p class="text-[15px] text-ink-2">{{ $t('{name} bilan ishlash qanday bo‘ldi?', { name }) }}</p>
      <div class="flex flex-col items-center gap-1.5 py-2">
        <StarRating v-model="stars" :size="34" />
        <span class="h-5 text-sm font-semibold text-muted">{{ stars ? $t(HINT[stars]) : '' }}</span>
      </div>
      <BaseTextarea v-model="comment" :label="$t('Izoh (ixtiyoriy)')" :rows="3" :maxlength="500" :placeholder="$t('Nima yoqdi yoki nimani yaxshilash kerak?')" data-testid="review-comment" />
      <p v-if="err" class="text-sm text-danger font-semibold" role="alert">{{ err }}</p>
      <p class="text-xs text-muted">{{ $t('Baho bir marta qo‘yiladi va keyin o‘zgartirilmaydi. Haqoratli izohlarni Support yashiradi.') }}</p>
    </div>
    <template #footer><BaseButton block :icon="Send" :loading="busy" data-testid="review-send" @click="send">{{ $t('Bahoni yuborish') }}</BaseButton></template>
  </BaseModal>
</template>
