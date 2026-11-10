import { t } from '@/i18n'
import { phoneProblem, PHONE_MESSAGES } from '@shared/phone'

// Ism/familiya: lotin yoki kirill harflari, o‘ g‘ belgilari, defis va bo‘sh joy (backend: schemas.NAME_RE bilan bir xil)
const NAME_RE = /^[A-Za-zÀ-ÖØ-öø-ɏЀ-ӿʻʼ‘’'`\- ]+$/

/** Formalar uchun oddiy validatsiya qoidalari. Xabarlar joriy tilda qaytadi. */
export const rules = {
  required: (v) => (v === 0 || (Array.isArray(v) ? v.length : String(v ?? '').trim()) ? null : t('Majburiy maydon')),
  phone: (v) => { const p = phoneProblem(v); return !p || p === 'empty' ? null : t(PHONE_MESSAGES[p]) },
  phoneRequired: (v) => { const p = phoneProblem(v); return p ? t(PHONE_MESSAGES[p]) : null },
  name: (v) => {
    const s = String(v ?? '').trim().replace(/\s+/g, ' ')
    if (!s) return null
    if (s.length < 2) return t('Kamida 2 ta harf kiriting')
    if (s.length > 40) return t('Ko‘pi bilan 40 ta belgi')
    return NAME_RE.test(s) ? null : t('Faqat harflar kiriting (raqam va belgilarsiz)')
  },
  password: (v) => {
    const s = String(v ?? '')
    if (s.length < 8) return t('Parol kamida 8 ta belgidan iborat bo‘lsin')
    if (!/[A-Za-zА-Яа-яЁё]/.test(s) || !/\d/.test(s)) return t('Parolda kamida bitta harf va bitta raqam bo‘lsin')
    return null
  },
  birthDate: (v) => {
    if (!v) return null
    const age = (Date.now() - new Date(v).getTime()) / (365.25 * 864e5)
    return age >= 14 && age <= 70 ? null : t('Tug‘ilgan sana noto‘g‘ri: yosh 14 dan 70 gacha bo‘lishi kerak')
  },
  max: (n) => (v) => (String(v ?? '').trim().length <= n ? null : t('Ko‘pi bilan {n} ta belgi', { n })),
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

/** Profil (Sozlamalar): familiya ixtiyoriy, lekin kiritilsa — to‘g‘ri bo‘lsin */
export const profileSchema = (role) => ({
  firstName: [rules.required, rules.name],
  lastName: [rules.name],
  phone: [rules.phoneRequired],
  telegram: [rules.telegram],
  ...(role === 'student' ? { birthDate: [rules.birthDate] } : {}),
  ...(role === 'employer' ? { company: [rules.required, rules.min(2), rules.max(120)] } : {}),
})

/** Ro‘yxatdan o‘tish: ism va familiya majburiy (backend RegisterIn bilan bir xil) */
export const registerSchema = (role) => ({ ...profileSchema(role), lastName: [rules.required, rules.name] })

/** Server 422 javobidagi maydon xatolari → { maydon: 'xato' } (formada tegishli maydon ostida ko‘rsatish uchun) */
export function serverFieldErrors(e) {
  const out = {}
  for (const x of e?.data?.errors || []) {
    const k = String(x.field || '').split('.')[0]
    if (k && !out[k]) out[k] = t(x.message)
  }
  return out
}