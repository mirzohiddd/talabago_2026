/**
 * Asia/Tashkent vaqt zonasi bilan ishlash.
 * Reklama vaqtlari bazada UTC ISO satri sifatida saqlanadi (masalan "2026-11-06T09:00:00.000Z"),
 * foydalanuvchiga esa doim Toshkent vaqtida ko‘rsatiladi va kiritiladi —
 * qurilma qaysi vaqt zonasida bo‘lishidan qat’i nazar.
 */
export const TZ = 'Asia/Tashkent'

const partsFmt = new Intl.DateTimeFormat('en-US', {
  timeZone: TZ, hourCycle: 'h23',
  year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', second: '2-digit',
})

function parts(date) {
  const m = {}
  for (const p of partsFmt.formatToParts(date)) m[p.type] = p.value
  return { y: +m.year, mo: +m.month, d: +m.day, h: +m.hour % 24, mi: +m.minute, s: +m.second }
}

/** Toshkentning UTC’dan farqi (daqiqada) berilgan paytda. Toshkent uchun doim +300. */
export function tashkentOffsetMinutes(date = new Date()) {
  const p = parts(date)
  const asUtc = Date.UTC(p.y, p.mo - 1, p.d, p.h, p.mi, p.s)
  return Math.round((asUtc - Math.floor(date.getTime() / 1000) * 1000) / 60000)
}

const pad = (n) => String(n).padStart(2, '0')

/** "2026-11-06T14:30" (Toshkent vaqti, <input type="datetime-local">) → UTC ISO */
export function tashkentInputToISO(value) {
  const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/.exec(value || '')
  if (!m) return null
  const guess = Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5])
  const off = tashkentOffsetMinutes(new Date(guess))
  return new Date(guess - off * 60000).toISOString()
}

/** UTC ISO → "2026-11-06T14:30" (Toshkent vaqti, input uchun) */
export function isoToTashkentInput(iso) {
  if (!iso) return ''
  const p = parts(new Date(iso))
  return `${p.y}-${pad(p.mo)}-${pad(p.d)}T${pad(p.h)}:${pad(p.mi)}`
}

/** UTC ISO → "06.11.2026, 14:30" (Toshkent vaqti) */
export function formatTashkent(iso, { seconds = false, date = true } = {}) {
  if (!iso) return '—'
  const p = parts(new Date(iso))
  const time = `${pad(p.h)}:${pad(p.mi)}${seconds ? ':' + pad(p.s) : ''}`
  return date ? `${pad(p.d)}.${pad(p.mo)}.${p.y}, ${time}` : time
}

/** Davomiylikni o‘qiladigan ko‘rinishda: "2 kun 3 soat", "5 daq 20 s" */
import { t } from '@/i18n'

export function humanDuration(ms) {
  const s = Math.max(0, Math.round(ms / 1000))
  const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60
  const D = (n) => t('{n} kun', { n }), Hh = (n) => t('{n} soat', { n }), M = (n) => t('{n} daq', { n }), S = (n) => t('{n} s', { n })
  if (d) return h ? `${D(d)} ${Hh(h)}` : D(d)
  if (h) return m ? `${Hh(h)} ${M(m)}` : Hh(h)
  if (m) return m < 10 && sec ? `${M(m)} ${S(sec)}` : M(m)
  return S(sec)
}
