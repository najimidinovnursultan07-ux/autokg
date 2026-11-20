import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowLeft, BadgeCheck, CarFront, Check, MapPin, MessageCircle, Navigation, Phone, Share2,
} from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getDealerBySlug } from '../api/dealers.js'
import { resolveMediaUrl } from '../api/client.js'
import CarGrid from '../components/cars/CarGrid.jsx'
import DealerReviews from '../components/dealers/DealerReviews.jsx'
import StarRating from '../components/dealers/StarRating.jsx'
import TwoGisMap from '../components/dealers/TwoGisMap.jsx'
import { LoadingState, ErrorState } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { hasLocation, toLatLng, twoGisPointUrl, twoGisRouteUrl } from '../utils/twoGis.js'

const BRAND_COLORS = ['#1f2937', '#b91c1c', '#1d4ed8', '#047857', '#7c3aed', '#c2410c', '#0f766e']

function brandColor(name = '') {
  const hash = [...name].reduce((sum, ch) => sum + ch.charCodeAt(0), 0)
  return BRAND_COLORS[hash % BRAND_COLORS.length]
}

function initials(name = '') {
  return name.split(/[\s_-]+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
}

function pluralCars(n) {
  const mod10 = n % 10
  const mod100 = n % 100
  if (mod10 === 1 && mod100 !== 11) return 'автомобиль'
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return 'автомобиля'
  return 'автомобилей'
}

const SORTS = {
  new: { label: 'Сначала новые', fn: (a, b) => new Date(b.created_at || 0) - new Date(a.created_at || 0) },
  cheap: { label: 'Дешевле', fn: (a, b) => Number(a.price || 0) - Number(b.price || 0) },
  expensive: { label: 'Дороже', fn: (a, b) => Number(b.price || 0) - Number(a.price || 0) },
  year: { label: 'Год выпуска', fn: (a, b) => Number(b.year || 0) - Number(a.year || 0) },
}

export default function DealerDetailPage() {
  const { slug } = useParams()
  const [dealer, setDealer] = useState(null)
  const [cars, setCars] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [brand, setBrand] = useState('')
  const [sort, setSort] = useState('new')
  const [copied, setCopied] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getDealerBySlug(slug)
      setDealer(data.dealer)
      setCars(data.cars || [])
    } catch (err) {
      setError(getErrorMessage(err, 'Автосалон не найден.'))
    } finally {
      setLoading(false)
    }
  }, [slug])

  useEffect(() => { load() }, [load])

  const mapMarkers = useMemo(
    () => (hasLocation(dealer) ? [{ id: dealer.id, position: toLatLng(dealer) }] : []),
    [dealer],
  )

  const brands = useMemo(() => {
    const counts = new Map()
    cars.forEach((c) => { if (c.brand) counts.set(c.brand, (counts.get(c.brand) || 0) + 1) })
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [cars])

  const visibleCars = useMemo(() => {
    const list = brand ? cars.filter((c) => c.brand === brand) : [...cars]
    return list.sort(SORTS[sort].fn)
  }, [cars, brand, sort])

  if (loading) return <div className="container page-section"><LoadingState label="Загружаем салон…" /></div>
  if (error || !dealer) return <div className="container page-section"><ErrorState message={error || 'Не найдено.'} onRetry={load} /></div>

  const total = dealer.car_count ?? cars.length
  const newCount = cars.filter((c) => c.condition === 'new').length
  const color = brandColor(dealer.name)
  const whatsappHref = dealer.whatsapp
    ? `https://wa.me/${dealer.whatsapp.replace(/\D/g, '')}?text=${encodeURIComponent(`Здравствуйте! Пишу с AutoBuy по поводу автомобилей салона «${dealer.name}».`)}`
    : ''
  const mapQuery = [dealer.city_name, dealer.address].filter(Boolean).join(', ')
  const located = hasLocation(dealer)
  const mapHref = located
    ? twoGisRouteUrl(dealer.latitude, dealer.longitude)
    : dealer.address ? `https://2gis.kg/search/${encodeURIComponent(mapQuery)}` : ''

  const share = async () => {
    const url = window.location.href
    try {
      if (navigator.share) {
        await navigator.share({ title: dealer.name, text: `Автосалон ${dealer.name} на AutoBuy`, url })
        return
      }
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch { /* пользователь отменил */ }
  }

  return (
    <div className="dealer-page">
      <section className="dealer-hero" style={{ '--dealer-color': color }}>
        <div className="container dealer-hero-inner">
          <Link className="dealer-back" to="/dealers"><ArrowLeft size={17} /> Все салоны</Link>
          <button type="button" className="dealer-share" onClick={share} aria-label="Поделиться">
            {copied ? <Check size={18} /> : <Share2 size={18} />}
          </button>
        </div>
      </section>

      <div className="container dealer-body">
        <div className="dealer-card-main">
          <div className="dealer-profile-top">
            <div className="dealer-avatar" style={dealer.logo_url ? undefined : { background: color }}>
              {dealer.logo_url
                ? <img src={resolveMediaUrl(dealer.logo_url)} alt={dealer.name} />
                : <span>{initials(dealer.name)}</span>}
            </div>

            <div className="dealer-identity">
              <div className="dealer-title">
                <h1>{dealer.name}</h1>
                <span className="dealer-verified"><BadgeCheck size={16} /> Партнёр AutoBuy</span>
              </div>
              <a className="dealer-rating-link" href="#reviews">
                <StarRating rating={dealer.rating} count={dealer.reviews_count} />
              </a>
              {(dealer.city_name || dealer.address) && (
                <p className="dealer-location">
                  <MapPin size={16} />
                  <span>{[dealer.city_name, dealer.address].filter(Boolean).join(', ')}</span>
                </p>
              )}
            </div>

            <div className="dealer-cta">
              <div className="dealer-actions">
                {dealer.phone && (
                  <a className="dealer-action dealer-action--call" href={`tel:${dealer.phone}`}>
                    <Phone size={18} /> Позвонить
                  </a>
                )}
                {whatsappHref && (
                  <a className="dealer-action dealer-action--wa" href={whatsappHref} target="_blank" rel="noopener noreferrer">
                    <MessageCircle size={18} /> WhatsApp
                  </a>
                )}
                {mapHref && (
                  <a className="dealer-action dealer-action--ghost" href={mapHref} target="_blank" rel="noopener noreferrer">
                    <Navigation size={18} /> Маршрут
                  </a>
                )}
              </div>
              {dealer.phone && <a className="dealer-phone-text" href={`tel:${dealer.phone}`}>{dealer.phone}</a>}
            </div>
          </div>

          <div className="dealer-profile-bottom">
            <div className="dealer-stats">
              <div><strong>{total}</strong><span>{pluralCars(total)} в наличии</span></div>
              <div><strong>{brands.length || '—'}</strong><span>марок</span></div>
              <div><strong>{newCount}</strong><span>новых авто</span></div>
            </div>
            {dealer.description && (
              <div className="dealer-about">
                <h2>О салоне</h2>
                <p>{dealer.description}</p>
              </div>
            )}
          </div>

          {located && (
            <div className="dealer-map">
              <div className="dealer-map-head">
                <h2>Как добраться</h2>
                <div className="dealer-map-links">
                  <a className="button button--outline" href={twoGisPointUrl(dealer.latitude, dealer.longitude)} target="_blank" rel="noopener noreferrer"><MapPin size={16} /> Открыть в 2ГИС</a>
                  <a className="button button--primary" href={twoGisRouteUrl(dealer.latitude, dealer.longitude)} target="_blank" rel="noopener noreferrer"><Navigation size={16} /> Маршрут</a>
                </div>
              </div>
              {dealer.address && <p className="dealer-map-address"><MapPin size={15} /> {[dealer.city_name, dealer.address].filter(Boolean).join(', ')}</p>}
              <TwoGisMap markers={mapMarkers} height={300} />
            </div>
          )}
        </div>

        <section className="dealer-cars">
          <div className="dealer-cars-head">
            <h2>Автомобили в наличии <span>{total}</span></h2>
            {cars.length > 1 && (
              <select className="dealer-sort" value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Сортировка">
                {Object.entries(SORTS).map(([key, s]) => <option key={key} value={key}>{s.label}</option>)}
              </select>
            )}
          </div>

          {brands.length > 1 && (
            <div className="dealer-chips">
              <button type="button" className={!brand ? 'is-active' : ''} onClick={() => setBrand('')}>
                Все <small>{cars.length}</small>
              </button>
              {brands.map(([name, count]) => (
                <button type="button" key={name} className={brand === name ? 'is-active' : ''} onClick={() => setBrand(name)}>
                  {name} <small>{count}</small>
                </button>
              ))}
            </div>
          )}

          {visibleCars.length
            ? <CarGrid cars={visibleCars} />
            : (
              <div className="dealer-empty">
                <CarFront size={36} />
                <strong>Сейчас нет активных объявлений</strong>
                <span>Позвоните в салон — возможно, нужная машина уже в пути.</span>
              </div>
            )}

          {dealer.car_count > cars.length && (
            <Link className="button button--outline dealer-all-cars" to={`/catalog?dealer=${encodeURIComponent(dealer.slug)}`}>
              Все автомобили салона ({dealer.car_count})
            </Link>
          )}
        </section>

        <div id="reviews">
          <DealerReviews dealer={dealer} />
        </div>
      </div>

      {(dealer.phone || whatsappHref) && (
        <div className="dealer-sticky">
          {dealer.phone && <a className="dealer-action dealer-action--call" href={`tel:${dealer.phone}`}><Phone size={18} /> Позвонить</a>}
          {whatsappHref && <a className="dealer-action dealer-action--wa" href={whatsappHref} target="_blank" rel="noopener noreferrer"><MessageCircle size={18} /> WhatsApp</a>}
        </div>
      )}
    </div>
  )
}
