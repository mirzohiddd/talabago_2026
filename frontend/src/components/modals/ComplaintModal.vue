<script setup>
/** Shikoyat → TalabaGo Support “Shikoyatlar” bo‘limiga tushadi */
import { ref, watch } from 'vue'
import { Flag } from 'lucide-vue-next'
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import ChipGroup from '@/components/ui/ChipGroup.vue'
import { useOptions } from '@/config/roles'
import { complaintsApi } from '@/services'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const open = defineModel({ type: Boolean })
const props = defineProps({ target: Object }) // { type: 'job'|'house'|'user', id, label }
const CATS = ['Firibgarlik', 'Noto‘g‘ri ma’lumot', 'To‘lov', 'Haqoratli xatti-harakat', 'Boshqa']
const catOpts = useOptions(CATS)
const category = ref(CATS[1])
const message = ref('')
const error = ref('')
const busy = ref(false)
watch(open, (v) => { if (v) { category.value = CATS[1]; message.value = ''; error.value = '' } })
async function send() {
  if (message.value.trim().length < 10) { error.value = t('Kamida {n} ta belgi', { n: 10 }); return }
  busy.value = true
  await complaintsApi.create({ target: props.target, category: category.value, message: message.value.trim() })
  busy.value = false; open.value = false
  toast(t('Shikoyat yuborildi. Moderatorlar ko‘rib chiqadi.'))
}
</script>
<template>
  <BaseModal v-model="open" :title="$t('Shikoyat qilish')" :subtitle="target?.label">
    <div class="space-y-4">
      <div><span class="label">{{ $t('Sabab') }}</span><ChipGroup v-model="category" :options="catOpts" size="sm" wrap /></div>
      <BaseTextarea v-model="message" :label="$t('Batafsil yozing')" :rows="4" :maxlength="500" :error="error" required />
    </div>
    <template #footer><BaseButton block :icon="Flag" :loading="busy" variant="dark" @click="send">{{ $t('Yuborish') }}</BaseButton></template>
  </BaseModal>
</template>
