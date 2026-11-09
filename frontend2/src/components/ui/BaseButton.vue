<script setup>
import { Loader2 } from 'lucide-vue-next'
import { haptic } from '@/services/platform'

const props = defineProps({
  variant: { type: String, default: 'primary' }, // primary | outline | ghost | soft | danger
  size: { type: String, default: 'md' }, // sm | md | lg
  loading: Boolean,
  disabled: Boolean,
  block: Boolean,
  icon: { type: [Object, Function], default: null },
  iconRight: { type: [Object, Function], default: null },
  type: { type: String, default: 'button' },
})
const emit = defineEmits(['click'])

const variants = {
  primary: 'btn-shine bg-brand text-white hover:bg-brand-600 shadow-[var(--shadow-brand)] hover:shadow-[0_10px_24px_-8px_rgba(16,185,129,.7)] active:shadow-none',
  outline: 'border-[1.5px] border-brand text-brand-700 bg-white hover:bg-brand-50 hover:border-brand-600',
  ghost: 'text-ink-2 hover:bg-surface',
  soft: 'bg-surface text-ink hover:bg-line',
  dark: 'bg-ink text-white hover:bg-black',
  danger: 'bg-danger/10 text-danger hover:bg-danger/15',
}
const sizes = {
  sm: 'h-9 px-3.5 text-[13px] rounded-xl gap-1.5',
  md: 'h-11 px-5 text-[15px] rounded-xl gap-2',
  lg: 'h-13 px-6 text-base rounded-2xl gap-2',
}
function onClick(e) {
  if (props.loading || props.disabled) return
  haptic.tap()
  emit('click', e)
}
</script>

<template>
  <button
    :type="type"
    :disabled="disabled || loading"
    :class="[
      'group relative inline-flex items-center justify-center font-semibold select-none whitespace-nowrap',
      'transition-all duration-200 active:scale-[.97] disabled:opacity-50 disabled:cursor-not-allowed disabled:shadow-none',
      variants[variant], sizes[size], block && 'w-full',
    ]"
    @click="onClick"
  >
    <Loader2 v-if="loading" class="size-[18px] animate-spin" />
    <component :is="icon" v-else-if="icon" class="size-[18px]" />
    <span v-if="$slots.default" :class="loading && 'opacity-80'"><slot /></span>
    <component :is="iconRight" v-if="iconRight && !loading" class="size-[18px] transition-transform group-hover:translate-x-0.5" />
  </button>
</template>
