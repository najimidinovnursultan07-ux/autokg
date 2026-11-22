import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import ScrollToTop from './components/routing/ScrollToTop.jsx'
import App from './App.jsx'
import ErrorBoundary from './components/common/ErrorBoundary.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { FavoritesProvider } from './context/FavoritesContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import './styles/global.css'
// Ловим beforeinstallprompt сразу при загрузке — для кнопки «Скачать приложение»
import './utils/pwaInstall.js'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
      <ScrollToTop />
      <ToastProvider>
        <AuthProvider>
          <FavoritesProvider>
            <ErrorBoundary>
              <App />
            </ErrorBoundary>
          </FavoritesProvider>
        </AuthProvider>
      </ToastProvider>
    </BrowserRouter>
  </StrictMode>,
)

if (import.meta.env.PROD && 'serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('Service worker registration failed:', error)
    })
  })
}

// После нового деплоя старые файлы страниц удаляются. Если вкладка была открыта до деплоя
// и пытается загрузить такую страницу — один раз перезагружаемся, чтобы получить свежую версию.
window.addEventListener('vite:preloadError', (event) => {
  const key = 'autobuy:chunk-reload'
  let reloadedRecently = false
  try {
    reloadedRecently = Date.now() - Number(sessionStorage.getItem(key) || 0) < 10000
    sessionStorage.setItem(key, String(Date.now()))
  } catch { /* sessionStorage недоступен — просто перезагружаемся */ }
  if (reloadedRecently) return
  event.preventDefault()
  window.location.reload()
})
