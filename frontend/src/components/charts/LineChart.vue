<script setup>
/**
 * Yengil SVG chiziqli grafik (kutubxonasiz). series: [{ key, label, color, values: number[] }], labels: string[] (sanalar).
 * Kursor/barmoq bilan ustiga kelganda o‘sha kunning qiymatlari ko‘rsatiladi.
 */
import { computed, ref } from 'vue'
const props = defineProps({ labels: { type: Array, required: true }, series: { type: Array, required: true }, height: { type: Number, default: 220 } })
const W = 640
const H = computed(() => props.height)
const P = { l: 34, r: 12, t: 12, b: 26 }
const max = computed(() => {
  const m = Math.max(1, ...props.series.flatMap((s) => s.values))
  const step = m <= 5 ? 1 : m <= 10 ? 2 : Math.ceil(m / 5)
  return Math.ceil(m / step) * step
})
const ticks = computed(() => [0, 0.25, 0.5, 0.75, 1].map((k) => Math.round(max.value * k)).filter((v, i, a) => a.indexOf(v) === i))
const x = (i) => P.l + (props.labels.length <= 1 ? 0 : (i / (props.labels.length - 1)) * (W - P.l - P.r))
const y = (v) => P.t + (1 - v / max.value) * (H.value - P.t - P.b)
const path = (vals) => vals.map((v, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ')
const area = (vals) => `${path(vals)} L${x(vals.length - 1)},${y(0)} L${x(0)},${y(0)} Z`
const every = computed(() => Math.max(1, Math.ceil(props.labels.length / 6)))
const short = (d) => { const [, m, day] = d.split('-'); return `${+day}.${m}` }
const hover = ref(null)
function move(e) {
  const r = e.currentTarget.getBoundingClientRect()
  const px = ((e.clientX ?? e.touches?.[0]?.clientX) - r.left) / r.width * W
  const i = Math.round(((px - P.l) / (W - P.l - P.r)) * (props.labels.length - 1))
  hover.value = Math.min(props.labels.length - 1, Math.max(0, i))
}
</script>

<template>
  <div class="relative">
    <svg :viewBox="`0 0 ${W} ${H}`" class="w-full h-auto select-none touch-pan-y" role="img" @mousemove="move" @touchstart.passive="move" @touchmove.passive="move" @mouseleave="hover = null">
      <g v-for="t in ticks" :key="t">
        <line :x1="P.l" :x2="W - P.r" :y1="y(t)" :y2="y(t)" stroke="#eef0f2" />
        <text :x="P.l - 6" :y="y(t) + 4" text-anchor="end" font-size="11" fill="#8a8f98">{{ t }}</text>
      </g>
      <text v-for="(d, i) in labels" v-show="i % every === 0 || i === labels.length - 1" :key="d" :x="x(i)" :y="H - 6" text-anchor="middle" font-size="11" fill="#8a8f98">{{ short(d) }}</text>
      <template v-for="s in series" :key="s.key">
        <path v-if="s.fill" :d="area(s.values)" :fill="s.color" opacity="0.10" />
        <path :d="path(s.values)" fill="none" :stroke="s.color" stroke-width="2.6" stroke-linejoin="round" stroke-linecap="round" />
      </template>
      <g v-if="hover !== null">
        <line :x1="x(hover)" :x2="x(hover)" :y1="P.t" :y2="H - P.b" stroke="#111" stroke-dasharray="3 3" opacity=".35" />
        <circle v-for="s in series" :key="s.key" :cx="x(hover)" :cy="y(s.values[hover])" r="4.5" :fill="s.color" stroke="#fff" stroke-width="2" />
      </g>
    </svg>
    <div v-if="hover !== null" class="absolute top-1 right-1 rounded-xl bg-white/95 border border-line shadow-sm px-3 py-2 text-xs pointer-events-none">
      <p class="font-bold mb-1">{{ labels[hover] }}</p>
      <p v-for="s in series" :key="s.key" class="flex items-center gap-1.5"><span class="size-2 rounded-full" :style="{ background: s.color }" />{{ s.label }}: <b>{{ s.values[hover] }}</b></p>
    </div>
  </div>
</template>
