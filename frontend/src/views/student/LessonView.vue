<script setup>
/** Dars: Video · Matn · Lug‘at · Tarjima · Test (5 savol). Testdan o‘tilsa dars yakunlanadi, keyingisi ochiladi. */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, ArrowRight, PlayCircle, FileText, Languages, Repeat2, ListChecks, CheckCircle2, XCircle, Lock, Award, Eye, EyeOff, RotateCcw } from 'lucide-vue-next'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import { coursesApi } from '@/services'
import { QUIZ_PASS } from '@/config/roles'
import { useMediaUrl } from '@/composables/useMediaUrl'
import { haptic } from '@/services/telegram'
import { toast } from '@/stores/session'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const course = ref(null)
const progress = ref({ completed: [], scores: {} })
const loading = ref(true)
const tab = ref('video')

async function load() {
  loading.value = true
  course.value = await coursesApi.get(route.params.courseId)
  if (course.value) progress.value = await coursesApi.progress(course.value.id)
  loading.value = false
}

const idx = computed(() => course.value?.lessons.findIndex((l) => l.id === route.params.lessonId) ?? -1)
const lesson = computed(() => course.value?.lessons[idx.value])
const next = computed(() => course.value?.lessons[idx.value + 1])
const prev = computed(() => course.value?.lessons[idx.value - 1])
const isDone = computed(() => lesson.value && progress.value.completed.includes(lesson.value.id))
const locked = computed(() => idx.value > 0 && !progress.value.completed.includes(prev.value?.id) && !isDone.value)
const videoUrl = useMediaUrl(() => lesson.value?.video?.url)
const posterUrl = useMediaUrl(() => lesson.value?.video?.poster)

const tabs = computed(() => [
  { value: 'video', label: t('Video'), icon: PlayCircle },
  { value: 'text', label: t('Matn'), icon: FileText },
  { value: 'vocab', label: t('Lug‘at'), icon: Languages },
  { value: 'tr', label: t('Tarjima'), icon: Repeat2 },
  { value: 'quiz', label: t('Test'), icon: ListChecks },
])

// ---- Tarjima mashqi: javobni yashirish/ko‘rsatish ----
const shown = ref(new Set())
const toggleShown = (i) => { const s = new Set(shown.value); s.has(i) ? s.delete(i) : s.add(i); shown.value = s }

// ---- Test ----
const answers = ref([])
const checked = ref(false)
const saving = ref(false)
function resetQuiz() { answers.value = []; checked.value = false; shown.value = new Set() }
const score = computed(() => lesson.value?.quiz.reduce((s, q, i) => s + (answers.value[i] === q.answer ? 1 : 0), 0) || 0)
const allAnswered = computed(() => lesson.value && lesson.value.quiz.every((_, i) => answers.value[i] != null))
async function check() {
  checked.value = true
  if (score.value >= QUIZ_PASS) {
    haptic.success()
    saving.value = true
    try {
      progress.value = await coursesApi.completeLesson(course.value.id, lesson.value.id, lesson.value.quiz.map((_, i) => answers.value[i] ?? -1))
      toast(t('Dars yakunlandi! {s}/5', { s: score.value }))
    } catch (e) {
      toast(e.message, 'error')
    } finally {
      saving.value = false
    }
  } else haptic.error()
}
watch(() => route.params.lessonId, () => { tab.value = 'video'; resetQuiz(); load() }, { immediate: true })

const optCls = (q, i, o) => {
  const sel = answers.value[i] === o
  if (!checked.value) return sel ? 'border-brand bg-brand-50 text-brand-800' : 'border-line hover:border-brand-200'
  if (o === q.answer) return 'border-success bg-success/10 text-success'
  if (sel) return 'border-danger bg-danger/10 text-danger'
  return 'border-line opacity-60'
}
</script>

<template>
  <div class="page lg:max-w-6xl">
    <button class="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink mb-3" @click="router.push(`/student/courses/${route.params.courseId}`)"><ArrowLeft class="size-4" />{{ course ? $t(course.title) : $t('Kurslar') }}</button>
    <SkeletonCard v-if="loading" :count="2" media />
    <EmptyState v-else-if="!lesson" :title="$t('Dars topilmadi')" text="" />
    <EmptyState v-else-if="locked" :title="$t('Bu dars hali yopiq')" :text="$t('Avval oldingi darsni yakunlang.')" illu="pen">
      <BaseButton @click="router.push(`/student/courses/${course.id}/${prev.id}`)">{{ prev.order }}-{{ $t('dars') }}</BaseButton>
    </EmptyState>
    <div v-else class="lg:grid lg:grid-cols-[minmax(0,1fr)_300px] lg:gap-8 lg:items-start">
      <section class="min-w-0">
        <p class="text-[13px] font-semibold text-brand-600">{{ $t(course.title) }} · {{ lesson.order }}-{{ $t('dars') }}</p>
        <h1 class="text-[24px] lg:text-[28px] font-extrabold tracking-tight leading-tight mt-1 flex items-center gap-2">
          {{ $tc(lesson.title) }}<CheckCircle2 v-if="isDone" class="size-6 text-success" />
        </h1>
        <p class="text-muted text-sm mt-1">{{ $tc(lesson.summary) }}</p>

        <div class="mt-4 -mx-4 px-4 overflow-x-auto no-scrollbar"><SegmentedControl v-model="tab" :options="tabs" class="min-w-[520px]" data-testid="lesson-tabs" /></div>

        <Transition name="fade" mode="out-in">
          <!-- Video -->
          <div v-if="tab === 'video'" key="v" class="mt-4">
            <div v-if="videoUrl" class="rounded-2xl overflow-hidden bg-ink aspect-video">
              <video :key="videoUrl" :src="videoUrl" :poster="posterUrl" controls playsinline preload="metadata" class="size-full object-contain" data-testid="lesson-video" />
            </div>
            <EmptyState v-else :title="$t('Bu darsda video yo‘q')" :text="$t('Matn va lug‘at bo‘limiga o‘ting.')" illu="laptop" />
            <BaseButton class="mt-4" variant="soft" :icon-right="ArrowRight" @click="tab = 'text'">{{ $t('Matnga o‘tish') }}</BaseButton>
          </div>
          <!-- Matn -->
          <article v-else-if="tab === 'text'" key="t" class="mt-4 card p-5 lg:p-6">
            <p v-for="(p, i) in lesson.text.split('\n\n')" :key="i" class="text-[15.5px] leading-relaxed text-ink-2 mb-3 last:mb-0">{{ $tc(p) }}</p>
          </article>
          <!-- Lug‘at -->
          <div v-else-if="tab === 'vocab'" key="w" class="mt-4 grid sm:grid-cols-2 gap-2.5" data-testid="vocab">
            <div v-for="w in lesson.vocab" :key="w.word" class="card p-4 flex items-center gap-3">
              <span class="size-9 rounded-xl bg-brand-50 text-brand-700 grid place-items-center font-bold text-sm shrink-0">{{ w.word[0] }}</span>
              <span class="min-w-0"><span class="block font-bold text-[16px]">{{ w.word }}</span><span class="block text-[13px] text-muted">{{ $tc(w.translation) }}</span></span>
            </div>
          </div>
          <!-- Tarjima -->
          <div v-else-if="tab === 'tr'" key="r" class="mt-4 space-y-2.5">
            <p class="text-sm text-muted">{{ $t('Avval o‘zingiz tarjima qiling, keyin javobni oching.') }}</p>
            <div v-for="(x, i) in lesson.translations" :key="i" class="card p-4">
              <p class="font-bold text-[16px]">{{ x.source }}</p>
              <div class="flex items-center gap-2 mt-2">
                <p :class="['flex-1 text-[14.5px] transition', shown.has(i) ? 'text-brand-700' : 'text-transparent bg-surface rounded-lg select-none']">{{ $tc(x.target) }}</p>
                <button class="inline-flex items-center gap-1 text-[13px] font-semibold text-ink-2 hover:text-ink" @click="toggleShown(i)"><component :is="shown.has(i) ? EyeOff : Eye" class="size-4" />{{ shown.has(i) ? $t('Yashirish') : $t('Ko‘rsatish') }}</button>
              </div>
            </div>
          </div>
          <!-- Test -->
          <div v-else key="q" class="mt-4" data-testid="quiz">
            <div v-if="isDone && !checked" class="mb-4 flex items-center gap-2 rounded-xl bg-success/10 text-success px-3 py-2.5 text-sm font-semibold"><Award class="size-5" />{{ $t('Bu dars yakunlangan. Natija: {s}/5', { s: progress.scores[lesson.id] }) }}</div>
            <ol class="space-y-4">
              <li v-for="(q, i) in lesson.quiz" :key="i" class="card p-4">
                <p class="font-bold"><span class="text-muted tabular-nums">{{ i + 1 }}.</span> {{ $tc(q.q) }}</p>
                <div class="grid sm:grid-cols-2 gap-2 mt-3" role="radiogroup">
                  <button v-for="(o, k) in q.options" :key="k" role="radio" :aria-checked="answers[i] === k" :disabled="checked"
                    :class="['min-h-11 px-3.5 py-2 rounded-xl border-[1.5px] text-left text-[14.5px] font-medium transition flex items-center gap-2', optCls(q, i, k)]"
                    :data-testid="`q${i}-o${k}`" @click="answers[i] = k; answers = [...answers]">
                    <CheckCircle2 v-if="checked && k === q.answer" class="size-4 shrink-0" /><XCircle v-else-if="checked && answers[i] === k" class="size-4 shrink-0" />{{ $tc(o) }}
                  </button>
                </div>
              </li>
            </ol>
            <div v-if="checked" :class="['mt-5 rounded-2xl p-5 text-center', score >= QUIZ_PASS ? 'bg-brand-50' : 'bg-danger/8']" data-testid="quiz-result">
              <RoundIllu :kind="score >= QUIZ_PASS ? 'student' : 'pen'" :size="84" class="mx-auto" :float="false" />
              <p class="text-[22px] font-extrabold mt-2 tabular-nums">{{ score }} / {{ lesson.quiz.length }}</p>
              <p class="text-sm text-ink-2">{{ score >= QUIZ_PASS ? $t('Ajoyib! Dars yakunlandi.') : $t('O‘tish uchun kamida {n} ta to‘g‘ri javob kerak.', { n: QUIZ_PASS }) }}</p>
              <div class="flex justify-center gap-2 mt-4">
                <BaseButton variant="soft" :icon="RotateCcw" @click="resetQuiz">{{ $t('Qayta topshirish') }}</BaseButton>
                <BaseButton v-if="score >= QUIZ_PASS && next" :icon-right="ArrowRight" :loading="saving" data-testid="next-lesson" @click="router.push(`/student/courses/${course.id}/${next.id}`)">{{ $t('Keyingi dars') }}</BaseButton>
                <BaseButton v-else-if="score >= QUIZ_PASS" :icon="Award" @click="router.push('/student/courses')">{{ $t('Kurslarga qaytish') }}</BaseButton>
              </div>
            </div>
            <BaseButton v-else block size="lg" class="mt-5" :disabled="!allAnswered" data-testid="quiz-check" @click="check">{{ $t('Javoblarni tekshirish') }}</BaseButton>
          </div>
        </Transition>

        <div class="flex justify-between gap-2 mt-6 pt-4 border-t border-line">
          <BaseButton v-if="prev" variant="ghost" :icon="ArrowLeft" @click="router.push(`/student/courses/${course.id}/${prev.id}`)">{{ prev.order }}-{{ $t('dars') }}</BaseButton><span v-else />
          <BaseButton v-if="next" variant="ghost" :icon-right="isDone ? ArrowRight : Lock" :disabled="!isDone" @click="router.push(`/student/courses/${course.id}/${next.id}`)">{{ $t('Keyingi dars') }}</BaseButton>
        </div>
      </section>

      <!-- Desktop: darslar ro‘yxati -->
      <aside class="hidden lg:block card p-4 sticky top-[88px]">
        <p class="font-bold mb-1">{{ $t('Darslar') }}</p>
        <p class="text-xs text-muted mb-3">{{ course.percent }}% · {{ $t('{a} / {b} dars tugatildi', { a: progress.completed.length, b: course.lessons.length }) }}</p>
        <ol class="space-y-1">
          <li v-for="(l, i) in course.lessons" :key="l.id">
            <RouterLink :to="`/student/courses/${course.id}/${l.id}`" :class="['flex items-center gap-2.5 h-10 px-2.5 rounded-xl text-sm', l.id === lesson.id ? 'bg-brand-50 text-brand-700 font-bold' : 'hover:bg-surface text-ink-2']">
              <CheckCircle2 v-if="progress.completed.includes(l.id)" class="size-4 text-success shrink-0" />
              <Lock v-else-if="i > 0 && !progress.completed.includes(course.lessons[i - 1].id)" class="size-4 text-muted shrink-0" />
              <span v-else class="size-4 grid place-items-center text-[11px] font-bold shrink-0">{{ l.order }}</span>
              <span class="truncate">{{ $tc(l.title) }}</span>
            </RouterLink>
          </li>
        </ol>
      </aside>
    </div>
  </div>
</template>
