import { ref, getCurrentScope, onScopeDispose } from 'vue'

/**
 * Har soniyada yangilanadigan umumiy "hozir" vaqti.
 * Reklamalar boshlanish/tugash vaqtiga 1 soniya aniqlikda avtomatik o‘tadi.
 * Ilova fonda bo‘lsa (Telegram yopilgan), qaytganda darhol yangilanadi.
 */
const now = ref(Date.now())
let timer = null
let users = 0
const tick = () => { now.value = Date.now() }

export function useNow() {
  users++
  if (!timer) {
    timer = setInterval(tick, 1000)
    document.addEventListener('visibilitychange', tick)
    window.addEventListener('focus', tick)
  }
  if (getCurrentScope()) {
    onScopeDispose(() => {
      if (--users === 0) {
        clearInterval(timer); timer = null
        document.removeEventListener('visibilitychange', tick)
        window.removeEventListener('focus', tick)
      }
    })
  }
  return now
}
