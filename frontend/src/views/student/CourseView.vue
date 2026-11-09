<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, CheckCircle2, Lock, PlayCircle } from 'lucide-vue-next'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import { coursesApi } from '@/services'

const route = useRoute()
const router = useRouter()
const course = ref(null)
const progress = ref({ completed: [], scores: {} })
const loading = ref(true)
onMounted(async () => {
  course.value = await coursesApi.get(route.params.courseId)
  if (course.value) progress.value = await coursesApi.progress(course.value.id)
  loading.value = false
})
const done = (l) => progress.value.completed.includes(l.id)
const unlocked = (i) => i === 0 || done(course.value.lessons[i - 1]) || done(course.value.lessons[i])
</script>

<template>
  <div class="page-narrow">
    <button class="inline-flex items-center gap-1.5 text-sm font-semibold text-muted hover:text-ink mb-3" @click="router.push('/student/courses')"><ArrowLeft class="size-4" />{{ $t('Kurslar') }}</button>
    <SkeletonCard v-if="loading" :count="3" />
    <EmptyState v-else-if="!course" :title="$t('Kurs topilmadi')" text="" />
    <template v-else>
      <div class="flex items-center gap-4">
        <RoundIllu :kind="course.key === 'ru' ? 'books' : 'chat'" :size="76" :float="false" />
        <div>
          <h1 class="text-[24px] font-extrabold tracking-tight">{{ $t(course.title) }}</h1>
          <p class="text-sm text-muted">{{ $t('{a} / {b} dars tugatildi', { a: course.done, b: course.lessons.length }) }} · {{ course.percent }}%</p>
        </div>
      </div>
      <div class="h-2 rounded-full bg-surface overflow-hidden mt-4"><div class="h-full bg-brand rounded-full transition-all" :style="{ width: `${course.percent}%` }" /></div>
      <ol class="mt-5 space-y-2.5 stagger" data-testid="lesson-list">
        <li v-for="(l, i) in course.lessons" :key="l.id">
          <button
            :disabled="!unlocked(i)"
            :class="['w-full card p-4 flex items-center gap-4 text-left transition', unlocked(i) ? 'card-hover' : 'opacity-60 cursor-not-allowed']"
            @click="router.push(`/student/courses/${course.id}/${l.id}`)"
          >
            <span :class="['size-11 rounded-2xl grid place-items-center shrink-0 font-extrabold', done(l) ? 'bg-brand text-white' : unlocked(i) ? 'bg-brand-50 text-brand-700' : 'bg-surface text-muted']">
              <CheckCircle2 v-if="done(l)" class="size-5" /><Lock v-else-if="!unlocked(i)" class="size-[18px]" /><template v-else>{{ l.order }}</template>
            </span>
            <span class="min-w-0 flex-1">
              <span class="block font-bold">{{ $tc(l.title) }}</span>
              <span class="block text-[13px] text-muted truncate">{{ $tc(l.summary) }}</span>
            </span>
            <span v-if="done(l)" class="text-[12px] font-bold text-success tabular-nums">{{ progress.scores[l.id] }}/5</span>
            <PlayCircle v-else-if="unlocked(i)" class="size-6 text-brand-600" />
          </button>
        </li>
      </ol>
    </template>
  </div>
</template>
