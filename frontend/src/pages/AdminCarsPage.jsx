import { useCallback, useEffect, useState } from 'react'
import { ChevronLeft, ChevronRight, ExternalLink, Search, Trash2 } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { deleteAdminCar, getAdminCars, updateAdminCar } from '../api/admin.js'
import { resolveMediaUrl } from '../api/client.js'
import { getAdminDealers } from '../api/dealers.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { CAR_STATUS_LABELS, formatPrice } from '../utils/format.js'

const PAGE_SIZE = 20

export default function AdminCarsPage() {
  const { notify } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') || ''
  const status = searchParams.get('status') || ''
  const dealer = searchParams.get('dealer') || ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const [searchInput, setSearchInput] = useState(search)
  const [cars, setCars] = useState([])
  const [dealers, setDealers] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(null)

  useEffect(() => { getAdminDealers().then(setDealers).catch(() => {}) }, [])

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getAdminCars({
        search: search || undefined,
        status: status || undefined,
        dealer: dealer || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      setCars(response.results || [])
      setCount(response.count || 0)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [page, search, status, dealer])

  useEffect(() => { load() }, [load])
  useEffect(() => { setSearchInput(search) }, [search])

  const setQuery = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  const patch = async (car, payload, message) => {
    setWorkingId(car.id)
    try {
      const updated = await updateAdminCar(car.id, payload)
      setCars((items) => items.map((item) => (item.id === car.id ? updated : item)))
      notify(message, 'success')
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const remove = async () => {
    const car = confirmDelete
    setWorkingId(car.id)
    try {
      await deleteAdminCar(car.id)
      notify('Объявление удалено вместе с фотографиями.', 'success')
      setConfirmDelete(null)
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось удалить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Все объявления" description="Модерация: скрывайте, удаляйте и переносите объявления между салонами." />
      <div className="admin-toolbar">
        <form className="admin-search-form" onSubmit={(e) => { e.preventDefault(); setQuery({ search: searchInput.trim() }) }}>
          <Search size={18} />
          <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Марка, модель, салон, телефон" aria-label="Поиск объявлений" />
          <button type="submit" className="button button--primary">Найти</button>
        </form>
        <select value={status} onChange={(e) => setQuery({ status: e.target.value })} aria-label="Статус">
          <option value="">Все статусы</option>
          {Object.entries(CAR_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
        </select>
        <select value={dealer} onChange={(e) => setQuery({ dealer: e.target.value })} aria-label="Салон">
          <option value="">Все салоны</option>
          {dealers.map((d) => <option key={d.id} value={d.slug}>{d.name}</option>)}
        </select>
      </div>

      {loading ? <LoadingState label="Загружаем объявления…" /> : error ? <ErrorState message={error} onRetry={load} /> : cars.length ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table admin-table--cards">
              <thead><tr><th>Автомобиль</th><th>Салон</th><th>Цена</th><th>Статус</th><th>Действия</th></tr></thead>
              <tbody>
                {cars.map((car) => {
                  const busy = workingId === car.id
                  return (
                    <tr key={car.id}>
                      <td className="admin-card-head">
                        <div className="dealer-car-cell">
                          <span className="dealer-car-thumb">{car.thumb ? <img src={resolveMediaUrl(car.thumb)} alt="" loading="lazy" /> : <span>Нет фото</span>}</span>
                          <span><strong>{car.brand} {car.model_name} · {car.year}</strong><small>{car.city_name} · {new Date(car.created_at).toLocaleDateString('ru-RU')}</small></span>
                        </div>
                      </td>
                      <td data-label="Салон">
                        <select value={car.dealer} disabled={busy} aria-label="Перенести в салон"
                          onChange={(e) => patch(car, { dealer: Number(e.target.value) }, 'Объявление перенесено в другой салон.')}>
                          {!dealers.some((d) => d.id === car.dealer) && <option value={car.dealer}>{car.dealer_name}</option>}
                          {dealers.map((d) => <option key={d.id} value={d.id}>{d.name}</option>)}
                        </select>
                        {car.dealer_is_active === false && <small className="text-danger">салон отключён</small>}
                      </td>
                      <td data-label="Цена">{formatPrice(car.price, car.currency)}</td>
                      <td data-label="Статус">
                        <select value={car.status} disabled={busy} aria-label="Статус"
                          onChange={(e) => patch(car, { status: e.target.value }, 'Статус изменён.')}>
                          {Object.entries(CAR_STATUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}
                        </select>
                      </td>
                      <td data-label="Действия">
                        <div className="table-actions">
                          {car.status === 'active' && car.dealer_is_active && (
                            <Link className="icon-action" to={`/cars/${car.id}`} target="_blank" title="Открыть на сайте" aria-label="Открыть на сайте"><ExternalLink size={16} /></Link>
                          )}
                          <button className="icon-action icon-action--danger" type="button" disabled={busy} onClick={() => setConfirmDelete(car)} title="Удалить" aria-label="Удалить"><Trash2 size={16} /></button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
          {pageCount > 1 && (
            <div className="admin-pagination">
              <span>{count} объявлений · страница {page} из {pageCount}</span>
              <div>
                <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => setQuery({ page: page - 1 > 1 ? String(page - 1) : '' })}><ChevronLeft size={16} /> Назад</button>
                <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => setQuery({ page: String(page + 1) })}>Далее <ChevronRight size={16} /></button>
              </div>
            </div>
          )}
        </>
      ) : <div className="admin-empty">Объявления не найдены.</div>}

      {confirmDelete && (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="admin-delete-title">
            <h2 id="admin-delete-title">Удалить объявление?</h2>
            <p>«{confirmDelete.brand} {confirmDelete.model_name} {confirmDelete.year}» ({confirmDelete.dealer_name}) и все его фото будут удалены безвозвратно. Чтобы просто убрать с сайта, выберите статус «Скрыто».</p>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setConfirmDelete(null)}>Отмена</button>
              <button type="button" className="button button--danger" disabled={workingId === confirmDelete.id} onClick={remove}>Удалить</button>
            </div>
          </div>
        </div>
      )}
    </section>
  )
}
