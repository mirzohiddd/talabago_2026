<script setup>
defineProps({ count: { type: Number, default: 3 }, media: Boolean })
</script>
<template>
  <div class="grid gap-3">
    <div v-for="i in count" :key="i" class="card p-4">
      <div v-if="media" class="skeleton h-36 mb-4" />
      <div class="flex gap-3">
        <div class="skeleton size-12 shrink-0" />
        <div class="flex-1 space-y-2 pt-1">
          <div class="skeleton h-4 w-3/4" />
          <div class="skeleton h-3 w-1/2" />
        </div>
      </div>
      <div class="flex gap-2 mt-4"><div class="skeleton h-6 w-20" /><div class="skeleton h-6 w-16" /></div>
    </div>
  </div>
</template>
