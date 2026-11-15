<script setup>
/**
 * Kursning yakuniy testi: barcha darslar tugagach ochiladi, jami 2 urinish (Support o‘zgartirishi mumkin).
 * Javoblar serverda tekshiriladi. O‘tilgach — QR-kodli PDF sertifikat (ommaviy havola orqali ochiladi).
 */
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Award, Download, ShieldCheck, Lock, RotateCcw, Send, XCircle, CheckCircle2 } from 'lucide-vue-next'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import { coursesApi } from '@/services'
import { openLink, haptic } from '@/services/telegram'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const courseId = route.params.courseId
const exam = ref(null)
const loading = ref(true)
const error = ref(null)
const answers = ref([])
const started = ref(false)
const result = ref(null)
const busy = ref(false)
const confirm = ref(false)

async function load() {
  loading.value = true; error.value = null
  try {
    exam.value = await coursesApi.exam(courseId)
    answers.value = exam.value.questions.map(() => null)
  } catch (e) { error.value = t(e.message) }
  loading.value = false
}
onMounted(load)

const answered = computed(() => answers.value.filter((a) => a !== null).length)
const total = computed(() => exam.value?.questions.length || 0)
const cert = computed(() => result.value?.certificate || exam.value?.certificate)
function start() { answers.value = exam.value.questions.map(() => null); result.value = null; started.value = true; window.scrollTo({ top: 0 }) }
function choose(qi, oi) { haptic.tap(); answers.value[qi] = oi }
function askSubmit() {
  if (answered.value < total.value) { toast(t('Barcha savollarga javob bering'), 'error'); document.querySelector('[data-unanswered]')?.scrollIntoView({ block: 'center', behavior: 'smooth' }); return }
  confirm.value = true
}
async function submit() {
  busy.value = true
  try {
    result.value = await coursesApi.submitExam(courseId, answers.value)
    confirm.value = false; started.value = false
    haptic.success?.()
    await load()
    window.scrollTo({ top: 0, behavior: 'smooth' })
  } catch (e) { toast(t(e.message), 'error'); confirm.value = false } finally { busy.value = false }
}
const openPdf = () => openLink(coursesApi.certificatePdfUrl(cert.value.code))
const openVerify = () => openLink(coursesApi.certificatePageUrl(cert.value.code))
</script>

<template>
  <div class="page-narrow">
    <button class="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink mb-3" @click="router.push(`/student/courses/${courseId}`)"><ArrowLeft class="size-4" />{{ $t('Kursga qaytish') }}</button>
    <SkeletonCard v-if="loading" :count="3" />
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <template v-else-if="exam">
      <div class="flex items-center gap-4 mb-4">
        <RoundIllu kind="trophy" :size="72" :float="false" />
        <div class="min-w-0">
          <p class="text-xs font-bold uppercase tracking-wide text-brand-700">{{ $t('Yakuniy test') }}</p>
          <h1 class="text-[22px] font-extrabold tracking-tight leading-tight">{{ $t(exam.courseTitle) }}</h1>
          <p class="text-sm text-muted">{{ $t('{n} ta savol', { n: total }) }} · {{ $t('o‘tish chegarasi {p}%', { p: exam.passPercent }) }} · {{ $t('jami {n} urinish', { n: exam.maxAttempts }) }}</p>
        </div>
      </div>

      <!-- Natija (oxirgi topshirish) -->
      <div v-if="result && !started" :class="['card p-4 mb-4 flex items-center gap-3 border-2', result.attempt.passed ? 'border-brand' : 'border-danger/40']" data-testid="exam-result">
        <component :is="result.attempt.passed ? CheckCircle2 : XCircle" :class="['size-9 shrink-0', result.attempt.passed ? 'text-brand-600' : 'text-danger']" />
        <div class="min-w-0">
          <p class="font-extrabold text-lg">{{ result.attempt.passed ? $t('Tabriklaymiz! Testdan o‘tdingiz') : $t('Afsuski, bu safar o‘ta olmadingiz') }}</p>
          <p class="text-sm text-muted">{{ $t('Natija: {s} / {t} ({p}%)', { s: result.attempt.score, t: result.attempt.total, p: result.attempt.percent }) }}<template v-if="!result.attempt.passed"> · {{ $t('Qolgan urinishlar: {n}', { n: result.attemptsLeft }) }}</template></p>
        </div>
      </div>

      <!-- Sertifikat -->
      <section v-if="cert && !started" class="card p-5 mb-4 relative overflow-hidden" data-testid="certificate">
        <div class="absolute -right-6 -top-6 size-28 rounded-full bg-brand-50" />
        <div class="relative flex items-start gap-4">
          <span class="size-14 rounded-2xl bg-brand text-white grid place-items-center shrink-0 shadow-[var(--shadow-brand)]"><Award class="size-7" /></span>
          <div class="min-w-0 flex-1">
            <h2 class="font-extrabold text-lg">{{ $t('Sertifikatingiz tayyor') }}</h2>
            <p class="text-sm text-ink-2">{{ cert.fullName }} · {{ $t(cert.courseTitle) }} · <b>{{ cert.percent }}%</b></p>
            <p class="text-xs text-muted mt-1">{{ $t('Raqam') }}: <span class="font-mono font-semibold text-ink">{{ cert.code }}</span> · {{ $date(cert.issuedAt) }}</p>
            <p v-if="cert.status === 'revoked'" class="mt-2 text-sm font-semibold text-danger">{{ $t('Sertifikat Support tomonidan bekor qilingan') }}</p>
          </div>
        </div>
        <div class="relative grid sm:grid-cols-2 gap-2 mt-4">
          <BaseButton :icon="Download" data-testid="cert-pdf" @click="openPdf">{{ $t('PDF sertifikat') }}</BaseButton>
          <BaseButton variant="outline" :icon="ShieldCheck" @click="openVerify">{{ $t('Haqiqiyligini tekshirish') }}</BaseButton>
        </div>
        <p class="relative text-xs text-muted mt-3">{{ $t('Sertifikatdagi QR-kodni skanerlagan har kim uning haqiqiyligini tekshira oladi.') }}</p>
      </section>

      <!-- Boshlash kartasi -->
      <section v-if="!started && !exam.passed" class="card p-5" data-testid="exam-start">
        <template v-if="!exam.eligible">
          <div class="flex items-center gap-3"><Lock class="size-6 text-muted" /><p class="font-bold">{{ $t('Test barcha darslar tugagach ochiladi') }}</p></div>
          <p class="text-sm text-muted mt-2">{{ $t('{a} / {b} dars tugatildi', { a: exam.lessonsDone, b: exam.lessonsTotal }) }}</p>
          <div class="h-2 rounded-full bg-surface overflow-hidden mt-3"><div class="h-full bg-brand rounded-full" :style="{ width: `${exam.lessonsTotal ? Math.round(exam.lessonsDone / exam.lessonsTotal * 100) : 0}%` }" /></div>
          <BaseButton class="mt-4" variant="soft" @click="router.push(`/student/courses/${courseId}`)">{{ $t('Darslarni davom ettirish') }}</BaseButton>
        </template>
        <template v-else-if="exam.attemptsLeft > 0">
          <ul class="text-sm text-ink-2 space-y-1.5 mb-4 list-disc pl-5">
            <li>{{ $t('Har bir savolga bitta javob tanlang.') }}</li>
            <li>{{ $t('Kamida {p}% to‘g‘ri javob — sertifikat beriladi.', { p: exam.passPercent }) }}</li>
            <li>{{ $t('Qolgan urinishlar: {n} / {m}', { n: exam.attemptsLeft, m: exam.maxAttempts }) }}</li>
          </ul>
          <BaseButton block :icon="exam.attempts.length ? RotateCcw : Send" data-testid="exam-begin" @click="start">{{ exam.attempts.length ? $t('Qayta topshirish') : $t('Testni boshlash') }}</BaseButton>
        </template>
        <template v-else>
          <p class="font-bold text-danger">{{ $t('Urinishlar tugadi') }}</p>
          <p class="text-sm text-muted mt-1">{{ $t('Qayta topshirish uchun “Texnik yordam” orqali Support’ga murojaat qiling.') }}</p>
          <BaseButton class="mt-3" variant="soft" @click="router.push('/student/support')">{{ $t('Support’ga yozish') }}</BaseButton>
        </template>
        <div v-if="exam.attempts.length" class="mt-4 pt-4 border-t border-line">
          <h3 class="text-sm font-bold mb-2">{{ $t('Urinishlar tarixi') }}</h3>
          <ul class="space-y-1.5 text-sm">
            <li v-for="(a, i) in exam.attempts" :key="a.id" class="flex items-center gap-2">
              <span class="text-muted w-20">{{ $t('{n}-urinish', { n: i + 1 }) }}</span>
              <b :class="a.passed ? 'text-brand-700' : 'text-danger'">{{ a.percent }}%</b>
              <span class="text-muted ml-auto">{{ $dateTime(a.createdAt) }}</span>
            </li>
          </ul>
        </div>
      </section>

      <!-- Savollar -->
      <form v-if="started" class="space-y-3" data-testid="exam-form" @submit.prevent="askSubmit">
        <div class="sticky top-[64px] z-10 -mx-4 px-4 py-2 bg-white/90 backdrop-blur border-b border-line flex items-center gap-3">
          <div class="flex-1 h-2 rounded-full bg-surface overflow-hidden"><div class="h-full bg-brand transition-all" :style="{ width: `${answered / total * 100}%` }" /></div>
          <span class="text-sm font-bold tabular-nums">{{ answered }} / {{ total }}</span>
        </div>
        <fieldset v-for="(q, qi) in exam.questions" :key="qi" class="card p-4" :data-unanswered="answers[qi] === null ? '' : undefined">
          <legend class="sr-only">{{ q.q }}</legend>
          <p class="font-bold mb-3"><span class="text-brand-700 mr-1">{{ qi + 1 }}.</span>{{ q.q }}</p>
          <div class="grid gap-2">
            <label v-for="(o, oi) in q.options" :key="oi" :class="['flex items-center gap-3 p-3 rounded-xl border-[1.5px] cursor-pointer transition', answers[qi] === oi ? 'border-brand bg-brand-50' : 'border-line hover:border-brand-200']">
              <input type="radio" class="accent-[var(--color-brand)] size-4" :name="`q${qi}`" :checked="answers[qi] === oi" :data-testid="`q${qi}-o${oi}`" @change="choose(qi, oi)" />
              <span class="text-[15px]">{{ o }}</span>
            </label>
          </div>
        </fieldset>
        <div class="flex gap-2 pt-1">
          <BaseButton variant="ghost" @click="started = false">{{ $t('Bekor') }}</BaseButton>
          <BaseButton type="submit" class="flex-1" :icon="Send" data-testid="exam-submit">{{ $t('Javoblarni yuborish') }}</BaseButton>
        </div>
      </form>
    </template>
    <ConfirmModal v-model="confirm" :title="$t('Javoblarni yuborasizmi?')" :text="$t('Bu urinish hisobga olinadi. Qolgan urinishlar: {n}', { n: exam?.attemptsLeft })" :confirm-text="$t('Yuborish')" :loading="busy" @confirm="submit" />
  </div>
</template>
