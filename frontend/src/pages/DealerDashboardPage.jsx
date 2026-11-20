import { useCallback, useEffect, useState } from 'react'
import { BadgeCheck, ChevronLeft, ChevronRight, Edit3, Eye, EyeOff, Plus, Rocket, Search, Trash2 } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { deleteDashboardCar, listDashboardCars, setDashboardCarStatus } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import PromoteModal from '../components/cars/PromoteModal.jsx'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { CAR_STATUS_LABELS, formatPrice, getCarCover, getCarTitle } from '../utils/format.js'

const PAGE_SIZE = 20
const statusTabs = [['', 'Все'], ['active', 'Активные'], ['hidden', 'Скрытые'], ['sold', 'Проданные']]

export default function DealerDashboardPage() {
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
  const [confirmDelete, setConfirmDelete] = useState(null)
  const [promoteCar, setPromoteCar] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const data = await listDashboardCars({
        search: search || undefined,
        status: status || undefined,
        page,
        page_size: PAGE_SIZE,
      })
      setCars(data.results || [])
      setCount(data.count || 0)
    } catch (err) {
      setError(getErrorMessage(err, 'Не удалось загрузить объявления.'))
    } finally {
      setLoading(false)
    }
  }, [search, status, page])

  useEffect(() => { load() }, [load])

  const setQuery = (changes) => {
    const next = new URLSearchParams(searchParams)
    Object.entries(changes).forEach(([key, value]) => (value ? next.set(key, value) : next.delete(key)))
    if (!('page' in changes)) next.delete('page')
    setSearchParams(next)
  }

  const changeStatus = async (car, newStatus, message) => {
    setWorkingId(car.id)
    try {
      await setDashboardCarStatus(car.id, newStatus)
      notify(message, 'success')
      await load()
    } catch (err) {
      notify(getErrorMessage(err, 'Не удалось изменить статус.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const remove = async () => {
    const car = confirmDelete
    setWorkingId(car.id)
    try {
      await deleteDashboardCar(car.id)
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
    <section className="account-page">
      <PageTitle
        eyebrow="Кабинет салона"
        title="Объявления"
        description="Добавляйте, редактируйте, скрывайте и отмечайте проданные автомобили."
        action={<Link className="button button--primary" to="/dashboard/cars/new"><Plus size={17} /> Добавить авто</Link>}
      />

      <div className="admin-toolbar">
        <form className="admin-search-form" onSubmit={(e) => { e.preventDefault(); setQuery({ search: searchInput.trim() }) }}>
          <Search size={18} />
          <input type="search" value={searchInput} onChange={(e) => setSearchInput(e.target.value)} placeholder="Марка, модель, цвет…" aria-label="Поиск объявлений" />
          <button type="submit" className="button button--primary">Найти</button>
        </form>
        <div className="dealer-status-tabs" role="tablist">
          {statusTabs.map(([value, label]) => (
            <button key={value || 'all'} type="button" role="tab" aria-selected={status === value}
              className={`dealer-status-tab ${status === value ? 'dealer-status-tab--active' : ''}`}
              onClick={() => setQuery({ status: value })}>{label}</button>
          ))}
        </div>
      </div>

      {loading ? <LoadingState label="Загружаем объявления…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : cars.length ? (
        <>
          <div className="admin-table-wrap">
            <table className="admin-table dealer-cars-table">
              <thead>
                <tr><th>Автомобиль</th><th>Цена</th><th>Статус</th><th>Просмотры</th><th title="Сколько раз открыли номер / нажали WhatsApp">Номер / WhatsApp</th><th>Действия</th></tr>
              </thead>
              <tbody>
                {cars.map((car) => {
                  const image = getCarCover(car)
                  const busy = workingId === car.id
                  return (
                    <tr key={car.id}>
                      <td>
                        <div className="dealer-car-cell">
                          <Link to={`/dashboard/cars/${car.id}/edit`} className="dealer-car-thumb">
                            {image ? <img src={resolveMediaUrl(image)} alt="" loading="lazy" /> : <span>Нет фото</span>}
                          </Link>
                          <span>
                            <Link to={`/dashboard/cars/${car.id}/edit`}><strong>{getCarTitle(car)}</strong></Link>
                            <small>{car.city_name} · {car.images?.length || 0} фото</small>
                          </span>
                        </div>
                      </td>
                      <td>{formatPrice(car.price, car.currency)}</td>
                      <td><span className={`admin-status admin-status--${car.status}`}>{CAR_STATUS_LABELS[car.status] || car.status}</span></td>
                      <td>{car.views_count || 0}</td>
                      <td>{car.phone_views || 0} / {car.whatsapp_clicks || 0}</td>
                      <td>
                        <div className="table-actions">
                          <Link className="icon-action" to={`/dashboard/cars/${car.id}/edit`} title="Изменить" aria-label="Изменить"><Edit3 size={16} /></Link>
                          {car.status === 'active' ? (
                            <button className="icon-action" type="button" disabled={busy} title="Скрыть" aria-label="Скрыть"
                              onClick={() => changeStatus(car, 'hidden', 'Объявление скрыто с сайта.')}><EyeOff size={16} /></button>
                          ) : (
                            <button className="icon-action" type="button" disabled={busy} title="Опубликовать" aria-label="Опубликовать"
                              onClick={() => changeStatus(car, 'active', 'Объявление опубликовано.')}><Eye size={16} /></button>
                          )}
                          {car.status !== 'sold' && (
                            <button className="icon-action" type="button" disabled={busy} title="Отметить проданным" aria-label="Отметить проданным"
                              onClick={() => changeStatus(car, 'sold', 'Объявление отмечено как проданное.')}><BadgeCheck size={16} /></button>
                          )}
                          {car.status === 'active' && (
                            <button className="icon-action" type="button" title="Продвинуть" aria-label="Продвинуть"
                              onClick={() => setPromoteCar(car)}><Rocket size={16} /></button>
                          )}
                          <button className="icon-action icon-action--danger" type="button" disabled={busy} title="Удалить" aria-label="Удалить"
                            onClick={() => setConfirmDelete(car)}><Trash2 size={16} /></button>
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
      ) : (
        <EmptyState
          title={search || status ? 'Ничего не найдено' : 'Объявлений пока нет'}
          action={<Link className="button button--primary" to="/dashboard/cars/new"><Plus size={17} /> Добавить первое авто</Link>}
        >
          {search || status ? 'Измените поиск или фильтр статуса.' : 'Добавьте автомобиль — он сразу появится в каталоге.'}
        </EmptyState>
      )}

      {confirmDelete && (
        <div className="admin-modal-backdrop" role="presentation">
          <div className="admin-modal" role="dialog" aria-modal="true" aria-labelledby="delete-title">
            <h2 id="delete-title">Удалить объявление?</h2>
            <p>«{getCarTitle(confirmDelete)}» и все его фотографии будут удалены без возможности восстановления. Если машина продана, лучше отметьте её как «Продано».</p>
            <div className="admin-modal-actions">
              <button type="button" className="button button--secondary" onClick={() => setConfirmDelete(null)}>Отмена</button>
              <button type="button" className="button button--danger" disabled={workingId === confirmDelete.id} onClick={remove}>
                {workingId === confirmDelete.id ? 'Удаляем…' : 'Удалить'}
              </button>
            </div>
          </div>
        </div>
      )}

      {promoteCar && (
        <PromoteModal
          car={promoteCar}
          onClose={() => setPromoteCar(null)}
          onPaymentCreated={(result) => { setPromoteCar(null); window.location.href = result.payment_url }}
        />
      )}
    </section>
  )
}
