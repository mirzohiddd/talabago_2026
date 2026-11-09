"""E2E uchun umumiy: ekrandan gorizontal chiqib ketgan elementlarni topish."""
OVERFLOW_JS = """() => {
  // Ko‘rinadigan element ekranning o‘ng chetidan chiqib ketganmi (body overflow-x: clip bo‘lsa ham aniqlanadi).
  // Ataylab gorizontal aylantiriladigan (overflow-x: auto/scroll/hidden) konteynerlar ichidagilar hisobga olinmaydi.
  const vw = innerWidth, bad = []
  const clipped = (el) => { for (let x = el.parentElement; x && x !== document.body; x = x.parentElement) { const o = getComputedStyle(x).overflowX; if (o === 'auto' || o === 'scroll' || o === 'hidden') return true } return false }
  for (const el of document.querySelectorAll('#app *')) {
    const r = el.getBoundingClientRect()
    if (!r.width || !r.height || r.right <= vw + 1) continue
    const s = getComputedStyle(el)
    if (s.visibility === 'hidden' || s.position === 'fixed' && r.left >= vw) continue
    if (clipped(el)) continue
    bad.push((el.getAttribute('data-testid') || el.tagName.toLowerCase() + '.' + String(el.className).split(' ').slice(0, 2).join('.')) + '@' + Math.round(r.right))
    if (bad.length > 4) break
  }
  return bad
}"""
