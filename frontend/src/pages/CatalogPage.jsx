import { useCallback, useEffect, useMemo, useState } from 'react'
import { Clock, Search, SlidersHorizontal, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { getLookups, listCars } from '../api/cars.js'
import { getDealers } from '../api/dealers.js'
import AdBanner from '../components/ads/AdBanner.jsx'
import CarGrid from '../components/cars/CarGrid.jsx'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { addSearchHistory, getSearchHistory, removeSearchHistory } from '../utils/searchHistory.js'

const emptyFilters = {
  search: '',
  brand: '',
  model: '',
  city: '',
  dealer: '',
  price_min: '',
  price_max: '',
  year_min: '',
  year_max: '',
  mileage_min: '',
  mileage_max: '',
  engine_type: '',
  transmission: '',
  drive_type: '',
  body_type: '',
  condition: '',
  murabaha: '',
  ordering: '-published_at',
}

function readFiltersFromUrl(params) {
  return Object.fromEntries(
    Object.entries(emptyFilters).map(([key, defaultValue]) => [
      key,
      params.get(key) || defaultValue,
    ]),
  )
}

function readPageFromUrl(params) {
  const page = Number(params.get('page'))
  return Number.isInteger(page) && page > 0 ? page : 1
}

function createUrlParams(filters, page = 1) {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([key, value]) => {
    if (value && value !== emptyFilters[key]) params.set(key, value)
  })
  if (page > 1) params.set('page', page)
  return params
}

const filtersOptions = {
  engine_type: [['petrol', 'Бензин'], ['diesel', 'Дизель'], ['hybrid', 'Гибрид'], ['electric', 'Электро'], ['lpg', 'Газ'], ['other', 'Другое']],
  transmission: [['manual', 'Механика'], ['automatic', 'Автомат'], ['cvt', 'Вариатор'], ['robotic', 'Робот']],
  drive_type: [['fwd', 'Передний'], ['rwd', 'Задний'], ['awd', 'Полный']],
  body_type: [['sedan', 'Седан'], ['hatchback', 'Хэтчбек'], ['suv', 'Внедорожник'], ['wagon', 'Универсал'], ['coupe', 'Купе'], ['minivan', 'Минивэн'], ['pickup', 'Пикап'], ['other', 'Другое']],
  condition: [['new', 'Новый'], ['used', 'С пробегом'], ['damaged', 'Требует ремонта']],
}

export default function CatalogPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [lookups, setLookups] = useState({ brands: [], models: [], cities: [], dealers: [] })
  const [lookupsError, setLookupsError] = useState('')

  useEffect(() => {
    Promise.all([getLookups(), getDealers().catch(() => [])])
      .then(([catalog, dealers]) => setLookups({ ...catalog, dealers }))
      .catch((requestError) => setLookupsError(getErrorMessage(requestError)))
  }, [])

  return (
    <CatalogResults
      key={searchParams.toString()}
      searchParams={searchParams}
      setSearchParams={setSearchParams}
      lookups={lookups}
      lookupsError={lookupsError}
    />
  )
}

function CatalogResults({ searchParams, setSearchParams, lookups, lookupsError }) {
  const [filters, setFilters] = useState(() => readFiltersFromUrl(searchParams))
  const [appliedFilters, setAppliedFilters] = useState(filters)
  const [cars, setCars] = useState([])
  const [count, setCount] = useState(0)
  const [next, setNext] = useState(null)
  const [previous, setPrevious] = useState(null)
  const [page, setPage] = useState(() => readPageFromUrl(searchParams))
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [mobileFiltersOpen, setMobileFiltersOpen] = useState(false)
  const [searchHistory, setSearchHistory] = useState(() => getSearchHistory())
  const [showHistory, setShowHistory] = useState(false)

  const visibleModels = useMemo(
    () => lookups.models.filter((model) => !filters.brand || String(model.brand) === filters.brand),
    [filters.brand, lookups.models],
  )

  const loadCars = useCallback(async (targetPage = page, activeFilters = appliedFilters) => {
    setLoading(true)
    setError('')
    try {
      const params = Object.fromEntries(
        Object.entries({ ...activeFilters, page: targetPage, page_size: 12 })
          .filter(([, value]) => value !== ''),
      )
      const response = await listCars(params)
      setCars(response.results || [])
      setCount(response.count || 0)
      setNext(response.next)
      setPrevious(response.previous)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить каталог.'))
    } finally {
      setLoading(false)
    }
  }, [appliedFilters, page])

  useEffect(() => {
    loadCars(page, appliedFilters)
  }, [loadCars, page, appliedFilters])

  const update = (key, value) => {
    setFilters((current) => ({
      ...current,
      [key]: value,
      ...(key === 'brand' ? { model: '' } : {}),
    }))
  }

  const submitFilters = (event) => {
    event.preventDefault()
    if (filters.search?.trim()) {
      addSearchHistory(filters.search.trim())
      setSearchHistory(getSearchHistory())
    }
    setPage(1)
    setAppliedFilters(filters)
    setSearchParams(createUrlParams(filters))
    setMobileFiltersOpen(false)
    setShowHistory(false)
  }

  const clearFilters = () => {
    setFilters(emptyFilters)
    setAppliedFilters(emptyFilters)
    setPage(1)
    setSearchParams({})
  }

  const changePage = (targetPage) => {
    setPage(targetPage)
    setSearchParams(createUrlParams(appliedFilters, targetPage))
  }

  const orderingLabels = {
    '-published_at': 'Последние объявления',
    price: 'Сначала дешевле',
    '-price': 'Сначала дороже',
    '-year': 'Сначала новее по году',
    mileage: 'По пробегу',
  }

  return (
    <section className="container page-section">
      <PageTitle
        eyebrow="Подберите автомобиль"
        title="Каталог автомобилей"
        description="Сравнивайте объявления и находите автомобиль под свои задачи."
      />
      {lookupsError && <p className="inline-warning">{lookupsError}</p>}
      <button
        className="button button--outline filter-mobile-toggle"
        type="button"
        onClick={() => setMobileFiltersOpen((open) => !open)}
      >
        <SlidersHorizontal size={17} /> Фильтры
      </button>
      <div className="catalog-layout">
        <aside className={`filter-panel ${mobileFiltersOpen ? 'filter-panel--open' : ''}`}>
          <div className="filter-heading"><h2>Фильтры</h2><button className="icon-button filter-close" onClick={() => setMobileFiltersOpen(false)} aria-label="Закрыть фильтры"><X size={18} /></button></div>
          <form onSubmit={submitFilters}>
            <label className="field-label">Поиск
              <div className="search-history-wrap">
                <input
                  value={filters.search}
                  onChange={(e) => update('search', e.target.value)}
                  onFocus={() => setShowHistory(true)}
                  onBlur={() => setTimeout(() => setShowHistory(false), 150)}
                  placeholder="Марка или модель"
                />
                {showHistory && searchHistory.length > 0 && (
                  <div className="search-history-dropdown">
                    <div className="search-history-header">
                      <span><Clock size={13} /> История поиска</span>
                      <button type="button" onClick={() => { removeSearchHistory('__all__'); setSearchHistory([]); localStorage.removeItem('autobuy_search_history') }}>Очистить</button>
                    </div>
                    {searchHistory.map((item) => (
                      <div key={item} className="search-history-item">
                        <button type="button" onMouseDown={() => { update('search', item); setShowHistory(false) }}><Clock size={12} /> {item}</button>
                        <button type="button" aria-label="Удалить" onMouseDown={() => { removeSearchHistory(item); setSearchHistory(getSearchHistory()) }}><X size={12} /></button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </label>
            <label className="field-label">Марка<select value={filters.brand} onChange={(e) => update('brand', e.target.value)}><option value="">Любая марка</option>{lookups.brands.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
            <label className="field-label">Модель<select value={filters.model} onChange={(e) => update('model', e.target.value)}><option value="">Любая модель</option>{visibleModels.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
            <label className="field-label">Город<select value={filters.city} onChange={(e) => update('city', e.target.value)}><option value="">Любой город</option>{lookups.cities.map((item) => <option value={item.id} key={item.id}>{item.name}</option>)}</select></label>
            <label className="field-label">Автосалон<select value={filters.dealer} onChange={(e) => update('dealer', e.target.value)}><option value="">Все салоны</option>{(lookups.dealers || []).map((item) => <option value={item.slug} key={item.id}>{item.name}</option>)}</select></label>
            <div className="field-label">Цена, сом<div className="field-range"><input type="number" min="0" placeholder="От" value={filters.price_min} onChange={(e) => update('price_min', e.target.value)} /><input type="number" min="0" placeholder="До" value={filters.price_max} onChange={(e) => update('price_max', e.target.value)} /></div></div>
            <div className="field-label">Год выпуска<div className="field-range"><input type="number" min="1980" max="2100" placeholder="От" value={filters.year_min} onChange={(e) => update('year_min', e.target.value)} /><input type="number" min="1980" max="2100" placeholder="До" value={filters.year_max} onChange={(e) => update('year_max', e.target.value)} /></div></div>
            <div className="field-label">Пробег, км<div className="field-range"><input type="number" min="0" placeholder="От" value={filters.mileage_min} onChange={(e) => update('mileage_min', e.target.value)} /><input type="number" min="0" placeholder="До" value={filters.mileage_max} onChange={(e) => update('mileage_max', e.target.value)} /></div></div>
            {Object.entries(filtersOptions).map(([field, options]) => (
              <label className="field-label" key={field}>{{
                engine_type: 'Двигатель',
                transmission: 'Коробка передач',
                drive_type: 'Привод',
                body_type: 'Кузов',
                condition: 'Состояние',
              }[field]}<select value={filters[field]} onChange={(e) => update(field, e.target.value)}><option value="">Не важно</option>{options.map(([value, label]) => <option value={value} key={value}>{label}</option>)}</select></label>
            ))}
            <label className="checkbox-label"><input type="checkbox" checked={filters.murabaha === 'true'} onChange={(e) => update('murabaha', e.target.checked ? 'true' : '')} /> Можно купить по мурабахе</label>
            <label className="field-label">Сортировка<select value={filters.ordering} onChange={(e) => update('ordering', e.target.value)}><option value="-published_at">Сначала новые</option><option value="price">Сначала дешевле</option><option value="-price">Сначала дороже</option><option value="-year">Сначала новее по году</option><option value="mileage">По пробегу</option></select></label>
            <button type="submit" className="button button--primary filter-submit"><Search size={16} /> Показать автомобили</button>
            <button type="button" className="filter-reset" onClick={clearFilters}>Сбросить фильтры</button>
          </form>
        </aside>

        <div className="catalog-results">
          <div className="catalog-results-top">
            <span><strong>{count}</strong> объявлений</span>
            <span className="catalog-sort-label">{orderingLabels[appliedFilters.ordering]}</span>
          </div>
          {loading ? <LoadingState label="Ищем подходящие автомобили…" /> : error ? <ErrorState message={error} onRetry={() => loadCars(page)} /> : cars.length ? (
            <>
              <CarGrid cars={cars} ad={<AdBanner placement="catalog_feed" />} />
              <div className="pagination">
                <button className="button button--outline" type="button" disabled={!previous} onClick={() => changePage(Math.max(1, page - 1))}>Назад</button>
                <span>Страница {page}</span>
                <button className="button button--outline" type="button" disabled={!next} onClick={() => changePage(page + 1)}>Дальше</button>
              </div>
            </>
          ) : (
            <EmptyState title="Ничего не найдено" action={<button className="button button--outline" onClick={clearFilters}>Сбросить фильтры</button>}>
              Попробуйте изменить критерии поиска.
            </EmptyState>
          )}
        </div>
      </div>
    </section>
  )
}
