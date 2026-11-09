/**
 * Telegram Mini Apps SDK uchun yupqa qobiq (telegram-web-app.js).
 * Telegram tashqarisida (brauzerda) ham xavfsiz ishlaydi — barcha chaqiruvlar no-op.
 */
const tg = typeof window !== 'undefined' ? window.Telegram?.WebApp : undefined

export const isTelegram = Boolean(tg && tg.initData)

export function initTelegram() {
  if (!tg) return
  try {
    tg.ready()
    tg.expand()
    tg.setHeaderColor?.('#FFFFFF')
    tg.setBackgroundColor?.('#FFFFFF')
    tg.setBottomBarColor?.('#FFFFFF')
    tg.disableVerticalSwipes?.()
    // Telegram viewport: klaviatura / panel o‘zgarganda balandlikni CSS’ga uzatish
    const setH = () => document.documentElement.style.setProperty('--app-height', `${tg.viewportStableHeight || window.innerHeight}px`)
    setH()
    tg.onEvent?.('viewportChanged', setH)
  } catch (e) {
    console.warn('[telegram] init', e)
  }
}

/** Telegram foydalanuvchisi (faqat UI uchun; backendda initData tekshiriladi). */
export function getTelegramUser() {
  return tg?.initDataUnsafe?.user ?? null
}

/** Backendga (FastAPI) yuboriladigan imzolangan initData satri. */
export function getInitData() {
  return tg?.initData ?? ''
}

export const haptic = {
  tap: () => tg?.HapticFeedback?.impactOccurred?.('light'),
  success: () => tg?.HapticFeedback?.notificationOccurred?.('success'),
  error: () => tg?.HapticFeedback?.notificationOccurred?.('error'),
  select: () => tg?.HapticFeedback?.selectionChanged?.(),
}

export const backButton = {
  show(handler) {
    if (!tg?.BackButton) return
    tg.BackButton.onClick(handler)
    tg.BackButton.show()
  },
  hide(handler) {
    if (!tg?.BackButton) return
    if (handler) tg.BackButton.offClick(handler)
    tg.BackButton.hide()
  },
}

export function openLink(url) {
  // t.me havolalari Telegram ichida ochiladi, qolganlari — ichki brauzerda
  if (/^https:\/\/t\.me\//i.test(url) && tg?.openTelegramLink) return tg.openTelegramLink(url)
  if (tg?.openLink) tg.openLink(url)
  else window.open(url, '_blank', 'noopener')
}
