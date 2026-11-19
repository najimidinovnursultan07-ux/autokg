import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Building2, MapPin, Phone } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getDealerBySlug } from '../api/dealers.js'
import { resolveMediaUrl } from '../api/client.js'
import CarGrid from '../components/cars/CarGrid.jsx'
import { LoadingState, ErrorState } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'

export default function DealerDetailPage() {
  const { slug } = useParams()
  const [dealer, setDealer] = useState(null)
  const [cars, setCars] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

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

  if (loading) return <div className="container page-section"><LoadingState label="Загружаем салон…" /></div>
  if (error || !dealer) return <div className="container page-section"><ErrorState message={error || 'Не найдено.'} onRetry={load} /></div>

  return (
    <section className="container page-section">
      <Link className="back-link" to="/dealers"><ArrowLeft size={17} /> Все салоны</Link>

      <div className="dealer-detail-header">
        <div className="dealer-detail-logo">
          {dealer.logo
            ? <img src={resolveMediaUrl(dealer.logo)} alt={dealer.name} />
            : <Building2 size={48} />
          }
        </div>
        <div className="dealer-detail-info">
          <h1>{dealer.name}</h1>
          {dealer.city_name && <p><MapPin size={15} /> {dealer.city_name}</p>}
          {dealer.address && <p>{dealer.address}</p>}
          {dealer.description && <p className="dealer-description">{dealer.description}</p>}
          <div className="dealer-detail-contacts">
            {dealer.phone && (
              <a className="button button--primary" href={`tel:${dealer.phone}`}>
                <Phone size={16} /> Позвонить
              </a>
            )}
            {dealer.whatsapp && (
              <a
                className="seller-whatsapp"
                href={`https://wa.me/${dealer.whatsapp.replace(/\D/g, '')}?text=Здравствуйте!`}
                target="_blank"
                rel="noopener noreferrer"
              >
                WhatsApp
              </a>
            )}
          </div>
        </div>
      </div>

      <div className="dealer-detail-cars">
        <h2>Автомобили салона ({cars.length})</h2>
        {cars.length ? <CarGrid cars={cars} /> : <p className="empty-inline">Объявлений пока нет.</p>}
      </div>
    </section>
  )
}
