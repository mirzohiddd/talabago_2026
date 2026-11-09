import { createRouter, createWebHashHistory } from 'vue-router'
import { session } from '@/stores/session'
import { ROLES } from '@/config/roles'
import RoleLayout from '@/components/layout/RoleLayout.vue'

const v = {
  jobs: () => import('@/views/shared/JobsBrowseView.vue'),
  houses: () => import('@/views/shared/HousesBrowseView.vue'),
  settings: () => import('@/views/shared/SettingsView.vue'),
  support: () => import('@/views/shared/SupportView.vue'),
}
// meta.title va meta.search — i18n kalitlari; meta.ads — sahifada reklama carousel bor
const supportRoutes = [
  { path: 'support', component: v.support, meta: { title: 'Texnik yordam', viewKey: 'support', illu: 'support' } },
  { path: 'support/:id', component: v.support, meta: { title: 'Texnik yordam', viewKey: 'support', illu: 'support' } },
]
const roleChildren = {
  student: [
    { path: 'jobs', component: v.jobs, meta: { title: 'Ishlar', subtitle: 'O‘qishingizga mos soatlik, kunlik va doimiy ishlar', illu: 'search-job', search: 'Ish, kompaniya yoki tuman...', ads: true } },
    { path: 'housing', component: v.houses, meta: { title: 'Turar joy', subtitle: 'Talabalar uchun qulay uy va xonalar', illu: 'search-house', search: 'Tuman, manzil yoki uy nomi...', ads: true } },
    { path: 'applications', component: () => import('@/views/student/ApplicationsView.vue'), meta: { title: 'Arizalarim', subtitle: 'Ish arizalari va ijara so‘rovlaringiz holati', illu: 'checklist', search: 'Arizalarni qidirish...' } },
    { path: 'courses', component: () => import('@/views/student/CoursesView.vue'), meta: { title: 'Kurslar', subtitle: 'Bepul online til kurslari: video, lug‘at, tarjima va test', illu: 'books' } },
    { path: 'courses/:courseId', component: () => import('@/views/student/CourseView.vue'), meta: { title: 'Kurslar' } },
    { path: 'courses/:courseId/:lessonId', component: () => import('@/views/student/LessonView.vue'), meta: { title: 'Kurslar' } },
    { path: 'settings', component: v.settings, meta: { title: 'Sozlamalar', subtitle: 'Profil, til, bildirishnomalar va yordam', illu: 'desk-lamp' } },
  ],
  employer: [
    { path: 'jobs', component: v.jobs, meta: { title: 'Ishlar', subtitle: 'Platformadagi barcha vakansiyalar', illu: 'briefcase', search: 'Ish, kompaniya yoki tuman...', ads: true } },
    { path: 'new', component: () => import('@/views/shared/PostListingView.vue'), meta: { title: 'E’lon qo‘shish', subtitle: 'Vakansiyalaringizni joylang va boshqaring', illu: 'laptop', search: 'E’lonlarimni qidirish...' } },
    { path: 'applications', component: () => import('@/views/shared/IncomingView.vue'), meta: { title: 'Arizalar', subtitle: 'Talabalardan kelgan arizalar', illu: 'office-worker', search: 'Nomzod, OTM yoki vakansiya...' } },
    { path: 'settings', component: v.settings, meta: { title: 'Sozlamalar', subtitle: 'Profil, til, bildirishnomalar va yordam', illu: 'desk-lamp' } },
  ],
  landlord: [
    { path: 'houses', component: v.houses, meta: { title: 'Uylar', subtitle: 'Platformadagi barcha uy e’lonlari', illu: 'building', search: 'Tuman, manzil yoki uy nomi...', ads: true } },
    { path: 'new', component: () => import('@/views/shared/PostListingView.vue'), meta: { title: 'E’lon qo‘shish', subtitle: 'Uy yoki xonangizni e’lon qiling', illu: 'keys', search: 'E’lonlarimni qidirish...' } },
    { path: 'requests', component: () => import('@/views/shared/IncomingView.vue'), meta: { title: 'So‘rovlar', subtitle: 'Talabalardan kelgan ijara so‘rovlari', illu: 'house', search: 'Talaba yoki uy...' } },
    { path: 'settings', component: v.settings, meta: { title: 'Sozlamalar', subtitle: 'Profil, til, bildirishnomalar va yordam', illu: 'desk-lamp' } },
  ],
}

const roleRoutes = Object.entries(roleChildren).map(([role, children]) => ({
  path: `/${role}`,
  component: RoleLayout,
  meta: { role, home: ROLES[role].home },
  redirect: ROLES[role].home,
  children: [...children, ...supportRoutes].map((c) => ({ ...c, meta: { ...c.meta, role, home: ROLES[role].home, requiresRole: role } })),
}))

const routes = [
  { path: '/', component: () => import('@/views/auth/SplashView.vue') },
  { path: '/welcome', component: () => import('@/views/auth/OnboardingView.vue') },
  { path: '/login', component: () => import('@/views/auth/LoginView.vue') },
  // eski havolalar
  { path: '/register', redirect: '/welcome' },
  { path: '/role', redirect: '/welcome' },
  ...roleRoutes,
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  // Telegram Mini App’da hash rejimi eng ishonchli (server sozlamasiz, chuqur havolalar ham ochiladi)
  history: createWebHashHistory(),
  routes,
  scrollBehavior: (to, from, saved) => saved || { top: 0 },
})

router.beforeEach((to) => {
  if (to.meta.requiresRole) {
    if (!session.token || !session.role) return '/welcome'
    if (session.role !== to.meta.requiresRole) return ROLES[session.role].home
  }
  // Ro‘yxatdan o‘tgan foydalanuvchiga onboarding va kirish sahifasi qayta ko‘rsatilmaydi
  if ((to.path === '/welcome' || to.path === '/login') && session.token && session.role) return ROLES[session.role].home
})

export default router
