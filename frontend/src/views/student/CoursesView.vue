<script setup>
/** Kurslar: hozircha ikki bepul online kurs (Rus tili, Ingliz tili). Tarkibi TalabaGo Support’da boshqariladi. */
import PageIntro from '@/components/layout/PageIntro.vue'
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { PlayCircle, BookOpen, Clock, Award } from 'lucide-vue-next'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import SkeletonCard from '@/components/ui/SkeletonCard.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import ErrorState from '@/components/ui/ErrorState.vue'
import { coursesApi } from '@/services'

const router = useRouter()
const items = ref([])
const loading = ref(true)
const error = ref(null)
async function load() {
  loading.value = true; error.value = null
  try { items.value = await coursesApi.list() } catch (e) { error.value = e.message }
  loading.value = false
}
onMounted(load)
const nextLesson = (c) => c.lessons.find((l, i) => i >= c.done) || c.lessons.at(-1)
</script>

<template>
  <div class="page-narrow lg:max-w-5xl!">
    <PageIntro class="mb-4" />
    <div v-if="loading" class="grid md:grid-cols-2 gap-4"><SkeletonCard :count="2" media class="contents" /></div>
    <ErrorState v-else-if="error" :message="error" @retry="load" />
    <EmptyState v-else-if="!items.length" :title="$t('Kurslar hali e’lon qilinmagan')" :text="$t('Tez orada qo‘shiladi.')" illu="books" />
    <div v-else class="grid md:grid-cols-2 gap-4 stagger" data-testid="course-list">
      <article v-for="c in items" :key="c.id" class="card card-hover p-5 flex flex-col cursor-pointer" :data-testid="`course-${c.key}`" @click="router.push(`/student/courses/${c.id}`)">
        <div class="flex items-start gap-4">
          <div class="relative">
            <RoundIllu :kind="c.key === 'ru' ? 'books' : 'chat'" :size="84" :float="false" />
            <span class="absolute -bottom-1 -right-1 h-7 px-2 rounded-full bg-ink text-white text-[12px] font-extrabold grid place-items-center">{{ c.key === 'ru' ? 'RU' : 'EN' }}</span>
          </div>
          <div class="min-w-0 flex-1">
            <span class="inline-flex h-6 px-2.5 items-center rounded-full bg-brand-50 text-brand-700 text-[11.5px] font-bold">{{ $t('Bepul') }} · {{ c.level }}</span>
            <h2 class="text-[20px] font-extrabold tracking-tight mt-1.5">{{ $t(c.title) }}</h2>
            <p class="text-[13px] text-muted">{{ $t(c.subtitle) }}</p>
          </div>
        </div>
        <p class="text-[14px] text-ink-2 mt-4 leading-relaxed">{{ $tc(c.description) }}</p>
        <div class="flex items-center gap-4 mt-4 text-[13px] text-ink-2">
          <span class="inline-flex items-center gap-1.5"><BookOpen class="size-4 text-muted" />{{ $t('{n} ta dars', { n: c.lessons.length }) }}</span>
          <span class="inline-flex items-center gap-1.5"><Clock class="size-4 text-muted" />~{{ c.lessons.length * 12 }} {{ $t('daqiqa') }}</span>
          <span v-if="c.percent === 100" class="inline-flex items-center gap-1.5 text-success font-semibold"><Award class="size-4" />{{ $t('Tugatildi') }}</span>
        </div>
        <div class="mt-4">
          <div class="flex justify-between text-[12.5px] font-semibold mb-1.5"><span>{{ $t('Progress') }}</span><span class="tabular-nums" :data-testid="`progress-${c.key}`">{{ c.percent }}%</span></div>
          <div class="h-2 rounded-full bg-surface overflow-hidden" role="progressbar" :aria-valuenow="c.percent" aria-valuemin="0" aria-valuemax="100"><div class="h-full rounded-full bg-brand transition-all duration-700" :style="{ width: `${c.percent}%` }" /></div>
        </div>
        <BaseButton block class="mt-5" :icon="PlayCircle" @click.stop="router.push(`/student/courses/${c.id}/${nextLesson(c)?.id}`)">
          {{ c.done ? $t('Davom ettirish') : $t('Boshlash') }} · {{ nextLesson(c)?.order }}-{{ $t('dars') }}
        </BaseButton>
      </article>
    </div>
  </div>
</template>
