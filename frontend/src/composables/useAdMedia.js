import { computed, toValue } from 'vue'

/** Mini App’da media doim URL (statik, server yoki data: URL) */
export function useAdMedia(mediaSource) {
  const src = computed(() => toValue(mediaSource)?.src || null)
  const poster = computed(() => toValue(mediaSource)?.posterSrc || null)
  const missing = computed(() => !!toValue(mediaSource) && !src.value)
  return { src, poster, missing }
}
