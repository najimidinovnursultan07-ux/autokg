import { ArrowUpRight, Building2, Gauge, MapPin, Settings2, TrendingDown } from 'lucide-react'
import { Link } from 'react-router-dom'
import { resolveMediaUrl } from '../../api/client.js'
import useRates from '../../hooks/useRates.js'
import { formatConvertedPrice, formatMileage, formatPrice, getCarCover, getCarTitle } from '../../utils/format.js'
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
  const rates = useRates()
  const converted = formatConvertedPrice(car.price, car.currency, rates)
  return (
    <article className={`car-card ${featured ? 'car-card--featured' : ''} ${car.is_top ? 'car-card--top' : ''} ${car.is_highlighted ? 'car-card--highlighted' : ''} ${car.is_urgent ? 'car-card--urgent' : ''}`}>
      <Link to={`/cars/${car.id}`} className="car-card-image">
        {image ? (
          <img src={resolveMediaUrl(image)} alt={getCarTitle(car)} loading="lazy" />
        ) : (
          <div className="image-placeholder"><span>AutoBuy</span></div>
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
        <div className="car-card-price-row">
          <strong className="car-card-price">{formatPrice(car.price, car.currency)}</strong>
          {car.price_drop && (
            <span className="car-card-drop" title="Цена снижена">
              <TrendingDown size={13} />
              <s>{formatPrice(car.price_drop.old_price, car.price_drop.currency)}</s>
            </span>
          )}
        </div>
        {converted && <small className="car-card-converted">{converted}</small>}
        <div className="car-card-meta">
          <span><Gauge size={15} />{formatMileage(car.mileage)}</span>
          <span><Settings2 size={15} />{transmissionLabels[car.transmission] || '—'}</span>
          <span><MapPin size={15} />{car.city_name || 'Кыргызстан'}</span>
        </div>
        {car.dealer_detail && (
          <Link to={`/dealers/${car.dealer_detail.slug}`} className="car-card-dealer">
            <span className="car-card-dealer-logo">
              {car.dealer_detail.logo
                ? <img src={resolveMediaUrl(car.dealer_detail.logo)} alt="" loading="lazy" />
                : <Building2 size={14} />}
            </span>
            <span>{car.dealer_detail.name}</span>
          </Link>
        )}
      </div>
    </article>
  )
}
