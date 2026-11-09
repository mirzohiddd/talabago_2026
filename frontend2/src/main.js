import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './services/http'
import { dropSession } from './services/auth'
import { toast } from './stores/toast'
import { i18n } from './i18n'
import { installBootGuards, markBooted } from '@shared/boot'
import './style.css'

// Server 401 qaytarsa (sessiya tugagan / parol almashgan) — login sahifasiga
setUnauthorizedHandler(() => {
  dropSession()
  if (router.currentRoute.value.path !== '/login') router.replace({ path: '/login', query: { expired: '1' } })
})

// Yangi relizdan keyin eski keshlangan chunk’lar sababli bo‘sh ekran bo‘lmasin
installBootGuards(router)

const app = createApp(App).use(i18n).use(router)
app.config.errorHandler = (err) => {
  console.error(err)
  if (err?.message) toast(err.message, 'error')
}
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason?.status !== undefined && e.reason?.message) toast(e.reason.message, 'error')
})
app.mount('#app')
markBooted()
