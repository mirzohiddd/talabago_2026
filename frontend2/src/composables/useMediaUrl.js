import { computed, toValue } from 'vue'
import { mediaUrl } from '@/services/http'

export const resolveMedia = (v) => mediaUrl(v)
export const useMediaUrl = (source) => computed(() => mediaUrl(toValue(source)))
export const useMediaList = (source) => computed(() => (toValue(source) || []).map(mediaUrl))
