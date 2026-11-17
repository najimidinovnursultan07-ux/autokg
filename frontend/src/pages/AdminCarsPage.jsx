import { useCallback, useEffect, useState } from 'react'
import { Check, ChevronLeft, ChevronRight, Search, Trash2, X } from 'lucide-react'
import { useSearchParams } from 'react-router-dom'
import { approveAdminCar, deleteAdminCar, getAdminCars, rejectAdminCar } from '../api/admin.js'
import { ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatPrice } from '../utils/format.js'

const PAGE_SIZE = 10
const statusNames = {
  draft: 'Черновик',
  pending: 'На модерации',
  published: 'Опубликовано',
  rejected: 'Отклонено',
  inactive: 'Снято',
  sold: 'Продано',
  removed: 'Удалено',
}
const statusOptions = [
  ['','Все статусы'],
  ['pending','На модерации'],
  ['published','Опубликовано'],
  ['draft','Черновик'],
  ['rejected','Отклонено'],
  ['inactive','Снято с публикации'],
  ['sold','Продано'],
  ['removed','Удалено'],
]

export default function AdminCarsPage() {
  const { notify } = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const search = searchParams.get('search') || ''
  const status = searchParams.get('status') || ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const [searchInput, setSearchInput] = useState(search)
  const [cars, setCars] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [workingId, setWorkingId] = useState(null)
  const [rejecting, setRejecting] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getAdminCars({
        search: search || undefined,
        status: status || undefined,
        page,
        page_size: PAGE_SIZE,
        ordering: '-created_at',
      })
      setCars(response.results || [])
      setCount(response.count || 0)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [page, search, status])

  useEffect(() => {
    load()
  }, [load])

  useEffect(() => {
    setSearchInput(search)
  }, [search])

  const updateQuery = (key, value) => {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value)
    else next.delete(key)
    next.delete('page')
    setSearchParams(next)
  }

  const changePage = (nextPage) => {
    const next = new URLSearchParams(searchParams)
    if (nextPage > 1) next.set('page', String(nextPage))
    else next.delete('page')
    setSearchParams(next)
  }

  const approve = async (car) => {
    const title = `${car.brand} ${car.model_name} ${car.year}`
    if (!window.confirm(`Одобрить объявление «${title}» и опубликовать его?`)) return
    setWorkingId(car.id)
    try {
      await approveAdminCar(car.id)
      notify('Объявление опубликовано.', 'success')
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось одобрить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const reject = async (event) => {
    event.preventDefault()
    if (!rejecting?.reason.trim()) return
    setWorkingId(rejecting.id)
    try {
      await rejectAdminCar(rejecting.id, rejecting.reason.trim())
      notify('Объявление отклонено.', 'success')
      setRejecting(null)
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось отклонить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const remove = async (car) => {
    const title = `${car.brand} ${car.model_name} ${car.year}`
    if (!window.confirm(`Удалить объявление «${title}»? Оно будет снято с публикации, а действие сохранится в журнале модерации.`)) return
    setWorkingId(car.id)
    try {
      await deleteAdminCar(car.id)
      notify('Объявление удалено.', 'success')
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось удалить объявление.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)

  return (
    <section className="admin-page">
      <PageTitle eyebrow="Администрирование" title="Объявления" description="Проверяйте публикации, управляйте статусами и удаляйте нарушающие правила объявления." />
      <div className="admin-toolbar">
        <form className="admin-search-form" onSubmit={(event) => {
          event.preventDefault()
          updateQuery('search', searchInput.trim())
        }}>
          <Search size={18} />
          <input
            type="search"
            value={searchInput}
            onChange={(event) => setSearchInput(event.target.value)}
            placeholder="Марка, модель или email владельца"
            aria-label="Поиск объявлений"
          />
          <button type="submit" className="button button--primary">Найти</button>
        </form>
        <select value={status} onChange={(event) => updateQuery('status', event.target.value)} aria-label="Фильтр по статусу объявления">
          {statusOptions.map(([value, label]) => <option key={value || 'all'} value={value}>{label}</option>)}
        </select>
      </div>

      {loading ? <LoadingState label="Загружаем объявления…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : cars.length ? (
        <>
          <div className="admin-listing-list">
            {cars.map((car) => (
              <article className="admin-listing-row" key={car.id}>
                <div className="admin-listing-main">
                  <span className={`admin-status admin-status--${car.status}`}>{statusNames[car.status] || car.status}</span>
                  <strong>{car.brand} {car.model_name} · {car.year}</strong>
                  <span>{car.owner_email} · {car.city_name}</span>
                </div>
                <strong className="admin-listing-price">{formatPrice(car.price)}</strong>
                <div className="admin-listing-actions">
                  {car.status === 'pending' && (
                    <>
                      <button type="button" className="admin-action-button admin-action-button--success" disabled={workingId === car.id} onClick={() => approve(car)}>
                        <Check size={15} /> Одобрить
                      </button>
                      <button type="button" className="admin-action-button admin-action-button--danger" disabled={workingId === car.id} onClick={() => setRejecting({ id: car.id, title: `${car.brand} ${car.model_name} ${car.year}`, reason: '' })}>
                        <X size={15} /> Отклонить
                      </button>
                    </>
                  )}
                  {car.status !== 'removed' && (
                    <button type="button" className="icon-action icon-action--danger" disabled={workingId === car.id} onClick={() => remove(car)} aria-label="Удалить объявление">
                      <Trash2 size={17} />
                    </button>
                  )}
                </div>
              </article>
            ))}
          </div>
          {pageCount > 1 && (
            <div className="admin-pagination">
              <span>{count} объявлений · страница {page} из {pageCount}</span>
              <div>
                <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => changePage(page - 1)}><ChevronLeft size={16} /> Назад</button>
                <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => changePage(page + 1)}>Далее <ChevronRight size={16} /></button>
              </div>
            </div>
          )}
        </>
      ) : <div className="admin-empty">Объявления не найдены.</div>}

      {rejecting && (
        <div className="admin-modal-backdrop" role="presentation">
          <form className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="reject-title" onSubmit={reject}>
            <h2 id="reject-title">Отклонить объявление</h2>
            <p>{rejecting.title}</p>
            <label className="field-label">Причина<textarea required maxLength={1000} rows={4} value={rejecting.reason} onChange={(event) => setRejecting({ ...rejecting, reason: event.target.value })} /></label>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setRejecting(null)}>Отмена</button>
              <button type="submit" className="button button--primary" disabled={workingId === rejecting.id || !rejecting.reason.trim()}>{workingId === rejecting.id ? 'Отправляем…' : 'Подтвердить отказ'}</button>
            </div>
          </form>
        </div>
      )}
    </section>
  )
}
