<script setup>
import { Phone, Send } from 'lucide-vue-next'
import { telLink, tgLink } from '@/utils/format'
import { openLink } from '@/services/telegram'
defineProps({ phone: String, telegram: String })
</script>
<template>
  <div class="flex flex-wrap gap-2">
    <a v-if="phone" :href="telLink(phone)" class="cbtn"><Phone class="size-4" />{{ phone }}</a>
    <button v-if="telegram" type="button" class="cbtn" @click="openLink(tgLink(telegram))"><Send class="size-4" />{{ telegram }}</button>
  </div>
</template>
<style scoped>
@reference "../../style.css";
.cbtn { @apply inline-flex items-center gap-2 h-10 px-3.5 rounded-xl bg-surface hover:bg-brand-50 hover:text-brand-700 text-sm font-semibold transition; }
</style>
