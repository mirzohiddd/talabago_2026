import { ref, watch, onMounted } from 'vue'
import { search } from '@/stores/session'

/**
 * Ro‘yxat sahifalari uchun umumiy composable:
 * yuklash/xato holati + filtrlar + navbar qidiruvi (debounce bilan).
 */
export function useList(fetcher, filters) {
  const items = ref([])
  const loading = ref(true)
  const error = ref(null)
  let t
  let seq = 0

  async function load() {
    const id = ++seq
    loading.value = true
    error.value = null
    try {
      const res = await fetcher({ ...(filters?.value ?? filters ?? {}), q: search.query })
      if (id !== seq) return // eski so‘rov natijasini tashlab yuborish
      items.value = res
    } catch (e) {
      if (id === seq) error.value = e.message || 'Xatolik'
    } finally {
      if (id === seq) loading.value = false
    }
  }

  onMounted(load)
  if (filters) watch(filters, load, { deep: true })
  watch(() => search.query, () => { clearTimeout(t); t = setTimeout(load, 280) })

  return { items, loading, error, reload: load }
}
