import { t } from '@/i18n'

export const money = (n) => new Intl.NumberFormat('ru-RU').format(n || 0).replace(/[  ,]/g, ' ')

const PERIOD_SHORT = { hour: 'soat', day: 'kun', week: 'hafta', month: 'oy' }
/** “25 000 so‘m / soat” */
export const salaryText = (j) => `${money(j.salary)} ${t('so‘m')} / ${t(PERIOD_SHORT[j.salaryPeriod] || 'oy')}`
export const priceText = (h) => `${money(h.price)} ${t('so‘m')} / ${t('oy')}`

export const initials = (name = '') =>
  name.split(' ').filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase() || 'T'

export const fileSize = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`)

/** Telefon: +998 XX XXX XX XX (9 raqam) */
export function normalizePhone(v = '') {
  const d = v.replace(/\D/g, '').replace(/^998/, '')
  return d.length === 9 ? `+998 ${d.slice(0, 2)} ${d.slice(2, 5)} ${d.slice(5, 7)} ${d.slice(7)}` : null
}
export const telLink = (p = '') => `tel:${p.replace(/[^\d+]/g, '')}`
export const tgLink = (u = '') => `https://t.me/${u.replace(/^@/, '')}`
