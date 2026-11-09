/**
 * Servis qatlami — komponentlar faqat shu funksiyalarni chaqiradi. Barcha ma’lumot TalabaGo API’dan (FastAPI, /api/v1).
 */
import { http, httpForm } from './http'
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
}

/* ============================== KURSLAR ============================== */
export const coursesApi = {
  list() { return http('/courses') },
  async get(id) { return (await this.list()).find((c) => c.id === id) || null },
  progress(courseId) { return http(`/courses/${courseId}/progress`) },
  /** Javoblar serverga yuboriladi — ball server tomonda hisoblanadi */
  completeLesson(courseId, lessonId, answers) { return http(`/courses/${courseId}/lessons/${lessonId}/complete`, { method: 'POST', body: { answers } }) },
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
