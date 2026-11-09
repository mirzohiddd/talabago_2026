<script setup>
import ToastHost from '@/components/ui/ToastHost.vue'
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <Transition name="fade" mode="out-in">
      <component :is="Component" :key="route.matched[0]?.path" />
    </Transition>
  </RouterView>
  <ToastHost />
</template>
