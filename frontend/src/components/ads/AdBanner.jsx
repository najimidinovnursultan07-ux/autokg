import { useCallback, useEffect, useRef, useState } from 'react'
import { adClickUrl, getAds, trackAdImpression } from '../../api/ads.js'
import { resolveMediaUrl } from '../../api/client.js'

const MAX_SLIDES = 3
const AUTOPLAY_MS = 5000
const SWIPE_PX = 40

// Порядок слайдов с учётом приоритета: баннер с приоритетом 3 чаще оказывается первым, чем с приоритетом 1
function weightedOrder(banners) {
  const rest = [...banners]
  const order = []
  while (rest.length) {
    const total = rest.reduce((sum, b) => sum + Math.max(1, b.priority || 1), 0)
    let roll = Math.random() * total
    let index = rest.findIndex((b) => (roll -= Math.max(1, b.priority || 1)) <= 0)
    if (index < 0) index = 0
    order.push(rest.splice(index, 1)[0])
  }
  return order
}

const prefersReducedMotion = () =>
  typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

/**
 * Слайдер рекламных баннеров партнёров для места placement (до трёх баннеров).
 * Ничего не рендерит, если сегодня для этого места нет баннеров.
 * Показ баннера засчитывается один раз, когда его слайд хотя бы наполовину виден на экране.
 */
export default function AdBanner({ placement, className = '' }) {
  const [banners, setBanners] = useState([])
  const [current, setCurrent] = useState(0)
  const [paused, setPaused] = useState(false)
  const [inView, setInView] = useState(false)
  const ref = useRef(null)
  const seen = useRef(new Set())
  const touchX = useRef(null)

  useEffect(() => {
    let alive = true
    getAds().then((ads) => {
      if (!alive) return
      setBanners(weightedOrder(ads.filter((ad) => ad.placement === placement)).slice(0, MAX_SLIDES))
      setCurrent(0)
    })
    return () => { alive = false }
  }, [placement])

  // Виден ли слайдер на экране
  useEffect(() => {
    const node = ref.current
    if (!banners.length || !node) return undefined
    if (typeof IntersectionObserver === 'undefined') {
      setInView(true)
      return undefined
    }
    const observer = new IntersectionObserver(
      (entries) => setInView(entries.some((entry) => entry.isIntersecting)),
      { threshold: 0.5 },
    )
    observer.observe(node)
    return () => observer.disconnect()
  }, [banners])

  // Показ текущего слайда
  useEffect(() => {
    const banner = banners[current]
    if (!inView || !banner || seen.current.has(banner.id)) return
    seen.current.add(banner.id)
    trackAdImpression(banner.id)
  }, [inView, current, banners])

  const count = banners.length
  const go = useCallback((index) => setCurrent(((index % count) + count) % count), [count])

  // Автопрокрутка, пока слайдер на экране и посетитель с ним не взаимодействует
  useEffect(() => {
    if (count < 2 || paused || !inView || prefersReducedMotion()) return undefined
    const timer = setTimeout(() => go(current + 1), AUTOPLAY_MS)
    return () => clearTimeout(timer)
  }, [count, current, paused, inView, go])

  if (!count) return null

  const onTouchStart = (e) => { touchX.current = e.touches[0].clientX; setPaused(true) }
  const onTouchEnd = (e) => {
    if (touchX.current != null) {
      const dx = e.changedTouches[0].clientX - touchX.current
      if (Math.abs(dx) > SWIPE_PX) go(current + (dx < 0 ? 1 : -1))
    }
    touchX.current = null
    setPaused(false)
  }

  return (
    <aside
      ref={ref}
      className={`ad-banner ad-banner--${placement} ${className}`}
      aria-label="Реклама"
      aria-roledescription={count > 1 ? 'карусель' : undefined}
      onMouseEnter={() => setPaused(true)}
      onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)}
      onBlur={() => setPaused(false)}
    >
      <div className="ad-banner-viewport" onTouchStart={onTouchStart} onTouchEnd={onTouchEnd}>
        <div className="ad-banner-track" style={{ transform: `translateX(-${current * 100}%)` }}>
          {banners.map((banner, index) => {
            const mobile = banner.mobile_image_url ? resolveMediaUrl(banner.mobile_image_url) : ''
            const active = index === current
            return (
              <a
                key={banner.id}
                href={adClickUrl(banner.id)}
                target="_blank"
                rel="noopener sponsored"
                className="ad-banner-link"
                aria-hidden={active ? undefined : true}
                tabIndex={active ? undefined : -1}
                aria-label={`Реклама: ${banner.advertiser}`}
              >
                <picture>
                  {mobile && <source media="(max-width: 640px)" srcSet={mobile} />}
                  <img src={resolveMediaUrl(banner.image_url)} alt={banner.title} loading={index ? 'lazy' : undefined} />
                </picture>
                <span className="ad-banner-label">Реклама · {banner.advertiser}</span>
              </a>
            )
          })}
        </div>
      </div>
      {count > 1 && (
        <div className="ad-banner-dots">
          {banners.map((banner, index) => (
            <button
              key={banner.id}
              type="button"
              className={`ad-banner-dot${index === current ? ' is-active' : ''}`}
              aria-label={`Баннер ${index + 1} из ${count}`}
              aria-current={index === current ? 'true' : undefined}
              onClick={() => go(index)}
            />
          ))}
        </div>
      )}
    </aside>
  )
}
