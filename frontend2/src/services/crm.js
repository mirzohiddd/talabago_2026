/**
 * TalabaGo Support ma’lumotlari: reaktiv ombor + TalabaGo API (/api/v1/crm/*). Barcha ma’lumot backend JSON fayllaridan.
 * Har bir amal serverda bajariladi, so‘ng server qaytargan yozuv omborga qo‘yiladi (statistika va grafiklar shu ombordan hisoblanadi).
 */
import { reactive } from 'vue'
import { http } from './http'

export const fullName = (u) => (u ? [u.firstName, u.lastName].filter(Boolean).join(' ') : '')

const SOURCES = {
  users: '/crm/users', jobs: '/crm/jobs', houses: '/crm/houses', applications: '/crm/applications', requests: '/crm/rental-requests',
  courses: '/crm/courses', progress: '/crm/progress', tickets: '/crm/support/tickets', complaints: '/crm/complaints',
}
const defaultSettings = () => ({
  profile: { name: '', email: '', avatar: null },
  platform: { name: 'TalabaGo', logo: null },
  notifications: { newTicket: true, newListing: true, newComplaint: true, dailyDigest: false },
  system: { maintenance: false, registrationOpen: true, moderation: true, adsEnabled: true },
})

export const crmStore = reactive({
  ...Object.fromEntries(Object.keys(SOURCES).map((k) => [k, []])),
  settings: defaultSettings(),
  /** Jami foydalanuvchilar hisobi: GET /crm/stats/users (41 — eski, tiklanmagan baza + keyin ro‘yxatdan o‘tganlar) */
  userStats: null,
  loaded: false,
  error: null,
  /** Yuklanmagan bo‘limlar (masalan, Render uyg‘onayotganda 502) — qolganlari baribir ko‘rsatiladi */
  failed: [],
  refreshedAt: null,
})

/** Server sozlamalari eski/to‘liqsiz bo‘lsa ham sahifalar yiqilmasin: standart qiymatlar bilan birlashtirish */
const mergeSettings = (s) => Object.fromEntries(Object.entries(defaultSettings()).map(([k, v]) => [k, { ...v, ...(s && typeof s[k] === 'object' ? s[k] : {}) }]))

/** Oxirgi yuklangan ma’lumotlarning server o‘zgarish belgilari (live.js shular bilan solishtiradi) */
export const known = {}
const RETRY = '__retry__' // yuklanmagan bo‘lim: live.js keyingi tekshiruvda uni qayta yuklaydi
const getVersions = () => http('/crm/changes').then((r) => r.versions).catch(() => null)

/** Vaqtinchalik xatoda (tarmoq, 5xx — masalan, Render “uyg‘onayotganda”) 2 marta qayta urinadi */
const transient = (e) => !e?.status || e.status >= 500 || e.status === 429
async function fetchRetry(path, tries = 3) {
  for (let i = 0; ; i++) {
    try {
      return await http(path)
    } catch (e) {
      if (i >= tries - 1 || !transient(e)) throw e
      await new Promise((r) => setTimeout(r, 1200 * 2 ** i))
    }
  }
}

export const refreshUserStats = () => fetchRetry('/crm/stats/users').then((r) => (crmStore.userStats = r)).catch(() => null)

/**
 * Barcha kolleksiyalarni serverdan yuklash (yoki yangilash).
 * Har bo‘lim mustaqil: bittasi xato bersa ham qolganlari ko‘rsatiladi (oldin bitta xato barcha sahifalarni bo‘sh qoldirardi).
 * Hech qachon reject qilmaydi — sahifalardagi “yuklanmoqda” holati doim tugaydi.
 */
export async function refreshCrm() {
  // Belgilar ma’lumotdan OLDIN olinadi: yuklash paytida kelgan o‘zgarish keyingi tekshiruvda albatta ushlanadi
  const versions = await getVersions()
  const keys = Object.keys(SOURCES)
  const [settings, stats, ...lists] = await Promise.allSettled([fetchRetry('/crm/settings'), refreshUserStats(), ...keys.map((k) => fetchRetry(SOURCES[k]))])
  const failed = []
  if (settings.status === 'fulfilled') { crmStore.settings = mergeSettings(settings.value); if (versions) known.settings = versions.settings }
  else { failed.push('settings'); known.settings = RETRY }
  keys.forEach((k, i) => {
    const r = lists[i]
    if (r.status === 'fulfilled' && Array.isArray(r.value)) {
      crmStore[k] = r.value
      if (versions) known[k] = versions[k]
    } else {
      failed.push(k); known[k] = RETRY
    }
  })
  void stats
  crmStore.failed = failed
  crmStore.error = failed.length ? (lists.find((r) => r.status === 'rejected')?.reason?.message || settings.reason?.message || 'Server xatosi') : null
  crmStore.refreshedAt = Date.now()
  crmStore.loaded = true
}

/** Faqat o‘zgargan kolleksiyalarni qayta yuklash (avtomatik yangilanish) */
export async function refreshCollections(keys, versions) {
  const prev = Object.fromEntries(keys.map((k) => [k, known[k]]))
  keys.forEach((k) => (known[k] = versions[k]))
  try {
    const data = await Promise.all(keys.map((k) => http(k === 'settings' ? '/crm/settings' : SOURCES[k])))
    keys.forEach((k, i) => {
      if (k === 'settings') crmStore.settings = mergeSettings(data[i])
      else if (SOURCES[k] && Array.isArray(data[i])) crmStore[k] = data[i]
    })
    if (keys.includes('users')) refreshUserStats()
    crmStore.failed = crmStore.failed.filter((k) => !keys.includes(k))
    if (!crmStore.failed.length) crmStore.error = null
    crmStore.refreshedAt = Date.now()
  } catch (e) {
    Object.assign(known, prev) // keyingi tekshiruvda qayta urinadi
    throw e
  }
}

let loading = null
export function ensureCrmLoaded() {
  if (crmStore.loaded) return Promise.resolve()
  return (loading ??= refreshCrm().finally(() => (loading = null)))
}

const put = (list, item) => {
  const i = crmStore[list].findIndex((x) => x.id === item.id)
  if (i >= 0) crmStore[list][i] = item
  else crmStore[list].unshift(item)
  return item
}
const drop = (list, id) => { crmStore[list] = crmStore[list].filter((x) => x.id !== id) }

function moderation(list, path) {
  return {
    approve: async (id) => put(list, await http(`${path}/${id}/approve`, { method: 'POST' })),
    reject: async (id, reason) => put(list, await http(`${path}/${id}/reject`, { method: 'POST', body: { reason } })),
    setStatus: async (id, status) => put(list, await http(`${path}/${id}`, { method: 'PATCH', body: { status } })),
    update: async (id, body) => put(list, await http(`${path}/${id}`, { method: 'PATCH', body })),
    remove: async (id) => { await http(`${path}/${id}`, { method: 'DELETE' }); drop(list, id) },
    /** Admin e’loni (ish beruvchi / uy egasi akkauntisiz): manba + tekshiruv; publish=true — darhol nashr */
    create: async (body) => put(list, await http(path, { method: 'POST', body })),
  }
}

export const crmApi = {
  // ---- Foydalanuvchilar ----
  setUserStatus: async (id, status) => put('users', await http(`/crm/users/${id}`, { method: 'PATCH', body: { status } })),
  updateUser: async (id, body) => put('users', await http(`/crm/users/${id}`, { method: 'PATCH', body })),

  // ---- E’lonlar ----
  jobs: moderation('jobs', '/crm/jobs'),
  /** Admin e’loniga kelgan ariza / ijara so‘rovi holati (egasi bor e’lonlarda server 403 qaytaradi) */
  setApplicationStatus: async (id, status, note) => put('applications', await http(`/crm/applications/${id}`, { method: 'PATCH', body: { status, note } })),
  setRequestStatus: async (id, status, note) => put('requests', await http(`/crm/rental-requests/${id}`, { method: 'PATCH', body: { status, note } })),
  houses: moderation('houses', '/crm/houses'),
  setJobStatus: (id, status) => crmApi.jobs.setStatus(id, status),
  setHouseStatus: (id, status) => crmApi.houses.setStatus(id, status),

  // ---- Kurslar ----
  async saveCourse(course) {
    const body = JSON.parse(JSON.stringify(course))
    body.lessons.forEach((l, i) => (l.order = i + 1))
    return put('courses', await http(`/crm/courses/${course.id}`, { method: 'PUT', body }))
  },

  // ---- Support ----
  async replyTicket(id, text, { status = 'answered', attachment = null } = {}) {
    return put('tickets', await http(`/crm/support/tickets/${id}/messages`, { method: 'POST', body: { text, attachment, status } }))
  },
  async setTicketStatus(id, status) {
    return put('tickets', await http(`/crm/support/tickets/${id}`, { method: 'PATCH', body: { status } }))
  },
  async markTicketRead(id) {
    const t = crmStore.tickets.find((x) => x.id === id)
    if (!t?.unreadBySupport) return
    t.unreadBySupport = 0
    await http(`/crm/support/tickets/${id}/read`, { method: 'POST' }).catch(() => {})
  },
  async refreshTickets() {
    crmStore.tickets = await http('/crm/support/tickets')
  },

  // ---- Shikoyatlar ----
  async updateComplaint(id, { status, note, priority }) {
    return put('complaints', await http(`/crm/complaints/${id}`, { method: 'PATCH', body: { status, note, priority } }))
  },

  // ---- Sozlamalar ----
  async saveSettings(settings) {
    crmStore.settings = await http('/crm/settings', { method: 'PUT', body: settings })
    return crmStore.settings
  },
}