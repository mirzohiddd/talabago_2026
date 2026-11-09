<script setup>
import { watch, onBeforeUnmount } from 'vue'
import { X } from 'lucide-vue-next'
const open = defineModel({ type: Boolean, default: false })
defineProps({ title: String, subtitle: String, width: { type: String, default: '480px' } })
const onKey = (e) => { if (e.key === 'Escape') open.value = false }
watch(open, (v) => (v ? window.addEventListener('keydown', onKey) : window.removeEventListener('keydown', onKey)))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>
<template>
  <Teleport to="body">
    <Transition name="fade"><div v-if="open" class="fixed inset-0 z-50 bg-ink/30 backdrop-blur-[2px]" @click="open = false" /></Transition>
    <Transition name="drawer">
      <aside v-if="open" class="fixed z-50 inset-y-0 right-0 w-full bg-white shadow-2xl flex flex-col" :style="{ maxWidth: width }" role="dialog" aria-modal="true">
        <header class="flex items-start gap-3 px-6 py-5 border-b border-line">
          <div class="flex-1 min-w-0"><h3 class="text-lg font-bold leading-tight">{{ title }}</h3><p v-if="subtitle" class="text-sm text-muted mt-0.5">{{ subtitle }}</p></div>
          <button class="size-9 grid place-items-center rounded-full bg-surface hover:bg-line transition" :aria-label="$t('Yopish')" @click="open = false"><X class="size-[18px]" /></button>
        </header>
        <div class="flex-1 overflow-y-auto px-6 py-5"><slot /></div>
        <footer v-if="$slots.footer" class="px-6 py-4 border-t border-line"><slot name="footer" /></footer>
      </aside>
    </Transition>
  </Teleport>
</template>
