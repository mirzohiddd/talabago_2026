import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import { i18n } from './i18n'
import { initTelegram } from './services/telegram'
import { setUnauthorizedHandler } from './services/http'
import { logout, toast } from './stores/session'
import { installBootGuards, markBooted } from '@shared/boot'
import './style.css'

initTelegram()

// Token muddati tugasa yoki hisob o‘chirilsa — qayta kirish
setUnauthorizedHandler(() => {
  logout()
  router.replace('/login')
})

// Yangi relizdan keyin eski keshlangan chunk’lar sababli bo‘sh ekran bo‘lmasin
installBootGuards(router)

const app = createApp(App).use(i18n).use(router)
// Kutilmagan xatolar foydalanuvchiga tushunarli xabar bilan ko‘rsatiladi (oq ekran o‘rniga)
app.config.errorHandler = (err) => {
  console.error(err)
  if (err?.message) toast(err.message, 'error')
}
window.addEventListener('unhandledrejection', (e) => {
  if (e.reason?.status !== undefined && e.reason?.message) toast(e.reason.message, 'error')
})
// Tanlangan til lug‘ati (rus/ingliz) yuklangach mount — o‘zbek tilida kutish yo‘q
i18n.ready.finally(() => {
  app.mount('#app')
  markBooted()
})