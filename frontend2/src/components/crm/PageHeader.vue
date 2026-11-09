<script setup>
/** CRM sahifa sarlavhasi: kichik dumaloq illustratsiya + nom (+ ixtiyoriy izoh), o‘ngda amallar. */
import RoundIllu from '@/components/brand/RoundIllu.vue'
defineProps({ title: String, subtitle: String, illu: String })
</script>
<template>
  <div class="flex flex-wrap items-center gap-3 mb-6 animate-fade-up">
    <div class="mr-auto min-w-0 flex items-center gap-3.5">
      <RoundIllu v-if="illu" :kind="illu" :size="56" :float="false" class="hidden sm:block" />
      <div class="min-w-0">
        <h1 class="text-[26px] font-extrabold tracking-tight leading-tight">{{ title }}</h1>
        <p v-if="subtitle || $slots.subtitle" class="text-sm text-muted mt-0.5"><slot name="subtitle">{{ subtitle }}</slot></p>
      </div>
    </div>
    <div class="flex flex-wrap items-center gap-2"><slot /></div>
  </div>
</template>
