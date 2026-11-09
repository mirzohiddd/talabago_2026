<script setup>
import { useId } from 'vue'
import { ChevronDown } from 'lucide-vue-next'
const model = defineModel({ type: [String, Number], default: '' })
defineProps({
  label: String,
  options: { type: Array, required: true }, // [{value,label}] yoki ['a','b']
  placeholder: String,
  icon: { type: [Object, Function], default: null },
  error: String,
  required: Boolean,
})
const id = useId()
const val = (o) => (typeof o === 'object' ? o.value : o)
const lab = (o) => (typeof o === 'object' ? o.label : o)
</script>

<template>
  <div>
    <label v-if="label" :for="id" class="label">{{ label }}<span v-if="required" class="text-danger ml-0.5" aria-hidden="true">*</span></label>
    <div
      :class="[
        'relative flex items-center gap-2.5 h-12 px-3.5 rounded-xl border bg-white transition-all',
        'focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10',
        error ? 'border-danger' : 'border-line',
      ]"
    >
      <component :is="icon" v-if="icon" class="size-[18px] text-muted shrink-0" />
      <select :id="id" v-model="model" :aria-invalid="!!error" :class="['flex-1 min-w-0 appearance-none bg-transparent outline-none text-[15px] pr-6 truncate', (model === '' || model == null) && 'text-muted']">
        <option v-if="placeholder" value="" disabled>{{ placeholder }}</option>
        <option v-for="o in options" :key="val(o)" :value="val(o)">{{ lab(o) }}</option>
      </select>
      <ChevronDown class="size-4 text-muted absolute right-3.5 pointer-events-none" />
    </div>
    <span v-if="error" class="block mt-1 text-xs text-danger" role="alert">{{ error }}</span>
  </div>
</template>
