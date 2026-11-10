<script setup>
/**
 * Telefon maydoni: “+998” doimiy prefiks, foydalanuvchi faqat 9 ta raqam kiritadi → “90 123 45 67”.
 * v-model qiymati: “+998 90 123 45 67” (to‘liq bo‘lmasa ham “+998 90 12” kabi — validatsiya formada).
 * Nusxa qo‘yilganda (+998901234567, 998 90 123 45 67, 90-123-45-67) ham to‘g‘ri ajratiladi.
 */
import { computed, ref, useId } from 'vue'
import { Phone } from 'lucide-vue-next'
import { PHONE_PREFIX, phoneDigits, formatLocal, phoneProblem, PHONE_MESSAGES } from '@shared/phone'
import { t } from '@/i18n'

const model = defineModel({ type: String, default: '' })
const props = defineProps({
  label: String,
  error: String,
  hint: String,
  required: Boolean,
  autocomplete: { type: String, default: 'tel-national' },
  validateOnBlur: { type: Boolean, default: true },
})
const id = useId()
const touched = ref(false)
const local = computed(() => formatLocal(phoneDigits(model.value)))
const shown = computed(() => {
  if (props.error) return props.error
  if (!props.validateOnBlur || !touched.value) return ''
  const p = phoneProblem(model.value)
  if (!p || (p === 'empty' && !props.required)) return ''
  return t(PHONE_MESSAGES[p])
})

function set(raw) {
  const d = phoneDigits(raw)
  model.value = d ? `${PHONE_PREFIX} ${formatLocal(d)}` : ''
}
function onInput(e) {
  const el = e.target
  const before = el.value
  const caretDigits = before.slice(0, el.selectionStart ?? before.length).replace(/\D/g, '').length
  set(before)
  el.value = local.value // 10-raqam yoki harf kiritilsa ham qiymat bir xil qolsa — DOM’ni majburan tozalash
  // kursorni raqamlar bo‘yicha saqlash (bo‘sh joylar qo‘shilganda sakramasin)
  requestAnimationFrame(() => {
    const v = el.value
    let pos = 0
    let seen = 0
    while (pos < v.length && seen < caretDigits) { if (/\d/.test(v[pos])) seen++; pos++ }
    try { el.setSelectionRange(pos, pos) } catch { /* */ }
  })
}
function onPaste(e) {
  const text = e.clipboardData?.getData('text') || ''
  if (!text) return
  e.preventDefault()
  set(text)
  e.target.value = local.value
}
function onKeydown(e) {
  // faqat raqam va boshqaruv tugmalari
  if (e.ctrlKey || e.metaKey || e.altKey || e.key.length > 1) return
  if (!/\d/.test(e.key)) e.preventDefault()
}
</script>

<template>
  <div>
    <label v-if="label" :for="id" class="label">{{ label }}<span v-if="required" class="text-danger ml-0.5" aria-hidden="true">*</span></label>
    <div
      :class="[
        'flex items-center gap-2.5 h-12 px-3.5 rounded-xl border bg-white transition-all duration-200',
        'focus-within:border-brand focus-within:ring-4 focus-within:ring-brand/10',
        shown ? 'border-danger' : 'border-line hover:border-[#dcdce0]',
      ]"
    >
      <Phone class="size-[18px] text-muted shrink-0" />
      <span class="text-[15px] font-semibold text-ink shrink-0 select-none" data-testid="phone-prefix">{{ PHONE_PREFIX }}</span>
      <input
        :id="id"
        :value="local"
        type="tel"
        inputmode="numeric"
        :autocomplete="autocomplete"
        placeholder="90 123 45 67"
        :required="required"
        :aria-invalid="!!shown"
        :aria-describedby="shown || hint ? `${id}-d` : undefined"
        class="flex-1 min-w-0 bg-transparent outline-none text-[15px] tracking-wide placeholder:text-muted placeholder:tracking-normal"
        @input="onInput"
        @paste="onPaste"
        @keydown="onKeydown"
        @blur="touched = true"
      />
    </div>
    <span v-if="shown" :id="`${id}-d`" class="block mt-1 text-xs text-danger" role="alert">{{ shown }}</span>
    <span v-else-if="hint" :id="`${id}-d`" class="block mt-1 text-xs text-muted">{{ hint }}</span>
  </div>
</template>

