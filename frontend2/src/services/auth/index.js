/**
 * TalabaGo Support autentifikatsiyasi — faqat server tomonda (FastAPI):
 *   POST /auth/admin/login  → HttpOnly cookie (JS o‘qiy olmaydi) + { user, expiresAt }
 *   GET  /auth/admin/me     · POST /auth/admin/logout · POST /auth/admin/password
 * Har bir /crm/* va /ads endpointi serverda administrator sessiyasini tekshiradi; frontend’dagi tekshiruv faqat UI uchun.
 */
import { reactive, computed } from 'vue'
import { API_URL } from '../http'

export class AuthError extends Error {
  constructor(code, message, extra = {}) { super(message); this.code = code; Object.assign(this, extra) }
}

async function req(path, opts = {}) {
  let res
  try {
    res = await fetch(API_URL + path, { credentials: 'include', ...opts, headers: { 'Content-Type': 'application/json', 'X-Requested-With': 'TalabaGo' } })
  } catch {
    throw new AuthError('network', 'Serverga ulanib bo‘lmadi')
  }
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  return { res, data }
}
const session = (data) => (data?.user?.role === 'admin' ? { user: data.user, expiresAt: Date.parse(data.expiresAt) || Date.now() + 3600_000 } : null)

export const provider = {
  async login(username, password) {
    const { res, data } = await req('/auth/admin/login', { method: 'POST', body: JSON.stringify({ username, password }) })
    if (res.status === 429) throw new AuthError('locked', data?.detail || 'Juda ko‘p urinish', { until: Date.now() + (+res.headers.get('retry-after') || 300) * 1000 })
    if (!res.ok) throw new AuthError('invalid', data?.detail || 'Username yoki parol noto‘g‘ri')
    const s = session(data)
    if (!s) throw new AuthError('forbidden', 'Bu hisobda administrator huquqi yo‘q')
    return s
  },
  async me() {
    const { res, data } = await req('/auth/admin/me').catch(() => ({ res: { ok: false } }))
    return res.ok ? session(data) : null
  },
  async logout() { await req('/auth/admin/logout', { method: 'POST' }).catch(() => {}) },
  async changePassword(current, next) {
    const { res, data } = await req('/auth/admin/password', { method: 'POST', body: JSON.stringify({ current, next }) })
    if (!res.ok) throw new AuthError(res.status === 400 ? 'invalid' : 'error', data?.detail || 'Parolni o‘zgartirib bo‘lmadi')
  },
}

export const auth = reactive({ user: null, expiresAt: 0, ready: false })
export const isAuthenticated = computed(() => auth.user?.role === 'admin' && auth.expiresAt > Date.now())

function apply(s) {
  auth.user = s?.user ?? null
  auth.expiresAt = s?.expiresAt ?? 0
}

let restoring = null
export function restoreSession() {
  if (auth.ready) return Promise.resolve()
  return (restoring ??= provider.me().then((s) => { apply(s); auth.ready = true }))
}
export async function login(username, password) {
  const s = await provider.login(username, password)
  apply(s)
  auth.ready = true
  return s
}
export async function logout() {
  await provider.logout()
  apply(null)
}
export function dropSession() { apply(null) }
