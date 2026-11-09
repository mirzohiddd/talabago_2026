import { computed, toValue } from 'vue'
import { mediaUrl } from '@/services/http'

/**
 * Reklama media manbasi: media.previewUrl (formadagi hali saqlanmagan fayl) yoki server URL (media.src / posterSrc).
 */
export function useAdMedia(mediaSource) {
  const src = computed(() => { const m = toValue(mediaSource); return m ? (m.previewUrl || mediaUrl(m.src)) : null })
  const poster = computed(() => { const m = toValue(mediaSource); return m ? (m.posterPreviewUrl || mediaUrl(m.posterSrc)) : null })
  const missing = computed(() => !!toValue(mediaSource) && !src.value)
  return { src, poster, missing }
}
