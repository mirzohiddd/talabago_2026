import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
import tailwindcss from '@tailwindcss/vite'
import { fileURLToPath, URL } from 'node:url'

/**
 * TalabaGo Support. Barcha manzillar .env orqali:
 *   VITE_API_URL        — brauzer API’ga qaysi manzil orqali murojaat qiladi (standart: /api/v1 — shu host orqali proxy)
 *   BACKEND_URL         — Vite proxy yo‘naltiradigan FastAPI manzili (standart: http://127.0.0.1:8000)
 *   VITE_ALLOWED_HOSTS  — tunnel/domen hostlari (vergul bilan; ".trycloudflare.com" — barcha subdomenlar)
 *   VITE_HMR_CLIENT_PORT — HTTPS tunnel orqali ochilganda 443 (hot reload websocket uchun)
 * Bitta Cloudflare host (https://app...) → Vite → /api va /media → FastAPI: CORS va “mixed content” muammosi bo‘lmaydi.
 */
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.BACKEND_URL || 'http://127.0.0.1:8000'
  const hosts = (env.VITE_ALLOWED_HOSTS || 'localhost,127.0.0.1,.trycloudflare.com').split(',').map((h) => h.trim()).filter(Boolean)
  // Dev server (HMR websocket ham) faqat shu hostlardan ochilgan sahifaga ruxsat beradi
  const hostAllowed = (origin) => {
    try {
      const h = new URL(origin).hostname
      return hosts.includes('all') || hosts.some((x) => (x.startsWith('.') ? h === x.slice(1) || h.endsWith(x) : h === x))
    } catch { return false }
  }
  const proxy = {
    '/api': { target: backend, changeOrigin: false, xfwd: true },
    '/media': { target: backend, changeOrigin: false, xfwd: true },
  }
  // Production rejimi (vite preview): index.html har safar qayta tekshiriladi — Telegram eski versiyani keshdan ochmasin
  const previewHeaders = { 'Cache-Control': 'no-cache' }
  return {
    // Eski Telegram WebView’lar (Android System WebView / iOS 14+) uchun JS sintaksisi pasaytiriladi
    build: { target: ['es2020', 'chrome87', 'safari14', 'firefox90'], cssTarget: ['chrome87', 'safari14'] },
    plugins: [vue(), tailwindcss()],
    resolve: {
      alias: {
        '@': fileURLToPath(new URL('./src', import.meta.url)),
        // Ikkala frontend uchun umumiy: i18n va domen konstantalari
        '@shared': fileURLToPath(new URL('../shared', import.meta.url)),
      },
    },
    server: {
      host: '127.0.0.1',
      port: 5174,
      strictPort: true,
      fs: { allow: ['..'] },
      allowedHosts: hosts.includes('all') ? true : hosts,
      cors: { origin: (origin, cb) => cb(null, !origin || hostAllowed(origin)) },
      proxy,
      hmr: env.VITE_HMR_CLIENT_PORT ? { clientPort: +env.VITE_HMR_CLIENT_PORT } : undefined,
    },
    preview: { host: '127.0.0.1', port: 4174, strictPort: true, allowedHosts: hosts.includes('all') ? true : hosts, proxy, headers: previewHeaders },
  }
})
