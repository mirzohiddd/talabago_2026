import { ref, watch, onMounted } from 'vue'
import { search, session } from '@/stores/session'

/**
 * Ro‘yxat sahifalari uchun umumiy composable:
 * yuklash/xato holati + filtrlar + navbar qidiruvi (debounce bilan).
 */
// stale-while-revalidate: sahifaga qaytilganda oxirgi ro‘yxat darhol ko‘rsatiladi, yangisi fonda yuklanadi
const CACHE = new WeakMap() // fetcher → Map(kalit → ro‘yxat)
const MAX_KEYS = 20

export function useList(fetcher, filters) {
  const items = ref([])
  const loading = ref(true)
  const error = ref(null)
  let t
  let seq = 0
  if (!CACHE.has(fetcher)) CACHE.set(fetcher, new Map())
  const cache = CACHE.get(fetcher)

  async function load() {
    const id = ++seq
    const params = { ...(filters?.value ?? filters ?? {}), q: search.query }
    const key = `${session.userId}|${JSON.stringify(params)}`
    const hit = cache.get(key)
    if (hit) { items.value = hit; loading.value = false } else loading.value = true
    error.value = null
    try {
      const res = await fetcher(params)
      if (id !== seq) return // eski so‘rov natijasini tashlab yuborish
      items.value = res
      cache.delete(key)
      cache.set(key, res)
      if (cache.size > MAX_KEYS) cache.delete(cache.keys().next().value)
    } catch (e) {
      if (id === seq && !hit) error.value = e.message || 'Xatolik' // keshdagi ro‘yxat bo‘lsa — o‘sha qoladi
    } finally {
      if (id === seq) loading.value = false
    }
  }

  onMounted(load)
  if (filters) watch(filters, load, { deep: true })
  watch(() => search.query, () => { clearTimeout(t); t = setTimeout(load, 280) })

  return { items, loading, error, reload: load }
}