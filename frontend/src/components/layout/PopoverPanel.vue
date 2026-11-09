<script setup>
/** Navbar’dan chiqadigan kichik dropdown (bildirishnomalar, profil). Esc bilan yopiladi. */
import { watch, onBeforeUnmount } from 'vue'
const open = defineModel({ type: Boolean, default: false })
defineProps({ title: String })
const onKey = (e) => { if (e.key === 'Escape') open.value = false }
watch(open, (v) => (v ? window.addEventListener('keydown', onKey) : window.removeEventListener('keydown', onKey)))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-40 bg-ink/10 lg:bg-transparent" @click="open = false" />
    </Transition>
    <Transition name="pop">
      <div
        v-if="open" role="dialog" :aria-label="title"
        class="fixed z-50 top-[calc(64px+var(--safe-top))] right-3 left-3 sm:left-auto sm:w-[360px] lg:right-6 bg-white rounded-2xl border border-line shadow-[var(--shadow-lift)] overflow-hidden"
      >
        <div v-if="title || $slots.action" class="flex items-center justify-between px-4 pt-3.5 pb-2">
          <h4 class="font-bold">{{ title }}</h4>
          <slot name="action" />
        </div>
        <slot />
      </div>
    </Transition>
  </Teleport>
</template>
