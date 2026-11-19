import { useEffect, useState } from 'react'
import { ArrowRight, Building2, Car, MapPin, Phone } from 'lucide-react'
import { Link } from 'react-router-dom'
import { getDealers } from '../api/dealers.js'
import { resolveMediaUrl } from '../api/client.js'
import { LoadingState, ErrorState, PageTitle } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function DealersPage() {
  const [dealers, setDealers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getDealers()
      .then(setDealers)
      .catch((err) => setError(getErrorMessage(err, 'Не удалось загрузить список салонов.')))
      .finally(() => setLoading(false))
  }, [])

  return (
    <section className="container page-section">
      <PageTitle
        eyebrow="AutoKG"
        title="Автосалоны"
        description="Официальные партнёры платформы AutoKG в Кыргызстане."
      />
      {loading ? <LoadingState label="Загружаем салоны…" /> : error ? (
        <ErrorState message={error} onRetry={() => window.location.reload()} />
      ) : (
        <div className="dealer-grid">
          {dealers.map((dealer) => (
            <Link key={dealer.id} to={`/dealers/${dealer.slug}`} className="dealer-card">
              <div className="dealer-card-logo">
                {dealer.logo_url
                  ? <img src={resolveMediaUrl(dealer.logo_url)} alt={dealer.name} />
                  : <Building2 size={32} />
                }
              </div>
              <div className="dealer-card-body">
                <strong>{dealer.name}</strong>
                {dealer.city_name && <span><MapPin size={13} /> {dealer.city_name}</span>}
                {dealer.phone && <span><Phone size={13} /> {dealer.phone}</span>}
                <span className="dealer-car-count"><Car size={13} /> {dealer.car_count} авто</span>
              </div>
              <ArrowRight size={18} className="dealer-card-arrow" />
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
