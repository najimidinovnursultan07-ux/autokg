import { useEffect, useMemo, useState } from 'react'
import { ArrowRight, Building2, Car, List, Map as MapIcon, MapPin, Phone } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { getDealers } from '../api/dealers.js'
import { resolveMediaUrl } from '../api/client.js'
import { LoadingState, ErrorState, PageTitle } from '../components/common/States.jsx'
import StarRating from '../components/dealers/StarRating.jsx'
import TwoGisMap from '../components/dealers/TwoGisMap.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { hasLocation, toLatLng, twoGisRouteUrl } from '../utils/twoGis.js'

// Всплывающая карточка салона на карте (DOM-элемент, чтобы ссылка работала через роутер)
function dealerPopup(dealer, navigate) {
  const root = document.createElement('div')
  root.className = 'map-popup'
  const title = document.createElement('strong')
  title.textContent = dealer.name
  root.appendChild(title)
  const meta = [dealer.address, dealer.reviews_count ? `★ ${Number(dealer.rating).toFixed(1)} (${dealer.reviews_count})` : '', `${dealer.car_count} авто`]
  meta.filter(Boolean).forEach((text) => {
    const line = document.createElement('span')
    line.textContent = text
    root.appendChild(line)
  })
  const actions = document.createElement('div')
  actions.className = 'map-popup-actions'
  const open = document.createElement('a')
  open.href = `/dealers/${dealer.slug}`
  open.textContent = 'Открыть салон'
  open.addEventListener('click', (event) => {
    event.preventDefault()
    navigate(`/dealers/${dealer.slug}`)
  })
  const route = document.createElement('a')
  route.href = twoGisRouteUrl(dealer.latitude, dealer.longitude)
  route.target = '_blank'
  route.rel = 'noopener noreferrer'
  route.textContent = 'Маршрут в 2ГИС'
  actions.append(open, route)
  root.appendChild(actions)
  return root
}

export default function DealersPage() {
  const [dealers, setDealers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [view, setView] = useState('list')
  const navigate = useNavigate()
  const markers = useMemo(
    () => dealers.filter(hasLocation).map((dealer) => ({
      id: dealer.id,
      position: toLatLng(dealer),
      popup: dealerPopup(dealer, navigate),
    })),
    [dealers, navigate],
  )

  useEffect(() => {
    getDealers()
      .then(setDealers)
      .catch((err) => setError(getErrorMessage(err, 'Не удалось загрузить список салонов.')))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="container page-section">
      <PageTitle
        eyebrow="AutoBuy"
        title="Автосалоны"
        description="Официальные партнёры платформы AutoBuy в Кыргызстане."
      />
      {!loading && !error && markers.length > 0 && (
        <div className="dealers-view-toggle" role="tablist" aria-label="Вид">
          <button type="button" role="tab" aria-selected={view === 'list'} className={view === 'list' ? 'is-active' : ''} onClick={() => setView('list')}><List size={16} /> Списком</button>
          <button type="button" role="tab" aria-selected={view === 'map'} className={view === 'map' ? 'is-active' : ''} onClick={() => setView('map')}><MapIcon size={16} /> На карте <small>{markers.length}</small></button>
        </div>
      )}
      {loading ? <LoadingState label="Загружаем салоны…" /> : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : view === 'map' ? (
        <div className="dealers-map">
          <TwoGisMap markers={markers} height={520} />
          {markers.length < dealers.length && (
            <small className="dealers-map-note">На карте {markers.length} из {dealers.length} салонов — остальные ещё не отметили адрес.</small>
          )}
        </div>
      ) : (
        <div className="dealer-grid">
          {dealers.map((dealer) => (
            <Link key={dealer.id} to={`/dealers/${dealer.slug}`} className="dealer-card">
              <div className="dealer-card-logo">
                {dealer.logo_url
                  ? <img src={resolveMediaUrl(dealer.logo_url)} alt={dealer.name} />
                  : <Building2 size={40} />
                }
              </div>
              <div className="dealer-card-body">
                <strong>{dealer.name}</strong>
                <StarRating rating={dealer.rating} count={dealer.reviews_count} size={14} compact />
                {dealer.city_name && <span><MapPin size={16} /> {dealer.city_name}</span>}
                {dealer.phone && <span><Phone size={16} /> {dealer.phone}</span>}
                <span className="dealer-car-count"><Car size={16} /> {dealer.car_count} авто</span>
              </div>
              <ArrowRight size={22} className="dealer-card-arrow" />
            </Link>
          ))}
          {!dealers.length && (
            <p className="empty-inline">Автосалоны пока не добавлены.</p>
          )}
        </div>
      )}
    </section>
  )
}
