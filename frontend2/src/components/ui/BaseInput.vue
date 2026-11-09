<script setup>
import { useId } from 'vue'
const model = defineModel({ type: [String, Number], default: '' })
defineProps({
  label: String,
  placeholder: String,
  type: { type: String, default: 'text' },
  icon: { type: [Object, Function], default: null },
  error: String,
  hint: String,
  suffix: String,
  inputmode: String,
  required: Boolean,
  maxlength: Number,
  autocomplete: String,
  name: String,
  min: [String, Number],
  max: [String, Number],
  list: String,
})
const id = useId()
</script>

<template>
  <div>
    <label v-if="label" :for="id" class="label">{{ label }}<span v-if="required" class="text-danger ml-0.5" aria-hidden="true">*</span></label>
    <div
      :class="[
        'flex items-center gap-2.5 h-12 px-3.5 rounded-xl border bg-white transition-all duration-200',
        'focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10',
        error ? 'border-danger' : 'border-line hover:border-[#dcdce0]',
      ]"
    >
      <component :is="icon" v-if="icon" class="size-[18px] text-muted shrink-0" />
      <input
        :id="id"
        v-model="model"
        :type="type" :name="name" :min="min" :max="max" :list="list"
        :placeholder="placeholder"
        :inputmode="inputmode"
        :maxlength="maxlength"
        :autocomplete="autocomplete"
        :required="required"
        :aria-invalid="!!error"
        :aria-describedby="error || hint ? `${id}-d` : undefined"
        class="flex-1 min-w-0 bg-transparent outline-none text-[15px] placeholder:text-muted"
      />
      <span v-if="suffix" class="text-sm text-muted shrink-0">{{ suffix }}</span>
    </div>
    <span v-if="error" :id="`${id}-d`" class="block mt-1 text-xs text-danger" role="alert">{{ error }}</span>
    <span v-else-if="hint" :id="`${id}-d`" class="block mt-1 text-xs text-muted">{{ hint }}</span>
  </div>
</template>
