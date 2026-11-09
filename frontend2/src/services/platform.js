/**
 * TalabaGo Support — oddiy brauzer ilovasi (Telegram Mini App emas).
 * Umumiy UI komponentlar (frontend/ dan) shu interfeysni chaqiradi, shuning uchun no-op adapter.
 */
export const haptic = { tap() {}, success() {}, error() {}, select() {} }
export const backButton = { show() {}, hide() {} }
export function openLink(url) {
  window.open(url, '_blank', 'noopener,noreferrer')
}
