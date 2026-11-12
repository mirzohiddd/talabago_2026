import { t, ago } from '@/i18n'
import { PERIOD_SHORT } from '@/config/status'

export const money = (n) => new Intl.NumberFormat('ru-RU').format(n || 0).replace(/[  ,]/g, ' ')
export const timeAgo = (iso) => ago(iso)
/** Maosh noma’lum bo‘lsa (admin e’loni) — “Kelishiladi” */
export const salaryText = (j) => (j.salaryNegotiable || j.salary == null ? t('Kelishiladi') : `${money(j.salary)} ${t('so‘m')} / ${t(PERIOD_SHORT[j.salaryPeriod] || 'oy')}`)
export const priceText = (h) => (h.priceNegotiable || h.price == null ? t('Kelishiladi') : `${money(h.price)} ${t('so‘m')} / ${t('oy')}`)
export const fileSize = (b) => (b > 1048576 ? `${(b / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(b / 1024))} KB`)
export const initials = (name = '') =>
  name.split(' ').filter(Boolean).slice(0, 2).map((s) => s[0]).join('').toUpperCase() || 'T'
export const pluralize = (n, word) => `${n} ta ${word}`
export const telLink = (p = '') => `tel:${p.replace(/[^\d+]/g, '')}`
export const tgLink = (u = '') => `https://t.me/${u.replace(/^@/, '')}`