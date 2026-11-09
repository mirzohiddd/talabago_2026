/**
 * TalabaGo API (FastAPI) uchun HTTP klient.
 * Token: Authorization: Bearer <JWT> (ro‘yxatdan o‘tish / kirishda server beradi).
 * Telegram ichida X-Telegram-Init-Data ham yuboriladi (server initData’ni HMAC bilan tekshiradi).
 */
import { getInitData } from './telegram'
import { session } from '@/stores/session'

// Nisbiy (/api/v1 — shu host orqali Vite/nginx proxy) yoki to‘liq URL (https://api.domen.uz/api/v1)
const RAW_API = (import.meta.env.VITE_API_URL || '/api/v1').replace(/\/$/, '')
export const API_URL = new URL(RAW_API, window.location.origin).href.replace(/\/$/, '')
export const API_ORIGIN = new URL(API_URL).origin

export class ApiError extends Error {
  constructor(status, message, data) {
    super(message)
    this.status = status
    this.data = data
  }
}

/** 401 bo‘lsa sessiya tozalanadi va onboarding/kirish sahifasiga qaytariladi (main.js da o‘rnatiladi) */
let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

function headers(extra = {}) {
  const h = { ...extra }
  if (session.token) h.Authorization = `Bearer ${session.token}`
  const init = getInitData()
  if (init) h['X-Telegram-Init-Data'] = init
  return h
}

async function handle(res, path) {
  const data = res.status === 204 ? null : await res.json().catch(() => null)
  if (!res.ok) {
    if (res.status === 401 && session.token && !path.startsWith('/auth/')) onUnauthorized()
    throw new ApiError(res.status, data?.detail || (res.status >= 500 ? 'Server xatosi. Birozdan so‘ng qayta urinib ko‘ring.' : 'So‘rov bajarilmadi'), data)
  }
  return data
}

/** So‘rov osilib qolsa (sekin tunnel / mobil tarmoq) — cheksiz yuklanish o‘rniga tushunarli xato */
async function timedFetch(url, opts, ms) {
  const ctrl = typeof AbortController !== 'undefined' ? new AbortController() : null
  const timer = ctrl && setTimeout(() => ctrl.abort(), ms)
  try {
    return await fetch(url, ctrl ? { ...opts, signal: ctrl.signal } : opts)
  } catch (e) {
    if (e?.name === 'AbortError') throw new ApiError(0, 'Server javob bermadi. Internet aloqasini tekshirib, qayta urinib ko‘ring.')
    throw new ApiError(0, 'Serverga ulanib bo‘lmadi. Internet aloqasini tekshiring.')
  } finally {
    if (timer) clearTimeout(timer)
  }
}

export async function http(path, { method = 'GET', body, params, timeout = 25000 } = {}) {
  const url = new URL(API_URL + path)
  if (params) {
    Object.entries(params).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '' && v !== 'all' && v !== false) url.searchParams.set(k, v)
    })
  }
  const res = await timedFetch(url, { method, headers: headers(body ? { 'Content-Type': 'application/json' } : {}), body: body ? JSON.stringify(body) : undefined }, timeout)
  return handle(res, path)
}

/** Fayl yuklash (multipart) */
export async function httpForm(path, formData, { method = 'POST' } = {}) {
  const res = await timedFetch(API_URL + path, { method, headers: headers(), body: formData }, 180000)
  return handle(res, path)
}

/** Statistika uchun “yuborib unut” so‘rovi */
export function ping(path) {
  fetch(API_URL + path, { method: 'POST', keepalive: true, headers: headers() }).catch(() => {})
}

/** Serverdagi /media/... manzilini to‘liq URL’ga aylantirish */
export function mediaUrl(v) {
  if (!v || typeof v !== 'string') return v || null
  return v.startsWith('/media/') ? API_ORIGIN + v : v
}
