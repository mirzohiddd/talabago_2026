/**
 * TalabaGo Support paneli HTTP klienti (FastAPI, /api/v1).
 * Sessiya HttpOnly cookie’da (JS o‘qiy olmaydi). O‘zgartiruvchi so‘rovlarda X-Requested-With — server CSRF tekshiruvi uchun.
 */
// Nisbiy (/api/v1 — shu host orqali Vite/nginx proxy) yoki to‘liq URL (https://api.domen.uz/api/v1)
const RAW_API = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
export const API_URL = new URL(RAW_API, window.location.origin).href.replace(/\/$/, '')
export const API_ORIGIN = new URL(API_URL).origin
const BASE_HEADERS = { 'X-Requested-With': 'TalabaGo' }

export class ApiError extends Error {
  constructor(status, message, data) { super(message); this.status = status; this.data = data }
}

/** 401 bo‘lsa router login sahifasiga qaytaradi (main.js da o‘rnatiladi) */
let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

/** Server sessiyani uzaytirganda (sliding) yangi tugash vaqti — X-Session-Expires sarlavhasida */
let onSessionExpires = () => {}
export const setSessionExpiresHandler = (fn) => { onSessionExpires = fn }
export function readSessionHeader(res) {
  const v = res?.headers?.get?.('x-session-expires')
  const ts = v ? Date.parse(v) : NaN
  if (Number.isFinite(ts)) onSessionExpires(ts)
}

async function handle(res, path) {
  readSessionHeader(res)
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (res.status === 401 && !path.startsWith('/auth/')) onUnauthorized()
  if (!res.ok) throw new ApiError(res.status, data?.detail || (res.status >= 500 ? 'Server xatosi' : 'So‘rov bajarilmadi'), data)
  return data
}

async function send(path, init) {
  try {
    return handle(await fetch(API_URL + path, { credentials: 'include', ...init, headers: { ...BASE_HEADERS, ...(init.headers || {}) } }), path)
  } catch (e) {
    if (e instanceof ApiError) throw e
    throw new ApiError(0, 'Serverga ulanib bo‘lmadi')
  }
}

export function http(path, { method = 'GET', body, params } = {}) {
  let p = path
  if (params) {
    const q = new URLSearchParams()
    Object.entries(params).forEach(([k, v]) => v != null && v !== '' && v !== 'all' && q.set(k, v))
    if ([...q].length) p += `?${q}`
  }
  return send(p, { method, headers: body ? { 'Content-Type': 'application/json' } : {}, body: body ? JSON.stringify(body) : undefined })
}

export function httpForm(path, formData, { method = 'POST' } = {}) {
  return send(path, { method, body: formData })
}

/** Fayl yuklash (dars videosi, logo, skrinshot, ...): POST /crm/files → { url, name, size, mime } */
export function uploadFile(file, kind = 'file') {
  const fd = new FormData()
  fd.append('file', file, file.name || 'file')
  fd.append('kind', kind)
  return httpForm('/crm/files', fd)
}

export function ping(path) {
  fetch(API_URL + path, { method: 'POST', keepalive: true }).catch(() => {})
}

/** Serverdagi /media/... manzilini to‘liq URL’ga aylantirish */
export function mediaUrl(v) {
  if (!v || typeof v !== 'string') return v || null
  return v.startsWith('/media/') ? API_ORIGIN + v : v
}