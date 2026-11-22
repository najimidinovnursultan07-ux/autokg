import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App.jsx'
import ErrorBoundary from './components/common/ErrorBoundary.jsx'
import { AuthProvider } from './context/AuthContext.jsx'
import { FavoritesProvider } from './context/FavoritesContext.jsx'
import { ToastProvider } from './context/ToastContext.jsx'
import './styles/global.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <BrowserRouter>
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
