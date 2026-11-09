/**
 * Ilova yuklanishini himoyalash (ikkala frontend uchun).
 *
 * Yangi versiya chiqqanda Telegram WebView / brauzer eski index.html’ni keshdan ochishi mumkin — u esa serverda
 * endi yo‘q bo‘lgan JS bo‘laklarini (chunk) so‘raydi va sahifa bo‘sh qoladi. Bunday xato ushlanadi va sahifa
 * BIR MARTA qayta yuklanadi (cheksiz sikl bo‘lmasligi uchun sessionStorage belgisi bilan).
 */
const KEY = 'talabago_chunk_reload'
const CHUNK_RE = /Failed to fetch dynamically imported module|Importing a module script failed|error loading dynamically imported module|Unable to preload CSS|Loading chunk/i

/** Qayta yuklash — foydalanuvchi ochmoqchi bo‘lgan sahifaning o‘zida (hash va history rejimlari uchun). */
function reloadOnce(href) {
  try {
    if (sessionStorage.getItem(KEY)) return false
    sessionStorage.setItem(KEY, String(Date.now()))
  } catch { /* storage yopiq bo‘lsa ham bir marta qayta yuklaymiz */ }
  const url = href ? new URL(href, window.location.href) : null
  if (url && url.href !== window.location.href) {
    if (url.pathname === window.location.pathname && url.search === window.location.search) {
      window.history.replaceState(window.history.state, '', url.href) // faqat hash farq qiladi → manzilni almashtirib qayta yuklaymiz
      window.location.reload()
    } else {
      window.location.assign(url.href)
    }
  } else {
    window.location.reload()
  }
  return true
}

export function installBootGuards(router) {
  let pending = null // hozir ochilayotgan sahifa (chunk yuklanmasa — aynan shu sahifaga qayta yuklanadi)
  router.beforeEach((to) => { pending = router.resolve(to).href })
  router.afterEach(() => { pending = null })
  window.addEventListener('vite:preloadError', (e) => {
    if (reloadOnce(pending)) e.preventDefault()
  })
  router.onError((err, to) => {
    if (CHUNK_RE.test(String(err?.message || err))) reloadOnce(to ? router.resolve(to).href : pending)
  })
  // Muvaffaqiyatli ishga tushgandan keyin belgi tozalanadi — keyingi relizda yana ishlaydi
  setTimeout(() => { try { sessionStorage.removeItem(KEY) } catch { /* */ } }, 15000)
}

/** index.html dagi zaxira “yuklanmoqda / yuklanmadi” ekranini o‘chirish (Vue mount bo‘lganda chaqiriladi). */
export function markBooted() {
  window.__talabagoBooted = true
}
