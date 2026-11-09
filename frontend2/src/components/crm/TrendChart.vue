<script setup>
/**
 * Bitta seriyali vaqt grafigi (area + 2px chiziq), hover’da vertikal chiziq va tooltip.
 * Bitta seriya → legend shart emas (sarlavha nomlaydi). Matnlar ink rangida, ma’lumot — brand.
 */
import { ref, computed } from 'vue'

const props = defineProps({
  points: { type: Array, required: true }, // [{ label, value }]
  unit: { type: String, default: '' },
  height: { type: Number, default: 220 },
})
const W = 720
const pad = { l: 36, r: 12, t: 14, b: 28 }
const H = computed(() => props.height)
const max = computed(() => {
  const m = Math.max(1, ...props.points.map((p) => p.value))
  const step = Math.pow(10, Math.floor(Math.log10(m)))
  return Math.ceil(m / step) * step
})
const x = (i) => pad.l + (i * (W - pad.l - pad.r)) / Math.max(1, props.points.length - 1)
const y = (v) => H.value - pad.b - (v / max.value) * (H.value - pad.t - pad.b)
const line = computed(() => props.points.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(''))
const area = computed(() => `${line.value}L${x(props.points.length - 1)},${H.value - pad.b}L${x(0)},${H.value - pad.b}Z`)
const step = computed(() => Math.max(1, Math.ceil(props.points.length / 8)))
const ticks = computed(() => [0, 0.5, 1].map((f) => Math.round(max.value * f)))

const hover = ref(null)
const svg = ref(null)
function onMove(e) {
  const r = svg.value.getBoundingClientRect()
  const px = ((e.clientX - r.left) / r.width) * W
  const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (props.points.length - 1))
  hover.value = Math.min(props.points.length - 1, Math.max(0, i))
}
</script>

<template>
  <div class="relative">
    <svg ref="svg" :viewBox="`0 0 ${W} ${H}`" class="w-full h-auto select-none" role="img" :aria-label="$t('Grafik')" @pointermove="onMove" @pointerleave="hover = null">
      <defs>
        <linearGradient id="trendFill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stop-color="#10B981" stop-opacity=".18" /><stop offset="1" stop-color="#10B981" stop-opacity="0" />
        </linearGradient>
      </defs>
      <g v-for="t in ticks" :key="t">
        <line :x1="pad.l" :x2="W - pad.r" :y1="y(t)" :y2="y(t)" stroke="#ECECEF" :stroke-dasharray="t ? '3 4' : ''" />
        <text :x="pad.l - 8" :y="y(t) + 4" text-anchor="end" class="fill-muted text-[11px] tabular-nums">{{ t }}</text>
      </g>
      <text v-for="(p, i) in points" v-show="i % step === 0" :key="'l' + i" :x="x(i)" :y="H - 8" text-anchor="middle" class="fill-muted text-[11px]">{{ p.label }}</text>
      <path :d="area" fill="url(#trendFill)" class="chart-in" />
      <path :d="line" fill="none" stroke="#10B981" stroke-width="2" stroke-linejoin="round" stroke-linecap="round" class="chart-line" />
      <template v-if="hover !== null">
        <line :x1="x(hover)" :x2="x(hover)" :y1="pad.t" :y2="H - pad.b" stroke="#111" stroke-opacity=".25" />
        <circle :cx="x(hover)" :cy="y(points[hover].value)" r="5" fill="#10B981" stroke="#fff" stroke-width="2" />
      </template>
      <rect :x="pad.l" :y="pad.t" :width="W - pad.l - pad.r" :height="H - pad.t - pad.b" fill="transparent" />
    </svg>
    <div
      v-if="hover !== null"
      class="pointer-events-none absolute top-1 -translate-x-1/2 rounded-xl bg-ink text-white px-3 py-2 text-xs shadow-lg whitespace-nowrap"
      :style="{ left: `${(x(hover) / W) * 100}%` }"
    >
      <p class="text-white/70">{{ points[hover].full || points[hover].label }}</p>
      <p class="font-bold text-sm tabular-nums">{{ points[hover].value }} {{ unit }}</p>
    </div>
  </div>
</template>

<style scoped>
.chart-line { stroke-dasharray: 2000; stroke-dashoffset: 2000; animation: draw 1.2s ease forwards; }
.chart-in { animation: fadein .8s ease .3s both; }
@keyframes draw { to { stroke-dashoffset: 0; } }
@keyframes fadein { from { opacity: 0; } }
</style>
