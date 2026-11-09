import { reactive } from 'vue'

export const toasts = reactive([])
export function toast(text, type = 'success') {
  const id = Math.random()
  toasts.push({ id, text, type })
  setTimeout(() => {
    const i = toasts.findIndex((t) => t.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, 2800)
}
