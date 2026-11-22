import { useEffect, useRef, useState } from 'react'
import { RefreshCw } from 'lucide-react'

const TRIGGER = 70 // на сколько пикселей потянуть, чтобы обновить
const MAX_PULL = 110

// В установленном приложении (PWA) у телефона нет своего «потянуть вниз — обновить».
// В обычном браузере он есть, поэтому там компонент ничего не делает.
function isInstalledApp() {
  return window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true
}

// Касание внутри прокручиваемого блока (модалка, список), который сам не в самом верху, — не обновляем
function insideScrolledBlock(target) {
  for (let el = target; el && el !== document.body; el = el.parentElement) {
    if (el.scrollTop > 0) return true
  }
  return false
}

export default function PullToRefresh() {
  const [pull, setPull] = useState(0)
  const [refreshing, setRefreshing] = useState(false)
  const startY = useRef(null)
  const pullRef = useRef(0)

  useEffect(() => {
    if (!isInstalledApp()) return undefined

    const onStart = (event) => {
      if (window.scrollY > 0 || event.touches.length !== 1 || insideScrolledBlock(event.target)) {
        startY.current = null
        return
      }
      startY.current = event.touches[0].clientY
    }
    const onMove = (event) => {
      if (startY.current === null) return
      const delta = event.touches[0].clientY - startY.current
      if (delta <= 0 || window.scrollY > 0) {
        pullRef.current = 0
        setPull(0)
        return
      }
      // Чем дальше тянем, тем «туже» — как в нативных приложениях
      const value = Math.min(MAX_PULL, delta * 0.5)
      pullRef.current = value
      setPull(value)
    }
    const onEnd = () => {
      if (startY.current === null) return
      startY.current = null
      if (pullRef.current >= TRIGGER) {
        setRefreshing(true)
        setPull(TRIGGER)
        window.location.reload()
      } else {
        pullRef.current = 0
        setPull(0)
      }
    }

    window.addEventListener('touchstart', onStart, { passive: true })
    window.addEventListener('touchmove', onMove, { passive: true })
    window.addEventListener('touchend', onEnd)
    window.addEventListener('touchcancel', onEnd)
    return () => {
      window.removeEventListener('touchstart', onStart)
      window.removeEventListener('touchmove', onMove)
      window.removeEventListener('touchend', onEnd)
      window.removeEventListener('touchcancel', onEnd)
    }
  }, [])

  if (!pull && !refreshing) return null
  const ready = pull >= TRIGGER
  return (
    <div className="pull-refresh" style={{ transform: `translate(-50%, ${pull - 50}px)` }} role="status" aria-live="polite">
      <span className={`pull-refresh-icon ${refreshing ? 'spin' : ''}`} style={refreshing ? undefined : { transform: `rotate(${pull * 3}deg)`, opacity: Math.min(1, pull / TRIGGER) }}>
        <RefreshCw size={20} />
      </span>
      <span className="sr-only">{refreshing ? 'Обновляем…' : ready ? 'Отпустите, чтобы обновить' : 'Потяните, чтобы обновить'}</span>
    </div>
  )
}
