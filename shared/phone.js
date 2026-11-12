/**
 * O‘zbekiston telefon raqami: +998 XX XXX XX XX (kod + 7 raqam = 9 raqam).
 * Ikkala frontend va backend (app/common.py) bir xil qoidadan foydalanadi.
 */

/** +998 dan keyingi ruxsat etilgan kodlar: mobil operatorlar, shahar (hududiy) kodlari, 55 (VoIP), 78 */
export const PHONE_CODES = [
  '20', '33', '50', '55', '61', '62', '65', '66', '67', '69', '70', '71', '72', '73', '74', '75', '76', '77', '78', '79',
  '80', '87', '88', '90', '91', '92', '93', '94', '95', '97', '98', '99',
]
export const PHONE_PREFIX = '+998'

/** Har qanday kiritishdan (+998 90 123-45-67, 998901234567, 901234567) — +998 dan keyingi raqamlar (ko‘pi bilan 9 ta) */
export function phoneDigits(v = '') {
  const s = String(v ?? '').trim()
  // “+998 …” — prefiksdan keyingi raqamlar (qisman kiritilgan “+998 90 12” ham to‘g‘ri: 9012)
  if (s.startsWith('+998')) return s.slice(4).replace(/\D/g, '').slice(0, 9)
  let d = s.replace(/\D/g, '')
  if (d.length > 9 && d.startsWith('998')) d = d.slice(3)
  return d.slice(0, 9)
}

/** Kiritish paytida: “90 123 45 67” (to‘liq bo‘lmasa ham) */
export function formatLocal(digits = '') {
  const d = phoneDigits(digits)
  return [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)].filter(Boolean).join(' ')
}

/** null — xato yo‘q; aks holda sabab: 'empty' | 'short' | 'code' */
export function phoneProblem(v) {
  const d = phoneDigits(v)
  if (!d) return 'empty'
  if (d.length < 9) return 'short'
  if (!PHONE_CODES.includes(d.slice(0, 2))) return 'code'
  return null
}

/** To‘liq va to‘g‘ri bo‘lsa “+998 90 123 45 67”, aks holda null */
export function formatPhone(v) {
  return phoneProblem(v) ? null : `${PHONE_PREFIX} ${formatLocal(phoneDigits(v))}`
}

/** Foydalanuvchiga ko‘rsatiladigan xato (o‘zbekcha kalit — i18n orqali tarjima qilinadi) */
export const PHONE_MESSAGES = {
  empty: 'Telefon raqamini kiriting',
  short: 'Telefon raqam to‘liq emas: +998 dan keyin 9 ta raqam kiriting',
  code: 'Operator kodi noto‘g‘ri (masalan: 90, 91, 93, 94, 97, 99, 33, 88)',
}