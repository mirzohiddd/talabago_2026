/**
 * Reklama boshqaruvi — TalabaGo API:
 *   GET    /ads                — barcha reklamalar (administrator)
 *   POST   /ads   (multipart: data=JSON, file, poster)      PATCH /ads/{id} (multipart; fayl ixtiyoriy)
 *   PATCH  /ads/{id}/enabled   PATCH /ads/order { ids }     DELETE /ads/{id}
 * Mini App reklamalarni GET /ads/active dan oladi — server yagona manba, qo‘shimcha “eksport” kerak emas.
 */
import { reactive } from 'vue'
import { http, httpForm } from './http'
import { sortAds } from '@/config/ads'

export const adsStore = reactive({ items: [], loaded: false, error: null })
const find = (id) => adsStore.items.find((a) => a.id === id)

let loading = null
export async function refreshAds() {
  try {
    adsStore.items = await http('/ads')
    adsStore.error = null
  } catch (e) {
    adsStore.error = e.message
  } finally {
    adsStore.loaded = true
  }
}
export function ensureAdsLoaded() {
  if (adsStore.loaded) return Promise.resolve()
  return (loading ??= refreshAds().finally(() => (loading = null)))
}

function toFormData(data, pending) {
  const fd = new FormData()
  const mediaMeta = pending ? { width: pending.width, height: pending.height, duration: pending.duration ?? null, mime: pending.mime } : {}
  fd.append('data', JSON.stringify({ ...data, mediaMeta }))
  if (pending) {
    fd.append('file', pending.file, pending.name)
    if (pending.poster) fd.append('poster', pending.poster, 'poster.jpg')
  }
  return fd
}

export const adsApi = {
  async create(data, pending) {
    await httpForm('/ads', toFormData(data, pending))
    await refreshAds() // tartib raqamlari serverda qayta hisoblanadi
  },
  /** pending = null bo‘lsa, eski fayl saqlanib qoladi */
  async update(id, data, pending = null) {
    await httpForm(`/ads/${id}`, toFormData(data, pending), { method: 'PATCH' })
    await refreshAds()
  },
  async setEnabled(id, enabled) {
    const ad = find(id)
    const prev = ad.enabled
    ad.enabled = enabled // optimistik yangilash
    try {
      Object.assign(ad, await http(`/ads/${id}/enabled`, { method: 'PATCH', body: { enabled } }))
    } catch (e) {
      ad.enabled = prev
      throw e
    }
  },
  async remove(id) {
    await http(`/ads/${id}`, { method: 'DELETE' })
    await refreshAds()
  },
  /** Panel ichidagi preview statistikaga yozilmaydi */
  trackView() {},
  trackClick() {},
  /** Tartibni bir qadam surish: dir = -1 (yuqoriga) | +1 (pastga) */
  async move(id, dir) {
    const list = sortAds(adsStore.items)
    const i = list.findIndex((a) => a.id === id)
    const j = i + dir
    if (i < 0 || j < 0 || j >= list.length) return
    ;[list[i], list[j]] = [list[j], list[i]]
    list.forEach((a, k) => { find(a.id).order = k + 1 })
    await http('/ads/order', { method: 'PATCH', body: { ids: list.map((a) => a.id) } })
  },
}
