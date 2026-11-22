// Установка сайта как приложения (PWA).
// Chrome/Edge присылают событие beforeinstallprompt один раз и рано — ловим его сразу
// при загрузке (модуль импортируется в main.jsx), а кнопка в футере вызывает prompt().
// iPhone/iPad такого события не дают: там только «Поделиться → На экран Домой».

let deferredPrompt = null
const listeners = new Set()
const notify = () => listeners.forEach((listener) => listener())

if (typeof window !== 'undefined') {
  window.addEventListener('beforeinstallprompt', (event) => {
    event.preventDefault()
    deferredPrompt = event
    notify()
  })
  window.addEventListener('appinstalled', () => {
    deferredPrompt = null
    notify()
  })
}

export function subscribeInstall(listener) {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

export function canPromptInstall() {
  return Boolean(deferredPrompt)
}

export function isStandalone() {
  if (typeof window === 'undefined') return false
  return window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
}

export function isIos() {
  if (typeof navigator === 'undefined') return false
  return /iphone|ipad|ipod/i.test(navigator.userAgent)
    || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1)
}

// true — пользователь согласился, false — отказался, null — системного окна нет
export async function promptInstall() {
  if (!deferredPrompt) return null
  const promptEvent = deferredPrompt
  deferredPrompt = null
  notify()
  promptEvent.prompt()
  const { outcome } = await promptEvent.userChoice
  return outcome === 'accepted'
}
