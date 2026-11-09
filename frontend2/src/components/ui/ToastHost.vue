<script setup>
import { CheckCircle2, AlertCircle } from 'lucide-vue-next'
import { toasts } from '@/stores/toast'
</script>
<template>
  <Teleport to="body">
    <div class="fixed top-3 inset-x-0 z-[60] flex flex-col items-center gap-2 pointer-events-none px-4">
      <TransitionGroup name="pop">
        <div v-for="t in toasts" :key="t.id" class="pointer-events-auto flex items-center gap-2.5 bg-ink text-white pl-3 pr-4 h-11 rounded-2xl shadow-xl text-sm font-medium">
          <CheckCircle2 v-if="t.type === 'success'" class="size-5 text-brand-600" />
          <AlertCircle v-else class="size-5 text-danger" />
          {{ t.text }}
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
