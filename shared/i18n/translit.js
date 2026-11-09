/**
 * O‘zbek lotin → kirill transliteratsiyasi (UI matnlari va kontent uchun).
 * Brend nomlari, {param}lar, URL, @username va lotin qisqartmalari o‘zgarmaydi.
 */
const KEEP = ['TalabaGo', 'Telegram', 'Developer', 'CRM', 'CV', 'IT', 'SMM', 'Wi-Fi', 'Online', 'Offline', 'online', 'offline',
  'JPG', 'PNG', 'WebP', 'MP4', 'WebM', 'JSON', 'PDF', 'URL', 'Asia/Tashkent', 'Support', 'IELTS', 'Zoom', 'Figma', 'Canva', 'Vue.js', 'GitHub', 'Excel']
const KEEP_RE = new RegExp(`(\\{[^}]+\\}|https?://\\S+|@[\\w.]+|${KEEP.map((k) => k.replace(/[.*+?^${}()|[\]\\/]/g, '\\$&')).join('|')}|\\b[A-Z]{2,}\\b)`, 'g')

const APOS = '[‘’ʻʼ\'`]'
const MULTI = [
  [new RegExp(`O${APOS}`, 'g'), 'Ў'], [new RegExp(`o${APOS}`, 'g'), 'ў'],
  [new RegExp(`G${APOS}`, 'g'), 'Ғ'], [new RegExp(`g${APOS}`, 'g'), 'ғ'],
  [/SH/g, 'Ш'], [/Sh/g, 'Ш'], [/sh/g, 'ш'],
  [/CH/g, 'Ч'], [/Ch/g, 'Ч'], [/ch/g, 'ч'],
  [/YO/g, 'Ё'], [/Yo/g, 'Ё'], [/yo/g, 'ё'],
  [/YU/g, 'Ю'], [/Yu/g, 'Ю'], [/yu/g, 'ю'],
  [/YA/g, 'Я'], [/Ya/g, 'Я'], [/ya/g, 'я'],
  [/YE/g, 'Е'], [/Ye/g, 'Е'], [/ye/g, 'е'],
  [/TS/g, 'Ц'], [/ts(?=[aeiou])/g, 'ц'],
]
const SINGLE = {
  a: 'а', b: 'б', d: 'д', e: 'е', f: 'ф', g: 'г', h: 'ҳ', i: 'и', j: 'ж', k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', q: 'қ',
  r: 'р', s: 'с', t: 'т', u: 'у', v: 'в', x: 'х', y: 'й', z: 'з', c: 'с', w: 'в',
}

function word(s) {
  // so‘z boshidagi "e" → "э"
  s = s.replace(/(^|[^A-Za-z‘’ʻʼ'`])e/g, '$1э').replace(/(^|[^A-Za-z‘’ʻʼ'`])E/g, '$1Э')
  for (const [re, v] of MULTI) s = s.replace(re, v)
  s = s.replace(/[A-Za-z]/g, (c) => {
    const low = SINGLE[c.toLowerCase()]
    if (!low) return c
    return c === c.toLowerCase() ? low : low.toUpperCase()
  })
  return s.replace(/[’ʼ'`]/g, 'ъ').replace(/‘/g, 'ъ')
}

export function toCyrillic(text) {
  if (!text) return text
  const parts = String(text).split(KEEP_RE)
  return parts.map((p, i) => (i % 2 ? p : word(p))).join('')
}
