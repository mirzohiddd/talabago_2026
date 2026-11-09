/**
 * TalabaGo Support — avtomatik yangilanish (samarali polling).
 *
 * Har LIVE_MS da faqat GET /crm/changes so‘raladi: u har bir kolleksiyaning o‘zgarish belgisini qaytaradi (server JSON’ni
 * o‘qimaydi — juda arzon). Belgisi o‘zgargan ro‘yxatgina qayta yuklanadi (masalan, yangi murojaat → faqat tickets).
 *  - Sahifa yashirin bo‘lsa (boshqa tab / ekran o‘chgan) so‘rov yuborilmaydi; qaytganda, fokusda va internet tiklanganda darhol tekshiriladi.
 *  - Tarmoq xatosida oraliq 2× dan 60 soniyagacha uzayadi, muvaffaqiyatdan keyin tiklanadi.
 *  - 401 bo‘lsa http.js login sahifasiga qaytaradi.
 */
import { reactive } from 'vue'
import { http } from './http'
import { known, refreshCollections } from './crm'
import { adsStore, refreshAds } from './ads'

export const LIVE_MS = 5000
const MAX_MS = 60000

export const live = reactive({ running: false, lastCheck: 0, lastChange: 0, error: null })

let timer = 0
let delay = LIVE_MS
let inflight = null

async function check() {
  const { versions } = await http('/crm/changes')
  const changed = Object.keys(versions).filter((k) => known[k] !== undefined && known[k] !== versions[k])
  if (changed.length) {
    const crmKeys = changed.filter((k) => k !== 'ads')
    const jobs = []
    if (crmKeys.length) jobs.push(refreshCollections(crmKeys, versions))
    if (changed.includes('ads') && adsStore.loaded) jobs.push(refreshAds(versions.ads))
    await Promise.all(jobs)
    live.lastChange = Date.now()
  }
  live.lastCheck = Date.now()
}

/** Hozir tekshirish (parallel chaqiruvlar bitta so‘rovga birlashadi) */
export function syncNow() {
  if (!inflight) {
    inflight = check()
      .then(() => { live.error = null; delay = LIVE_MS })
      .catch((e) => { live.error = e.message; if (e.status !== 401) delay = Math.min(delay * 2, MAX_MS) })
      .finally(() => { inflight = null })
  }
  return inflight
}

function schedule() {
  clearTimeout(timer)
  if (!live.running) return
  timer = setTimeout(async () => {
    if (document.visibilityState === 'visible') await syncNow()
    schedule()
  }, delay)
}

function wake() {
  if (!live.running || document.visibilityState !== 'visible') return
  syncNow().finally(schedule)
}

export function startLive() {
  if (live.running) return
  live.running = true
  document.addEventListener('visibilitychange', wake)
  window.addEventListener('focus', wake)
  window.addEventListener('online', wake)
  schedule()
}

export function stopLive() {
  live.running = false
  clearTimeout(timer)
  document.removeEventListener('visibilitychange', wake)
  window.removeEventListener('focus', wake)
  window.removeEventListener('online', wake)
}
