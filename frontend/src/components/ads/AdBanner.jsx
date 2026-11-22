import { useEffect, useRef, useState } from 'react'
import { adClickUrl, getAds, trackAdImpression } from '../../api/ads.js'
import { resolveMediaUrl } from '../../api/client.js'

// Случайный баннер с учётом приоритета: приоритет 3 показывается в 3 раза чаще, чем 1
function pickWeighted(banners) {
  const total = banners.reduce((sum, b) => sum + Math.max(1, b.priority || 1), 0)
  let roll = Math.random() * total
  for (const banner of banners) {
    roll -= Math.max(1, banner.priority || 1)
    if (roll <= 0) return banner
  }
  return banners[0]
}

/**
 * Рекламный баннер партнёра для места placement.
 * Ничего не рендерит, если сегодня для этого места нет баннеров.
 * Показ засчитывается один раз, когда баннер хотя бы наполовину виден на экране.
 */
export default function AdBanner({ placement, className = '' }) {
  const [banner, setBanner] = useState(null)
  const ref = useRef(null)

  useEffect(() => {
    let alive = true
    getAds().then((ads) => {
      const options = ads.filter((ad) => ad.placement === placement)
      if (alive) setBanner(options.length ? pickWeighted(options) : null)
    })
    return () => { alive = false }
  }, [placement])

  useEffect(() => {
    const node = ref.current
    if (!banner || !node) return undefined
    if (typeof IntersectionObserver === 'undefined') {
      trackAdImpression(banner.id)
      return undefined
    }
    const observer = new IntersectionObserver((entries) => {
      if (entries.some((entry) => entry.isIntersecting)) {
        trackAdImpression(banner.id)
        observer.disconnect()
      }
    }, { threshold: 0.5 })
    observer.observe(node)
    return () => observer.disconnect()
  }, [banner])

  if (!banner) return null

  const image = resolveMediaUrl(banner.image_url)
  const mobile = banner.mobile_image_url ? resolveMediaUrl(banner.mobile_image_url) : ''

  return (
    <aside className={`ad-banner ad-banner--${placement} ${className}`} aria-label={`Реклама: ${banner.advertiser}`}>
      <a ref={ref} href={adClickUrl(banner.id)} target="_blank" rel="noopener sponsored" className="ad-banner-link">
        <picture>
          {mobile && <source media="(max-width: 640px)" srcSet={mobile} />}
          <img src={image} alt={banner.title} loading="lazy" />
        </picture>
        <span className="ad-banner-label">Реклама · {banner.advertiser}</span>
      </a>
    </aside>
  )
}
