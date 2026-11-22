import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  ArrowUp,
  BadgeCheck,
  Building2,
  CalendarDays,
  ChevronRight,
  Crown,
  Flame,
  Leaf,
  Search,
  Settings2,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Wallet,
  Zap,
} from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { getLookups, listCars } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { getDealers } from '../api/dealers.js'
import AdBanner from '../components/ads/AdBanner.jsx'
import CarCard from '../components/cars/CarCard.jsx'
import { EmptyState, ErrorState } from '../components/common/States.jsx'
import Shelf, { ShelfSkeleton } from '../components/home/Shelf.jsx'
import { getErrorMessage } from '../utils/errors.js'
import herofon from '../assets/herofon.png'
import coupeImg from '../assets/body-types/coupe.webp'
import hatchbackImg from '../assets/body-types/hatchback.webp'
import minivanImg from '../assets/body-types/minivan.webp'
import pickupImg from '../assets/body-types/pickup.webp'
import sedanImg from '../assets/body-types/sedan.webp'
import suvImg from '../assets/body-types/suv.webp'
import wagonImg from '../assets/body-types/wagon.webp'

// Постоянные картинки категорий (src/assets/body-types)
const BODY_TYPES = [
  ['sedan', 'Седаны', sedanImg],
  ['suv', 'Внедорожники', suvImg],
  ['hatchback', 'Хэтчбеки', hatchbackImg],
  ['minivan', 'Минивэны', minivanImg],
  ['wagon', 'Универсалы', wagonImg],
  ['pickup', 'Пикапы', pickupImg],
  ['coupe', 'Купе', coupeImg],
]

const QUICK_FILTERS = [
  { label: 'Новые', icon: Sparkles, query: 'condition=new' },
  { label: 'Автомат', icon: Settings2, query: 'transmission=automatic' },
  { label: 'До 1 млн сом', icon: Wallet, query: 'price_max=1000000' },
  { label: 'От 2020 года', icon: CalendarDays, query: 'year_min=2020' },
  { label: 'Гибрид', icon: Leaf, query: 'engine_type=hybrid' },
  { label: 'Электро', icon: Zap, query: 'engine_type=electric' },
]

const DEALER_SHELVES = 3
const PREMIUM_LIMIT = 4

// Стабильный цвет плитки салона без логотипа
function tileColor(name = '') {
  const palette = ['#1f2937', '#b91c1c', '#1d4ed8', '#047857', '#7c3aed', '#c2410c', '#0f766e']
  const hash = [...name].reduce((sum, ch) => sum + ch.charCodeAt(0), 0)
  return palette[hash % palette.length]
}

function initials(name = '') {
  return name.split(/\s+/).filter(Boolean).slice(0, 2).map((w) => w[0]).join('').toUpperCase()
}

export default function HomePage() {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [cars, setCars] = useState([])
  const [dealers, setDealers] = useState([])
  const [brands, setBrands] = useState([])
  const [dealerCars, setDealerCars] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showTop, setShowTop] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const [carsPage, dealerList, lookups] = await Promise.all([
        listCars({ page_size: 24 }),
        getDealers(),
        getLookups().catch(() => ({ brands: [] })),
      ])
      // Премиум-салоны — первыми, дальше по числу машин
      const sortedDealers = [...dealerList].sort(
        (a, b) => Number(b.is_featured) - Number(a.is_featured) || (b.car_count || 0) - (a.car_count || 0),
      )
      setCars(carsPage.results || [])
      setDealers(sortedDealers)
      setBrands(lookups.brands || [])

      // Ленты по самым крупным салонам
      const withCars = sortedDealers.filter((d) => d.car_count > 0)
      const premium = withCars.filter((d) => d.is_featured).slice(0, PREMIUM_LIMIT)
      const regular = withCars.filter((d) => !d.is_featured).slice(0, DEALER_SHELVES)
      const featured = [...premium, ...regular]
      const pages = await Promise.all(
        featured.map((d) => listCars({ dealer: d.slug, page_size: 10 }).catch(() => ({ results: [] }))),
      )
      setDealerCars(Object.fromEntries(featured.map((d, i) => [d.slug, pages[i].results || []])))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  useEffect(() => {
    const onScroll = () => setShowTop(window.scrollY > 600)
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])

  const topCars = useMemo(() => cars.filter((c) => c.is_top || c.is_urgent || c.is_highlighted), [cars])


  const featuredDealers = dealers.filter((d) => !d.is_featured && dealerCars[d.slug]?.length)
  const premiumDealers = dealers.filter((d) => d.is_featured && dealerCars[d.slug]?.length)

  const submitSearch = (event) => {
    event.preventDefault()
    const q = search.trim()
    navigate(q ? `/catalog?search=${encodeURIComponent(q)}` : '/catalog')
  }

  return (
    <div className="home-app">
      {/* Поиск — закреплён под шапкой, как в мобильном приложении */}
      <div className="home-sticky-search">
        <form className="container home-search-pill" onSubmit={submitSearch} role="search">
          <Search size={19} />
          <input
            type="search"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Марка, модель или салон"
            aria-label="Поиск автомобилей"
          />
          {search && <button type="submit" className="home-search-go">Найти</button>}
        </form>
      </div>

      {/* Герой — только на больших экранах */}
      <section className="home-hero-compact">
        <div className="container home-hero-inner">
          <div>
            <span className="eyebrow">Автосалоны Кыргызстана</span>
            <h1>Автомобили от проверенных салонов</h1>
            <p>Все объявления — только от автосалонов-партнёров AutoBuy. Звоните и пишите в WhatsApp напрямую.</p>
          </div>
          <img src={herofon} alt="" aria-hidden="true" />
        </div>
      </section>

      {/* Быстрые фильтры */}
      <div className="chip-row container">
        <Link className="chip chip--icon" to="/catalog" aria-label="Все фильтры"><SlidersHorizontal size={17} /></Link>
        {QUICK_FILTERS.map(({ label, icon: Icon, query }) => (
          <Link key={label} className="chip" to={`/catalog?${query}`}><Icon size={15} /> {label}</Link>
        ))}
      </div>

      <AdBanner placement="home_top" className="container" />

      {error ? (
        <div className="container"><ErrorState message={error} onRetry={load} /></div>
      ) : (
        <>
          {/* Премиум-салоны (тариф «Премиум») — отдельный блок с их машинами */}
          {premiumDealers.length > 0 && (
            <section className="premium-block" aria-labelledby="premium-title">
              <div className="container premium-block-head">
                <span className="eyebrow"><Crown size={14} /> Премиум-салоны</span>
                <h2 id="premium-title">Проверенные салоны AutoBuy</h2>
              </div>
              {premiumDealers.map((d) => (
                <Shelf
                  key={d.slug}
                  title={(
                    <>
                      {d.name}
                      <BadgeCheck size={17} className="verified-mark" aria-label="Проверенный дилер" />
                      <small className="premium-shelf-meta">{d.car_count} авто{d.city_name ? ` · ${d.city_name}` : ''}{d.reviews_count ? ` · ★ ${Number(d.rating).toFixed(1)}` : ''}</small>
                    </>
                  )}
                  icon={(
                    <span className="shelf-dealer-logo" style={d.logo_url ? undefined : { background: tileColor(d.name) }}>
                      {d.logo_url ? <img src={resolveMediaUrl(d.logo_url)} alt="" /> : <b>{initials(d.name)}</b>}
                    </span>
                  )}
                  allTo={`/dealers/${d.slug}`}
                  allLabel="Все авто салона"
                >
                  {dealerCars[d.slug].map((car) => <div key={car.id} className="shelf-card"><CarCard car={car} /></div>)}
                </Shelf>
              ))}
            </section>
          )}

          {/* Популярные салоны — плитки-логотипы */}
          <Shelf title="Популярные салоны" allTo="/dealers" variant="dealers">
            {loading ? <ShelfSkeleton count={6} variant="tile" /> : dealers.map((d) => (
              <Link key={d.id} to={`/dealers/${d.slug}`} className="dealer-tile">
                <span className="dealer-tile-logo" style={d.logo_url ? undefined : { background: tileColor(d.name) }}>
                  {d.logo_url ? <img src={resolveMediaUrl(d.logo_url)} alt={d.name} loading="lazy" /> : <b>{initials(d.name)}</b>}
                </span>
                <strong>{d.name}</strong>
                <small>{d.car_count || 0} авто{d.city_name ? ` · ${d.city_name}` : ''}</small>
              </Link>
            ))}
          </Shelf>

          {/* Категории по типу кузова */}
          <Shelf title="Что ищете?" allTo="/catalog" variant="categories">
            {BODY_TYPES.map(([value, label, image]) => (
              <Link key={value} to={`/catalog?body_type=${value}`} className="category-tile">
                <span className="category-tile-img">
                  <img src={image} alt="" loading="lazy" width="480" height="360" />
                </span>
                <span>{label}</span>
              </Link>
            ))}
          </Shelf>

          <AdBanner placement="home_middle" className="container" />

          {/* Продвигаемые объявления */}
          {!loading && topCars.length > 0 && (
            <Shelf title="Горячие предложения" icon={<Flame size={22} className="shelf-icon-hot" />} allTo="/catalog">
              {topCars.map((car) => <div key={car.id} className="shelf-card"><CarCard car={car} /></div>)}
            </Shelf>
          )}

          {/* Новые поступления */}
          <Shelf title="Новые поступления" allTo="/catalog?ordering=-published_at">
            {loading
              ? <ShelfSkeleton count={4} />
              : cars.map((car) => <div key={car.id} className="shelf-card"><CarCard car={car} /></div>)}
          </Shelf>

          {!loading && !cars.length && (
            <div className="container">
              <EmptyState title="Объявлений пока нет">Автосалоны скоро добавят автомобили — загляните позже.</EmptyState>
            </div>
          )}

          {/* Ленты по салонам */}
          {featuredDealers.slice(0, DEALER_SHELVES).map((d) => (
            <Shelf
              key={d.slug}
              title={d.name}
              icon={(
                <span className="shelf-dealer-logo" style={d.logo_url ? undefined : { background: tileColor(d.name) }}>
                  {d.logo_url ? <img src={resolveMediaUrl(d.logo_url)} alt="" /> : <b>{initials(d.name)}</b>}
                </span>
              )}
              allTo={`/dealers/${d.slug}`}
            >
              {dealerCars[d.slug].map((car) => <div key={car.id} className="shelf-card"><CarCard car={car} /></div>)}
            </Shelf>
          ))}

          {/* Марки */}
          {brands.length > 0 && (
            <Shelf title="Марки" allTo="/catalog" variant="brands">
              {brands.slice(0, 16).map((b) => (
                <Link key={b.id} className="brand-chip" to={`/catalog?brand=${b.id}`}>
                  <span>{b.name.slice(0, 1)}</span>{b.name}
                </Link>
              ))}
            </Shelf>
          )}
        </>
      )}

      <section className="container value-strip">
        <div className="section-heading value-heading"><div><span className="eyebrow">Почему AutoBuy</span><h2>Покупайте у проверенных салонов</h2></div></div>
        <div className="value-item"><span className="value-icon"><ShieldCheck size={20} /></span><div><strong>Только проверенные салоны</strong><p>Объявления публикуют только автосалоны-партнёры, подключённые администрацией AutoBuy.</p></div></div>
        <div className="value-item"><span className="value-icon"><Building2 size={20} /></span><div><strong>Все салоны в одном месте</strong><p>Сравнивайте предложения разных автосалонов без поездок по городу.</p></div></div>
        <div className="value-item"><span className="value-icon"><BadgeCheck size={20} /></span><div><strong>Прямой контакт с салоном</strong><p>Звоните или пишите в WhatsApp салону прямо со страницы автомобиля.</p></div></div>
      </section>

      <section className="seller-cta">
        <div className="container seller-cta-inner">
          <div><span className="eyebrow eyebrow--light">Автосалонам</span><h2>Разместите автосалон на AutoBuy</h2><p>Свой кабинет и страница салона на любом тарифе. Выберите тариф — мы подключим салон и выдадим доступ.</p></div>
          <Link to="/pricing" className="button button--white">Тарифы для салонов <ChevronRight size={17} /></Link>
        </div>
      </section>

      {showTop && (
        <button type="button" className="scroll-top-fab" onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })} aria-label="Наверх">
          <ArrowUp size={22} />
        </button>
      )}
    </div>
  )
}
