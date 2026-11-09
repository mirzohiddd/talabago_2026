/**
 * Mini App reklama carousel’i: GET /ads/active — reklamalar TalabaGo Support panelida boshqariladi.
 * Server faqat aktiv/rejalashtirilgan reklamalarni qaytaradi; carousel vaqtni har soniyada tekshiradi.
 */
import { reactive } from 'vue'
import { http, ping, mediaUrl } from './http'

export const adsFeed = reactive({ items: [], loaded: false, error: null })
const withUrls = (a) => ({ ...a, media: { ...a.media, src: mediaUrl(a.media?.src), posterSrc: mediaUrl(a.media?.posterSrc) } })

let loading = null
let timer = null
export async function refreshFeed() {
  try {
    adsFeed.items = (await http('/ads/active')).map(withUrls)
    adsFeed.error = null
  } catch (e) {
    adsFeed.error = e.message // eski ro‘yxat saqlanib qoladi
  } finally {
    adsFeed.loaded = true
  }
}
export function ensureFeedLoaded() {
  if (!timer) timer = setInterval(refreshFeed, 5 * 60 * 1000)
  if (adsFeed.loaded) return Promise.resolve()
  return (loading ??= refreshFeed().finally(() => (loading = null)))
}
export const trackAdView = (id) => ping(`/ads/${id}/view`)
export const trackAdClick = (id) => ping(`/ads/${id}/click`)
