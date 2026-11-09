<script setup>
import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ToastHost from '@/components/ui/ToastHost.vue'
import { backButton } from '@/services/telegram'

const route = useRoute()
const router = useRouter()

// Telegram "Orqaga" tugmasi: faqat auth oqimining ichki sahifalarida ko‘rinadi
const goBack = () => router.back()
watch(() => route.path, (p) => {
  if (['/register', '/role'].includes(p) && window.history.length > 1) backButton.show(goBack)
  else backButton.hide(goBack)
})
</script>

<template>
  <RouterView v-slot="{ Component, route: r }">
    <Transition name="page" mode="out-in">
      <component :is="Component" :key="r.matched[0]?.path" />
    </Transition>
  </RouterView>
  <ToastHost />
</template>
