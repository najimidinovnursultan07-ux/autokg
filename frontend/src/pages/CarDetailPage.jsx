import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, Building2, ChevronLeft, ChevronRight, Eye, Fuel, Gauge, GitCompareArrows, MapPin, MessageCircle, Phone, Settings2, ShieldCheck, TrendingDown, X } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { getCar, revealCarContacts } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import FavoriteButton from '../components/cars/FavoriteButton.jsx'
import ShareButtons from '../components/cars/ShareButtons.jsx'
import { ErrorState, LoadingState } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatConvertedPrice, formatDate, formatMileage, formatPrice, getCarTitle } from '../utils/format.js'
import { whatsappLink } from '../utils/contacts.js'
import useRates from '../hooks/useRates.js'
import { addToCompare, isInCompare, removeFromCompare } from '../utils/compare.js'

const labels = {
  engine_type: { petrol: 'Бензин', diesel: 'Дизель', hybrid: 'Гибрид', electric: 'Электро', lpg: 'Газ', other: 'Другое' },
  transmission: { manual: 'Механическая', automatic: 'Автоматическая', cvt: 'Вариатор', robotic: 'Робот' },
  drive_type: { fwd: 'Передний', rwd: 'Задний', awd: 'Полный' },
  body_type: { sedan: 'Седан', hatchback: 'Хэтчбек', suv: 'Внедорожник', wagon: 'Универсал', coupe: 'Купе', minivan: 'Минивэн', pickup: 'Пикап', other: 'Другое' },
  condition: { new: 'Новый', used: 'С пробегом', damaged: 'Требует ремонта' },
}

function SellerContacts({ car }) {
  const [contacts, setContacts] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const message = `Здравствуйте! Интересует ${getCarTitle(car)} на AutoBuy`

  const reveal = async (kind) => {
    setError('')
    const data = await revealCarContacts(car.id, kind)
    setContacts(data)
    return data
  }

  const showPhone = async () => {
    setLoading(true)
    try {
      await reveal('phone')
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось получить номер. Попробуйте ещё раз.'))
    } finally {
      setLoading(false)
    }
  }

  const openWhatsapp = async () => {
    // Окно открываем сразу по клику — иначе браузер заблокирует его после запроса
    const popup = window.open('', '_blank')
    try {
      const data = await reveal('whatsapp')
      const href = whatsappLink(data.whatsapp, message)
      if (!href) throw new Error('no whatsapp')
      if (popup) popup.location.href = href
      else window.location.href = href
    } catch (requestError) {
      popup?.close()
      setError(getErrorMessage(requestError, 'Не удалось открыть WhatsApp. Попробуйте ещё раз.'))
    }
  }

  return (
    <>
      {car.has_whatsapp && (
        <button type="button" className="seller-whatsapp" onClick={openWhatsapp}>
          <MessageCircle size={16} /> Написать в WhatsApp
        </button>
      )}
      {car.has_phone && (contacts?.phone ? (
        <a className="seller-phone seller-phone--revealed" href={`tel:${contacts.phone}`}>
          <Phone size={14} /> {contacts.phone}
        </a>
      ) : (
        <button type="button" className="button button--outline seller-show-phone" onClick={showPhone} disabled={loading}>
          <Phone size={15} /> {loading ? 'Загружаем…' : 'Показать номер'}
        </button>
      ))}
      {error && <p className="seller-contact-error" role="alert">{error}</p>}
    </>
  )
}

function PriceHistory({ history }) {
  if (!history || history.length < 2) return null
  return (
    <div className="detail-card price-history-card">
      <h2>История цены</h2>
      <ul className="price-history">
        {history.map((item, index) => {
          const previous = history[index + 1]
          const diff = previous && previous.currency === item.currency ? Number(item.price) - Number(previous.price) : 0
          return (
            <li key={`${item.changed_at}-${index}`}>
              <span>{formatDate(item.changed_at)}</span>
              <strong>{formatPrice(item.price, item.currency)}</strong>
              {diff !== 0 && (
                <em className={diff < 0 ? 'price-diff price-diff--down' : 'price-diff price-diff--up'}>
                  {diff < 0 ? '−' : '+'}{formatPrice(Math.abs(diff), item.currency)}
                </em>
              )}
              {!previous && <em className="price-diff">первая цена</em>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

export default function CarDetailPage() {
  const { id } = useParams()
  const [car, setCar] = useState(null)
  const [activeImage, setActiveImage] = useState(0)
  const [lightbox, setLightbox] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [inCompare, setInCompare] = useState(false)
  const rates = useRates()

  useEffect(() => {
    if (car) setInCompare(isInCompare(car.id))
  }, [car])

  const toggleCompare = () => {
    if (inCompare) {
      removeFromCompare(car.id)
      setInCompare(false)
    } else {
      const result = addToCompare(car)
      if (result.added) setInCompare(true)
      else if (result.reason === 'full') alert('Максимум 3 автомобиля для сравнения. Удалите один из списка.')
    }
  }

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

  // Lightbox keyboard navigation
  useEffect(() => {
    if (!lightbox) return
    const handleKey = (e) => {
      if (e.key === 'Escape') setLightbox(false)
      if (e.key === 'ArrowRight') setActiveImage((i) => (i + 1) % (car?.images?.length || 1))
      if (e.key === 'ArrowLeft') setActiveImage((i) => (i - 1 + (car?.images?.length || 1)) % (car?.images?.length || 1))
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [lightbox, car])

  if (loading) return <div className="container page-section"><LoadingState label="Загружаем объявление…" /></div>
  if (error || !car) return <div className="container page-section"><ErrorState message={error || 'Объявление не найдено.'} onRetry={loadCar} /><Link className="text-link" to="/catalog"><ArrowLeft size={17} /> Вернуться в каталог</Link></div>

  const images = car.images || []
  const currentImage = images[activeImage]?.url || images[activeImage]?.image
  const features = [
    ['Год выпуска', car.year],
    ['Пробег', formatMileage(car.mileage)],
    ['Двигатель', labels.engine_type[car.engine_type] || car.engine_type],
    ['Объём двигателя', car.engine_volume ? `${car.engine_volume} л` : '—'],
    ['Коробка передач', labels.transmission[car.transmission] || car.transmission],
    ['Привод', labels.drive_type[car.drive_type] || car.drive_type],
    ['Кузов', labels.body_type[car.body_type] || car.body_type],
    ['Состояние', labels.condition[car.condition] || car.condition],
    ...(car.color ? [['Цвет', car.color]] : []),
  ]

  return (
    <section className="container detail-section">
      <Link className="back-link" to="/catalog"><ArrowLeft size={17} /> Каталог</Link>
      <div className="detail-heading">
        <div><span className="eyebrow">{car.city_name || 'Кыргызстан'} · объявление AutoBuy</span><h1>{getCarTitle(car)}</h1></div>
        <div className="detail-heading-actions">
          {car.views_count > 0 && <span className="detail-views"><Eye size={15} /> {car.views_count} просмотров</span>}
          <button
            type="button"
            className={`button button--outline detail-compare-btn ${inCompare ? 'detail-compare-btn--active' : ''}`}
            onClick={toggleCompare}
            title={inCompare ? 'Убрать из сравнения' : 'Добавить к сравнению'}
          >
            <GitCompareArrows size={16} />
            {inCompare ? 'В сравнении' : 'Сравнить'}
          </button>
          <FavoriteButton car={car} className="detail-favorite" />
        </div>
      </div>
      <div className="detail-layout">
        <div className="detail-main">
          <div className="gallery">
            <div className="gallery-main" onClick={() => images.length > 0 && setLightbox(true)} style={{ cursor: images.length > 0 ? 'zoom-in' : 'default' }}>
              {currentImage ? <img src={resolveMediaUrl(currentImage)} alt={getCarTitle(car)} /> : <div className="image-placeholder"><span>AutoBuy</span></div>}
              {images.length > 1 && <>
                <button className="gallery-arrow gallery-arrow--left" onClick={(e) => { e.stopPropagation(); setActiveImage((activeImage - 1 + images.length) % images.length) }} aria-label="Предыдущее фото"><ChevronLeft /></button>
                <button className="gallery-arrow gallery-arrow--right" onClick={(e) => { e.stopPropagation(); setActiveImage((activeImage + 1) % images.length) }} aria-label="Следующее фото"><ChevronRight /></button>
                <span className="gallery-counter">{activeImage + 1} / {images.length}</span>
              </>}
            </div>
            {images.length > 1 && <div className="gallery-thumbs">{images.map((image, index) => <button key={image.id} className={index === activeImage ? 'gallery-thumb gallery-thumb--active' : 'gallery-thumb'} onClick={() => setActiveImage(index)} aria-label={`Фото ${index + 1}`}><img src={resolveMediaUrl(image.thumb || image.image)} alt="" loading="lazy" /></button>)}</div>}
          </div>
          <div className="detail-card">
            <div className="detail-card-heading"><h2>Характеристики</h2><span><ShieldCheck size={16} /> Проверенное объявление</span></div>
            <div className="spec-grid">{features.map(([label, value]) => <div className="spec-item" key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
          </div>
          <div className="detail-card description-card"><h2>Описание</h2><p>{car.description || 'Продавец не добавил описание.'}</p></div>
          <PriceHistory history={car.price_history} />
        </div>
        <aside className="seller-panel">
          <span className="eyebrow">Цена автомобиля</span>
          {car.price_drop && (
            <span className="price-drop-label"><TrendingDown size={14} /> Цена снижена</span>
          )}
          <strong className={`detail-price ${car.price_drop ? 'detail-price--dropped' : ''}`}>{formatPrice(car.price, car.currency)}</strong>
          {car.price_drop && (
            <s className="detail-old-price">{formatPrice(car.price_drop.old_price, car.price_drop.currency)}</s>
          )}
          {formatConvertedPrice(car.price, car.currency, rates) && (
            <span className="detail-converted-price" title={`По курсу НБКР на ${rates.date}: 1 $ = ${Number(rates.rates.USD).toFixed(2)} сом`}>
              {formatConvertedPrice(car.price, car.currency, rates)} <small>по курсу НБКР</small>
            </span>
          )}

          {/* Dealer блок */}
          {car.dealer_detail ? (
            <div className="dealer-panel">
              <Link to={`/dealers/${car.dealer_detail.slug}`} className="dealer-panel-header">
                <span className="dealer-panel-logo">
                  {car.dealer_detail.logo
                    ? <img src={resolveMediaUrl(car.dealer_detail.logo)} alt={car.dealer_detail.name} />
                    : <Building2 size={22} />
                  }
                </span>
                <div>
                  <strong>{car.dealer_detail.name}</strong>
                  {car.dealer_detail.city_name && (
                    <span><MapPin size={12} /> {car.dealer_detail.city_name}</span>
                  )}
                </div>
              </Link>
              {car.dealer_detail.address && (
                <p className="dealer-panel-address">{car.dealer_detail.address}</p>
              )}
            </div>
          ) : (
            <div className="seller-summary">
              <span className="seller-avatar">
                {car.owner_detail?.profile_photo
                  ? <img src={resolveMediaUrl(car.owner_detail.profile_photo)} alt={car.owner_detail.first_name || 'Продавец'} style={{width:'100%',height:'100%',objectFit:'cover',borderRadius:'50%'}} />
                  : <span>{(car.owner_detail?.first_name || 'A').slice(0, 1).toUpperCase()}</span>
                }
              </span>
              <div>
                <strong>
                  {car.owner_detail?.first_name || car.owner_detail?.last_name
                    ? [car.owner_detail.first_name, car.owner_detail.last_name].filter(Boolean).join(' ')
                    : 'Частный продавец'
                  }
                </strong>
                <span><MapPin size={14} /> {car.city_name || 'Кыргызстан'}</span>
              </div>
            </div>
          )}

          {/* Контакты: номер открывается по клику и считается в статистике салона */}
          <SellerContacts car={car} />

          <div className="seller-notice"><ShieldCheck size={17} /><span>Не переводите предоплату до личного осмотра автомобиля.</span></div>
          <ShareButtons
            title={getCarTitle(car)}
            text={`${getCarTitle(car)} — ${formatPrice(car.price, car.currency)} на AutoBuy`}
          />
          <div className="seller-facts">
            <span><Gauge size={16} />{formatMileage(car.mileage)}</span>
            <span><Fuel size={16} />{labels.engine_type[car.engine_type] || '—'}</span>
            <span><Settings2 size={16} />{labels.transmission[car.transmission] || '—'}</span>
          </div>
        </aside>
      </div>

      {/* Lightbox */}
      {lightbox && (
        <div className="lightbox-backdrop" onClick={() => setLightbox(false)} role="dialog" aria-modal="true">
          <button className="lightbox-close" onClick={() => setLightbox(false)} aria-label="Закрыть"><X size={24} /></button>
          <button className="lightbox-arrow lightbox-arrow--left" onClick={(e) => { e.stopPropagation(); setActiveImage((activeImage - 1 + images.length) % images.length) }} aria-label="Предыдущее фото"><ChevronLeft size={36} /></button>
          <div className="lightbox-img-wrap" onClick={(e) => e.stopPropagation()}>
            <img src={resolveMediaUrl(images[activeImage]?.url || images[activeImage]?.image)} alt={getCarTitle(car)} />
            <span className="lightbox-counter">{activeImage + 1} / {images.length}</span>
          </div>
          <button className="lightbox-arrow lightbox-arrow--right" onClick={(e) => { e.stopPropagation(); setActiveImage((activeImage + 1) % images.length) }} aria-label="Следующее фото"><ChevronRight size={36} /></button>
        </div>
      )}
    </section>
  )
}
