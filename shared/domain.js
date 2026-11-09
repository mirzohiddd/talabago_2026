/**
 * TalabaGo domen konstantalari — ikkala frontend va kelajakdagi FastAPI sxemalari uchun yagona manba.
 * `label` — o‘zbekcha matn va bir vaqtda i18n kaliti (UI’da t(label) bilan chiqariladi).
 * `value` — API’dagi enum qiymati (backendda Python Enum bilan bir xil bo‘lishi kerak).
 */

export const ROLE_KEYS = ['student', 'employer', 'landlord']
export const ROLE_LABELS = { student: 'Talaba', employer: 'Ish beruvchi', landlord: 'Uy egasi' }

/* ---------------- Ish ---------------- */
export const JOB_TYPES = [
  { value: 'hourly', label: 'Soatlik' },
  { value: 'daily', label: 'Kunlik' },
  { value: 'permanent', label: 'Doimiy' },
]
// Hybrid ataylab yo‘q
export const JOB_FORMATS = [
  { value: 'online', label: 'Online' },
  { value: 'offline', label: 'Offline' },
]
export const SALARY_PERIODS = [
  { value: 'hour', label: 'soatiga' },
  { value: 'day', label: 'kuniga' },
  { value: 'week', label: 'haftasiga' },
  { value: 'month', label: 'oyiga' },
]
export const DEFAULT_PERIOD = { hourly: 'hour', daily: 'day', permanent: 'month' }
export const WORK_TIMES = [
  { value: 'morning', label: 'Ertalab' },
  { value: 'day', label: 'Kunduzi' },
  { value: 'evening', label: 'Kechqurun' },
  { value: 'night', label: 'Tunda' },
  { value: 'weekend', label: 'Dam olish kunlari' },
  { value: 'flexible', label: 'Moslashuvchan' },
]
/** Maosh filtri: oyiga taxminiy daromad (soatlik ×160, kunlik ×22, haftalik ×4) */
export const SALARY_RANGES = [
  { value: 'all', label: 'Har qanday' },
  { value: '1', label: '1 mln+', min: 1_000_000 },
  { value: '3', label: '3 mln+', min: 3_000_000 },
  { value: '5', label: '5 mln+', min: 5_000_000 },
]
export const monthlyEstimate = (j) => j.salary * ({ hour: 160, day: 22, week: 4, month: 1 }[j.salaryPeriod] || 1)

export const JOB_CATEGORIES = ['IT', 'Marketing', 'Ta’lim', 'Savdo', 'Xizmat ko‘rsatish', 'Yetkazib berish', 'Mijozlar bilan ishlash', 'Boshqa']
export const INDUSTRIES = ['IT va texnologiya', 'Savdo', 'Umumiy ovqatlanish', 'Ta’lim', 'Marketing', 'Logistika', 'Moliya', 'Boshqa']

/* ---------------- Turar joy ---------------- */
export const HOUSE_TYPES = [
  { value: 'flat', label: 'Kvartira' },
  { value: 'room', label: 'Xona' },
  { value: 'dorm', label: 'Yotoqxona' },
  { value: 'house', label: 'Hovli uy' },
]
export const AUDIENCES = [
  { value: 'any', label: 'Farqi yo‘q' },
  { value: 'male', label: 'Yigitlar' },
  { value: 'female', label: 'Qizlar' },
]
export const ROOM_FILTERS = [
  { value: 'all', label: 'Har qanday' },
  { value: '1', label: '1 xona' },
  { value: '2', label: '2 xona' },
  { value: '3', label: '3+ xona' },
]
export const PRICE_RANGES = [
  { value: 'all', label: 'Har qanday' },
  { value: '1', label: '1 mln gacha', max: 1_000_000 },
  { value: '2', label: '2 mln gacha', max: 2_000_000 },
  { value: '3', label: '3 mln gacha', max: 3_000_000 },
  { value: '5', label: '5 mln gacha', max: 5_000_000 },
]
export const AMENITIES = ['Wi-Fi', 'Mebel', 'Konditsioner', 'Kir yuvish mashinasi', 'Oshxona', 'Lift', 'Qo‘riqlash', 'Isitish', 'Muzlatgich', 'Avtoturargoh']
export const OCCUPANCY = [
  { value: 'free', label: 'Bo‘sh' },
  { value: 'occupied', label: 'Band' },
]
export const RENT_TERMS = [
  { value: '1', label: '1 oy' },
  { value: '3', label: '3 oy' },
  { value: '6', label: '6 oy' },
  { value: '12', label: '1 yil' },
]
export const HOUSE_PHOTOS = { min: 3, max: 10 }

/* ---------------- Joylashuv ---------------- */
export const CITIES = {
  Toshkent: ['Bektemir', 'Chilonzor', 'Mirobod', 'Mirzo Ulug‘bek', 'Olmazor', 'Sergeli', 'Shayxontohur', 'Uchtepa', 'Yakkasaroy', 'Yangihayot', 'Yashnobod', 'Yunusobod'],
  Samarqand: ['Markaz', 'Bog‘ishamol', 'Sattepo'],
  Buxoro: ['Markaz', 'Fayzobod'],
  Andijon: ['Markaz', 'Bog‘ishamol'],
  Namangan: ['Markaz', 'Davlatobod'],
  'Farg‘ona': ['Markaz', 'Qirguli'],
  Nukus: ['Markaz'],
  Qarshi: ['Markaz'],
}
export const CITY_LIST = Object.keys(CITIES)
/** Taxminiy koordinatalar (xarita uchun; aniq manzil ko‘rsatilmaydi) */
export const CITY_CENTER = {
  Toshkent: [41.3111, 69.2797], Samarqand: [39.6542, 66.9597], Buxoro: [39.7747, 64.4286], Andijon: [40.7821, 72.3442],
  Namangan: [40.9983, 71.6726], 'Farg‘ona': [40.3864, 71.7864], Nukus: [42.4531, 59.6103], Qarshi: [38.8606, 65.7891],
}
export const DISTRICT_CENTER = {
  Bektemir: [41.209, 69.334], Chilonzor: [41.275, 69.204], Mirobod: [41.289, 69.281], 'Mirzo Ulug‘bek': [41.336, 69.335],
  Olmazor: [41.35, 69.225], Sergeli: [41.227, 69.218], Shayxontohur: [41.325, 69.232], Uchtepa: [41.296, 69.178],
  Yakkasaroy: [41.284, 69.256], Yangihayot: [41.205, 69.255], Yashnobod: [41.296, 69.335], Yunusobod: [41.366, 69.287],
}

/* ---------------- Talaba ---------------- */
export const UNIVERSITIES = ['TATU', 'O‘zMU', 'TDIU', 'INHA', 'Westminster', 'JMCU', 'UzSWLU', 'TDTU', 'SamDU', 'BuxDU', 'Boshqa']
export const SHIFTS = [
  { value: 'day', label: 'Kunduzgi' },
  { value: 'evening', label: 'Kechki' },
  { value: 'distance', label: 'Sirtqi' },
  { value: 'online', label: 'Masofaviy' },
]
export const SKILLS = ['Muloqot', 'Rus tili', 'Ingliz tili', 'Kompyuter savodxonligi', 'Excel', 'Canva', 'Figma', 'Copywriting', 'Sotuv', 'Haydovchilik', 'Vue.js', 'Python', 'SMM', 'Jamoada ishlash']

/* ---------------- Holatlar ---------------- */
// tone: brand | green | red | amber | blue | gray
export const STATUS = {
  // E’lon (ish / uy) moderatsiyasi
  pending: { label: 'Tekshiruvda', tone: 'amber' },
  active: { label: 'Faol', tone: 'green' },
  rejected: { label: 'Rad etilgan', tone: 'red' },
  closed: { label: 'Yopilgan', tone: 'gray' },
  hidden: { label: 'Yashirilgan', tone: 'gray' },
  // Uy bandligi
  free: { label: 'Bo‘sh', tone: 'green' },
  occupied: { label: 'Band', tone: 'gray' },
  // Ariza / ijara so‘rovi
  sent: { label: 'Yuborildi', tone: 'blue' },
  viewed: { label: 'Ko‘rildi', tone: 'gray' },
  interview: { label: 'Suhbatga chaqirildi', tone: 'amber' },
  accepted: { label: 'Qabul qilindi', tone: 'green' },
  declined: { label: 'Rad etildi', tone: 'red' },
  withdrawn: { label: 'Bekor qilindi', tone: 'gray' },
  // Support / shikoyat
  new: { label: 'Yangi', tone: 'brand' },
  in_review: { label: 'Ko‘rib chiqilmoqda', tone: 'amber' },
  answered: { label: 'Javob berildi', tone: 'blue' },
  resolved: { label: 'Hal qilindi', tone: 'green' },
  dismissed: { label: 'Asossiz', tone: 'gray' },
  // Foydalanuvchi
  blocked: { label: 'Bloklangan', tone: 'red' },
  // Kurs / dars
  published: { label: 'Nashr qilingan', tone: 'green' },
  draft: { label: 'Yashirin', tone: 'gray' },
}
export const LISTING_STATUSES = ['pending', 'active', 'rejected', 'closed']
export const APPLICATION_STATUSES = ['sent', 'viewed', 'interview', 'accepted', 'declined']
export const REQUEST_STATUSES = ['sent', 'viewed', 'accepted', 'declined']

/* ---------------- Support ---------------- */
export const TICKET_TYPES = [
  { value: 'technical', label: 'Texnik muammo' },
  { value: 'account', label: 'Akkaunt' },
  { value: 'job', label: 'Ish/ariza' },
  { value: 'housing', label: 'Turar joy' },
  { value: 'courses', label: 'Kurslar' },
  { value: 'other', label: 'Boshqa' },
]
export const TICKET_STATUSES = ['new', 'in_review', 'answered', 'resolved']

/* ---------------- Shikoyat ---------------- */
export const COMPLAINT_STATUSES = ['new', 'in_review', 'resolved', 'dismissed']
export const PRIORITY = {
  high: { label: 'Yuqori', tone: 'red' },
  medium: { label: 'O‘rta', tone: 'amber' },
  low: { label: 'Past', tone: 'gray' },
}

/* ---------------- Kurslar ---------------- */
export const COURSE_KEYS = ['ru', 'en']
export const QUIZ_SIZE = 5
export const QUIZ_PASS = 3 // 5 tadan kamida 3 ta to‘g‘ri — dars yakunlanadi
