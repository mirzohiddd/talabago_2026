<script setup>
/**
 * TalabaGo illustratsiyasi (haqiqiy rasm: src/assets/illustrations/*.webp).
 * Standart — dumaloq oq-yashil “sfera” ichida; `bare` — doirasiz.
 * kind: asset nomi (student, worker, office-worker, student-laptop, building, laptop, books, briefcase, house, keys,
 *       desk-lamp, calendar, checklist, stats, mail, search-job, search-house, support, trophy, translate,
 *       video, quiz, dictionary, code, office) yoki eski taxalluslar (key, pen, plant, desk, chat).
 */
import { computed } from 'vue'

const FILES = import.meta.glob('@/assets/illustrations/*.webp', { eager: true, import: 'default' })
const SRC = Object.fromEntries(Object.entries(FILES).map(([p, url]) => [p.split('/').pop().replace('.webp', ''), url]))
const ALIAS = { key: 'keys', pen: 'quiz', plant: 'desk-lamp', desk: 'office', chat: 'translate' }
const PEOPLE = ['student', 'worker', 'office-worker', 'student-laptop']

const props = defineProps({
  kind: { type: String, default: 'laptop' },
  size: { type: [Number, String], default: 120 },
  float: { type: Boolean, default: true },
  delay: { type: Number, default: 0 },
  bare: { type: Boolean, default: false },
})
const name = computed(() => ALIAS[props.kind] || props.kind)
const src = computed(() => SRC[name.value] || SRC.laptop)
const person = computed(() => PEOPLE.includes(name.value))
const px = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
</script>

<template>
  <div
    class="round-illu shrink-0 select-none pointer-events-none"
    :class="[float && 'is-float', !bare && 'is-round']"
    :style="{ width: px, height: px, animationDelay: `${delay}s` }"
    aria-hidden="true"
  >
    <span class="relative block size-full">
    <img
      :src="src" alt="" draggable="false" loading="lazy" decoding="async"
      :class="['absolute object-contain', bare ? 'inset-0 size-full' : person ? 'inset-x-[10%] bottom-[6%] w-[80%] h-[86%] object-bottom' : 'inset-[16%] w-[68%] h-[68%]']"
    />
    </span>
  </div>
</template>

<style scoped>
.is-round {
  border-radius: 9999px;
  background: radial-gradient(circle at 34% 26%, #FFFFFF 0%, #F3FCF8 48%, #DDF6EC 100%);
  box-shadow: inset 0 0 0 1px rgba(16, 185, 129, .14), inset 0 -10px 22px rgba(16, 185, 129, .10), 0 14px 30px -14px rgba(6, 95, 70, .35);
  overflow: hidden;
}
.round-illu { animation: illu-in .7s cubic-bezier(.22, 1, .36, 1) both; }
.round-illu.is-float { animation: illu-in .7s cubic-bezier(.22, 1, .36, 1) both, illu-float 6s ease-in-out .7s infinite; }
@keyframes illu-in { from { opacity: 0; transform: translateY(18px) scale(.9); } to { opacity: 1; transform: none; } }
@keyframes illu-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-7px); } }
@media (prefers-reduced-motion: reduce) { .round-illu, .round-illu.is-float { animation: none; } }
</style>
