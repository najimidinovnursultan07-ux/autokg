import { useCallback, useEffect, useState } from 'react'
import { ArrowLeft, ArrowRight, CarFront, Edit3, EyeOff, Plus, RotateCcw, Send, Trash2 } from 'lucide-react'
import { Link, useSearchParams } from 'react-router-dom'
import { deactivateCar, deleteCar, getMyCars, reactivateCar, submitCar } from '../api/cars.js'
import { resolveMediaUrl } from '../api/client.js'
import { EmptyState, ErrorState, LoadingState, PageTitle } from '../components/common/States.jsx'
import { useToast } from '../context/ToastContext.jsx'
import { getErrorMessage } from '../utils/errors.js'
import { formatPrice, getCarCover, getCarTitle } from '../utils/format.js'

const PAGE_SIZE = 10
const statuses = {
  draft: 'Черновик',
  pending: 'На модерации',
  published: 'Опубликовано',
  rejected: 'Отклонено',
  inactive: 'Снято с публикации',
  sold: 'Продано',
}
const tabs = [
  { label: 'Все объявления', status: '' },
  { label: 'Активные', status: 'published' },
  { label: 'Неактивные', status: 'inactive' },
]

export default function MyCarsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const status = searchParams.get('status') || ''
  const page = Math.max(1, Number(searchParams.get('page')) || 1)
  const [cars, setCars] = useState([])
  const [count, setCount] = useState(0)
  const [loading, setLoading] = useState(true)
  const [workingId, setWorkingId] = useState(null)
  const [error, setError] = useState('')
  const { notify } = useToast()

  const load = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const response = await getMyCars({ status: status || undefined, page, page_size: PAGE_SIZE })
      setCars(response.results || [])
      setCount(response.count ?? 0)
    } catch (requestError) {
      setError(getErrorMessage(requestError, 'Не удалось загрузить ваши объявления.'))
    } finally {
      setLoading(false)
    }
  }, [page, status])

  useEffect(() => {
    load()
  }, [load])

  const performAction = async (car, action) => {
    setWorkingId(car.id)
    try {
      if (action === 'delete') {
        if (!window.confirm(`Удалить объявление «${getCarTitle(car)}»?`)) return
        await deleteCar(car.id)
        notify('Объявление удалено из каталога.', 'success')
      } else if (action === 'submit') {
        await submitCar(car.id)
        notify('Объявление отправлено на модерацию.', 'success')
      } else if (action === 'reactivate') {
        await reactivateCar(car.id)
        notify('Объявление повторно отправлено на проверку.', 'success')
      } else {
        await deactivateCar(car.id)
        notify('Объявление снято с публикации.', 'success')
      }
      await load()
    } catch (requestError) {
      notify(getErrorMessage(requestError, 'Не удалось выполнить действие.'), 'error')
    } finally {
      setWorkingId(null)
    }
  }

  const updatePage = (nextPage) => {
    const nextParams = new URLSearchParams(searchParams)
    if (nextPage > 1) nextParams.set('page', String(nextPage))
    else nextParams.delete('page')
    setSearchParams(nextParams)
  }

  const pageCount = Math.ceil(count / PAGE_SIZE)
  const title = status === 'published' ? 'Активные объявления'
    : status === 'inactive' ? 'Неактивные объявления' : 'Мои объявления'

  return (
    <section className="account-page">
      <PageTitle
        eyebrow="Личный кабинет"
        title={title}
        description="Управляйте публикациями и обновляйте информацию."
        action={<Link className="button button--primary" to="/cars/new"><Plus size={17} /> Добавить автомобиль</Link>}
      />
      <nav className="account-tabs" aria-label="Фильтр объявлений">
        {tabs.map((tab) => {
          const isActive = status === tab.status
          const to = tab.status ? `/my-cars?status=${tab.status}` : '/my-cars'
          return (
            <Link
              className={`account-tab ${isActive ? 'account-tab--active' : ''}`}
              to={to}
              key={tab.label}
              aria-current={isActive ? 'page' : undefined}
            >
              {tab.label}
            </Link>
          )
        })}
      </nav>

      {loading ? <LoadingState label="Загружаем объявления…" /> : error ? (
        <ErrorState message={error} onRetry={load} />
      ) : cars.length ? (
        <>
          <div className="my-cars-list">
            {cars.map((car) => {
              const image = getCarCover(car)
              return (
                <article className="my-car-row" key={car.id}>
                  <Link to={`/cars/${car.id}/edit`} className="my-car-thumb">
                    {image ? <img src={resolveMediaUrl(image)} alt="" /> : <CarFront size={25} />}
                  </Link>
                  <div className="my-car-info">
                    <span className={`status-pill status-pill--${car.status}`}>{statuses[car.status] || car.status}</span>
                    <Link className="my-car-title" to={`/cars/${car.id}/edit`}>{getCarTitle(car)}</Link>
                    <span className="my-car-price">{formatPrice(car.price)}</span>
                    {car.status === 'rejected' && <small className="rejection-note">Проверьте данные объявления и отправьте его повторно.</small>}
                  </div>
                  <div className="my-car-actions">
                    <Link className="icon-action" to={`/cars/${car.id}/edit`} aria-label="Редактировать"><Edit3 size={17} /></Link>
                    {['draft', 'rejected'].includes(car.status) && <button className="icon-action" type="button" disabled={workingId === car.id} onClick={() => performAction(car, 'submit')} aria-label="Отправить на модерацию"><Send size={17} /></button>}
                    {car.status === 'inactive' && <button className="icon-action" type="button" disabled={workingId === car.id} onClick={() => performAction(car, 'reactivate')} aria-label="Повторно опубликовать"><RotateCcw size={17} /></button>}
                    {car.status === 'published' && <button className="icon-action" type="button" disabled={workingId === car.id} onClick={() => performAction(car, 'deactivate')} aria-label="Снять с публикации"><EyeOff size={17} /></button>}
                    <button className="icon-action icon-action--danger" type="button" disabled={workingId === car.id} onClick={() => performAction(car, 'delete')} aria-label="Удалить"><Trash2 size={17} /></button>
                  </div>
                </article>
              )
            })}
          </div>
          {pageCount > 1 && (
            <nav className="account-pagination" aria-label="Страницы объявлений">
              <button type="button" className="button button--secondary" disabled={page <= 1} onClick={() => updatePage(page - 1)}>
                <ArrowLeft size={16} /> Назад
              </button>
              <span>Страница {page} из {pageCount}</span>
              <button type="button" className="button button--secondary" disabled={page >= pageCount} onClick={() => updatePage(page + 1)}>
                Вперёд <ArrowRight size={16} />
              </button>
            </nav>
          )}
        </>
      ) : (
        <EmptyState
          title={status ? 'Объявлений в этом разделе нет' : 'Объявлений пока нет'}
          action={<Link className="button button--primary" to="/cars/new"><Plus size={17} /> Добавить автомобиль</Link>}
        >
          {status === 'published'
            ? 'Опубликованные автомобили появятся здесь.'
            : status === 'inactive'
              ? 'Снятые с публикации автомобили появятся здесь.'
              : 'Создайте объявление — оно появится здесь после сохранения.'}
        </EmptyState>
      )}
      {!loading && !error && count > 0 && <p className="account-list-count">Всего объявлений: {count}</p>}
    </section>
  )
}
