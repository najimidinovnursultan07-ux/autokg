import { ArrowUpRight, Gauge, MapPin, Settings2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { resolveMediaUrl } from '../../api/client.js'
import { formatMileage, formatPrice, getCarCover, getCarTitle } from '../../utils/format.js'
import FavoriteButton from './FavoriteButton.jsx'
import CarBadges from './CarBadges.jsx'

const transmissionLabels = {
  manual: 'Механика',
  automatic: 'Автомат',
  cvt: 'Вариатор',
  robotic: 'Робот',
}

export default function CarCard({ car, featured = false }) {
  const image = getCarCover(car)
  return (
    <article className={`car-card ${featured ? 'car-card--featured' : ''} ${car.is_top ? 'car-card--top' : ''} ${car.is_highlighted ? 'car-card--highlighted' : ''} ${car.is_urgent ? 'car-card--urgent' : ''}`}>
      <Link to={`/cars/${car.id}`} className="car-card-image">
        {image ? (
          <img src={resolveMediaUrl(image)} alt={getCarTitle(car)} loading="lazy" />
        ) : (
          <div className="image-placeholder"><span>AutoKG</span></div>
        )}
        {car.condition === 'new' && <span className="car-badge">Новый</span>}
        <span className="image-count">{car.images?.length || 0} фото</span>
        <CarBadges car={car} size="sm" />
      </Link>
      <FavoriteButton car={car} className="car-card-favorite" />
      <div className="car-card-body">
        <div className="car-card-heading">
          <Link to={`/cars/${car.id}`} className="car-card-title">
            {getCarTitle(car)}
          </Link>
          <Link to={`/cars/${car.id}`} className="card-arrow" aria-label="Подробнее">
            <ArrowUpRight size={17} />
          </Link>
        </div>
        <strong className="car-card-price">{formatPrice(car.price)}</strong>
        <div className="car-card-meta">
          <span><Gauge size={15} />{formatMileage(car.mileage)}</span>
          <span><Settings2 size={15} />{transmissionLabels[car.transmission] || '—'}</span>
          <span><MapPin size={15} />{car.city_name || 'Кыргызстан'}</span>
        </div>
      </div>
    </article>
  )
}
