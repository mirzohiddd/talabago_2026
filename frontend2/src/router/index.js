import { createRouter, createWebHistory } from 'vue-router'
import { restoreSession, isAuthenticated } from '@/services/auth'
import CrmLayout from '@/views/crm/CrmLayout.vue'
import { t } from '@/i18n'

const page = (path, title, loader, extra = {}) => ({ path, component: loader, meta: { title, ...extra } })

const routes = [
  { path: '/login', component: () => import('@/views/auth/LoginView.vue'), meta: { public: true, title: 'Kirish' } },
  {
    path: '/',
    component: CrmLayout,
    redirect: '/dashboard',
    children: [
      page('dashboard', 'Dashboard', () => import('@/views/crm/DashboardView.vue')),
      page('users', 'Foydalanuvchilar', () => import('@/views/crm/UsersView.vue')),
      page('jobs', 'Ish e’lonlari', () => import('@/views/crm/JobsView.vue')),
      page('housing', 'Turar joylar', () => import('@/views/crm/HousingView.vue')),
      page('ads', 'Reklama boshqaruvi', () => import('@/views/crm/AdsView.vue')),
      page('ads/new', 'Yangi reklama', () => import('@/views/crm/AdEditView.vue'), { section: '/ads' }),
      page('ads/:id/edit', 'Reklamani tahrirlash', () => import('@/views/crm/AdEditView.vue'), { section: '/ads' }),
      page('courses', 'Kurslar boshqaruvi', () => import('@/views/crm/CoursesView.vue')),
      page('courses/:id', 'Kurslar boshqaruvi', () => import('@/views/crm/CoursesView.vue'), { section: '/courses', viewKey: 'courses' }),
      page('applications', 'Arizalar va so‘rovlar', () => import('@/views/crm/ApplicationsView.vue')),
      page('support', 'Support', () => import('@/views/crm/SupportView.vue'), { viewKey: 'support' }),
      page('support/:id', 'Support', () => import('@/views/crm/SupportView.vue'), { section: '/support', viewKey: 'support' }),
      page('complaints', 'Shikoyatlar', () => import('@/views/crm/ComplaintsView.vue')),
      page('settings', 'Sozlamalar', () => import('@/views/crm/SettingsView.vue')),
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 }),
})

// Kirish nazorati (UI darajasida). Haqiqiy himoya — backend: har bir /crm/* so‘rov administrator sessiyasini tekshiradi.
router.beforeEach(async (to) => {
  await restoreSession()
  if (!to.meta.public && !isAuthenticated.value) {
    return { path: '/login', query: to.fullPath !== '/dashboard' && to.fullPath !== '/' ? { redirect: to.fullPath } : {} }
  }
  if (to.path === '/login' && isAuthenticated.value) return '/dashboard'
})
router.afterEach((to) => { document.title = `${t(to.meta.title || 'CRM')} · TalabaGo Support` })

export default router
