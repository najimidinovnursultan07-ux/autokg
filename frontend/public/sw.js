// AutoBuy service worker.
// Кэширует только статику самого сайта (same-origin). Запросы к API и медиа бэкенда
// идут мимо service worker, чтобы данные (цены, объявления, авторизация) всегда были свежими.

const VERSION = 'v2'
const SHELL_CACHE = `autobuy-shell-${VERSION}`
const STATIC_CACHE = `autobuy-static-${VERSION}`
const SHELL_URL = '/index.html'

const PRECACHE = [
  '/',
  SHELL_URL,
  '/manifest.webmanifest',
  '/favicon.svg',
  '/favicon.ico',
  '/pwa-192.png',
  '/pwa-512.png',
]

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(SHELL_CACHE)
      .then((cache) => cache.addAll(PRECACHE))
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys
          .filter((key) => key.startsWith('autobuy-') && key !== SHELL_CACHE && key !== STATIC_CACHE)
          .map((key) => caches.delete(key)),
      ))
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event
  if (request.method !== 'GET') return

  const url = new URL(request.url)
  if (url.origin !== self.location.origin) return
  // Данные и файлы бэкенда (когда он на том же домене) — всегда из сети, без кэша
  if (/^\/(api|media|static|django-admin)\//.test(url.pathname)) return

  // Навигация по SPA: сначала сеть, офлайн — закэшированная оболочка.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((response) => {
          if (response.ok) {
            const copy = response.clone()
            caches.open(SHELL_CACHE).then((cache) => cache.put(SHELL_URL, copy))
          }
          return response
        })
        .catch(() => caches.match(SHELL_URL)),
    )
    return
  }

  // Собранные Vite файлы имеют хэш в имени — их можно отдавать из кэша.
  if (url.pathname.startsWith('/assets/')) {
    event.respondWith(
      caches.match(request).then((cached) => cached || fetch(request).then((response) => {
        if (response.ok) {
          const copy = response.clone()
          caches.open(STATIC_CACHE).then((cache) => cache.put(request, copy))
        }
        return response
      })),
    )
    return
  }

  // Остальная статика из public/: отдаём из кэша и обновляем в фоне.
  event.respondWith(
    caches.open(STATIC_CACHE).then((cache) => cache.match(request).then((cached) => {
      const network = fetch(request)
        .then((response) => {
          if (response.ok) cache.put(request, response.clone())
          return response
        })
        .catch(() => cached)
      return cached || network
    })),
  )
})
