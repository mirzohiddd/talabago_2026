/**
 * Servis qatlami — komponentlar faqat shu funksiyalarni chaqiradi. Barcha ma’lumot TalabaGo API’dan (FastAPI, /api/v1).
 */
import { http, httpForm, API_URL } from './http'
import { getInitData } from './telegram'

export const fullName = (u) => (u ? [u.firstName, u.lastName].filter(Boolean).join(' ') : '')

const KIND = { ph: 'photo', photo: 'photo', shot: 'shot', cv: 'cv', logo: 'logo' }
/** Fayl yuklash: POST /files → { url: '/media/...', name, size } */
export async function uploadFile(file, prefix = 'file') {
  const fd = new FormData()
  fd.append('file', file, file.name || 'file')
  fd.append('kind', KIND[prefix] || 'file')
  return (await httpForm('/files', fd)).url
}

/* ============================== AUTH / PROFIL ============================== */
export const authApi = {
  /** POST /auth/register — Telegram ichida initData (serverda tekshiriladi), brauzerda parol bilan */
  register(role, payload) {
    const initData = getInitData()
    return http('/auth/register', { method: 'POST', body: { role, ...payload, ...(initData ? { initData } : {}) } })
  },
  login(phone, password) { return http('/auth/login', { method: 'POST', body: { phone, password } }) },
  /** Telegram Mini App: imzolangan initData bilan avtomatik kirish (hisob bo‘lmasa 404) */
  telegramLogin() { return http('/auth/telegram', { method: 'POST', body: { initData: getInitData() } }) },
  linkTelegram() { return http('/auth/telegram/link', { method: 'POST', body: { initData: getInitData() } }) },
  me() { return http('/users/me') },
  updateProfile(patch) { return http('/users/me', { method: 'PATCH', body: patch }) },
  changePassword(current, next) { return http('/users/me/password', { method: 'POST', body: { current, next } }) },
  publicConfig() { return http('/public/config') },
}

/* ============================== ISHLAR ============================== */
export const jobsApi = {
  list(f = {}) { return http('/jobs', { params: f }) },
  get(id) { return http(`/jobs/${id}`) },
  view(id) { return http(`/jobs/${id}/view`, { method: 'POST' }).catch(() => {}) },
  mine({ status, q } = {}) { return http('/employer/jobs', { params: { status, q } }) },
  create(payload) { return http('/employer/jobs', { method: 'POST', body: payload }) },
  update(id, payload) { return http(`/employer/jobs/${id}`, { method: 'PATCH', body: payload }) },
  duplicate(id) { return http(`/employer/jobs/${id}/duplicate`, { method: 'POST' }) },
  setActive(id, active) { return http(`/employer/jobs/${id}/active`, { method: 'PATCH', body: { active } }) },
  remove(id) { return http(`/employer/jobs/${id}`, { method: 'DELETE' }) },
  apply(jobId, { message }) { return http(`/jobs/${jobId}/apply`, { method: 'POST', body: { message } }) },
  toggleSave(id) { return http(`/jobs/${id}/save`, { method: 'POST' }) },
  async savedCount() { return (await http('/jobs', { params: { saved: true } })).length },
}

/* ============================== TURAR JOY ============================== */
export const housingApi = {
  list(f = {}) { return http('/houses', { params: f }) },
  get(id) { return http(`/houses/${id}`) },
  view(id) { return http(`/houses/${id}/view`, { method: 'POST' }).catch(() => {}) },
  mine({ status, q } = {}) { return http('/landlord/houses', { params: { status, q } }) },
  create(payload) { return http('/landlord/houses', { method: 'POST', body: payload }) },
  update(id, payload) { return http(`/landlord/houses/${id}`, { method: 'PATCH', body: payload }) },
  duplicate(id) { return http(`/landlord/houses/${id}/duplicate`, { method: 'POST' }) },
  setActive(id, active) { return http(`/landlord/houses/${id}/active`, { method: 'PATCH', body: { active } }) },
  setOccupancy(id, occupancy) { return http(`/landlord/houses/${id}/occupancy`, { method: 'PATCH', body: { occupancy } }) },
  remove(id) { return http(`/landlord/houses/${id}`, { method: 'DELETE' }) },
  request(houseId, { message, moveIn, term }) { return http(`/houses/${houseId}/requests`, { method: 'POST', body: { message, moveIn, term } }) },
  toggleSave(id) { return http(`/houses/${id}/save`, { method: 'POST' }) },
  async savedCount() { return (await http('/houses', { params: { saved: true } })).length },
}

/* ============================== ARIZALAR / SO‘ROVLAR ============================== */
export const applicationsApi = {
  myJobs() { return http('/me/applications') },
  myRequests() { return http('/me/rental-requests') },
  withdraw(kind, id) { return http(`/me/${kind === 'job' ? 'applications' : 'rental-requests'}/${id}/withdraw`, { method: 'POST' }) },
  forEmployer({ status, jobId, q } = {}) { return http('/employer/applications', { params: { status, job_id: jobId, q } }) },
  setEmployerStatus(id, status, extra = {}) { return http(`/employer/applications/${id}`, { method: 'PATCH', body: { status, ...extra } }) },
  forLandlord({ status, houseId, q } = {}) { return http('/landlord/requests', { params: { status, house_id: houseId, q } }) },
  setLandlordStatus(id, status, extra = {}) { return http(`/landlord/requests/${id}`, { method: 'PATCH', body: { status, ...extra } }) },
  /** Talaba: qabul qilingan ishni “yakunlandi” deb belgilash (keyin o‘zaro baholash ochiladi) */
  complete(id) { return http(`/me/applications/${id}/complete`, { method: 'POST' }) },
}

/* ============================== CHAT (talaba ↔ ish beruvchi) ============================== */
export const chatApi = {
  list() { return http('/chats') },
  unread() { return http('/chats/unread').then((r) => r.count).catch(() => 0) },
  get(id) { return http(`/chats/${id}`) },
  forApplication(appId) { return http(`/applications/${appId}/chat`, { method: 'POST' }) },
  messages(id, after) { return http(`/chats/${id}/messages`, { params: { after } }) },
  send(id, text) { return http(`/chats/${id}/messages`, { method: 'POST', body: { text } }) },
  read(id) { return http(`/chats/${id}/read`, { method: 'POST' }).catch(() => {}) },
}

/* ============================== BAHOLASH ============================== */
export const reviewsApi = {
  forApplication(appId) { return http(`/applications/${appId}/reviews`) },
  create(appId, { stars, comment }) { return http(`/applications/${appId}/review`, { method: 'POST', body: { stars, comment } }) },
  ofUser(userId) { return http(`/users/${userId}/reviews`) },
}

/* ============================== ISH BERUVCHI MONITORINGI ============================== */
export const insightsApi = {
  get(days = 30) { return http('/employer/insights', { params: { days } }) },
}

/* ============================== KURSLAR ============================== */
export const coursesApi = {
  list() { return http('/courses') },
  async get(id) { return (await this.list()).find((c) => c.id === id) || null },
  progress(courseId) { return http(`/courses/${courseId}/progress`) },
  /** Javoblar serverga yuboriladi — ball server tomonda hisoblanadi */
  completeLesson(courseId, lessonId, answers) { return http(`/courses/${courseId}/lessons/${lessonId}/complete`, { method: 'POST', body: { answers } }) },
  /** Yakuniy test: savollar (to‘g‘ri javoblarsiz), urinishlar, sertifikat */
  exam(courseId) { return http(`/courses/${courseId}/exam`) },
  submitExam(courseId, answers) { return http(`/courses/${courseId}/exam/submit`, { method: 'POST', body: { answers } }) },
  certificates() { return http('/me/certificates') },
  /** Ommaviy PDF va tekshirish sahifasi (QR shu sahifaga olib boradi) */
  certificatePdfUrl(code) { return `${API_URL}/certificates/${encodeURIComponent(code)}/pdf` },
  certificatePageUrl(code) { return `${API_URL}/certificates/${encodeURIComponent(code)}/page` },
}

/* ============================== SUPPORT ============================== */
export const supportApi = {
  list() { return http('/support/tickets') },
  get(id) { return http(`/support/tickets/${id}`) },
  create({ type, subject, text, attachment }) { return http('/support/tickets', { method: 'POST', body: { type, subject, text, attachment } }) },
  send(id, { text, attachment }) { return http(`/support/tickets/${id}/messages`, { method: 'POST', body: { text, attachment } }) },
  markRead(id) { return http(`/support/tickets/${id}/read`, { method: 'POST' }) },
}

/* ============================== SHIKOYAT / FOYDALANUVCHI / BILDIRISHNOMA ============================== */
export const complaintsApi = {
  create({ target, category, message }) { return http('/complaints', { method: 'POST', body: { target, category, message } }) },
}
export const usersApi = {
  student(id) { return http(`/users/${id}/public`) },
}
export const notificationsApi = {
  list() { return http('/notifications') },
  readAll() { return http('/notifications/read-all', { method: 'POST' }) },
}