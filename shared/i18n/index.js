/**
 * TalabaGo i18n — kalit sifatida o‘zbekcha (lotin) matn ishlatiladi:
 *   t('Ish e’lonlari') → uz: o‘zi, uz-Cyrl: avtomatik kirill, ru/en: lug‘atdan (yo‘q bo‘lsa — o‘zbekcha).
 * Framework’ga bog‘liq emas: Vue’ning reactive() funksiyasi tashqaridan beriladi (shared/ da node_modules yo‘q).
 * Backend ulanganda ham shu lug‘atlar ishlaydi; foydalanuvchi tili PATCH /users/me { language } bilan saqlanadi.
 */
import { toCyrillic } from './translit.js'

export const LOCALES = [
  { value: 'uz', label: 'O‘zbekcha', sub: 'Lotin', flag: '🇺🇿', intl: 'uz-Latn-UZ' },
  { value: 'uz-Cyrl', label: 'Ўзбекча', sub: 'Кирилл', flag: '🇺🇿', intl: 'uz-Cyrl-UZ' },
  { value: 'ru', label: 'Русский', sub: 'Russian', flag: '🇷🇺', intl: 'ru-RU' },
  { value: 'en', label: 'English', sub: 'Ingliz', flag: '🇬🇧', intl: 'en-GB' },
]
// Lug‘atlar faqat kerak bo‘lganda yuklanadi (alohida chunk): o‘zbek tilidagi foydalanuvchi ~110 KB ortiqcha JS yuklamaydi
const DICTS = {}
const LOADERS = { ru: () => import('./ru.js'), en: () => import('./en.js') }
export function loadDict(locale) {
  if (!LOADERS[locale] || DICTS[locale]) return Promise.resolve()
  return LOADERS[locale]().then((m) => { DICTS[locale] = m.default }).catch(() => { /* tarmoq xatosi — o‘zbekcha ko‘rsatiladi */ })
}
const cyrCache = new Map()

function fill(s, params) {
  if (!params) return s
  return s.replace(/\{(\w+)\}/g, (m, k) => (params[k] ?? m))
}

export function translate(locale, key, params) {
  if (key == null) return ''
  let s = key
  if (locale === 'uz-Cyrl') {
    if (!cyrCache.has(key)) cyrCache.set(key, toCyrillic(key))
    s = cyrCache.get(key)
  } else if (DICTS[locale]) {
    s = DICTS[locale][key] ?? key
    // Tarjimasi yo‘q kalitlarni yig‘ish (test va lug‘atni to‘ldirish uchun): window.__i18nMissing
    if (DICTS[locale][key] == null && typeof window !== 'undefined' && /[a-z]/i.test(key)) (window.__i18nMissing ||= new Set()).add(key)
  }
  return fill(s, params)
}

/** Kontent (e’lon nomi, tavsif): faqat kirill rejimida transliteratsiya qilinadi, boshqa tillarda o‘zgarmaydi. */
export function translateContent(locale, text) {
  return locale === 'uz-Cyrl' ? toCyrillic(text) : text
}

export function createI18n({ reactive, storageKey, fallback = 'uz' }) {
  let initial = fallback
  try { initial = localStorage.getItem(storageKey) || fallback } catch {}
  if (!LOCALES.some((l) => l.value === initial)) initial = fallback
  const state = reactive({ locale: initial })
  /** Boshlang‘ich til lug‘ati yuklanguncha ilova mount qilinmaydi (rus/ingliz foydalanuvchida o‘zbekcha “miltillash” bo‘lmasin) */
  const ready = loadDict(initial)

  const t = (key, params) => translate(state.locale, key, params)
  const tc = (text) => translateContent(state.locale, text)
  const intl = () => LOCALES.find((l) => l.value === state.locale)?.intl || 'uz-Latn-UZ'

  function setLocale(v) {
    if (!LOCALES.some((l) => l.value === v)) return Promise.resolve()
    try { localStorage.setItem(storageKey, v) } catch {}
    return loadDict(v).then(() => {
      state.locale = v
      if (typeof document !== 'undefined') document.documentElement.lang = v === 'uz-Cyrl' ? 'uz-Cyrl' : v
    })
  }
  if (typeof document !== 'undefined') document.documentElement.lang = state.locale

  /** “3 soat oldin” */
  function ago(iso) {
    const diff = (Date.now() - new Date(iso).getTime()) / 1000
    if (diff < 60) return t('hozirgina')
    if (diff < 3600) return t('{n} daqiqa oldin', { n: Math.floor(diff / 60) })
    if (diff < 86400) return t('{n} soat oldin', { n: Math.floor(diff / 3600) })
    if (diff < 86400 * 7) return t('{n} kun oldin', { n: Math.floor(diff / 86400) })
    return date(iso)
  }
  // Brauzerlarda uz-Latn/uz-Cyrl uchun Intl ma’lumotlari to‘liq emas ("2026 M11 1") — o‘zbekcha oy nomlari qo‘lda
  const UZ_MONTHS = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek']
  function parts(iso) {
    const p = Object.fromEntries(new Intl.DateTimeFormat('en-GB', { timeZone: 'Asia/Tashkent', year: 'numeric', month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' })
      .formatToParts(new Date(iso)).map((x) => [x.type, x.value]))
    return { y: +p.year, m: +p.month, d: +p.day, time: `${p.hour}:${p.minute}` }
  }
  const date = (iso, opts = { day: 'numeric', month: 'short', year: 'numeric' }) => {
    if (!iso || Number.isNaN(Date.parse(iso))) return '—'
    if (state.locale === 'uz' || state.locale === 'uz-Cyrl') {
      const p = parts(iso)
      const sameYear = p.y === parts(new Date().toISOString()).y
      let s = `${p.d}-${UZ_MONTHS[p.m - 1]}`
      if (opts.year && !(opts.hour && sameYear)) s += ` ${p.y}`
      if (opts.hour) s += `, ${p.time}`
      return state.locale === 'uz-Cyrl' ? toCyrillic(s) : s
    }
    try { return new Intl.DateTimeFormat(intl(), { timeZone: 'Asia/Tashkent', ...opts }).format(new Date(iso)) } catch { return new Date(iso).toLocaleDateString() }
  }
  const dateTime = (iso) => date(iso, { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })

  return {
    state, t, tc, setLocale, ago, date, dateTime, intl, ready,
    install(app) {
      app.config.globalProperties.$t = t
      app.config.globalProperties.$tc = tc
      app.config.globalProperties.$ago = ago
      app.config.globalProperties.$date = date
      app.config.globalProperties.$dateTime = dateTime
    },
  }
}