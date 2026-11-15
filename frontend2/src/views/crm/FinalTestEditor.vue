<script setup>
/**
 * Kursning yakuniy testi (Support): savollar, variantlar, to‘g‘ri javob, o‘tish foizi, urinishlar soni, nashr holati.
 * Talabalar barcha darslarni tugatgach topshiradi; o‘tganlarga QR-kodli PDF sertifikat beriladi.
 */
import { ref, watch, computed } from 'vue'
import { Plus, Trash2, ArrowUp, ArrowDown, Save, CheckCircle2, Eye, EyeOff } from 'lucide-vue-next'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import { crmApi } from '@/services/crm'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const props = defineProps({ courseId: { type: String, required: true } })
const form = ref(null)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const dirty = ref(false)
const blank = () => ({ q: '', options: ['', '', '', ''], answer: 0 })

async function load() {
  loading.value = true; error.value = ''
  try {
    const t0 = await crmApi.finalTest(props.courseId)
    form.value = { ...t0, questions: t0.questions.length ? t0.questions.map((q) => ({ ...q, options: [...q.options] })) : [blank()] }
    dirty.value = false
  } catch (e) { error.value = t(e.message) }
  loading.value = false
}
watch(() => props.courseId, load, { immediate: true })
watch(form, () => { if (!loading.value) dirty.value = true }, { deep: true })

const problems = computed(() => (form.value?.questions || []).map((q) => {
  const opts = q.options.filter((o) => o.trim())
  if (q.q.trim().length < 3) return t('Savol matnini kiriting')
  if (opts.length < 2) return t('Kamida 2 ta variant kiriting')
  if (!q.options[q.answer]?.trim()) return t('To‘g‘ri javob bo‘sh variant bo‘lmasin')
  return ''
}))
function add() { form.value.questions.push(blank()) }
function del(i) { form.value.questions.splice(i, 1) }
function mv(i, d) { const a = form.value.questions; const j = i + d; if (j >= 0 && j < a.length) [a[i], a[j]] = [a[j], a[i]] }
function addOpt(q) { if (q.options.length < 6) q.options.push('') }
function delOpt(q, oi) { if (q.options.length <= 2) return; q.options.splice(oi, 1); if (q.answer >= q.options.length) q.answer = 0; else if (q.answer > oi) q.answer-- }

async function save(status) {
  const f = form.value
  const target = status || f.status
  if (problems.value.some(Boolean)) { error.value = t('Savollardagi xatolarni tuzating'); return }
  if (target === 'published' && f.questions.length < 3) { error.value = t('Nashr qilish uchun kamida 3 ta savol kiriting'); return }
  error.value = ''; saving.value = true
  try {
    // bo‘sh variantlar olib tashlanadi, to‘g‘ri javob indeksi moslanadi
    const questions = f.questions.map((q) => {
      const keep = q.options.map((o, i) => ({ o: o.trim(), i })).filter((x) => x.o)
      return { q: q.q.trim(), options: keep.map((x) => x.o), answer: keep.findIndex((x) => x.i === q.answer) }
    })
    const saved = await crmApi.saveFinalTest(props.courseId, { status: target, passPercent: +f.passPercent, maxAttempts: +f.maxAttempts, questions })
    form.value = { ...saved, questions: saved.questions.map((q) => ({ ...q, options: [...q.options] })) }
    setTimeout(() => (dirty.value = false))
    toast(target === 'published' ? t('Yakuniy test nashr qilindi') : t('Yakuniy test saqlandi'))
  } catch (e) { error.value = t(e.message) } finally { saving.value = false }
}
</script>

<template>
  <div class="space-y-4" data-testid="final-test-editor">
    <p v-if="loading" class="text-sm text-muted">{{ $t('Yuklanmoqda...') }}</p>
    <template v-else-if="form">
      <section class="crm-card p-5 grid sm:grid-cols-[1fr_160px_160px_auto] gap-4 items-end">
        <div>
          <p class="font-bold flex items-center gap-2">{{ $t('Yakuniy test') }} <StatusBadge :status="form.status" /></p>
          <p class="text-xs text-muted mt-1">{{ $t('Talaba barcha darslarni tugatgach topshiradi. O‘tganlarga QR-kodli PDF sertifikat beriladi.') }}</p>
        </div>
        <BaseInput v-model="form.passPercent" type="number" min="10" max="100" :label="$t('O‘tish foizi')" data-testid="ft-pass" />
        <BaseInput v-model="form.maxAttempts" type="number" min="1" max="5" :label="$t('Urinishlar soni')" data-testid="ft-attempts" />
        <div class="flex gap-2">
          <BaseButton variant="soft" :icon="Save" :loading="saving" data-testid="ft-save" @click="save()">{{ $t('Saqlash') }}</BaseButton>
          <BaseButton v-if="form.status !== 'published'" :icon="Eye" :loading="saving" data-testid="ft-publish" @click="save('published')">{{ $t('Nashr qilish') }}</BaseButton>
          <BaseButton v-else variant="outline" :icon="EyeOff" :loading="saving" @click="save('draft')">{{ $t('Yashirish') }}</BaseButton>
        </div>
      </section>
      <p v-if="error" class="text-sm font-semibold text-danger" role="alert">{{ error }}</p>
      <p v-else-if="dirty" class="text-xs text-muted">{{ $t('Saqlanmagan o‘zgarishlar bor') }}</p>

      <ol class="space-y-3">
        <li v-for="(q, i) in form.questions" :key="i" class="crm-card p-4" :data-testid="`ft-q${i}`">
          <div class="flex items-start gap-2">
            <span class="size-8 rounded-lg bg-brand-50 text-brand-700 grid place-items-center font-bold text-sm shrink-0">{{ i + 1 }}</span>
            <BaseInput v-model="q.q" class="flex-1" :placeholder="$t('Savol matni')" :aria-label="$t('Savol matni')" />
            <button class="icon-btn" :disabled="i === 0" :aria-label="$t('Yuqoriga')" @click="mv(i, -1)"><ArrowUp class="size-4" /></button>
            <button class="icon-btn" :disabled="i === form.questions.length - 1" :aria-label="$t('Pastga')" @click="mv(i, 1)"><ArrowDown class="size-4" /></button>
            <button class="icon-btn icon-btn-danger" :aria-label="$t('O‘chirish')" @click="del(i)"><Trash2 class="size-4" /></button>
          </div>
          <div class="grid sm:grid-cols-2 gap-2 mt-3 sm:pl-10">
            <label v-for="(o, oi) in q.options" :key="oi" :class="['flex items-center gap-2 rounded-xl border px-2.5 py-1.5', q.answer === oi ? 'border-brand bg-brand-50' : 'border-line']">
              <input v-model="q.answer" type="radio" :value="oi" :name="`ans-${i}`" class="accent-[var(--color-brand)]" :title="$t('To‘g‘ri javob')" />
              <input v-model="q.options[oi]" class="flex-1 bg-transparent outline-none text-sm py-1" :placeholder="$t('{n}-variant', { n: oi + 1 })" />
              <button v-if="q.options.length > 2" class="text-muted hover:text-danger" :aria-label="$t('O‘chirish')" @click="delOpt(q, oi)"><Trash2 class="size-3.5" /></button>
            </label>
          </div>
          <div class="flex items-center gap-3 mt-2 sm:pl-10">
            <button v-if="q.options.length < 6" class="text-xs font-semibold text-brand-700 hover:underline" @click="addOpt(q)">+ {{ $t('Variant qo‘shish') }}</button>
            <span class="text-xs text-muted inline-flex items-center gap-1"><CheckCircle2 class="size-3.5 text-brand-600" />{{ $t('Doira — to‘g‘ri javob') }}</span>
            <span v-if="problems[i]" class="text-xs font-semibold text-danger ml-auto">{{ problems[i] }}</span>
          </div>
        </li>
      </ol>
      <BaseButton variant="soft" :icon="Plus" data-testid="ft-add" @click="add">{{ $t('Savol qo‘shish') }}</BaseButton>
    </template>
    <p v-else-if="error" class="text-sm text-danger">{{ error }}</p>
  </div>
</template>
