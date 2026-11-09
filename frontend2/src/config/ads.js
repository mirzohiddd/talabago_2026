/**
 * Reklama moduli: umumiy shartnoma (frontend/ va frontend2/ da AYNAN bir xil fayl).
 * Holat mantiqi sof funksiyalar — backendda ham xuddi shunday hisoblanadi.
 *
 * Reklama obyekti:
 * { id, name, type: 'image'|'video', title, description, link, placements: string[],
 *   startAt: ISO(UTC), endAt: ISO(UTC), enabled: boolean, order: number,
 *   media: { src?, posterSrc?, key?, posterKey?, mime, size, width, height, duration? },
 *   views, clicks, createdAt }
 */

export const AD_TYPES = [
  { value: 'image', label: 'Rasm' },
  { value: 'video', label: 'Video' },
]

/** Fayl cheklovlari. Video brauzer xotirasida (IndexedDB) saqlanadi — localStorage’ga hech qachon yozilmaydi. */
export const MEDIA_RULES = {
  image: {
    mimes: ['image/jpeg', 'image/png', 'image/webp'],
    exts: ['jpg', 'jpeg', 'png', 'webp'],
    maxBytes: 2 * 1024 * 1024,
    label: 'JPG, PNG yoki WebP · 2 MB gacha',
  },
  video: {
    mimes: ['video/mp4', 'video/webm'],
    exts: ['mp4', 'webm'],
    maxBytes: 20 * 1024 * 1024,
    maxSeconds: 60,
    label: 'MP4 yoki WebM · 20 MB va 60 soniyagacha',
  },
}
/** Carousel nisbati 5:3 — tavsiya etilgan o‘lcham 1200×720 */
export const AD_ASPECT = 5 / 3
export const IMAGE_SLIDE_MS = 5000

/** Reklama ko‘rsatiladigan sahifalar (carousel faqat shu ro‘yxat sahifalarida, navbar ostida). "all" — barchasi. */
export const AD_PLACEMENTS = [
  { value: '/student/jobs', label: 'Talaba · Ishlar', group: 'Talaba' },
  { value: '/student/housing', label: 'Talaba · Turar joy', group: 'Talaba' },
  { value: '/employer/jobs', label: 'Ish beruvchi · Ishlar', group: 'Ish beruvchi' },
  { value: '/landlord/houses', label: 'Uy egasi · Uylar', group: 'Uy egasi' },
]
export const PLACEMENT_PAGES = AD_PLACEMENTS.map((p) => p.value)

export function placementLabels(list = []) {
  if (list.includes('all')) return ['Barcha sahifalar']
  return list.map((v) => AD_PLACEMENTS.find((p) => p.value === v)?.label || v)
}

/** Holatlar: Muddati tugagan > Noaktiv > Rejalashtirilgan > Ko‘rsatilmoqda */
export const AD_STATES = {
  live: { label: 'Ko‘rsatilmoqda', tone: 'green' },
  scheduled: { label: 'Rejalashtirilgan', tone: 'blue' },
  inactive: { label: 'Noaktiv', tone: 'gray' },
  expired: { label: 'Muddati tugagan', tone: 'red' },
}

export function adState(ad, now = Date.now()) {
  const start = Date.parse(ad.startAt)
  const end = Date.parse(ad.endAt)
  if (now >= end) return 'expired'
  if (!ad.enabled) return 'inactive'
  if (now < start) return 'scheduled'
  return 'live'
}

export function isAdVisible(ad, placement, now = Date.now()) {
  if (adState(ad, now) !== 'live') return false
  if (!PLACEMENT_PAGES.includes(placement)) return false
  return ad.placements.includes('all') || ad.placements.includes(placement)
}

/** Keyingi holat o‘zgarishigacha qolgan vaqt (ms) — CRM’dagi teskari sanoq uchun */
export function msToNextChange(ad, now = Date.now()) {
  const s = adState(ad, now)
  if (s === 'scheduled') return Date.parse(ad.startAt) - now
  if (s === 'live' || s === 'inactive') return Date.parse(ad.endAt) - now
  return null
}

/** Carousel tartibi: kichik "order" birinchi, teng bo‘lsa — avval yaratilgani */
export function sortAds(list) {
  return [...list].sort((a, b) => (a.order ?? 999) - (b.order ?? 999) || Date.parse(a.createdAt) - Date.parse(b.createdAt))
}
