import { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, LoaderCircle, Search } from 'lucide-react'
import { Link } from 'react-router-dom'
import { listDashboardCars, saveDashboardCar } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { getDealerProfile, updateDealerProfile } from '../api/dealers.js'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { CAR_STATUS_LABELS, formatPrice, getCarCover, getCarTitle } from '../utils/format.js'

const TERM_FIELDS = [
  'murabaha_enabled', 'murabaha_markup_percent', 'murabaha_min_down_percent',
  'murabaha_max_term_months', 'murabaha_note',
]
const PAGE_SIZE = 20

// Условия мурабахи салона (наценка, взнос, срок)
function MurabahaTerms({ onSaved }) {
  const { notify } = useToast()
  const [form, setForm] = useState(null)
  const [error, setError] = useState('')
  const [saving, setSaving] = useState(false)

  const load = useCallback(async () => {
    setError('')
    try {
      const data = await getDealerProfile()
      setForm(Object.fromEntries(TERM_FIELDS.map((key) => [key, data[key] ?? ''])))
      onSaved(Boolean(data.murabaha_enabled))
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить условия мурабахи.'))
    }
  }, [onSaved])

  useEffect(() => { load() }, [load])

  const save = async (event) => {
    event.preventDefault()
    setSaving(true)
    try {
      const data = await updateDealerProfile(Object.fromEntries(TERM_FIELDS.map((key) => [key, form[key]])))
      setForm(Object.fromEntries(TERM_FIELDS.map((key) => [key, data[key] ?? ''])))
      onSaved(Boolean(data.murabaha_enabled))
      notify('Условия мурабахи сохранены.', 'success')
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось сохранить условия.'), 'error')
    } finally {
      setSaving(false)
    }
  }

  if (error) return <ErrorState message={error} onRetry={load} />
  if (!form) return <LoadingState label="Загружаем условия…" />

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value })

  return (
    <form className="listing-form" onSubmit={save}>
      <section className="form-section">
        <div className="form-section-heading"><span>01</span><div><h2>Условия</h2><p>Одинаковые для всех автомобилей салона, которые продаются по мурабахе.</p></div></div>
        <label className="checkbox-label">
          <input type="checkbox" checked={Boolean(form.murabaha_enabled)} onChange={(e) => setForm({ ...form, murabaha_enabled: e.target.checked })} />
          Салон продаёт автомобили по мурабахе
        </label>
        {form.murabaha_enabled && <>
          <div className="form-grid">
            <label className="field-label">Наценка, % в год<input type="number" required min="0" max="100" step="0.1" value={form.murabaha_markup_percent} onChange={set('murabaha_markup_percent')} placeholder="12" /></label>
            <label className="field-label">Минимальный первый взнос, %<input type="number" required min="0" max="90" step="1" value={form.murabaha_min_down_percent} onChange={set('murabaha_min_down_percent')} placeholder="30" /></label>
            <label className="field-label">Максимальный срок, мес.<input type="number" required min="3" max="120" step="1" value={form.murabaha_max_term_months} onChange={set('murabaha_max_term_months')} placeholder="24" /></label>
          </div>
          <label className="field-label">Примечание для покупателей<input maxLength="300" value={form.murabaha_note} onChange={set('murabaha_note')} placeholder="Например: без поручителей, оформление за 1 день" /></label>
        </>}
        <div className="form-actions">
          <button className="button button--primary" type="submit" disabled={saving}>{saving && <LoaderCircle className="spin" size={16} />} Сохранить условия</button>
        </div>
      </section>
    </form>
  )
}

// Какие автомобили продаются по мурабахе
function MurabahaCars({ enabled }) {
  const { notify } = useToast()
  const [cars, setCars] = useState([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listDashboardCars({ search: search || undefined, page, page_size: PAGE_SIZE })
      setCars(data.results || [])
      setCount(data.count || 0)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [search, page])

  useEffect(() => { load() }, [load])

  const toggle = async (car) => {
    setWorkingId(car.id)
    try {
      const saved = await saveDashboardCar({ murabaha_available: !car.murabaha_available }, car.id)
      setCars((items) => items.map((item) => (item.id === car.id ? { ...item, murabaha_available: saved.murabaha_available } : item)))
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.max(1, Math.ceil(count / PAGE_SIZE))

  return (
    <section className="form-section murabaha-cars">
      <div className="form-section-heading"><span>02</span><div><h2>Автомобили</h2><p>Отметьте, какие автомобили можно купить по мурабахе. У них появится бейдж и калькулятор платежа.</p></div></div>
      {!enabled && <p className="field-hint murabaha-off-hint">Мурабаха выключена — покупатели не увидят отметки, пока вы не включите её в условиях выше.</p>}
      <form className="admin-search-form" onSubmit={(e) => { e.preventDefault(); setPage(1); setSearch(searchInput.trim()) }}>
        <Search size={18} />
        <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Марка, модель, цвет…" aria-label="Поиск объявлений" />
        <button type="submit" className="button button--primary">Найти</button>
      </form>
      {loading ? <LoadingState label="Загружаем объявления…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : cars.length ? (
        <>
          <ul className="murabaha-car-list">
            {cars.map((car) => {
              const image = getCarCover(car)
              return (
                <li key={car.id}>
                  <label className="murabaha-car-row">
                    <input type="checkbox" checked={Boolean(car.murabaha_available)} disabled={workingId === car.id} onChange={() => toggle(car)} aria-label={`Мурабаха: ${getCarTitle(car)}`} />
                    <span className="dealer-car-thumb">{image ? <img src={resolveMediaUrl(image)} alt="" loading="lazy" /> : <span>Нет фото</span>}</span>
                    <span className="murabaha-car-info">
                      <strong>{getCarTitle(car)}</strong>
                      <small>{formatPrice(car.price, car.currency)} · {CAR_STATUS_LABELS[car.status] || car.status}</small>
                    </span>
                  </label>
                </li>
              )
            })}
          </ul>
          {pageCount > 1 && (
            <div className="admin-pagination">
              <span>{count} объявлений · страница {page} из {pageCount}</span>
              <div>
                <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}><ChevronLeft size={16} /> Назад</button>
                <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => setPage(page + 1)}>Далее <ChevronRight size={16} /></button>
              </div>
            </div>
          )}
        </>
      ) : (
        <EmptyState title={search ? 'Ничего не найдено' : 'Объявлений пока нет'}>
          {search ? 'Измените поиск.' : <Link className="text-link" to="/dashboard/cars/new">Добавьте первый автомобиль</Link>}
        </EmptyState>
      )}
    </section>
  )
}

export default function DealerMurabahaPage() {
  const [enabled, setEnabled] = useState(true)
  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Кабинет салона"
        title="Мурабаха"
        description="Покупка в рассрочку без процентов: фиксированная наценка, известная заранее. Задайте условия и отметьте автомобили — покупатели увидят бейдж «Мурабаха» и калькулятор платежа."
      />
      <MurabahaTerms onSaved={setEnabled} />
      <MurabahaCars enabled={enabled} />
    </section>
  )
}
