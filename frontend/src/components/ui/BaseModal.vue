<script setup>
import { watch, ref, nextTick, onBeforeUnmount, useId } from 'vue'
import { X } from 'lucide-vue-next'
/**
 * Mobil: pastdan chiqadigan bottom sheet (swipe-down bilan yopiladi).
 * Desktop: markazdagi modal yoki `drawer` bo‘lsa o‘ngdan chiqadigan panel.
 * Esc yopadi, fokus modal ichiga o‘tadi va yopilganda qaytadi.
 */
const open = defineModel({ type: Boolean, default: false })
const props = defineProps({ title: String, subtitle: String, wide: Boolean, drawer: Boolean })
const id = useId()
const panel = ref(null)
let lastFocus = null
let openCount = 0

function onKey(e) {
  if (e.key === 'Escape') { e.stopPropagation(); open.value = false }
  if (e.key === 'Tab' && panel.value) {
    const f = [...panel.value.querySelectorAll('button,[href],input,select,textarea,[tabindex]:not([tabindex="-1"])')].filter((x) => !x.disabled && x.offsetParent)
    if (!f.length) return
    if (e.shiftKey && document.activeElement === f[0]) { e.preventDefault(); f.at(-1).focus() }
    else if (!e.shiftKey && document.activeElement === f.at(-1)) { e.preventDefault(); f[0].focus() }
  }
}
watch(open, async (v) => {
  document.body.style.overflow = v ? 'hidden' : ''
  if (v) {
    lastFocus = document.activeElement
    window.addEventListener('keydown', onKey)
    await nextTick()
    panel.value?.querySelector('[data-autofocus]')?.focus() || panel.value?.focus()
  } else {
    window.removeEventListener('keydown', onKey)
    lastFocus?.focus?.()
  }
}, { immediate: true })
onBeforeUnmount(() => { document.body.style.overflow = ''; window.removeEventListener('keydown', onKey) })

// Mobil sheet: tutqichdan pastga tortib yopish
const dragY = ref(0)
let startY = null
const onStart = (e) => { startY = e.touches[0].clientY }
const onMove = (e) => { if (startY != null) dragY.value = Math.max(0, e.touches[0].clientY - startY) }
const onEnd = () => { if (dragY.value > 110) open.value = false; dragY.value = 0; startY = null }
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="open" class="fixed inset-0 z-50 bg-ink/40 backdrop-blur-[2px]" @click="open = false" />
    </Transition>
    <Transition :name="drawer ? 'sheet-drawer' : 'sheet'">
      <div
        v-if="open"
        :class="['fixed z-50 pointer-events-none inset-x-0 bottom-0',
          drawer ? 'lg:inset-y-0 lg:left-auto lg:right-0 lg:w-[min(560px,100vw)]' : 'sm:inset-0 sm:m-auto sm:h-fit', !drawer && (wide ? 'sm:max-w-2xl' : 'sm:max-w-lg')]"
      >
        <div
          ref="panel"
          role="dialog" aria-modal="true" :aria-labelledby="`${id}-t`" tabindex="-1"
          :class="['pointer-events-auto bg-white flex flex-col shadow-2xl outline-none max-h-[92dvh] rounded-t-[28px]',
            drawer ? 'lg:h-full lg:max-h-none lg:rounded-none lg:rounded-l-[28px]' : 'sm:rounded-3xl']"
          :style="dragY ? { transform: `translateY(${dragY}px)`, transition: 'none' } : null"
        >
          <div class="pt-2.5 pb-1 flex justify-center sm:hidden touch-none" @touchstart.passive="onStart" @touchmove.passive="onMove" @touchend="onEnd"><span class="h-1.5 w-10 rounded-full bg-line" /></div>
          <div class="flex items-start gap-3 px-5 sm:px-6 pt-2 sm:pt-5 pb-3">
            <div class="flex-1 min-w-0">
              <h3 :id="`${id}-t`" class="text-lg font-bold leading-tight">{{ title }}</h3>
              <p v-if="subtitle" class="text-sm text-muted mt-0.5">{{ subtitle }}</p>
            </div>
            <slot name="head" />
            <button class="size-9 grid place-items-center rounded-full bg-surface hover:bg-line transition active:scale-90 shrink-0" :aria-label="$t('Yopish')" @click="open = false">
              <X class="size-[18px]" />
            </button>
          </div>
          <div class="overflow-y-auto overscroll-contain px-5 sm:px-6 pb-4 flex-1"><slot /></div>
          <div v-if="$slots.footer" class="px-5 sm:px-6 pt-3 border-t border-line safe-bottom sm:pb-4"><slot name="footer" /></div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
