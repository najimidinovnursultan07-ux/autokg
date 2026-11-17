import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, ChevronLeft, ChevronRight, Fuel, Gauge, MapPin, Phone, Settings2, ShieldCheck } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getCar } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import FavoriteButton from '../components/cars/FavoriteButton.jsx'
import { ErrorState, LoadingState } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatMileage, formatPrice, getCarTitle } from '../utils/format.js'

const labels = {
  engine_type: { petrol: 'Бензин', diesel: 'Дизель', hybrid: 'Гибрид', electric: 'Электро', lpg: 'Газ', other: 'Другое' },
  transmission: { manual: 'Механическая', automatic: 'Автоматическая', cvt: 'Вариатор', robotic: 'Робот' },
  drive_type: { fwd: 'Передний', rwd: 'Задний', awd: 'Полный' },
  body_type: { sedan: 'Седан', hatchback: 'Хэтчбек', suv: 'Внедорожник', wagon: 'Универсал', coupe: 'Купе', minivan: 'Минивэн', pickup: 'Пикап', other: 'Другое' },
  condition: { new: 'Новый', used: 'С пробегом', damaged: 'Требует ремонта' },
}

export default function CarDetailPage() {
  const { id } = useParams()
  const [car, setCar] = useState(null)
  const [activeImage, setActiveImage] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const loadCar = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await getCar(id)
      setCar(data)
      setActiveImage(0)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Объявление не найдено.'))
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => {
    loadCar()
  }, [loadCar])

  if (loading) return <div className="container page-section"><LoadingState label="Загружаем объявление…" /></div>
  if (error || !car) return <div className="container page-section"><ErrorState message={error || 'Объявление не найдено.'} onRetry={loadCar} /><Link className="text-link" to="/catalog"><ArrowLeft size={17} /> Вернуться в каталог</Link></div>

  const images = car.images || []
  const currentImage = images[activeImage]?.image
  const features = [
    ['Год выпуска', car.year],
    ['Пробег', formatMileage(car.mileage)],
    ['Двигатель', labels.engine_type[car.engine_type] || car.engine_type],
    ['Объём двигателя', car.engine_volume ? `${car.engine_volume} л` : '—'],
    ['Коробка передач', labels.transmission[car.transmission] || car.transmission],
    ['Привод', labels.drive_type[car.drive_type] || car.drive_type],
    ['Кузов', labels.body_type[car.body_type] || car.body_type],
    ['Состояние', labels.condition[car.condition] || car.condition],
  ]

  return (
    <section className="container detail-section">
      <Link className="back-link" to="/catalog"><ArrowLeft size={17} /> Каталог</Link>
      <div className="detail-heading">
        <div><span className="eyebrow">{car.city_name || 'Кыргызстан'} · объявление AutoKG</span><h1>{getCarTitle(car)}</h1></div>
        <FavoriteButton car={car} className="detail-favorite" />
      </div>
      <div className="detail-layout">
        <div className="detail-main">
          <div className="gallery">
            <div className="gallery-main">
              {currentImage ? <img src={resolveMediaUrl(currentImage)} alt={getCarTitle(car)} /> : <div className="image-placeholder"><span>AutoKG</span></div>}
              {images.length > 1 && <>
                <button className="gallery-arrow gallery-arrow--left" onClick={() => setActiveImage((activeImage - 1 + images.length) % images.length)} aria-label="Предыдущее фото"><ChevronLeft /></button>
                <button className="gallery-arrow gallery-arrow--right" onClick={() => setActiveImage((activeImage + 1) % images.length)} aria-label="Следующее фото"><ChevronRight /></button>
                <span className="gallery-counter">{activeImage + 1} / {images.length}</span>
              </>}
            </div>
            {images.length > 1 && <div className="gallery-thumbs">{images.map((image, index) => <button key={image.id} className={index === activeImage ? 'gallery-thumb gallery-thumb--active' : 'gallery-thumb'} onClick={() => setActiveImage(index)} aria-label={`Фото ${index + 1}`}><img src={resolveMediaUrl(image.image)} alt="" /></button>)}</div>}
          </div>
          <div className="detail-card">
            <div className="detail-card-heading"><h2>Характеристики</h2><span><ShieldCheck size={16} /> Проверенное объявление</span></div>
            <div className="spec-grid">{features.map(([label, value]) => <div className="spec-item" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
          </div>
          <div className="detail-card description-card"><h2>Описание</h2><p>{car.description || 'Продавец не добавил описание.'}</p></div>
        </div>
        <aside className="seller-panel">
          <span className="eyebrow">Цена автомобиля</span>
          <strong className="detail-price">{formatPrice(car.price)}</strong>
          <div className="seller-summary"><span className="seller-avatar">{(car.contact_phone || 'A').slice(-2)}</span><div><strong>Частный продавец</strong><span><MapPin size={14} /> {car.city_name || 'Кыргызстан'}</span></div></div>
          <a className="button button--primary seller-call" href={`tel:${car.contact_phone}`}><Phone size={18} /> Позвонить продавцу</a>
          <a className="seller-phone" href={`tel:${car.contact_phone}`}>{car.contact_phone}</a>
          <div className="seller-notice"><ShieldCheck size={17} /><span>Не переводите предоплату до личного осмотра автомобиля.</span></div>
          <div className="seller-facts"><span><Gauge size={16} />{formatMileage(car.mileage)}</span><span><Fuel size={16} />{labels.engine_type[car.engine_type] || '—'}</span><span><Settings2 size={16} />{labels.transmission[car.transmission] || '—'}</span></div>
        </aside>
      </div>
    </section>
  )
}
