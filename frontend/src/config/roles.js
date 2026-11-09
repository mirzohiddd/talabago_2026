import { computed } from 'vue'
import { Briefcase, Building2, PlusCircle, Inbox, Users, GraduationCap, KeyRound, Settings, FileText, BookOpen } from 'lucide-vue-next'
import { t } from '@/i18n'

export * from '@shared/domain.js'

/**
 * Har bir rolning asosiy sahifalari (topshiriq bo‘yicha aniq ro‘yxat; alohida Dashboard yo‘q).
 * Mobil: pastki navigatsiya. Desktop: chap sidebar. Support — Sozlamalar va navbar’dagi yordam ikonkasidan.
 * `label` i18n kaliti sifatida ishlatiladi.
 */
export const ROLES = {
  student: {
    key: 'student', title: 'Talaba', cta: 'Men talabaman', icon: GraduationCap, illu: 'student',
    desc: 'Ish, turar joy va bepul til kurslari',
    home: '/student/jobs',
    nav: [
      { to: '/student/jobs', label: 'Ishlar', icon: Briefcase },
      { to: '/student/housing', label: 'Turar joy', icon: Building2 },
      { to: '/student/applications', label: 'Arizalarim', icon: FileText },
      { to: '/student/courses', label: 'Kurslar', icon: BookOpen },
      { to: '/student/settings', label: 'Sozlamalar', icon: Settings },
    ],
  },
  employer: {
    key: 'employer', title: 'Ish beruvchi', cta: 'Men ish beruvchiman', icon: Briefcase, illu: 'briefcase',
    desc: 'Vakansiya joylashtirish va nomzod topish',
    home: '/employer/jobs',
    nav: [
      { to: '/employer/jobs', label: 'Ishlar', icon: Briefcase },
      { to: '/employer/new', label: 'E’lon qo‘shish', icon: PlusCircle },
      { to: '/employer/applications', label: 'Arizalar', icon: Users },
      { to: '/employer/settings', label: 'Sozlamalar', icon: Settings },
    ],
  },
  landlord: {
    key: 'landlord', title: 'Uy egasi', cta: 'Men uy egasiman', icon: KeyRound, illu: 'keys',
    desc: 'Uy yoki xonani talabalarga ijaraga berish',
    home: '/landlord/houses',
    nav: [
      { to: '/landlord/houses', label: 'Uylar', icon: Building2 },
      { to: '/landlord/new', label: 'E’lon qo‘shish', icon: PlusCircle },
      { to: '/landlord/requests', label: 'So‘rovlar', icon: Inbox },
      { to: '/landlord/settings', label: 'Sozlamalar', icon: Settings },
    ],
  },
}

/** Domen ro‘yxatini joriy tilga o‘girilgan {value,label} ga aylantiradi (til almashsa qayta hisoblanadi) */
export const useOptions = (list, { all } = {}) => computed(() => [
  ...(all ? [{ value: 'all', label: t(all) }] : []),
  ...list.map((o) => (typeof o === 'string' ? { value: o, label: t(o) } : { ...o, label: t(o.label) })),
])
