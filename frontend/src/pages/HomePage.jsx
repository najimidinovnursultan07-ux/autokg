import { useCallback, useEffect, useState } from 'react'
import {
  ArrowRight,
  BadgeCheck,
  CarFront,
  ChevronRight,
  Search,
  ShieldCheck,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { getLookups, listCars } from '../api/cars.js'
import CarGrid from '../components/cars/CarGrid.jsx'
import { ErrorState, LoadingState } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'

const heroImage =
  'https://images.unsplash.com/photo-1555215695-3004980ad54e?auto=format&fit=crop&w=1500&q=85'

export default function HomePage() {
  const [cars, setCars] = useState([])
  const [lookups, setLookups] = useState({ brands: [], models: [], cities: [] })
  const [lookupError, setLookupError] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ search: '', brand: '', city: '' })
  const navigate = useNavigate()
  const brandNames = new Map(lookups.brands.map((brand) => [brand.id, brand.name]))
  const catalogModels = lookups.models.slice(0, 4)

  useEffect(() => {
    getLookups()
      .then(setLookups)
      .catch((requestError) => {
        setLookupError(getErrorMessage(requestError, 'Не удалось загрузить фильтры поиска.'))
      })
  }, [])

  const loadCars = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await listCars({ page_size: 6, ordering: '-published_at' })
      setCars(response.results || [])
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить последние объявления.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadCars()
  }, [loadCars])

  const submitSearch = (event) => {
    event.preventDefault()
    const query = new URLSearchParams()
    if (filters.search.trim()) query.set('search', filters.search.trim())
    if (filters.brand) query.set('brand', filters.brand)
    if (filters.city) query.set('city', filters.city)
    navigate(`/catalog${query.size ? `?${query}` : ''}`)
  }

  return (
    <>
      <section className="hero-section">
        <div className="container hero-content">
          <div className="hero-copy">
            <span className="hero-kicker"><span className="hero-kicker-dot" /> Автомобильный маркетплейс Кыргызстана</span>
            <h1>Лучшие автомобили<br /><em>в одном месте</em></h1>
            <p>Находите, сравнивайте и покупайте автомобиль без лишних хлопот.</p>
            <div className="hero-actions">
              <Link className="button button--primary" to="/catalog">Найти автомобиль <ArrowRight size={17} /></Link>
              <span><ShieldCheck size={16} /> Объявления проходят модерацию</span>
            </div>
          </div>
          <div className="hero-visual" aria-hidden="true">
            <div className="hero-visual-glow" />
            <img src={heroImage} alt="" />
            <div className="hero-image-caption"><span className="hero-caption-dot" /> Новый выбор каждый день</div>
          </div>
        </div>
      </section>

      <section className="container home-search-wrap" aria-label="Поиск автомобилей">
        <form className="home-search-panel" onSubmit={submitSearch}>
          <label className="home-search-field home-search-query">
            <span>Марка или модель</span>
            <span className="home-search-input">
              <Search size={17} />
              <input
                value={filters.search}
                onChange={(event) => setFilters({ ...filters, search: event.target.value })}
                placeholder="Например, Toyota Camry"
                aria-label="Марка или модель"
              />
            </span>
          </label>
          <label className="home-search-field">
            <span>Марка</span>
            <select value={filters.brand} onChange={(event) => setFilters({ ...filters, brand: event.target.value })}>
              <option value="">Любая марка</option>
              {lookups.brands.map((brand) => <option value={brand.id} key={brand.id}>{brand.name}</option>)}
            </select>
          </label>
          <label className="home-search-field">
            <span>Город</span>
            <select value={filters.city} onChange={(event) => setFilters({ ...filters, city: event.target.value })}>
              <option value="">Весь Кыргызстан</option>
              {lookups.cities.map((city) => <option value={city.id} key={city.id}>{city.name}</option>)}
            </select>
          </label>
          <button className="button button--primary home-search-submit" type="submit"><Search size={17} /> Найти авто</button>
          {lookupError && <p className="home-search-error" role="alert">{lookupError}</p>}
        </form>
      </section>

      <section className="container brands-section">
        <div className="section-heading section-heading--compact">
          <div><span className="eyebrow">Выбирайте уверенно</span><h2>Марки в каталоге</h2></div>
          <Link className="text-link" to="/catalog">Все марки <ChevronRight size={17} /></Link>
        </div>
        <div className="brand-shortcuts">
          {lookups.brands.slice(0, 6).map((brand) => (
            <Link
              className="brand-shortcut"
              key={brand.id}
              to={`/catalog?brand=${brand.id}`}
            >
              <span className="brand-shortcut-mark">{brand.name.slice(0, 1)}</span>
              <span>{brand.name}</span>
              <ArrowRight size={14} />
            </Link>
          ))}
          {!lookups.brands.length && !lookupError && <p className="empty-inline">Марки появятся после загрузки каталога.</p>}
        </div>
      </section>

      <section className="container home-section home-section--listings">
        <div className="section-heading">
          <div>
            <span className="eyebrow">Свежие объявления</span>
            <h2>Новые автомобили</h2>
          </div>
          <Link className="text-link" to="/catalog">Смотреть все <ArrowRight size={17} /></Link>
        </div>
        {loading ? (
          <LoadingState label="Загружаем объявления…" />
        ) : error ? (
          <ErrorState message={error} onRetry={loadCars} />
        ) : cars.length ? (
          <CarGrid cars={cars} />
        ) : (
          <div className="empty-inline">
            <CarFront size={26} />
            <span>Пока нет опубликованных объявлений. Загляните в каталог позже.</span>
          </div>
        )}
      </section>

      <section className="popular-models-section">
        <div className="container">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Ассортимент каталога</span>
              <h2>Модели в каталоге</h2>
            </div>
            <Link className="text-link" to="/catalog">Открыть каталог <ArrowRight size={17} /></Link>
          </div>
          <div className="popular-model-grid">
            {catalogModels.map((model, index) => (
              <Link
                className={`popular-model-card popular-model-card--${index + 1}`}
                key={model.id}
                to={`/catalog?model=${model.id}`}
              >
                <span className="popular-model-note">{brandNames.get(model.brand) || 'Модель'}</span>
                <strong>{[brandNames.get(model.brand), model.name].filter(Boolean).join(' ')}</strong>
                <span className="popular-model-link">Смотреть объявления <ArrowRight size={15} /></span>
              </Link>
            ))}
            {!catalogModels.length && !lookupError && <p className="empty-inline">Модели появятся после загрузки каталога.</p>}
          </div>
        </div>
      </section>

      <section className="container value-strip">
        <div className="section-heading value-heading"><div><span className="eyebrow">Почему AutoKG</span><h2>Всё для комфортной покупки</h2></div></div>
        <div className="value-item"><span className="value-icon"><Search size={20} /></span><div><strong>Поиск без лишних шагов</strong><p>Фильтры по марке, городу и характеристикам помогают найти нужное быстрее.</p></div></div>
        <div className="value-item"><span className="value-icon"><ShieldCheck size={20} /></span><div><strong>Внимание к объявлениям</strong><p>Новые публикации проходят модерацию перед появлением в каталоге.</p></div></div>
        <div className="value-item"><span className="value-icon"><BadgeCheck size={20} /></span><div><strong>Удобно продавать</strong><p>Добавляйте фотографии и управляйте объявлениями в личном кабинете.</p></div></div>
      </section>

      <section className="seller-cta">
        <div className="container seller-cta-inner">
          <div><span className="eyebrow eyebrow--light">Просто начать</span><h2>Продайте автомобиль на AutoKG</h2><p>Добавьте описание и фотографии — покупатели найдут ваше объявление в каталоге.</p></div>
          <Link to="/cars/new" className="button button--white"><CarFront size={17} /> Продать автомобиль</Link>
        </div>
      </section>
    </>
  )
}
