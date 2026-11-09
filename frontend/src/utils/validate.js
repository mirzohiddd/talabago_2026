import { t } from '@/i18n'
import { normalizePhone } from './format'

/** Formalar uchun oddiy validatsiya qoidalari. Xabarlar joriy tilda qaytadi. */
export const rules = {
  required: (v) => (v === 0 || (Array.isArray(v) ? v.length : String(v ?? '').trim()) ? null : t('Majburiy maydon')),
  phone: (v) => (!v || normalizePhone(v) ? null : t('Telefon raqam noto‘g‘ri: +998 XX XXX XX XX')),
  telegram: (v) => (!v || /^@?[a-zA-Z][\w]{4,31}$/.test(v.trim()) ? null : t('Telegram username noto‘g‘ri (masalan, @talabago)')),
  min: (n) => (v) => (String(v ?? '').trim().length >= n ? null : t('Kamida {n} ta belgi', { n })),
  positive: (v) => (+v > 0 ? null : t('Musbat son kiriting')),
  url: (v) => (!v || /^https?:\/\/\S+\.\S+/.test(v) ? null : t('Havola http:// yoki https:// bilan boshlanishi kerak')),
}

/** schema: { field: [rule, rule] } → { field: 'xato' } (bo‘sh obyekt — xatosiz) */
export function validate(form, schema) {
  const errors = {}
  for (const [k, list] of Object.entries(schema)) {
    for (const r of list) {
      const e = r(form[k], form)
      if (e) { errors[k] = e; break }
    }
  }
  return errors
}

export const profileSchema = (role) => ({
  firstName: [rules.required, rules.min(2)],
  phone: [rules.required, rules.phone],
  telegram: [rules.telegram],
  ...(role === 'employer' ? { company: [rules.required, rules.min(2)] } : {}),
})
