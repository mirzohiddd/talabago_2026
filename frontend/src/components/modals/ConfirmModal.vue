<script setup>
import BaseModal from '@/components/ui/BaseModal.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
const open = defineModel({ type: Boolean })
defineProps({ title: String, text: String, confirmText: String, danger: Boolean, loading: Boolean })
defineEmits(['confirm'])
</script>
<template>
  <BaseModal v-model="open" :title="title">
    <p class="text-ink-2 text-[15px]">{{ text }}</p>
    <slot />
    <template #footer>
      <div class="flex gap-2">
        <BaseButton variant="soft" class="flex-1" @click="open = false">{{ $t('Bekor qilish') }}</BaseButton>
        <BaseButton :variant="danger ? 'danger' : 'primary'" class="flex-1" :loading="loading" data-testid="confirm-ok" @click="$emit('confirm')">{{ confirmText || $t('Tasdiqlash') }}</BaseButton>
      </div>
    </template>
  </BaseModal>
</template>
