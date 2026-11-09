<script setup>
/**
 * Kurslar boshqaruvi: faqat ikki bepul kurs (Rus tili, Ingliz tili).
 * Darslar: qo‘shish, tahrirlash (video, matn, lug‘at, tarjima, 5 savolli test), tartiblash, nashr/yashirish, o‘chirish.
 * Talabalar progressi jadvali.
 */
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Plus, Pencil, Trash2, ArrowUp, ArrowDown, Eye, EyeOff, GripVertical, Video, Upload, X, CheckCircle2, ListChecks, Languages, FileText, Repeat2, Users } from 'lucide-vue-next'
import PageHeader from '@/components/crm/PageHeader.vue'
import SegmentedControl from '@/components/ui/SegmentedControl.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'
import BaseButton from '@/components/ui/BaseButton.vue'
import BaseInput from '@/components/ui/BaseInput.vue'
import BaseTextarea from '@/components/ui/BaseTextarea.vue'
import BaseModal from '@/components/ui/BaseModal.vue'
import Avatar from '@/components/ui/Avatar.vue'
import ConfirmModal from '@/components/modals/ConfirmModal.vue'
import SkeletonRows from '@/components/crm/SkeletonRows.vue'
import RoundIllu from '@/components/brand/RoundIllu.vue'
import { crmStore, ensureCrmLoaded, crmApi, fullName } from '@/services/crm'
import { uploadFile } from '@/services/http'
import { useMediaUrl } from '@/composables/useMediaUrl'
import { QUIZ_SIZE } from '@/config/status'
import { fileSize } from '@/utils/format'
import { toast } from '@/stores/toast'
import { t } from '@/i18n'

const route = useRoute()
const router = useRouter()
const loading = ref(!crmStore.loaded)
ensureCrmLoaded().then(() => (loading.value = false))

const courseId = computed({ get: () => route.params.id || 'c-ru', set: (v) => router.replace(`/courses/${v}`) })
const course = computed(() => crmStore.courses.find((c) => c.id === courseId.value))
const courseOpts = computed(() => crmStore.courses.map((c) => ({ value: c.id, label: `${t(c.title)} · ${c.lessons.length}` })))
const view = ref('lessons')
const viewOpts = computed(() => [{ value: 'lessons', label: t('Darslar'), icon: ListChecks }, { value: 'progress', label: t('Talabalar progressi'), icon: Users }])

async function save(mut, msg) {
  const draft = JSON.parse(JSON.stringify(course.value))
  mut(draft)
  await crmApi.saveCourse(draft)
  if (msg) toast(msg)
}
const move = (i, d) => save((c) => { const j = i + d; if (j < 0 || j >= c.lessons.length) return; [c.lessons[i], c.lessons[j]] = [c.lessons[j], c.lessons[i]] }, t('Tartib saqlandi'))
const togglePublish = (l) => save((c) => { const x = c.lessons.find((y) => y.id === l.id); x.status = x.status === 'published' ? 'draft' : 'published' }, l.status === 'published' ? t('Dars yashirildi') : t('Dars nashr qilindi'))
const toggleCourse = () => save((c) => { c.status = c.status === 'published' ? 'draft' : 'published' }, t('Kurs holati yangilandi'))
const dragFrom = ref(null)
function onDrop(i) {
  const from = dragFrom.value; dragFrom.value = null
  if (from == null || from === i) return
  save((c) => { const [x] = c.lessons.splice(from, 1); c.lessons.splice(i, 0, x) }, t('Tartib saqlandi'))
}

// ---- O‘chirish ----
const delOpen = ref(false)
const delTarget = ref(null)
function askDelete(l) { delTarget.value = l; delOpen.value = true }
async function remove() { await save((c) => { c.lessons = c.lessons.filter((x) => x.id !== delTarget.value.id) }, t('Dars o‘chirildi')); delOpen.value = false }

// ---- Dars muharriri ----
const edOpen = ref(false)
const tab = ref('main')
const edTabs = computed(() => [
  { value: 'main', label: t('Asosiy'), icon: FileText },
  { value: 'vocab', label: t('Lug‘at'), icon: Languages },
  { value: 'tr', label: t('Tarjima'), icon: Repeat2 },
  { value: 'quiz', label: `${t('Test')} (${QUIZ_SIZE})`, icon: ListChecks },
])
const L = ref(null)
const isNew = ref(false)
const errors = ref({})
const emptyQuiz = () => Array.from({ length: QUIZ_SIZE }, () => ({ q: '', options: ['', '', '', ''], answer: 0 }))
function openEditor(l) {
  isNew.value = !l
  L.value = l ? JSON.parse(JSON.stringify(l)) : { id: `${course.value.key}-${Date.now().toString(36)}`, title: '', summary: '', status: 'draft', durationMin: 10, video: null, text: '', vocab: [{ word: '', translation: '' }], translations: [{ source: '', target: '' }], quiz: emptyQuiz() }
  while (L.value.quiz.length < QUIZ_SIZE) L.value.quiz.push({ q: '', options: ['', '', '', ''], answer: 0 })
  errors.value = {}
  tab.value = 'main'
  edOpen.value = true
}
const videoUrl = useMediaUrl(() => L.value?.video?.url)
const videoInput = ref(null)
const uploading = ref(false)
async function onVideo(e) {
  const f = e.target.files?.[0]; e.target.value = ''
  if (!f) return
  if (!/^video\/(mp4|webm)$/.test(f.type)) return toast(t('Faqat MP4 yoki WebM'), 'error')
  if (f.size > 50 * 1048576) return toast(t('Video 50 MB dan oshmasin'), 'error')
  uploading.value = true
  try {
    const r = await uploadFile(f, 'lesson')
    L.value.video = { url: r.url, poster: null, name: r.name, size: r.size }
  } catch (err) {
    toast(err.message, 'error')
  } finally {
    uploading.value = false
  }
}
function validateLesson() {
  const e = {}
  if (!L.value.title.trim()) e.title = t('Majburiy maydon')
  if (L.value.text.trim().length < 20) e.text = t('Kamida {n} ta belgi', { n: 20 })
  const vocab = L.value.vocab.filter((v) => v.word.trim() && v.translation.trim())
  if (!vocab.length) e.vocab = t('Kamida 1 ta so‘z kiriting')
  L.value.quiz.forEach((q, i) => { if (!q.q.trim() || q.options.some((o) => !o.trim())) e.quiz = t('{n}-savol to‘liq emas', { n: i + 1 }) })
  return e
}
async function saveLesson() {
  errors.value = validateLesson()
  if (Object.keys(errors.value).length) {
    tab.value = errors.value.title || errors.value.text ? 'main' : errors.value.vocab ? 'vocab' : 'quiz'
    return
  }
  const clean = { ...L.value, vocab: L.value.vocab.filter((v) => v.word.trim()), translations: L.value.translations.filter((x) => x.source.trim()) }
  await save((c) => {
    const i = c.lessons.findIndex((x) => x.id === clean.id)
    if (i >= 0) c.lessons[i] = clean
    else c.lessons.push(clean)
  }, isNew.value ? t('Dars qo‘shildi') : t('Dars saqlandi'))
  edOpen.value = false
}

// ---- Progress ----
const progressRows = computed(() => crmStore.progress.filter((p) => p.courseId === courseId.value)
  .map((p) => ({ ...p, user: crmStore.users.find((u) => u.id === p.userId), percent: Math.round((p.completed.length / Math.max(1, course.value?.lessons.length || 1)) * 100), avg: p.completed.length ? (Object.values(p.scores).reduce((s, x) => s + x, 0) / Object.values(p.scores).length).toFixed(1) : '—' }))
  .sort((a, b) => b.percent - a.percent))
const avgPercent = computed(() => (progressRows.value.length ? Math.round(progressRows.value.reduce((s, r) => s + r.percent, 0) / progressRows.value.length) : 0))
watch(courseId, () => (view.value = 'lessons'))
</script>

<template>
  <div>
    <PageHeader :title="$t('Kurslar boshqaruvi')" illu="dictionary">
      <SegmentedControl v-model="courseId" :options="courseOpts" class="w-full sm:w-80" data-testid="course-switch" />
    </PageHeader>
    <SkeletonRows v-if="loading || !course" :rows="5" :cols="4" class="crm-card" />
    <template v-else>
      <section class="crm-card p-5 flex flex-wrap items-center gap-4">
        <RoundIllu :kind="course.key === 'ru' ? 'books' : 'chat'" :size="64" :float="false" />
        <div class="min-w-0 flex-1">
          <p class="text-lg font-extrabold">{{ $t(course.title) }} <span class="pill ml-1">{{ $t('Bepul') }} · {{ course.level }}</span></p>
          <p class="text-sm text-muted">{{ course.lessons.length }} {{ $t('dars') }} · {{ course.lessons.filter((l) => l.status === 'published').length }} {{ $t('nashr qilingan') }} · {{ progressRows.length }} {{ $t('talaba') }} · {{ $t('o‘rtacha') }} {{ avgPercent }}%</p>
        </div>
        <StatusBadge :status="course.status" />
        <BaseButton variant="soft" size="sm" :icon="course.status === 'published' ? EyeOff : Eye" @click="toggleCourse">{{ course.status === 'published' ? $t('Kursni yashirish') : $t('Nashr qilish') }}</BaseButton>
      </section>

      <div class="flex flex-wrap items-center gap-3 mt-4 mb-3">
        <SegmentedControl v-model="view" :options="viewOpts" class="w-full sm:w-96" />
        <BaseButton v-if="view === 'lessons'" class="ml-auto" :icon="Plus" data-testid="add-lesson" @click="openEditor(null)">{{ $t('Dars qo‘shish') }}</BaseButton>
      </div>

      <!-- Darslar -->
      <ol v-if="view === 'lessons'" class="crm-card divide-y divide-line" data-testid="crm-lessons">
        <li v-for="(l, i) in course.lessons" :key="l.id" draggable="true" class="flex items-center gap-3 px-4 py-3 hover:bg-[#fafafb]" @dragstart="dragFrom = i" @dragover.prevent @drop.prevent="onDrop(i)">
          <GripVertical class="size-4 text-muted cursor-grab shrink-0 hidden sm:block" />
          <span class="size-9 rounded-xl bg-brand-50 text-brand-700 grid place-items-center font-bold text-sm shrink-0 tabular-nums">{{ i + 1 }}</span>
          <div class="min-w-0 flex-1">
            <p class="font-semibold truncate">{{ l.title }}</p>
            <p class="text-xs text-muted truncate">
              <Video v-if="l.video" class="inline size-3.5 -mt-0.5" /> {{ l.video ? $t('Video') + ' · ' : '' }}{{ l.vocab.length }} {{ $t('so‘z') }} · {{ l.translations.length }} {{ $t('tarjima') }} · {{ l.quiz.length }} {{ $t('savol') }}
            </p>
          </div>
          <StatusBadge :status="l.status" class="hidden sm:inline-flex" />
          <div class="flex gap-0.5">
            <button class="icon-btn" :disabled="i === 0" :aria-label="$t('Yuqoriga')" @click="move(i, -1)"><ArrowUp class="size-4" /></button>
            <button class="icon-btn" :disabled="i === course.lessons.length - 1" :aria-label="$t('Pastga')" @click="move(i, 1)"><ArrowDown class="size-4" /></button>
            <button class="icon-btn" :title="l.status === 'published' ? $t('Yashirish') : $t('Nashr qilish')" :aria-label="l.status === 'published' ? $t('Yashirish') : $t('Nashr qilish')" data-testid="toggle-lesson" @click="togglePublish(l)"><component :is="l.status === 'published' ? EyeOff : Eye" class="size-4" /></button>
            <button class="icon-btn" :aria-label="$t('Tahrirlash')" data-testid="edit-lesson" @click="openEditor(l)"><Pencil class="size-4" /></button>
            <button class="icon-btn icon-btn-danger" :aria-label="$t('O‘chirish')" @click="askDelete(l)"><Trash2 class="size-4" /></button>
          </div>
        </li>
        <li v-if="!course.lessons.length" class="p-8 text-center text-sm text-muted">{{ $t('Hali dars yo‘q') }}</li>
      </ol>

      <!-- Progress -->
      <div v-else class="crm-card overflow-x-auto">
        <table class="crm-table min-w-[720px]" data-testid="progress-table">
          <thead><tr><th>{{ $t('Talaba') }}</th><th>{{ $t('Tugatilgan darslar') }}</th><th>{{ $t('Progress') }}</th><th>{{ $t('O‘rtacha test') }}</th><th>{{ $t('Oxirgi faollik') }}</th></tr></thead>
          <tbody>
            <tr v-for="r in progressRows" :key="r.id">
              <td><RouterLink :to="{ path: '/users', query: { id: r.userId } }" class="flex items-center gap-2.5 hover:text-brand-700"><Avatar :name="fullName(r.user)" size="sm" /><span class="font-semibold">{{ fullName(r.user) }}</span></RouterLink></td>
              <td class="tabular-nums">{{ r.completed.length }} / {{ course.lessons.length }}</td>
              <td class="w-56"><div class="flex items-center gap-2"><div class="flex-1 h-2 rounded-full bg-surface overflow-hidden"><div class="h-full bg-brand rounded-full" :style="{ width: `${r.percent}%` }" /></div><span class="tabular-nums text-xs font-bold w-9 text-right">{{ r.percent }}%</span></div></td>
              <td class="tabular-nums">{{ r.avg }}{{ r.avg !== '—' ? ' / 5' : '' }}</td>
              <td class="whitespace-nowrap text-muted">{{ $ago(r.updatedAt) }}</td>
            </tr>
            <tr v-if="!progressRows.length"><td colspan="5" class="text-center text-muted py-8">{{ $t('Hali hech kim boshlamagan') }}</td></tr>
          </tbody>
        </table>
      </div>
    </template>

    <!-- Dars muharriri -->
    <BaseModal v-model="edOpen" drawer :title="isNew ? $t('Yangi dars') : $t('Darsni tahrirlash')" :subtitle="course && $t(course.title)">
      <div v-if="L" class="space-y-4" data-testid="lesson-editor">
        <SegmentedControl v-model="tab" :options="edTabs" />
        <template v-if="tab === 'main'">
          <BaseInput v-model="L.title" :label="$t('Dars nomi')" required :error="errors.title" data-testid="le-title" />
          <BaseInput v-model="L.summary" :label="$t('Qisqa tavsif')" />
          <div>
            <span class="label">{{ $t('Video') }}</span>
            <div v-if="L.video" class="rounded-xl overflow-hidden bg-ink aspect-video relative">
              <video v-if="videoUrl" :src="videoUrl" controls playsinline class="size-full object-contain" />
              <button class="absolute right-2 top-2 size-8 rounded-full bg-white/90 grid place-items-center" :aria-label="$t('O‘chirish')" @click="L.video = null"><X class="size-4" /></button>
            </div>
            <button v-else class="w-full h-24 rounded-xl border-2 border-dashed border-line hover:border-brand grid place-items-center text-sm font-semibold text-ink-2" :disabled="uploading" @click="videoInput.click()">
              <span class="inline-flex items-center gap-2"><Upload class="size-4 text-brand-600" />{{ uploading ? $t('Yuklanmoqda...') : $t('MP4 / WebM yuklash (50 MB gacha)') }}</span>
            </button>
            <p v-if="L.video?.name" class="text-xs text-muted mt-1">{{ L.video.name }} · {{ fileSize(L.video.size || 0) }}</p>
            <input ref="videoInput" type="file" accept="video/mp4,video/webm" class="hidden" @change="onVideo" />
          </div>
          <BaseTextarea v-model="L.text" :label="$t('Dars matni (xatboshilar bo‘sh qator bilan)')" :rows="8" required :error="errors.text" data-testid="le-text" />
        </template>
        <template v-else-if="tab === 'vocab'">
          <p v-if="errors.vocab" class="text-xs text-danger">{{ errors.vocab }}</p>
          <div v-for="(v, i) in L.vocab" :key="i" class="grid grid-cols-[1fr_1fr_auto] gap-2">
            <input v-model="v.word" :placeholder="$t('So‘z')" class="fld" /><input v-model="v.translation" :placeholder="$t('Tarjimasi')" class="fld" />
            <button class="icon-btn icon-btn-danger self-center" :aria-label="$t('O‘chirish')" @click="L.vocab.splice(i, 1)"><X class="size-4" /></button>
          </div>
          <BaseButton size="sm" variant="soft" :icon="Plus" @click="L.vocab.push({ word: '', translation: '' })">{{ $t('So‘z qo‘shish') }}</BaseButton>
        </template>
        <template v-else-if="tab === 'tr'">
          <div v-for="(x, i) in L.translations" :key="i" class="grid grid-cols-[1fr_auto] gap-2 rounded-xl border border-line p-3">
            <div class="space-y-2"><input v-model="x.source" :placeholder="$t('Gap (o‘rganilayotgan tilda)')" class="fld w-full" /><input v-model="x.target" :placeholder="$t('Tarjimasi')" class="fld w-full" /></div>
            <button class="icon-btn icon-btn-danger" :aria-label="$t('O‘chirish')" @click="L.translations.splice(i, 1)"><X class="size-4" /></button>
          </div>
          <BaseButton size="sm" variant="soft" :icon="Plus" @click="L.translations.push({ source: '', target: '' })">{{ $t('Tarjima qo‘shish') }}</BaseButton>
        </template>
        <template v-else>
          <p v-if="errors.quiz" class="text-xs text-danger" role="alert">{{ errors.quiz }}</p>
          <div v-for="(q, i) in L.quiz" :key="i" class="rounded-xl border border-line p-3 space-y-2">
            <p class="text-xs font-bold text-muted">{{ i + 1 }}-{{ $t('savol') }}</p>
            <input v-model="q.q" :placeholder="$t('Savol matni')" class="fld w-full" :data-testid="`le-q${i}`" />
            <div class="grid sm:grid-cols-2 gap-2">
              <label v-for="(o, k) in q.options" :key="k" :class="['flex items-center gap-2 rounded-lg border px-2', q.answer === k ? 'border-brand bg-brand-25' : 'border-line']">
                <input v-model="q.answer" type="radio" :name="`q${i}`" :value="k" :aria-label="$t('To‘g‘ri javob')" class="accent-[#10B981]" />
                <input v-model="q.options[k]" :placeholder="`${$t('Variant')} ${k + 1}`" class="flex-1 min-w-0 h-9 outline-none text-sm bg-transparent" />
                <CheckCircle2 v-if="q.answer === k" class="size-4 text-brand-600 shrink-0" />
              </label>
            </div>
          </div>
          <p class="text-xs text-muted">{{ $t('Talaba 5 tadan kamida 3 ta to‘g‘ri javob bersa, dars yakunlanadi.') }}</p>
        </template>
        <label class="flex items-center gap-2 text-sm font-semibold pt-2"><input type="checkbox" :checked="L.status === 'published'" class="accent-[#10B981] size-4" @change="L.status = $event.target.checked ? 'published' : 'draft'" />{{ $t('Saqlangach nashr qilish') }}</label>
      </div>
      <template #footer><BaseButton block data-testid="le-save" @click="saveLesson">{{ $t('Saqlash') }}</BaseButton></template>
    </BaseModal>

    <ConfirmModal v-model="delOpen" :title="$t('Darsni o‘chirish')" :text="$t('“{x}” darsi va unga bog‘liq test o‘chiriladi.', { x: delTarget?.title })" :confirm-text="$t('O‘chirish')" danger @confirm="remove" />
  </div>
</template>

<style scoped>
@reference "../../style.css";
.fld { @apply h-10 px-3 rounded-lg border border-line outline-none text-sm focus:border-brand focus:ring-4 focus:ring-brand/10; }
</style>
