import { reactive, computed, watch } from 'vue'

/**
 * Sessiya: qaysi foydalanuvchi va rol, onboarding holati, sozlamalar.
 * Profil ma’lumotlari users jadvalida (servis orqali), bu yerda faqat havola.
 * Backend: token (Telegram initData server tomonida tekshirilgandan keyin beriladi).
 */
const KEY = 'talabago_session_v2'

function load() {
  try { return JSON.parse(localStorage.getItem(KEY)) || {} } catch { return {} }
}
const saved = load()

export const session = reactive({
  userId: saved.userId || null,
  role: saved.role || null, // 'student' | 'employer' | 'landlord'
  token: saved.token || null,
  onboarding: saved.onboarding || { step: 1, role: null }, // onboarding qayerda to‘xtagani
  settings: saved.settings || { notifications: true, telegramAlerts: true, emailDigest: false },
  sidebarCollapsed: saved.sidebarCollapsed || false,
  user: null, // joriy foydalanuvchi profili (servisdan yuklanadi, saqlanmaydi)
})

watch(session, (s) => {
  const { user, ...rest } = s
  try { localStorage.setItem(KEY, JSON.stringify(rest)) } catch {}
}, { deep: true })

export const isRegistered = computed(() => Boolean(session.userId && session.role))

export function signIn({ userId, role, token }) {
  Object.assign(session, { userId, role, token, onboarding: { step: 1, role: null } })
}
export function logout() {
  Object.assign(session, { userId: null, role: null, token: null, user: null, onboarding: { step: 1, role: null } })
}

/* -------- Navbar qidiruvi: joriy sahifa shu qiymat bo‘yicha filtrlaydi -------- */
export const search = reactive({ query: '', open: false })

/* -------- Toast xabarlari -------- */
export const toasts = reactive([])
export function toast(text, type = 'success') {
  const id = Math.random()
  toasts.push({ id, text, type })
  setTimeout(() => {
    const i = toasts.findIndex((x) => x.id === id)
    if (i >= 0) toasts.splice(i, 1)
  }, 2800)
}
