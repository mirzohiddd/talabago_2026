<script setup>
import { useId } from 'vue'
const model = defineModel({ type: String, default: '' })
defineProps({ label: String, placeholder: String, rows: { type: Number, default: 4 }, error: String, maxlength: Number, required: Boolean })
const id = useId()
</script>

<template>
  <div>
    <label v-if="label" :for="id" class="label">{{ label }}<span v-if="required" class="text-danger ml-0.5" aria-hidden="true">*</span></label>
    <textarea
      :id="id"
      v-model="model"
      :rows="rows"
      :placeholder="placeholder"
      :maxlength="maxlength"
      :aria-invalid="!!error"
      :class="[
        'w-full px-3.5 py-3 rounded-xl border bg-white outline-none resize-none text-[15px] placeholder:text-muted transition-all',
        'focus:border-brand focus:ring-4 focus:ring-brand/10',
        error ? 'border-danger' : 'border-line',
      ]"
    />
    <div v-if="error || maxlength" class="flex justify-between mt-1 text-xs">
      <span class="text-danger" role="alert">{{ error }}</span>
      <span v-if="maxlength" class="text-muted tabular-nums">{{ (model || '').length }}/{{ maxlength }}</span>
    </div>
  </div>
</template>
