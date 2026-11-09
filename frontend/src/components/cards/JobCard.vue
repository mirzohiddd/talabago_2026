<script setup>
import { computed } from 'vue'
import { Briefcase, MapPin, Heart, Clock, Wifi, CheckCircle2 } from 'lucide-vue-next'
import { salaryText } from '@/utils/format'
import { JOB_TYPES, WORK_TIMES } from '@/config/roles'

const props = defineProps({ job: { type: Object, required: true }, showSave: Boolean })
defineEmits(['open', 'save'])
const isNew = computed(() => Date.now() - Date.parse(props.job.createdAt) < 86400000)
const typeLabel = computed(() => JOB_TYPES.find((x) => x.value === props.job.type)?.label)
const timeLabel = computed(() => WORK_TIMES.find((x) => x.value === props.job.workTime)?.label)
</script>

<template>
  <article class="card card-hover p-4 cursor-pointer flex flex-col" tabindex="0" role="button" :aria-label="job.title" data-testid="job-card" @click="$emit('open', job)" @keydown.enter="$emit('open', job)">
    <div class="flex gap-3">
      <span class="size-12 rounded-2xl bg-brand-50 text-brand-600 grid place-items-center shrink-0"><Briefcase class="size-[22px]" /></span>
      <div class="min-w-0 flex-1">
        <div class="flex items-start gap-2">
          <h3 class="font-bold text-[16px] leading-snug line-clamp-2 flex-1">{{ $tc(job.title) }}</h3>
          <span v-if="isNew" class="shrink-0 h-[22px] px-2 rounded-full bg-brand text-white text-[11px] font-bold grid place-items-center">{{ $t('Yangi') }}</span>
        </div>
        <p class="text-[13px] text-muted mt-0.5 truncate">{{ job.company }}</p>
      </div>
    </div>
    <p class="mt-3 font-extrabold text-[17px] tracking-tight">{{ salaryText(job) }}</p>
    <p class="mt-1 text-[13px] text-ink-2 flex items-center gap-1.5">
      <component :is="job.format === 'online' ? Wifi : MapPin" class="size-3.5 text-muted shrink-0" />
      <span class="truncate">{{ job.format === 'online' ? $t('Masofaviy (online)') : `${$t(job.district || '')}, ${$t(job.city)}` }}</span>
      <span class="text-muted shrink-0">· {{ $ago(job.createdAt) }}</span>
    </p>
    <div class="mt-3 pt-3 border-t border-line flex flex-wrap items-center gap-1.5 mt-auto">
      <span class="tag tag-brand">{{ $t(typeLabel) }}</span>
      <span class="tag">{{ job.format === 'online' ? 'Online' : 'Offline' }}</span>
      <span v-if="timeLabel" class="tag"><Clock class="size-3" />{{ $t(timeLabel) }}</span>
      <span v-if="job.applied" class="ml-auto inline-flex items-center gap-1 text-[12px] font-semibold text-success whitespace-nowrap"><CheckCircle2 class="size-4" />{{ $t('Ariza yuborilgan') }}</span>
      <button
        v-else-if="showSave" :class="['ml-auto size-9 grid place-items-center rounded-full transition active:scale-90', job.saved ? 'text-brand-600 bg-brand-50' : 'text-muted hover:bg-surface']"
        :aria-label="job.saved ? $t('Saqlanganlardan olib tashlash') : $t('Saqlash')" :aria-pressed="job.saved" data-testid="save-job" @click.stop="$emit('save', job)"
      ><Heart class="size-[18px]" :fill="job.saved ? 'currentColor' : 'none'" /></button>
    </div>
  </article>
</template>

<style scoped>
@reference "../../style.css";
.tag { @apply inline-flex items-center gap-1 h-6 px-2 rounded-lg text-[11.5px] font-semibold bg-surface text-ink-2 whitespace-nowrap; }
.tag-brand { @apply bg-brand-50 text-brand-700; }
</style>
